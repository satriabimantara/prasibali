// Mode toggle (DESIGN.md "Pengalih mode"): Simple by default, Advanced = Mode Peneliti.
// Stores the choice in localStorage, sets <html data-mode>, and copies it into every form's hidden `mode` field
// so the server knows whether to use the research choices or the defaults.
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

  document.addEventListener("DOMContentLoaded", function () {
    apply(current());
    document.querySelectorAll("[data-mode-value]").forEach(function (button) {
      button.addEventListener("click", function () {
        var mode = button.dataset.modeValue;
        try {
          localStorage.setItem("prasibali-mode", mode);
        } catch (e) {}
        apply(mode);
      });
    });
  });
})();
