import builtins

import pytest

from src.portable_research_action_policy import contains_portable_action_language


@pytest.mark.parametrize(
    "text",
    (
        "buy common shares",
        "execute one large block trade",
        "open another position",
        "cover the short",
        "go strategically net long",
        "The note says the strategy executes trades.",
    ),
)
def test_existing_active_action_families_remain_non_portable(text):
    assert contains_portable_action_language(text) is True


@pytest.mark.parametrize(
    "text",
    (
        "The filing covers the current position disclosure.",
        "The model builds a current position estimate.",
        "Hold the current equity method constant.",
        "Held-to-maturity securities remain unchanged.",
        "Available-for-sale securities remain unchanged.",
        "No recommendation; not investment advice.",
    ),
)
def test_existing_reference_and_boundary_prose_remains_portable(text):
    assert contains_portable_action_language(text) is False


def test_policy_is_repeatable_and_never_opens_files(monkeypatch):
    def fail_open(*args, **kwargs):
        raise AssertionError("portable policy must not read files")

    monkeypatch.setattr(builtins, "open", fail_open)
    assert contains_portable_action_language("buy shares") is True
    assert contains_portable_action_language("buy shares") is True
