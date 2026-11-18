// Released notices / Candidate fixes tabs on the notices list.
(function () {
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.notices-tabs [role="tab"]'));
  if (!tabs.length) return;

  function select(tab, focus) {
    tabs.forEach(function (t) {
      var on = t === tab;
      t.setAttribute("aria-selected", on);
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
    if (focus) tab.focus();
  }

  tabs.forEach(function (tab, i) {
    tab.addEventListener("click", function () {
      select(tab);
      history.replaceState(null, "", tab.id === "tab-candidates" ? "#candidates" : location.pathname + location.search);
    });
    tab.addEventListener("keydown", function (e) {
      var d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (d) { e.preventDefault(); select(tabs[(i + d + tabs.length) % tabs.length], true); }
    });
  });

  function fromHash() {
    if (location.hash === "#candidates") {
      select(document.getElementById("tab-candidates"));
      document.querySelector(".notices-tabs").scrollIntoView();
    }
  }
  window.addEventListener("hashchange", fromHash);
  fromHash();
})();
