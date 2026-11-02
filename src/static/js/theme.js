// Theme toggle (DESIGN.md "Tema dan mode"): light by default, the button names the theme it switches to.
(function () {
  function isDark() {
    return document.documentElement.classList.contains("dark");
  }

  function sync(button) {
    var dark = isDark();
    // Only the label changes; the sun/moon icons switch through the .dark class in CSS.
    var label = button.querySelector("[data-label]") || button;
    label.textContent = dark ? button.dataset.labelLight : button.dataset.labelDark;
    button.setAttribute("aria-pressed", dark ? "true" : "false");
  }

  document.addEventListener("DOMContentLoaded", function () {
    var buttons = document.querySelectorAll("[data-theme-toggle]");
    buttons.forEach(function (button) {
      sync(button);
      button.addEventListener("click", function () {
        var dark = !isDark();
        document.documentElement.classList.toggle("dark", dark);
        try {
          localStorage.setItem("prasibali-theme", dark ? "dark" : "light");
        } catch (e) {}
        buttons.forEach(sync);
      });
    });
  });
})();
