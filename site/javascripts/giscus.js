/**
 * Embed Giscus on individual production pages only (pathname mapping).
 * Configuration mirrors wiki.toml [giscus].
 */
(function () {
  var PRODUCTION_PATH = /^\/productions\/\d{4}\/\d{2}\/[^/]+\/?$/;

  if (!PRODUCTION_PATH.test(window.location.pathname)) {
    return;
  }

  var footer = document.querySelector(".wiki-contribute-footer");
  if (!footer) {
    return;
  }

  var host = document.createElement("div");
  host.className = "giscus-host";
  footer.insertAdjacentElement("afterend", host);

  var script = document.createElement("script");
  script.src = "https://giscus.app/client.js";
  script.setAttribute("data-repo", "coleamckenna/la-trobe-student-theatre-history");
  script.setAttribute("data-repo-id", "R_kgDOSTvE8A");
  script.setAttribute("data-category", "General");
  script.setAttribute("data-category-id", "DIC_kwDOSTvE8M4C-ayT");
  script.setAttribute("data-mapping", "pathname");
  script.setAttribute("data-strict", "0");
  script.setAttribute("data-reactions-enabled", "1");
  script.setAttribute("data-emit-metadata", "0");
  script.setAttribute("data-input-position", "bottom");
  script.setAttribute("data-theme", "purple_dark");
  script.setAttribute("data-lang", "en");
  script.setAttribute("data-loading", "lazy");
  script.setAttribute("crossorigin", "anonymous");
  script.async = true;
  host.appendChild(script);
})();
