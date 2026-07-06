import json
from pathlib import Path
from urllib.error import URLError

import pandas as pd

from src.universe_builder import (
    SOURCE_FALLBACK_URLS,
    SOURCE_URLS,
    _print_result,
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

SP500_LONG_FIXTURE = """Symbol,Security,GICS Sector
A,Agilent Technologies,Health Care
AAPL,Apple Inc.,Information Technology
ABNB,Airbnb,Consumer Discretionary
ABT,Abbott Laboratories,Health Care
ACN,Accenture,Information Technology
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

SMH_HTML_FIXTURE = """
<table>
  <thead><tr><th>#</th><th>Symbol</th><th>Holding</th><th>% Weight</th><th>Shares</th></tr></thead>
  <tbody>
    <tr><td>1</td><td><a href="/stocks/nvda/">NVDA</a></td><td>NVIDIA Corporation</td><td>18.16%</td><td>66,842,647</td></tr>
    <tr><td>2</td><td><a href="/stocks/mu/">MU</a></td><td>Micron Technology Inc.</td><td>5.99%</td><td>3,700,000</td></tr>
  </tbody>
</table>
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


def test_capped_universe_preview_prioritizes_smh_rows_before_generic_sp500_rows(tmp_path: Path):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="sp500,smh",
        max_tickers=2,
        loader=_loader({SOURCE_URLS["sp500"]: SP500_LONG_FIXTURE, SOURCE_URLS["smh"]: SMH_FIXTURE}),
    )
    rows = pd.DataFrame(result["rows"])

    assert set(rows["ticker"]) == {"AVGO", "NVDA"}
    assert rows["in_smh"].fillna(False).astype(bool).all()
    assert result["summary"]["membership_counts"]["in_smh"] == 2


def test_build_universe_preview_uses_smh_fallback_when_primary_source_fails(tmp_path: Path):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="smh",
        loader=_loader({SOURCE_FALLBACK_URLS["smh"][1]: SMH_HTML_FIXTURE}),
    )
    rows = pd.DataFrame(result["rows"])

    assert result["sources"][0]["status"] == "loaded"
    assert result["sources"][0]["source_url"] == SOURCE_FALLBACK_URLS["smh"][1]
    assert any("using fallback source" in warning for warning in result["sources"][0]["warnings"])
    assert any("primary source unavailable" in warning for warning in result["sources"][0]["warnings"])
    assert sum("primary source unavailable" in warning for warning in result["sources"][0]["warnings"]) == 1
    assert not any("remote source unavailable" in warning for warning in result["sources"][0]["warnings"])
    assert set(rows["ticker"]) == {"MU", "NVDA"}
    assert rows.loc[rows["ticker"] == "NVDA", "company_name"].iloc[0] == "NVIDIA Corporation"
    assert rows.loc[rows["ticker"] == "NVDA", "source_detail"].iloc[0] == "SMH weight: 18.16%"


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


def test_apply_universe_import_preserves_existing_membership_labels(tmp_path: Path):
    data_dir = tmp_path / "data"
    imports_dir = data_dir / "imports"
    imports_dir.mkdir(parents=True)
    (data_dir / "universe.csv").write_text(
        "ticker,theme,sector_etf,default_purpose,market_cap_bucket,notes,company_name,"
        "universe_source,source_detail,index_membership,etf_membership,exchange,is_etf,as_of_date,"
        "in_local_sample,in_sp500,in_nasdaq,in_smh,in_holdings,in_custom\n"
        "AAPL,Unclassified,,Core Compounder,Unknown,sp500 and nasdaq notes,Apple Inc.,"
        "\"sp500, nasdaq\",,\"S&P 500, Nasdaq-listed\",,NASDAQ,False,,False,True,True,False,False,False\n",
        encoding="utf-8",
    )
    (imports_dir / "universe.csv").write_text(
        "ticker,theme,sector_etf,default_purpose,market_cap_bucket,notes,company_name,"
        "universe_source,source_detail,index_membership,etf_membership,exchange,is_etf,as_of_date,"
        "in_local_sample,in_sp500,in_nasdaq,in_smh,in_holdings,in_custom\n"
        "AAPL,Unclassified,,Core Compounder,Unknown,sp500 notes,Apple Inc.,"
        "sp500,Information Technology,S&P 500,,NASDAQ,False,,False,True,False,False,False,False\n",
        encoding="utf-8",
    )

    result = apply_universe_import(base_dir=tmp_path)

    assert result["status"] == "applied"
    merged = pd.read_csv(data_dir / "universe.csv")
    aapl = merged.loc[merged["ticker"] == "AAPL"].iloc[0]
    assert aapl["universe_source"] == "sp500, nasdaq"
    assert aapl["index_membership"] == "S&P 500, Nasdaq-listed"
    assert bool(aapl["in_nasdaq"]) is True


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


def test_universe_preview_default_output_is_compact_and_keeps_raw_rows_hidden(
    tmp_path: Path,
    capsys,
):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="sp500,smh,holdings",
        loader=_loader({SOURCE_URLS["sp500"]: SP500_FIXTURE, SOURCE_FALLBACK_URLS["smh"][1]: SMH_HTML_FIXTURE}),
    )

    _print_result(result, as_json=False)
    output = capsys.readouterr().out

    assert "Universe Preview" in output
    assert "status: ok" in output
    assert "does not unlock fundamentals, share count, DCF, peer valuation, earnings, analyst estimates, or recommendations" in output
    assert "row_count:" in output
    assert "source_differences:" in output
    assert "source difference boundary: source rows may differ from local metadata before protected-field merge" in output
    assert "canonical_apply_effect:" in output
    assert "canonical apply boundary: universe-apply preserves meaningful existing local fields and keeps true membership flags" in output
    assert "protected_sample:" in output
    assert "- NVDA: preserves theme, sector_etf, market_cap_bucket" in output
    assert "staged_import:" in output
    assert "sources:" in output
    assert "smh: loaded" in output
    assert "smh: primary source unavailable (redirect/cookie/location handling)." in output
    assert "using fallback source" in output
    assert "source_review: apply_gate=review_required; fallback_sources_used=1; unavailable_sources=0; raw_rows_hidden=true" in output
    assert "fallback boundary: review fallback source row counts before staging; use manual CSV only if all remote sources fail" in output
    assert "review_sample:" in output
    assert "- NVDA: existing; sources=smh, sp500; memberships=S&P 500, SMH" in output
    assert "- MU: new; sources=smh; memberships=SMH" in output
    assert "review sample is capped" in output
    assert "manual SMH fallback only if all remote SMH sources fail" in output
    assert "HTTP Error" not in output
    assert "stage data/imports/universe.csv as the manual SMH fallback" not in output
    assert "next:" in output
    assert "python3 -m src.universe_builder --preview --preset sp500_smh --max-tickers 50 --json" in output
    assert "make universe-stage OVERWRITE=1" in output
    assert "make universe-apply" in output
    assert '"rows"' not in output
    assert '"ticker": "NVDA"' not in output


def test_universe_preview_noop_apply_effect_does_not_recommend_apply(
    tmp_path: Path,
    capsys,
):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="local",
    )
    result["summary"]["apply_effect"] = {
        "new_rows": 0,
        "updated_rows": 0,
        "unchanged_rows": 1,
        "protected_existing_value_count": 0,
        "protected_existing_value_sample": [],
        "boundary": "universe-apply preserves meaningful existing local fields and keeps true membership flags.",
    }

    _print_result(result, as_json=False)
    output = capsys.readouterr().out

    assert "canonical_apply_effect: new=0; updated=0;" in output
    assert "canonical_apply_state: no_apply_needed" in output
    assert "No universe apply needed: canonical merge would not add or update rows." in output
    assert "make universe-stage OVERWRITE=1" not in output
    assert "make universe-apply" not in output


def test_universe_preview_summary_json_keeps_raw_rows_hidden(
    tmp_path: Path,
    capsys,
):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="sp500,smh,holdings",
        loader=_loader({SOURCE_URLS["sp500"]: SP500_FIXTURE, SOURCE_FALLBACK_URLS["smh"][1]: SMH_HTML_FIXTURE}),
    )
    result["sources"][1]["warnings"] = [
        "smh: remote source unavailable (same redirect).",
        "smh: remote source unavailable (same redirect).",
        f"smh: using fallback source {SOURCE_FALLBACK_URLS['smh'][1]}.",
    ]

    _print_result(result, as_json=False, summary_json=True)
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert payload["status"] == "ok"
    assert payload["summary"]["row_count"] == 3
    assert payload["sources"][0]["source_name"] == "sp500"
    assert payload["next_steps"] == [
        "Review source warnings and row counts before writing any universe import.",
        "Use full --json only for intentionally reviewed row inspection.",
        "To inspect full preview rows without writing: make universe-preview.",
        "To stage reviewed rows only after row-scope review: make universe-stage OVERWRITE=1.",
        "To apply staged rows after review: make universe-apply.",
    ]
    assert "rows" not in payload
    assert "NVDA" not in output
    assert payload["sources"][1]["warnings"].count("smh: remote source unavailable (same redirect).") == 1
    assert "available_columns" not in payload["sources"][0]
    assert payload["sources"][0]["available_column_count"] > 0


def test_universe_preview_summary_json_surfaces_fallback_and_apply_gate(
    tmp_path: Path,
    capsys,
):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="sp500,smh,holdings",
        loader=_loader({SOURCE_URLS["sp500"]: SP500_FIXTURE, SOURCE_FALLBACK_URLS["smh"][1]: SMH_HTML_FIXTURE}),
    )

    _print_result(result, as_json=False, summary_json=True)
    payload = json.loads(capsys.readouterr().out)
    review = payload["source_review"]

    assert review["apply_gate"] == "review_required"
    assert review["raw_rows_hidden"] is True
    assert review["source_status_counts"]["loaded"] == 3
    assert review["fallback_sources_used"] == [
        {
            "source_name": "smh",
            "source_url": SOURCE_FALLBACK_URLS["smh"][1],
            "status": "loaded",
        }
    ]
    assert review["unavailable_sources"] == []
    assert "review source warnings and row counts" in review["next_safe_step"].lower()
    assert "rows" not in payload


def test_universe_preview_summary_json_surfaces_safe_apply_effect(
    tmp_path: Path,
    capsys,
):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="sp500,smh,holdings",
        loader=_loader({SOURCE_URLS["sp500"]: SP500_FIXTURE, SOURCE_URLS["smh"]: SMH_FIXTURE}),
    )

    _print_result(result, as_json=False, summary_json=True)
    payload = json.loads(capsys.readouterr().out)
    apply_effect = payload["summary"]["apply_effect"]

    assert apply_effect["new_rows"] == 2
    assert apply_effect["updated_rows"] == 1
    assert apply_effect["protected_existing_value_count"] >= 3
    assert "protected_existing_value_sample" not in apply_effect
    assert "preserves meaningful existing local fields" in apply_effect["boundary"]


def test_universe_preview_surfaces_existing_staged_import_boundary(
    tmp_path: Path,
    capsys,
):
    _setup_base_dir(tmp_path)
    staged_path = tmp_path / "data" / "imports" / "universe.csv"
    staged_path.write_text(
        "ticker,theme,sector_etf,default_purpose,market_cap_bucket,notes,in_sp500\n"
        "NVDA,AI Semiconductors,SMH,Momentum Leader,Large,old staged,True\n",
        encoding="utf-8",
    )
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="sp500,smh,holdings",
        loader=_loader({SOURCE_URLS["sp500"]: SP500_FIXTURE, SOURCE_URLS["smh"]: SMH_FIXTURE}),
    )

    _print_result(result, as_json=False)
    output = capsys.readouterr().out

    assert "staged_import: exists; rows=1; validation=valid" in output
    assert "Do not run universe-apply until the staged import file is intentionally reviewed" in output
    assert "make universe-stage OVERWRITE=1" in output
    assert result["summary"]["staged_import"]["exists"] is True
    assert result["summary"]["staged_import"]["row_count"] == 1


def test_universe_preview_summary_json_surfaces_unavailable_sources(
    tmp_path: Path,
    capsys,
):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="sp500,smh",
        loader=_loader({}),
    )

    _print_result(result, as_json=False, summary_json=True)
    payload = json.loads(capsys.readouterr().out)
    review = payload["source_review"]

    assert review["source_status_counts"]["source_unavailable"] == 2
    assert review["fallback_sources_used"] == []
    assert review["unavailable_sources"] == [
        {"source_name": "sp500", "source_url": SOURCE_URLS["sp500"], "status": "source_unavailable"},
        {"source_name": "smh", "source_url": SOURCE_FALLBACK_URLS["smh"][1], "status": "source_unavailable"},
    ]
    assert review["apply_gate"] == "review_required"


def test_universe_preview_compact_output_deduplicates_source_warnings(
    tmp_path: Path,
    capsys,
):
    _setup_base_dir(tmp_path)
    result = build_universe_preview(
        base_dir=tmp_path,
        sources="smh",
        loader=_loader({SOURCE_FALLBACK_URLS["smh"][1]: SMH_HTML_FIXTURE}),
    )
    duplicate_warning = "smh: remote source unavailable (same redirect)."
    result["sources"][0]["warnings"] = [
        duplicate_warning,
        duplicate_warning,
        f"smh: using fallback source {SOURCE_FALLBACK_URLS['smh'][1]}.",
    ]

    _print_result(result, as_json=False)
    output = capsys.readouterr().out

    assert output.count(duplicate_warning) == 1
    assert output.count("using fallback source") == 1


def test_summarize_universe_manager_reports_current_and_staged_status(tmp_path: Path):
    _setup_base_dir(tmp_path)
    summary = summarize_universe_manager(base_dir=tmp_path)

    assert summary["current_universe"]["row_count"] == 1
    assert summary["staged_universe"]["validation"]["status"] == "missing_file"
