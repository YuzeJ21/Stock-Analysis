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


@pytest.mark.parametrize(
    "text",
    (
        "Shares should be bought now.",
        "The stock should be sold.",
        "A trade should be executed.",
        "The order should be submitted.",
        "The position should be increased.",
        "Long exposure should be opened.",
    ),
)
def test_modal_passive_transaction_language_is_not_portable(text):
    assert contains_portable_action_language(text) is True


@pytest.mark.parametrize(
    "text, expected",
    (
        ("Shares must be bought.", True),
        ("Shares must get bought.", True),
        ("Shares should be bought.", True),
        ("Shares should get bought.", True),
        ("Shares can be bought.", True),
        ("Shares can get bought.", True),
        ("Shares could be bought.", True),
        ("Shares could get bought.", True),
        ("Shares may be bought.", True),
        ("Shares may get bought.", True),
        ("Shares might be bought.", True),
        ("Shares might get bought.", True),
        ("Shares will be bought.", True),
        ("Shares will get bought.", True),
        ("Shares would be bought.", True),
        ("Shares would get bought.", True),
        ("Shares shall be bought.", True),
        ("Shares shall get bought.", True),
        ("The stock is sold.", True),
        ("Shares are bought.", True),
        ("A trade was executed.", True),
        ("The orders were submitted.", True),
        ("Shares been bought.", True),
        ("Shares being bought.", True),
        ("The stock gets sold.", True),
        ("Shares got bought.", True),
        ("Shares getting bought.", True),
        ("Shares should not be bought.", True),
        ("A trade was never quietly executed.", True),
        ("Shares, should be bought.", True),
        ("Long‐exposure should be opened.", True),
        ("Ｓｈａｒｅｓ should be bought.", True),
        ("Sha\u200bres should be bought.", True),
        ("Shares should review the evidence.", False),
        ("Shares should be carefully reviewed.", False),
        ("A trade should execute the model.", False),
    ),
)
def test_modal_passive_policy_handles_supported_chains_and_normalization(text, expected):
    assert contains_portable_action_language(text) is expected


@pytest.mark.parametrize(
    "text",
    (
        "The position estimate should be increased.",
        "The trade record should be ordered by date.",
        "The equity method should be held constant.",
        "Securities are held to maturity.",
        "Assets are available for sale.",
        "Shares are a commonly purchased investment class.",
        "Shares are family purchased investment units.",
        "Shares are ordered by market capitalization.",
    ),
)
def test_modal_reference_and_classification_prose_remains_portable(text):
    assert contains_portable_action_language(text) is False


@pytest.mark.parametrize(
    "text, expected",
    (
        ("Shares are ordered by market capitalization.", False),
        ("Shares are ordered by market capitalization and then reviewed.", False),
        ("Shares are ordered by market capitalization and then sold.", True),
        ("Shares are ordered by market capitalization and then held.", True),
    ),
)
def test_passive_reference_phrase_does_not_hide_appended_actions(text, expected):
    assert contains_portable_action_language(text) is expected


@pytest.mark.parametrize(
    "text, expected",
    (
        ("Historical evidence shows shares were purchased by the issuer in 2024.", False),
        ("Shares were purchased.", True),
        ("Shares were purchased by the issuer.", True),
        ("Historical evidence shows shares were purchased.", True),
        ("Shares should be purchased by the issuer.", True),
        ("The report shows shares are purchased by the issuer tomorrow.", True),
        ("Current evidence shows shares are purchased by the issuer.", True),
        ("Historical evidence shows shares are purchased by the issuer tomorrow.", True),
        ("Historical evidence shows shares were purchased by the issuer tomorrow.", True),
        ("Historical evidence shows shares were purchased by the issuer currently.", True),
        ("Historical evidence shows shares were purchased by the issuer in the future.", True),
    ),
)
def test_direct_passive_historical_attribution_exception_is_narrow(text, expected):
    assert contains_portable_action_language(text) is expected


def test_policy_is_repeatable_and_never_opens_files(monkeypatch):
    def fail_open(*args, **kwargs):
        raise AssertionError("portable policy must not read files")

    monkeypatch.setattr(builtins, "open", fail_open)
    assert contains_portable_action_language("buy shares") is True
    assert contains_portable_action_language("buy shares") is True
