// Theme (DESIGN.md "Tema dan mode"): light by default. The navbar toggle names the theme it switches to; the
// settings page has one button per theme ([data-theme-set], aria-pressed). Both are kept in sync.
(function () {
  function isDark() {
    return document.documentElement.classList.contains("dark");
  }

  function apply(dark) {
    document.documentElement.classList.toggle("dark", dark);
    try {
      localStorage.setItem("prasibali-theme", dark ? "dark" : "light");
    } catch (e) {}
    syncAll();
  }

  function syncAll() {
    var dark = isDark();
    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
      // Only the label changes; the sun/moon icons switch through the .dark class in CSS.
      var label = button.querySelector("[data-label]") || button;
      label.textContent = dark ? button.dataset.labelLight : button.dataset.labelDark;
      button.setAttribute("aria-pressed", dark ? "true" : "false");
    });
    document.querySelectorAll("[data-theme-set]").forEach(function (button) {
      button.setAttribute("aria-pressed", (button.dataset.themeSet === "dark") === dark ? "true" : "false");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    syncAll();
    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
      button.addEventListener("click", function () { apply(!isDark()); });
    });
    document.querySelectorAll("[data-theme-set]").forEach(function (button) {
      button.addEventListener("click", function () { apply(button.dataset.themeSet === "dark"); });
    });
  });
})();
