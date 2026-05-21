from pathlib import Path

import pandas as pd

from src.project_status import build_project_status_payload


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
    assert "make verify" in payload["recommended_next_commands"]
    assert not (tmp_path / "outputs" / "project_status.csv").exists()
