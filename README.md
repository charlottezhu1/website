# Personal Website

A Flask + Supabase personal website for Charlotte (Xuyang) Zhu. It combines a portfolio with an emotionally aware AI chat agent.

## What it does

**Portfolio**
- Home page, research, projects (with detail pages), writings and articles, drawings, and photos.
- A PhD application tracker at `/phd-tracker`, backed by a CRUD API (`/api/phd-applications`) and protected by a dev password.

**"Charlotte" AI chat (`/chat`)**
- Users sign in through Supabase Auth. Each user has a role (friend, parent, colleague, and so on).
- Messages go to DeepSeek Chat. The system prompt is in `app/utils/system_prompts/charlotte.txt`.
- The agent tracks its own emotional state (emotion plus intensity) separately for each user.
- It remembers past conversations in a memory stream and retrieves relevant context by vector similarity. Retrieval is weighted about 70% toward the user's own memories and 30% toward shared ones.
- Conversations can be saved with a quality score. An auto-observer extracts insights from them into a shared knowledge base.
- Embeddings use multilingual E5 (768 dimensions). The embedding code is currently disabled in `requirements.txt`.

## Structure

```
main.py                    entry point
app/__init__.py            app factory, Supabase setup
app/routes/index_routes.py portfolio, articles, PhD tracker, dev auth
app/routes/chat_routes.py  chat, auth, emotion/memory logs, saving
app/utils/                 agent components, LLM calls, prompts, project data
app/templates, app/static  Jinja templates, chat.js, style.css
sqls/                      database migrations (run in order)
scripts/                   populate_embeddings.py
```

## Run

```bash
pip install -r requirements.txt
python main.py
```

API keys and database credentials live in `settings.py`. Move them to environment variables before deploying.
