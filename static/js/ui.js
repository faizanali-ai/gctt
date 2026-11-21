(function () {
  "use strict";

  var $ = function (selector, root) {
    return (root || document).querySelector(selector);
  };
  var $$ = function (selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  };
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* --------------------------------------------------------------- theme */
  var THEME_KEY = "gctt-theme";
  var themeQuery = window.matchMedia("(prefers-color-scheme: dark)");

  function effectiveTheme() {
    var explicit = document.documentElement.getAttribute("data-theme");
    if (explicit === "light" || explicit === "dark") return explicit;
    return themeQuery.matches ? "dark" : "light";
  }

  function paintThemeButtons(theme) {
    $$("[data-theme-toggle]").forEach(function (button) {
      button.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
      button.setAttribute(
        "aria-label",
        theme === "dark" ? "Switch to light theme" : "Switch to dark theme"
      );
      var use = button.querySelector("use");
      if (!use) return;
      var href = use.getAttribute("href") || "";
      use.setAttribute("href", href.replace(/#(sun|moon)$/, theme === "dark" ? "#sun" : "#moon"));
    });
  }

  function applyTheme(theme, persist) {
    document.documentElement.setAttribute("data-theme", theme);
    if (persist) {
      try {
        window.localStorage.setItem(THEME_KEY, theme);
      } catch (error) {
        /* Storage disabled: the choice still applies for this page. */
      }
    }
    paintThemeButtons(theme);
  }

  document.addEventListener("click", function (event) {
    var toggle = event.target.closest("[data-theme-toggle]");
    if (!toggle) return;
    applyTheme(effectiveTheme() === "dark" ? "light" : "dark", true);
  });

  paintThemeButtons(effectiveTheme());
  if (themeQuery.addEventListener) {
    themeQuery.addEventListener("change", function () {
      if (!document.documentElement.hasAttribute("data-theme")) {
        paintThemeButtons(effectiveTheme());
      }
    });
  }


  /* ------------------------------------------------------------ dialogs */
  function lockScroll() {
    document.body.style.overflow = document.querySelector("dialog[open]") ? "hidden" : "";
  }

  function openDialog(dialog, opener) {
    if (!dialog) return;
    dialog._opener = opener || document.activeElement;
    if (typeof dialog.showModal === "function") {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
    lockScroll();
  }

  function closeDialog(dialog) {
    if (!dialog) return;
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
    lockScroll();
  }

  document.addEventListener("click", function (event) {
    var opener = event.target.closest("[data-dialog-open]");
    if (opener) {
      openDialog(document.getElementById(opener.getAttribute("data-dialog-open")), opener);
      return;
    }
    var closer = event.target.closest("[data-dialog-close]");
    if (closer) {
      closeDialog(closer.closest("dialog"));
    }
  });

  $$("dialog").forEach(function (dialog) {
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) closeDialog(dialog);
    });
    dialog.addEventListener("close", lockScroll);
  });

  /* --------------------------------------------------------- record drawer */
  document.addEventListener("click", function (event) {
    var trigger = event.target.closest("[data-drawer-template]");
    if (!trigger) return;
    var template = document.getElementById(trigger.getAttribute("data-drawer-template"));
    var drawer = document.getElementById("record-drawer");
    var body = document.getElementById("record-drawer-body");
    if (!template || !drawer || !body) return;
    body.replaceChildren(template.content.cloneNode(true));
    var title = trigger.getAttribute("data-drawer-title");
    var heading = drawer.querySelector("h2");
    if (title && heading) heading.textContent = title;
    openDialog(drawer, trigger);
  });

  /* --------------------------------------------------------------- toasts */
  function toast(message, tone) {
    var stack =
      document.querySelector(".toast-stack") ||
      document.getElementById("toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.id = "toast-stack";
      stack.className = "toast-stack";
      stack.setAttribute("aria-live", "polite");
      document.body.append(stack);
    }
    var item = document.createElement("div");
    item.className = "toast";
    if (tone === "danger") item.style.borderLeftColor = "var(--danger)";
    var text = document.createElement("p");
    text.className = "flex-1";
    text.textContent = message;
    var dismiss = document.createElement("button");
    dismiss.type = "button";
    dismiss.className = "btn btn-ghost btn-sm";
    dismiss.setAttribute("aria-label", "Dismiss notification");
    dismiss.textContent = "\u00d7";
    dismiss.addEventListener("click", function () {
      item.remove();
    });
    item.append(text, dismiss);
    stack.append(item);
    if (tone !== "danger") {
      window.setTimeout(function () {
        item.remove();
      }, 6000);
    }
  }
  window.gcttToast = toast;

  document.addEventListener("click", function (event) {
    var dismiss = event.target.closest("[data-toast-dismiss]");
    if (!dismiss) return;
    var item = dismiss.closest(".toast");
    if (item) item.remove();
  });

  $$("[data-autodismiss]").forEach(function (item) {
    var delay = parseInt(item.getAttribute("data-autodismiss"), 10) || 6000;
    window.setTimeout(function () {
      item.remove();
    }, delay);
  });

  /* ----------------------------------------------------- password reveal */
  $$('input[type="password"]').forEach(function (input) {
    if (input.closest("[data-no-reveal]") || input.dataset.revealReady) return;
    input.dataset.revealReady = "true";
    var wrap = document.createElement("div");
    wrap.className = "relative";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    input.classList.add("pr-16");
    var button = document.createElement("button");
    button.type = "button";
    button.className =
      "absolute right-2 top-1/2 -translate-y-1/2 rounded px-2 py-1 text-2xs font-semibold text-muted hover:text-ink";
    button.textContent = "Show";
    button.setAttribute("aria-label", "Show password");
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", function () {
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      button.textContent = show ? "Hide" : "Show";
      button.setAttribute("aria-pressed", show ? "true" : "false");
      button.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
    wrap.appendChild(button);
  });

  /* --------------------------------------------------- account type sync */
  var accountRadios = $$('[name="account_type"]');
  if (accountRadios.length) {
    var accountSubmit = $("[data-account-submit]");
    var googleSignup = $("[data-google-signup]");
    var syncAccount = function () {
      var picked = $('[name="account_type"]:checked');
      if (!picked) return;
      var label = picked.value === "student" ? "student" : "candidate";
      if (accountSubmit) accountSubmit.textContent = "Create " + label + " account";
      if (googleSignup && googleSignup.getAttribute("data-base-href")) {
        googleSignup.href =
          googleSignup.getAttribute("data-base-href") +
          "?account_type=" +
          encodeURIComponent(picked.value);
      }
    };
    accountRadios.forEach(function (radio) {
      radio.addEventListener("change", syncAccount);
    });
    syncAccount();
  }

  /* ------------------------------------------------------------ clipboard */
  function copyText(value) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(value);
    }
    var area = document.createElement("textarea");
    area.value = value;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.append(area);
    area.select();
    var ok = document.execCommand("copy");
    area.remove();
    return ok ? Promise.resolve() : Promise.reject(new Error("copy failed"));
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-copy]");
    if (!button) return;
    copyText(button.getAttribute("data-copy") || "").then(
      function () {
        toast("Copied to clipboard");
      },
      function () {
        toast("Could not copy. Select the text manually.", "danger");
      }
    );
  });

  /* ----------------------------------------------------- password reveal */
  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-password-toggle]");
    if (!button) return;
    var input = document.getElementById(button.getAttribute("data-password-toggle"));
    if (!input) return;
    var show = input.type === "password";
    input.type = show ? "text" : "password";
    button.setAttribute("aria-pressed", show ? "true" : "false");
    button.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });

  /* --------------------------------------------------------------- reveals */
  var reveals = $$(".reveal");
  var heroItems = $$(".hero-enter");
  if ((reveals.length || heroItems.length) && !reduceMotion) {
    document.documentElement.classList.add("js-ready");
  }
  if (heroItems.length) {
    if (reduceMotion || !window.requestAnimationFrame) {
      heroItems.forEach(function (item) {
        item.classList.add("is-in");
      });
    } else {
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(function () {
          heroItems.forEach(function (item) {
            item.classList.add("is-in");
          });
        });
      });
    }
  }
  if (reveals.length) {
    if (reduceMotion || !("IntersectionObserver" in window)) {
      reveals.forEach(function (item) {
        item.classList.add("in-view");
      });
    } else {
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              entry.target.classList.add("in-view");
              observer.unobserve(entry.target);
            }
          });
        },
        { rootMargin: "0px 0px -40px 0px", threshold: 0.15 }
      );
      reveals.forEach(function (item) {
        observer.observe(item);
      });
    }
  }

  /* -------------------------------------------------- nav indicator slider */
  var nav = document.getElementById("primary-nav");
  var indicator = document.getElementById("nav-indicator");
  if (nav && indicator) {
    var links = $$(".nav-link", nav);
    var activeLink = function () {
      return $('[aria-current="page"]', nav);
    };
    var moveTo = function (link) {
      if (!link || !nav.offsetWidth) {
        indicator.style.opacity = "0";
        return;
      }
      var navBox = nav.getBoundingClientRect();
      var linkBox = link.getBoundingClientRect();
      indicator.style.width = linkBox.width + "px";
      indicator.style.transform = "translateX(" + (linkBox.left - navBox.left) + "px)";
      indicator.style.opacity = "1";
    };
    var reset = function () {
      moveTo(activeLink());
    };
    var place = function () {
      indicator.style.transition = "none";
      reset();
      window.requestAnimationFrame(function () {
        indicator.style.transition = "";
      });
    };
    links.forEach(function (link) {
      link.addEventListener("mouseenter", function () {
        moveTo(link);
      });
      link.addEventListener("focus", function () {
        moveTo(link);
      });
    });
    nav.addEventListener("mouseleave", reset);
    window.addEventListener("resize", reset, { passive: true });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(place);
    place();
  }

  /* --------------------------------------------------------------- confirm */
  var confirmDialog = document.getElementById("confirm-dialog");
  var pendingForm = null;

  document.addEventListener("submit", function (event) {
    var form = event.target.closest("form[data-confirm]");
    if (!form || form.dataset.confirmed === "true") return;
    event.preventDefault();
    pendingForm = form;
    var message = document.getElementById("confirm-message");
    var accept = document.getElementById("confirm-accept");
    if (message) message.textContent = form.getAttribute("data-confirm");
    if (accept) accept.textContent = form.getAttribute("data-confirm-action") || "Confirm";
    openDialog(confirmDialog, event.submitter || form.querySelector('[type="submit"]'));
  });

  if (confirmDialog) {
    confirmDialog.addEventListener("close", function () {
      pendingForm = null;
    });
    var acceptButton = document.getElementById("confirm-accept");
    if (acceptButton) {
      acceptButton.addEventListener("click", function () {
        var form = pendingForm;
        if (!form) return;
        pendingForm = null;
        form.dataset.confirmed = "true";
        closeDialog(confirmDialog);
        form.requestSubmit();
        delete form.dataset.confirmed;
      });
    }
  }

  /* --------------------------------------------------------------- stepper */
  $$("[data-stepper]").forEach(function (root) {
    var steps = $$("[data-step]", root);
    if (steps.length < 2) return;
    var labels = $$("[data-step-label]", root);
    var bars = $$("[data-progress]", root);
    var counter = $("[data-step-counter]", root);
    var index = 0;
    var firstRender = true;

    function show(next) {
      index = Math.max(0, Math.min(next, steps.length - 1));
      steps.forEach(function (step, position) {
        step.hidden = position !== index;
      });
      labels.forEach(function (label, position) {
        if (position === index) label.setAttribute("aria-current", "step");
        else label.removeAttribute("aria-current");
      });
      bars.forEach(function (bar, position) {
        bar.classList.toggle("bg-accent", position <= index);
        bar.classList.toggle("bg-line", position > index);
      });
      if (counter) counter.textContent = "Step " + (index + 1) + " of " + steps.length;
      if (index === steps.length - 1) {
        $$("[data-review]", root).forEach(function (out) {
          var source = root.querySelector('[name="' + out.getAttribute("data-review") + '"]');
          if (source && source.type === "file") {
            out.textContent = source.files && source.files[0] ? source.files[0].name : "\u2014";
            return;
          }
          out.textContent = source && source.value ? source.value : "\u2014";
        });
      }
      if (!firstRender) {
        var heading = steps[index].querySelector("h2, h3");
        if (heading) {
          heading.setAttribute("tabindex", "-1");
          heading.focus({ preventScroll: true });
        }
      }
      firstRender = false;
    }

    function validStep() {
      var fields = $$("input, select, textarea", steps[index]).filter(function (field) {
        return field.willValidate && field.required;
      });
      for (var i = 0; i < fields.length; i += 1) {
        if (!fields[i].checkValidity()) {
          fields[i].reportValidity();
          return false;
        }
      }
      return true;
    }

    root.addEventListener("click", function (event) {
      if (event.target.closest("[data-step-next]") && validStep()) show(index + 1);
      if (event.target.closest("[data-step-prev]")) show(index - 1);
    });

    var errorField = root.querySelector(".field-error");
    var startStep = 0;
    if (errorField) {
      var errorStep = errorField.closest("[data-step]");
      var errorIndex = steps.indexOf(errorStep);
      if (errorIndex >= 0) startStep = errorIndex;
    }
    show(startStep);
    if (errorField) {
      var firstError = errorField.querySelector("input, select, textarea");
      if (firstError) firstError.focus({ preventScroll: true });
    }
  });

  /* --------------------------------------------------------- career advisor */
  var advisor = document.querySelector("[data-advisor-form]");
  if (advisor) {
    advisor.addEventListener("submit", function (event) {
      event.preventDefault();
      var button = $("[data-advisor-submit]", advisor);
      var placeholder = $("[data-advisor-placeholder]");
      var output = $("[data-advisor-output]");
      var live = advisor.parentElement.querySelector("[aria-live]");
      var token = advisor.querySelector('[name="csrfmiddlewaretoken"]');
      var error = $("[data-advisor-error]", advisor.parentElement);
      if (error) error.remove();

      var data = {};
      new FormData(advisor).forEach(function (value, key) {
        if (key !== "csrfmiddlewaretoken") data[key] = value;
      });

      if (button) {
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
      }
      if (live) live.setAttribute("aria-busy", "true");

      fetch(advisor.getAttribute("action"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": token ? token.value : ""
        },
        body: JSON.stringify(data)
      })
        .then(function (response) {
          if (!response.ok) throw new Error("advisor request failed");
          return response.json();
        })
        .then(function (payload) {
          if (!payload.success || !payload.data) throw new Error("advisor returned no data");
          var result = payload.data;
          var set = function (name, value) {
            var target = $('[data-advisor-field="' + name + '"]', advisor.parentElement);
            if (target) target.textContent = value || "";
          };
          set("track", result.track);
          set("timeline", result.timeline);
          set("comp", result.market_comp);
          set("summary", result.summary);
          var fit = $('[data-advisor-field="fit"]', advisor.parentElement);
          if (fit) {
            fit.textContent = result.fit_score ? result.fit_score + "% indicative fit" : "";
            fit.hidden = !result.fit_score;
          }
          var milestones = $('[data-advisor-field="milestones"]', advisor.parentElement);
          if (milestones) {
            milestones.replaceChildren();
            (result.milestones || []).forEach(function (item) {
              var li = document.createElement("li");
              li.textContent = item;
              milestones.append(li);
            });
          }
          if (placeholder) placeholder.hidden = true;
          if (output) output.hidden = false;
        })
        .catch(function () {
          var message = document.createElement("p");
          message.className = "alert alert-danger mt-4";
          message.setAttribute("data-advisor-error", "");
          message.setAttribute("role", "alert");
          message.textContent = "The advisor is unavailable right now. Try again, or request a cohort briefing.";
          if (output) output.before(message);
          else if (placeholder) placeholder.before(message);
        })
        .finally(function () {
          if (button) {
            button.disabled = false;
            button.removeAttribute("aria-busy");
          }
          if (live) live.removeAttribute("aria-busy");
        });
    });
  }

  /* ------------------------------------------------------ error summary */
  var errorSummary = $("[data-form-errors]");
  if (errorSummary) errorSummary.focus();

  /* ------------------------------------------- field hint/error wiring */
  $$(".field").forEach(function (field) {
    var control = field.querySelector("input, select, textarea");
    if (!control) return;
    var describedIds = (control.getAttribute("aria-describedby") || "")
      .split(/\s+/)
      .filter(Boolean);
    var hint = field.querySelector(".hint");
    var list = field.querySelector(".errorlist");
    if (hint) {
      if (!hint.id) hint.id = (control.id || "field") + "-hint";
      describedIds.push(hint.id);
    }
    if (list) {
      if (!list.id) list.id = (control.id || "field") + "-error";
      describedIds.push(list.id);
      control.setAttribute("aria-invalid", "true");
    }
    if (describedIds.length) {
      control.setAttribute(
        "aria-describedby",
        Array.from(new Set(describedIds)).join(" ")
      );
    }
  });

  /* --------------------------------------------------------------- print */
  document.addEventListener("click", function (event) {
    if (event.target.closest("[data-print]")) window.print();
  });

  /* ------------------------------------------------------- role subgroup */
  var roleSelect = $("[data-role-select]");
  if (roleSelect) {
    var subgroupField = $("[data-subgroup-field]");
    var syncRole = function () {
      if (subgroupField) subgroupField.hidden = roleSelect.value !== "staff";
    };
    roleSelect.addEventListener("change", syncRole);
    syncRole();
  }

  /* ------------------------------------------------- submit busy state */
  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (form.hasAttribute("data-confirm") || form.hasAttribute("data-advisor-form")) return;
    var button = form.querySelector('[type="submit"]');
    if (!button) return;
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
  });
})();
