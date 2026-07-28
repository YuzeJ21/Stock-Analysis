import importlib
import inspect
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


BRIDGE_PATH = Path("src/accessibility_bridge.py")
BUNDLED_NODE = (
    Path.home()
    / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
)

SEMANTIC_MAIN_DOM_HARNESS = r"""
const fs = require("node:fs");
const vm = require("node:vm");

const request = JSON.parse(fs.readFileSync(0, "utf8"));
const observers = [];

function queueMutation(record) {
  for (const observer of observers) {
    if (observer.accepts(record)) observer.records.push(record);
  }
}

class Element {
  constructor(name, tagName, attributes = {}, inBody = true) {
    this.name = name;
    this.tagName = tagName.toUpperCase();
    this.isConnected = true;
    this.inBody = inBody;
    this.attributes = new Map(
      Object.entries(attributes).map(([key, value]) => [key, String(value)])
    );
  }

  getAttribute(name) {
    return this.attributes.has(name) ? this.attributes.get(name) : null;
  }

  hasAttribute(name) {
    return this.attributes.has(name);
  }

  setAttribute(name, value) {
    const normalized = String(value);
    if (this.getAttribute(name) === normalized) return;
    this.attributes.set(name, normalized);
    queueMutation({
      type: "attributes",
      target: this,
      attributeName: name,
    });
  }

  removeAttribute(name) {
    if (!this.attributes.has(name)) return;
    this.attributes.delete(name);
    queueMutation({
      type: "attributes",
      target: this,
      attributeName: name,
    });
  }
}

const elements = new Map();
const documentElement = new Element("document", "html", {}, false);
const body = new Element("body", "body");

function addElement(definition, announce = false) {
  const element = new Element(
    definition.name,
    definition.tag,
    definition.attributes || {}
  );
  elements.set(definition.name, element);
  if (announce) {
    queueMutation({type: "childList", target: body});
  }
  return element;
}

for (const definition of request.elements || []) addElement(definition);

function matchesSimpleSelector(element, selector) {
  const attributeMatch = selector.match(
    /^\[([a-zA-Z0-9_-]+)="([^"]*)"\]$/
  );
  if (attributeMatch) {
    return element.getAttribute(attributeMatch[1]) === attributeMatch[2];
  }
  return element.tagName.toLowerCase() === selector.toLowerCase();
}

const document = {
  body,
  documentElement,
  queryCount: 0,
  querySelectorAll(selector) {
    this.queryCount += 1;
    const selectors = selector.split(",").map((part) => part.trim());
    return Array.from(elements.values()).filter(
      (element) =>
        element.isConnected &&
        selectors.some((part) => matchesSimpleSelector(element, part))
    );
  },
};

class MutationObserver {
  constructor(callback) {
    this.callback = callback;
    this.disconnected = false;
    this.options = null;
    this.records = [];
    observers.push(this);
  }

  accepts(record) {
    if (this.disconnected || !this.options) return false;
    if (record.type === "childList") return this.options.childList;
    if (record.type !== "attributes" || !this.options.attributes) {
      return false;
    }
    if (!record.target.inBody || !record.target.isConnected) return false;
    const filter = this.options.attributeFilter;
    return !filter || filter.includes(record.attributeName);
  }

  disconnect() {
    this.disconnected = true;
    this.records = [];
  }

  observe(_target, options) {
    this.disconnected = false;
    this.options = options;
  }
}

function flushMutations() {
  let deliveries = 0;
  for (const observer of observers) {
    if (!observer.disconnected && observer.records.length) {
      const records = observer.records.splice(0);
      deliveries += 1;
      observer.callback(records, observer);
    }
  }
  return deliveries;
}

const parentWindow = {document};
const context = {
  MutationObserver,
  window: {parent: parentWindow},
};

function runBridge() {
  vm.runInNewContext(request.script, context);
}

function snapshot() {
  const connected = Array.from(elements.values()).filter(
    (element) => element.isConnected
  );
  const mains = connected.filter(
    (element) =>
      element.tagName.toLowerCase() === "main" ||
      element.getAttribute("role") === "main"
  );
  const researchMainIds = connected.filter(
    (element) => element.getAttribute("id") === "research-main"
  );
  return {
    status: documentElement.getAttribute(
      "data-research-main-bridge-status"
    ),
    elements: Object.fromEntries(
      Array.from(elements.entries()).map(([name, element]) => [
        name,
        {
          attributes: Object.fromEntries(element.attributes.entries()),
          connected: element.isConnected,
          tag: element.tagName.toLowerCase(),
        },
      ])
    ),
    mainCount: mains.length,
    researchMainIdCount: researchMainIds.length,
    observerCount: observers.length,
    observers: observers.map((observer) => ({
      disconnected: observer.disconnected,
      options: observer.options,
    })),
    queryCount: document.queryCount,
  };
}

const captures = [];
const flushes = [];
for (const operation of request.operations || []) {
  if (operation.op === "run") {
    runBridge();
  } else if (operation.op === "capture") {
    captures.push(snapshot());
  } else if (operation.op === "flush") {
    flushes.push(flushMutations());
  } else if (operation.op === "add") {
    addElement(operation.element, true);
  } else if (operation.op === "set-attribute") {
    elements.get(operation.target).setAttribute(
      operation.name,
      operation.value
    );
  } else if (operation.op === "remove-attribute") {
    elements.get(operation.target).removeAttribute(operation.name);
  } else if (operation.op === "set-connected") {
    const element = elements.get(operation.target);
    if (element.isConnected !== operation.connected) {
      element.isConnected = operation.connected;
      queueMutation({type: "childList", target: body});
    }
  } else {
    throw new Error(`Unsupported operation: ${operation.op}`);
  }
}

process.stdout.write(JSON.stringify({
  captures,
  final: snapshot(),
  flushes,
}));
"""


def _bridge_module():
    try:
        return importlib.import_module("src.accessibility_bridge")
    except ModuleNotFoundError:
        pytest.fail("src.accessibility_bridge does not exist")


def _run_semantic_main_scenario(*, elements, operations):
    document = _bridge_module().SEMANTIC_MAIN_BRIDGE_HTML
    match = re.fullmatch(r"\s*<script>\s*(.*?)\s*</script>\s*", document, re.S)
    assert match is not None
    node = shutil.which("node")
    if node is None and BUNDLED_NODE.exists():
        node = str(BUNDLED_NODE)
    assert node is not None, "Node is required for executable bridge tests"

    completed = subprocess.run(
        [node, "-e", SEMANTIC_MAIN_DOM_HARNESS],
        check=False,
        capture_output=True,
        input=json.dumps(
            {
                "elements": elements,
                "operations": operations,
                "script": match.group(1),
            }
        ),
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_required_thesis_id_maps_to_stable_field_error():
    error = _bridge_module().authoring_field_error(
        "thesis_id is required",
        profile_key="personal",
        ticker="AVGO",
        kind="thesis",
    )

    assert error is not None
    assert error.field_name == "thesis_id"
    assert error.field_label == "Thesis Id"
    assert error.message == "thesis_id is required"
    assert error.error_id == "research-authoring-personal-avgo-thesis-thesis-id-error"


@pytest.mark.parametrize(
    ("reason", "kind"),
    (
        ("unknown_field is required", "thesis"),
        ("effective_at must be an ISO-8601 timestamp", "thesis"),
        (" thesis_id is required", "thesis"),
        ("thesis_id is required ", "thesis"),
        ("Thesis_id is required", "thesis"),
        ("thesis_id is required", "unsupported"),
    ),
)
def test_unknown_or_non_exact_validation_reasons_do_not_bind_a_field(reason, kind):
    assert (
        _bridge_module().authoring_field_error(
            reason,
            profile_key="personal",
            ticker="AVGO",
            kind=kind,
        )
        is None
    )


def test_error_id_normalizes_scope_without_changing_the_exact_field_contract():
    error = _bridge_module().authoring_field_error(
        "source_ref is required",
        profile_key=" Personal Research ",
        ticker="BRK.B",
        kind="evidence",
    )

    assert error is not None
    assert error.error_id == (
        "research-authoring-personal-research-brk-b-evidence-source-ref-error"
    )


def test_rendered_binding_contains_only_fixed_error_configuration():
    calls = []
    error = _bridge_module().AuthoringFieldError(
        field_name="thesis_id",
        field_label="Thesis Id",
        message="thesis_id is required",
        error_id="research-authoring-personal-avgo-thesis-thesis-id-error",
    )

    _bridge_module().render_authoring_error_binding(
        lambda *args, **kwargs: calls.append((args, kwargs)),
        error,
    )

    assert len(calls) == 1
    (document,), options = calls[0]
    match = re.search(r"const config = (\{.*\});", document)
    assert match is not None
    assert json.loads(match.group(1)) == {
        "fieldLabel": "Thesis Id",
        "errorId": "research-authoring-personal-avgo-thesis-thesis-id-error",
        "message": "thesis_id is required",
    }
    assert options == {"height": 0, "scrolling": False}


def test_cleanup_binding_contains_no_field_configuration():
    calls = []

    _bridge_module().render_authoring_error_binding(
        lambda *args, **kwargs: calls.append((args, kwargs)),
        None,
    )

    assert len(calls) == 1
    (document,), options = calls[0]
    match = re.search(r"const config = (\{.*\});", document)
    assert match is not None
    assert json.loads(match.group(1)) == {
        "fieldLabel": None,
        "errorId": None,
        "message": None,
    }
    assert options == {"height": 0, "scrolling": False}


def test_rendered_binding_is_bounded_exact_label_idempotent_and_non_actioning():
    calls = []
    bridge = _bridge_module()
    bridge.render_authoring_error_binding(
        lambda document, **options: calls.append((document, options)),
        bridge.AuthoringFieldError(
            "thesis_id",
            "Thesis Id",
            "thesis_id is required",
            "research-authoring-personal-avgo-thesis-thesis-id-error",
        ),
    )
    document, _ = calls[0]

    assert 'frameElement.closest(\'[data-testid="stExpander"]\')' in document
    assert "label.textContent.trim() === config.fieldLabel" in document
    assert "controls.length !== 1" in document
    assert 'setAttribute("aria-invalid", "true")' in document
    assert 'setAttribute("aria-describedby", describedBy.join(" "))' in document
    assert "existingErrors.length !== 0" in document
    assert 'document.createElement("p")' in document
    assert "insertAdjacentElement" in document
    assert ".focus(" in document
    assert 'data-research-authoring-error-owned' in document
    assert 'data-research-authoring-describedby-owned' in document
    assert 'data-research-authoring-previous-invalid' in document
    assert "token !== ownedDescription" in document
    assert "remainingDescriptions.join" in document
    assert 'if (!config.errorId) return' in document
    for forbidden in (
        ".click(",
        "dispatchevent",
        "requestsubmit",
        ".submit(",
        "postmessage",
    ):
        assert forbidden not in document.lower()


def test_accessibility_bridge_has_no_network_storage_clipboard_or_value_reading():
    assert BRIDGE_PATH.exists()
    source = BRIDGE_PATH.read_text(encoding="utf-8").lower()

    for forbidden in (
        "fetch(",
        "xmlhttprequest",
        "websocket",
        "localstorage",
        "sessionstorage",
        "indexeddb",
        "navigator.clipboard",
        ".value",
    ):
        assert forbidden not in source


def test_semantic_main_bridge_is_fixed_idempotent_and_non_networked():
    document = _bridge_module().SEMANTIC_MAIN_BRIDGE_HTML
    source = document.lower()

    assert '[data-testid="stmain"]' in source
    assert 'setattribute("role", "main")' in source
    assert 'setattribute("id", "research-main")' in source
    assert 'setattribute("aria-label", "stock research workspace")' in source
    assert "mutationobserver" in source
    assert "disconnect()" in source
    assert document.count(
        'host.querySelectorAll(\'[data-testid="stMain"]\')'
    ) == 1
    for forbidden in (
        "fetch(",
        "xmlhttprequest",
        "websocket",
        "localstorage",
        "sessionstorage",
        "indexeddb",
        ".cookie",
        "clipboard",
        ".value",
        "postmessage",
        ".click(",
        "dispatchevent",
        "requestsubmit",
        ".submit(",
        "window.location",
        "document.location",
        "history.",
        "createelement",
        "appendchild",
        "insertadjacentelement",
    ):
        assert forbidden not in source


@pytest.mark.parametrize(
    ("tag", "metadata"),
    (
        ("div", {}),
        ("main", {"id": "native-main", "aria-label": "Native workspace"}),
        (
            "div",
            {
                "role": "main",
                "id": "existing-main",
                "aria-label": "Existing workspace",
            },
        ),
        (
            "div",
            {
                "role": "region",
                "id": "workspace",
                "aria-label": "Workspace",
            },
        ),
    ),
)
def test_semantic_main_bridge_restores_each_original_attribute(tag, metadata):
    original = {"data-testid": "stMain", **metadata}
    result = _run_semantic_main_scenario(
        elements=[{"name": "target", "tag": tag, "attributes": original}],
        operations=[
            {"op": "run"},
            {"op": "capture"},
            {
                "op": "remove-attribute",
                "target": "target",
                "name": "data-testid",
            },
            {"op": "flush"},
            {"op": "capture"},
        ],
    )

    applied, cleaned = result["captures"]
    assert applied["status"] == "applied"
    assert applied["elements"]["target"]["attributes"] | {
        "data-testid": "stMain"
    } == {
        "data-testid": "stMain",
        "role": "main",
        "id": "research-main",
        "aria-label": "Stock research workspace",
        "data-research-main-bridge-owned": "true",
    }
    assert cleaned["status"] == "missing"
    assert cleaned["elements"]["target"]["attributes"] == metadata
    assert cleaned["mainCount"] == int(
        tag == "main" or metadata.get("role") == "main"
    )
    assert cleaned["researchMainIdCount"] == 0


def test_semantic_main_bridge_does_not_resnapshot_on_idempotent_rerender():
    metadata = {
        "role": "region",
        "id": "workspace",
        "aria-label": "Original workspace",
    }
    result = _run_semantic_main_scenario(
        elements=[
            {
                "name": "target",
                "tag": "div",
                "attributes": {"data-testid": "stMain", **metadata},
            }
        ],
        operations=[
            {"op": "run"},
            {"op": "run"},
            {
                "op": "remove-attribute",
                "target": "target",
                "name": "data-testid",
            },
            {"op": "flush"},
            {"op": "capture"},
        ],
    )

    cleaned = result["captures"][0]
    assert cleaned["elements"]["target"]["attributes"] == metadata
    assert cleaned["observerCount"] == 2
    assert [observer["disconnected"] for observer in cleaned["observers"]] == [
        True,
        False,
    ]


def test_semantic_main_bridge_cleanup_preserves_later_framework_changes():
    result = _run_semantic_main_scenario(
        elements=[
            {
                "name": "target",
                "tag": "div",
                "attributes": {
                    "data-testid": "stMain",
                    "role": "region",
                    "id": "workspace",
                    "aria-label": "Original workspace",
                },
            }
        ],
        operations=[
            {"op": "run"},
            {
                "op": "set-attribute",
                "target": "target",
                "name": "role",
                "value": "complementary",
            },
            {
                "op": "set-attribute",
                "target": "target",
                "name": "id",
                "value": "framework-workspace",
            },
            {
                "op": "set-attribute",
                "target": "target",
                "name": "aria-label",
                "value": "Framework workspace",
            },
            {
                "op": "remove-attribute",
                "target": "target",
                "name": "data-testid",
            },
            {"op": "flush"},
            {"op": "capture"},
        ],
    )

    assert result["captures"][0]["elements"]["target"]["attributes"] == {
        "role": "complementary",
        "id": "framework-workspace",
        "aria-label": "Framework workspace",
    }


def test_semantic_main_bridge_observes_attribute_only_target_transitions():
    result = _run_semantic_main_scenario(
        elements=[{"name": "target", "tag": "div"}],
        operations=[
            {"op": "run"},
            {"op": "capture"},
            {
                "op": "set-attribute",
                "target": "target",
                "name": "data-testid",
                "value": "stMain",
            },
            {"op": "flush"},
            {"op": "capture"},
            {"op": "flush"},
            {"op": "capture"},
            {
                "op": "remove-attribute",
                "target": "target",
                "name": "data-testid",
            },
            {"op": "flush"},
            {"op": "capture"},
        ],
    )

    missing, applied, stable, removed = result["captures"]
    assert missing["status"] == "missing"
    assert applied["status"] == "applied"
    assert applied["elements"]["target"]["attributes"] == {
        "data-testid": "stMain",
        "role": "main",
        "id": "research-main",
        "aria-label": "Stock research workspace",
        "data-research-main-bridge-owned": "true",
    }
    assert stable["queryCount"] == applied["queryCount"]
    assert removed["status"] == "missing"
    assert removed["elements"]["target"]["attributes"] == {}
    assert result["flushes"] == [1, 1, 1]
    assert applied["observers"][0]["options"] == {
        "attributes": True,
        "attributeFilter": ["data-testid", "role", "id", "aria-label"],
        "childList": True,
        "subtree": True,
    }


@pytest.mark.parametrize(
    ("name", "value", "main_count", "research_id_count"),
    (
        ("role", "main", 1, 0),
        ("id", "research-main", 0, 1),
    ),
)
def test_semantic_main_bridge_fails_closed_on_later_sibling_conflict(
    name, value, main_count, research_id_count
):
    result = _run_semantic_main_scenario(
        elements=[
            {
                "name": "target",
                "tag": "div",
                "attributes": {"data-testid": "stMain"},
            },
            {"name": "sibling", "tag": "div"},
        ],
        operations=[
            {"op": "run"},
            {"op": "capture"},
            {
                "op": "set-attribute",
                "target": "sibling",
                "name": name,
                "value": value,
            },
            {"op": "flush"},
            {"op": "capture"},
            {"op": "flush"},
            {"op": "capture"},
            {"op": "flush"},
            {"op": "capture"},
        ],
    )

    applied, blocked, filtered, stable = result["captures"]
    assert applied["status"] == "applied"
    assert blocked["status"] == "ambiguous"
    assert blocked["mainCount"] == main_count
    assert blocked["researchMainIdCount"] == research_id_count
    assert blocked["elements"]["target"]["attributes"] == {
        "data-testid": "stMain"
    }
    assert blocked["elements"]["sibling"]["attributes"] == {name: value}
    assert filtered["queryCount"] == blocked["queryCount"]
    assert stable["queryCount"] == blocked["queryCount"]
    assert result["flushes"] == [1, 1, 0]


def test_semantic_main_dom_harness_does_not_deliver_pre_observation_mutations():
    result = _run_semantic_main_scenario(
        elements=[{"name": "target", "tag": "div"}],
        operations=[
            {
                "op": "set-attribute",
                "target": "target",
                "name": "data-testid",
                "value": "stMain",
            },
            {"op": "run"},
            {"op": "capture"},
            {"op": "flush"},
            {"op": "capture"},
        ],
    )

    before_flush, after_flush = result["captures"]
    assert after_flush["queryCount"] == before_flush["queryCount"]
    assert result["flushes"] == [0]


def test_semantic_main_dom_harness_disconnect_discards_observer_queue():
    result = _run_semantic_main_scenario(
        elements=[
            {
                "name": "target",
                "tag": "div",
                "attributes": {"data-testid": "stMain"},
            }
        ],
        operations=[
            {"op": "run"},
            {
                "op": "set-attribute",
                "target": "target",
                "name": "data-testid",
                "value": "retiredMain",
            },
            {"op": "run"},
            {"op": "capture"},
            {"op": "flush"},
            {"op": "capture"},
        ],
    )

    before_flush, after_flush = result["captures"]
    assert before_flush["status"] == "missing"
    assert after_flush["queryCount"] == before_flush["queryCount"]
    assert result["flushes"] == [0]


def test_semantic_main_bridge_cleans_ambiguity_then_applies_remaining_target():
    result = _run_semantic_main_scenario(
        elements=[
            {
                "name": "first",
                "tag": "div",
                "attributes": {"data-testid": "stMain"},
            }
        ],
        operations=[
            {"op": "run"},
            {
                "op": "add",
                "element": {
                    "name": "second",
                    "tag": "div",
                    "attributes": {"data-testid": "stMain"},
                },
            },
            {"op": "flush"},
            {"op": "capture"},
            {
                "op": "set-connected",
                "target": "first",
                "connected": False,
            },
            {"op": "flush"},
            {"op": "capture"},
        ],
    )

    ambiguous, replacement = result["captures"]
    assert ambiguous["status"] == "ambiguous"
    assert ambiguous["mainCount"] == 0
    assert ambiguous["researchMainIdCount"] == 0
    assert ambiguous["elements"]["first"]["attributes"] == {
        "data-testid": "stMain"
    }
    assert ambiguous["elements"]["second"]["attributes"] == {
        "data-testid": "stMain"
    }
    assert replacement["status"] == "applied"
    assert replacement["mainCount"] == 1
    assert replacement["researchMainIdCount"] == 1
    assert replacement["elements"]["second"]["attributes"]["role"] == "main"


def test_semantic_main_bridge_replaces_plain_target_without_duplicate_landmark():
    result = _run_semantic_main_scenario(
        elements=[
            {
                "name": "first",
                "tag": "div",
                "attributes": {
                    "data-testid": "stMain",
                    "role": "region",
                    "id": "first-workspace",
                },
            }
        ],
        operations=[
            {"op": "run"},
            {
                "op": "set-attribute",
                "target": "first",
                "name": "data-testid",
                "value": "retiredMain",
            },
            {
                "op": "add",
                "element": {
                    "name": "second",
                    "tag": "div",
                    "attributes": {"data-testid": "stMain"},
                },
            },
            {"op": "flush"},
            {"op": "capture"},
        ],
    )

    replacement = result["captures"][0]
    assert replacement["status"] == "applied"
    assert replacement["mainCount"] == 1
    assert replacement["researchMainIdCount"] == 1
    assert replacement["elements"]["first"]["attributes"] == {
        "data-testid": "retiredMain",
        "role": "region",
        "id": "first-workspace",
    }
    assert replacement["elements"]["second"]["attributes"]["role"] == "main"


@pytest.mark.parametrize(
    ("tag", "metadata"),
    (
        ("main", {"id": "native-workspace"}),
        ("div", {"role": "main", "id": "role-workspace"}),
        ("div", {"role": "region", "id": "research-main"}),
    ),
)
def test_semantic_main_bridge_fails_closed_before_unsafe_replacement(
    tag, metadata
):
    result = _run_semantic_main_scenario(
        elements=[
            {
                "name": "first",
                "tag": tag,
                "attributes": {"data-testid": "stMain", **metadata},
            }
        ],
        operations=[
            {"op": "run"},
            {
                "op": "set-attribute",
                "target": "first",
                "name": "data-testid",
                "value": "retiredMain",
            },
            {
                "op": "add",
                "element": {
                    "name": "second",
                    "tag": "div",
                    "attributes": {"data-testid": "stMain"},
                },
            },
            {"op": "flush"},
            {"op": "capture"},
            {
                "op": "set-connected",
                "target": "first",
                "connected": False,
            },
            {"op": "flush"},
            {"op": "capture"},
        ],
    )

    blocked, recovered = result["captures"]
    assert blocked["status"] == "ambiguous"
    assert blocked["mainCount"] <= 1
    assert blocked["researchMainIdCount"] <= 1
    assert blocked["elements"]["second"]["attributes"] == {
        "data-testid": "stMain"
    }
    assert recovered["status"] == "applied"
    assert recovered["mainCount"] == 1
    assert recovered["researchMainIdCount"] == 1


@pytest.mark.parametrize(
    "blocker",
    (
        {"name": "other", "tag": "main", "attributes": {}},
        {
            "name": "other",
            "tag": "div",
            "attributes": {"role": "main"},
        },
        {
            "name": "other",
            "tag": "div",
            "attributes": {"id": "research-main"},
        },
    ),
)
def test_semantic_main_bridge_does_not_apply_beside_connected_conflict(blocker):
    result = _run_semantic_main_scenario(
        elements=[
            {
                "name": "target",
                "tag": "div",
                "attributes": {"data-testid": "stMain"},
            },
            blocker,
        ],
        operations=[{"op": "run"}, {"op": "capture"}],
    )

    blocked = result["captures"][0]
    assert blocked["status"] == "ambiguous"
    assert blocked["mainCount"] <= 1
    assert blocked["researchMainIdCount"] <= 1
    assert blocked["elements"]["target"]["attributes"] == {
        "data-testid": "stMain"
    }


def test_render_semantic_main_bridge_renders_only_the_fixed_constant():
    bridge = _bridge_module()
    calls = []

    result = bridge.render_semantic_main_bridge(
        lambda *args, **kwargs: calls.append((args, kwargs))
    )

    assert result is None
    assert calls == [
        ((bridge.SEMANTIC_MAIN_BRIDGE_HTML,), {"height": 0, "scrolling": False})
    ]
    assert tuple(
        inspect.signature(bridge.render_semantic_main_bridge).parameters
    ) == (
        "component_html",
    )
