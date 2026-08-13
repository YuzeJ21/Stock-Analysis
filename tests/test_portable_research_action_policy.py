import builtins

import pytest

from src.portable_research_action_policy import contains_portable_action_language


_MODIFIED_MODAL_PASSIVE_ACTIONS = (
    "Shares should definitely be bought now.",
    "Shares should probably be bought now.",
    "Shares should ultimately be bought now.",
    "Shares should promptly be bought now.",
    "Shares should gradually be bought now.",
    "Shares should aggressively be bought now.",
    "Shares definitely should be bought now.",
    "Shares probably should be bought now.",
    "Shares ultimately should be bought now.",
    "Shares promptly should be bought now.",
    "Shares gradually should be bought now.",
    "Shares aggressively should be bought now.",
    "Shares reviewwise should planwise be bought now.",
    "Shares outstanding should be bought now.",
    "Shares based on review should be bought now.",
    "The share count should be purchased now.",
    "Shares data should be bought now.",
    "Shares should be purchased, dataset quality permitting.",
    "Shares should be purchased, source dataset quality permitting.",
    "The share count should be normalized using the most recently purchased dataset and then sold.",
    "The share count should be normalized using the most recently purchased source dataset and then sold.",
    "Shares should reviewwise planwise slowly carefully deliberately eventually be bought now.",
    "Shares reviewwise planwise slowly carefully deliberately eventually should be bought now.",
)
_ACTIVE_EXPOSURE_ACTIONS = (
    "Increase exposure now.",
    "Reduce exposure now.",
    "Build exposure now.",
    "Initiate exposure now.",
    "Increase the current direct strategic gross net total aggregate absolute adjusted exposure now.",
)
_CONTRACTED_MODAL_PASSIVE_ACTIONS = (
    "Shares cannot be bought now.",
    "Shares mustn't be bought now.",
    "Shares shouldn't be bought now.",
    "Shares can't be bought now.",
    "Shares couldn't be bought now.",
    "Shares mayn't be bought now.",
    "Shares mightn't be bought now.",
    "Shares won't be bought now.",
    "Shares wouldn't be bought now.",
    "Shares shan't be bought now.",
    "Shares mustn’t be bought now.",
    "Shares shouldn’t be bought now.",
    "Shares can’t be bought now.",
    "Shares couldn’t be bought now.",
    "Shares mayn’t be bought now.",
    "Shares mightn’t be bought now.",
    "Shares won’t be bought now.",
    "Shares wouldn’t be bought now.",
    "Shares shan’t be bought now.",
)


@pytest.mark.parametrize(
    "text",
    (
        "buy common shares",
        "execute one large block trade",
        "open another position",
        "cover the short",
        "go strategically net long",
        "The note says the strategy executes trades.",
        "Increase the model detail using the reviewed historical assumptions and document the resulting shares now.",
        "Increase the model detail using the reviewed historical assumptions and increase the resulting exposure now.",
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


@pytest.mark.parametrize("text", _MODIFIED_MODAL_PASSIVE_ACTIONS)
def test_modal_passive_modifier_runs_cannot_escape_policy_within_a_clause(text):
    assert contains_portable_action_language(text) is True


@pytest.mark.parametrize("text", _ACTIVE_EXPOSURE_ACTIONS)
def test_active_position_lifecycle_exposure_instructions_are_not_portable(text):
    assert contains_portable_action_language(text) is True


@pytest.mark.parametrize(
    "text",
    (
        "Purchase the entire share count now.",
        "Sell the selected share count now.",
        "Buy the full share count now.",
        "Acquire the resulting share count now.",
    ),
)
def test_active_share_count_transaction_objects_are_not_reference_exempt(text):
    assert contains_portable_action_language(text) is True


@pytest.mark.parametrize("text", _CONTRACTED_MODAL_PASSIVE_ACTIONS)
def test_supported_modal_negation_contractions_are_not_portable(text):
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
        "The position estimate based on reviewed historical evidence and documented assumptions should be increased.",
        "The share count should be normalized using the most recently purchased dataset.",
        "The share count should be normalized using the most recently purchased source dataset.",
        "Increase the model detail using the reviewed historical assumptions and document the resulting share count.",
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
    "text",
    (
        "The share count should be normalized using the most recently purchased vendor dataset.",
        "The share count should be normalized using the purchased external source dataset.",
        "The share count should be normalized using the dataset most recently purchased from the vendor.",
        "The share count should be normalized using the recently purchased third-party dataset.",
    ),
)
def test_bounded_purchased_dataset_methodology_context_remains_portable(text):
    assert contains_portable_action_language(text) is False


@pytest.mark.parametrize(
    "text",
    (
        "The share count should be normalized using the most recently purchased, vendor dataset.",
        "The share count should be normalized using the purchased external, source dataset.",
        "The share count should be normalized using the dataset most recently purchased, from the vendor.",
        "The share count should be normalized using the recently sold vendor dataset.",
        "The share count should be normalized using the recently purchased and then dataset.",
        "The share count should be normalized using the dataset and then purchased from the vendor.",
        "The share count should be normalized using the most recently purchased vendor dataset and then sold.",
        "The share count should be normalized using the dataset most recently purchased from the vendor and then sold.",
    ),
)
def test_purchased_dataset_methodology_context_rejects_wrong_participles_boundaries_and_suffix_actions(text):
    assert contains_portable_action_language(text) is True


def test_distant_documented_position_estimate_reference_remains_portable():
    text = "Increase the model detail using reviewed historical assumptions and document the resulting position estimate."

    assert contains_portable_action_language(text) is False


@pytest.mark.parametrize(
    "text",
    (
        "Increase as the model directs and document the resulting share count.",
        "Increase it per model and document the resulting position estimate.",
        "Increase model-directed quantity and document the resulting share count.",
        "Reduce model-directed quantity and document the resulting position estimate.",
        "Increase the model detail using reviewed historical assumptions and document the resulting position.",
        "Reduce the model detail using reviewed historical assumptions and document the resulting exposure.",
        "Build the model detail using reviewed historical assumptions and document the resulting shares.",
        "Initiate the model review using reviewed historical assumptions and document the resulting position.",
    ),
)
def test_long_distance_unqualified_action_endpoints_remain_non_portable(text):
    assert contains_portable_action_language(text) is True


@pytest.mark.parametrize(
    "text, expected",
    (
        ("Shares are ordered by market capitalization.", False),
        ("Shares are ordered by market capitalization and then reviewed.", False),
        ("Shares are ordered by market capitalization and then sold.", True),
        ("Shares are ordered by market capitalization and then held.", True),
        ("Shares are ordered by market capitalization and then covered.", True),
        ("Shares are ordered by market capitalization and then routed.", True),
    ),
)
def test_passive_reference_phrase_does_not_hide_appended_actions(text, expected):
    assert contains_portable_action_language(text) is expected


@pytest.mark.parametrize(
    "text, expected",
    (
        ("Historical evidence shows shares were purchased by the issuer in 2024.", False),
        ("Historical evidence shows shares were purchased by the issuer.", False),
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
        ("Historical evidence shows shares were purchased by the issuer in the present period.", True),
        ("Historical evidence shows shares were purchased by the issuer later this week.", True),
        ("Historical evidence shows shares were purchased by the issuer during 2024.", True),
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
