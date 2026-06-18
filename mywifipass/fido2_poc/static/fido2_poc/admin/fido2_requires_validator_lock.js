//  Copyright (c) 2025, Pablo Diz de la Cruz
//  All rights reserved.
//  Licensed under the BSD 3-Clause License. See LICENSE file in the project root for full license information.

(function () {
  function getRequiresValidatorCheckbox() {
    return document.getElementById("id_requires_validator");
  }

  function getFido2Checkboxes() {
    return Array.from(
      document.querySelectorAll('input[type="checkbox"][name$="-requires_fido2"]')
    );
  }

  function anyFido2Enabled() {
    return getFido2Checkboxes().some(function (cb) {
      return cb.checked;
    });
  }

  function ensureLockHint(container) {
    if (!container) return;
    if (container.querySelector(".fido2-lock-hint")) return;

    var hint = document.createElement("div");
    hint.className = "help fido2-lock-hint";
    hint.style.marginTop = "6px";
    hint.textContent = "Locked because FIDO2 validation is enabled for this network.";
    container.appendChild(hint);
  }

  function removeLockHint(container) {
    if (!container) return;
    var hint = container.querySelector(".fido2-lock-hint");
    if (hint) {
      hint.remove();
    }
  }

  function updateRequiresValidatorLock() {
    var requiresValidator = getRequiresValidatorCheckbox();
    if (!requiresValidator) return;

    var fido2Enabled = anyFido2Enabled();
    var fieldRow = requiresValidator.closest(".form-row") || requiresValidator.closest(".field-box");

    if (fido2Enabled) {
      requiresValidator.checked = true;
      requiresValidator.disabled = true;
      if (fieldRow) {
        fieldRow.style.opacity = "0.7";
      }
      ensureLockHint(fieldRow);
    } else {
      requiresValidator.disabled = false;
      if (fieldRow) {
        fieldRow.style.opacity = "";
      }
      removeLockHint(fieldRow);
    }
  }

  function bindListeners() {
    getFido2Checkboxes().forEach(function (checkbox) {
      checkbox.addEventListener("change", updateRequiresValidatorLock);
    });
  }

  function initialize() {
    bindListeners();
    updateRequiresValidatorLock();

    var body = document.body;
    if (!body) return;

    var observer = new MutationObserver(function () {
      bindListeners();
      updateRequiresValidatorLock();
    });

    observer.observe(body, {
      childList: true,
      subtree: true,
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
  } else {
    initialize();
  }
})();
