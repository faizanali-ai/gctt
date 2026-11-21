(function () {
  "use strict";

  try {
    var choice = window.localStorage.getItem("gctt-theme");
    if (choice === "light" || choice === "dark") {
      document.documentElement.setAttribute("data-theme", choice);
    }
  } catch (error) {
    /* Private mode or storage disabled: fall back to the OS preference. */
  }
})();
