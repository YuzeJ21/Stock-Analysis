from pathlib import Path
import sys

import pandas as pd
import pytest

from src.project_status import build_project_status_payload, main


def _write_minimal_local_data(root: Path) -> None:
    data_dir = root / "data"
    outputs_dir = root / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
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
    assert not (tmp_path / "outputs" / "project_status.csv").exists()


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
    assert "command: python3 -m src.stock_report --sec-stage-fundamentals --tickers nvda" in output
    assert "fix top prices blocker (nvda): make focus-price ticker=nvda" in output
    assert "no verified local price history is present for this ticker yet." in output or "at least 21 are needed" in output
    assert "run price coverage bundle: make runbook-prices" in output


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
    assert payload["recommended_next_command_rows"][1]["Command"] == "make runbook-prices-broader"


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
    assert payload["recommended_next_command_rows"][1]["Command"] == "make runbook-prices"
