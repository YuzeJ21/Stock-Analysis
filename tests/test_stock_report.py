import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.providers.market_data import (
    AnalystEstimateSummary,
    EarningsSummary,
    FinancialSnapshot,
    QuoteSnapshot,
    make_source_metadata,
)
from src.providers.local_market_data import LocalCSVMarketDataProvider
from src.providers.mock_market_data import MockMarketDataProvider
from src.stock_report import (
    _display_setup_text,
    _format_inline_make_commands,
    _public_report_brief,
    _stock_report_dcf_input_triage_lines,
    _stock_report_best_review_path_lines,
    _stock_report_optional_context_ladder_lines,
    _stock_report_one_minute_state_phrase,
    _stock_report_peer_evidence_ladder_lines,
    _stock_report_peer_unlock_lines,
    _stock_report_missing_data_lines,
    _stock_report_reader_guide_lines,
    _stock_report_reader_question_lines,
    _stock_report_valuation_lines,
    _stock_report_purpose_fields,
    build_readiness_only_markdown,
    build_stock_report,
    create_stock_report_payload,
    export_stock_report_json,
    export_stock_report_markdown,
    main,
)

RICH_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "rich_local_data"


def test_stock_report_formats_bare_make_commands_as_copyable_inline_commands():
    text = _format_inline_make_commands(
        "Run make focus-fundamentals TICKER=META, then make imports-validate before review. "
        "This should make the comparison easier to review. You can also run make dashboard."
    )

    assert "`make focus-fundamentals TICKER=META`" in text
    assert "`make imports-validate`" in text
    assert "`make dashboard`" in text
    assert "make the comparison" in text
    assert "`make the`" not in text


def test_public_report_brief_caps_dense_diagnostic_bullets():
    long_text = (
        "Purpose alignment: Purpose alignment needs review because the saved research view includes trend conflict. "
        "Trend support failed below both 50SMA and 200SMA. Missing data: EPS growth, gross margin, debt to equity, "
        "P/E, forward P/E, EV/sales, EV/EBITDA, price to free cash flow, FCF yield. "
        "Next blocker: fundamentals. Withheld: DCF interpretation and peer-relative valuation."
    )

    brief = _public_report_brief(long_text, "Purpose alignment:", max_chars=120)

    assert brief.startswith("Purpose alignment needs review")
    assert "Review the readiness sections below before drawing conclusions" in brief
    assert "Additional diagnostics are summarized" not in brief
    assert "Next blocker: fundamentals" in brief
    assert "Withheld: DCF interpretation and peer-relative valuation" in brief
    assert "EV/EBITDA" not in brief
    assert "Run make focus-fundamentals" not in brief


def test_stock_report_one_minute_state_phrase_explains_partial_readiness():
    core_ready = _stock_report_one_minute_state_phrase(
        ticker="NVDA",
        readiness={"overall_readiness_state": "partial"},
        dcf_status_text="ready",
        peer_ready=True,
        optional_locked=True,
        monitor_context=False,
    )
    monitor = _stock_report_one_minute_state_phrase(
        ticker="QQQ",
        readiness={"overall_readiness_state": "partial"},
        dcf_status_text="excluded",
        peer_ready=False,
        optional_locked=True,
        monitor_context=True,
    )
    data_unlock = _stock_report_one_minute_state_phrase(
        ticker="APLD",
        readiness={"overall_readiness_state": "partial"},
        dcf_status_text="blocked",
        peer_ready=False,
        optional_locked=True,
        monitor_context=False,
    )

    assert "optional earnings/estimate context is locked; core DCF and peer inputs are ready" in core_ready
    assert "monitor context is usable while company valuation is excluded" in monitor
    assert "review ready inputs first and treat locked inputs as data-unlock work" in data_unlock


def test_stock_report_humanized_terms_preserve_copyable_dcf_commands():
    text = _stock_report_dcf_input_triage_lines(
        ticker="META",
        dcf={"missing_dcf_fields": ["shares_outstanding"]},
        valuation_readiness={},
        dcf_status_text="blocked",
        monitor_context=False,
    )
    rendered = "\n".join(text)

    assert "`make dcf-readiness`" in rendered
    assert "make DCF-readiness" not in rendered


def test_stock_report_setup_text_relabels_not_ready_company_rows_as_data_limited():
    text = _display_setup_text(
        "Capped score at 50 because valuation readiness is `not_ready`; "
        "treat as monitor-only until missing data is resolved."
    )

    assert "valuation readiness is not ready" in text
    assert "treat as data-limited review until missing data is resolved" in text
    assert "treat as monitor-only" not in text.lower()


def test_stock_report_dcf_input_triage_explains_missing_fields_without_recommendations():
    lines = _stock_report_dcf_input_triage_lines(
        ticker="TSLA",
        dcf={"missing_dcf_fields": ["revenue", "free_cash_flow", "shares_outstanding"]},
        valuation_readiness={},
        dcf_status_text="blocked",
        monitor_context=False,
    )
    rendered = " ".join(lines).lower()

    assert "blocked inputs are repair steps, not negative company signals" in rendered
    assert "trusted price and share count anchor per-share output" in rendered
    assert "revenue plus free cash flow or fcf margin builds base fcf" in rendered
    assert "cash/debt adjusts enterprise value to equity value" in rendered
    assert "missing revenue" in rendered
    assert "sets the operating scale used for forecast assumptions" in rendered
    assert "missing free cash flow" in rendered
    assert "drives base fcf for projected cash flows" in rendered
    assert "missing shares outstanding" in rendered
    assert "converts equity value into fair value per share" in rendered
    assert "make focus-fundamentals ticker=tsla" in rendered
    assert "make sec-stage tickers=tsla" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "make dcf-readiness" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_dcf_input_triage_marks_monitor_context_as_excluded():
    lines = _stock_report_dcf_input_triage_lines(
        ticker="QQQ",
        dcf={"missing_dcf_fields": ["revenue"]},
        valuation_readiness={},
        dcf_status_text="excluded",
        monitor_context=True,
    )

    assert lines == [
        "- DCF input triage: not required for ETF/index/fund monitor context; operating-company valuation is excluded rather than repaired.",
    ]


def test_stock_report_peer_evidence_ladder_splits_trend_and_valuation():
    lines = _stock_report_peer_evidence_ladder_lines(
        ticker="COHR",
        peer={
            "peer_count": 2,
            "mapping_status": "mapped",
            "peer_blocker_type": "peer_valuation_blocked",
            "peer_trend_comparison_ready": True,
            "peer_valuation_comparison_ready": False,
            "peer_dcf_comparison_ready": False,
        },
        dcf_status_text="ready",
        monitor_context=False,
        peer_ready=False,
    )
    rendered = " ".join(lines).lower()

    assert "standalone dcf can be reviewed before peer valuation is ready" in rendered
    assert "mapping status=mapped; peer count=2; blocker=peer valuation blocked" in rendered
    assert "trend evidence: possible from mapped peer price history" in rendered
    assert "valuation evidence: locked" in rendered
    assert "do not show peer-relative premium/discount, peer valuation comparison, or peer dcf comparison" in rendered
    assert "data/imports/peers.csv" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_peer_ready_copy_uses_source_readiness_language():
    peer = {
        "peer_count": 2,
        "mapping_status": "mapped",
        "peer_trend_comparison_ready": True,
        "peer_valuation_comparison_ready": True,
        "peer_dcf_comparison_ready": True,
    }
    unlock_lines = _stock_report_peer_unlock_lines(
        ticker="COHR",
        peer=peer,
        dcf_status_text="ready",
        monitor_context=False,
        peer_ready=True,
        next_peer_action="Peer context ready.",
    )
    evidence_lines = _stock_report_peer_evidence_ladder_lines(
        ticker="COHR",
        peer=peer,
        dcf_status_text="ready",
        monitor_context=False,
        peer_ready=True,
    )
    rendered = " ".join(unlock_lines + evidence_lines).lower()

    assert "source readiness" in rendered
    assert "mapped peers and freshness" not in rendered
    assert "review freshness" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_optional_context_ladder_keeps_missing_rows_locked():
    lines = _stock_report_optional_context_ladder_lines(
        ticker="NVDA",
        earnings_ready=False,
        estimates_ready=False,
        earnings_summary={},
        analyst_estimate_summary={},
    )
    rendered = " ".join(lines).lower()

    assert "optional context ladder" in rendered
    assert "earnings and analyst estimates add timing, consensus, and revision context only" in rendered
    assert "earnings evidence: locked" in rendered
    assert "templates are not data" in rendered
    assert "analyst-estimate evidence: locked" in rendered
    assert "data/staged/earnings/" in rendered
    assert "data/staged/analyst_estimates/" in rendered
    assert "make import-earnings" in rendered
    assert "make import-analyst-estimates" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "data/rejected/earnings_import_rejected.csv" in rendered
    assert "data/rejected/analyst_estimates_import_rejected.csv" in rendered
    assert "make optional-context-readiness" in rendered
    assert "missing earnings or estimates must not appear as event timing, consensus, revision, upside, downside, undervalued, or overvalued analysis" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_reader_questions_route_optional_locked_core_ready_names():
    lines = _stock_report_reader_question_lines(
        ticker="NVDA",
        supported_now="Price, fundamentals, DCF, and peer context can be reviewed from trusted local inputs.",
        locked_now="Earnings and analyst estimates remain unavailable until trusted optional CSV rows exist.",
        next_action="Optional context missing for NVDA; leave unavailable unless trusted local CSVs exist.",
        dcf_status_text="ready",
        monitor_context=False,
        price_ready=True,
        peer_ready=True,
        earnings_ready=False,
        estimates_ready=False,
    )
    rendered = "\n".join(lines).lower()

    assert "trusted optional earnings or analyst-estimate csv rows" in rendered
    assert "`make optional-context-worklist tickers=nvda top_n=10`" in rendered
    assert "`make stock-report-md ticker=nvda`" not in rendered
    assert "source-backed peer mappings and peer valuation inputs" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_best_review_path_routes_ready_blocked_and_monitor_modes():
    ready_lines = _stock_report_best_review_path_lines(
        ticker="NVDA",
        dcf_status_text="ready",
        monitor_context=False,
        price_ready=True,
        peer_ready=True,
        earnings_ready=False,
        estimates_ready=False,
    )
    ready_rendered = " ".join(ready_lines).lower()
    assert "dcf calculation path, then peer workflow, then source readiness" in ready_rendered
    assert "richest company-review path" in ready_rendered
    assert "`make stock-report-md ticker=nvda`" in ready_rendered
    assert "optional earnings and analyst-estimate context remains locked" in ready_rendered

    blocked_lines = _stock_report_best_review_path_lines(
        ticker="META",
        dcf_status_text="blocked",
        monitor_context=False,
        price_ready=True,
        peer_ready=False,
        earnings_ready=False,
        estimates_ready=False,
    )
    blocked_rendered = " ".join(blocked_lines).lower()
    assert "dcf input triage and data unlock summary" in blocked_rendered
    assert "company valuation stays blocked" in blocked_rendered
    assert "`make focus-fundamentals ticker=meta`" in blocked_rendered

    monitor_lines = _stock_report_best_review_path_lines(
        ticker="QQQ",
        dcf_status_text="excluded",
        monitor_context=True,
        price_ready=True,
        peer_ready=False,
        earnings_ready=False,
        estimates_ready=False,
    )
    monitor_rendered = " ".join(monitor_lines).lower()
    assert "operating-company dcf and peer-relative company valuation are excluded" in monitor_rendered
    assert "`make stock-report-md ticker=qqq`" in monitor_rendered
    assert "broker" not in ready_rendered + blocked_rendered + monitor_rendered
    assert "order" not in ready_rendered + blocked_rendered + monitor_rendered
    assert "trading" not in ready_rendered + blocked_rendered + monitor_rendered
    assert "buy" not in ready_rendered + blocked_rendered + monitor_rendered
    assert "sell" not in ready_rendered + blocked_rendered + monitor_rendered


def _copy_rich_fixture(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for path in RICH_FIXTURE_DIR.glob("*.csv"):
        (data_dir / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_build_stock_report_assembles_expected_sections(tmp_path: Path):
    source = make_source_metadata(
        provider="mock",
        freshness="daily snapshot",
        official=False,
        notes=["Unofficial / research-grade market data."],
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
    history = pd.DataFrame(
        [{"date": pd.Timestamp("2025-05-12") + pd.Timedelta(days=day), "close": 100.0 + day} for day in range(260)]
    )

    provider = MockMarketDataProvider(
        quotes={
            "MSFT": QuoteSnapshot(
                ticker="MSFT",
                price=360.0,
                previous_close=355.0,
                open=356.0,
                day_high=362.0,
                day_low=354.0,
                volume=1_000_000,
                currency="USD",
                market_time="2026-05-11T15:30:00Z",
                source=source,
            )
        },
        histories={("MSFT", "1y", "1d"): history},
        financials={
            "MSFT": FinancialSnapshot(
                ticker="MSFT",
                revenue=250_000_000_000,
                revenue_growth=0.10,
                eps=12.5,
                gross_margin=0.68,
                operating_margin=0.42,
                free_cash_flow=90_000_000_000,
                fcf_margin=0.36,
                cash=90_000_000_000,
                debt=40_000_000_000,
                market_cap=2_700_000_000_000,
                shares_outstanding=7_400_000_000,
                source=source,
            )
        },
        earnings={
            "MSFT": EarningsSummary(
                ticker="MSFT",
                next_earnings_date="2026-07-24",
                last_earnings_date="2026-04-24",
                eps_estimate=3.0,
                eps_actual=3.1,
                surprise_pct=0.03,
                source=source,
            )
        },
        estimates={
            "MSFT": AnalystEstimateSummary(
                ticker="MSFT",
                current_quarter_eps=3.1,
                next_quarter_eps=3.25,
                current_year_eps=13.0,
                next_year_eps=14.1,
                recommendation="outperform",
                target_mean_price=390.0,
                source=source,
            )
        },
    )

    report = build_stock_report("MSFT", provider)
    report.screener_context = {
        "momentum_leaders": {
            "ATRorVolatilityPct": 0.031,
            "ATRorVolatilitySource": "volatility_proxy",
        }
    }
    report_dict = report.to_dict()
    markdown = export_stock_report_markdown(report, tmp_path / "msft.md")

    assert report_dict["ticker"] == "MSFT"
    assert report_dict["provider_name"] == "MockMarketDataProvider"
    assert report_dict["generated_at"] is not None
    assert report_dict["price_snapshot"]["price"] == 360.0
    assert report_dict["performance"]["one_month"] is not None
    assert report_dict["financial_summary"]["revenue"] == 250_000_000_000
    assert report_dict["valuation_snapshot"]["status"] == "calculated"
    assert report_dict["valuation_snapshot"]["dcf_result"]["fair_value_per_share"] is not None
    assert report_dict["earnings_summary"]["next_earnings_date"] == "2026-07-24"
    assert report_dict["analyst_estimate_summary"]["target_mean_price"] == 390.0
    assert "missing_data_warnings" in report_dict
    assert report_dict["valuation_readiness"]["dcf_ready"] is True
    assert report_dict["local_data_validation"] == []
    assert len(report_dict["data_freshness"]) >= 3
    assert any("research-grade" in " ".join(note["notes"]).lower() for note in report_dict["data_freshness"])
    assert "## How To Read This Report" in markdown
    assert "Read top-down: readiness state first, supported analysis second, blocked or excluded analysis third" in markdown
    assert "Standalone DCF review: company DCF assumptions can be reviewed" in markdown
    assert "project code implements readiness gates and report wording" in markdown
    assert "shipped analysis comes from project code and local data" in markdown
    assert "plugins can help development review" not in markdown
    assert "source readiness: daily snapshot" in markdown
    assert "retrieved 20" not in markdown
    assert "research context only" in markdown
    assert "account actions" in markdown
    assert "Visitor scan: read At A Glance, Reader Guide, Evaluation Snapshot, and Proof Checklist first" in markdown
    assert "## At A Glance" in markdown
    assert "## Reader Guide" in markdown
    assert "## Evaluation Snapshot" in markdown
    assert "## Best Review Path" in markdown
    assert markdown.index("Visitor scan:") < markdown.index("## At A Glance")
    assert markdown.index("## At A Glance") < markdown.index("## How To Read This Report")
    assert (
        markdown.index("## At A Glance")
        < markdown.index("## Reader Guide")
        < markdown.index("## Evaluation Snapshot")
        < markdown.index("## Best Review Path")
        < markdown.index("## How To Read This Report")
    )
    assert "- Mode: `Standalone DCF review`." in markdown
    assert "- Decision view:" in markdown
    assert "- DCF: Ready for scenario review." in markdown
    assert "- Valuation support: Standalone DCF assumptions and sensitivity are reviewable; base scenario fair value/share is $" in markdown
    assert "as scenario math" in markdown
    assert "- Peer context: Locked until source-backed peer inputs are ready." in markdown
    assert "- Optional context: Locked until trusted earnings and analyst-estimate rows exist." in markdown
    assert "- Method: project readiness gates decide what can appear" in markdown
    assert "discounted terminal value, cash/debt adjustment, and fair value per share when ready" in markdown
    assert "- Next local step:" in markdown
    assert "## What We Can Analyze Now" in markdown
    assert "- Analyze now:" in markdown
    assert "- Still locked:" in markdown
    assert "- Trusted input: Source-backed peer mappings and peer valuation inputs." in markdown
    assert "- Data Health lane: Peer Mapping Unlock. Suggested local check: `make focus-peers TICKER=MSFT`" in markdown
    assert "Confirm with `make readiness && make peer-mapping-queue TICKERS=MSFT TOP_N=10` before treating the lane as unlocked" in markdown
    assert "- First read: Start with DCF Calculation Path and Valuation Boundary Checklist" in markdown
    assert "- Then check: What We Can Analyze Now, Valuation Boundary Checklist, and Source Readiness Check." in markdown
    assert "- Copy-only proof step: `make focus-peers TICKER=MSFT`" in markdown
    assert "- Copy next:" not in markdown
    assert "## Executive Summary" in markdown
    assert "Bottom line: MSFT is in `Standalone DCF review` mode" in markdown
    assert "- Confidence: medium: standalone DCF inputs are ready, but peer-relative valuation remains locked." in markdown
    assert "## Data And App Method" in markdown
    assert "## Data Vs Product Logic" not in markdown
    assert "Source inputs: local CSV rows or labeled provider-assisted rows supply prices, fundamentals, peers, earnings, and estimates" in markdown
    assert "Product checks: project readiness gates decide whether each input is usable before report sections appear" in markdown
    assert "DCF method: calculated locally from trusted price, fundamentals, cash-flow or margin, share count, and cash/debt inputs" in markdown
    assert "the report does not ask a third party or model to create a valuation opinion" in markdown
    assert "Peer method: blocked locally until source-backed peer mappings and peer metrics exist" in markdown
    assert "empty optional files are an intentional locked state" in markdown
    assert "ATR / volatility: 3.1% (Volatility proxy approximation)." in markdown
    assert "approximation from close-to-close volatility" in markdown
    assert re.search(r"- 1M performance: -?\d+\.\d%", markdown)
    assert re.search(r"- 3M performance: -?\d+\.\d%", markdown)
    assert re.search(r"- 1Y performance: -?\d+\.\d%", markdown)
    assert re.search(r"- 1M performance: -?0\.\d{3,}", markdown) is None
    assert "Use now:" in markdown
    assert "Do not infer:" in markdown
    assert "Next step:" in markdown
    assert "- Supported evaluation: Company-level review can use local price context, fundamentals, and standalone DCF assumptions" in markdown
    assert "- Valuation boundary: Standalone DCF assumptions can be reviewed, but peer-relative valuation stays locked until source-backed peer inputs exist." in markdown
    assert "- Confidence cue: medium: standalone DCF inputs are ready, but peer-relative valuation remains locked." in markdown
    assert "- Next proof: Not available." in markdown
    assert "- Stop rule: Blocked features:" in markdown
    assert "## Analysis Mode Guide" in markdown
    assert "`Standalone DCF review` (current)" in markdown
    assert (
        "`Data-unlock only` (other): Reference state for tickers with no trusted local inputs yet; add the first missing input before drawing conclusions."
        in markdown
    )
    assert "Do not analyze yet" not in markdown
    for mode in (
        "DCF-ready review",
        "Price/setup review only",
        "Monitor-only context",
        "Data-unlock only",
    ):
        assert f"`{mode}`" in markdown
    assert "Ready inputs:" in markdown
    assert "Supported now:" in markdown
    assert "Still locked or excluded:" in markdown
    assert "## Next Layer To Unlock" in markdown
    assert "Current supported layer: Standalone DCF review; assumptions and sensitivity can be read before peer-relative valuation." in markdown
    assert "Next trusted input: Source-backed peer mappings plus peer price, fundamentals, and valuation inputs." in markdown
    assert "Proof command: `make focus-peers TICKER=MSFT` before treating the next layer as unlocked." in markdown
    assert "Stop rule: if trusted rows are unavailable, leave the section locked; do not infer, backfill, or use placeholders." in markdown
    assert "Excluded features: Not available" not in markdown
    assert "Missing price reason: Not available" not in markdown
    assert "Peer blocker type: not available" not in markdown
    assert "## Analysis Quality" in markdown
    assert "Analysis mode: Standalone DCF review" in markdown
    assert "peer-relative valuation remains limited until trusted peer inputs are ready" in markdown
    assert "## Methodology" in markdown
    assert "Method order: readiness gate first, supported analysis second, valuation math third, explanation last" in markdown
    assert "Input boundary: local or provider-assisted rows supply data; project rules decide readiness, calculations, blockers, and report wording" in markdown
    assert "Analysis recipe: prices unlock setup/trend review; fundamentals unlock field review and DCF input quality" in markdown
    assert "Black-box check: every supported section should trace back to a ready input, a visible formula or score, or an explicit blocker" in markdown
    assert "Methodology proof ladder: input row -> readiness gate -> local calculation or score -> supported/blocked/excluded label -> explicit next step" in markdown
    assert "Reader check path: start with Source Readiness, then Data Readiness, then DCF Calculation Path or Peer Workflow" in markdown
    assert "DCF formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value" in markdown
    assert "DCF status boundary: ready means assumptions can be reviewed, blocked means required company inputs are missing" in markdown
    assert "standalone DCF projects free cash flow under bear/base/bull assumptions" in markdown
    assert "Report method: text is built from local readiness, DCF, peer, decision, and source readiness outputs" in markdown
    assert "## Evaluation Function Check" in markdown
    assert "Readiness gate: strongest function" in markdown
    assert "Price and setup: ready for local trend/setup review" in markdown
    assert "Fundamentals / DCF: ready for standalone DCF assumptions and sensitivity review" in markdown
    assert "Peer comparison: blocked until source-backed peer mappings and peer valuation inputs are ready" in markdown
    assert "readiness gates, DCF boundaries, peer blockers, and report wording are implemented in project code" in markdown
    assert "shipped analysis comes from project code and local data" in markdown
    assert "plugins can help development review" not in markdown
    assert "no open source was used" not in markdown.lower()
    assert "Base DCF scenario fair value/share" in markdown
    assert "DCF input trace: base revenue=$250.0B; base FCF=$90.0B; FCF margin=36.0%; shares outstanding=7.4B" in markdown
    assert "balance-sheet adjustment uses cash=$90.0B; debt=$40.0B" in markdown
    assert "Base DCF assumptions" in markdown
    assert "input path=direct free cash flow" in markdown
    assert "method=fcf_direct" not in markdown
    assert "Scenario coverage: bear, base, bull" in markdown
    assert "Sensitivity table:" in markdown
    assert "Sensitivity snapshot: at WACC 9.0%, TG 2.0% ->" in markdown
    assert "TG 3.0% ->" in markdown
    assert "TG 4.0% ->" in markdown
    assert "## DCF Calculation Path" in markdown
    assert "State: ready; standalone DCF math is calculated locally from trusted price and fundamentals inputs" in markdown
    assert "Input source: local price/fundamentals rows; base revenue=$250.0B; base FCF=$90.0B; shares outstanding=7.4B" in markdown
    assert "Reader takeaway: this is scenario math and methodology evidence, not a price target or direct recommendation" in markdown
    assert "## DCF Input Triage" in markdown
    assert "DCF input triage: required inputs passed readiness for standalone DCF review" in markdown
    assert "Next check: review assumptions, sensitivity, and source readiness; do not convert fair value math into a recommendation" in markdown
    assert "## Valuation Boundary Checklist" in markdown
    assert "DCF boundary: ready for assumption, scenario, and sensitivity review; still research context, not a price target" in markdown
    assert "Peer-relative boundary: blocked until source-backed peer mappings and peer valuation inputs pass readiness" in markdown
    assert "Optional-context boundary: locked until trusted local earnings and analyst-estimate rows pass import validation" in markdown
    assert "Conclusion boundary: missing or excluded inputs do not become intrinsic value, peer-relative value, undervalued, or overvalued conclusions" in markdown
    assert "Reason not ready: Not available" not in markdown
    assert "DCF missing fields: Not available" not in markdown
    assert "missing valuation inputs are not inferred" in markdown
    assert "Relative valuation: blocked until trusted peer mappings and peer valuation inputs are ready" in markdown
    assert "## Data Unlock Summary" in markdown
    assert "## Data Unlock Summary" in markdown.split("## Source Readiness Check")[0]
    assert "Data Health lane: Peer Mapping Unlock" in markdown
    assert "Price unlock:" in markdown
    assert "Fundamentals / DCF unlock:" in markdown
    assert "Peer unlock:" in markdown
    assert "Optional context unlock:" in markdown
    assert "## Copyable Unlock Commands" in markdown
    assert "## Copyable Unlock Commands" in markdown.split("## Source Readiness Check")[0]
    assert "Copy-only: these are local research commands to copy when you choose" in markdown
    assert "the report does not run imports or refreshes and does not connect to external accounts" in markdown
    assert "`make stock-report-md TICKER=MSFT`" in markdown
    assert "Report command: `make stock-report-md TICKER=MSFT`. Research-only Markdown output; copyable command only." in markdown
    assert "Report command: `make stock-report TICKER=MSFT`" not in markdown
    assert "`make trusted-data-pilot-packet TICKER=MSFT`" in markdown
    assert markdown.count("`make trusted-data-pilot-packet TICKER=MSFT`") == 1
    assert "`make focus-fundamentals TICKER=MSFT`" in markdown
    assert "`make focus-peers TICKER=MSFT`" in markdown
    assert "`make optional-context-worklist TICKERS=MSFT TOP_N=10`" in markdown
    assert "`make imports-validate && make imports-preview && make imports-apply`" in markdown
    assert "Peer rebuild proof: `make readiness && make peer-mapping-queue TICKERS=MSFT TOP_N=10`" in markdown
    assert "Optional-context rebuild proof: `make optional-context-readiness && make readiness`" in markdown
    assert "Import paths, rejected-row files, and credential state are listed in the Source Readiness Check below." in markdown
    assert "import file path `data/staged/prices/` or `data/imports/prices.csv`" in markdown
    assert "import file path `data/imports/peers.csv`" in markdown
    assert "import draft path" not in markdown
    assert "preview-first local import workflows" in markdown
    assert "staged path" not in markdown
    assert "staged import workflows" not in markdown


def test_stock_report_purpose_fields_reconcile_report_local_peer_valuation():
    fields = _stock_report_purpose_fields(
        ticker="NVDA",
        readiness={"asset_type": "company", "ready_features": "price, fundamentals, dcf, peer"},
        decision={
            "decision_bucket": "Research Now",
            "decision_subtype": "Research Candidate - Optional Context Locked",
            "primary_blocker": "earnings",
            "data_confidence": "medium",
            "main_reason": "Core data is ready for a supported research pass.",
            "valuation_evaluation": (
                "DCF inputs are ready, but valuation interpretation is constrained by Insufficient Data "
                "and peer status `Peer Data Unavailable`."
            ),
        },
        dcf_status_text="ready",
        peer_ready=True,
        relative_status="calculated",
    )

    valuation = fields["valuation_evaluation"].lower()
    assert "report-local peer valuation is calculated" in valuation
    assert "broad value labels may still remain limited" in valuation
    assert "peer data unavailable" not in valuation
    assert "buy" not in valuation
    assert "sell" not in valuation


def test_stock_report_valuation_lines_withhold_relative_valuation_when_dcf_readiness_is_blocked():
    lines = _stock_report_valuation_lines(
        valuation_snapshot={
            "status": "calculated",
            "dcf_result": {
                "status": "calculated",
                "fair_value_per_share": None,
                "assumptions": {
                    "method_name": "fcf_direct",
                    "revenue_growth": 0.4,
                    "fcf_margin": 0.45,
                    "wacc": 0.09,
                    "terminal_growth": 0.03,
                    "forecast_years": 5,
                },
            },
            "sensitivity_table": {"status": "insufficient_data"},
            "relative_valuation": {
                "status": "calculated",
                "peer_count": 2,
                "missing_fields": ["market_cap_or_price_and_shares"],
                "peer_missing_data_warnings": ["Peer inputs for pe were unavailable for: GOOG."],
            },
            "scenarios": [{"name": "bear"}, {"name": "base"}, {"name": "bull"}],
        },
        valuation_readiness={"dcf_missing_fields": ["shares_outstanding"]},
        dcf={"missing_dcf_fields": "missing shares_outstanding", "reason_not_ready": "missing shares_outstanding"},
        dcf_status_text="blocked",
        monitor_context=False,
    )
    rendered = " ".join(lines).lower()

    assert "dcf status: blocked" in rendered
    assert "dcf status: calculated" not in rendered
    assert "relative valuation: withheld until trusted fundamentals and dcf readiness pass" in rendered
    assert "available peer context is held back until the company dcf gate is ready (peer status=calculated; peer count=2)" in rendered
    assert "background relative-multiple calculation" not in rendered
    assert "relative valuation: calculated from trusted peer inputs" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_missing_data_hides_dcf_normalization_warnings_until_dcf_is_ready():
    payload = {
        "missing_data_warnings": [
            "Observed revenue growth 65.5% exceeded the conservative start-growth cap of 40.0% and was normalized before projection.",
            "Observed FCF margin 113.4% exceeded the conservative margin cap of 45.0% and was normalized before projection.",
            "No trusted earnings CSV has been added yet.",
        ]
    }

    blocked_lines = _stock_report_missing_data_lines(payload, monitor_context=False, dcf_status_text="blocked")
    ready_lines = _stock_report_missing_data_lines(payload, monitor_context=False, dcf_status_text="ready")

    blocked_rendered = " ".join(blocked_lines)
    ready_rendered = " ".join(ready_lines)
    assert "Observed revenue growth" not in blocked_rendered
    assert "Observed FCF margin" not in blocked_rendered
    assert "No trusted earnings CSV has been added yet" in blocked_rendered
    assert "Observed revenue growth" in ready_rendered
    assert "Observed FCF margin" in ready_rendered


def test_stock_report_missing_data_uses_reader_friendly_lock_reasons():
    lines = _stock_report_missing_data_lines(
        {
            "missing_data_warnings": [
                "analyst_estimates has no local row for this ticker.",
                "earnings has no local row for this ticker.",
                "Valuation missing field: shares_outstanding",
                "Peer inputs for pe were unavailable for: GOOG.",
            ]
        },
        monitor_context=False,
        dcf_status_text="ready",
    )

    rendered = " ".join(lines)

    assert "Analyst estimates: no trusted local row for this ticker; optional context stays locked." in rendered
    assert "Earnings: no trusted local row for this ticker; optional context stays locked." in rendered
    assert "Valuation input still missing: shares outstanding." in rendered
    assert "Peer input still missing: P/E unavailable for peer(s) GOOG." in rendered
    assert "analyst_estimates" not in rendered
    assert "shares_outstanding" not in rendered


def test_stock_report_reader_guide_distinguishes_dcf_ready_from_standalone_dcf():
    standalone = " ".join(
        _stock_report_reader_guide_lines(
            dcf_status_text="ready",
            monitor_context=False,
            price_ready=True,
            peer_ready=False,
        )
    )
    full = " ".join(
        _stock_report_reader_guide_lines(
            dcf_status_text="ready",
            monitor_context=False,
            price_ready=True,
            peer_ready=True,
        )
    )

    assert "Standalone DCF review" in standalone
    assert "peer-relative valuation stays locked" in standalone
    assert "DCF-ready review" not in standalone
    assert "DCF-ready review" in full
    assert "Standalone DCF review" not in full


def test_build_stock_report_surfaces_missing_data_risks(tmp_path: Path):
    source = make_source_metadata(
        provider="mock",
        freshness="stale",
        official=False,
        notes=["Limited coverage."],
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
    provider = MockMarketDataProvider(
        quotes={
            "TSLA": QuoteSnapshot(
                ticker="TSLA",
                price=180.0,
                previous_close=179.0,
                open=178.0,
                day_high=181.0,
                day_low=176.0,
                volume=100,
                currency="USD",
                market_time=None,
                source=source,
            )
        },
        histories={("TSLA", "1y", "1d"): pd.DataFrame([{"date": pd.Timestamp("2026-05-11"), "close": 180.0}])},
        financials={"TSLA": FinancialSnapshot(ticker="TSLA", free_cash_flow=None, operating_margin=-0.01, source=source)},
        earnings={"TSLA": EarningsSummary(ticker="TSLA", source=source)},
        estimates={"TSLA": AnalystEstimateSummary(ticker="TSLA", source=source)},
    )

    report = build_stock_report("TSLA", provider)
    markdown = export_stock_report_markdown(report, tmp_path / "tsla-price-setup-report.md")

    assert any("1Y price performance is unavailable" in risk for risk in report.key_risks)
    assert any("Free-cash-flow coverage is unavailable" in risk for risk in report.key_risks)
    assert any("Operating margin is negative" in risk for risk in report.key_risks)
    assert report.valuation_snapshot["status"] == "insufficient_data"
    assert "Current use: Price/setup review only until trusted fundamentals, DCF, and peer inputs are ready." in markdown
    assert "Analysis mode: Price/setup review only" in markdown
    assert "Fundamentals / DCF are blocked:" in markdown
    assert "Inspect `make focus-fundamentals TICKER=TSLA`" in markdown
    assert "`make sec-stage TICKERS=TSLA`" in markdown
    assert "trusted manual fundamentals rows before `make imports-validate`, `make imports-preview`, `make imports-apply`, and `make dcf-readiness`" in markdown
    assert "## Next Layer To Unlock" in markdown
    assert "Current supported layer: Price/setup review only; company valuation stays locked until fundamentals and DCF inputs pass readiness." in markdown
    assert "Next trusted input: Trusted fundamentals, free-cash-flow or margin inputs, share count, and DCF fields." in markdown
    assert "Proof command: `make focus-fundamentals TICKER=TSLA` before treating the next layer as unlocked." in markdown


def test_stock_report_json_export_is_serializable_and_contains_freshness_metadata(tmp_path: Path):
    source = make_source_metadata(
        provider="mock",
        freshness="daily snapshot",
        official=False,
        notes=["Unofficial / research-grade market data."],
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
    provider = MockMarketDataProvider(
        quotes={
            "AAPL": QuoteSnapshot(
                ticker="AAPL",
                price=200.0,
                previous_close=198.0,
                open=199.0,
                day_high=201.0,
                day_low=197.0,
                volume=1000,
                currency="USD",
                market_time="2026-05-11T12:00:00Z",
                source=source,
            )
        },
        histories={("AAPL", "1y", "1d"): pd.DataFrame([{"date": pd.Timestamp("2026-01-01"), "close": 100.0}] * 260)},
        financials={"AAPL": FinancialSnapshot(ticker="AAPL", source=source)},
        earnings={"AAPL": EarningsSummary(ticker="AAPL", source=source)},
        estimates={"AAPL": AnalystEstimateSummary(ticker="AAPL", source=source)},
    )

    report = build_stock_report("AAPL", provider)
    output_path = tmp_path / "report.json"
    payload = export_stock_report_json(report, output_path)
    parsed = json.loads(payload)

    assert output_path.exists()
    assert parsed["ticker"] == "AAPL"
    assert parsed["data_freshness"][0]["provider"] == "mock"
    assert parsed["provider_name"] == "MockMarketDataProvider"
    assert "missing_data_warnings" in parsed
    assert "valuation_readiness" in parsed
    assert "status" in parsed["valuation_snapshot"]
    assert parsed["valuation_snapshot"]["status"] == "insufficient_data"


def test_stock_report_markdown_export_summarizes_readiness_without_advice(tmp_path: Path):
    source = make_source_metadata(
        provider="mock",
        freshness="daily snapshot",
        official=False,
        notes=["Research-grade fixture data."],
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
    provider = MockMarketDataProvider(
        quotes={
            "QQQ": QuoteSnapshot(
                ticker="QQQ",
                price=500.0,
                previous_close=499.0,
                open=499.5,
                day_high=501.0,
                day_low=498.0,
                volume=1_000_000,
                currency="USD",
                market_time="2026-05-27T16:00:00Z",
                source=source,
            )
        },
        histories={("QQQ", "1y", "1d"): pd.DataFrame([{"date": pd.Timestamp("2026-01-01"), "close": 500.0}] * 30)},
        financials={"QQQ": FinancialSnapshot(ticker="QQQ", source=source)},
        earnings={"QQQ": EarningsSummary(ticker="QQQ", source=source)},
        estimates={"QQQ": AnalystEstimateSummary(ticker="QQQ", source=source)},
    )
    report = build_stock_report("QQQ", provider)
    output_path = tmp_path / "qqq.md"
    markdown = export_stock_report_markdown(
        report,
        output_path,
        local_context={
            "readiness": {"overall_readiness_state": "partial", "price_ready": True, "excluded_features": "dcf"},
            "decision": {
                "decision_bucket": "Monitor",
                "decision_subtype": "Monitor - ETF Market Proxy",
                "primary_blocker": "none",
                "main_reason": "ETF market proxy.",
                "next_best_action": "Use as market/risk context.",
                "purpose_thesis": "Purpose: ETF / Defensive / Hedge. Use as market, theme, liquidity, or risk context; operating-company valuation remains excluded.",
                "purpose_alignment": "Purpose alignment: ETF / Defensive / Hedge is evaluated as market/risk context when price, liquidity, and correlation data are ready; operating-company valuation is not applicable.",
                "setup_evaluation": "Setup status: Setup Forming; final state: Setup Forming.",
                "valuation_evaluation": "Operating-company DCF is excluded for this asset type; use market/risk context instead of valuation conclusions.",
                "supported_analysis": "Supported analysis: price history, setup and momentum context, ETF/index monitoring, not operating-company valuation.",
                "unsupported_analysis": "Unsupported analysis: operating-company DCF conclusions.",
                "risk_watchpoint": "Risk watchpoint: monitor liquidity, correlation, and theme exposure; company-specific DCF does not apply.",
                "invalidation_condition": "Invalidate market-proxy usefulness if liquidity, correlation, or theme trend no longer supports the intended monitoring role.",
                "next_research_question": "Which source-backed peer mappings or peer metrics would make the market-proxy comparison more trustworthy?",
                "review_priority_reason": "Monitor priority: use this proxy for market, theme, liquidity, or risk context; do not treat it as operating-company valuation.",
                "confidence_explanation": "Data confidence is medium: monitoring is supported by price, momentum, market_direction, while optional context remains unavailable.",
            },
            "dcf": {"reason_not_ready": "DCF excluded for etf."},
            "peer": {
                "peer_blocker_type": "missing_peer_mapping",
                "mapping_status": "missing_mapping",
                "peer_count": 0,
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
                "next_peer_action": "Add source-backed peer mappings for QQQ.",
            },
        },
    )

    assert output_path.exists()
    assert "# QQQ Single-Stock Research Report" in markdown
    for heading in (
        "## How To Read This Report",
        "## Executive Summary",
        "## Analysis Quality",
        "## Methodology",
        "## Evaluation Function Check",
        "## What This Stock Is",
        "## Data Readiness",
        "## Supported Analysis",
        "## Setup / Momentum",
        "## Valuation Readiness",
        "## DCF Calculation Path",
        "## Peer Workflow",
        "## Risk Notes",
        "## Source Readiness",
        "## Next Research Step",
    ):
        assert heading in markdown
    assert "## One-Minute Status" in markdown
    assert "## Reader Guide" in markdown
    assert "- Analyze now: Monitor context is supported where local price, liquidity, correlation, and theme data are available." in markdown
    assert "- Still locked: Blocked features: none. Excluded features: DCF." in markdown
    assert "- Trusted input: No company DCF input is required for monitor context." in markdown
    assert "- Data Health lane: Single-Stock Review. Suggested local check: `make stock-report-md TICKER=QQQ`" in markdown
    assert "## Next Layer To Unlock" in markdown
    assert "## Proof Checklist" in markdown
    assert "Current mode proof: `Monitor-only context` because asset-type gate marks this as monitor context" in markdown
    assert "Next unlock proof: `make stock-report-md TICKER=QQQ` after any local data changes" in markdown
    assert "Withhold until proven: Blocked features: none. Excluded features: DCF" in markdown
    assert "Current supported layer: Monitor-only context; market, theme, liquidity, or risk review can be read when local inputs are ready." in markdown
    assert "Next trusted input: No operating-company DCF or peer-valuation input is required for this monitor role." in markdown
    assert "Proof command: `make stock-report-md TICKER=QQQ` before treating the next layer as unlocked." in markdown
    assert "Bottom line: QQQ is in `Monitor-only context` mode" in markdown
    assert "`Monitor-only context` (current)" in markdown
    assert "Decision: Monitor - ETF Market Proxy" in markdown
    assert "Monitor - ETF Market Proxy" in markdown
    assert "Research-only local report" in markdown
    assert "Monitor-only context when local price, liquidity, correlation, or theme inputs are ready" in markdown
    assert "shipped analysis comes from project code and local data" in markdown
    assert "plugins can help development review" not in markdown
    assert "source readiness:" in markdown
    assert "retrieved 20" not in markdown
    assert "allocation instructions" in markdown
    assert "trade instruction" not in markdown.lower()
    assert "transaction execution" not in markdown.lower()
    assert "execute transactions" not in markdown.lower()
    assert "DCF: excluded" in markdown
    assert "- Valuation support: Monitor context only; operating-company DCF and peer valuation are excluded." in markdown
    assert "Analysis mode: Monitor-only context" in markdown
    assert "Operating-company DCF and peer valuation are excluded, not failed" in markdown
    assert "Fundamentals / DCF: excluded for ETF/index/fund monitor context, not failed" in markdown
    assert "Peer comparison: excluded for monitor context" in markdown
    assert "Method source: readiness gates, DCF boundaries, peer blockers, and report wording are implemented in project code" in markdown
    assert "DCF applicability: excluded" in markdown
    assert "not a failed valuation input" in markdown
    assert "State: excluded; operating-company DCF is not the right method for ETF/index/fund monitor context" in markdown
    assert "Formula path: not run for this ticker because the asset-type gate excludes company DCF" in markdown
    assert "## DCF Input Triage" in markdown
    assert "DCF input triage: not required for ETF/index/fund monitor context; operating-company valuation is excluded rather than repaired" in markdown
    assert "Optional earnings or analyst-estimate context is unavailable" in markdown
    assert "## Purpose Evaluation" in markdown
    assert "Research-only purpose brief" in markdown
    assert "Thesis" in markdown
    assert "Alignment" in markdown
    assert "Research review summary: Monitor context" in markdown
    assert "operating-company DCF and peer valuation are excluded" in markdown
    assert "ETF / Defensive / Hedge" in markdown
    assert "market/risk context" in markdown
    assert "## Supported Analysis" in markdown
    assert "## Locked Analysis" in markdown
    assert "## Risk Notes" in markdown
    assert "market, theme, liquidity, or risk context" in markdown
    assert "Operating-company DCF is excluded" in markdown
    assert "Supported analysis" in markdown
    assert "Currently withheld" in markdown
    assert "operating-company DCF conclusions" in markdown
    assert "Invalidate market-proxy usefulness" in markdown
    assert "What market, theme, liquidity, or risk context should QQQ monitor" in markdown
    assert "Which source-backed peer mappings or peer metrics would make the market-proxy comparison more trustworthy" not in markdown
    assert "Monitor priority" in markdown
    assert "## Source Readiness Check" in markdown
    assert "data/staged/earnings/" in markdown
    assert "make import-analyst-estimates" in markdown
    assert "STOOQ_API_KEY" in markdown
    assert "DCF excluded for etf" not in markdown
    assert "company valuation fields are not treated as repair items" in markdown
    assert "Valuation missing field:" not in markdown
    assert "fundamentals has no local row" not in markdown.lower()
    assert "Peer Workflow" in markdown
    assert "What this means: peer-relative company valuation is excluded for ETF/index/fund monitor context" in markdown
    assert "What is still locked: operating-company peer valuation is not a repair item for this monitor role" in markdown
    assert "Trusted input path: no peer import is required for monitor context; do not add guessed peers to force valuation" in markdown
    assert "Peer ladder: monitor context; operating-company peer valuation is excluded rather than repaired" in markdown
    assert "Mapping evidence: optional context only for ETF/index/fund monitor rows; do not add guessed peers to force company valuation" in markdown
    assert "Valuation evidence: excluded; no peer-relative premium/discount or peer DCF comparison is shown" in markdown
    assert "Primary blocker: monitor context" in markdown
    assert "Peer blocker type: monitor context" in markdown
    assert "Missing price reason: none" in markdown
    assert "No peer import is required" in markdown
    assert "Add source-backed peer mappings for QQQ" not in markdown
    assert "buy" not in markdown.lower()
    assert "sell" not in markdown.lower()


def test_stock_report_markdown_prioritizes_peer_action_when_primary_blocker_is_peers(tmp_path: Path):
    source = make_source_metadata(
        provider="mock",
        freshness="daily snapshot",
        official=False,
        notes=["Research-grade fixture data."],
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
    provider = MockMarketDataProvider(
        quotes={
            "COHR": QuoteSnapshot(
                ticker="COHR",
                price=80.0,
                previous_close=79.0,
                open=79.5,
                day_high=81.0,
                day_low=78.0,
                volume=1_000_000,
                currency="USD",
                market_time="2026-05-27T16:00:00Z",
                source=source,
            )
        },
        histories={("COHR", "1y", "1d"): pd.DataFrame([{"date": pd.Timestamp("2026-01-01"), "close": 80.0}] * 30)},
        financials={"COHR": FinancialSnapshot(ticker="COHR", source=source)},
        earnings={"COHR": EarningsSummary(ticker="COHR", source=source)},
        estimates={"COHR": AnalystEstimateSummary(ticker="COHR", source=source)},
    )
    report = build_stock_report("COHR", provider)
    peer_action = "Add at least 2 source-backed peer mappings for COHR in data/imports/peers.csv."
    optional_action = "Optional context missing for COHR; leave unavailable unless trusted local CSVs exist."
    markdown = export_stock_report_markdown(
        report,
        tmp_path / "cohr.md",
        local_context={
            "readiness": {
                "overall_readiness_state": "partial",
                "price_ready": True,
                "fundamentals_ready": True,
                "dcf_ready": True,
                "peer_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
            },
            "decision": {
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - DCF Ready But Peer Blocked",
                "primary_blocker": "peers",
                "main_reason": "Core data is ready for a supported research pass.",
                "next_best_action": optional_action,
            },
            "peer": {
                "peer_blocker_type": "peer_valuation_blocked",
                "mapping_status": "mapped",
                "peer_count": 2,
                "peer_trend_comparison_ready": "True",
                "peer_valuation_comparison_ready": "False",
                "next_peer_action": peer_action,
            },
        },
    )

    assert f"Next: {peer_action}" in markdown
    assert "## Analysis Quality" in markdown
    assert "Analysis mode: Standalone DCF review" in markdown
    assert "peer-relative valuation remains limited until trusted peer inputs are ready" in markdown
    assert "- Boundary: Workflow state only: standalone company and DCF review can continue" in markdown
    assert "peer-relative valuation stays locked until trusted peer inputs are ready" in markdown
    assert f"- Next action: {peer_action}" in markdown
    assert "Research review summary:" in markdown
    assert "Research workflow summary:" not in markdown
    assert "Next blocker: peers" in markdown
    assert "Withheld:" in markdown
    assert "Purpose status unavailable" not in markdown
    assert "Which source-backed peers should be added for COHR" in markdown
    assert "## Proof Checklist" in markdown
    assert "Current mode proof: `Standalone DCF review` because standalone DCF passed local readiness" in markdown
    assert "Next unlock proof: `make focus-peers TICKER=COHR` with source-backed peer mappings and peer inputs" in markdown
    assert "What this means: standalone DCF can be reviewed, but peer-relative valuation is locked by peer valuation blocked" in markdown
    assert "peer trend comparison can be reviewed from mapped peer price history" in markdown
    assert "but peer-relative valuation, premium/discount, and peer DCF comparison stay withheld" in markdown
    assert "Mapped peer count=2" in markdown
    assert "What is still locked: peer valuation, peer-relative premium/discount, and peer DCF comparison" in markdown
    assert "Trusted input path: add source-backed rows in `data/imports/peers.csv`" in markdown
    assert "Peer ladder: standalone DCF can be reviewed before peer valuation is ready" in markdown
    assert "Mapping evidence: mapping status=mapped; peer count=2; blocker=peer valuation blocked" in markdown
    assert "Trend evidence: possible from mapped peer price history" in markdown
    assert "Valuation evidence: locked; do not show peer-relative premium/discount, peer valuation comparison, or peer DCF comparison" in markdown
    assert "Trusted peer path: add source-backed rows in `data/imports/peers.csv`" in markdown
    assert "make imports-validate" in markdown
    assert "Fallback boundary: sector or industry context is fallback only; it is not trusted manual peer data" in markdown
    assert "## Optional Context Workflow" in markdown
    assert "Optional context ladder: earnings and analyst estimates add timing, consensus, and revision context only" in markdown
    assert "Earnings evidence: locked; missing trusted local CSV input is an intentional state, not broken analysis" in markdown
    assert "Analyst-estimate evidence: locked; missing trusted local CSV input is an intentional state, not hidden consensus analysis" in markdown
    assert "Rejected-row checks: review `data/rejected/earnings_import_rejected.csv` and `data/rejected/analyst_estimates_import_rejected.csv`" in markdown
    assert "Rebuild proof: run `make optional-context-readiness`, then `make stock-report-md TICKER=COHR`" in markdown
    assert optional_action not in markdown
    assert "copyable command only" in markdown
    assert "trade instruction" not in markdown.lower()
    assert "transaction execution" not in markdown.lower()


def test_readiness_only_markdown_handles_blocked_broad_universe_ticker_without_advice():
    markdown = build_readiness_only_markdown(
        "APLD",
        {
            "readiness": {
                "overall_readiness_state": "blocked",
                "asset_type": "company",
                "price_ready": False,
                "blocked_features": "price, momentum, dcf",
                "missing_data": "needs at least 5 valid price rows with positive close",
                "next_action": "Import price rows through the preview-first workflow or refresh the price provider for APLD.",
            },
            "decision": {
                "decision_bucket": "Blocked by Data",
                "decision_subtype": "Blocked by Data - Missing Price",
                "primary_blocker": "price",
                "main_reason": "Missing usable price data.",
                "next_best_action": "Import price rows through the preview-first workflow or refresh the price provider for APLD.",
                "purpose_thesis": "Purpose: Speculative Optionality. Interpretation is blocked until price history is available.",
                "purpose_alignment": "Purpose alignment for Speculative Optionality cannot be checked until usable price history exists.",
                "setup_evaluation": "Setup cannot be evaluated because usable price history is missing.",
                "valuation_evaluation": "Valuation conclusion is blocked until trusted DCF/fundamental inputs are complete.",
                "supported_analysis": "Supported analysis: none yet; this row is an unlock checklist until core inputs are available.",
                "unsupported_analysis": "Unsupported analysis: trend, setup, liquidity, volatility, and relative strength, DCF interpretation.",
                "risk_watchpoint": "Primary risk is analytical blindness from missing price history; do not interpret trend or volatility yet.",
                "invalidation_condition": "Invalidate any setup read until price history is available and passes readiness checks.",
                "next_research_question": "Can trusted local price rows be staged for APLD so trend, liquidity, and downstream analysis become testable?",
                "review_priority_reason": "Unlock priority: price is the first blocker before setup, valuation, or risk interpretation should be trusted.",
                "confidence_explanation": "Data confidence is low because the primary blocker is price; current output is an unlock checklist, not analysis.",
            },
            "price_coverage": {"price_rows": 0, "missing_price_reason": "needs at least 5 valid price rows"},
            "peer": {
                "peer_blocker_type": "missing_peer_mapping",
                "mapping_status": "missing_mapping",
                "peer_count": 0,
                "next_peer_action": "Add source-backed peer mappings after price data exists.",
            },
        },
        "No local price rows were found for APLD.",
    )

    assert "data-unlock report" in markdown
    assert "First blocker to resolve: No local price rows were found for APLD." in markdown
    assert "full stock-report provider" not in markdown
    assert "Provider blocker" not in markdown
    assert "could not assemble price-backed analysis" not in markdown
    assert "# APLD Single-Stock Research Report" in markdown
    assert "Visitor scan: read At A Glance, Reader Guide, Evaluation Snapshot, and Proof Checklist first" in markdown
    assert "## At A Glance" in markdown
    assert "## Reader Guide" in markdown
    assert "## Evaluation Snapshot" in markdown
    assert markdown.index("Visitor scan:") < markdown.index("## At A Glance")
    assert markdown.index("## At A Glance") < markdown.index("## How To Read This Report")
    assert (
        markdown.index("## At A Glance")
        < markdown.index("## Reader Guide")
        < markdown.index("## Evaluation Snapshot")
        < markdown.index("## How To Read This Report")
    )
    assert "- Mode: `Data-unlock only`." in markdown
    assert "- DCF: Blocked until trusted fundamentals and DCF inputs are ready." in markdown
    assert "- Valuation support: Blocked until trusted price, fundamentals, cash-flow or margin, and share-count inputs are ready." in markdown
    assert "- Peer context: Locked until source-backed peer inputs are ready." in markdown
    assert "- Boundary: Data-unlock state: price blocks evaluation, so conclusions stay withheld." in markdown
    assert "- Optional context: Locked until trusted earnings and analyst-estimate rows exist." in markdown
    assert "- Method: project readiness gates decide what can appear" in markdown
    assert "discounted terminal value, cash/debt adjustment, and fair value per share when ready" in markdown
    assert "## How To Read This Report" in markdown
    assert "- Analyze now: Use available price or setup context only." in markdown
    assert "- Still locked: Blocked features: price, momentum, DCF." in markdown
    assert "- Trusted input: Trusted local price history." in markdown
    assert "- Data Health lane: Price Coverage Batch. Suggested local check: `make focus-price TICKER=APLD`" in markdown
    assert "Confirm with `make price-coverage TOP_N=25 && make readiness` before treating the lane as unlocked" in markdown
    assert "- Supported evaluation: Use available price or setup context only." in markdown
    assert "- Valuation boundary: Company valuation is blocked until trusted fundamentals, cash-flow or margin, share-count, and DCF inputs pass readiness." in markdown
    assert "- Confidence cue: low: price history is still the first required unlock." in markdown
    assert "- Stop rule: Blocked features: price, momentum, DCF." in markdown
    assert "## Proof Checklist" in markdown
    assert "Current mode proof: `Data-unlock only` because trusted local price history is not ready" in markdown
    assert "Next unlock proof: `make focus-price TICKER=APLD` followed by readiness rebuild" in markdown
    assert "Withhold until proven: Blocked features: price, momentum, DCF" in markdown
    assert "Data-unlock only until trusted price, fundamentals, DCF, and peer inputs are ready" in markdown
    assert "Read top-down: readiness state first" in markdown
    assert "## Executive Summary" in markdown
    assert "Bottom line: APLD is in `Data-unlock only` mode" in markdown
    assert "Ready inputs: none yet." in markdown
    assert "Next step: Add or refresh trusted local price history for APLD" in markdown
    assert "## Next Layer To Unlock" in markdown
    assert "Current supported layer: Data-unlock only; conclusions stay withheld until trusted local price history exists." in markdown
    assert "Next trusted input: Trusted local price history." in markdown
    assert "Proof command: `make focus-price TICKER=APLD` before treating the next layer as unlocked." in markdown
    assert "`Data-unlock only` (current)" in markdown
    assert (
        "`Data-unlock only` (current): Pause analysis for this ticker until the first trusted local input is available."
        in markdown
    )
    assert "## What This Stock Is" in markdown
    assert "## Analysis Quality" in markdown
    assert "## Data And App Method" in markdown
    assert "## Data Vs Product Logic" not in markdown
    assert "DCF method: blocked locally because required price, fundamentals, cash-flow or margin, share count, or DCF fields are missing" in markdown
    assert "Peer method: blocked locally until source-backed peer mappings and peer metrics exist" in markdown
    assert "empty optional files are an intentional locked state" in markdown
    assert "## Methodology" in markdown
    assert "## Evaluation Function Check" in markdown
    assert "Analysis mode: Data-unlock only" in markdown
    assert "Analysis recipe: prices unlock setup/trend review; fundamentals unlock field review and DCF input quality" in markdown
    assert "Black-box check: every supported section should trace back to a ready input, a visible formula or score, or an explicit blocker" in markdown
    assert "DCF formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value" in markdown
    assert "standalone DCF stays blocked until trusted local price, revenue, free cash flow or FCF margin" in markdown
    assert "DCF assumptions: withheld until price, fundamentals, free cash flow or FCF margin" in markdown
    assert "DCF assumptions: hidden" not in markdown
    assert "Start with verified local price history before relying on momentum" in markdown
    assert "Price and setup: locked until enough trusted price history is available" in markdown
    assert "Fundamentals / DCF: blocked until trusted fundamentals, cash-flow or margin, share-count, and DCF inputs are ready" in markdown
    assert "Optional context: locked until trusted local earnings and analyst-estimate rows exist" in markdown
    assert "shipped analysis comes from project code and local data" in markdown
    assert "plugins can help development review" not in markdown
    assert "## Data Readiness" in markdown
    assert "## Valuation Readiness" in markdown
    assert "DCF missing inputs:" in markdown
    assert "Why DCF is blocked:" in markdown
    assert "## DCF Input Triage" in markdown
    assert "DCF input triage: blocked inputs are repair steps, not negative company signals" in markdown
    assert "Safe sequence: `make focus-fundamentals TICKER=APLD` -> stage SEC or trusted manual fundamentals rows -> `make imports-validate` -> `make imports-preview` -> `make imports-apply` -> `make dcf-readiness`" in markdown
    assert "`make trusted-data-pilot-packet TICKER=APLD`" in markdown
    assert "Relative valuation: withheld until trusted fundamentals and DCF readiness pass" in markdown
    assert "available peer context is held back until the company DCF gate is ready" in markdown
    assert "background relative-multiple calculation" not in markdown
    assert "## DCF Calculation Path" in markdown
    assert "State: blocked; the product withholds DCF math until trusted company inputs pass readiness checks" in markdown
    assert "Formula path: withheld before base FCF, projected FCF, terminal value, equity value, or fair value/share are calculated" in markdown
    assert "## Valuation Boundary Checklist" in markdown
    assert "DCF boundary: blocked until trusted price, fundamentals, cash-flow or margin, share-count, and DCF fields pass readiness" in markdown
    assert "Peer-relative boundary: withheld until trusted fundamentals and DCF readiness pass first" in markdown
    assert "Conclusion boundary: missing or excluded inputs do not become intrinsic value, peer-relative value, undervalued, or overvalued conclusions" in markdown
    assert "## Risk Notes" in markdown
    assert "## Next Research Step" in markdown
    assert "allocation instructions" in markdown
    assert "trade instruction" not in markdown.lower()
    assert "transaction execution" not in markdown.lower()
    assert "## One-Minute Status" in markdown
    assert "Decision: Blocked by Data - Missing Price" in markdown
    assert "Primary blocker: price" in markdown
    assert "Blocked by Data - Missing Price" in markdown
    assert "DCF: blocked" in markdown
    assert "## Purpose Evaluation" in markdown
    assert "Research-only purpose brief" in markdown
    assert "Research review summary:" in markdown
    assert "Research workflow summary:" not in markdown
    assert "Next blocker: price" in markdown
    assert "Can trusted local price rows be staged for APLD" in markdown
    assert "Purpose alignment for Speculative Optionality cannot be checked" in markdown
    assert "Setup cannot be evaluated because usable price history is missing" in markdown
    assert "## Supported Analysis" in markdown
    assert "## Locked Analysis" in markdown
    assert "Supported analysis: none yet" in markdown
    assert "Currently withheld: trend, setup, liquidity" in markdown
    assert "analytical blindness" in markdown
    assert "Unlock priority: price is the first blocker" in markdown
    assert "primary blocker is price" in markdown
    assert "## Data Unlock Summary" in markdown
    assert "Data Health lane: Price Coverage Batch" in markdown
    assert "Price history is the first unlock" in markdown
    assert "make focus-price TICKER=APLD" in markdown
    assert "## Copyable Unlock Commands" in markdown
    assert "`make price-worklist TICKERS=APLD TOP_N=10`" in markdown
    assert "`make price-validate && make price-preview && make price-apply`" in markdown
    assert "Price rebuild proof: `make price-coverage TOP_N=25 && make readiness`" in markdown
    assert "`make focus-fundamentals TICKER=APLD`" in markdown
    assert "DCF rebuild proof: `make dcf-readiness && make readiness`" in markdown
    assert "`make peer-mapping-queue TICKERS=APLD TOP_N=10`" in markdown
    assert "`make optional-context-worklist TICKERS=APLD TOP_N=10`" in markdown
    assert "the report does not run imports or refreshes and does not connect to external accounts" in markdown
    assert "Wait on fundamentals / DCF interpretation until price coverage starts" in markdown
    assert "After `make focus-price TICKER=APLD` is resolved, run `make focus-fundamentals TICKER=APLD`" in markdown
    assert "Peer valuation should wait until trusted price, fundamentals, and DCF inputs are ready" in markdown
    assert "## Source Readiness Check" in markdown
    assert "Report command: `make stock-report-md TICKER=APLD`. Research-only Markdown output; copyable command only." in markdown
    assert "Report command: `make stock-report TICKER=APLD`" not in markdown
    assert "data/staged/prices/" in markdown
    assert "data/rejected/price_import_rejected.csv" in markdown
    assert "Peer Workflow" in markdown
    assert "What this means: peer valuation waits behind price, fundamentals, and standalone DCF readiness" in markdown
    assert "What can be reviewed now: only the ready local inputs listed above; peer rows should not create valuation context yet" in markdown
    assert "Trusted input path: resolve fundamentals / DCF first, then use `make focus-peers TICKER=APLD` if peer context is still needed" in markdown
    assert "Peer ladder: paused behind core company readiness" in markdown
    assert "Do not use peer rows to bypass missing price, fundamentals, or DCF inputs" in markdown
    assert "Valuation evidence: withheld until standalone DCF plus source-backed peer mappings and peer valuation inputs pass readiness" in markdown
    assert "blocked until fundamentals / DCF" in markdown
    assert "## Optional Context Workflow" in markdown
    assert "No-conclusion boundary: missing earnings or estimates must not appear as event timing, consensus, revision, upside, downside, undervalued, or overvalued analysis" in markdown
    assert "Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready" in markdown
    assert "Add source-backed peer mappings after price data exists" not in markdown
    assert "No local price rows were found for APLD" in markdown
    assert "buy" not in markdown.lower()
    assert "sell" not in markdown.lower()


def test_create_stock_report_payload_uses_local_provider_when_csvs_are_available(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,MSFT,100,1000\n"
        "2026-05-11,MSFT,130,1100\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "fundamentals.csv").write_text(
        "ticker,profit_margin,operating_margin,pe_ratio\n"
        "MSFT,0.30,0.35,28\n",
        encoding="utf-8",
    )

    payload = create_stock_report_payload("MSFT", provider_name="local", base_dir=tmp_path)

    assert payload["ticker"] == "MSFT"
    assert payload["price_snapshot"]["price"] == 130.0
    assert payload["financial_summary"]["profit_margin"] == 0.30
    assert payload["data_freshness"][0]["provider"] == "local:prices.csv"
    assert payload["dataset_coverage"]
    assert "local_data_validation" in payload
    assert "valuation_readiness" in payload
    assert payload["valuation_snapshot"]["status"] == "calculated"
    assert payload["valuation_snapshot"]["coverage"] == "partial"


def test_stock_report_cli_fails_gracefully_for_missing_local_ticker(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,SPY,100,1000\n",
        encoding="utf-8",
    )
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--ticker", "AAPL", "--provider", "local"]
    try:
        with pytest.raises(SystemExit, match="Stock report generation failed: No local price rows were found for AAPL"):
            main()
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_cli_quiet_mode_writes_markdown_without_full_json(tmp_path: Path, capsys):
    _copy_rich_fixture(tmp_path)
    markdown_path = tmp_path / "outputs" / "stock_reports" / "alfa.md"
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]
    sys.argv = [
        "python",
        "--project-root",
        str(tmp_path),
        "--ticker",
        "ALFA",
        "--provider",
        "local",
        "--markdown-output",
        str(markdown_path),
        "--quiet",
    ]
    try:
        main()
        output = capsys.readouterr().out
        assert "Markdown report:" in output
        assert "outputs/stock_reports/alfa.md" in output
        assert str(tmp_path) not in output
        assert "Project root:" not in output
        assert "Data dir:" not in output
        assert "Outputs dir:" not in output
        assert '"ticker": "ALFA"' not in output
        assert markdown_path.exists()
        markdown = markdown_path.read_text(encoding="utf-8")
        assert "Relative valuation: calculated; peer count=2" in markdown
        assert "Relative valuation: blocked until trusted peer mappings" not in markdown
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_cli_lists_local_tickers(tmp_path: Path, capsys):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,SPY,100,1000\n"
        "2026-01-03,QQQ,101,1001\n",
        encoding="utf-8",
    )
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--list-local-tickers"]
    try:
        main()
        output = capsys.readouterr().out.strip().splitlines()
        assert f"Project root: {tmp_path}" in output
        assert output[-2:] == ["QQQ", "SPY"]
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_cli_validate_local_data_json(tmp_path: Path, capsys):
    _copy_rich_fixture(tmp_path)
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--validate-local-data", "--json"]
    try:
        main()
        payload = json.loads(capsys.readouterr().out)
        assert any(item["name"] == "fundamentals" for item in payload)
        assert any(item["name"] == "peers" for item in payload)
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_cli_validate_local_data_human_output(tmp_path: Path, capsys):
    _copy_rich_fixture(tmp_path)
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--validate-local-data"]
    try:
        main()
        output = capsys.readouterr().out
        assert "prices: status=valid" in output
        assert "fundamentals: status=valid" in output
        assert "peers: status=valid" in output
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_cli_write_local_data_templates(tmp_path: Path, capsys):
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--write-local-data-templates"]
    try:
        main()
        output = capsys.readouterr().out
        assert "fundamentals: created" in output
        assert "peers: created" in output
        assert (tmp_path / "data" / "templates" / "fundamentals.csv").exists()
        assert (tmp_path / "data" / "templates" / "peers.csv").exists()
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_cli_write_local_data_templates_json(tmp_path: Path, capsys):
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--write-local-data-templates", "--json"]
    try:
        main()
        payload = json.loads(capsys.readouterr().out)
        assert any(item["dataset_name"] == "fundamentals" for item in payload)
        assert any(item["dataset_name"] == "analyst_estimates" for item in payload)
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_cli_write_import_staging(tmp_path: Path, capsys):
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--write-import-staging"]
    try:
        main()
        output = capsys.readouterr().out
        assert "fundamentals: created" in output
        assert (tmp_path / "data" / "imports" / "fundamentals.csv").exists()
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_cli_validate_imports_handles_no_staged_files(tmp_path: Path, capsys):
    (tmp_path / "data").mkdir()
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--validate-imports"]
    try:
        main()
        output = capsys.readouterr().out.strip()
        assert "no_staged_files:" in output
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_cli_validate_imports_json(tmp_path: Path, capsys):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "imports").mkdir()
    (tmp_path / "data" / "imports" / "fundamentals.csv").write_text(
        "ticker,revenue,source,as_of_date\n"
        "NVDA,1000,manual,2026-05-01\n",
        encoding="utf-8",
    )
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--validate-imports", "--json"]
    try:
        main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "valid"
        assert payload["files"][0]["file_name"] == "fundamentals.csv"
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_cli_preview_import_merge_handles_no_staged_files(tmp_path: Path, capsys):
    (tmp_path / "data").mkdir()
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--preview-import-merge"]
    try:
        main()
        output = capsys.readouterr().out.strip()
        assert "no_staged_files:" in output
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_cli_apply_import_merge_updates_canonical_file(tmp_path: Path, capsys):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "imports").mkdir()
    (tmp_path / "data" / "fundamentals.csv").write_text(
        "ticker,revenue,source,as_of_date\n"
        "MSFT,1000,old,2026-01-01\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "imports" / "fundamentals.csv").write_text(
        "ticker,revenue,source,as_of_date\n"
        "MSFT,1100,new,2026-05-01\n",
        encoding="utf-8",
    )
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--apply-import-merge"]
    try:
        main()
        output = capsys.readouterr().out
        assert "fundamentals.csv: applied=True" in output
        payload = pd.read_csv(tmp_path / "data" / "fundamentals.csv")
        assert payload.loc[0, "revenue"] == 1100
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_cli_preview_import_merge_json(tmp_path: Path, capsys):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "imports").mkdir()
    (tmp_path / "data" / "imports" / "fundamentals.csv").write_text(
        "ticker,revenue,source,as_of_date\n"
        "NVDA,1000,manual,2026-05-01\n",
        encoding="utf-8",
    )
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--preview-import-merge", "--json"]
    try:
        main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "valid"
        assert payload["preview"][0]["file_name"] == "fundamentals.csv"
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_cli_apply_import_merge_json(tmp_path: Path, capsys):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "imports").mkdir()
    (tmp_path / "data" / "fundamentals.csv").write_text(
        "ticker,revenue,source,as_of_date\n"
        "MSFT,1000,old,2026-01-01\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "imports" / "fundamentals.csv").write_text(
        "ticker,revenue,source,as_of_date\n"
        "MSFT,1100,new,2026-05-01\n",
        encoding="utf-8",
    )
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--apply-import-merge", "--json"]
    try:
        main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "applied"
        assert payload["applied"][0]["file_name"] == "fundamentals.csv"
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_cli_sec_stage_json_surfaces_make_based_follow_up(monkeypatch, tmp_path: Path, capsys):
    (tmp_path / "data").mkdir()
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    previous_argv = sys.argv[:]

    monkeypatch.setattr(
        "src.stock_report.build_sec_fundamentals_rows",
        lambda requested_tickers, user_agent, cache_dir, refresh: {
            "requested_tickers": requested_tickers,
            "resolved_tickers": requested_tickers,
            "unresolved_tickers": [],
            "rows": [{"ticker": requested_tickers[0], "revenue": 1000}],
            "warnings": [],
            "row_summaries": [{"ticker": requested_tickers[0], "populated_fields": ["revenue"], "missing_fields": [], "warnings": []}],
        },
    )
    monkeypatch.setattr(
        "src.stock_report.write_sec_fundamentals_import",
        lambda rows, output_path, overwrite: {
            "rows_written": len(rows),
            "staged_row_count": len(rows),
            "output_path": str(output_path),
        },
    )

    sys.argv = ["python", "--project-root", str(tmp_path), "--sec-stage-fundamentals", "--tickers", "NVDA", "--json"]
    try:
        main()
        payload = json.loads(capsys.readouterr().out)
        assert payload["recommended_next_commands"] == [
            "make imports-validate",
            "make imports-preview",
            "make imports-apply",
        ]
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def test_stock_report_from_rich_local_fixture_is_serializable_and_includes_validation(tmp_path: Path):
    payload = create_stock_report_payload("ALFA", provider_name="local", base_dir=_copy_rich_fixture(tmp_path))

    assert payload["valuation_snapshot"]["dcf_result"]["status"] == "calculated"
    assert payload["valuation_snapshot"]["relative_valuation"]["status"] == "calculated"
    assert payload["valuation_readiness"]["dcf_ready"] is True
    assert payload["valuation_readiness"]["peer_ready"] is True
    assert payload["valuation_snapshot"]["relative_valuation"]["peer_group"] == "fixture_group"
    assert payload["valuation_snapshot"]["relative_valuation"]["peer_tickers"] == ["BETA", "GAMMA"]
    assert payload["valuation_snapshot"]["relative_valuation"]["relative_discount_premium_by_metric"]["pe"] is not None
    assert payload["valuation_readiness"]["peer_count"] == 2
    assert payload["valuation_readiness"]["earnings_available"] is True
    assert payload["valuation_readiness"]["analyst_estimates_available"] is True
    assert payload["local_data_validation"]
    assert any(item["name"] == "peers" for item in payload["local_data_validation"])
