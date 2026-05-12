import json
from pathlib import Path
from urllib.error import URLError

import pandas as pd

from src.universe_builder import (
    SOURCE_URLS,
    apply_universe_import,
    build_universe_preview,
    summarize_universe_manager,
    validate_universe_sources,
    write_universe_import,
)


SP500_FIXTURE = """Symbol,Security,GICS Sector
NVDA,NVIDIA Corporation,Information Technology
MSFT,Microsoft Corporation,Information Technology
"""

NASDAQ_FIXTURE = """Symbol|Security Name|Test Issue|ETF
NVDA|NVIDIA Corporation Common Stock|N|N
QQQM|Invesco Nasdaq 100 ETF|N|Y
ABCD|Example Test Issue Common Stock|Y|N
UNIT|Example Acquisition Unit|N|N
File Creation Time|20260511|
"""

SMH_FIXTURE = """Ticker,Name,Weight,AsOfDate
NVDA,NVIDIA Corporation,19.2,2026-05-11
AVGO,Broadcom Inc.,12.5,2026-05-11
"""


def _loader(payloads: dict[str, str]):
    def _load(url: str) -> str:
        if url not in payloads:
            raise URLError("offline test source unavailable")
        return payloads[url]

    return _load


def _setup_base_dir(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    imports_dir = data_dir / "imports"
    data_dir.mkdir()
    imports_dir.mkdir()
    (data_dir / "universe.csv").write_text(
        "Ticker,Theme,SectorETF,DefaultPurpose,MarketCapBucket,Notes\n"
        "NVDA,AI Semiconductors,SMH,Momentum Leader,Large,existing sample\n",
        encoding="utf-8",
    )
    (data_dir / "holdings.csv").write_text(
        "Ticker,PrimaryPurpose\n"
        "MSFT,Core Compounder\n",
        encoding="utf-8",
    )


def test_validate_universe_sources_reports_remote_and_local_statuses(tmp_path: Path):
    _setup_base_dir(tmp_path)
    result = validate_universe_sources(
        base_dir=tmp_path,
        sources="local,holdings,sp500",
        loader=_loader({SOURCE_URLS["sp500"]: SP500_FIXTURE}),
    )

    assert result["status"] == "valid"
    assert [item["source_name"] for item in result["sources"]] == ["local", "holdings", "sp500"]
    assert result["sources"][2]["row_count"] == 2


def test_build_universe_preview_parses_sp500_and_preserves_membership_flags(tmp_path: Path):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="local,sp500,holdings",
        loader=_loader({SOURCE_URLS["sp500"]: SP500_FIXTURE}),
    )

    assert result["status"] == "ok"
    rows = pd.DataFrame(result["rows"])
    nvda = rows.loc[rows["ticker"] == "NVDA"].iloc[0]
    msft = rows.loc[rows["ticker"] == "MSFT"].iloc[0]
    assert bool(nvda["in_local_sample"]) is True
    assert bool(nvda["in_sp500"]) is True
    assert bool(msft["in_holdings"]) is True
    assert result["summary"]["new_tickers"] == 1


def test_build_universe_preview_excludes_nasdaq_test_issues_and_etfs_by_default(tmp_path: Path):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="nasdaq",
        loader=_loader({SOURCE_URLS["nasdaq"]: NASDAQ_FIXTURE}),
    )
    rows = pd.DataFrame(result["rows"])

    assert set(rows["ticker"]) == {"NVDA"}


def test_build_universe_preview_can_include_nasdaq_etfs(tmp_path: Path):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="nasdaq",
        include_etfs=True,
        loader=_loader({SOURCE_URLS["nasdaq"]: NASDAQ_FIXTURE}),
    )
    rows = pd.DataFrame(result["rows"])

    assert {"NVDA", "QQQM"}.issubset(set(rows["ticker"]))
    qqqm = rows.loc[rows["ticker"] == "QQQM"].iloc[0]
    assert bool(qqqm["is_etf"]) is True


def test_build_universe_preview_parses_smh_holdings_fixture(tmp_path: Path):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="smh",
        loader=_loader({SOURCE_URLS["smh"]: SMH_FIXTURE}),
    )
    rows = pd.DataFrame(result["rows"])

    assert set(rows["ticker"]) == {"AVGO", "NVDA"}
    assert rows.loc[rows["ticker"] == "NVDA", "etf_membership"].iloc[0] == "SMH"


def test_smh_remote_failure_explains_manual_fallback(tmp_path: Path):
    _setup_base_dir(tmp_path)
    result = validate_universe_sources(base_dir=tmp_path, sources="smh", loader=_loader({}))

    warning_text = " ".join(result["sources"][0]["warnings"])
    assert result["sources"][0]["status"] == "source_unavailable"
    assert "data/custom_universe.csv" in warning_text
    assert "data/imports/universe.csv" in warning_text


def test_write_universe_import_stages_csv_without_applying(tmp_path: Path):
    _setup_base_dir(tmp_path)
    result = write_universe_import(
        base_dir=tmp_path,
        sources="sp500,holdings",
        loader=_loader({SOURCE_URLS["sp500"]: SP500_FIXTURE}),
    )

    staged_path = tmp_path / "data" / "imports" / "universe.csv"
    assert result["status"] == "written"
    assert staged_path.exists()
    staged = pd.read_csv(staged_path)
    assert {"ticker", "theme", "default_purpose"}.issubset(set(staged.columns))
    canonical = pd.read_csv(tmp_path / "data" / "universe.csv")
    assert list(canonical["Ticker"]) == ["NVDA"]


def test_apply_universe_import_creates_backup_and_merges_by_ticker(tmp_path: Path):
    _setup_base_dir(tmp_path)
    staged_path = tmp_path / "data" / "imports" / "universe.csv"
    staged_path.write_text(
        "ticker,theme,sector_etf,default_purpose,market_cap_bucket,notes,in_sp500\n"
        "NVDA,AI Semiconductors,SMH,Momentum Leader,Large,updated,True\n"
        "MSFT,Unclassified,,Core Compounder,Unknown,new row,True\n",
        encoding="utf-8",
    )

    result = apply_universe_import(base_dir=tmp_path)

    assert result["status"] == "applied"
    assert result["backup_path"] is not None
    merged = pd.read_csv(tmp_path / "data" / "universe.csv")
    assert set(merged["ticker"]) == {"MSFT", "NVDA"}
    assert bool(merged.loc[merged["ticker"] == "NVDA", "in_sp500"].iloc[0]) is True


def test_build_universe_preview_handles_missing_remote_source_gracefully(tmp_path: Path):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(base_dir=tmp_path, sources="sp500,holdings", loader=_loader({}))

    assert result["status"] == "ok"
    assert any(source["status"] == "source_unavailable" for source in result["sources"])
    rows = pd.DataFrame(result["rows"])
    assert set(rows["ticker"]) == {"MSFT"}


def test_universe_builder_results_are_json_serializable(tmp_path: Path):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="sp500,smh,holdings",
        loader=_loader({SOURCE_URLS["sp500"]: SP500_FIXTURE, SOURCE_URLS["smh"]: SMH_FIXTURE}),
    )

    payload = json.dumps(result, default=str)
    assert "NVDA" in payload


def test_summarize_universe_manager_reports_current_and_staged_status(tmp_path: Path):
    _setup_base_dir(tmp_path)
    summary = summarize_universe_manager(base_dir=tmp_path)

    assert summary["current_universe"]["row_count"] == 1
    assert summary["staged_universe"]["validation"]["status"] == "missing_file"
