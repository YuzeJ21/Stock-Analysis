import json
from pathlib import Path

import pandas as pd

from src.track_record import calculate_monthly_track_record


def _write_track_fixture(base: Path) -> None:
    (base / "data").mkdir()
    (base / "outputs").mkdir()
    (base / "data" / "universe.csv").write_text(
        "Ticker,Theme,SectorETF,DefaultPurpose,MarketCapBucket\n"
        "AAA,AI,QQQ,Momentum Leader,Large\n"
        "BBB,Cloud,QQQ,Momentum Leader,Large\n",
        encoding="utf-8",
    )
    rows = ["date,ticker,adj_close,volume"]
    for month, base_value in [("01", 100), ("02", 115), ("03", 125)]:
        for day in range(1, 29):
            rows.append(f"2026-{month}-{day:02d},AAA,{base_value + day * 0.4},1000000")
            rows.append(f"2026-{month}-{day:02d},BBB,{base_value - 5 + day * 0.2},900000")
            rows.append(f"2026-{month}-{day:02d},SPY,{100 + int(month) * 2 + day * 0.1},2000000")
    (base / "data" / "prices.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_track_record_calculates_forward_returns_and_benchmark(tmp_path: Path):
    _write_track_fixture(tmp_path)

    result = calculate_monthly_track_record(tmp_path, top_n=1, benchmark="SPY")

    assert result["row_count"] >= 1
    track = pd.read_csv(tmp_path / "outputs" / "monthly_picks_track_record.csv")
    assert {"AveragePickReturn", "BenchmarkReturn", "ExcessReturn"}.issubset(track.columns)
    assert track["NumberOfPicks"].max() >= 1
    assert (tmp_path / "outputs" / "monthly_picks_equity_curve.csv").exists()
    assert json.dumps(result, default=str)


def test_track_record_reports_insufficient_history_without_fake_results(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "data" / "universe.csv").write_text("Ticker,Theme,SectorETF,DefaultPurpose,MarketCapBucket\nAAA,AI,QQQ,Momentum Leader,Large\n", encoding="utf-8")
    (tmp_path / "data" / "prices.csv").write_text("date,ticker,adj_close,volume\n2026-01-01,AAA,10,1000\n", encoding="utf-8")

    result = calculate_monthly_track_record(tmp_path)

    assert result["equity_curve_rows"] == 0
    assert "Insufficient local history" in result["track_record"][0]["Notes"]
