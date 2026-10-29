"""Synthetic contract tests for the read-only issuer/security candidate bridge."""

from __future__ import annotations


def _directory_report(row_count: int = 1) -> dict:
    return {
        "status": "validated_receipts",
        "inspection_only": True,
        "import_status": "held",
        "rights_status": "unreviewed",
        "source_created_at": "2026-10-26T21:31",
        "observed_at_utc": "2026-10-27T02:17:14Z",
        "total_non_test_symbols": row_count,
        "sources": [
            {
                "source": "nasdaq",
                "last_modified": "Tue, 27 Oct 2026 01:31:42 GMT",
                "source_created_at": "2026-10-26T21:31",
                "observed_at_utc": "2026-10-27T02:17:14Z",
                "sha256": "a" * 64,
            },
            {
                "source": "other",
                "last_modified": "Tue, 27 Oct 2026 01:31:42 GMT",
                "source_created_at": "2026-10-26T21:31",
                "observed_at_utc": "2026-10-27T02:17:14Z",
                "sha256": "b" * 64,
            },
        ],
    }


def _sec_report(
    last_modified: str = "2026-10-27T00:00:00Z",
    *,
    row_count: int = 1,
    distinct_cik_count: int = 1,
) -> dict:
    return {
        "status": "validated_receipt",
        "inspection_only": True,
        "safe_to_import": False,
        "url": "https://www.sec.gov/files/company_tickers_exchange.json",
        "sha256": "c" * 64,
        "last_modified_at_utc": last_modified,
        "observed_at_utc": "2026-10-27T01:00:00Z",
        "row_count": row_count,
        "distinct_cik_count": distinct_cik_count,
        "rights_status": "unreviewed",
    }


def _directory_row(
    act: str,
    *,
    source: str = "nasdaq",
    venue: str = "",
    cqs: str = "",
    nasdaq: str = "",
) -> dict[str, str]:
    return {
        "act_symbol": act,
        "cqs_symbol": cqs,
        "nasdaq_symbol": nasdaq,
        "source": source,
        "exchange_code": venue,
        "market_category": "Q" if source == "nasdaq" else "",
        "etf": "N",
        "security_name": f"Synthetic {act}",
    }


def _sec_row(ticker: str, cik: int, exchange: str) -> dict[str, object]:
    return {"ticker": ticker, "cik": cik, "exchange": exchange, "name": "Synthetic issuer"}


def test_source_cutoff_mismatch_blocks_comparison_without_gap_or_queue():
    from src.issuer_security_bridge import build_issuer_security_bridge

    report = build_issuer_security_bridge(
        _directory_report(),
        [_directory_row("ALFA")],
        _sec_report("2026-10-23T21:00:38Z"),
        [_sec_row("ALFA", 1001, "Nasdaq")],
    )

    assert report["status"] == "cutoff_mismatch"
    assert report["comparison_performed"] is False
    assert report["comparison_counts"] is None
    assert report["review_queue"] == []
    assert report["review_queue_total_count"] is None
    assert report["source_alignment"] == {
        "basis": "http_last_modified_utc_calendar_date",
        "directory_date": "2026-10-27",
        "sec_date": "2026-10-23",
        "status": "mismatch",
        "simultaneous_cut_proven": False,
    }
    assert report["safe_to_import"] is False
    assert report["rights_status"] == "unreviewed"
    assert report["inputs"]["directory_receipts"][0]["source_created_at"] == "2026-10-26T21:31"
    assert report["inputs"]["directory_receipts"][0]["observed_at_utc"] == "2026-10-27T02:17:14Z"
    assert report["inputs"]["sec_receipt"]["observed_at_utc"] == "2026-10-27T01:00:00Z"


def test_same_date_separates_act_secondary_notation_and_missing_leads():
    from src.issuer_security_bridge import build_issuer_security_bridge

    directory_rows = [
        _directory_row("ALFA"),
        _directory_row("BETA", source="other", venue="N", cqs="ALT"),
        _directory_row("FICT.C", source="other", venue="N"),
        _directory_row("ORPH", source="other", venue="A"),
    ]
    sec_rows = [
        _sec_row("ALFA", 1001, "Nasdaq"),
        _sec_row("ALT", 1002, "NYSE"),
        _sec_row("FICT-C", 1003, "NYSE"),
        _sec_row("MISSING", 1004, "OTC"),
    ]
    report = build_issuer_security_bridge(
        _directory_report(4), directory_rows,
        _sec_report(row_count=4, distinct_cik_count=4), sec_rows,
    )

    assert report["status"] == "same_date_inspection"
    assert report["comparison_performed"] is True
    assert report["source_alignment"]["simultaneous_cut_proven"] is False
    assert report["comparison_counts"] == {
        "exact_act_leads": 1,
        "secondary_symbol_leads": 1,
        "notation_leads": 1,
        "ambiguous_directory_symbols": 0,
        "sec_ticker_conflicts": 0,
        "no_directory_counterpart": 1,
        "venue_concordant_exact_act": 1,
        "venue_conflicts": 0,
        "venue_unmapped": 0,
        "directory_rows_without_sec_lead": 1,
        "ciks_with_multiple_tickers": 0,
    }
    assert {(row["ticker"], row["reason"]) for row in report["review_queue"]} == {
        ("ALT", "secondary_symbol_lead"),
        ("FICT-C", "notation_lead"),
        ("MISSING", "no_directory_counterpart"),
    }
    assert report["review_queue_total_count"] == 3
    assert report["safe_to_import"] is False
    assert report["withheld_fields"] == [
        "issuer_identity", "security_identity", "issuer_domicile",
        "security_type", "active_status", "point_in_time_membership",
        "financial_coverage", "analysis_eligibility",
    ]


def test_competing_symbol_fields_on_distinct_rows_are_queued_as_ambiguous():
    from src.issuer_security_bridge import build_issuer_security_bridge

    report = build_issuer_security_bridge(
        _directory_report(2),
        [
            _directory_row("ONE", source="other", venue="N", cqs="CROSS"),
            _directory_row("TWO", source="other", venue="N", nasdaq="CROSS"),
        ],
        _sec_report(),
        [_sec_row("CROSS", 2001, "NYSE")],
    )

    assert report["comparison_counts"]["ambiguous_directory_symbols"] == 1
    assert report["comparison_counts"]["secondary_symbol_leads"] == 0
    assert report["review_queue"][0]["reason"] == "ambiguous_directory_symbol"
    assert report["review_queue"][0]["candidate_act_symbols"] == ["ONE", "TWO"]
    assert report["safe_to_import"] is False


def test_exact_symbol_and_distinct_punctuation_counterpart_are_ambiguous():
    from src.issuer_security_bridge import build_issuer_security_bridge

    report = build_issuer_security_bridge(
        _directory_report(2),
        [
            _directory_row("AB-PD", source="other", venue="N"),
            _directory_row("AB$D", source="other", venue="N"),
        ],
        _sec_report(),
        [_sec_row("AB-PD", 2001, "NYSE")],
    )

    assert report["comparison_counts"]["ambiguous_directory_symbols"] == 1
    assert report["comparison_counts"]["exact_act_leads"] == 0
    assert report["review_queue"][0]["candidate_act_symbols"] == ["AB$D", "AB-PD"]


def test_reused_sec_ticker_across_ciks_is_conflict_not_one_security():
    from src.issuer_security_bridge import build_issuer_security_bridge

    report = build_issuer_security_bridge(
        _directory_report(), [_directory_row("ALFA")],
        _sec_report(row_count=2, distinct_cik_count=2),
        [_sec_row("ALFA", 1001, "Nasdaq"), _sec_row("ALFA", 2002, "Nasdaq")],
    )

    assert report["comparison_counts"]["sec_ticker_conflicts"] == 1
    assert report["comparison_counts"]["exact_act_leads"] == 0
    assert report["comparison_counts"]["directory_rows_without_sec_lead"] == 0
    assert report["review_queue"][0]["reason"] == "sec_ticker_conflict"
    assert report["review_queue"][0]["candidate_ciks"] == [1001, 2002]


def test_multiple_tickers_for_one_cik_remain_distinct_symbol_leads():
    from src.issuer_security_bridge import build_issuer_security_bridge

    report = build_issuer_security_bridge(
        _directory_report(2), [_directory_row("ALFA"), _directory_row("BETA")],
        _sec_report(row_count=2, distinct_cik_count=1),
        [_sec_row("ALFA", 1001, "Nasdaq"), _sec_row("BETA", 1001, "Nasdaq")],
    )

    assert report["comparison_counts"]["exact_act_leads"] == 2
    assert report["comparison_counts"]["ciks_with_multiple_tickers"] == 1
    assert report["comparison_counts"]["sec_ticker_conflicts"] == 0


def test_unknown_and_conflicting_venues_require_review():
    from src.issuer_security_bridge import build_issuer_security_bridge

    report = build_issuer_security_bridge(
        _directory_report(2), [_directory_row("ALFA"), _directory_row("BETA")],
        _sec_report(row_count=2, distinct_cik_count=2),
        [_sec_row("ALFA", 1001, "Unrecognized Venue"), _sec_row("BETA", 1002, "NYSE")],
    )

    assert report["comparison_counts"]["exact_act_leads"] == 2
    assert report["comparison_counts"]["venue_unmapped"] == 1
    assert report["comparison_counts"]["venue_conflicts"] == 1
    assert {(row["ticker"], row["reason"]) for row in report["review_queue"]} == {
        ("ALFA", "venue_unmapped"), ("BETA", "venue_conflict")
    }


def test_txse_code_is_compared_to_directory_f_without_identity_promotion():
    from src.issuer_security_bridge import build_issuer_security_bridge

    report = build_issuer_security_bridge(
        _directory_report(), [_directory_row("ALFA", source="other", venue="F")],
        _sec_report(), [_sec_row("ALFA", 1001, "TXSE")],
    )

    assert report["comparison_counts"]["venue_concordant_exact_act"] == 1
    assert report["comparison_counts"]["venue_unmapped"] == 0
    assert report["safe_to_import"] is False


def test_queue_is_bounded_and_prioritizes_ambiguity_over_missing_symbols():
    from src.issuer_security_bridge import build_issuer_security_bridge

    rows = [
        _directory_row("ONE", source="other", venue="N", cqs="CROSS"),
        _directory_row("TWO", source="other", venue="N", cqs="CROSS"),
    ]
    sec_rows = [
        _sec_row("ZZZ", 1001, "OTC"),
        _sec_row("CROSS", 1002, "NYSE"),
    ]
    full = build_issuer_security_bridge(
        _directory_report(2), rows,
        _sec_report(row_count=2, distinct_cik_count=2), sec_rows,
        top_n=20,
    )
    short = build_issuer_security_bridge(
        _directory_report(2), rows,
        _sec_report(row_count=2, distinct_cik_count=2), sec_rows,
        top_n=1,
    )

    assert full["review_queue_total_count"] == 2
    assert short["review_queue_total_count"] == 2
    assert short["review_queue"] == full["review_queue"][:1]
    assert short["review_queue"][0]["reason"] == "ambiguous_directory_symbol"


def test_reported_row_count_mismatch_is_rejected_before_comparison():
    import pytest
    from src.issuer_security_bridge import build_issuer_security_bridge

    with pytest.raises(ValueError, match="directory_count_mismatch"):
        build_issuer_security_bridge(
            _directory_report(2), [_directory_row("ALFA")],
            _sec_report(), [_sec_row("ALFA", 1001, "Nasdaq")],
        )


def test_unvalidated_receipt_status_is_rejected():
    import pytest
    from src.issuer_security_bridge import build_issuer_security_bridge

    sec_report = _sec_report()
    sec_report["status"] = "unverified"
    with pytest.raises(ValueError, match="sec_receipt_invalid"):
        build_issuer_security_bridge(
            _directory_report(), [_directory_row("ALFA")],
            sec_report, [_sec_row("ALFA", 1001, "Nasdaq")],
        )


def test_distinct_cik_receipt_count_must_match_actual_rows():
    import pytest
    from src.issuer_security_bridge import build_issuer_security_bridge

    with pytest.raises(ValueError, match="sec_cik_count_mismatch"):
        build_issuer_security_bridge(
            _directory_report(), [_directory_row("ALFA")],
            _sec_report(distinct_cik_count=2),
            [_sec_row("ALFA", 1001, "Nasdaq")],
        )
