import pandas as pd
import pytest

from src.commercial_source_rights import SourceRights
from src.dcf_price_lineage import review_dcf_price_lineage


def _readiness_row(ticker: str, *, dcf_ready: bool = False, fundamentals_ready: bool = False) -> dict[str, object]:
    return {
        "ticker": ticker,
        "dcf_ready": dcf_ready,
        "fundamentals_ready": fundamentals_ready,
    }


def _rights(
    source_id: str,
    *,
    commercial_use: str = "approved",
    supported_fields: tuple[str, ...] = ("prices",),
) -> SourceRights:
    return SourceRights(
        source_id=source_id,
        display_name=source_id,
        permitted_use="source_backed_market_data",
        commercial_use=commercial_use,
        redistribution="derived_data_only",
        storage_limits="reviewed local rows",
        attribution="required",
        rate_limits="provider terms",
        authentication="provider specific",
        expected_freshness="daily",
        supported_fields=supported_fields,
        fallback_priority=1,
    )


def _price_row(
    ticker: str,
    date: str,
    close: object,
    *,
    source: object = "approved_prices",
    source_ref: object = "https://example.test/price-row",
    retrieved_at: object = "2026-01-04T23:00:00Z",
) -> dict[str, object]:
    return {
        "ticker": ticker,
        "date": date,
        "close": close,
        "source": source,
        "source_ref": source_ref,
        "retrieved_at": retrieved_at,
    }


def test_review_selects_only_false_to_true_dcf_promotions_and_can_complete():
    saved = pd.DataFrame(
        [
            _readiness_row("AAA"),
            _readiness_row("BBB", dcf_ready=True),
            _readiness_row("CCC"),
        ]
    )
    proposed = pd.DataFrame(
        [
            _readiness_row("AAA", dcf_ready=True),
            _readiness_row("BBB", dcf_ready=True),
            _readiness_row("CCC", fundamentals_ready=True),
        ]
    )
    prices = pd.DataFrame(
        [
            _price_row("AAA", "2026-01-02", 10.0, source_ref="https://example.test/AAA/2026-01-02"),
            _price_row("AAA", "2026-01-03", 11.0, source_ref="https://example.test/AAA/2026-01-03"),
            _price_row("BBB", "2026-01-03", 20.0),
            _price_row("CCC", "2026-01-03", 30.0),
        ]
    )

    review = review_dcf_price_lineage(
        saved,
        proposed,
        prices,
        rights_registry={"approved_prices": _rights("approved_prices")},
        review_cutoff="2026-01-05T00:00:00Z",
        top_n=5,
    )

    assert review.status == "price_lineage_review_complete"
    assert review.promotion_count == 1
    assert review.usable_latest_row_count == 1
    assert review.missing_latest_row_count == 0
    assert review.ambiguous_latest_row_count == 0
    assert review.lineage_complete_count == 1
    assert review.rights_approved_count == 1
    assert review.field_scope_complete_count == 1
    assert review.source_counts == (("approved_prices", 1),)
    assert review.rights_status_counts == (("approved", 1),)
    assert len(review.evidence_rows) == 1
    evidence = review.evidence_rows[0]
    assert evidence.ticker == "AAA"
    assert evidence.observation_date == "2026-01-03"
    assert evidence.valid_row_count == 2
    assert evidence.latest_row_count == 1
    assert evidence.source_reference == "https://example.test/AAA/2026-01-03"
    assert evidence.missing_provenance_fields == ()
    assert evidence.missing_supported_fields == ()
    assert evidence.blockers == ()


@pytest.mark.parametrize(
    ("prices", "blocker"),
    [
        (pd.DataFrame(), "missing_latest_price_row"),
        (pd.DataFrame([_price_row("AAA", "not-a-date", 10.0)]), "missing_latest_price_row"),
        (pd.DataFrame([_price_row("AAA", "2026-01-03", 0)]), "missing_latest_price_row"),
    ],
)
def test_review_fails_closed_when_no_usable_latest_row(prices: pd.DataFrame, blocker: str):
    saved = pd.DataFrame([_readiness_row("AAA")])
    proposed = pd.DataFrame([_readiness_row("AAA", dcf_ready=True)])

    review = review_dcf_price_lineage(
        saved,
        proposed,
        prices,
        rights_registry={"approved_prices": _rights("approved_prices")},
    )

    assert review.status == "price_lineage_review_required"
    assert review.usable_latest_row_count == 0
    assert review.missing_latest_row_count == 1
    assert review.lineage_complete_count == 0
    assert review.rights_approved_count == 0
    assert review.field_scope_complete_count == 0
    assert review.evidence_rows[0].source_id == "<missing>"
    assert review.evidence_rows[0].rights_status == "not_evaluated_missing_evidence"
    assert review.evidence_rows[0].blockers == (blocker,)


def test_review_fails_closed_on_duplicate_latest_price_rows():
    saved = pd.DataFrame([_readiness_row("AAA")])
    proposed = pd.DataFrame([_readiness_row("AAA", dcf_ready=True)])
    prices = pd.DataFrame(
        [
            _price_row("AAA", "2026-01-02", 9.0),
            _price_row("AAA", "2026-01-03", 10.0),
            _price_row("AAA", "2026-01-03", 10.0),
        ]
    )

    review = review_dcf_price_lineage(
        saved,
        proposed,
        prices,
        rights_registry={"approved_prices": _rights("approved_prices")},
    )

    assert review.ambiguous_latest_row_count == 1
    assert review.missing_latest_row_count == 0
    assert review.evidence_rows[0].source_id == "<ambiguous>"
    assert review.evidence_rows[0].latest_row_count == 2
    assert review.evidence_rows[0].rights_status == "not_evaluated_ambiguous_evidence"
    assert review.evidence_rows[0].blockers == ("ambiguous_latest_price_row",)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", ""),
        ("source_ref", ""),
        ("retrieved_at", ""),
    ],
)
def test_review_reports_each_missing_provenance_field_independently(field: str, value: str):
    saved = pd.DataFrame([_readiness_row("AAA")])
    proposed = pd.DataFrame([_readiness_row("AAA", dcf_ready=True)])
    row = _price_row("AAA", "2026-01-03", 10.0)
    row[field] = value

    review = review_dcf_price_lineage(
        saved,
        proposed,
        pd.DataFrame([row]),
        rights_registry={"approved_prices": _rights("approved_prices")},
        review_cutoff="2026-01-05T00:00:00Z",
    )

    evidence = review.evidence_rows[0]
    assert review.status == "price_lineage_review_required"
    assert review.lineage_complete_count == 0
    assert field in evidence.missing_provenance_fields
    assert f"missing_provenance:{field}" in evidence.blockers


@pytest.mark.parametrize(
    ("retrieved_at", "cutoff", "blocker"),
    [
        ("2026-01-03T23:00:00", "2026-01-05T00:00:00Z", "retrieved_at_timezone_required"),
        ("2026-01-03T23:59:59Z", "2026-01-05T00:00:00Z", "retrieved_before_observation_available"),
        ("2026-01-05T00:00:01Z", "2026-01-05T00:00:00Z", "retrieved_after_review_cutoff"),
        ("2026-01-04T23:00:00Z", None, "review_cutoff_required"),
    ],
)
def test_review_uses_shared_price_temporal_gate(
    retrieved_at: str,
    cutoff: str | None,
    blocker: str,
):
    saved = pd.DataFrame([_readiness_row("AAA")])
    proposed = pd.DataFrame([_readiness_row("AAA", dcf_ready=True)])
    prices = pd.DataFrame(
        [_price_row("AAA", "2026-01-03", 10.0, retrieved_at=retrieved_at)]
    )

    review = review_dcf_price_lineage(
        saved,
        proposed,
        prices,
        rights_registry={"approved_prices": _rights("approved_prices")},
        review_cutoff=cutoff,
    )

    evidence = review.evidence_rows[0]
    assert review.status == "price_lineage_review_required"
    assert blocker in evidence.blockers


@pytest.mark.parametrize(
    ("source_id", "registry", "rights_status"),
    [
        ("unknown_prices", {}, "unknown_source"),
        ("approved_prices; other", {"approved_prices": _rights("approved_prices")}, "unknown_source"),
        (
            "research_prices",
            {"research_prices": _rights("research_prices", commercial_use="unverified")},
            "commercial_rights_unverified",
        ),
    ],
)
def test_review_evaluates_exact_source_without_inference(
    source_id: str,
    registry: dict[str, SourceRights],
    rights_status: str,
):
    saved = pd.DataFrame([_readiness_row("AAA")])
    proposed = pd.DataFrame([_readiness_row("AAA", dcf_ready=True)])

    review = review_dcf_price_lineage(
        saved,
        proposed,
        pd.DataFrame([_price_row("AAA", "2026-01-03", 10.0, source=source_id)]),
        rights_registry=registry,
        review_cutoff="2026-01-05T00:00:00Z",
    )

    assert review.rights_approved_count == 0
    assert review.evidence_rows[0].source_id == source_id
    assert review.evidence_rows[0].rights_status == rights_status
    assert f"commercial_rights:{rights_status}" in review.evidence_rows[0].blockers


def test_review_keeps_approved_rights_separate_from_registered_price_scope():
    saved = pd.DataFrame([_readiness_row("AAA")])
    proposed = pd.DataFrame([_readiness_row("AAA", dcf_ready=True)])

    review = review_dcf_price_lineage(
        saved,
        proposed,
        pd.DataFrame([_price_row("AAA", "2026-01-03", 10.0)]),
        rights_registry={"approved_prices": _rights("approved_prices", supported_fields=("revenue",))},
        review_cutoff="2026-01-05T00:00:00Z",
    )

    assert review.status == "price_lineage_review_required"
    assert review.rights_approved_count == 1
    assert review.field_scope_complete_count == 0
    assert review.evidence_rows[0].missing_supported_fields == ("prices",)
    assert "registered_price_scope_incomplete" in review.evidence_rows[0].blockers


def test_review_caps_evidence_without_changing_totals_and_validates_top_n():
    tickers = ["AAA", "BBB", "CCC"]
    saved = pd.DataFrame([_readiness_row(ticker) for ticker in tickers])
    proposed = pd.DataFrame([_readiness_row(ticker, dcf_ready=True) for ticker in tickers])
    prices = pd.DataFrame([_price_row(ticker, "2026-01-03", 10.0) for ticker in tickers])

    review = review_dcf_price_lineage(
        saved,
        proposed,
        prices,
        rights_registry={"approved_prices": _rights("approved_prices")},
        review_cutoff="2026-01-05T00:00:00Z",
        top_n=1,
    )

    assert review.promotion_count == 3
    assert review.usable_latest_row_count == 3
    assert review.lineage_complete_count == 3
    assert len(review.evidence_rows) == 1
    assert review.evidence_rows[0].ticker == "AAA"

    with pytest.raises(ValueError, match="top_n must be at least 1"):
        review_dcf_price_lineage(saved, proposed, prices, rights_registry={}, top_n=0)


def test_review_reports_no_dcf_promotions_without_inspecting_prices():
    saved = pd.DataFrame([_readiness_row("AAA")])
    proposed = pd.DataFrame([_readiness_row("AAA", fundamentals_ready=True)])

    review = review_dcf_price_lineage(saved, proposed, pd.DataFrame(), rights_registry={}, top_n=5)

    assert review.status == "no_dcf_promotions"
    assert review.promotion_count == 0
    assert review.evidence_rows == ()
