// Analysis form: busy state while the (synchronous) analysis runs, and focus on the result when it arrives.
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var form = document.querySelector("[data-analysis-form]");
    if (form) {
      form.addEventListener("submit", function () {
        var button = form.querySelector("button[type=submit]");
        if (!button) return;
        var label = button.querySelector("[data-label]");
        if (label && button.dataset.labelBusy) label.textContent = button.dataset.labelBusy;
        form.setAttribute("aria-busy", "true");
        // Disable after the submit event so the browser still sends the form.
        setTimeout(function () { button.disabled = true; }, 0);
      });
      var retry = document.querySelector("[data-retry]");
      if (retry) {
        retry.addEventListener("click", function (event) {
          event.preventDefault();
          form.requestSubmit ? form.requestSubmit() : form.submit();
        });
      }
    }
    var title = document.getElementById("result-title");
    if (title) title.focus();
  });
})();
