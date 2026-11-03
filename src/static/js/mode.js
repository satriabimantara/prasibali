// Mode toggle (DESIGN.md "Pengalih mode"): General user by default, Advanced = Mode Peneliti.
// Stores the choice in localStorage, sets <html data-mode>, and copies it into every form's hidden `mode` field
// so the server knows whether to use the research choices or the defaults. Uses event delegation and re-applies
// after HTMX swaps, because the workspace (with its toggle and form) is replaced after every analysis.
(function () {
  function current() {
    return document.documentElement.dataset.mode === "advanced" ? "advanced" : "simple";
  }

  function apply(mode) {
    document.documentElement.dataset.mode = mode;
    document.querySelectorAll("[data-mode-value]").forEach(function (button) {
      button.setAttribute("aria-pressed", button.dataset.modeValue === mode ? "true" : "false");
    });
    document.querySelectorAll("input[name=mode]").forEach(function (input) {
      input.value = mode;
    });
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-mode-value]");
    if (!button) return;
    var mode = button.dataset.modeValue;
    try {
      localStorage.setItem("prasibali-mode", mode);
    } catch (e) {}
    apply(mode);
  });

  document.addEventListener("DOMContentLoaded", function () { apply(current()); });
  document.addEventListener("htmx:afterSettle", function () { apply(current()); });
})();
