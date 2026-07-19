from pathlib import Path

import pandas as pd

from src import readiness_preview
from src.commercial_source_rights import SourceRights
from src.readiness_preview import (
    build_readiness_impact_preview,
    compare_readiness_frames,
    render_readiness_impact_preview,
    review_readiness_promotions,
)


def _row(ticker: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "ticker": ticker,
        "overall_readiness_state": "blocked",
        "price_ready": False,
        "momentum_ready": False,
        "fundamentals_ready": False,
        "dcf_ready": False,
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "ready_features": "",
        "partial_features": "",
        "blocked_features": "price, fundamentals",
        "excluded_features": "",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    row.update(overrides)
    return row


def _file_manifest(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _rights_registry() -> dict[str, SourceRights]:
    return {
        "sec_companyfacts": SourceRights(
            source_id="sec_companyfacts",
            display_name="SEC Companyfacts",
            permitted_use="source_backed_company_facts",
            commercial_use="approved",
            redistribution="derived_data_only",
            storage_limits="reviewed local facts",
            attribution="SEC EDGAR",
            rate_limits="fair access",
            authentication="SEC_USER_AGENT",
            expected_freshness="filing driven",
            supported_fields=("revenue", "shares_outstanding", "filing_dates"),
            fallback_priority=1,
        ),
        "yfinance": SourceRights(
            source_id="yfinance",
            display_name="yfinance",
            permitted_use="research_only",
            commercial_use="unverified",
            redistribution="not_permitted",
            storage_limits="local cache",
            attribution="Yahoo Finance",
            rate_limits="upstream terms",
            authentication="none",
            expected_freshness="market dependent",
            supported_fields=("prices",),
            fallback_priority=90,
        ),
    }


def test_compare_ignores_updated_at_but_reports_stable_fields():
    saved = pd.DataFrame([_row("AAA")])
    timestamp_only = pd.DataFrame([_row("AAA", updated_at="2026-07-18T00:00:00+00:00")])
    changed = pd.DataFrame(
        [
            _row(
                "AAA",
                price_ready=True,
                ready_features="price",
                blocked_features="fundamentals",
                updated_at="2026-07-18T00:00:00+00:00",
            )
        ]
    )

    assert compare_readiness_frames(saved, timestamp_only, top_n=20).status == "no_readiness_changes"
    preview = compare_readiness_frames(saved, changed, top_n=20)

    assert preview.status == "changes_detected"
    assert preview.changed_ticker_count == 1
    assert preview.changed_tickers[0].ticker == "AAA"
    assert preview.changed_tickers[0].fields == ("price_ready", "ready_features", "blocked_features")


def test_compare_caps_detail_and_preserves_total_with_added_and_removed_rows():
    saved = pd.DataFrame([_row("AAA"), _row("BBB")])
    proposed = pd.DataFrame([_row("CCC"), _row("DDD")])

    preview = compare_readiness_frames(saved, proposed, top_n=2)

    assert preview.changed_ticker_count == 4
    assert [change.ticker for change in preview.changed_tickers] == ["AAA", "BBB"]
    assert all(change.fields == ("row_presence",) for change in preview.changed_tickers)


def test_promotion_review_keeps_technical_changes_separate_from_evidence_gates():
    saved = pd.DataFrame([_row("AAA"), _row("BBB"), _row("CCC")])
    proposed = pd.DataFrame(
        [
            _row("AAA", fundamentals_ready=True, dcf_ready=True),
            _row("BBB", fundamentals_ready=True),
            _row("CCC", fundamentals_ready=True),
        ]
    )
    fundamentals = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "source": "sec_companyfacts",
                "as_of_date": "2025-12-31",
                "sec_accession": "0001",
            },
            {
                "ticker": "BBB",
                "source": "sec_companyfacts; sec_filing_document",
                "as_of_date": "2025-12-31",
                "sec_accession": "0002",
            },
            {
                "ticker": "CCC",
                "source": "sec_companyfacts",
                "as_of_date": "",
                "sec_accession": "",
            },
        ]
    )

    review = review_readiness_promotions(
        saved,
        proposed,
        fundamentals,
        rights_registry=_rights_registry(),
        top_n=2,
    )

    assert review.status == "evidence_review_required"
    assert review.promotion_count == 3
    assert review.fundamentals_promotion_count == 3
    assert review.dcf_promotion_count == 1
    assert review.rights_approved_count == 2
    assert review.rights_review_required_count == 1
    assert review.provenance_complete_count == 2
    assert review.provenance_review_required_count == 1
    assert review.field_scope_complete_count == 0
    assert review.field_scope_review_required_count == 3
    assert review.source_counts == (
        ("sec_companyfacts", 2),
        ("sec_companyfacts; sec_filing_document", 1),
    )
    assert len(review.evidence_rows) == 2
    assert review.evidence_rows[0].ticker == "AAA"
    assert review.evidence_rows[0].promoted_fields == ("fundamentals_ready", "dcf_ready")
    assert review.evidence_rows[0].rights_status == "approved"
    assert review.evidence_rows[0].missing_supported_fields == ("free_cash_flow", "fcf_margin")
    assert review.evidence_rows[1].rights_status == "unknown_source"
    assert review.evidence_rows[1].source_id == "sec_companyfacts; sec_filing_document"


def test_promotion_review_fails_closed_on_duplicate_fundamentals_rows():
    saved = pd.DataFrame([_row("AAA")])
    proposed = pd.DataFrame([_row("AAA", fundamentals_ready=True)])
    fundamentals = pd.DataFrame(
        [
            {"ticker": "AAA", "source": "sec_companyfacts", "as_of_date": "2025-12-31", "sec_accession": "0001"},
            {"ticker": "AAA", "source": "sec_companyfacts", "as_of_date": "2026-03-31", "sec_accession": "0002"},
        ]
    )

    review = review_readiness_promotions(
        saved,
        proposed,
        fundamentals,
        rights_registry=_rights_registry(),
        top_n=5,
    )

    assert review.status == "evidence_review_required"
    assert review.rights_approved_count == 0
    assert review.provenance_complete_count == 0
    assert review.field_scope_complete_count == 0
    assert review.evidence_rows[0].rights_status == "not_evaluated_ambiguous_evidence"
    assert review.evidence_rows[0].blockers == ("duplicate_fundamentals_rows",)


def test_promotion_review_reports_no_promotions_without_source_rows():
    saved = pd.DataFrame([_row("AAA")])
    proposed = pd.DataFrame([_row("AAA")])

    review = review_readiness_promotions(
        saved,
        proposed,
        pd.DataFrame(),
        rights_registry=_rights_registry(),
        top_n=5,
    )

    assert review.status == "no_promotions"
    assert review.promotion_count == 0
    assert review.evidence_rows == ()


def test_missing_saved_snapshot_fails_closed_without_building_or_writing(tmp_path: Path, monkeypatch):
    called = False

    def _unexpected_build(*args: object, **kwargs: object) -> dict[str, pd.DataFrame]:
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(readiness_preview, "build_ticker_readiness_report", _unexpected_build)
    before = _file_manifest(tmp_path)

    preview = build_readiness_impact_preview(tmp_path)
    rendered = render_readiness_impact_preview(preview)

    assert preview.status == "missing_saved_snapshot"
    assert called is False
    assert "comparison is unavailable" in rendered.lower()
    assert "does not make saved readiness current" in rendered
    assert _file_manifest(tmp_path) == before


def test_preview_builds_in_memory_and_renders_non_unlock_boundary(tmp_path: Path, monkeypatch):
    reports_dir = tmp_path / "data" / "reports"
    reports_dir.mkdir(parents=True)
    pd.DataFrame([_row("AAA")]).to_csv(reports_dir / "ticker_readiness_report.csv", index=False)
    pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "source": "sec_companyfacts",
                "as_of_date": "2025-12-31",
                "sec_accession": "0001",
            }
        ]
    ).to_csv(tmp_path / "data" / "fundamentals.csv", index=False)

    def _build(*args: object, **kwargs: object) -> dict[str, pd.DataFrame]:
        assert kwargs["write_outputs"] is False
        return {"ticker_readiness_report": pd.DataFrame([_row("AAA", price_ready=True)])}

    monkeypatch.setattr(readiness_preview, "build_ticker_readiness_report", _build)
    before = _file_manifest(tmp_path)

    preview = build_readiness_impact_preview(tmp_path, top_n=5, rights_registry=_rights_registry())
    rendered = render_readiness_impact_preview(preview)

    assert preview.status == "changes_detected"
    assert preview.promotion_review is not None
    assert preview.promotion_review.promotion_count == 0
    assert "Promotion Evidence Review" in rendered
    assert "Technical readiness movement is not source-rights or provenance approval." in rendered
    assert "DCF price-source provenance is outside this fundamentals review" in rendered
    assert "Read-only: no files were created, modified, or deleted." in rendered
    assert "This preview does not make saved readiness current." in rendered
    assert "An intentional reviewed make readiness run remains the separate rebuild boundary." in rendered
    assert _file_manifest(tmp_path) == before
