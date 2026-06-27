import pandas as pd

from src.data_health_dcf_source_commands import dcf_source_loop_progress_strip_cards, dcf_source_loop_route_cards
from src.dcf_input_proof_queue import (
    build_dcf_input_proof_handoff,
    build_dcf_input_proof_queue,
    build_dcf_input_source_command_plan,
    build_dcf_input_source_review_rows,
    build_dcf_input_source_guard,
    render_dcf_input_proof_handoff,
    render_dcf_input_proof_queue,
    render_dcf_input_source_command_plan,
    render_dcf_input_source_guard,
    render_dcf_input_source_review_rows,
    summarize_missing_input_families,
)


def test_dcf_source_loop_route_cards_summarize_source_to_proof_path_without_unlocking():
    checklist = pd.DataFrame(
        [
            {
                "Step": "1. Select source-review batch",
                "State": "ready",
                "Next Safe Action": "make dcf-input-source-command-plan FAMILY=shares_outstanding TICKERS=AMD TOP_N=1",
                "Missing Or Manual Gate": "-",
                "Review Boundary": "Use a capped source-review scope before opening raw DCF rows.",
            },
            {
                "Step": "2. Fill reviewed source fields",
                "State": "needs_field_fills",
                "Next Safe Action": "Fill reviewed source fields; do not write canonical fundamentals.",
                "Missing Or Manual Gate": "source_file_or_url, source_date",
                "Review Boundary": "Evidence fields must be reviewed source values, not placeholders or inferred inputs.",
            },
            {
                "Step": "3. Run source guard",
                "State": "blocked",
                "Next Safe Action": "Finish source guard before validate/preview.",
                "Missing Or Manual Gate": "reviewed source fields",
                "Review Boundary": "Run the guard only after every required source field is reviewed.",
            },
            {
                "Step": "4. Validate and preview",
                "State": "blocked",
                "Next Safe Action": "Finish source guard before validate/preview.",
                "Missing Or Manual Gate": "ready_for_guard source row",
                "Review Boundary": "Validation, preview, and rejected-row reports must be reviewed before any apply decision.",
            },
            {
                "Step": "5. Apply, skip, or keep blocked",
                "State": "blocked",
                "Next Safe Action": "Choose apply_reviewed, skip_reviewed, or still_blocked after preview review.",
                "Missing Or Manual Gate": "explicit apply/skip/still-blocked decision",
                "Review Boundary": "Canonical data changes require an explicit reviewed decision; no automatic apply from the dashboard.",
            },
            {
                "Step": "6. Rebuild readiness and record proof",
                "State": "blocked",
                "Next Safe Action": "Finish validate, preview, apply/skip, and readiness comparison first.",
                "Missing Or Manual Gate": "validation_result, preview_result, apply_result",
                "Review Boundary": "Record proof only after rebuilt readiness, changed counts, source files, and generated-artifact review.",
            },
        ]
    )

    cards = dcf_source_loop_route_cards(checklist, "shares_outstanding")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["ROUTE 1", "ROUTE 2", "ROUTE 3", "STOP RULE"]
    assert "shares_outstanding: finish source review fields" in rendered
    assert "use reviewed source values only" in rendered
    assert "run guard before validate and preview" in rendered
    assert "validate, preview, then choose apply/skip" in rendered
    assert "rejected-row review and an explicit apply_reviewed, skip_reviewed, or still_blocked choice stay manual" in rendered
    assert "proof record comes last" in rendered
    assert "do not record supported until rebuilt readiness" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered


def test_dcf_source_loop_progress_strip_cards_show_current_gate_and_stop_rule():
    checklist = pd.DataFrame(
        [
            {
                "Step": "1. Select source-review batch",
                "State": "ready",
                "Next Safe Action": "make dcf-input-source-command-plan FAMILY=shares_outstanding TICKERS=AMD TOP_N=1",
                "Missing Or Manual Gate": "-",
                "Review Boundary": "Use a capped source-review scope before opening raw DCF rows.",
            },
            {
                "Step": "2. Fill reviewed source fields",
                "State": "needs_field_fills",
                "Next Safe Action": "Fill reviewed source fields; do not write canonical fundamentals.",
                "Missing Or Manual Gate": "source_file_or_url, source_date",
                "Review Boundary": "Evidence fields must be reviewed source values, not placeholders or inferred inputs.",
            },
            {
                "Step": "6. Rebuild readiness and record proof",
                "State": "blocked",
                "Next Safe Action": "Finish validate, preview, apply/skip, and readiness comparison first.",
                "Missing Or Manual Gate": "validation_result, preview_result, apply_result",
                "Review Boundary": "Record proof only after rebuilt readiness, changed counts, source files, and generated-artifact review.",
            },
        ]
    )

    cards = dcf_source_loop_progress_strip_cards(checklist, "shares_outstanding")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "WHERE AM I",
        "REVIEWED EVIDENCE",
        "NEXT SAFE ACTION",
        "STOP RULE",
    ]
    assert "shares_outstanding: 1/3 source-loop steps ready" in rendered
    assert "current gate: 2. fill reviewed source fields" in rendered
    assert "source_file_or_url, source_date" in rendered
    assert "evidence fields must be reviewed source values, not placeholders" in rendered
    assert "commands stay copy-only and dry-run-first" in rendered
    assert "do not record proof early" in rendered
    assert "validate, preview, rejected-row review, apply/skip" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered


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
    assert by_ticker["META"].source_mode == "price dry-run first; PROVIDER=auto tries Stooq, Yahoo, optional IBKR read-only, and configured FMP/Alpha Vantage/Finnhub"
    assert "make price-refresh TICKERS=META PROVIDER=auto" == by_ticker["META"].next_safe_command
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


def test_dcf_input_queue_uses_session_preflight_to_mark_sec_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "research@example.com")
    (tmp_path / "outputs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "outputs" / "session_source_preflight.json").write_text(
        """{
  "sources": {
    "sec": {"status": "unavailable"}
  }
}
""",
        encoding="utf-8",
    )

    rows = build_dcf_input_proof_queue(
        root=tmp_path,
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=10,
    )
    by_ticker = {row.ticker: row for row in rows}

    assert by_ticker["AMD"].source_mode == (
        "fundamentals source ladder without SEC in this session; yfinance status unknown; "
        "FMP status unknown; Alpha Vantage status unknown; Finnhub status unknown"
    )


def test_dcf_input_queue_deprioritizes_share_blockers_when_session_cannot_fix_shares(tmp_path, monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "research@example.com")
    (tmp_path / "outputs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "outputs" / "session_source_preflight.json").write_text(
        """{
  "sources": {
    "sec": {"status": "unavailable"},
    "yfinance_stage": {"status": "unavailable", "reason_code": "probe_failed"},
    "fmp": {"status": "unavailable", "reason_code": "provider_key_missing"},
    "alpha_vantage": {"status": "unavailable", "reason_code": "provider_key_missing"},
    "local_fundamentals": {"share_count_fixable_ticker_count": 0}
  }
}
""",
        encoding="utf-8",
    )

    rows = build_dcf_input_proof_queue(
        root=tmp_path,
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=10,
    )

    assert rows[0].ticker == "HOOD"
    assert rows[0].missing_input_family == "fundamentals_bundle"


def test_dcf_input_queue_deprioritizes_reviewed_non_actionable_blockers(tmp_path, monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "research@example.com")
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "reviewed_batch_proofs.csv").write_text(
        "batch_id,review_date,reviewer,lane,scope,tickers,command_run,validation_result,"
        "preview_result,apply_result,pre_run_readiness_snapshot,post_run_readiness_snapshot,"
        "changed_readiness_counts,changed_tickers,source_files,generated_artifacts_reviewed,"
        "final_outcome,notes\n"
        "RB-PAYC,2026-06-27,local reviewer,fundamentals,reviewed scope,PAYC,"
        "make focus-fundamentals TICKER=PAYC,passed,valid,not_applied,before,after,"
        "none,none,data/imports/fundamentals.csv,excluded,still_blocked,"
        "zero revenue keeps fcf_margin blocked\n",
        encoding="utf-8",
    )

    rows = build_dcf_input_proof_queue(
        root=tmp_path,
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=10,
    )
    by_ticker = {row.ticker: row for row in rows}

    assert [row.ticker for row in rows[:3]] == ["AMD", "HOOD", "META"]
    assert rows[-1].ticker == "PAYC"
    assert "reviewed proof ledger already records" in by_ticker["PAYC"].source_note.lower()


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
    assert "FINAL_OUTCOME='<supported|candidate_context_only|still_blocked|skipped|excluded>'" in handoff.proof_record_scaffold
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


def test_dcf_input_source_command_plan_builds_copy_only_guard_sequence(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "research@example.com")

    queue = build_dcf_input_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=10,
    )
    plan = build_dcf_input_source_command_plan(queue, family="shares_outstanding")
    rendered = render_dcf_input_source_command_plan(plan).lower()

    assert [row.step for row in plan] == [
        "1. Open source-review intake",
        "2. Fill and run source guard",
        "3. Validate import rows",
        "4. Preview import merge",
        "5. Apply boundary",
        "6. Rebuild DCF proof",
        "7. Proof handoff",
    ]
    assert plan[0].command == "make dcf-input-source-review FAMILY=shares_outstanding TOP_N=10"
    assert plan[1].status == "blocked_until_reviewed_fields_filled"
    assert "make dcf-input-source-guard" in plan[1].command
    assert "TICKER=AMD" in plan[1].command
    assert "SHARES_OUTSTANDING='<reviewed_shares_outstanding>'" in plan[1].command
    assert plan[2].command == "make imports-validate"
    assert plan[3].command == "make imports-preview"
    assert plan[4].command == "make imports-apply"
    assert "do not run apply unless source proof" in plan[4].review_boundary.lower()
    assert plan[6].command == "make dcf-input-proof-handoff FAMILY=shares_outstanding TOP_N=10"
    assert "read-only" in rendered
    assert "research-only" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered


def test_dcf_input_source_command_plan_blocks_empty_family():
    plan = build_dcf_input_source_command_plan([], family="shares_outstanding")
    rendered = render_dcf_input_source_command_plan(plan).lower()

    assert len(plan) == 1
    assert plan[0].status == "blocked"
    assert plan[0].command == "make dcf-input-proof-queue TOP_N=10"
    assert "no source-review command can be built" in plan[0].review_boundary.lower()
    assert "does not apply imports" in rendered


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
