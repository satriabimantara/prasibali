// Site navigation disclosures (DESIGN.md "Navigasi situs"): the features dropdown, the account menu and the mobile
// menu. WAI-ARIA disclosure pattern: a button with aria-expanded/aria-controls shows or hides its panel.
// Escape closes and returns focus to the button, a click or focus outside closes, and the arrow keys move between
// the links inside an open panel. Only one panel is open at a time.
(function () {
  var openButton = null;

  function panelOf(button) {
    return document.getElementById(button.getAttribute("aria-controls"));
  }

  function items(panel) {
    return Array.prototype.filter.call(
      panel.querySelectorAll("a[href], button:not([disabled]), input:not([disabled])"),
      function (el) { return el.offsetParent !== null; }
    );
  }

  function close(button, returnFocus) {
    button.setAttribute("aria-expanded", "false");
    panelOf(button).hidden = true;
    if (openButton === button) openButton = null;
    if (returnFocus) button.focus();
  }

  function open(button) {
    if (openButton && openButton !== button) close(openButton, false);
    button.setAttribute("aria-expanded", "true");
    panelOf(button).hidden = false;
    openButton = button;
  }

  function contains(button, target) {
    return button === target || button.contains(target) || panelOf(button).contains(target);
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-disclosure]");
    if (button) {
      if (button.getAttribute("aria-expanded") === "true") close(button, false);
      else open(button);
      return;
    }
    if (openButton && !contains(openButton, event.target)) close(openButton, false);
  });

  document.addEventListener("focusin", function (event) {
    if (openButton && !contains(openButton, event.target)) close(openButton, false);
  });

  document.addEventListener("keydown", function (event) {
    var button = event.target.closest && event.target.closest("[data-disclosure]");
    if (button && !openButton && event.key === "ArrowDown") {
      // Arrow down on a closed toggle opens it and moves to the first link.
      event.preventDefault();
      open(button);
      var first = items(panelOf(button))[0];
      if (first) first.focus();
      return;
    }
    if (!openButton) return;
    if (event.key === "Escape") {
      event.preventDefault();
      close(openButton, true);
      return;
    }
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp" && event.key !== "Home" && event.key !== "End") return;
    var panel = panelOf(openButton);
    if (event.target !== openButton && !panel.contains(event.target)) return;
    var list = items(panel);
    if (!list.length) return;
    event.preventDefault();
    var index = list.indexOf(document.activeElement);
    var next;
    if (event.key === "Home") next = 0;
    else if (event.key === "End") next = list.length - 1;
    else if (event.key === "ArrowDown") next = index < 0 ? 0 : (index + 1) % list.length;
    else next = index <= 0 ? list.length - 1 : index - 1;
    list[next].focus();
  });
})();
