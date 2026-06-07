import json
import os
from pathlib import Path
import sys

import pandas as pd
import pytest

import src.project_status as project_status
from src.project_status import build_project_status_payload, main, write_project_status_output


def _write_minimal_local_data(root: Path) -> None:
    data_dir = root / "data"
    outputs_dir = root / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    (root / "config.yaml").write_text(Path("config.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    pd.DataFrame(
        [
            {"ticker": "NVDA", "date": "2026-01-01", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1000},
            {"ticker": "NVDA", "date": "2026-01-02", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 1100},
        ]
    ).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame([{"ticker": "NVDA", "theme": "AI", "sectoretf": "SMH", "defaultpurpose": "Momentum Leader"}]).to_csv(
        data_dir / "universe.csv",
        index=False,
    )
    pd.DataFrame([{"ticker": "NVDA", "shares": 1, "primarypurpose": "Momentum Leader"}]).to_csv(
        data_dir / "holdings.csv",
        index=False,
    )
    pd.DataFrame([{"ticker": "NVDA", "theme": "AI"}]).to_csv(data_dir / "fundamentals.csv", index=False)


def _write_fast_status_artifacts(root: Path) -> None:
    data_dir = root / "data"
    reports_dir = data_dir / "reports"
    outputs_dir = root / "outputs"
    reports_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    (root / "config.yaml").write_text(Path("config.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    pd.DataFrame(
        [
            {"ticker": "NVDA", "price_ready": True, "momentum_ready": True, "dcf_ready": True, "peer_ready": False},
            {"ticker": "AMD", "price_ready": False, "momentum_ready": False, "dcf_ready": False, "peer_ready": False},
        ]
    ).to_csv(reports_dir / "ticker_readiness_report.csv", index=False)
    pd.DataFrame(
        [
            {"dataset": "prices", "availability_status": "available", "focus_command": "make status"},
            {"dataset": "fundamentals", "availability_status": "partial", "focus_command": "make imports-validate"},
        ]
    ).to_csv(outputs_dir / "data_source_status.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "fundamentals",
                "ticker": "AMD",
                "status": "partial",
                "recommended_action": "Run make focus-fundamentals TICKER=AMD.",
            }
        ]
    ).to_csv(outputs_dir / "data_gap_report.csv", index=False)
    pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "dataset": "fundamentals",
                "status": "missing",
                "reason": "Missing trusted fundamentals.",
                "recommended_action": "Run make focus-fundamentals TICKER=AMD.",
                "focus_command": "make focus-fundamentals TICKER=AMD",
                "example_command": "make sec-stage TICKERS=AMD",
            }
        ]
    ).to_csv(outputs_dir / "data_onboarding_actions.csv", index=False)
    pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "broader_queue",
                "ticker_count": 1,
                "tickers": "AMD",
                "runbook_shortcut_command": "make runbook-fundamentals-broader",
                "goal_summary": "Advance trusted fundamentals.",
            }
        ]
    ).to_csv(outputs_dir / "command_bundles.csv", index=False)
    pd.DataFrame(
        [
            {"Step": "Fix top fundamentals blocker", "Command": "make focus-fundamentals TICKER=AMD", "Reason": "Missing trusted fundamentals."}
        ]
    ).to_csv(outputs_dir / "project_status_next_steps.csv", index=False)


def test_project_status_payload_is_read_only_and_summarizes_local_gaps(tmp_path: Path):
    _write_minimal_local_data(tmp_path)

    payload = build_project_status_payload(tmp_path, top_n=3)

    assert payload["summary"]["data_sources_total"] >= 1
    assert payload["summary"]["tickers_total"] == 1
    assert payload["summary"]["tickers_with_prices"] == 1
    assert len(payload["top_onboarding_actions"]) <= 3
    assert payload["top_onboarding_actions"][0]["focus_command"] == "make focus-price TICKER=NVDA"
    assert payload["top_onboarding_actions"][0]["example_command"] == "make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual"
    assert payload["recommended_next_command_rows"][0]["Command"] == "make focus-price TICKER=NVDA"
    assert "make runbook-prices" in payload["recommended_next_commands"]
    assert "make verify" in payload["recommended_next_commands"]
    assert not (tmp_path / "outputs" / "project_status.json").exists()


def test_project_status_prefers_central_readiness_dcf_count(tmp_path: Path):
    _write_minimal_local_data(tmp_path)
    reports_dir = tmp_path / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"ticker": "NVDA", "dcf_ready": False},
            {"ticker": "AMD", "dcf_ready": True},
        ]
    ).to_csv(reports_dir / "ticker_readiness_report.csv", index=False)

    payload = build_project_status_payload(tmp_path, top_n=3)

    assert payload["summary"]["tickers_dcf_ready"] == 1


def test_project_status_payload_respects_ticker_slice_for_read_only_views(tmp_path: Path):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    pd.DataFrame(
        [
            {"ticker": "NVDA", "date": "2026-01-01", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1000},
            {"ticker": "NVDA", "date": "2026-01-02", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 1100},
        ]
    ).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "NVDA", "theme": "AI", "sectoretf": "SMH", "defaultpurpose": "Momentum Leader"},
            {"ticker": "AMD", "theme": "AI", "sectoretf": "SMH", "defaultpurpose": "Momentum Leader"},
        ]
    ).to_csv(data_dir / "universe.csv", index=False)
    pd.DataFrame([{"ticker": "NVDA", "shares": 1, "primarypurpose": "Momentum Leader"}]).to_csv(
        data_dir / "holdings.csv",
        index=False,
    )
    pd.DataFrame([{"ticker": "NVDA", "theme": "AI"}]).to_csv(data_dir / "fundamentals.csv", index=False)

    payload = build_project_status_payload(tmp_path, top_n=5, tickers=["nvda"])

    assert payload["summary"]["tickers_total"] == 1
    assert payload["summary"]["onboarding_actions"] >= 1
    assert all(row["ticker"] == "NVDA" for row in payload["top_onboarding_actions"])
    assert all(row["ticker"] == "NVDA" for row in payload["top_data_gaps"])
    assert payload["recommended_next_command_rows"][0]["Command"] == "make focus-price TICKER=NVDA"


def test_project_status_prefers_live_price_status_context_for_price_actions(tmp_path: Path):
    _write_minimal_local_data(tmp_path)
    pd.DataFrame(
        [
            {
                "run_timestamp": "2026-05-21T00:00:00+00:00",
                "ticker": "NVDA",
                "requested_start": "",
                "requested_end": "2026-05-21",
                "provider": "FakePriceSource",
                "status": "parse_error",
                "rows_fetched": 0,
                "rows_merged": 0,
                "error_category": "parse_error",
                "error_message": "NVDA: parse failed",
                "fallback_used": True,
                "recommended_action": "Run make focus-price TICKER=NVDA first. For batch planning, preview make price-refresh-loop DRY_RUN=1; if you choose to refresh this ticker, run make price-refresh TICKERS=NVDA; if the free refresh path fails, normalize verified downloaded OHLCV files into data/imports/prices.csv.",
                "focus_command": "make focus-price TICKER=NVDA",
                "example_command": "make onboarding",
                "target_file": "data/imports/prices.csv",
            }
        ]
    ).to_csv(tmp_path / "outputs" / "price_update_status.csv", index=False)

    payload = build_project_status_payload(tmp_path, top_n=3)

    top_action = payload["top_onboarding_actions"][0]
    assert top_action["ticker"] == "NVDA"
    assert top_action["status"] == "parse_error"
    assert top_action["reason"] == "NVDA: parse failed"
    assert top_action["example_command"] == "make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual"
    assert payload["recommended_next_command_rows"][0]["Reason"] == "NVDA: parse failed"
    assert payload["recommended_next_command_rows"][0]["SourceContext"] == "data/imports/prices.csv"
    assert payload["recommended_next_command_rows"][0]["FreshnessContext"] == "2026-05-21"


def test_project_status_does_not_let_successful_price_status_hide_remaining_price_work(tmp_path: Path):
    _write_minimal_local_data(tmp_path)
    pd.DataFrame(
        [
            {
                "run_timestamp": "2026-05-21T00:00:00+00:00",
                "ticker": "NVDA",
                "requested_start": "",
                "requested_end": "2026-05-21",
                "provider": "FakePriceSource",
                "status": "fetched",
                "rows_fetched": 1,
                "rows_merged": 1,
                "error_category": "",
                "error_message": "",
                "fallback_used": False,
                "recommended_action": "No action needed; remote rows were merged into local prices.",
                "focus_command": float("nan"),
                "example_command": float("nan"),
                "target_file": "data/prices.csv",
            }
        ]
    ).to_csv(tmp_path / "outputs" / "price_update_status.csv", index=False)

    payload = build_project_status_payload(tmp_path, top_n=3)

    top_action = payload["top_onboarding_actions"][0]
    assert top_action["ticker"] == "NVDA"
    assert top_action["recommended_action"].startswith("Run make focus-price TICKER=NVDA")
    assert top_action["focus_command"] == "make focus-price TICKER=NVDA"
    rendered_commands = " ".join(row["Command"] for row in payload["recommended_next_command_rows"])
    assert "nan" not in rendered_commands.lower()


def test_project_status_normalizes_legacy_raw_price_example_command(tmp_path: Path):
    _write_minimal_local_data(tmp_path)
    pd.DataFrame(
        [
            {
                "run_timestamp": "2026-05-21T00:00:00+00:00",
                "ticker": "NVDA",
                "requested_start": "",
                "requested_end": "2026-05-21",
                "provider": "FakePriceSource",
                "status": "parse_error",
                "rows_fetched": 0,
                "rows_merged": 0,
                "error_category": "parse_error",
                "error_message": "NVDA: parse failed",
                "fallback_used": True,
                "recommended_action": "Run make focus-price TICKER=NVDA first. For batch planning, preview make price-refresh-loop DRY_RUN=1; if you choose to refresh this ticker, run make price-refresh TICKERS=NVDA; if the free refresh path fails, normalize verified downloaded OHLCV files into data/imports/prices.csv.",
                "focus_command": "make focus-price TICKER=NVDA",
                "example_command": "python3 -m src.data_update --tickers NVDA",
                "target_file": "data/imports/prices.csv",
            }
        ]
    ).to_csv(tmp_path / "outputs" / "price_update_status.csv", index=False)

    payload = build_project_status_payload(tmp_path, top_n=3)

    top_action = payload["top_onboarding_actions"][0]
    assert top_action["example_command"] == "make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual"


def test_project_status_normalizes_legacy_raw_price_action_text(tmp_path: Path):
    _write_minimal_local_data(tmp_path)
    pd.DataFrame(
        [
            {
                "run_timestamp": "2026-05-21T00:00:00+00:00",
                "ticker": "NVDA",
                "requested_start": "",
                "requested_end": "2026-05-21",
                "provider": "FakePriceSource",
                "status": "parse_error",
                "rows_fetched": 0,
                "rows_merged": 0,
                "error_category": "parse_error",
                "error_message": "NVDA: parse failed",
                "fallback_used": True,
                "recommended_action": "Run make focus-price TICKER=NVDA, or run python3 -m src.data_update --tickers NVDA and normalize verified downloaded OHLCV files into data/imports/prices.csv.",
                "focus_command": "make focus-price TICKER=NVDA",
                "example_command": "make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual",
                "target_file": "data/imports/prices.csv",
            }
        ]
    ).to_csv(tmp_path / "outputs" / "price_update_status.csv", index=False)

    payload = build_project_status_payload(tmp_path, top_n=3)

    top_action = payload["top_onboarding_actions"][0]
    assert "make price-refresh-loop DRY_RUN=1" in top_action["recommended_action"]
    assert "make price-refresh TICKERS=NVDA" in top_action["recommended_action"]
    assert "python3 -m src.data_update --tickers NVDA" not in top_action["recommended_action"]


def test_project_status_surfaces_staged_fundamentals_follow_through_in_next_steps(tmp_path: Path):
    _write_minimal_local_data(tmp_path)
    imports_dir = tmp_path / "data" / "imports"
    imports_dir.mkdir()
    pd.DataFrame(
        [
            {
                "ticker": "AMD",
                "theme": "AI",
                "sector": "Semis",
                "revenue": 100,
                "revenue_growth": 0.2,
                "eps": 1.0,
                "free_cash_flow": 10,
                "fcf": 10,
                "fcf_margin": 0.1,
                "profit_margin": 0.2,
                "operating_margin": 0.15,
                "gross_margin": 0.3,
                "ebitda": 15,
                "cash": 20,
                "debt": 5,
                "net_debt": -15,
                "shares_outstanding": 100,
                "pe_ratio": 25,
                "trailing_pe": 24,
                "forward_pe": 22,
                "price_to_book": 3,
                "market_cap": 1000,
                "enterprise_value": 1020,
                "debt_to_equity": 0.4,
                "source": "sec_companyfacts",
                "as_of_date": "2025-12-31",
                "sec_cik": "1",
                "sec_form": "10-K",
                "sec_filed_date": "2026-02-01",
                "sec_accession": "0001",
                "sec_fact_warnings": "",
                "sec_entity_name": "AMD INC",
            }
        ]
    ).to_csv(imports_dir / "fundamentals.csv", index=False)

    payload = build_project_status_payload(tmp_path, top_n=4)

    commands = [row["Command"] for row in payload["recommended_next_command_rows"]]
    assert "make imports-validate" in commands
    staged_row = next(row for row in payload["recommended_next_command_rows"] if row["Command"] == "make imports-validate")
    assert staged_row["Step"] == "Review fundamentals import draft"
    assert "make imports-apply" in staged_row["Reason"]
    assert staged_row["SourceContext"] == "data/imports/fundamentals.csv"
    assert staged_row["FreshnessContext"]


def test_project_status_surfaces_fundamentals_input_path_when_sec_user_agent_missing(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "date": f"2026-01-{day:02d}",
                "open": 10 + day,
                "high": 11 + day,
                "low": 9 + day,
                "close": 10 + day,
                "volume": 1000 + day,
            }
            for day in range(1, 23)
        ]
    ).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame([{"ticker": "NVDA", "theme": "AI", "sectoretf": "SMH", "defaultpurpose": "Momentum Leader"}]).to_csv(
        data_dir / "universe.csv",
        index=False,
    )
    pd.DataFrame([{"ticker": "NVDA", "shares": 1, "primarypurpose": "Momentum Leader"}]).to_csv(
        data_dir / "holdings.csv",
        index=False,
    )
    pd.DataFrame([{"ticker": "NVDA", "theme": "AI"}]).to_csv(data_dir / "fundamentals.csv", index=False)

    payload = build_project_status_payload(tmp_path, top_n=5)

    input_path_row = next(
        row for row in payload["recommended_next_command_rows"] if row["Step"] == "Choose fundamentals input path"
    )
    assert input_path_row["Command"] == "make templates"
    assert "SEC_USER_AGENT is not configured" in input_path_row["Reason"]
    assert "data/imports/fundamentals.csv" in input_path_row["Reason"]
    assert input_path_row["SourceContext"] == "SEC_USER_AGENT or data/imports/fundamentals.csv"
    assert "credential/manual import state" in input_path_row["FreshnessContext"]


def test_project_status_combines_staged_fundamentals_and_peer_imports_into_one_follow_through(tmp_path: Path):
    _write_minimal_local_data(tmp_path)
    imports_dir = tmp_path / "data" / "imports"
    imports_dir.mkdir()
    pd.DataFrame(
        [
            {
                "ticker": "AMD",
                "theme": "AI",
                "sector": "Semis",
                "revenue": 100,
                "revenue_growth": 0.2,
                "eps": 1.0,
                "free_cash_flow": 10,
                "fcf": 10,
                "fcf_margin": 0.1,
                "profit_margin": 0.2,
                "operating_margin": 0.15,
                "gross_margin": 0.3,
                "ebitda": 15,
                "cash": 20,
                "debt": 5,
                "net_debt": -15,
                "shares_outstanding": 100,
                "pe_ratio": 25,
                "trailing_pe": 24,
                "forward_pe": 22,
                "price_to_book": 3,
                "market_cap": 1000,
                "enterprise_value": 1020,
                "debt_to_equity": 0.4,
                "source": "sec_companyfacts",
                "as_of_date": "2025-12-31",
                "sec_cik": "1",
                "sec_form": "10-K",
                "sec_filed_date": "2026-02-01",
                "sec_accession": "0001",
                "sec_fact_warnings": "",
                "sec_entity_name": "AMD INC",
            }
        ]
    ).to_csv(imports_dir / "fundamentals.csv", index=False)
    pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "peer_ticker": "AMD",
                "peer_group": "ai_semis",
                "sector": "Semis",
                "industry": "Semiconductors",
                "source": "manual",
                "as_of_date": "2026-05-22",
            }
        ]
    ).to_csv(imports_dir / "peers.csv", index=False)

    payload = build_project_status_payload(tmp_path, top_n=4)

    staged_rows = [row for row in payload["recommended_next_command_rows"] if row["Command"] == "make imports-validate"]
    assert len(staged_rows) == 1
    staged_row = staged_rows[0]
    assert staged_row["Step"] == "Review import drafts"
    assert "data/imports/fundamentals.csv" in staged_row["Reason"]
    assert "data/imports/peers.csv" in staged_row["Reason"]
    assert "fundamentals and peers" in staged_row["Reason"]
    assert "make imports-apply" in staged_row["Reason"]


def test_project_status_normalizes_legacy_parse_error_reason_from_price_status(tmp_path: Path):
    _write_minimal_local_data(tmp_path)
    pd.DataFrame(
        [
            {
                "run_timestamp": "2026-05-21T00:00:00+00:00",
                "ticker": "NVDA",
                "requested_start": "",
                "requested_end": "2026-05-21",
                "provider": "FakePriceSource",
                "status": "parse_error",
                "rows_fetched": 0,
                "rows_merged": 0,
                "error_category": "parse_error",
                "error_message": "NVDA: update failed (Error tokenizing data. C error: Expected 1 fields in line 6, saw 2\n)",
                "fallback_used": True,
                "recommended_action": "Retry later or use the manual price import draft workflow in data/imports/prices.csv.",
            }
        ]
    ).to_csv(tmp_path / "outputs" / "price_update_status.csv", index=False)

    payload = build_project_status_payload(tmp_path, top_n=3)

    assert payload["recommended_next_command_rows"][0]["Reason"] == "NVDA: provider rows could not be parsed cleanly (Expected 1 fields in line 6, saw 2)"


def test_project_status_write_output_persists_machine_readable_files(tmp_path: Path):
    _write_minimal_local_data(tmp_path)

    payload = write_project_status_output(tmp_path, top_n=3)
    outputs_dir = tmp_path / "outputs"

    json_path = outputs_dir / "project_status.json"
    summary_path = outputs_dir / "project_status_summary.csv"
    top_actions_path = outputs_dir / "project_status_top_actions.csv"
    next_steps_path = outputs_dir / "project_status_next_steps.csv"
    purpose_summary_path = outputs_dir / "purpose_evaluation_summary.csv"

    assert json_path.exists()
    assert summary_path.exists()
    assert top_actions_path.exists()
    assert next_steps_path.exists()
    assert purpose_summary_path.exists()
    assert payload["written_files"]["project_status_json"] == str(json_path)
    assert payload["written_files"]["purpose_evaluation_summary"] == str(purpose_summary_path)

    written_payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert written_payload["summary"]["tickers_total"] == 1

    summary_frame = pd.read_csv(summary_path)
    assert summary_frame.iloc[0]["tickers_total"] == 1

    actions_frame = pd.read_csv(top_actions_path)
    assert actions_frame.iloc[0]["focus_command"] == "make focus-price TICKER=NVDA"

    next_steps_frame = pd.read_csv(next_steps_path)
    assert next_steps_frame.iloc[0]["Command"] == "make focus-price TICKER=NVDA"
    assert "SourceContext" in next_steps_frame.columns
    assert "FreshnessContext" in next_steps_frame.columns
    assert next_steps_frame["SourceContext"].fillna("").str.len().gt(0).any()
    assert next_steps_frame["FreshnessContext"].fillna("").str.len().gt(0).any()


def test_project_status_human_output_surfaces_focus_and_exact_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _write_minimal_local_data(tmp_path)

    argv_before = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--top-n", "2"]
    try:
        main()
        output = capsys.readouterr().out.lower()
    finally:
        sys.argv = argv_before

    assert "top onboarding actions" in output
    assert "command: make price-normalize input=data/raw/prices/nvda.csv ticker=nvda source=yahoo_manual" in output
    assert "focus: make focus-fundamentals ticker=nvda" in output
    assert "command: make sec-stage tickers=nvda" in output
    assert "fix top prices blocker (nvda): make focus-price ticker=nvda" in output
    assert "no verified local price history is present for this ticker yet." in output or "at least 21 are needed" in output
    assert "source:" in output
    assert "freshness:" in output
    assert "open price coverage guided data batch: make runbook-prices" in output


def test_project_status_cli_check_uses_read_only_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _write_minimal_local_data(tmp_path)

    argv_before = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--check", "--top-n", "2"]
    try:
        main()
        output = capsys.readouterr().out.lower()
    finally:
        sys.argv = argv_before

    assert "project status summary" in output
    assert "wrote:" not in output


def test_project_status_cli_check_uses_fast_generated_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    _write_fast_status_artifacts(tmp_path)

    def fail_full_payload(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("status-check should use generated artifacts before full recomputation")

    monkeypatch.setattr(project_status, "build_project_status_payload", fail_full_payload)

    argv_before = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--check", "--top-n", "2"]
    try:
        main()
        output = capsys.readouterr().out
    finally:
        sys.argv = argv_before

    assert "Project status summary:" in output
    assert "Read-only project snapshot." in output
    assert "Read-only operator snapshot." not in output
    assert "Commands below are copy-only local research helpers" in output
    assert "Local folders:" in output
    assert "data: data" in output
    assert "outputs: outputs" in output
    assert str(tmp_path) not in output
    assert "Tickers with prices: 1/2" in output
    assert "DCF-ready tickers: 1/2" in output
    assert "make focus-fundamentals TICKER=AMD" in output
    assert "generated CSV churn" not in output
    assert "Wrote:" not in output


def test_project_status_fast_check_normalizes_stale_generated_price_actions(tmp_path: Path):
    _write_fast_status_artifacts(tmp_path)
    pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "dataset": "prices",
                "status": "missing_or_incomplete",
                "reason": "Only 2 verified local price rows are present.",
                "recommended_action": "Run make focus-price TICKER=AMD, or run make price-refresh TICKERS=AMD; if the free refresh path fails, normalize verified downloaded OHLCV files into data/imports/prices.csv.",
                "focus_command": "make focus-price TICKER=AMD",
                "example_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
            }
        ]
    ).to_csv(tmp_path / "outputs" / "data_onboarding_actions.csv", index=False)

    payload = project_status._fast_status_payload_from_outputs(tmp_path, top_n=5)

    assert payload is not None
    action = payload["top_onboarding_actions"][0]
    assert "make price-refresh-loop DRY_RUN=1" in action["recommended_action"]
    assert "if you choose to refresh this ticker, run make price-refresh TICKERS=AMD" in action["recommended_action"]
    assert "or run make price-refresh" not in action["recommended_action"]


def test_project_status_fast_check_normalizes_stale_generated_next_steps(tmp_path: Path):
    _write_fast_status_artifacts(tmp_path)
    pd.DataFrame(
        [
            {
                "Step": "Refresh next capped missing-price batch",
                "Command": "make price-refresh-loop DRY_RUN=1",
                "Reason": "Preview the broad-universe price frontier first.",
                "SourceContext": "data/imports/prices.csv fallback plus optional Yahoo refresh",
                "FreshnessContext": "dry-run first; verify source/freshness and generated CSV churn after any refresh",
            },
            {
                "Step": "Open Price Coverage Bundle (Broader Queue) runbook",
                "Command": "make runbook-prices-broader",
                "Reason": "Unlock Monthly Picks for 5 tickers across this bundle.",
                "SourceContext": "data/imports/prices.csv",
                "FreshnessContext": "bundle generated from current onboarding outputs",
            }
        ]
    ).to_csv(tmp_path / "outputs" / "project_status_next_steps.csv", index=False)

    payload = project_status._fast_status_payload_from_outputs(tmp_path, top_n=5)

    assert payload is not None
    command_row = payload["recommended_next_command_rows"][0]
    assert command_row["Step"] == "Refresh next capped missing-price batch"
    assert (
        command_row["FreshnessContext"]
        == "dry-run first; verify source/readiness notes and local CSV changes after any refresh"
    )
    assert "generated CSV churn" not in command_row["FreshnessContext"]
    guided_row = payload["recommended_next_command_rows"][1]
    assert guided_row["Step"] == "Open Price Coverage Guided Data Batch (Broader Queue)"
    assert guided_row["Reason"] == "Unlock Monthly Picks for 5 tickers across this guided data batch."
    assert guided_row["FreshnessContext"] == "guided batch generated from current onboarding outputs"


def test_project_status_fast_check_respects_ticker_filter(tmp_path: Path):
    _write_fast_status_artifacts(tmp_path)

    payload = project_status._fast_status_payload_from_outputs(tmp_path, top_n=5, tickers=["nvda"])

    assert payload is not None
    assert payload["summary"]["tickers_total"] == 1
    assert payload["summary"]["tickers_with_prices"] == 1
    assert payload["summary"]["onboarding_actions"] == 0
    assert payload["top_onboarding_actions"] == []


def test_project_status_fast_check_warns_when_source_csv_is_newer(tmp_path: Path):
    _write_fast_status_artifacts(tmp_path)
    readiness_path = tmp_path / "data" / "reports" / "ticker_readiness_report.csv"
    source_path = tmp_path / "data" / "peers.csv"
    source_path.write_text("ticker,peer_ticker,source\nNVDA,AMD,fixture\n", encoding="utf-8")
    old_time = 1_700_000_000
    new_time = old_time + 60
    os.utime(readiness_path, (old_time, old_time))
    os.utime(source_path, (new_time, new_time))

    payload = project_status._fast_status_payload_from_outputs(tmp_path, top_n=5)

    assert payload is not None
    assert payload["warnings"]
    assert "make readiness" in payload["warnings"][0]
    assert "data/peers.csv" in payload["warnings"][0]


def test_project_status_human_write_output_reports_written_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _write_minimal_local_data(tmp_path)

    argv_before = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--write-output", "--top-n", "2"]
    try:
        main()
        output = capsys.readouterr().out.lower()
    finally:
        sys.argv = argv_before

    assert "wrote:" in output
    assert "project_status.json" in output
    assert "project_status_summary.csv" in output


def test_project_status_refresh_artifacts_writes_supporting_operator_outputs(tmp_path: Path):
    _write_minimal_local_data(tmp_path)
    pd.DataFrame(
        [
            {
                "run_timestamp": "2026-05-21T00:00:00+00:00",
                "ticker": "AMD",
                "requested_start": "",
                "requested_end": "2026-05-21",
                "provider": "FakePriceSource",
                "status": "parse_error",
                "rows_fetched": 0,
                "rows_merged": 0,
                "error_category": "parse_error",
                "error_message": "AMD: parse failed",
                "fallback_used": True,
                "recommended_action": "Retry later or use the manual price import draft workflow in data/imports/prices.csv.",
            }
        ]
    ).to_csv(tmp_path / "outputs" / "price_update_status.csv", index=False)

    payload = write_project_status_output(tmp_path, top_n=2, refresh_supporting_outputs=True)
    outputs_dir = tmp_path / "outputs"

    assert (outputs_dir / "data_source_status.csv").exists()
    assert (outputs_dir / "data_gap_report.csv").exists()
    assert (outputs_dir / "ticker_data_coverage.csv").exists()
    assert (outputs_dir / "data_onboarding_actions.csv").exists()
    assert (outputs_dir / "data_quality_wizard.csv").exists()
    assert (outputs_dir / "liquidity_risk.csv").exists()
    assert (outputs_dir / "correlation_risk.csv").exists()
    assert (outputs_dir / "research_action_queue.csv").exists()
    assert (outputs_dir / "project_status.json").exists()
    refreshed_price_status = pd.read_csv(outputs_dir / "price_update_status.csv")
    assert refreshed_price_status.iloc[0]["focus_command"] == "make focus-price TICKER=AMD"
    assert refreshed_price_status.iloc[0]["target_file"] == "data/imports/prices.csv"
    assert payload["recommended_next_command_rows"][0]["Command"] == "make focus-price TICKER=NVDA"


def test_project_status_human_refresh_artifacts_keeps_cli_clean(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    _write_minimal_local_data(tmp_path)

    argv_before = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--refresh-artifacts", "--top-n", "2"]
    try:
        main()
        output = capsys.readouterr().out.lower()
    finally:
        sys.argv = argv_before

    assert "project status summary" in output
    assert "fix top prices blocker (nvda): make focus-price ticker=nvda" in output
    assert "wrote:" not in output
    assert (tmp_path / "outputs" / "project_status.json").exists()


def test_project_status_prefers_bundle_matching_top_blocker_ticker(tmp_path: Path):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "date": f"2026-01-{day:02d}",
                "open": 10 + day,
                "high": 11 + day,
                "low": 9 + day,
                "close": 10 + day,
                "volume": 1000 + day,
            }
            for day in range(1, 23)
        ]
    ).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "NVDA", "theme": "AI", "sectoretf": "SMH", "defaultpurpose": "Momentum Leader"},
            {"ticker": "AMD", "theme": "AI", "sectoretf": "SMH", "defaultpurpose": "Momentum Leader"},
        ]
    ).to_csv(data_dir / "universe.csv", index=False)
    pd.DataFrame([{"ticker": "NVDA", "shares": 1, "primarypurpose": "Momentum Leader"}]).to_csv(
        data_dir / "holdings.csv",
        index=False,
    )
    pd.DataFrame([{"ticker": "NVDA", "theme": "AI"}]).to_csv(data_dir / "fundamentals.csv", index=False)

    payload = build_project_status_payload(tmp_path, top_n=5)

    assert payload["top_onboarding_actions"][0]["ticker"] == "AMD"
    assert payload["recommended_next_command_rows"][0]["Step"] == "Refresh next capped missing-price batch"
    assert payload["recommended_next_command_rows"][0]["Command"] == "make price-refresh-loop DRY_RUN=1"
    assert (
        payload["recommended_next_command_rows"][0]["FreshnessContext"]
        == "dry-run first; verify source/readiness notes and local CSV changes after any refresh"
    )
    assert "generated CSV churn" not in payload["recommended_next_command_rows"][0]["FreshnessContext"]
    assert payload["recommended_next_command_rows"][2]["Step"] == "Open Price Coverage Guided Data Batch (Broader Queue)"
    assert payload["recommended_next_command_rows"][2]["Command"] == "make runbook-prices-broader"
    assert payload["recommended_next_command_rows"][2]["FreshnessContext"] == "guided batch generated from current onboarding outputs"


def test_project_status_prefers_holdings_first_price_blockers_when_priority_matches(tmp_path: Path):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {"ticker": "NVDA", "date": "2026-01-01", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1000},
            {"ticker": "NVDA", "date": "2026-01-02", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 1100},
        ]
    ).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "META", "theme": "AI", "sectoretf": "QQQ", "defaultpurpose": "Core Compounder"},
            {"ticker": "AMD", "theme": "AI", "sectoretf": "SMH", "defaultpurpose": "Momentum Leader"},
            {"ticker": "NVDA", "theme": "AI", "sectoretf": "SMH", "defaultpurpose": "Momentum Leader"},
        ]
    ).to_csv(data_dir / "universe.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "NVDA", "shares": 1, "primarypurpose": "Momentum Leader"},
            {"ticker": "META", "shares": 1, "primarypurpose": "Core Compounder"},
        ]
    ).to_csv(data_dir / "holdings.csv", index=False)
    pd.DataFrame([{"ticker": "NVDA", "theme": "AI"}]).to_csv(data_dir / "fundamentals.csv", index=False)

    payload = build_project_status_payload(tmp_path, top_n=5)

    assert payload["top_onboarding_actions"][0]["ticker"] == "META"
    assert payload["top_onboarding_actions"][0]["focus_command"] == "make focus-price TICKER=META"
    assert payload["recommended_next_command_rows"][0]["Command"] == "make focus-price TICKER=META"
    assert payload["recommended_next_command_rows"][1]["Step"] == "Open Price Coverage Guided Data Batch"
    assert payload["recommended_next_command_rows"][1]["Command"] == "make runbook-prices"
