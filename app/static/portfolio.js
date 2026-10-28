// Portfolio gallery: category dropdown + Show more / Show less.
// The first render comes from the server (the URL picks the initial filter). Changing the
// dropdown fetches a server-rendered fragment so the filter logic lives in one place,
// and never touches the page URL.
(function () {
  // Email is shown as "name [at] domain.com" in the HTML to avoid scrapers, and turned into
  // a real mailto: link here. Without JS the link jumps to the intro, where the
  // address is readable.
  Array.prototype.forEach.call(document.querySelectorAll("a.email-link"), function (a) {
    a.href = "mailto:" + a.dataset.email.replace(/\s*\[at\]\s*/i, "@");
  });

  var select = document.getElementById("category-filter");
  var region = document.getElementById("gallery-region");
  if (!select || !region) return;

  var latestRequest = 0;

  function gallery() {
    return document.getElementById("gallery");
  }

  function wireShowMore() {
    var button = document.getElementById("show-more");
    var grid = document.getElementById("project-list");
    if (!button || !grid) return;
    button.addEventListener("click", function () {
      var expanded = grid.classList.toggle("expanded");
      button.setAttribute("aria-expanded", expanded ? "true" : "false");
      button.textContent = expanded ? button.dataset.less : button.dataset.more;
    });
  }

  // Keep the dropdown in step with what is actually rendered. This also overrides
  // browser form restoration on refresh and back/forward, so a route always starts
  // from its own filter.
  function syncSelect() {
    var g = gallery();
    if (g) select.value = g.dataset.category;
  }

  select.addEventListener("change", function () {
    var category = select.value;
    var request = ++latestRequest;
    fetch(select.dataset.galleryUrl + "?category=" + encodeURIComponent(category), {
      headers: { "X-Requested-With": "fetch" },
    })
      .then(function (response) {
        if (!response.ok) throw new Error("bad response");
        return response.text();
      })
      .then(function (html) {
        if (request !== latestRequest) return; // a newer change superseded this one
        region.innerHTML = html;
        wireShowMore();
      })
      .catch(function () {
        if (request === latestRequest) syncSelect(); // keep dropdown honest on failure
      });
  });

  window.addEventListener("pageshow", syncSelect);
  syncSelect();
  wireShowMore();
})();
