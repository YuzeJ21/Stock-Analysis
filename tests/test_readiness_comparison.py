from pathlib import Path

from src.readiness_comparison import compare_readiness_snapshots, render_readiness_comparison


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sample_reports(root: Path) -> None:
    header = (
        "ticker,overall_readiness_state,price_ready,fundamentals_ready,dcf_ready,peer_ready,"
        "peer_trend_comparison_ready,peer_valuation_comparison_ready,earnings_ready,"
        "analyst_estimates_ready,blocked_features,excluded_features,missing_data\n"
    )
    _write(
        root / "data" / "reports" / "ticker_readiness_report.previous.csv",
        header
        + "AAA,blocked,false,false,false,false,false,false,false,false,price fundamentals,,price rows\n"
        + "BBB,partial,true,false,false,false,false,false,false,false,fundamentals,,revenue\n",
    )
    _write(
        root / "data" / "reports" / "ticker_readiness_report.csv",
        header
        + "AAA,partial,true,false,false,false,false,false,false,false,fundamentals,,revenue\n"
        + "BBB,partial,true,false,false,false,false,false,false,false,fundamentals,,revenue\n",
    )
    _write(root / "data" / "reports" / "feature_readiness_summary.csv", "feature,ready_count\nprice,1\n")
    _write(root / "data" / "prices.csv", "ticker,date,close\nAAA,2026-01-01,1\n")
    _write(root / "data" / "fundamentals.csv", "ticker,source\n")
    _write(root / "data" / "peers.csv", "ticker,peer_ticker\n")
    _write(root / "data" / "earnings.csv", "ticker,source\n")
    _write(root / "data" / "analyst_estimates.csv", "ticker,source\n")


def test_readiness_comparison_summarizes_counts_and_changed_tickers(tmp_path: Path):
    _sample_reports(tmp_path)

    comparison = compare_readiness_snapshots(tmp_path, top_n=5)
    rendered = render_readiness_comparison(
        comparison,
        batch_id="RB-TEST",
        lane="prices",
        review_date="2026-06-12",
    )

    assert comparison.status == "ok"
    assert comparison.before_rows == 2
    assert comparison.after_rows == 2
    assert comparison.changed_tickers == ("AAA",)
    assert "overall_readiness_state (blocked: 1->0; partial: 1->2)" in comparison.changed_readiness_counts
    assert "price_ready (not_ready: 1->0; ready: 1->2)" in comparison.changed_readiness_counts
    assert "Reviewed Batch Readiness Comparison" in rendered
    assert "Read-only" in rendered
    assert "not investment advice" in rendered
    assert 'BATCH_ID="RB-TEST"' in rendered
    assert 'CHANGED_TICKERS="AAA"' in rendered


def test_readiness_comparison_reports_missing_prior_snapshot(tmp_path: Path):
    _write(tmp_path / "data" / "reports" / "ticker_readiness_report.csv", "ticker,overall_readiness_state\nAAA,partial\n")
    _write(tmp_path / "data" / "reports" / "feature_readiness_summary.csv", "feature,ready_count\nprice,1\n")

    comparison = compare_readiness_snapshots(tmp_path)
    rendered = render_readiness_comparison(comparison)

    assert comparison.status == "missing_before"
    assert "Run make readiness-snapshot before a reviewed batch" in rendered
    assert "Changed tickers (0): none" in rendered
