import json

from src.local_profile_seed import seed_local_profile


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_local_profile_seed_copies_runtime_data_without_caches_backups_or_demo(tmp_path):
    _write(tmp_path / "data" / "prices.csv", "date,ticker,close\n2026-07-01,NVDA,100\n")
    _write(tmp_path / "data" / "fundamentals.csv", "ticker,revenue\nNVDA,1\n")
    _write(tmp_path / "data" / "reports" / "ticker_readiness_report.csv", "ticker,price_ready\nNVDA,True\n")
    _write(tmp_path / "data" / "imports" / "prices.csv", "date,ticker,close\n")
    _write(tmp_path / "data" / "cache" / "provider.json", "private cache")
    _write(tmp_path / "data" / "backups" / "old" / "prices.csv", "old")
    _write(tmp_path / "data" / "demo" / "prices.csv", "demo")
    _write(tmp_path / "outputs" / "research_decisions.csv", "ticker\nNVDA\n")
    _write(tmp_path / "outputs" / "stock_reports" / "nvda.md", "generated report")

    result = seed_local_profile(tmp_path)

    assert result["status"] == "seeded"
    assert (tmp_path / "data" / "local" / "prices.csv").exists()
    assert (tmp_path / "data" / "local" / "reports" / "ticker_readiness_report.csv").exists()
    assert (tmp_path / "data" / "local" / "imports" / "prices.csv").exists()
    assert (tmp_path / "outputs" / "local" / "research_decisions.csv").exists()
    assert not (tmp_path / "data" / "local" / "cache").exists()
    assert not (tmp_path / "data" / "local" / "backups").exists()
    assert not (tmp_path / "data" / "local" / "demo").exists()
    assert not (tmp_path / "outputs" / "local" / "stock_reports").exists()
    assert json.loads((tmp_path / "data" / "local" / ".profile_seed.json").read_text())["profile"] == "local"
