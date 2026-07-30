import pytest
from streamlit.testing.v1 import AppTest

from src.research_state_accessibility import (
    research_state_message,
    research_state_message_html,
    research_state_transition_key,
)


@pytest.mark.parametrize(
    ("state", "role", "live"),
    [
        ("validation_rejected", "alert", "assertive"),
        ("preview_ready", "status", "polite"),
        ("draft_changed", "status", "polite"),
        ("save_reloaded", "status", "polite"),
        ("save_reload_unverified", "alert", "assertive"),
    ],
)
def test_state_message_semantics(state, role, live):
    message = research_state_message(
        state,
        scope="demo:NVDA:thesis",
        title="State changed",
        detail="Review the visible next step.",
        identity="receipt-1",
    )

    assert (message.role, message.live) == (role, live)
    rendered = research_state_message_html(message, announce=True)

    assert f"role='{role}'" in rendered
    assert f"aria-live='{live}'" in rendered
    assert "aria-atomic='true'" in rendered
    assert rendered.count("State changed") == 1
    assert rendered.count("Review the visible next step.") == 1


def test_transition_identity_is_stable_and_receipt_specific():
    first = research_state_message(
        "preview_ready",
        scope=" demo:NVDA:thesis ",
        title="Preview ready",
        detail="This exact record is ready for review and is not saved.",
        identity="receipt-1",
    )
    same = research_state_message(
        "preview_ready",
        scope="demo:NVDA:thesis",
        title="Preview ready",
        detail="This exact record is ready for review and is not saved.",
        identity="receipt-1",
    )
    later = research_state_message(
        "preview_ready",
        scope="demo:NVDA:thesis",
        title="Preview ready",
        detail="This exact record is ready for review and is not saved.",
        identity="receipt-2",
    )

    assert research_state_transition_key(first) == research_state_transition_key(same)
    assert research_state_transition_key(first) != research_state_transition_key(later)
    assert "receipt-1" not in first.message_id
    assert first.message_id.startswith("research-state-demo-nvda-thesis-preview-ready-")


def test_state_message_html_escapes_visible_and_attribute_content():
    message = research_state_message(
        "draft_changed",
        scope="demo:'NVDA':thesis",
        title="<Draft> & changed",
        detail='"Validate" <again>.',
        identity="receipt-'1'",
    )

    rendered = research_state_message_html(message)

    assert "<Draft>" not in rendered
    assert "&lt;Draft&gt; &amp; changed" in rendered
    assert "&quot;Validate&quot; &lt;again&gt;." in rendered
    assert "receipt-'1'" not in rendered


def test_non_announcing_render_stays_visible_without_a_live_region():
    message = research_state_message(
        "save_reloaded",
        scope="demo:NVDA:thesis",
        title="Record saved",
        detail="The append-only record was reloaded.",
        identity="record-1",
    )

    rendered = research_state_message_html(message, announce=False)

    assert "role='group'" in rendered
    assert "aria-live" not in rendered
    assert "aria-atomic" not in rendered
    assert "Record saved" in rendered
    assert "The append-only record was reloaded." in rendered


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("state", "unknown"),
        ("scope", " "),
        ("title", ""),
        ("identity", "\t"),
    ],
)
def test_state_message_rejects_unknown_or_unscoped_inputs(field, value):
    values = {
        "state": "preview_ready",
        "scope": "demo:NVDA:thesis",
        "title": "Preview ready",
        "detail": "Review the visible next step.",
        "identity": "receipt-1",
    }
    values[field] = value

    with pytest.raises(ValueError):
        research_state_message(**values)


def test_synthetic_state_harness_exposes_static_states_without_live_noise():
    app = AppTest.from_file(
        "tests/fixtures/research_state_accessibility_app.py"
    ).run(timeout=20)

    assert not app.exception
    assert [button.key for button in app.button] == [
        "transition-validation-rejected",
        "transition-preview-ready",
        "transition-draft-changed",
        "transition-save-reloaded",
        "transition-save-reload-unverified",
    ]
    static_bodies = [
        element.proto.body
        for element in app.get("html")
        if "data-research-static-state" in element.proto.body
    ]
    assert len(static_bodies) == 6
    loading = next(body for body in static_bodies if "state-loading" in body)
    assert "aria-busy='true'" in loading
    assert "aria-live" not in loading
    assert all("aria-live" not in body for body in static_bodies)
    assert all("TEST1" in body for body in static_bodies)


@pytest.mark.parametrize(
    ("button_key", "role", "live", "title"),
    [
        (
            "transition-validation-rejected",
            "alert",
            "assertive",
            "Validation rejected",
        ),
        ("transition-preview-ready", "status", "polite", "Preview ready"),
        ("transition-draft-changed", "status", "polite", "Draft changed"),
        ("transition-save-reloaded", "status", "polite", "Record saved"),
        (
            "transition-save-reload-unverified",
            "alert",
            "assertive",
            "Save verification incomplete",
        ),
    ],
)
def test_synthetic_state_harness_uses_production_transition_semantics(
    button_key, role, live, title
):
    app = AppTest.from_file(
        "tests/fixtures/research_state_accessibility_app.py"
    ).run(timeout=20)

    app.button(key=button_key).click().run()

    messages = [
        element.proto.body
        for element in app.get("html")
        if "research-state-message" in element.proto.body
    ]
    assert len(messages) == 1
    assert f"role='{role}'" in messages[0]
    assert f"aria-live='{live}'" in messages[0]
    assert "aria-atomic='true'" in messages[0]
    assert title in messages[0]
    assert "TEST1" in messages[0]
