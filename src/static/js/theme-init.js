// Runs in <head> before the CSS (DESIGN.md "Tema dan mode"): light theme by default, mode "simple" by default.
(function () {
  var theme = null, mode = null;
  try {
    theme = localStorage.getItem("prasibali-theme");
    mode = localStorage.getItem("prasibali-mode");
  } catch (e) {}
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.documentElement.dataset.mode = mode === "advanced" ? "advanced" : "simple";
})();
