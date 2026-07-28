import importlib
import json
import re
from pathlib import Path

import pytest


BRIDGE_PATH = Path("src/accessibility_bridge.py")


def _bridge_module():
    try:
        return importlib.import_module("src.accessibility_bridge")
    except ModuleNotFoundError:
        pytest.fail("src.accessibility_bridge does not exist")


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
