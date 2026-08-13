"""Bounded presentation bridges for research accessibility semantics."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

import streamlit


SEMANTIC_MAIN_BRIDGE_HTML = """
<script>
(() => {
  try {
    const host = document;
    const observerKey = "__stockResearchMainObserver";
    const targetKey = "__stockResearchMainTarget";
    const ownershipKey = "__stockResearchMainOwnership";
    const markerName = "data-research-main-bridge-owned";
    const bridgeAttributes = {
      "role": "main",
      "id": "research-main",
      "aria-label": "Stock research workspace",
      "tabindex": "-1"
    };
    if (window[observerKey]) {
      window[observerKey].disconnect();
    }
    let activeObserver = null;
    const ownedMutations = [];

    function rememberOwnedMutation(target, name) {
      if (
        activeObserver &&
        Object.prototype.hasOwnProperty.call(bridgeAttributes, name)
      ) {
        ownedMutations.push({target: target, name: name});
      }
    }

    function consumeOwnedMutation(mutation) {
      if (mutation.type !== "attributes") return false;
      const index = ownedMutations.findIndex(
        (owned) =>
          owned.target === mutation.target &&
          owned.name === mutation.attributeName
      );
      if (index === -1) return false;
      ownedMutations.splice(index, 1);
      return true;
    }

    function rememberFrameworkMutation(mutation) {
      const target = window[targetKey];
      if (
        mutation.type !== "attributes" ||
        mutation.target !== target ||
        !Object.prototype.hasOwnProperty.call(
          bridgeAttributes,
          mutation.attributeName
        )
      ) {
        return;
      }
      const ownership = target[ownershipKey];
      if (ownership) {
        ownership.attributes[mutation.attributeName] = attributeSnapshot(
          target,
          mutation.attributeName
        );
      }
    }

    function writeAttribute(target, name, value) {
      if (target.getAttribute(name) !== value) {
        rememberOwnedMutation(target, name);
        target.setAttribute(name, value);
      }
    }

    function removeAttribute(target, name) {
      if (target.hasAttribute(name)) {
        rememberOwnedMutation(target, name);
        target.removeAttribute(name);
      }
    }

    function setStatus(status) {
      writeAttribute(
        host.documentElement,
        "data-research-main-bridge-status",
        status
      );
    }

    function attributeSnapshot(target, name) {
      return {
        present: target.hasAttribute(name),
        prior: target.getAttribute(name)
      };
    }

    function snapshotTarget(target) {
      if (!target[ownershipKey]) {
        target[ownershipKey] = {
          attributes: {
            "role": attributeSnapshot(target, "role"),
            "id": attributeSnapshot(target, "id"),
            "aria-label": attributeSnapshot(target, "aria-label"),
            "tabindex": attributeSnapshot(target, "tabindex")
          },
          marker: attributeSnapshot(target, markerName)
        };
      }
      return target[ownershipKey];
    }

    function restoreAttribute(target, name, original) {
      if (target.getAttribute(name) !== bridgeAttributes[name]) return;
      if (original.present) {
        writeAttribute(target, name, original.prior);
      } else {
        removeAttribute(target, name);
      }
    }

    function cleanupTarget(target) {
      const ownership = target[ownershipKey];
      if (!ownership) return;
      for (const name of Object.keys(bridgeAttributes)) {
        restoreAttribute(target, name, ownership.attributes[name]);
      }
      if (target.getAttribute(markerName) === "true") {
        if (ownership.marker.present) {
          writeAttribute(target, markerName, ownership.marker.prior);
        } else {
          target.removeAttribute(markerName);
        }
      }
      delete target[ownershipKey];
    }

    function valueAfterCleanup(target, name) {
      const ownership = target[ownershipKey];
      const current = target.getAttribute(name);
      if (!ownership || current !== bridgeAttributes[name]) return current;
      const original = ownership.attributes[name];
      return original.present ? original.prior : null;
    }

    function unsafeConnectedCleanup(target) {
      if (!target.isConnected) return false;
      const remainsMain =
        target.tagName.toLowerCase() === "main" ||
        valueAfterCleanup(target, "role") === "main";
      const retainsResearchId =
        valueAfterCleanup(target, "id") === "research-main";
      return remainsMain || retainsResearchId;
    }

    function hasConnectedConflict(target) {
      const otherMain = Array.from(
        host.querySelectorAll('main, [role="main"]')
      ).some((node) => node !== target);
      const otherResearchId = Array.from(
        host.querySelectorAll('[id="research-main"]')
      ).some((node) => node !== target);
      return otherMain || otherResearchId;
    }

    function applyMainLandmark() {
      const nodes = host.querySelectorAll('[data-testid="stMain"]');
      const previous = window[targetKey];
      if (nodes.length !== 1) {
        if (previous) cleanupTarget(previous);
        window[targetKey] = null;
        setStatus(nodes.length === 0 ? "missing" : "ambiguous");
        return;
      }

      const target = nodes[0];
      if (
        previous &&
        previous !== target &&
        unsafeConnectedCleanup(previous)
      ) {
        setStatus("ambiguous");
        return;
      }
      if (previous && previous !== target) {
        cleanupTarget(previous);
        window[targetKey] = null;
      }

      if (hasConnectedConflict(target)) {
        if (window[targetKey] === target) {
          cleanupTarget(target);
          window[targetKey] = null;
        }
        setStatus("ambiguous");
        return;
      }

      snapshotTarget(target);
      writeAttribute(target, markerName, "true");
      if (target.getAttribute("role") !== "main") {
        rememberOwnedMutation(target, "role");
        target.setAttribute("role", "main");
      }
      if (target.getAttribute("id") !== "research-main") {
        rememberOwnedMutation(target, "id");
        target.setAttribute("id", "research-main");
      }
      if (
        target.getAttribute("aria-label") !== "Stock research workspace"
      ) {
        rememberOwnedMutation(target, "aria-label");
        target.setAttribute("aria-label", "Stock research workspace");
      }
      if (target.getAttribute("tabindex") !== "-1") {
        rememberOwnedMutation(target, "tabindex");
        target.setAttribute("tabindex", "-1");
      }
      window[targetKey] = target;
      setStatus("applied");
    }

    function handleMutations(mutations) {
      let shouldApply = false;
      for (const mutation of mutations) {
        if (consumeOwnedMutation(mutation)) continue;
        rememberFrameworkMutation(mutation);
        if (
          mutation.type === "childList" ||
          (
            mutation.type === "attributes" &&
            (
              mutation.attributeName === "data-testid" ||
              mutation.attributeName === "role" ||
              mutation.attributeName === "id" ||
              mutation.attributeName === "tabindex" ||
              (
                mutation.attributeName === "aria-label" &&
                mutation.target === window[targetKey]
              )
            )
          )
        ) {
          shouldApply = true;
        }
      }
      if (shouldApply) applyMainLandmark();
    }

    applyMainLandmark();
    activeObserver = new MutationObserver(handleMutations);
    window[observerKey] = activeObserver;
    activeObserver.observe(
      host.body,
      {
        attributes: true,
        attributeFilter: [
          "data-testid", "role", "id", "aria-label", "tabindex"
        ],
        childList: true,
        subtree: true
      }
    );
  } catch (error) {
    return;
  }
})();
</script>
"""


def _same_document_html_renderer(
    renderer: Callable[..., Any] | None,
) -> Callable[..., Any]:
    resolved = renderer if renderer is not None else getattr(streamlit, "html", None)
    if not callable(resolved):
        raise RuntimeError(
            "Streamlit >=1.52,<2 with st.html JavaScript support is required."
        )
    return resolved


def render_semantic_main_bridge(
    *, html_renderer: Callable[..., Any] | None = None
) -> None:
    """Render the fixed, local semantic-main bridge without research data."""

    renderer = _same_document_html_renderer(html_renderer)
    renderer(SEMANTIC_MAIN_BRIDGE_HTML, unsafe_allow_javascript=True)


@dataclass(frozen=True)
class AuthoringFieldError:
    """One deterministic required-field error safe to expose to the browser."""

    field_name: str
    field_label: str
    message: str
    error_id: str


def _normalized_id_part(part: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(part).strip().lower()).strip("-")


def authoring_field_error(
    reason: str,
    *,
    profile_key: str,
    ticker: str,
    kind: str,
) -> AuthoringFieldError | None:
    """Map only an exact required-field rejection from the active field contract."""

    match = re.fullmatch(r"([a-z][a-z0-9_]*) is required", str(reason))
    if match is None:
        return None
    field_name = match.group(1)

    from src.research_record_authoring_ui import authoring_field_contract

    try:
        contract = authoring_field_contract(kind)
    except ValueError:
        return None
    if field_name not in contract:
        return None
    field_label = field_name.replace("_", " ").title()
    error_id = "-".join(
        (
            "research-authoring",
            _normalized_id_part(profile_key),
            _normalized_id_part(ticker),
            _normalized_id_part(kind),
            _normalized_id_part(field_name),
            "error",
        )
    )
    return AuthoringFieldError(field_name, field_label, str(reason), error_id)


def render_authoring_error_binding(
    error: AuthoringFieldError | None,
    *,
    html_renderer: Callable[..., Any] | None = None,
) -> None:
    """Clear bridge-owned state, then optionally associate one current error."""

    config = json.dumps(
        {
            "fieldLabel": error.field_label if error is not None else None,
            "errorId": error.error_id if error is not None else None,
            "message": error.message if error is not None else None,
        },
        ensure_ascii=True,
    )
    document = f"""
<script>
(() => {{
  const config = {config};
  try {{
    const scriptElement = document.currentScript;
    if (!scriptElement) return;
    const htmlContainer = scriptElement.closest('[data-testid="stHtml"]');
    if (!htmlContainer) return;
    const composer = htmlContainer.closest('[data-testid="stExpander"]');
    if (!composer) return;

    for (const control of composer.querySelectorAll(
      "[data-research-authoring-describedby-owned], " +
      "[data-research-authoring-previous-invalid]"
    )) {{
      const ownedDescription = control.getAttribute(
        "data-research-authoring-describedby-owned"
      );
      if (ownedDescription) {{
        const describedBy = (control.getAttribute("aria-describedby") || "")
          .split(/\\s+/)
          .filter(Boolean);
        const remainingDescriptions = describedBy.filter(
          (token) => token !== ownedDescription
        );
        if (remainingDescriptions.length) {{
          control.setAttribute("aria-describedby", remainingDescriptions.join(" "));
        }} else {{
          control.removeAttribute("aria-describedby");
        }}
        control.removeAttribute("data-research-authoring-describedby-owned");
      }}

      const previousInvalid = control.getAttribute(
        "data-research-authoring-previous-invalid"
      );
      if (previousInvalid !== null) {{
        if (previousInvalid === "__absent__") {{
          control.removeAttribute("aria-invalid");
        }} else {{
          control.setAttribute("aria-invalid", previousInvalid);
        }}
        control.removeAttribute("data-research-authoring-previous-invalid");
      }}
    }}
    for (const errorText of composer.querySelectorAll(
      '[data-research-authoring-error-owned="true"]'
    )) {{
      errorText.remove();
    }}
    if (!config.errorId) return;

    const selector = 'input, textarea, select, [role="combobox"]';
    const candidates = [];
    const labels = Array.from(composer.querySelectorAll("label")).filter(
      (label) => label.textContent.trim() === config.fieldLabel
    );
    for (const label of labels) {{
      let control = label.control;
      const targetId = label.getAttribute("for");
      if (!control && targetId) {{
        control = Array.from(composer.querySelectorAll("[id]")).find(
          (element) => element.id === targetId
        );
      }}
      if (!control) control = label.querySelector(selector);
      if (control && control.matches(selector)) candidates.push(control);
    }}
    for (const control of composer.querySelectorAll(selector)) {{
      if (control.getAttribute("aria-label") === config.fieldLabel) {{
        candidates.push(control);
      }}
    }}
    const controls = Array.from(new Set(candidates));
    if (controls.length !== 1) return;

    const existingErrors = Array.from(composer.querySelectorAll("[id]")).filter(
      (element) => element.id === config.errorId
    );
    if (existingErrors.length !== 0) return;

    const control = controls[0];
    const errorText = document.createElement("p");
    errorText.id = config.errorId;
    errorText.className = "research-authoring-field-error";
    errorText.setAttribute("data-research-authoring-error-owned", "true");
    errorText.textContent = config.message;
    errorText.style.color = "var(--text-color)";
    errorText.style.margin = "0.25rem 0 0";

    const previousInvalid = control.getAttribute("aria-invalid");
    control.setAttribute(
      "data-research-authoring-previous-invalid",
      previousInvalid === null ? "__absent__" : previousInvalid
    );
    control.setAttribute("aria-invalid", "true");
    const describedBy = (control.getAttribute("aria-describedby") || "")
      .split(/\\s+/)
      .filter(Boolean);
    if (!describedBy.includes(config.errorId)) describedBy.push(config.errorId);
    control.setAttribute("aria-describedby", describedBy.join(" "));
    control.setAttribute(
      "data-research-authoring-describedby-owned",
      config.errorId
    );
    control.insertAdjacentElement("afterend", errorText);
    control.focus({{preventScroll: false}});
  }} catch (error) {{
    return;
  }}
}})();
</script>
"""
    renderer = _same_document_html_renderer(html_renderer)
    renderer(document, unsafe_allow_javascript=True)
