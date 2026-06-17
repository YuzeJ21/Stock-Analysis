import pandas as pd

from src.dcf_input_proof_queue import (
    build_dcf_input_proof_handoff,
    build_dcf_input_proof_queue,
    build_dcf_input_source_review_rows,
    build_dcf_input_source_guard,
    render_dcf_input_proof_handoff,
    render_dcf_input_proof_queue,
    render_dcf_input_source_guard,
    render_dcf_input_source_review_rows,
    summarize_missing_input_families,
)


def _sample_universe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"ticker": "AMD", "asset_type": "company", "in_active_universe": True},
            {"ticker": "HOOD", "asset_type": "company", "in_active_universe": True},
            {"ticker": "META", "asset_type": "company", "in_active_universe": False},
            {"ticker": "PAYC", "asset_type": "company", "in_active_universe": False},
            {"ticker": "NVDA", "asset_type": "company", "in_active_universe": True},
            {"ticker": "QQQ", "asset_type": "etf", "in_active_universe": True},
        ]
    )


def _sample_fundamentals() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"ticker": "AMD", "revenue": 100, "free_cash_flow": 20, "fcf_margin": 0.2},
            {"ticker": "HOOD", "shares_outstanding": 20},
            {"ticker": "META", "revenue": 100, "free_cash_flow": 20, "fcf_margin": 0.2, "shares_outstanding": 10},
            {"ticker": "PAYC", "revenue": 0, "free_cash_flow": 12, "shares_outstanding": 5},
            {"ticker": "NVDA", "revenue": 120, "free_cash_flow": 30, "fcf_margin": 0.25, "shares_outstanding": 10},
            {"ticker": "QQQ", "revenue": 1, "free_cash_flow": 1, "fcf_margin": 1, "shares_outstanding": 1},
        ]
    )


def _sample_prices() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"ticker": "AMD", "date": "2026-01-01", "close": 100},
            {"ticker": "HOOD", "date": "2026-01-01", "close": 25},
            {"ticker": "NVDA", "date": "2026-01-01", "close": 200},
            {"ticker": "PAYC", "date": "2026-01-01", "close": 50},
            {"ticker": "QQQ", "date": "2026-01-01", "close": 500},
        ]
    )


def test_dcf_input_queue_classifies_exact_missing_input_families(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "research@example.com")

    rows = build_dcf_input_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=10,
    )
    by_ticker = {row.ticker: row for row in rows}

    assert [row.ticker for row in rows[:2]] == ["AMD", "HOOD"]
    assert by_ticker["AMD"].missing_input_family == "shares_outstanding"
    assert by_ticker["AMD"].dcf_input_status == "single-input blocker: shares_outstanding"
    assert by_ticker["AMD"].next_safe_command == "make share-count-proof-queue TICKERS=AMD"
    assert by_ticker["AMD"].proof_packet_command == "DRY_RUN=1 make reviewed-batch LANE=share_count TICKERS=AMD"
    assert by_ticker["HOOD"].missing_input_family == "fundamentals_bundle"
    assert by_ticker["PAYC"].missing_input_family == "fcf_margin"
    assert by_ticker["META"].missing_input_family == "price"
    assert by_ticker["META"].source_mode == "price dry-run first"
    assert "make price-worklist TICKERS=META" == by_ticker["META"].next_safe_command
    assert "NVDA" not in by_ticker
    assert "QQQ" not in by_ticker


def test_dcf_input_queue_respects_top_n_and_ticker_scope(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)

    rows = build_dcf_input_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=1,
        tickers=["PAYC", "AMD"],
    )

    assert [row.ticker for row in rows] == ["AMD"]
    assert "trusted-local/manual" in rows[0].source_mode


def test_dcf_input_queue_family_summary_counts_rows(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "research@example.com")

    rows = build_dcf_input_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=10,
    )

    summary = summarize_missing_input_families(rows)

    assert "shares_outstanding: 1" in summary
    assert "fundamentals_bundle: 1" in summary
    assert "fcf_margin: 1" in summary
    assert "price: 1" in summary


def test_dcf_input_queue_renderer_keeps_research_only_boundaries(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "research@example.com")

    rows = build_dcf_input_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=3,
    )
    rendered = render_dcf_input_proof_queue(rows)
    lowered = rendered.lower()

    assert "dcf input proof queue" in lowered
    assert "read-only" in lowered
    assert "research-only" in lowered
    assert "not investment advice" in lowered
    assert "direct buy/sell instruction" in lowered
    assert "do not infer prices, revenue, free cash flow" in lowered
    assert "validate -> preview -> rejected-row review -> apply" in lowered
    assert "make share-count-proof-queue tickers=amd" in lowered
    assert "make focus-fundamentals ticker=hood" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered
    assert "undervalued" not in lowered


def test_dcf_input_queue_empty_scope_explains_no_blockers(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "research@example.com")

    rows = build_dcf_input_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=10,
        tickers=["NVDA"],
    )

    assert rows == []
    assert "No company DCF input blockers found" in render_dcf_input_proof_queue(rows)


def test_dcf_input_handoff_builds_copy_only_proof_record_scaffold(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "research@example.com")

    rows = build_dcf_input_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=10,
    )
    handoff = build_dcf_input_proof_handoff(rows, family="shares_outstanding")
    rendered = render_dcf_input_proof_handoff(handoff).lower()

    assert handoff.input_family == "shares_outstanding"
    assert handoff.lane == "share_count"
    assert handoff.proof_packet_command == "DRY_RUN=1 make reviewed-batch LANE=share_count TICKERS=AMD"
    assert handoff.validation_command == "make imports-validate"
    assert handoff.preview_command == "make imports-preview"
    assert "dry_run=1 make reviewed-batch-proof-record" in handoff.proof_record_scaffold.lower()
    assert "FINAL_OUTCOME='<supported|still_blocked|skipped|excluded>'" in handoff.proof_record_scaffold
    assert "COMMAND_RUN='DRY_RUN=1 make reviewed-batch LANE=share_count TICKERS=AMD'" in handoff.proof_record_scaffold
    assert "copy-only sequence" in rendered
    assert "read-only" in rendered
    assert "research-only" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered


def test_dcf_input_handoff_defaults_to_top_family_not_mixed_batch(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "research@example.com")

    rows = build_dcf_input_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=10,
    )
    handoff = build_dcf_input_proof_handoff(rows)

    assert handoff.input_family == "shares_outstanding"
    assert handoff.tickers == "AMD"
    assert handoff.proof_packet_command == "DRY_RUN=1 make reviewed-batch LANE=share_count TICKERS=AMD"
    assert "HOOD" not in handoff.proof_packet_command
    assert "PAYC" not in handoff.proof_packet_command


def test_dcf_input_handoff_keeps_missing_family_blocked():
    handoff = build_dcf_input_proof_handoff([], family="shares_outstanding")
    rendered = render_dcf_input_proof_handoff(handoff).lower()

    assert handoff.selected_rows == 0
    assert handoff.tickers == "<reviewed_tickers>"
    assert "do not record proof until required fields replace placeholders" in handoff.record_boundary
    assert "stop if the selected dcf input family has no queued blockers" in rendered


def test_dcf_input_source_review_rows_show_required_field_fills(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "research@example.com")

    queue = build_dcf_input_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=10,
    )
    rows = build_dcf_input_source_review_rows(queue, family="shares_outstanding")
    rendered = render_dcf_input_source_review_rows(rows).lower()

    assert len(rows) == 1
    row = rows[0]
    assert row.ticker == "AMD"
    assert row.input_family == "shares_outstanding"
    assert row.target_file == "data/imports/fundamentals.csv"
    assert row.completion_status == "needs_field_fills"
    assert "source_file_or_url" in row.missing_review_fields
    assert "validation_result" in row.missing_review_fields
    assert "shares_outstanding" in row.import_row_scaffold
    assert "<reviewed_shares_outstanding>" in row.import_row_scaffold
    assert "dcf input source review intake" in rendered
    assert "read-only" in rendered
    assert "source review proves data readiness" in rendered
    assert "do not infer revenue" in rendered
    assert "validate -> preview -> rejected-row review -> apply decision" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered


def test_dcf_input_source_review_defaults_to_top_family_not_mixed(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "research@example.com")

    queue = build_dcf_input_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=10,
    )
    rows = build_dcf_input_source_review_rows(queue)

    assert [row.ticker for row in rows] == ["AMD"]
    assert {row.input_family for row in rows} == {"shares_outstanding"}


def test_dcf_input_source_guard_blocks_placeholders_and_missing_values():
    guard = build_dcf_input_source_guard(ticker="AMD", input_family="shares_outstanding", missing_dcf_fields="shares_outstanding")
    rendered = render_dcf_input_source_guard(guard).lower()

    assert guard.status == "blocked"
    assert "source_file_or_url" in guard.blocking_reasons
    assert "shares_outstanding" in guard.blocking_reasons
    assert guard.csv_row == ""
    assert "blocked until reviewed fields are complete" in rendered
    assert "read-only" in rendered
    assert "broker integration" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered


def test_dcf_input_source_guard_previews_import_row_when_reviewed():
    guard = build_dcf_input_source_guard(
        ticker="AMD",
        input_family="shares_outstanding",
        missing_dcf_fields="shares_outstanding",
        period="FY2025",
        shares_outstanding="123456789",
        source_file_or_url="https://www.sec.gov/example",
        source_as_of_date="2026-02-20",
        reviewer="local reviewer",
        review_date="2026-06-17",
        source_proof_status="reviewed",
        validation_result="pass",
        preview_result="reviewed",
        apply_decision="skipped_after_review",
    )
    rendered = render_dcf_input_source_guard(guard)

    assert guard.status == "ready_for_validate_preview"
    assert guard.blocking_reasons == ()
    assert guard.csv_header == "ticker,period,revenue,free_cash_flow,fcf_margin,shares_outstanding,source,as_of_date"
    assert guard.csv_row == "AMD,FY2025,,,,123456789,https://www.sec.gov/example,2026-02-20"
    assert "Run make imports-apply only after imports-preview" in guard.apply_boundary
    assert "CSV row: AMD,FY2025,,,,123456789,https://www.sec.gov/example,2026-02-20" in rendered
