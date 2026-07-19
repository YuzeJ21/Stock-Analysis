from pathlib import Path

import pandas as pd

from src.readiness_engine import (
    build_peer_readiness_report,
    build_ticker_readiness_report,
    save_previous_ticker_readiness_snapshot,
)


def _file_manifest(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_ticker_readiness_no_write_returns_reports_without_mutating_files(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "name": "NVIDIA",
                "exchange": "NASDAQ",
                "asset_type": "company",
                "sector": "Technology",
                "source": "test_fixture",
            }
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame(
        [{"ticker": "NVDA", "scope": "active_research", "theme": "AI"}]
    ).to_csv(data_dir / "universe_active.csv", index=False)
    before = _file_manifest(tmp_path)

    reports = build_ticker_readiness_report(
        tmp_path,
        data_dir=data_dir,
        output_dir=tmp_path / "outputs",
        write_outputs=False,
    )

    assert "ticker_readiness_report" in reports
    assert "data_source_status" in reports
    assert set(reports["ticker_readiness_report"]["ticker"]) == {"NVDA"}
    assert _file_manifest(tmp_path) == before
    assert not (tmp_path / "outputs").exists()


def _price_rows(ticker: str, periods: int) -> list[dict[str, object]]:
    return [
        {
            "ticker": ticker,
            "date": date.strftime("%Y-%m-%d"),
            "open": 100 + index,
            "high": 101 + index,
            "low": 99 + index,
            "close": 100 + index,
            "volume": 1_000_000 + index,
            "source": "test_fixture",
        }
        for index, date in enumerate(pd.date_range("2026-01-01", periods=periods, freq="D"))
    ]


def test_save_previous_ticker_readiness_snapshot_uses_deterministic_prior_path(tmp_path: Path):
    data_dir = tmp_path / "data"
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True)
    current = reports_dir / "ticker_readiness_report.csv"
    pd.DataFrame(
        [
            {"ticker": "AAA", "price_ready": True, "updated_at": "2026-05-29T00:00:00+00:00"},
            {"ticker": "BBB", "price_ready": False, "updated_at": "2026-05-29T00:00:00+00:00"},
        ]
    ).to_csv(current, index=False)

    payload = save_previous_ticker_readiness_snapshot(tmp_path, data_dir=data_dir)
    snapshot = reports_dir / "ticker_readiness_report.previous.csv"

    assert payload["status"] == "written"
    assert payload["rows"] == 2
    assert payload["snapshot_path"] == str(snapshot)
    assert snapshot.exists()
    assert pd.read_csv(snapshot).to_dict("records") == pd.read_csv(current).to_dict("records")


def test_save_previous_ticker_readiness_snapshot_is_honest_when_current_report_missing(tmp_path: Path):
    payload = save_previous_ticker_readiness_snapshot(tmp_path, data_dir=tmp_path / "data")

    assert payload["status"] == "missing_current_report"
    assert payload["rows"] == 0
    assert "make readiness" in payload["message"]


def test_ticker_readiness_report_tracks_ready_blocked_and_excluded_states(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {"ticker": "NVDA", "name": "NVIDIA", "exchange": "NASDAQ", "asset_type": "company", "sector": "Tech", "source": "test"},
            {"ticker": "AMD", "name": "AMD", "exchange": "NASDAQ", "asset_type": "company", "sector": "Tech", "source": "test"},
            {"ticker": "QQQ", "name": "Invesco QQQ", "exchange": "NASDAQ", "asset_type": "etf", "sector": "ETF", "source": "test"},
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "NVDA", "scope": "active_research", "theme": "AI"},
            {"ticker": "AMD", "scope": "active_research", "theme": "AI"},
            {"ticker": "QQQ", "scope": "active_research", "theme": "Market Proxy"},
        ]
    ).to_csv(data_dir / "universe_active.csv", index=False)
    pd.DataFrame(_price_rows("NVDA", 60) + _price_rows("QQQ", 20)).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "revenue": 100_000_000,
                "free_cash_flow": 25_000_000,
                "fcf_margin": 0.25,
                "shares_outstanding": 2_000_000,
                "source": "test_fixture",
            }
        ]
    ).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(columns=["ticker", "peer_ticker", "peer_group", "source"]).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "earnings.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "analyst_estimates.csv", index=False)
    pd.DataFrame(columns=["ticker", "shares"]).to_csv(data_dir / "holdings.csv", index=False)

    reports = build_ticker_readiness_report(tmp_path, data_dir=data_dir, output_dir=outputs_dir)
    readiness = reports["ticker_readiness_report"].set_index("ticker")
    feature_summary = reports["feature_readiness_summary"].set_index("feature")
    source_status = reports["data_source_status"].set_index("source_name")
    peer_unlock = reports["peer_unlock_worklist"].set_index("ticker")

    assert bool(readiness.loc["NVDA", "price_ready"]) is True
    assert bool(readiness.loc["NVDA", "momentum_ready"]) is True
    assert bool(readiness.loc["NVDA", "liquidity_ready"]) is True
    assert bool(readiness.loc["NVDA", "dcf_ready"]) is True
    assert "data/imports/peers.csv" in readiness.loc["NVDA", "next_action"]
    assert "make imports-validate" in readiness.loc["NVDA", "next_action"]
    assert "make imports-preview" in readiness.loc["NVDA", "next_action"]
    assert "make imports-apply" in readiness.loc["NVDA", "next_action"]
    assert "Optional context" not in readiness.loc["NVDA", "next_action"]
    assert bool(readiness.loc["AMD", "price_ready"]) is False
    assert readiness.loc["AMD", "overall_readiness_state"] == "blocked"
    assert "price" in readiness.loc["AMD", "blocked_features"]
    assert "dcf" in readiness.loc["QQQ", "excluded_features"]
    assert "peer" in readiness.loc["QQQ", "excluded_features"]
    assert "peer" not in readiness.loc["QQQ", "blocked_features"]
    assert "peer mappings" not in readiness.loc["QQQ", "next_action"].lower()
    assert bool(readiness.loc["QQQ", "dcf_ready"]) is False
    assert source_status.loc["remote_price_provider", "status"] == "credential_missing"
    assert source_status.loc["remote_price_provider", "manual_import_path"] == "data/staged/prices/"
    assert source_status.loc["auto_price_ladder", "status"] == "available"
    assert source_status.loc["auto_price_ladder", "manual_import_path"] == "make price-refresh PROVIDER=auto"
    assert int(feature_summary.loc["price", "ready_count"]) == 2
    assert int(feature_summary.loc["price", "blocked_count"]) == 1
    assert int(feature_summary.loc["dcf", "ready_count"]) == 1
    assert int(feature_summary.loc["dcf", "excluded_count"]) == 1
    assert int(feature_summary.loc["peer", "excluded_count"]) == 1
    assert "AMD" in feature_summary.loc["price", "sample_blocked_tickers"]
    assert "NVDA" in feature_summary.loc["dcf", "sample_ready_tickers"]
    assert feature_summary.loc["dcf", "unlock_command"] == "make dcf-readiness"
    assert feature_summary.loc["fundamentals", "next_action"] == "make fundamentals-source-ladder-queue TOP_N=25"
    assert feature_summary.loc["fundamentals", "unlock_command"] == "make fundamentals-source-ladder-queue TOP_N=25"
    assert feature_summary.loc["price", "next_action"] == "make price-refresh-loop DRY_RUN=1"
    assert feature_summary.loc["momentum", "next_action"] == "make price-refresh-loop DRY_RUN=1"
    assert feature_summary.loc["market_direction", "next_action"] == "make price-refresh-loop DRY_RUN=1"
    assert peer_unlock.loc["NVDA", "unlock_stage"] == "add_source_backed_peer_mappings"
    assert peer_unlock.loc["NVDA", "workflow_group"] == "dcf_ready_peer_mapping"
    assert peer_unlock.loc["NVDA", "workflow_scope"] == "active_universe"
    assert "source-backed peer rows" in peer_unlock.loc["NVDA", "next_action_summary"]
    assert peer_unlock.loc["NVDA", "peer_trend_status"] == "peer_trend_blocked"
    assert peer_unlock.loc["NVDA", "peer_valuation_status"] == "peer_valuation_blocked"
    assert peer_unlock.loc["NVDA", "next_input_file"] == "data/imports/peers.csv"
    assert "imports-preview" in peer_unlock.loc["NVDA", "validation_sequence"]
    assert "Copy commands only" in peer_unlock.loc["NVDA", "copy_only_note"]
    assert (data_dir / "reports" / "ticker_readiness_report.csv").exists()
    assert (data_dir / "reports" / "feature_readiness_summary.csv").exists()
    assert (data_dir / "reports" / "peer_unlock_worklist.csv").exists()
    assert (outputs_dir / "feature_readiness_summary.csv").exists()
    assert (outputs_dir / "peer_unlock_worklist.csv").exists()
    assert (data_dir / "reports" / "data_source_status.csv").exists()


def test_company_dcf_excludes_explicit_spac_and_closed_end_fund_names(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {
                "ticker": "ACME",
                "name": "Acme Acquisition Corp. - Class A Ordinary Shares",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "ACQI",
                "name": "AcquiCo Acquisition Inc. - Class A Ordinary Shares",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "ACQII",
                "name": "AcquiCo Acquisition II Corporation - Class A Ordinary Shares",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "CEF",
                "name": "Example Income Fund - Closed End Fund",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "OPCO",
                "name": "Operating Company Inc. - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame(
        _price_rows("ACME", 60)
        + _price_rows("ACQI", 60)
        + _price_rows("ACQII", 60)
        + _price_rows("CEF", 60)
        + _price_rows("OPCO", 60)
    ).to_csv(
        data_dir / "prices.csv",
        index=False,
    )
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(columns=["ticker", "peer_ticker", "peer_group", "source"]).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "earnings.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "analyst_estimates.csv", index=False)
    pd.DataFrame(columns=["ticker", "shares"]).to_csv(data_dir / "holdings.csv", index=False)

    reports = build_ticker_readiness_report(tmp_path, data_dir=data_dir, output_dir=outputs_dir)
    readiness = reports["ticker_readiness_report"].set_index("ticker")
    feature_summary = reports["feature_readiness_summary"].set_index("feature")

    assert "dcf" in readiness.loc["ACME", "excluded_features"]
    assert "dcf" not in readiness.loc["ACME", "blocked_features"]
    assert "dcf:" not in readiness.loc["ACME", "missing_data"]
    assert "trusted fundamentals" not in readiness.loc["ACME", "next_action"]
    assert "dcf" in readiness.loc["ACQI", "excluded_features"]
    assert "dcf" not in readiness.loc["ACQI", "blocked_features"]
    assert "dcf" in readiness.loc["ACQII", "excluded_features"]
    assert "dcf" not in readiness.loc["ACQII", "blocked_features"]
    assert "dcf" in readiness.loc["CEF", "excluded_features"]
    assert "dcf" not in readiness.loc["CEF", "blocked_features"]
    assert "dcf:" not in readiness.loc["CEF", "missing_data"]
    assert "dcf" in readiness.loc["OPCO", "blocked_features"]
    assert "dcf:" in readiness.loc["OPCO", "missing_data"]
    assert int(feature_summary.loc["dcf", "excluded_count"]) == 4


def test_company_dcf_excludes_zero_revenue_margin_model_blockers(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {
                "ticker": "ZREV",
                "name": "Zero Revenue Therapeutics Inc. - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "OPCO",
                "name": "Operating Company Inc. - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame(_price_rows("ZREV", 60) + _price_rows("OPCO", 60)).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(
        [
            {
                "ticker": "ZREV",
                "revenue": 0,
                "free_cash_flow": -10_000_000,
                "shares_outstanding": 20_000_000,
                "source": "sec_companyfacts",
            },
            {
                "ticker": "OPCO",
                "revenue": 50_000_000,
                "shares_outstanding": 10_000_000,
                "source": "sec_companyfacts",
            },
        ]
    ).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(columns=["ticker", "peer_ticker", "peer_group", "source"]).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "earnings.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "analyst_estimates.csv", index=False)
    pd.DataFrame(columns=["ticker", "shares"]).to_csv(data_dir / "holdings.csv", index=False)

    reports = build_ticker_readiness_report(tmp_path, data_dir=data_dir, output_dir=outputs_dir)
    readiness = reports["ticker_readiness_report"].set_index("ticker")
    feature_summary = reports["feature_readiness_summary"].set_index("feature")

    assert "dcf" in readiness.loc["ZREV", "excluded_features"]
    assert "dcf" not in readiness.loc["ZREV", "blocked_features"]
    assert "dcf:" not in readiness.loc["ZREV", "missing_data"]
    assert bool(readiness.loc["ZREV", "dcf_ready"]) is False
    assert "dcf" in readiness.loc["OPCO", "blocked_features"]
    assert "dcf:" in readiness.loc["OPCO", "missing_data"]
    assert int(feature_summary.loc["dcf", "excluded_count"]) == 1
    assert int(feature_summary.loc["dcf", "blocked_count"]) == 1


def test_company_dcf_excludes_explicit_financial_institution_names(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {
                "ticker": "BANK",
                "name": "Bank First Corporation - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "BANC",
                "name": "Affinity Bancshares, Inc. - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "INSR",
                "name": "Example Insurance Group, Inc. - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "REIT",
                "name": "Example Real Estate Investment Trust - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "OPCO",
                "name": "Operating Company Inc. - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame(
        _price_rows("BANK", 60)
        + _price_rows("BANC", 60)
        + _price_rows("INSR", 60)
        + _price_rows("REIT", 60)
        + _price_rows("OPCO", 60)
    ).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(columns=["ticker", "peer_ticker", "peer_group", "source"]).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "earnings.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "analyst_estimates.csv", index=False)
    pd.DataFrame(columns=["ticker", "shares"]).to_csv(data_dir / "holdings.csv", index=False)

    reports = build_ticker_readiness_report(tmp_path, data_dir=data_dir, output_dir=outputs_dir)
    readiness = reports["ticker_readiness_report"].set_index("ticker")
    feature_summary = reports["feature_readiness_summary"].set_index("feature")

    for ticker in ("BANK", "BANC", "INSR", "REIT"):
        assert "dcf" in readiness.loc[ticker, "excluded_features"]
        assert "dcf" not in readiness.loc[ticker, "blocked_features"]
        assert "dcf:" not in readiness.loc[ticker, "missing_data"]
        assert "trusted fundamentals" not in readiness.loc[ticker, "next_action"]

    assert "dcf" in readiness.loc["OPCO", "blocked_features"]
    assert "dcf:" in readiness.loc["OPCO", "missing_data"]
    assert int(feature_summary.loc["dcf", "excluded_count"]) == 4


def test_company_dcf_excludes_explicit_scope_variant_names(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {
                "ticker": "ACQCO",
                "name": "Chenghe Acquisition III Co. - Class A Ordinary Shares",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "ACQPL",
                "name": "Iron Horse Acquisitions II Corp. - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "FINI",
                "name": "AmeriServ Financial Inc. - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "BNK7",
                "name": "Bank7 Corp. - Common stock",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "AVBH",
                "name": "Avidbank Holdings, Inc. - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "OPCO",
                "name": "Operating Company Inc. - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame(
        _price_rows("ACQCO", 60)
        + _price_rows("ACQPL", 60)
        + _price_rows("FINI", 60)
        + _price_rows("BNK7", 60)
        + _price_rows("AVBH", 60)
        + _price_rows("OPCO", 60)
    ).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(columns=["ticker", "peer_ticker", "peer_group", "source"]).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "earnings.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "analyst_estimates.csv", index=False)
    pd.DataFrame(columns=["ticker", "shares"]).to_csv(data_dir / "holdings.csv", index=False)

    reports = build_ticker_readiness_report(tmp_path, data_dir=data_dir, output_dir=outputs_dir)
    readiness = reports["ticker_readiness_report"].set_index("ticker")
    feature_summary = reports["feature_readiness_summary"].set_index("feature")

    for ticker in ("ACQCO", "ACQPL", "FINI", "BNK7", "AVBH"):
        assert "dcf" in readiness.loc[ticker, "excluded_features"]
        assert "dcf" not in readiness.loc[ticker, "blocked_features"]
        assert "dcf:" not in readiness.loc[ticker, "missing_data"]

    assert "dcf" in readiness.loc["OPCO", "blocked_features"]
    assert "dcf:" in readiness.loc["OPCO", "missing_data"]
    assert int(feature_summary.loc["dcf", "excluded_count"]) == 5


def test_company_dcf_excludes_compact_acquisition_and_financial_names(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {
                "ticker": "KRAQ",
                "name": "KRAKacquisition Corp - Class A Ordinary Shares",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "NBRG",
                "name": "Newbridge Acquisition Limited - Class A Ordinary Share",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "SYF",
                "name": "Synchrony Financial",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "OPCO",
                "name": "Operating Company Inc. - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame(
        _price_rows("KRAQ", 60)
        + _price_rows("NBRG", 60)
        + _price_rows("SYF", 60)
        + _price_rows("OPCO", 60)
    ).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(columns=["ticker", "peer_ticker", "peer_group", "source"]).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "earnings.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "analyst_estimates.csv", index=False)
    pd.DataFrame(columns=["ticker", "shares"]).to_csv(data_dir / "holdings.csv", index=False)

    reports = build_ticker_readiness_report(tmp_path, data_dir=data_dir, output_dir=outputs_dir)
    readiness = reports["ticker_readiness_report"].set_index("ticker")
    feature_summary = reports["feature_readiness_summary"].set_index("feature")

    for ticker in ("KRAQ", "NBRG", "SYF"):
        assert "dcf" in readiness.loc[ticker, "excluded_features"]
        assert "dcf" not in readiness.loc[ticker, "blocked_features"]
        assert "dcf:" not in readiness.loc[ticker, "missing_data"]

    assert "dcf" in readiness.loc["OPCO", "blocked_features"]
    assert "dcf:" in readiness.loc["OPCO", "missing_data"]
    assert int(feature_summary.loc["dcf", "excluded_count"]) == 3


def test_company_dcf_excludes_finance_trust_and_capital_vehicle_names(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {
                "ticker": "BANC",
                "name": "First Interstate BancSystem, Inc. - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "TRST",
                "name": "Seven Hills Realty Trust - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "BDCO",
                "name": "Gladstone Investment Corporation - Business Development Company",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "CAPC",
                "name": "Churchill Capital Corp IX - Ordinary Shares",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "FINC",
                "name": "Chicago Atlantic Real Estate Finance, Inc. - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
            {
                "ticker": "OPCO",
                "name": "Operating Company Inc. - Common Stock",
                "asset_type": "company",
                "source": "fixture",
            },
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame(
        _price_rows("BANC", 60)
        + _price_rows("TRST", 60)
        + _price_rows("BDCO", 60)
        + _price_rows("CAPC", 60)
        + _price_rows("FINC", 60)
        + _price_rows("OPCO", 60)
    ).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(columns=["ticker", "peer_ticker", "peer_group", "source"]).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "earnings.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "analyst_estimates.csv", index=False)
    pd.DataFrame(columns=["ticker", "shares"]).to_csv(data_dir / "holdings.csv", index=False)

    reports = build_ticker_readiness_report(tmp_path, data_dir=data_dir, output_dir=outputs_dir)
    readiness = reports["ticker_readiness_report"].set_index("ticker")
    feature_summary = reports["feature_readiness_summary"].set_index("feature")

    for ticker in ("BANC", "TRST", "BDCO", "CAPC", "FINC"):
        assert "dcf" in readiness.loc[ticker, "excluded_features"]
        assert "dcf" not in readiness.loc[ticker, "blocked_features"]
        assert "dcf:" not in readiness.loc[ticker, "missing_data"]

    assert "dcf" in readiness.loc["OPCO", "blocked_features"]
    assert "dcf:" in readiness.loc["OPCO", "missing_data"]
    assert int(feature_summary.loc["dcf", "excluded_count"]) == 5


def test_peer_unlock_worklist_sorts_active_dcf_ready_rows_before_master_rows(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {"ticker": "A", "name": "Agilent", "asset_type": "company", "source": "fixture"},
            {"ticker": "META", "name": "Meta", "asset_type": "company", "source": "fixture"},
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame([{"ticker": "META", "scope": "active_research", "theme": "Platforms"}]).to_csv(
        data_dir / "universe_active.csv",
        index=False,
    )
    pd.DataFrame(_price_rows("A", 60) + _price_rows("META", 60)).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "A", "revenue": 100, "free_cash_flow": 20, "fcf_margin": 0.2, "shares_outstanding": 10, "source": "fixture"},
            {"ticker": "META", "revenue": 100, "free_cash_flow": 20, "fcf_margin": 0.2, "shares_outstanding": 10, "source": "fixture"},
        ]
    ).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(columns=["ticker", "peer_ticker", "peer_group", "source"]).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "earnings.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "analyst_estimates.csv", index=False)
    pd.DataFrame(columns=["ticker", "shares"]).to_csv(data_dir / "holdings.csv", index=False)

    reports = build_ticker_readiness_report(tmp_path, data_dir=data_dir, output_dir=outputs_dir)
    worklist = reports["peer_unlock_worklist"]

    assert list(worklist["ticker"].head(2)) == ["META", "A"]
    assert list(worklist["workflow_scope"].head(2)) == ["active_universe", "master_universe"]
    assert set(worklist["workflow_group"]) == {"dcf_ready_peer_mapping"}
    assert set(["workflow_group", "workflow_scope", "next_action_summary", "next_input_file", "validation_sequence"]).issubset(worklist.columns)
    assert worklist["next_input_file"].eq("data/imports/peers.csv").all()
    assert worklist["validation_sequence"].str.contains("make imports-preview", regex=False).all()
    assert worklist["copy_only_note"].str.contains("Copy commands only", regex=False).all()


def test_partial_peer_mapping_next_action_prioritizes_peer_unlock(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {"ticker": "COHR", "name": "Coherent", "asset_type": "company", "source": "fixture"},
            {"ticker": "LITE", "name": "Lumentum", "asset_type": "company", "source": "fixture"},
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame([{"ticker": "COHR", "scope": "active_research", "theme": "Optical AI Infrastructure"}]).to_csv(
        data_dir / "universe_active.csv",
        index=False,
    )
    pd.DataFrame(_price_rows("COHR", 60) + _price_rows("LITE", 60)).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "COHR", "revenue": 100, "free_cash_flow": 20, "fcf_margin": 0.2, "shares_outstanding": 10, "source": "fixture"},
            {"ticker": "LITE", "revenue": 100, "free_cash_flow": 20, "fcf_margin": 0.2, "shares_outstanding": 10, "source": "fixture"},
        ]
    ).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame([{"ticker": "COHR", "peer_ticker": "LITE", "peer_group": "Optical", "source": "fixture"}]).to_csv(
        data_dir / "peers.csv",
        index=False,
    )
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "earnings.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "analyst_estimates.csv", index=False)
    pd.DataFrame(columns=["ticker", "shares"]).to_csv(data_dir / "holdings.csv", index=False)

    reports = build_ticker_readiness_report(tmp_path, data_dir=data_dir, output_dir=outputs_dir)
    readiness = reports["ticker_readiness_report"].set_index("ticker")

    assert bool(readiness.loc["COHR", "dcf_ready"]) is True
    assert bool(readiness.loc["COHR", "peer_ready"]) is False
    assert "peer" in readiness.loc["COHR", "partial_features"]
    assert "data/imports/peers.csv" in readiness.loc["COHR", "next_action"]
    assert "make imports-validate" in readiness.loc["COHR", "next_action"]
    assert "Optional context" not in readiness.loc["COHR", "next_action"]


def test_candidate_peer_layer_guides_next_action_without_unlocking_trusted_peer_readiness(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {"ticker": "CRDO", "name": "Credo", "asset_type": "company", "source": "fixture"},
            {"ticker": "ALAB", "name": "Astera", "asset_type": "company", "source": "fixture"},
            {"ticker": "MRVL", "name": "Marvell", "asset_type": "company", "source": "fixture"},
        ]
    ).to_csv(
        data_dir / "universe_master.csv",
        index=False,
    )
    pd.DataFrame([{"ticker": "CRDO", "scope": "active_research", "theme": "Connectivity"}]).to_csv(
        data_dir / "universe_active.csv",
        index=False,
    )
    pd.DataFrame(_price_rows("CRDO", 60) + _price_rows("ALAB", 60) + _price_rows("MRVL", 60)).to_csv(
        data_dir / "prices.csv",
        index=False,
    )
    pd.DataFrame(
        [
            {"ticker": "CRDO", "revenue": 100, "free_cash_flow": 20, "fcf_margin": 0.2, "shares_outstanding": 10, "source": "fixture"},
            {"ticker": "ALAB", "revenue": 80, "free_cash_flow": 10, "fcf_margin": 0.125, "shares_outstanding": 8, "source": "fixture"},
            {"ticker": "MRVL", "revenue": 90, "free_cash_flow": 12, "fcf_margin": 0.13, "shares_outstanding": 9, "source": "fixture"},
        ]
    ).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(columns=["ticker", "peer_ticker", "peer_group", "source"]).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(
        [
            {
                "ticker": "CRDO",
                "peer_ticker": "ALAB",
                "candidate_state": "candidate",
                "peer_group": "connectivity",
                "source": "fixture",
            },
            {
                "ticker": "CRDO",
                "peer_ticker": "MRVL",
                "candidate_state": "research_only",
                "peer_group": "connectivity",
                "source": "fixture",
            },
        ]
    ).to_csv(data_dir / "peer_candidates.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "earnings.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "analyst_estimates.csv", index=False)
    pd.DataFrame(columns=["ticker", "shares"]).to_csv(data_dir / "holdings.csv", index=False)

    reports = build_ticker_readiness_report(tmp_path, data_dir=data_dir, output_dir=outputs_dir)
    readiness = reports["ticker_readiness_report"].set_index("ticker")
    peers = reports["peer_readiness_report"].set_index("ticker")
    source_status = reports["data_source_status"].set_index("source_name")
    worklist = reports["peer_unlock_worklist"].set_index("ticker")

    assert bool(readiness.loc["CRDO", "dcf_ready"]) is True
    assert bool(readiness.loc["CRDO", "peer_ready"]) is False
    assert int(peers.loc["CRDO", "peer_count"]) == 0
    assert int(peers.loc["CRDO", "candidate_peer_count"]) == 2
    assert peers.loc["CRDO", "candidate_mapping_status"] == "candidate_available"
    assert peers.loc["CRDO", "candidate_states"] == "candidate, research_only"
    assert "data/peer_candidates.csv" in peers.loc["CRDO", "next_peer_action"]
    assert "data/imports/peers.csv" in peers.loc["CRDO", "next_peer_action"]
    assert source_status.loc["local_peer_candidates", "status"] == "available"
    assert "data/imports/peer_candidates.csv" == source_status.loc["local_peer_candidates", "manual_import_path"]
    assert "data/peer_candidates.csv" in worklist.loc["CRDO", "next_action_summary"]
    assert worklist.loc["CRDO", "next_input_file"] == "data/imports/peers.csv"


def test_readiness_requires_source_and_minimum_ready_peer_metrics(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {"ticker": "AAA", "name": "A Corp", "asset_type": "company", "source": "fixture"},
            {"ticker": "BBB", "name": "B Corp", "asset_type": "company", "source": "fixture"},
            {"ticker": "CCC", "name": "C Corp", "asset_type": "company", "source": "fixture"},
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "AAA", "scope": "active_research", "theme": "Test"},
            {"ticker": "BBB", "scope": "active_research", "theme": "Test"},
            {"ticker": "CCC", "scope": "active_research", "theme": "Test"},
        ]
    ).to_csv(data_dir / "universe_active.csv", index=False)
    pd.DataFrame(_price_rows("AAA", 60) + _price_rows("BBB", 60) + _price_rows("CCC", 60)).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "AAA", "revenue": 100, "source": ""},
            {"ticker": "BBB", "revenue": 100, "source": "fixture"},
            {"ticker": "CCC", "theme": "Metadata only", "sector": "Test", "source": ""},
        ]
    ).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "AAA", "peer_ticker": "BBB", "peer_group": "Test", "peer_role": "core_peer", "relationship_rationale": "Synthetic fixture overlap", "comparability_basis": "business model; growth and margin", "valuation_anchor_eligible": "yes", "source": "fixture", "as_of_date": "2026-06-30"},
            {"ticker": "AAA", "peer_ticker": "CCC", "peer_group": "Test", "peer_role": "secondary_peer", "relationship_rationale": "Synthetic fixture overlap", "comparability_basis": "business model; growth and margin", "valuation_anchor_eligible": "yes", "source": "fixture", "as_of_date": "2026-06-30"},
        ]
    ).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "earnings.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "analyst_estimates.csv", index=False)
    pd.DataFrame(columns=["ticker", "shares"]).to_csv(data_dir / "holdings.csv", index=False)

    reports = build_ticker_readiness_report(tmp_path, data_dir=data_dir, output_dir=outputs_dir)
    readiness = reports["ticker_readiness_report"].set_index("ticker")
    fundamentals = reports["fundamentals_coverage_report"].set_index("ticker")
    peers = reports["peer_readiness_report"].set_index("ticker")

    assert bool(fundamentals.loc["AAA", "has_fundamentals"]) is True
    assert bool(fundamentals.loc["AAA", "fundamentals_ready"]) is False
    assert bool(fundamentals.loc["BBB", "has_fundamentals"]) is True
    assert bool(fundamentals.loc["BBB", "fundamentals_ready"]) is False
    assert "free_cash_flow" in fundamentals.loc["BBB", "missing_fundamentals_fields"]
    assert bool(fundamentals.loc["CCC", "has_fundamentals"]) is False
    assert bool(readiness.loc["AAA", "fundamentals_ready"]) is False
    assert "manual fundamentals import file workflow" in readiness.loc["AAA", "next_action"]
    assert "missing fields: free_cash_flow" in readiness.loc["AAA", "next_action"]
    assert "make focus-fundamentals TICKER=AAA" in readiness.loc["AAA", "next_action"]
    assert int(peers.loc["AAA", "peer_count"]) == 2
    assert int(peers.loc["AAA", "ready_peer_count"]) == 2
    assert bool(peers.loc["AAA", "peer_price_ready"]) is True
    assert bool(peers.loc["AAA", "peer_momentum_ready"]) is True
    assert bool(peers.loc["AAA", "peer_fundamentals_ready"]) is False
    assert bool(peers.loc["AAA", "peer_valuation_ready"]) is False
    assert peers.loc["AAA", "peer_blocker_type"] == "peer_fundamentals_missing"
    assert "CCC" in peers.loc["AAA", "peer_missing_fundamentals_tickers"]
    assert bool(peers.loc["AAA", "peer_trend_comparison_ready"]) is True
    assert bool(peers.loc["AAA", "peer_valuation_comparison_ready"]) is False
    assert "fundamentals" in peers.loc["AAA", "next_peer_action"].lower()
    assert bool(peers.loc["AAA", "peer_ready"]) is True
    assert bool(readiness.loc["AAA", "peer_ready"]) is True


def test_readiness_next_action_uses_peer_metric_blocker_when_mappings_exist(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {"ticker": "AAA", "name": "A Corp", "asset_type": "company", "source": "fixture"},
            {"ticker": "BBB", "name": "B Corp", "asset_type": "company", "source": "fixture"},
            {"ticker": "CCC", "name": "C Corp", "asset_type": "company", "source": "fixture"},
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame([{"ticker": "AAA", "scope": "active_research", "theme": "Test"}]).to_csv(data_dir / "universe_active.csv", index=False)
    pd.DataFrame(_price_rows("AAA", 60)).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "AAA", "revenue": 100, "free_cash_flow": 20, "fcf_margin": 0.2, "shares_outstanding": 10, "source": "fixture"},
            {"ticker": "BBB", "revenue": 100, "free_cash_flow": 20, "fcf_margin": 0.2, "shares_outstanding": 10, "source": "fixture"},
            {"ticker": "CCC", "revenue": 100, "free_cash_flow": 20, "fcf_margin": 0.2, "shares_outstanding": 10, "source": "fixture"},
        ]
    ).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "AAA", "peer_ticker": "BBB", "peer_group": "Test", "source": "fixture"},
            {"ticker": "AAA", "peer_ticker": "CCC", "peer_group": "Test", "source": "fixture"},
        ]
    ).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "earnings.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "analyst_estimates.csv", index=False)
    pd.DataFrame(columns=["ticker", "shares"]).to_csv(data_dir / "holdings.csv", index=False)

    reports = build_ticker_readiness_report(tmp_path, data_dir=data_dir, output_dir=outputs_dir)
    readiness = reports["ticker_readiness_report"].set_index("ticker")
    peers = reports["peer_readiness_report"].set_index("ticker")

    assert peers.loc["AAA", "peer_blocker_type"] == "peer_price_missing"
    assert "price history" in readiness.loc["AAA", "next_action"].lower()
    assert "mapped peers" in readiness.loc["AAA", "next_action"].lower()
    assert "source-backed peer mappings" not in readiness.loc["AAA", "next_action"]


def test_peer_valuation_comparison_requires_dcf_ready_peer_inputs(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    pd.DataFrame(
        [
            {"ticker": "AAA", "name": "A Corp", "asset_type": "company", "source": "fixture"},
            {"ticker": "BBB", "name": "B Corp", "asset_type": "company", "source": "fixture"},
            {"ticker": "CCC", "name": "C Corp", "asset_type": "company", "source": "fixture"},
        ]
    ).to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame([{"ticker": "AAA", "scope": "active_research", "theme": "Test"}]).to_csv(data_dir / "universe_active.csv", index=False)
    pd.DataFrame(_price_rows("AAA", 60) + _price_rows("BBB", 60) + _price_rows("CCC", 60)).to_csv(data_dir / "prices.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "AAA", "revenue": 100, "free_cash_flow": 20, "fcf_margin": 0.2, "shares_outstanding": 10, "source": "fixture"},
            {"ticker": "BBB", "revenue": 100, "source": "fixture"},
            {"ticker": "CCC", "revenue": 100, "source": "fixture"},
        ]
    ).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "AAA", "peer_ticker": "BBB", "peer_group": "Test", "peer_role": "core_peer", "relationship_rationale": "Synthetic fixture overlap", "comparability_basis": "business model; growth and margin", "valuation_anchor_eligible": "yes", "source": "fixture", "as_of_date": "2026-06-30"},
            {"ticker": "AAA", "peer_ticker": "CCC", "peer_group": "Test", "peer_role": "secondary_peer", "relationship_rationale": "Synthetic fixture overlap", "comparability_basis": "business model; growth and margin", "valuation_anchor_eligible": "yes", "source": "fixture", "as_of_date": "2026-06-30"},
        ]
    ).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "earnings.csv", index=False)
    pd.DataFrame(columns=["ticker", "source"]).to_csv(data_dir / "analyst_estimates.csv", index=False)
    pd.DataFrame(columns=["ticker", "shares"]).to_csv(data_dir / "holdings.csv", index=False)

    reports = build_ticker_readiness_report(tmp_path, data_dir=data_dir, output_dir=outputs_dir)
    peers = reports["peer_readiness_report"].set_index("ticker")
    worklist = reports["peer_unlock_worklist"].set_index("ticker")

    assert bool(peers.loc["AAA", "peer_trend_comparison_ready"]) is True
    assert bool(peers.loc["AAA", "peer_fundamentals_ready"]) is True
    assert bool(peers.loc["AAA", "peer_valuation_ready"]) is False
    assert bool(peers.loc["AAA", "peer_valuation_comparison_ready"]) is False
    assert peers.loc["AAA", "peer_blocker_type"] == "peer_valuation_blocked"
    assert worklist.loc["AAA", "workflow_group"] == "peer_valuation_unlock"
    assert worklist.loc["AAA", "peer_trend_status"] == "peer_trend_possible"
    assert worklist.loc["AAA", "peer_valuation_status"] == "peer_valuation_blocked"


def test_peer_trend_readiness_stays_independent_when_valuation_anchor_evidence_is_missing(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    master = pd.DataFrame(
        [
            {"ticker": "AAA", "asset_type": "company"},
            {"ticker": "BBB", "asset_type": "company"},
            {"ticker": "CCC", "asset_type": "company"},
        ]
    )
    master.to_csv(data_dir / "universe_master.csv", index=False)
    pd.DataFrame(_price_rows("AAA", 60) + _price_rows("BBB", 60) + _price_rows("CCC", 60)).to_csv(
        data_dir / "prices.csv", index=False
    )
    pd.DataFrame(
        [
            {"ticker": ticker, "revenue": 100, "free_cash_flow": 20, "fcf_margin": 0.2, "shares_outstanding": 10, "source": "fixture"}
            for ticker in ("AAA", "BBB", "CCC")
        ]
    ).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "AAA", "peer_ticker": "BBB", "peer_group": "Test", "source": "fixture", "as_of_date": "2026-06-30"},
            {"ticker": "AAA", "peer_ticker": "CCC", "peer_group": "Test", "source": "fixture", "as_of_date": "2026-06-30"},
        ]
    ).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(columns=["ticker", "peer_ticker", "candidate_state"]).to_csv(data_dir / "peer_candidates.csv", index=False)

    report = build_peer_readiness_report(tmp_path, data_dir, master, {"price_ready": {"min_rows": 5}, "momentum_ready": {"min_rows": 20}, "peer_ready": {"min_peers": 2}}).set_index("ticker")

    assert bool(report.loc["AAA", "peer_trend_comparison_ready"]) is True
    assert bool(report.loc["AAA", "peer_valuation_ready"]) is False
    assert int(report.loc["AAA", "peer_valuation_anchor_eligible_count"]) == 0
    assert report.loc["AAA", "peer_blocker_type"] == "peer_comparability_unreviewed"
    assert "peer role" in report.loc["AAA", "next_peer_action"].lower()


def test_only_explicitly_eligible_peers_can_unlock_peer_valuation_readiness(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    master = pd.DataFrame(
        [
            {"ticker": "AAA", "asset_type": "company"},
            {"ticker": "BBB", "asset_type": "company"},
            {"ticker": "CCC", "asset_type": "company"},
        ]
    )
    pd.DataFrame(_price_rows("AAA", 60) + _price_rows("BBB", 60) + _price_rows("CCC", 60)).to_csv(
        data_dir / "prices.csv", index=False
    )
    pd.DataFrame(
        [
            {"ticker": ticker, "revenue": 100, "free_cash_flow": 20, "fcf_margin": 0.2, "shares_outstanding": 10, "source": "fixture"}
            for ticker in ("AAA", "BBB", "CCC")
        ]
    ).to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(
        [
            {"ticker": "AAA", "peer_ticker": peer, "peer_group": "Test", "peer_role": role, "relationship_rationale": "Reviewed operating overlap", "comparability_basis": "business model; growth and margin", "valuation_anchor_eligible": "yes", "source": "fixture", "as_of_date": "2026-06-30"}
            for peer, role in (("BBB", "core_peer"), ("CCC", "secondary_peer"))
        ]
    ).to_csv(data_dir / "peers.csv", index=False)
    pd.DataFrame(columns=["ticker", "peer_ticker", "candidate_state"]).to_csv(data_dir / "peer_candidates.csv", index=False)

    report = build_peer_readiness_report(tmp_path, data_dir, master, {"price_ready": {"min_rows": 5}, "momentum_ready": {"min_rows": 20}, "peer_ready": {"min_peers": 2}}).set_index("ticker")

    assert int(report.loc["AAA", "peer_valuation_anchor_eligible_count"]) == 2
    assert bool(report.loc["AAA", "peer_valuation_ready"]) is True
    assert report.loc["AAA", "peer_valuation_anchor_blockers"] == ""
