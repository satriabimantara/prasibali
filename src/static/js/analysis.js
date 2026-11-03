// Analysis workspace: busy state while analysing (HTMX or plain POST), focus on the result, character selection
// with sentence context (client side, no request), and roving tabindex over the highlighted names.
// Event delegation on document: the workspace is replaced by HTMX after every analysis.
(function () {
  function setBusy(form, busy) {
    var button = form.querySelector("button[type=submit]");
    var label = button && button.querySelector("[data-label]");
    if (label) {
      if (!label.dataset.labelIdle) label.dataset.labelIdle = label.textContent;
      label.textContent = busy ? button.dataset.labelBusy || label.textContent : label.dataset.labelIdle;
    }
    if (busy) form.setAttribute("aria-busy", "true");
    else form.removeAttribute("aria-busy");
  }

  // ------------------------------------------------------------------ character selection
  function entities(root) {
    return Array.prototype.slice.call(root.querySelectorAll(".entity[data-char]"));
  }

  function select(root, key, focusPanel) {
    root.querySelectorAll("[data-char]").forEach(function (el) {
      el.setAttribute("aria-pressed", el.dataset.char === key ? "true" : "false");
    });
    var shown = false;
    root.querySelectorAll("[data-context-for]").forEach(function (el) {
      var match = el.dataset.contextFor === key;
      el.hidden = !match;
      shown = shown || match;
    });
    var empty = root.querySelector("[data-context-empty]");
    if (empty) empty.hidden = shown;
    // The roving tab stop follows the selection.
    var list = entities(root);
    var current = list.find(function (el) { return el.dataset.char === key; });
    if (current) list.forEach(function (el) { el.tabIndex = el === current ? 0 : -1; });
    var panel = root.querySelector("[data-context-panel]");
    if (panel && focusPanel) panel.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  function initResult(root) {
    var list = entities(root);
    if (list.length) list[0].tabIndex = 0;
  }

  document.addEventListener("click", function (event) {
    var trigger = event.target.closest("[data-char]");
    if (trigger) {
      var root = trigger.closest("[data-result]");
      if (root) select(root, trigger.dataset.char, !trigger.classList.contains("entity") || window.innerWidth < 1024);
      return;
    }
    var retry = event.target.closest("[data-retry]");
    if (retry) {
      var form = document.querySelector("[data-analysis-form]");
      if (form) {
        event.preventDefault();
        if (form.requestSubmit) form.requestSubmit();
        else form.submit();
      }
      return;
    }
    // Reset: the link reloads an empty workspace (no text, no result, default models); also go back to the
    // default display mode before leaving the page.
    if (event.target.closest("[data-reset]")) {
      try {
        localStorage.setItem("prasibali-mode", "simple");
      } catch (e) {}
    }
  });

  document.addEventListener("keydown", function (event) {
    var current = event.target.closest && event.target.closest(".entity[data-char]");
    if (!current || (event.key !== "ArrowRight" && event.key !== "ArrowLeft" && event.key !== "Home" && event.key !== "End")) return;
    var root = current.closest("[data-result]");
    var list = entities(root);
    var index = list.indexOf(current);
    var next = event.key === "Home" ? 0 : event.key === "End" ? list.length - 1
      : (index + (event.key === "ArrowRight" ? 1 : -1) + list.length) % list.length;
    event.preventDefault();
    list.forEach(function (el, i) { el.tabIndex = i === next ? 0 : -1; });
    list[next].focus();
  });

  // ------------------------------------------------------------------ form submission
  document.addEventListener("submit", function (event) {
    var form = event.target.closest("[data-analysis-form]");
    if (!form) return;
    setBusy(form, true);
    if (!window.htmx) {
      // Plain POST: disable after the submit event so the browser still sends the form.
      var button = form.querySelector("button[type=submit]");
      if (button) setTimeout(function () { button.disabled = true; }, 0);
    }
  });

  document.addEventListener("htmx:afterRequest", function (event) {
    var form = event.target.closest && event.target.closest("[data-analysis-form]");
    if (form && document.body.contains(form)) setBusy(form, false);
  });

  // Network or server error: the workspace is not swapped, so say what happened next to the button.
  document.addEventListener("htmx:sendError", showRequestError);
  document.addEventListener("htmx:responseError", showRequestError);

  function showRequestError(event) {
    var form = event.target.closest && event.target.closest("[data-analysis-form]");
    if (!form) return;
    var box = form.querySelector("[data-request-error]");
    if (!box) {
      box = document.createElement("p");
      box.className = "alert alert--danger";
      box.setAttribute("role", "alert");
      box.dataset.requestError = "";
      form.appendChild(box);
    }
    box.textContent = form.dataset.requestErrorText || "The analysis could not be completed. Your text has not been lost.";
  }

  document.addEventListener("htmx:afterSettle", function (event) {
    var workspace = event.target.id === "workspace" ? event.target : null;
    if (!workspace) return;
    var result = workspace.querySelector("[data-result]");
    if (result) initResult(result);
    var focusTarget = workspace.querySelector("#result-title") || workspace.querySelector("[role=alert]") ||
      workspace.querySelector("[aria-invalid=true]");
    if (focusTarget) {
      if (!focusTarget.hasAttribute("tabindex") && focusTarget.getAttribute("role") === "alert") focusTarget.tabIndex = -1;
      focusTarget.focus();
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-result]").forEach(initResult);
    var title = document.getElementById("result-title");
    if (title && document.querySelector("[data-analysis-form]")) title.focus();
  });
})();
