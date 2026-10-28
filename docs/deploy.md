# Deploying to Lightsail

The public site is a small Flask app with no database. Production runs `wsgi.py`, which serves only the
portfolio: no Supabase, no `settings.py`, and none of the chat, admin, or dev-login routes.

```bash
gunicorn wsgi:app --workers 2 --bind 127.0.0.1:8000
```

It has to run behind the web server you already use (nginx or Apache) that forwards your domain to
port 8000, or it can listen on the port the old app used. On macOS, add
`OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` when testing locally. A Linux server does not need it.

## 1. Find out how the current site is run (read-only)

SSH into the instance and run these. They change nothing.

```bash
ps aux | grep -E "gunicorn|flask|python" | grep -v grep
sudo systemctl list-units --type=service | grep -Ei "gunicorn|flask|app|site"
sudo nginx -T 2>/dev/null | grep -E "server_name|proxy_pass|root"
```

Note the folder the app lives in and the service name. Everything below assumes a service called `site`
in `~/website`. Substitute yours.

## 2. Update

```bash
cd ~/website
cp -r ~/website ~/website-backup-$(date +%F)     # a copy you can switch back to
git fetch --all
git checkout main && git pull                     # the merged restyle
python3 -m venv .venv && .venv/bin/pip install -r requirements-prod.txt
```

Point the service at the new command: `ExecStart=/home/<user>/website/.venv/bin/gunicorn wsgi:app --workers 2 --bind 127.0.0.1:8000`
(edit with `sudo systemctl edit --full site`), then:

```bash
sudo systemctl daemon-reload && sudo systemctl restart site
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/     # expect 200
```

## 3. Check it

Open your domain on a phone and a laptop. Try `/apm`, `/engineering`, `/research`, `/publications`, and a
page that does not exist (it should show the "Page not found" page).

## Roll back

```bash
cd ~/website && git checkout academic-v1
sudo systemctl restart site
```

or restore the `~/website-backup-<date>` copy. The old site is also kept on GitHub as the `academic` branch.

## Notes

- Everything in `app/static/` is public, including every PDF in `app/static/files/`.
- Content edits (`content/*.yaml`) show up on the next page load; there is no build step. Only a new route in
  `route_filters` needs a service restart.
- HTTPS and the domain's DNS are handled in Lightsail (the instance's networking tab). Nothing in this repo changes them.
