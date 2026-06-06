from pathlib import Path

import src.dashboard as dashboard
import pandas as pd


def test_dashboard_format_helpers_hide_raw_missing_values():
    assert dashboard.format_missing(None) == "Not available"
    assert dashboard.format_missing(float("nan")) == "Not available"
    assert dashboard.format_percent(None) == "Not enough history"
    assert dashboard.format_date_short("2026-03-14T00:00:00") == "2026-03-14"
    assert "nan" not in dashboard.score_badge(None).lower()
    cleaned = dashboard.clean_display_frame(pd.DataFrame({"Ready": [True, False]}))
    assert cleaned.iloc[0]["Ready"] == "Yes"
    assert cleaned.iloc[1]["Ready"] == "No"
    assert dashboard.public_status_label("insufficient_data") == "Insufficient data"
    assert dashboard.public_status_label("peer_data_unavailable") == "Peer data unavailable"
    assert dashboard.public_status_label("monitor_context") == "Monitor context"
    assert dashboard.public_status_label("not_ready") == "Not ready"
    assert dashboard.public_status_label("Broken") == "Thesis Review Needed"
    assert dashboard.public_status_label("Avoid") == "No Setup"

    action_rows = dashboard.clean_display_frame(
        pd.DataFrame(
            {
                "recommended_action": [
                    "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local fundamentals."
                ]
            }
        )
    )
    assert "make status-check TOP_N=5" in action_rows.iloc[0]["Recommended Action"]

    card_html = dashboard.signal_card_html(
        "staged flow",
        "Review peer import draft",
        "Peer import draft ready; run make status before trusting peer mapping import drafts.",
        ["staged flow"],
        "make imports-preview",
    )
    assert "Review peer import draft" in card_html
    assert "Peer import draft ready" in card_html
    assert "make status-check TOP_N=5" in card_html
    assert "import draft flow" in card_html
    assert "staged peer" not in card_html.lower()

    workflow_rows = dashboard.clean_display_frame(
        pd.DataFrame(
            {
                "workflow_group": ["dcf_ready_peer_mapping"],
                "workflow_scope": ["active_universe"],
                "peer_blocker_type": ["missing_peer_mapping"],
                "peer_valuation_status": ["peer_valuation_blocked"],
                "mapping_status": ["insufficient_mapping"],
                "valuation_status": ["not_ready"],
                "peer_relative_status": ["peer_data_unavailable"],
            }
        )
    )
    rendered = " ".join(workflow_rows.astype(str).stack().tolist()).lower()
    rendered_columns = " ".join(workflow_rows.columns).lower()
    assert "dcf-ready peer mapping" in rendered
    assert "active universe" in rendered
    assert "missing peer mapping" in rendered
    assert "peer valuation blocked" in rendered
    assert "insufficient mapping" in rendered
    assert "not ready" in rendered
    assert "peer data unavailable" in rendered
    assert "dcf_ready_peer_mapping" not in rendered
    assert "active_universe" not in rendered
    assert "missing_peer_mapping" not in rendered
    assert "peer_data_unavailable" not in rendered
    assert "not_ready" not in rendered
    assert "Workflow Group" in workflow_rows.columns
    assert "Workflow Scope" in workflow_rows.columns
    assert "Peer Blocker Type" in workflow_rows.columns
    assert "workflow_group" not in rendered_columns
    assert "workflow_scope" not in rendered_columns


def test_plain_home_demo_example_frame_maps_report_modes_without_recommendations():
    frame = dashboard._plain_home_demo_example_frame()
    rendered = " ".join(str(value) for value in frame.to_numpy().ravel()).lower()

    assert list(frame["Example"]) == ["NVDA", "A", "META", "QQQ / SMH", "APLD"]
    assert list(frame["Comparison Role"]) == [
        "Richer company example",
        "Standalone DCF but peer-locked",
        "Price/setup gated company",
        "ETF/index monitor example",
        "Blocked-data example",
    ]
    assert "standalone dcf review" in rendered
    assert "price/setup review only" in rendered
    assert "monitor-only context" in rendered
    assert "data-unlock only" in rendered
    assert "trusted local dcf inputs, input path, assumptions, and sensitivity" in rendered
    assert "peer-relative valuation stays locked" in rendered
    assert "operating-company dcf is excluded, not failed" in rendered
    assert "no valuation conclusion appears" in rendered
    assert "make stock-report-md ticker=nvda" in rendered
    assert "make stock-report-md ticker=a" in rendered
    assert "make stock-report-md ticker=apld" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_plain_home_readiness_cards_include_copyable_next_commands():
    cards = dashboard._plain_home_readiness_cards(
        {
            "master_universe": 3538,
            "active_universe": 12,
            "price_ready": 240,
            "dcf_ready": 23,
            "peer_ready": 3,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
            "blocked": 3298,
            "partial": 240,
        },
        pd.DataFrame(
            {
                "decision_bucket": [
                    "Research Now",
                    "Research Now",
                    "Monitor",
                    "Blocked by Data",
                ]
            }
        ),
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "UNIVERSE",
        "READY TO REVIEW",
        "DEEP ANALYSIS",
        "OPTIONAL CONTEXT",
        "DECISIONS",
    ]
    assert "3,538 tickers tracked" in rendered
    assert "12 are in the active research list" in rendered
    assert "240 have price data" in rendered
    assert "23 dcf-ready / 3 peer-ready" in rendered
    assert "0 earnings / 0 estimates" in rendered
    assert "2 research now / 1 monitor" in rendered
    assert "3,298 names are blocked by missing data" in rendered
    assert "make status-check top_n=5" in rendered
    assert "make price-refresh-loop dry_run=1" in rendered
    assert "make sec-stage-queue top_n=25" in rendered
    assert "make optional-context-worklist top_n=10" in rendered
    assert "make research-health top_n=10" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_price_refresh_operator_plan_cards_calculate_broad_capped_path_without_manual_repeats():
    cards = dashboard.price_refresh_operator_plan_cards(
        {
            "master_universe": 3538,
            "price_ready": 240,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    source = Path("src/dashboard.py").read_text(encoding="utf-8")

    assert [card["kicker"] for card in cards] == [
        "PRICE COVERAGE PLAN",
        "BEFORE UPDATE",
        "CAPPED RUN",
        "AFTER UPDATE",
    ]
    assert "3,298 ticker(s)" in rendered
    assert "dry run with max_candidates" in rendered
    assert "calculates capped batches" in rendered
    assert "before any local csv files change" in rendered
    assert "make price-refresh-loop dry_run=1 max_candidates=3300 top_n=100 provider=yahoo" in rendered
    assert "make readiness-snapshot" in rendered
    assert "make price-refresh-loop max_candidates=3300 top_n=100 provider=yahoo sleep_seconds=30" in rendered
    assert "make diff-hygiene" in rendered
    assert "repeating" not in rendered
    assert "render_signal_cards(price_refresh_operator_plan_cards(summary))" in source
    assert "render_signal_cards(price_refresh_operator_plan_cards(readiness_summary))" in source
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_dashboard_badges_use_high_contrast_html():
    html = dashboard.status_badge("Watch")
    assert "background" in html
    assert "color" in html
    assert "Watch" in html
    raw_status_html = dashboard.status_badge("insufficient_peer_data")
    assert "Insufficient peer data" in raw_status_html
    assert "insufficient_peer_data" not in raw_status_html


def test_dashboard_page_query_supports_visitor_friendly_deep_links():
    assert dashboard.dashboard_page_slug("Single-Stock Report") == "single-stock-report"
    assert dashboard.dashboard_page_slug("Value / Re-rating") == "value-re-rating"
    assert dashboard.dashboard_page_from_query("single-stock-report") == "Single-Stock Report"
    assert dashboard.dashboard_page_from_query("Single-Stock%20Report") == "Single-Stock Report"
    assert dashboard.dashboard_page_from_query(["data-health"]) == "Data Health"
    assert dashboard.dashboard_page_from_query("Value / Re-rating") == "Value / Re-rating"
    assert dashboard.dashboard_page_from_query("not-a-page") == "Home"
    assert dashboard.dashboard_page_from_query(None) == "Home"


def test_dashboard_page_reader_cards_answer_analyze_locked_and_copy_next():
    pages = ["Home", "Single-Stock Report", "Value / Re-rating", "Data Health"]
    cards = [card for page in pages for card in dashboard.dashboard_page_reader_cards(page)]
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 12
    assert all(card["kicker"] in {"PAGE GUIDE", "LOCKED / EXCLUDED", "COPY NEXT"} for card in cards)
    assert "home: what can i analyze now?" in rendered
    assert "single-stock report: what can i analyze now?" in rendered
    assert "value / re-rating: what can i analyze now?" in rendered
    assert "data health: what can i analyze now?" in rendered
    assert "unsupported dcf, peer valuation, earnings, and estimate sections stay withheld" in rendered
    assert "dcf-ready company rows can support assumption, scenario, sensitivity, and source-freshness review" in rendered
    assert "missing inputs are an unlock queue, not weak conclusions" in rendered
    assert "dashboard does not run refreshes, imports, or external account actions" in rendered
    assert "make stock-report-md ticker=nvda" in rendered
    assert "make dcf-readiness" in rendered
    assert "make data-wizard top_n=10" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_major_dashboard_pages_render_plain_english_reader_guides():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")

    assert 'render_signal_cards(dashboard_page_reader_cards("Home"))' in source
    assert 'render_signal_cards(dashboard_page_reader_cards("Single-Stock Report"))' in source
    assert 'render_signal_cards(dashboard_page_reader_cards("Data Health"))' in source
    assert 'if title == "Value / Re-rating":' in source
    assert "render_signal_cards(dashboard_page_reader_cards(title))" in source


def test_sidebar_navigation_note_matches_selected_page():
    home_title, home_body = dashboard.sidebar_navigation_note("Home")
    report_title, report_body = dashboard.sidebar_navigation_note("Single-Stock Report")

    assert home_title == "Start here."
    assert "what is ready" in home_body
    assert "safest next review path" in home_body
    assert report_title == "Viewing Single-Stock Report."
    assert "selected workflow" in report_body
    assert "return to Home" in report_body
    assert "Home explains what is ready" not in report_body


def test_dashboard_theme_pins_review_surfaces_to_readable_colors(monkeypatch):
    captured: dict[str, object] = {}

    def fake_markdown(body: str, unsafe_allow_html: bool = False) -> None:
        captured["body"] = body
        captured["unsafe_allow_html"] = unsafe_allow_html

    monkeypatch.setattr(dashboard.st, "markdown", fake_markdown)

    dashboard.apply_dashboard_theme()

    css = str(captured["body"])
    assert captured["unsafe_allow_html"] is True
    assert '[data-testid="stAppViewContainer"]' in css
    assert '[data-testid="stDataFrame"]' in css
    assert '[data-testid="stExpander"]' in css
    assert '[data-baseweb="popover"]' in css
    assert "color: #111827 !important" in css
    assert "background: #fffefa !important" in css


def test_dashboard_card_helpers_render_modern_markup():
    metric = dashboard.metric_card_html("Universe", 12, "local tickers")
    action = dashboard.action_card_html("Price fallback", "Normalize downloaded CSVs", "make price-normalize", "warning")
    notice = dashboard.notice_card_html("Missing output", "Run the pipeline to regenerate local CSV outputs.", "make pipeline")

    assert "metric-card" in metric
    assert "Universe" in metric
    assert "action-card warning" in action
    assert "make price-normalize" in action
    assert "notice-card" in notice
    assert "make pipeline" in notice


def test_single_stock_default_prefers_demo_ticker_when_available():
    assert dashboard.preferred_single_stock_default([]) == 0
    assert dashboard.preferred_single_stock_default(["A", "MSFT"]) == 1
    assert dashboard.preferred_single_stock_default(["A", "NVDA", "QQQ"]) == 2
    assert dashboard.preferred_single_stock_default(["nvda", "QQQ"]) == 1


def test_single_stock_source_json_label_uses_visitor_friendly_language():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")

    assert "Source and freshness details" in source
    assert "stock_report_source_detail_summary_frame(report_payload)" in source
    assert "Source and freshness details (JSON)" not in source
    assert "Advanced source audit (JSON)" not in source
    assert "Developer detail: raw report JSON" not in source
    assert "st.json(report_payload" not in source
    assert "One-ticker research workflow" in source
    assert "Structured research workflow for one ticker" not in source
    assert "A readable view of local research inputs" in source
    assert "A structured view of local research inputs" not in source
    assert "Saved local data is the default" in source
    assert "Optional online research mode stays off by default" in source
    assert "Local CSV-backed data is the default" not in source
    assert "Optional yfinance mode stays off by default" not in source
    assert "Optional online provider mode" in source
    assert "saved local-data path" in source
    assert "Show report source details" in source
    assert "Adds source and freshness troubleshooting under Sources & Gaps" in source
    assert "Adds raw JSON under Sources & Gaps" not in source
    assert "Most users can leave this off" in source
    assert "Show more explanation" in source
    assert "#### Where to go next" in source
    assert 'st.expander("Start guide"' not in source
    assert 'st.expander("Help for using the app"' in source
    assert 'st.expander("Help, commands, and paths"' not in source
    assert 'st.expander("Advanced command help"' not in source
    assert 'st.expander("How to read status labels"' not in source
    assert 'st.expander("Missing-data guide"' not in source
    assert 'st.expander("Local file paths"' not in source
    assert "#### Status labels" in source
    assert "#### If analysis is blocked" in source
    assert "#### Where local files live" in source
    assert "App folder:" in source
    assert "Trusted input CSVs:" in source
    assert "Generated reports:" in source
    assert "Project root:" not in source
    assert "Data dir:" not in source
    assert "Outputs dir:" not in source
    assert "#### Local file paths" not in source
    assert 'st.expander("Technical paths"' not in source
    assert 'st.expander("Copyable commands"' in source
    assert 'st.expander("Advanced commands"' not in source
    assert 'st.expander("Full valuation output table"' in source
    assert 'st.expander("Advanced valuation output table"' not in source
    assert "### Copyable Commands" in source
    assert "### Copyable Terminal Workflow" not in source
    assert "### CLI Workflow" not in source
    assert "CLI-only" not in source
    assert "CLI only" not in source
    assert "terminal-only" not in source
    assert "make stock-report-md TICKER=NVDA\\nmake dashboard-smoke" in source
    assert "make stock-report TICKER=NVDA\\nmake dashboard-smoke" not in source
    assert "diagnostics" not in source.lower()


def test_data_health_bundle_detail_copy_uses_operator_language():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")

    assert "Ticker-level bundle steps" in source
    assert "Ticker-level bundle steps are not available yet" in source
    assert "generate ticker-level bundle steps" in source
    assert "Command bundle detail rows" not in source
    assert "generate ticker-level bundle detail rows" not in source


def test_home_capability_cards_explain_quality_limits_and_provenance():
    cards = dashboard._plain_home_capability_cards()
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 5
    assert "ready-data research" in rendered
    assert "blocked fundamentals, peers, earnings, or estimates" in rendered
    assert "copy commands, then run them yourself" in rendered
    assert "do not run refreshes, imports, or external account actions" in rendered
    assert "implemented in the project code" in rendered
    assert "project rules" in rendered
    assert "product boundary" in rendered
    assert "project code powers the analysis" in rendered
    assert "standard packages help build and run the app" in rendered
    assert "assistant plugins or skills can help development review" not in rendered
    assert "research output comes from project rules and local data" in rendered
    assert "development helpers stay separate" not in rendered
    assert "public equity investing" not in rendered
    assert "investment banking" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_home_evaluation_workflow_cards_show_product_sequence_without_overclaiming():
    cards = dashboard._plain_home_evaluation_workflow_cards()
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["STEP 1", "STEP 2", "STEP 3", "STEP 4"]
    assert "check readiness first" in rendered
    assert "local prices, fundamentals, dcf fields, peers, earnings, and estimates" in rendered
    assert "run only supported analysis" in rendered
    assert "price-ready rows can support setup and risk context" in rendered
    assert "dcf-ready rows can support assumptions and sensitivity" in rendered
    assert "peer-ready rows can support source-backed relative context" in rendered
    assert "keep locked sections visible" in rendered
    assert "missing fundamentals, peer inputs, earnings, or estimates stay locked" in rendered
    assert "etf/index/fund dcf is excluded, not failed" in rendered
    assert "read the report boundary" in rendered
    assert "what data came from source rows" in rendered
    assert "what the product calculated" in rendered
    assert "what stayed withheld" in rendered
    assert "copy-only local step" in rendered
    assert "make readiness" in rendered
    assert "make stock-report-md ticker=nvda" in rendered
    assert "make data-wizard top_n=10" in rendered
    assert "make stock-report-md ticker=a" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_home_next_step_cards_are_copyable_and_readiness_gated():
    price_gap_cards = dashboard._plain_home_next_step_cards(
        {
            "master_universe": 100,
            "price_ready": 20,
            "dcf_ready": 2,
            "peer_ready": 1,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    fundamentals_cards = dashboard._plain_home_next_step_cards(
        {
            "master_universe": 100,
            "price_ready": 100,
            "dcf_ready": 1,
            "peer_ready": 1,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    peer_cards = dashboard._plain_home_next_step_cards(
        {
            "master_universe": 100,
            "price_ready": 100,
            "dcf_ready": 10,
            "peer_ready": 1,
            "earnings_ready": 1,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(
        str(value)
        for card in price_gap_cards + fundamentals_cards + peer_cards
        for value in card.values()
    ).lower()

    assert price_gap_cards[0]["command"] == "make price-refresh-loop DRY_RUN=1"
    assert fundamentals_cards[0]["command"] == "make sec-stage-queue TOP_N=25"
    assert peer_cards[0]["command"] == "make peer-mapping-queue TOP_N=25"
    assert price_gap_cards[1]["command"] == "make stock-report-md TICKER=NVDA"
    assert price_gap_cards[2]["command"] == "make data-wizard TOP_N=10"
    assert price_gap_cards[3]["command"] == "make optional-context-worklist TOP_N=25"
    assert "scalable dry run" in rendered
    assert "instead of repeating 25-ticker refreshes manually" in rendered
    assert "blocked rows are useful, but they are a data-unlock queue, not a conclusion list" in rendered
    assert "no data, no conclusion" in rendered
    assert "earnings and analyst estimates are not broken" in rendered
    assert "optional context is available" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_home_page_renders_evaluation_workflow_before_next_steps():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")

    workflow_index = source.index('render_section_header("Evaluation Workflow"')
    next_step_index = source.index('render_section_header("What To Do Next"')

    assert workflow_index < next_step_index
    assert "How the product moves from trusted data to supported analysis without overclaiming." in source
    assert "render_signal_cards(_plain_home_evaluation_workflow_cards())" in source


def test_home_provenance_cards_separate_repo_logic_libraries_and_plugins():
    cards = dashboard._plain_home_provenance_cards()
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 4
    assert "rules are implemented in project code" in rendered
    assert "readiness, momentum, dcf, peer checks, decision buckets, and report wording" in rendered
    assert "standard python packages support the app" in rendered
    assert "stock-analysis rules stay in this repository" in rendered
    assert "support layer" in rendered
    assert "pandas" in rendered
    assert "streamlit" in rendered
    assert "open-source packages support the app" not in rendered
    assert "yfinance is optional and research-grade" in rendered
    assert "csv-first local path is default" in rendered
    assert "not analysis rules" in rendered
    assert "support tools and libraries are separate from the stock-analysis rules" in rendered
    assert "development tools" not in rendered
    assert "development tooling is separate from the shipped research logic" not in rendered
    assert "development tooling is not shipped analysis" not in rendered
    assert "public equity investing" not in rendered
    assert "investment banking" not in rendered
    assert "analysis and decisions come from project code and local data" in rendered
    assert "product engines" not in rendered
    assert "no open source was used" not in rendered
    assert "100% original" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_home_function_quality_frame_explains_supported_scope_and_logic_source():
    frame = dashboard._plain_home_function_quality_frame(
        {
            "master_universe": 3538,
            "price_ready": 240,
            "dcf_ready": 23,
            "peer_ready": 3,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert list(frame.columns) == [
        "Function Area",
        "Quality Verdict",
        "Best Use Today",
        "Current Status",
        "Supported Today",
        "Needs Trusted Data",
        "Logic Source",
    ]
    assert "readiness gates" in rendered
    assert "strong today" in rendered
    assert "trust this first" in rendered
    assert "strongest layer" in rendered
    assert "price / momentum" in rendered
    assert "good when price history is ready" in rendered
    assert "240 / 3,538 price-ready" in rendered
    assert "fundamentals / dcf" in rendered
    assert "good for dcf-ready companies only" in rendered
    assert "review the dcf input path, assumptions, scenarios, and sensitivity" in rendered
    assert "23 / 3,538 dcf-ready" in rendered
    assert "dcf-ready company analysis with visible input path, assumptions, and sensitivity" in rendered
    assert "peer comparison" in rendered
    assert "workflow-ready, coverage-limited" in rendered
    assert "3 / 3,538 peer-ready" in rendered
    assert "no guessed peer mappings" in rendered
    assert "earnings / estimates" in rendered
    assert "intentionally locked without trusted rows" in rendered
    assert "do not interpret empty coverage as analysis" in rendered
    assert "0 / 3,538 earnings-ready" in rendered
    assert "0 / 3,538 analyst-estimate-ready" in rendered
    assert "intentionally unavailable" in rendered
    assert "single-stock report" in rendered
    assert "strongest visitor-facing workflow" in rendered
    assert "supported, blocked, excluded, and monitor-only analysis" in rendered
    assert "libraries/adapters" in rendered
    assert "support layer, not analysis logic" in rendered
    assert "analysis rules remain under src/" in rendered
    assert "no open source was used" not in rendered
    assert "100% original" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_function_quality_cards_summarize_supported_analysis_and_provenance():
    cards = dashboard.stock_report_function_quality_cards(
        {
            "readiness": {
                "price_ready": True,
                "momentum_ready": True,
                "liquidity_ready": True,
                "correlation_ready": True,
                "fundamentals_ready": True,
            },
            "valuation_readiness": {
                "dcf_ready": True,
                "peer_ready": False,
                "earnings_available": False,
                "analyst_estimates_available": False,
            },
            "valuation_snapshot": {"status": "calculated"},
            "asset_type": "company",
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "DATA GATE",
        "PRICE / RISK",
        "VALUATION",
        "OPTIONAL CONTEXT",
        "LOGIC SOURCE",
    ]
    assert "ready, blocked, or excluded first" in rendered
    assert "missing inputs stay visible instead of being guessed" in rendered
    assert "ready for local trend/setup review" in rendered
    assert "ready for local liquidity/correlation context" in rendered
    assert "ready for standalone dcf assumptions and sensitivity review" in rendered
    assert "peer context: blocked until source-backed peer mappings" in rendered
    assert "empty optional files are not treated as conclusions" in rendered
    assert "project rules" in rendered
    assert "shipped analysis comes from project code and local data" in rendered
    assert "plugins can help development review" not in rendered
    assert "no open source was used" not in rendered
    assert "100% original" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_notice_card_escapes_content_and_uses_tones():
    html = dashboard.notice_card_html("<Missing>", "Use <safe> local files.", "make pipeline", tone="warning")

    assert "&lt;Missing&gt;" in html
    assert "&lt;safe&gt;" in html
    assert "notice-card warning" in html


def test_load_output_missing_message_uses_verify(tmp_path):
    frame, message = dashboard.load_output(tmp_path / "final_watchlist.csv")

    assert frame is None
    assert "make verify" in message
    assert "report_generator" not in message


def test_context_note_html_is_readable_and_escaped():
    html = dashboard.context_note_html("<Filters>", "Use <trusted> local CSV inputs.", tone="warning")

    assert "context-note warning" in html
    assert "&lt;Filters&gt;" in html
    assert "&lt;trusted&gt;" in html


def test_section_header_html_uses_shell_and_escapes_content():
    html = dashboard.section_header_html("<Monthly Picks>", "Use <local> research coverage.")

    assert "section-shell" in html
    assert "section-kicker" in html
    assert "Research View" in html
    assert "&lt;Monthly Picks&gt;" in html
    assert "&lt;local&gt;" in html


def test_chart_panel_title_normalizes_spacing_and_trailing_punctuation():
    assert dashboard.chart_panel_title(" Score context. ") == "Score context"
    assert dashboard.chart_panel_title("Price history chart:") == "Price history chart"
    assert dashboard.chart_panel_title("") == "Chart"


def test_state_styles_include_text_color_for_dark_mode():
    styled = dashboard.style_frame(pd.DataFrame({"FinalState": ["No Setup"]}))._compute()
    css_values = [item for styles in styled.ctx.values() for item in styles]

    assert ("color", "#991b1b") in css_values
    assert ("font-weight", "700") in css_values


def test_normalize_public_labels_preserves_valuation_avoid_category():
    frame = pd.DataFrame(
        {
            "SetupStatus": ["Avoid", "Extended / No Chase"],
            "FinalState": ["Avoid", "Extended / No Chase"],
            "PrimaryPurpose": ["Broken / Avoid", "Core Compounder"],
            "FinalValueCategory": ["Avoid", "Insufficient Data"],
            "Reason": ["Compounder setup: Avoid", "Valuation category is Avoid"],
        }
    )

    normalized = dashboard.normalize_public_labels(frame)

    assert normalized["SetupStatus"].tolist() == ["No Setup", "Extended"]
    assert normalized["FinalState"].tolist() == ["No Setup", "Extended"]
    assert normalized["PrimaryPurpose"].tolist() == ["Broken / No Setup", "Core Compounder"]
    assert normalized["FinalValueCategory"].tolist() == ["Avoid", "Insufficient Data"]
    assert normalized["Reason"].tolist() == ["Compounder setup: No Setup", "Valuation category is Avoid"]


def test_missing_data_notice_translates_common_gaps():
    html = dashboard.missing_data_notice("fundamentals unavailable, peers")
    assert "Needs SEC enrichment" in html
    assert "Needs peers.csv" in html


def test_missing_data_summary_limits_noisy_fields():
    text = dashboard.summarize_missing_fields("Return1M, Return3M, Return6M, EPSGrowth, FCFMargin, ForwardPE", max_items=3)
    mixed = dashboard.summarize_missing_fields("revenue; free_cash_flow|shares_outstanding", max_items=5)

    assert "Not enough price history" in text
    assert "+1 more" in text
    assert mixed == "revenue, free_cash_flow, shares_outstanding"


def test_monthly_pick_availability_message_handles_less_than_top_n():
    message = dashboard.monthly_pick_availability_message(4, 5)

    assert "4 of 5" in message
    assert "not forced" in message


def test_track_record_status_message_explains_insufficient_history():
    message = dashboard.track_record_status_message(None, None)

    assert "Insufficient local history" in message
    assert "forward returns" in message


def test_compact_reason_avoids_wall_of_text():
    reason = (
        "Composite score uses transparent local components. "
        "This row is a research candidate, not execution guidance. "
        "Missing or incomplete fields reduced data confidence."
    )

    compact = dashboard.compact_reason(reason, max_sentences=2)

    assert compact.count(".") == 2
    assert "Missing or incomplete" not in compact


def test_compact_table_columns_prefers_summaries_over_raw_reason():
    frame = pd.DataFrame(
        {
            "Ticker": ["NVDA"],
            "FinalState": ["Review Thesis"],
            "Reason": ["Long reason"],
            "ReasonSummary": ["Short reason"],
            "MissingDataFields": ["Return1M"],
            "DataGaps": ["Not enough price history"],
        }
    )

    columns = dashboard.compact_table_columns(frame)

    assert "ReasonSummary" in columns
    assert "DataGaps" in columns
    assert "Reason" not in columns


def test_compact_table_columns_prioritize_rank_purpose_and_hide_noise():
    frame = pd.DataFrame(
        {
            "GeneratedAt": ["2026-05-21T00:00:00Z"],
            "SourceFiles": ["outputs/final_watchlist.csv"],
            "Month": ["2026-05"],
            "Rank": [1],
            "Ticker": ["NVDA"],
            "PrimaryPurpose": ["Momentum Leader"],
            "CompositeScore": [52.5],
            "ReasonSummary": ["Transparent local context."],
            "DataGaps": ["Needs SEC enrichment"],
        }
    )

    columns = dashboard.compact_table_columns(frame)

    assert columns[:4] == ["Month", "Rank", "Ticker", "PrimaryPurpose"]
    assert "GeneratedAt" not in columns
    assert "SourceFiles" not in columns


def test_reorder_columns_surfaces_summary_and_research_context_first():
    frame = pd.DataFrame(
        {
            "ReasonSummary": ["Short reason"],
            "Ticker": ["NVDA"],
            "CompositeScore": [55.0],
            "PrimaryPurpose": ["Momentum Leader"],
            "DataGaps": ["Not enough price history"],
            "NextBestAction": ["Run make focus-price TICKER=NVDA"],
            "FocusCommand": ["make focus-price TICKER=NVDA"],
            "ExampleCommand": ["make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual"],
            "GeneratedAt": ["2026-05-21T00:00:00Z"],
        }
    )

    reordered = dashboard.reorder_columns(frame)

    assert list(reordered.columns[:8]) == [
        "Ticker",
        "PrimaryPurpose",
        "CompositeScore",
        "NextBestAction",
        "FocusCommand",
        "ExampleCommand",
        "ReasonSummary",
        "DataGaps",
    ]


def test_table_focus_cards_summarize_state_context_and_gaps_cleanly():
    frame = pd.DataFrame(
        {
            "Ticker": ["NVDA", "AMD"],
            "PrimaryPurpose": ["Momentum Leader", "Momentum Leader"],
            "FinalState": ["Watch", "Watch"],
            "MissingDataFields": ["Return3M", ""],
            "WatchlistScore": [72.0, 61.0],
        }
    )

    cards = dashboard.table_focus_cards(frame)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 4
    assert "2 rows" in rendered
    assert "watch" in rendered
    assert "momentum leader" in rendered
    assert "1 row with gaps" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_output_tab_summary_cards_explain_missing_theme_context_without_zero_row_copy():
    frame = pd.DataFrame(
        {
            "Ticker": ["A", "B"],
            "FinalValueCategory": ["Insufficient Data", "Insufficient Data"],
            "Reason": ["Missing peer inputs.", "Missing fundamentals."],
            "MissingDataFields": ["peers", "fundamentals"],
        }
    )

    cards = dashboard.output_tab_summary_cards("Value / Re-rating", frame)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "no populated theme or sector context is available" in rendered
    assert "saved local output" in rendered
    assert "csv output" not in rendered
    assert "across 0 rows" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_detail_columns_group_reasons_support_and_operational_fields():
    frame = pd.DataFrame(
        {
            "Ticker": ["NVDA"],
            "Theme": ["AI"],
            "FinalState": ["Watch"],
            "Reason": ["Transparent local context."],
            "RankReason": ["Strong relative score."],
            "MissingDataFields": ["Return3M"],
            "ConflictReasons": ["Price history is short."],
            "RiskPenalty": [12.0],
            "SourceFiles": ["outputs/final_watchlist.csv"],
            "GeneratedAt": ["2026-05-21T00:00:00Z"],
            "MemberTickers": ["NVDA, AVGO"],
        }
    )

    reason_columns = dashboard.detail_columns(frame, "reasons")
    support_columns = dashboard.detail_columns(frame, "support")
    operations_columns = dashboard.detail_columns(frame, "operations")

    assert "Reason" in reason_columns
    assert "RankReason" in reason_columns
    assert "MissingDataFields" in support_columns
    assert "ConflictReasons" in support_columns
    assert "RiskPenalty" in support_columns
    assert "SourceFiles" in operations_columns
    assert "GeneratedAt" in operations_columns
    assert "MemberTickers" in operations_columns


def test_detail_sections_build_mid_level_panels_without_buy_sell_language():
    frame = pd.DataFrame(
        {
            "Ticker": ["NVDA"],
            "Theme": ["AI"],
            "FinalState": ["Watch"],
            "Reason": ["Transparent local context."],
            "MissingDataFields": ["Return3M"],
            "SourceFiles": ["outputs/final_watchlist.csv"],
        }
    )

    sections = dashboard.detail_sections(frame, show_reason_details=True)
    titles = [title for title, _ in sections]
    rendered = " ".join(str(value) for title, detail in sections for value in [title, detail.to_dict()]).lower()

    assert titles == ["Reasons", "Risk and data gaps", "Source and operational context"]
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_pick_filter_column_prefers_first_populated_candidate():
    frame = pd.DataFrame(
        {
            "Sector": ["", None],
            "SectorETF": ["SMH", "QQQ"],
            "ETF": ["", ""],
        }
    )

    assert dashboard.pick_filter_column(frame, ["Sector", "SectorETF", "ETF"]) == "SectorETF"


def test_filter_summary_text_stays_readable_and_compact():
    text = dashboard.filter_summary_text(
        "monthly-research-picks",
        "nvda",
        "FinalState",
        ["Watch", "Review Thesis", "Setup Forming", "No Setup"],
        "Theme",
        ["AI"],
        "SectorETF",
        ["SMH"],
        4,
        12,
    )

    assert "4 of 12 rows visible" in text
    assert "search `nvda`" in text
    assert "Final State: Watch, Review Thesis, Setup Forming +1 more" in text
    assert "Theme: AI" in text
    assert "Sector ETF: SMH" in text
    assert "nan" not in text.lower()
    assert "none" not in text.lower()


def test_filter_summary_text_handles_no_active_filters():
    text = dashboard.filter_summary_text(
        "market-direction",
        "",
        None,
        [],
        None,
        [],
        None,
        [],
        9,
        9,
    )

    assert "Market Direction" in text
    assert "9 of 9 rows visible" in text
    assert "Use search or filters" in text


def test_filter_summary_text_uses_user_facing_value_page_name():
    text = dashboard.filter_summary_text(
        "value-re-rating",
        "",
        None,
        [],
        None,
        [],
        None,
        [],
        23,
        23,
    )

    assert text.startswith("Value / Re-rating: 23 of 23 rows visible.")
    assert "Value Re Rating" not in text


def test_filter_summary_text_can_be_wrapped_in_context_note():
    summary = dashboard.filter_summary_text(
        "final-watchlist",
        "nvda",
        "FinalState",
        ["Watch"],
        "Theme",
        ["AI"],
        "SectorETF",
        ["SMH"],
        1,
        12,
    )
    html = dashboard.context_note_html("Active filters.", summary)

    assert "context-note" in html
    assert "Active filters." in html
    assert "1 of 12 rows visible" in html


def test_ticker_coverage_display_frame_hides_noisy_paths():
    coverage = pd.DataFrame(
        [
            {
                "dataset_name": "prices",
                "file_path": "/tmp/prices.csv",
                "validation_status": "valid",
                "ticker_present": True,
                "row_count_for_ticker": 25,
                "latest_data_timestamp": "2026-03-14T00:00:00",
                "notes": ["Ticker rows found in local dataset."],
            }
        ]
    )

    display = dashboard.ticker_coverage_display_frame(coverage)

    assert list(display.columns) == ["Dataset", "Status", "TickerData", "Rows", "Latest", "Notes"]
    assert display.iloc[0]["TickerData"] == "Available"
    assert display.iloc[0]["Latest"] == "2026-03-14"


def _fake_pipeline_outputs(_root, *, output_dir):
    output_path = Path(output_dir)
    for filename in dashboard.PIPELINE_FILES:
        pd.DataFrame([{"ticker": "NVDA", "status": "fixture"}]).to_csv(output_path / filename, index=False)


def _fake_monthly_research_picks(_root, *, output_dir, top_n):
    pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "monthly_pick_status": "fixture",
                "research_only_note": "Copy-only research fixture.",
            }
        ]
    ).to_csv(Path(output_dir) / "monthly_research_picks.csv", index=False)


def _fake_monthly_track_record(_root, *, output_dir, top_n, write_output):
    output_path = Path(output_dir)
    pd.DataFrame([{"ticker": "NVDA", "status": "fixture"}]).to_csv(
        output_path / "monthly_picks_track_record.csv",
        index=False,
    )
    pd.DataFrame([{"month": "2026-01", "equity": 1.0}]).to_csv(
        output_path / "monthly_picks_equity_curve.csv",
        index=False,
    )


def _fake_data_source_outputs(_root, *, output_dir):
    payload = {
        "data_sources": [
            {
                "dataset": "fundamentals",
                "source_name": "fixture",
                "source_type": "local_csv",
                "availability_status": "partial",
                "required_for": "valuation",
                "fallback_action": "Run make imports-validate, then make imports-preview.",
                "target_file": "data/imports/fundamentals.csv",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "credential_required": "",
                "credential_present": False,
                "manual_fallback_command": "make templates",
                "command_safety_note": "Copy-only command.",
                "local_file": "data/imports/fundamentals.csv",
                "row_count": 1,
                "validation_warnings": "",
            }
        ],
        "data_gaps": [
            {
                "dataset": "fundamentals",
                "ticker": "",
                "status": "partial",
                "reason": "fixture",
                "required_for": "valuation",
                "recommended_action": "Run make imports-validate, then make imports-preview.",
                "target_file": "data/imports/fundamentals.csv",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "credential_required": "",
                "credential_present": False,
                "manual_fallback_command": "make templates",
                "command_safety_note": "Copy-only command.",
                "local_file": "data/imports/fundamentals.csv",
                "source_name": "fixture",
            }
        ],
    }
    output_path = Path(output_dir)
    pd.DataFrame(payload["data_sources"]).to_csv(output_path / "data_source_status.csv", index=False)
    pd.DataFrame(payload["data_gaps"]).to_csv(output_path / "data_gap_report.csv", index=False)
    return payload


def test_data_source_status_tables_handle_missing_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "write_data_source_outputs", _fake_data_source_outputs)
    tables = dashboard.load_data_source_status_tables(tmp_path, allow_refresh=True)

    source_frame, source_message = tables["data_source_status.csv"]
    gap_frame, gap_message = tables["data_gap_report.csv"]

    assert source_frame is not None
    assert gap_frame is not None
    assert source_message is None
    assert gap_message is None
    assert "focus_command" in source_frame.columns
    assert "focus_command" in gap_frame.columns
    assert dashboard.friendly_data_source_status("manual_only") == "Manual input needed"
    assert dashboard.friendly_data_source_status("optional_unofficial") == "Optional unofficial"


def test_pipeline_outputs_loader_regenerates_missing_core_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "run_report_generator", _fake_pipeline_outputs)
    old_base = dashboard.BASE_DIR
    old_outputs = dashboard.OUTPUTS_DIR
    try:
        dashboard.BASE_DIR = tmp_path
        dashboard.OUTPUTS_DIR = tmp_path
        tables = dashboard.load_pipeline_outputs(tmp_path, allow_refresh=True)
    finally:
        dashboard.BASE_DIR = old_base
        dashboard.OUTPUTS_DIR = old_outputs

    for filename in dashboard.PIPELINE_FILES:
        frame, message = tables[filename]
        assert frame is not None
        assert message is None

    assert (tmp_path / "purpose_classification.csv").exists()
    assert (tmp_path / "market_direction.csv").exists()
    assert (tmp_path / "final_watchlist.csv").exists()


def test_monthly_outputs_loader_regenerates_missing_monthly_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "build_monthly_research_picks", _fake_monthly_research_picks)
    monkeypatch.setattr(dashboard, "calculate_monthly_track_record", _fake_monthly_track_record)
    old_base = dashboard.BASE_DIR
    old_outputs = dashboard.OUTPUTS_DIR
    try:
        dashboard.BASE_DIR = tmp_path
        dashboard.OUTPUTS_DIR = tmp_path
        tables = dashboard.load_monthly_outputs(tmp_path, allow_refresh=True)
    finally:
        dashboard.BASE_DIR = old_base
        dashboard.OUTPUTS_DIR = old_outputs

    for filename in dashboard.MONTHLY_FILES:
        frame, _message = tables[filename]
        assert frame is not None

    assert (tmp_path / "monthly_research_picks.csv").exists()
    assert (tmp_path / "monthly_picks_track_record.csv").exists()
    assert (tmp_path / "monthly_picks_equity_curve.csv").exists()


def test_dashboard_loaders_are_read_only_by_default(tmp_path, monkeypatch):
    def fail_refresh(*_args, **_kwargs):
        raise AssertionError("dashboard loader should not refresh artifacts by default")

    monkeypatch.setattr(dashboard, "run_report_generator", fail_refresh)
    monkeypatch.setattr(dashboard, "build_monthly_research_picks", fail_refresh)
    monkeypatch.setattr(dashboard, "calculate_monthly_track_record", fail_refresh)
    monkeypatch.setattr(dashboard, "write_data_source_outputs", fail_refresh)
    monkeypatch.setattr(dashboard, "write_onboarding_outputs", fail_refresh)
    monkeypatch.setattr(dashboard, "run_research_health", fail_refresh)
    monkeypatch.setattr(dashboard, "write_action_queue_output", fail_refresh)

    pipeline_tables = dashboard.load_pipeline_outputs(tmp_path)
    monthly_tables = dashboard.load_monthly_outputs(tmp_path)
    source_tables = dashboard.load_data_source_status_tables(tmp_path)
    onboarding_tables = dashboard.load_data_onboarding_tables(tmp_path)
    health_tables = dashboard.load_research_health_tables(tmp_path)
    queue_frame, queue_message = dashboard.load_action_queue(tmp_path)

    assert all(frame is None for frame, _message in pipeline_tables.values())
    assert all(frame is None for frame, _message in monthly_tables.values())
    assert all(frame is None for frame, _message in source_tables.values())
    assert all(frame is None for frame, _message in onboarding_tables.values())
    assert all(frame is None for frame, _message in health_tables.values())
    assert queue_frame is None
    assert "make action-queue" in queue_message


def test_price_update_status_loader_does_not_rewrite_by_default(tmp_path):
    path = tmp_path / "price_update_status.csv"
    original = (
        "ticker,status,rows_fetched,rows_merged,error_category,error_message,fallback_used,recommended_action\n"
        "AMD,parse_error,0,0,parse_error,AMD parse failed,True,Run make focus-price TICKER=AMD\n"
    )
    path.write_text(original, encoding="utf-8")

    frame, message = dashboard.load_price_update_status(tmp_path)

    assert message is None
    assert frame is not None
    assert "focus_command" in frame.columns
    assert path.read_text(encoding="utf-8") == original


def test_data_source_status_table_columns_surface_command_fields():
    frame = pd.DataFrame(
        [
            {
                "dataset": "fundamentals",
                "availability_status": "partial",
                "required_for": "valuation",
                "fallback_action": "Start with make status.",
                "focus_command": "make status",
                "example_command": "make sec-stage TICKERS=NVDA",
                "credential_required": "SEC_USER_AGENT",
                "credential_present": False,
                "manual_fallback_command": "make templates",
                "command_safety_note": "SEC import draft workflow requires credentials.",
                "local_file": "data/fundamentals.csv",
                "row_count": 6,
                "validation_warnings": "as_of_date missing",
                "source_name": "fixture",
                "source_type": "local_csv",
                "expected_local_file": "data/fundamentals.csv",
                "notes": "fixture",
            }
        ]
    )

    columns = dashboard.data_source_status_table_columns(frame)

    assert columns[:10] == [
        "dataset",
        "availability_status",
        "required_for",
        "fallback_action",
        "focus_command",
        "example_command",
        "credential_required",
        "credential_present",
        "manual_fallback_command",
        "command_safety_note",
    ]


def test_data_source_status_tables_refresh_stale_gap_report_columns(tmp_path):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    (data_dir / "prices.csv").write_text("date,ticker,adj_close,volume\n2026-01-02,NVDA,100,1000\n", encoding="utf-8")
    (data_dir / "universe.csv").write_text(
        "ticker,theme,sectoretf,defaultpurpose,marketcapbucket,notes\n"
        "NVDA,AI,SMH,Momentum Leader,Large,fixture\n",
        encoding="utf-8",
    )
    (data_dir / "holdings.csv").write_text("ticker,primarypurpose\nNVDA,Momentum Leader\n", encoding="utf-8")
    pd.DataFrame(
        [
            {
                "dataset": "fundamentals",
                "ticker": "",
                "status": "partial",
                "reason": "stale",
                "required_for": "valuation",
                "recommended_action": "old",
                "local_file": "data/fundamentals.csv",
                "source_name": "fixture",
            }
        ]
    ).to_csv(outputs_dir / "data_gap_report.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "prices",
                "source_name": "fixture",
                "source_type": "local_csv",
                "availability_status": "available",
                "required_for": "momentum",
                "is_required": True,
                "is_optional": False,
                "is_manual_only": False,
                "is_unofficial": False,
                "requires_network": False,
                "requires_user_agent": False,
                "requires_api_key": False,
                "expected_local_file": "data/prices.csv",
                "fallback_action": "old",
                "notes": "old",
                "local_file": "data/prices.csv",
                "row_count": 1,
                "available_columns": "date,ticker,adj_close,volume",
                "validation_warnings": "",
            }
        ]
    ).to_csv(outputs_dir / "data_source_status.csv", index=False)

    old_base = dashboard.BASE_DIR
    try:
        dashboard.BASE_DIR = tmp_path
        tables = dashboard.load_data_source_status_tables(outputs_dir, allow_refresh=True)
    finally:
        dashboard.BASE_DIR = old_base

    gap_frame, _ = tables["data_gap_report.csv"]
    assert gap_frame is not None
    assert "target_file" in gap_frame.columns
    assert "focus_command" in gap_frame.columns
    assert "example_command" in gap_frame.columns
    assert gap_frame.loc[gap_frame["dataset"] == "fundamentals", "example_command"].iloc[0] == "make runbook-fundamentals-broader"


def test_data_source_status_tables_refresh_stale_source_status_columns(tmp_path):
    outputs_dir = tmp_path
    pd.DataFrame(
        [
            {
                "dataset": "fundamentals",
                "ticker": "",
                "status": "partial",
                "reason": "old",
                "required_for": "valuation",
                "recommended_action": "Start with make status",
                "focus_command": "make status",
                "example_command": "make runbook-fundamentals-broader",
                "local_file": "data/fundamentals.csv",
                "source_name": "fixture",
            }
        ]
    ).to_csv(outputs_dir / "data_gap_report.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "fundamentals",
                "source_name": "fixture",
                "source_type": "local_csv",
                "availability_status": "partial",
                "required_for": "valuation",
                "is_required": False,
                "is_optional": True,
                "is_manual_only": False,
                "is_unofficial": False,
                "requires_network": False,
                "requires_user_agent": False,
                "requires_api_key": False,
                "expected_local_file": "data/fundamentals.csv",
                "fallback_action": "old",
                "notes": "old",
                "local_file": "data/fundamentals.csv",
                "row_count": 1,
                "available_columns": "ticker,pe_ratio",
                "validation_warnings": "",
            }
        ]
    ).to_csv(outputs_dir / "data_source_status.csv", index=False)

    old_base = dashboard.BASE_DIR
    try:
        dashboard.BASE_DIR = tmp_path
        tables = dashboard.load_data_source_status_tables(outputs_dir, allow_refresh=True)
    finally:
        dashboard.BASE_DIR = old_base

    source_frame, _ = tables["data_source_status.csv"]
    assert source_frame is not None
    assert "target_file" in source_frame.columns
    assert "focus_command" in source_frame.columns
    assert "example_command" in source_frame.columns
    assert source_frame.loc[source_frame["dataset"] == "fundamentals", "example_command"].iloc[0] == "make runbook-fundamentals-broader"


def test_data_source_status_tables_refresh_stale_example_commands(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "write_data_source_outputs", _fake_data_source_outputs)
    outputs_dir = tmp_path
    pd.DataFrame(
        [
            {
                "dataset": "fundamentals",
                "ticker": "",
                "status": "partial",
                "reason": "old",
                "required_for": "valuation",
                "recommended_action": "Start with make status, then follow the printed fundamentals focus or runbook path.",
                "target_file": "data/imports/fundamentals.csv",
                "focus_command": "make status",
                "example_command": "make status",
                "local_file": "data/fundamentals.csv",
                "source_name": "fixture",
            }
        ]
    ).to_csv(outputs_dir / "data_gap_report.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "fundamentals",
                "source_name": "fixture",
                "source_type": "local_csv",
                "availability_status": "partial",
                "required_for": "valuation",
                "is_required": False,
                "is_optional": True,
                "is_manual_only": False,
                "is_unofficial": False,
                "requires_network": False,
                "requires_user_agent": False,
                "requires_api_key": False,
                "expected_local_file": "data/fundamentals.csv",
                "fallback_action": "Start with make status, then follow the printed fundamentals focus or runbook path.",
                "target_file": "data/imports/fundamentals.csv",
                "focus_command": "make status",
                "example_command": "make status",
                "notes": "old",
                "local_file": "data/fundamentals.csv",
                "row_count": 6,
                "available_columns": "ticker,revenue,fcf",
                "validation_warnings": "as_of_date missing",
            }
        ]
    ).to_csv(outputs_dir / "data_source_status.csv", index=False)

    tables = dashboard.load_data_source_status_tables(outputs_dir, allow_refresh=True)

    source_frame, _ = tables["data_source_status.csv"]
    gap_frame, _ = tables["data_gap_report.csv"]
    assert source_frame is not None
    assert gap_frame is not None
    assert source_frame.loc[source_frame["dataset"] == "fundamentals", "example_command"].iloc[0] == "make imports-preview"
    assert gap_frame.loc[gap_frame["dataset"] == "fundamentals", "example_command"].iloc[0] == "make imports-preview"


def test_data_source_status_tables_refresh_stale_action_text(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "write_data_source_outputs", _fake_data_source_outputs)
    outputs_dir = tmp_path
    pd.DataFrame(
        [
            {
                "dataset": "fundamentals",
                "ticker": "",
                "status": "partial",
                "reason": "old",
                "required_for": "valuation",
                "recommended_action": "Stage fundamentals manually, then apply them later.",
                "target_file": "data/imports/fundamentals.csv",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "local_file": "data/imports/fundamentals.csv",
                "source_name": "fixture",
            }
        ]
    ).to_csv(outputs_dir / "data_gap_report.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "fundamentals",
                "source_name": "fixture",
                "source_type": "local_csv",
                "availability_status": "partial",
                "required_for": "valuation",
                "is_required": False,
                "is_optional": True,
                "is_manual_only": False,
                "is_unofficial": False,
                "requires_network": False,
                "requires_user_agent": False,
                "requires_api_key": False,
                "expected_local_file": "data/fundamentals.csv",
                "fallback_action": "Stage fundamentals manually, then apply them later.",
                "target_file": "data/imports/fundamentals.csv",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "notes": "old",
                "local_file": "data/imports/fundamentals.csv",
                "row_count": 6,
                "available_columns": "ticker,revenue,fcf",
                "validation_warnings": "as_of_date missing",
            }
        ]
    ).to_csv(outputs_dir / "data_source_status.csv", index=False)

    tables = dashboard.load_data_source_status_tables(outputs_dir, allow_refresh=True)

    source_frame, _ = tables["data_source_status.csv"]
    gap_frame, _ = tables["data_gap_report.csv"]
    assert source_frame is not None
    assert gap_frame is not None
    refreshed_source_action = source_frame.loc[source_frame["dataset"] == "fundamentals", "fallback_action"].iloc[0]
    refreshed_gap_action = gap_frame.loc[gap_frame["dataset"] == "fundamentals", "recommended_action"].iloc[0]
    assert "make imports-validate" in refreshed_source_action
    assert "make imports-preview" in refreshed_source_action
    assert "make imports-validate" in refreshed_gap_action
    assert "make imports-preview" in refreshed_gap_action


def test_price_update_status_helpers_handle_missing_and_counts(tmp_path):
    frame, message = dashboard.load_price_update_status(tmp_path, allow_write=True)

    assert frame is None
    assert "price_update_status.csv" in message
    assert "make runbook-prices-broader" in message
    assert "make focus-price" in message
    assert "make price-normalize" in message
    assert "make price-validate" in message
    assert "make price-preview" in message
    assert "make price-apply" in message

    counts = dashboard.summarize_price_update_status(
        pd.DataFrame({"status": ["fetched", "parse_error", "parse_error", "source_unavailable"]})
    )

    assert counts["fetched"] == 1
    assert counts["parse_error"] == 2


def test_load_price_update_status_enriches_legacy_command_fields(tmp_path):
    path = tmp_path / "price_update_status.csv"
    pd.DataFrame(
        [
            {
                "ticker": "AMD",
                "status": "parse_error",
                "rows_fetched": 0,
                "rows_merged": 0,
                "error_category": "parse_error",
                "error_message": "AMD parse failed",
                "fallback_used": True,
                "recommended_action": "Run make focus-price TICKER=AMD, or run python3 -m src.data_update --tickers AMD and normalize verified downloaded OHLCV rows into data/imports/prices.csv.",
            }
        ]
    ).to_csv(path, index=False)

    frame, message = dashboard.load_price_update_status(tmp_path, allow_write=True)

    assert message is None
    assert frame is not None
    assert frame.iloc[0]["recommended_action"].startswith("Run make focus-price TICKER=AMD")
    assert frame.iloc[0]["focus_command"] == "make focus-price TICKER=AMD"
    assert frame.iloc[0]["example_command"] == "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual"
    assert frame.iloc[0]["target_file"] == "data/imports/prices.csv"
    rewritten = pd.read_csv(path)
    assert rewritten.iloc[0]["recommended_action"].startswith("Run make focus-price TICKER=AMD")
    assert rewritten.iloc[0]["focus_command"] == "make focus-price TICKER=AMD"
    assert rewritten.iloc[0]["example_command"] == "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual"
    assert rewritten.iloc[0]["target_file"] == "data/imports/prices.csv"


def test_price_update_status_table_columns_surface_command_fields():
    columns = dashboard.price_update_status_table_columns(
        pd.DataFrame(
            [
                {
                    "ticker": "AMD",
                    "status": "parse_error",
                    "rows_fetched": 0,
                    "rows_merged": 0,
                    "error_category": "parse_error",
                    "error_message": "AMD parse failed",
                    "fallback_used": True,
                    "recommended_action": "Fix prices",
                    "focus_command": "make focus-price TICKER=AMD",
                    "example_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                    "target_file": "data/imports/prices.csv",
                }
            ]
        )
    )

    assert columns == [
        "ticker",
        "status",
        "rows_fetched",
        "rows_merged",
        "error_category",
        "error_message",
        "fallback_used",
        "recommended_action",
        "focus_command",
        "example_command",
        "target_file",
    ]


def test_action_queue_table_columns_include_command_safety_context():
    frame = pd.DataFrame(
        [
            {
                "priority": 2,
                "urgency": "high",
                "action_type": "fundamentals",
                "ticker": "NVDA",
                "title": "Stage fundamentals for NVDA",
                "recommended_action": "Inspect fundamentals first.",
                "focus_command": "make focus-fundamentals TICKER=NVDA",
                "example_command": "make sec-stage TICKERS=NVDA",
                "credential_required": "SEC_USER_AGENT",
                "credential_present": False,
                "manual_fallback_command": "make templates",
                "command_safety_note": "Use manual import if credentials are missing.",
                "reason": "Missing fundamentals.",
            }
        ]
    )

    columns = dashboard.action_queue_table_columns(frame)

    assert columns == [
        "priority",
        "urgency",
        "action_type",
        "ticker",
        "title",
        "recommended_action",
        "focus_command",
        "example_command",
        "credential_required",
        "credential_present",
        "manual_fallback_command",
        "command_safety_note",
        "reason",
    ]
    display = dashboard.clean_display_frame(frame[columns])
    assert display.iloc[0]["Credential Present"] == "No"
    assert display.iloc[0]["Manual Fallback Command"] == "make templates"


def test_operator_workflow_table_columns_insert_safety_after_example_command():
    frame = pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "example_command": "make sec-stage TICKERS=NVDA",
                "credential_required": "SEC_USER_AGENT",
                "credential_present": False,
                "manual_fallback_command": "make templates",
                "command_safety_note": "SEC import draft workflow requires credentials.",
            }
        ]
    )

    columns = dashboard.operator_workflow_table_columns(frame, ["ticker", "example_command"])

    assert columns == [
        "ticker",
        "example_command",
        "credential_required",
        "credential_present",
        "manual_fallback_command",
        "command_safety_note",
    ]


def test_ensure_command_safety_columns_preserves_rows_without_regeneration(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    frame = pd.DataFrame(
        [
            {
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
            },
            {
                "focus_command": "make focus-fundamentals TICKER=NVDA",
                "example_command": "make sec-stage TICKERS=NVDA",
            },
        ]
    )

    enriched = dashboard.ensure_command_safety_columns(frame)

    assert enriched is not None
    assert len(enriched) == 2
    assert enriched.iloc[0]["credential_required"] == ""
    assert enriched.iloc[1]["credential_required"] == "SEC_USER_AGENT"
    assert enriched.iloc[1]["credential_present"] is False
    assert enriched.iloc[1]["manual_fallback_command"] == "make templates"


def test_load_action_queue_refreshes_stale_queue_artifact(tmp_path, monkeypatch):
    def fake_write_action_queue_output(_root, *, output_dir):
        pd.DataFrame(
            [
                {
                    "priority": 1,
                    "urgency": "critical",
                    "action_type": "prices",
                    "ticker": "AMD",
                    "title": "Repair price history for AMD",
                    "status": "parse_error",
                    "recommended_action": "Run make focus-price TICKER=AMD, then make price-refresh TICKERS=AMD PROVIDER=yahoo.",
                    "focus_command": "make focus-price TICKER=AMD",
                    "example_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                    "target_file": "data/imports/prices.csv",
                    "source_file": "data/imports/prices.csv",
                    "source_artifact": "outputs/price_update_status.csv",
                    "reason": "AMD parse failed.",
                }
            ]
        ).to_csv(Path(output_dir) / "research_action_queue.csv", index=False)
        return {}

    monkeypatch.setattr(dashboard, "write_action_queue_output", fake_write_action_queue_output)
    pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "AMD",
                "title": "Repair price history for AMD",
                "status": "parse_error",
                "recommended_action": "Retry later or use the manual price import draft workflow in data/imports/prices.csv.",
                "example_command": "python3 -m src.data_update --tickers AMD",
                "source_file": "data/imports/prices.csv",
                "source_artifact": "outputs/price_update_status.csv",
                "reason": "AMD parse failed",
            }
        ]
    ).to_csv(tmp_path / "research_action_queue.csv", index=False)

    frame, message = dashboard.load_action_queue(tmp_path, allow_refresh=True)

    assert message is None
    assert frame is not None
    assert "focus_command" in frame.columns
    assert "example_command" in frame.columns
    assert "target_file" in frame.columns
    price_rows = frame.loc[frame["action_type"].astype(str).str.strip().eq("prices")]
    if not price_rows.empty:
        assert price_rows["recommended_action"].astype(str).str.contains("make focus-price").all()
        assert price_rows["target_file"].astype(str).str.strip().eq("data/imports/prices.csv").all()
    else:
        fundamentals_rows = frame.loc[frame["action_type"].astype(str).str.strip().eq("fundamentals")]
        assert not fundamentals_rows.empty
        assert fundamentals_rows["focus_command"].astype(str).str.startswith("make focus-fundamentals").any()


def test_load_action_queue_refreshes_stale_price_action_text_even_with_current_command_fields(tmp_path, monkeypatch):
    def fake_write_action_queue_output(_root, *, output_dir):
        pd.DataFrame(
            [
                {
                    "priority": 1,
                    "urgency": "critical",
                    "action_type": "prices",
                    "ticker": "AMD",
                    "title": "Repair price history for AMD",
                    "status": "parse_error",
                    "recommended_action": "Run make focus-price TICKER=AMD, then make price-refresh TICKERS=AMD PROVIDER=yahoo.",
                    "focus_command": "make focus-price TICKER=AMD",
                    "example_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                    "target_file": "data/imports/prices.csv",
                    "source_file": "data/imports/prices.csv",
                    "source_artifact": "outputs/price_update_status.csv",
                    "reason": "AMD has stale price action text.",
                }
            ]
        ).to_csv(Path(output_dir) / "research_action_queue.csv", index=False)
        return {}

    monkeypatch.setattr(dashboard, "write_action_queue_output", fake_write_action_queue_output)
    pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "AMD",
                "title": "Fix price coverage",
                "status": "parse_error",
                "recommended_action": "Run make focus-price TICKER=AMD, or run python3 -m src.data_update --tickers AMD and normalize verified downloaded OHLCV files into data/imports/prices.csv.",
                "focus_command": "make focus-price TICKER=AMD",
                "example_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "target_file": "data/imports/prices.csv",
                "source_file": "data/imports/prices.csv",
                "source_artifact": "outputs/data_quality_wizard.csv",
                "reason": "AMD has 0 local price rows.",
            }
        ]
    ).to_csv(tmp_path / "research_action_queue.csv", index=False)

    frame, message = dashboard.load_action_queue(tmp_path, allow_refresh=True)

    assert message is None
    assert frame is not None
    price_rows = frame.loc[(frame["action_type"].astype(str).str.strip() == "prices") & (frame["ticker"].astype(str).str.strip() == "AMD")]
    if not price_rows.empty:
        amd_row = price_rows.iloc[0]
        assert "make price-refresh TICKERS=AMD" in str(amd_row["recommended_action"])
        assert amd_row["focus_command"] == "make focus-price TICKER=AMD"
        assert amd_row["example_command"] == "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual"
    else:
        assert not frame["recommended_action"].astype(str).str.contains("python3 -m src.data_update --tickers AMD").any()
        assert frame["focus_command"].astype(str).str.startswith(("make focus-", "make templates")).any()


def test_load_action_queue_refreshes_stale_staged_fundamentals_queue_artifact(tmp_path, monkeypatch):
    def fake_write_action_queue_output(_root, *, output_dir):
        pd.DataFrame(
            [
                {
                    "priority": 2,
                    "urgency": "high",
                    "action_type": "fundamentals",
                    "ticker": "",
                    "title": "Review fundamentals import draft",
                    "status": "partial",
                    "recommended_action": "Run make imports-validate, then make imports-preview, then make imports-apply.",
                    "focus_command": "make imports-validate",
                    "example_command": "make imports-preview",
                    "target_file": "data/imports/fundamentals.csv",
                    "source_file": "data/imports/fundamentals.csv",
                    "source_artifact": "outputs/data_gap_report.csv",
                    "reason": "Local import draft rows are present in data/imports/fundamentals.csv.",
                }
            ]
        ).to_csv(Path(output_dir) / "research_action_queue.csv", index=False)
        return {}

    monkeypatch.setattr(dashboard, "write_action_queue_output", fake_write_action_queue_output)
    pd.DataFrame(
        [
            {
                "priority": 2,
                "urgency": "high",
                "action_type": "fundamentals",
                "ticker": "",
                "title": "Resolve fundamentals gap",
                "status": "partial",
                "recommended_action": "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local fundamentals and DCF inputs.",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "target_file": "data/imports/fundamentals.csv",
                "source_file": "data/imports/fundamentals.csv",
                "source_artifact": "outputs/data_gap_report.csv",
                "reason": "as_of_date column is unavailable, so freshness is file-based only.",
            }
        ]
    ).to_csv(tmp_path / "research_action_queue.csv", index=False)

    frame, message = dashboard.load_action_queue(tmp_path, allow_refresh=True)

    assert message is None
    assert frame is not None
    staged_rows = frame.loc[frame["focus_command"].astype(str).str.strip().eq("make imports-validate")]
    assert not staged_rows.empty
    assert staged_rows.iloc[0]["title"] == "Review fundamentals import draft"
    assert "data/imports/fundamentals.csv" in str(staged_rows.iloc[0]["reason"])


def test_load_action_queue_refreshes_stale_staged_peer_queue_artifact(tmp_path):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    imports_dir = data_dir / "imports"
    data_dir.mkdir()
    outputs_dir.mkdir()
    imports_dir.mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (data_dir / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,NVDA,100,1000\n",
        encoding="utf-8",
    )
    (data_dir / "fundamentals.csv").write_text(
        "ticker,theme,sector,pe_ratio,revenue_growth,profit_margin,debt_to_equity\n"
        "NVDA,AI,Semis,30,0.2,0.3,0.4\n",
        encoding="utf-8",
    )
    (data_dir / "universe.csv").write_text(
        "ticker,theme,sectoretf,defaultpurpose,marketcapbucket,notes\n"
        "NVDA,AI,SMH,Momentum Leader,Large,fixture\n",
        encoding="utf-8",
    )
    (data_dir / "holdings.csv").write_text(
        "ticker,primarypurpose\n"
        "NVDA,Momentum Leader\n",
        encoding="utf-8",
    )
    (imports_dir / "peers.csv").write_text(
        "ticker,peer_ticker,peer_group,source,as_of_date\n"
        "NVDA,AMD,ai_semis,manual,2026-05-22\n",
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "priority": 2,
                "urgency": "high",
                "action_type": "peers",
                "ticker": "",
                "title": "Resolve peers gap",
                "status": "partial",
                "recommended_action": "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local peer inputs.",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "target_file": "data/imports/peers.csv",
                "source_file": "data/imports/peers.csv",
                "source_artifact": "outputs/data_gap_report.csv",
                "reason": "as_of_date column is unavailable, so freshness is file-based only.",
            }
        ]
    ).to_csv(outputs_dir / "research_action_queue.csv", index=False)

    old_base = dashboard.BASE_DIR
    try:
        dashboard.BASE_DIR = tmp_path
        frame, message = dashboard.load_action_queue(outputs_dir, allow_refresh=True)
    finally:
        dashboard.BASE_DIR = old_base

    assert message is None
    assert frame is not None
    staged_rows = frame.loc[
        frame["focus_command"].astype(str).str.strip().eq("make imports-validate")
        & frame["action_type"].astype(str).str.strip().eq("peers")
    ]
    assert not staged_rows.empty
    assert staged_rows.iloc[0]["title"] == "Review peer import draft"
    assert staged_rows.iloc[0]["target_file"] == "data/imports/peers.csv"
    assert "local import draft rows are present" in str(staged_rows.iloc[0]["reason"]).lower()


def test_load_action_queue_refreshes_stale_manual_peer_queue_artifact(tmp_path):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    pd.DataFrame(
        [
            {"ticker": "AMD", "theme": "AI", "sectoretf": "SMH", "defaultpurpose": "Momentum Leader"},
        ]
    ).to_csv(data_dir / "universe.csv", index=False)
    pd.DataFrame(columns=["ticker", "shares", "primarypurpose"]).to_csv(data_dir / "holdings.csv", index=False)
    pd.DataFrame(
        [
            {
                "priority": 3,
                "urgency": "high",
                "action_type": "peers",
                "ticker": "AMD",
                "title": "Improve peers coverage for AMD",
                "status": "manual_input_needed",
                "recommended_action": "Add peer mappings manually to data/imports/peers.csv.",
                "focus_command": "make templates",
                "example_command": "make templates",
                "target_file": "data/imports/peers.csv",
                "source_file": "data/imports/peers.csv",
                "source_artifact": "outputs/data_onboarding_actions.csv",
                "reason": "No local peer mapping is configured for this ticker.",
            }
        ]
    ).to_csv(outputs_dir / "research_action_queue.csv", index=False)

    old_base = dashboard.BASE_DIR
    try:
        dashboard.BASE_DIR = tmp_path
        frame, message = dashboard.load_action_queue(outputs_dir, allow_refresh=True)
    finally:
        dashboard.BASE_DIR = old_base

    assert message is None
    assert frame is not None
    peer_rows = frame.loc[frame["action_type"].astype(str).str.strip().eq("peers")]
    assert not peer_rows.empty
    assert peer_rows.iloc[0]["focus_command"] == "make focus-peers TICKER=AMD"
    assert "make focus-peers TICKER=AMD" in str(peer_rows.iloc[0]["recommended_action"])


def _fake_research_health_outputs(_root, *, data_dir=None, output_dir):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    stale = pd.read_csv(output_path / "data_quality_wizard.csv") if (output_path / "data_quality_wizard.csv").exists() else pd.DataFrame()
    if stale.empty:
        stale = pd.DataFrame(
            [
                {
                    "Ticker": "AMD",
                    "ReadinessStatus": "Needs Price Data",
                    "NextBestAction": "old",
                }
            ]
        )
    rows = []
    for _, row in stale.iterrows():
        ticker = str(row.get("Ticker", "AMD")).strip().upper() or "AMD"
        status = str(row.get("ReadinessStatus", "Needs Price Data")).strip()
        if status == "Needs Price Data":
            focus_command = f"make focus-price TICKER={ticker}"
            example_command = f"make price-normalize INPUT=data/raw/prices/{ticker}.csv TICKER={ticker} SOURCE=yahoo_manual"
            next_action = f"Run {focus_command}, then make price-refresh TICKERS={ticker} PROVIDER=yahoo."
        else:
            focus_command = f"make focus-fundamentals TICKER={ticker}"
            example_command = f"make sec-stage TICKERS={ticker}"
            next_action = f"Run {focus_command}, then validate fundamentals import drafts before apply."
        rows.append(
            {
                **row.to_dict(),
                "Ticker": ticker,
                "ReadinessStatus": status,
                "NextBestAction": next_action,
                "FocusCommand": focus_command,
                "ExampleCommand": example_command,
            }
        )
    pd.DataFrame(rows).to_csv(output_path / "data_quality_wizard.csv", index=False)
    pd.DataFrame([{"Ticker": "AMD", "LiquidityStatus": "Thin / Needs Review"}]).to_csv(
        output_path / "liquidity_risk.csv",
        index=False,
    )
    pd.DataFrame([{"Ticker": "AMD", "CorrelationStatus": "Low Co-movement"}]).to_csv(
        output_path / "correlation_risk.csv",
        index=False,
    )


def _fake_action_queue_outputs(_root, *, output_dir):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "AMD",
                "title": "Repair price history for AMD",
                "status": "missing",
                "recommended_action": "Run make focus-price TICKER=AMD, then make price-refresh TICKERS=AMD PROVIDER=yahoo.",
                "focus_command": "make focus-price TICKER=AMD",
                "example_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "target_file": "data/imports/prices.csv",
                "source_file": "data/imports/prices.csv",
                "source_artifact": "outputs/price_update_status.csv",
                "reason": "Fixture row.",
            }
        ]
    ).to_csv(output_path / "research_action_queue.csv", index=False)
    return {}


def _fake_onboarding_outputs(_root, *, output_dir):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    coverage = (
        pd.read_csv(output_path / "ticker_data_coverage.csv")
        if (output_path / "ticker_data_coverage.csv").exists()
        else pd.DataFrame([{"ticker": "AMD"}])
    )
    if "ticker" not in coverage.columns:
        coverage["ticker"] = "AMD"
    coverage["target_file"] = "data/imports/prices.csv"
    coverage["focus_command"] = coverage["ticker"].astype(str).str.upper().map(lambda ticker: f"make focus-price TICKER={ticker}")
    coverage["example_command"] = coverage["ticker"].astype(str).str.upper().map(
        lambda ticker: f"make price-normalize INPUT=data/raw/prices/{ticker}.csv TICKER={ticker} SOURCE=yahoo_manual"
    )
    coverage["next_best_action"] = coverage["ticker"].astype(str).str.upper().map(
        lambda ticker: f"Run make focus-price TICKER={ticker}, then make price-refresh TICKERS={ticker} PROVIDER=yahoo."
    )
    coverage.to_csv(output_path / "ticker_data_coverage.csv", index=False)

    optional = (
        pd.read_csv(output_path / "optional_context_worklist.csv")
        if (output_path / "optional_context_worklist.csv").exists()
        else pd.DataFrame([{"ticker": "AMD"}])
    )
    optional["focus_command"] = "make templates"
    optional.to_csv(output_path / "optional_context_worklist.csv", index=False)

    wizard = (
        pd.read_csv(output_path / "data_coverage_wizard.csv")
        if (output_path / "data_coverage_wizard.csv").exists()
        else pd.DataFrame(
            [
                {
                    "priority": 1,
                    "ticker": "AMD",
                    "unlock_goal": "Unlock Monthly Picks",
                    "blocking_dataset": "prices",
                    "current_status": "0 local price rows",
                }
            ]
        )
    )
    wizard_rows = []
    for _, row in wizard.iterrows():
        ticker = str(row.get("ticker", "AMD")).strip().upper() or "AMD"
        dataset = str(row.get("blocking_dataset", "prices")).strip()
        refreshed = row.to_dict()
        refreshed["ticker"] = ticker
        refreshed["credential_required"] = ""
        refreshed["credential_present"] = False
        refreshed["manual_fallback_command"] = "make templates"
        refreshed["command_safety_note"] = "Copy-only command."
        if dataset == "fundamentals":
            refreshed["target_file"] = "data/imports/fundamentals.csv"
            refreshed["focus_command"] = f"make focus-fundamentals TICKER={ticker}"
            refreshed["example_command"] = f"make sec-stage TICKERS={ticker}"
            refreshed["recommended_action"] = (
                f"Run make focus-fundamentals TICKER={ticker}, then make sec-stage TICKERS={ticker} "
                "before validating fundamentals import drafts."
            )
        elif dataset == "peers":
            refreshed["target_file"] = "data/imports/peers.csv"
            refreshed["focus_command"] = f"make focus-peers TICKER={ticker}"
            refreshed["example_command"] = "make templates"
            refreshed["recommended_action"] = (
                f"Run make focus-peers TICKER={ticker}, then fill data/imports/peers.csv with trusted peer mappings."
            )
        else:
            refreshed["blocking_dataset"] = "prices"
            refreshed["target_file"] = "data/imports/prices.csv"
            refreshed["focus_command"] = f"make focus-price TICKER={ticker}"
            refreshed["example_command"] = (
                f"make price-normalize INPUT=data/raw/prices/{ticker}.csv TICKER={ticker} SOURCE=yahoo_manual"
            )
            refreshed["recommended_action"] = (
                f"Run make focus-price TICKER={ticker}, then make price-refresh TICKERS={ticker} PROVIDER=yahoo."
            )
        wizard_rows.append(refreshed)
    pd.DataFrame(wizard_rows).to_csv(output_path / "data_coverage_wizard.csv", index=False)

    pd.DataFrame(
        [
            {
                "dataset": "prices",
                "ticker": "AMD",
                "priority": 1,
                "status": "missing",
                "recommended_action": "Run make focus-price TICKER=AMD, then make price-refresh TICKERS=AMD PROVIDER=yahoo.",
                "target_file": "data/imports/prices.csv",
                "focus_command": "make focus-price TICKER=AMD",
                "example_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "credential_required": "",
                "credential_present": False,
                "manual_fallback_command": "make templates",
                "command_safety_note": "Copy-only command.",
            }
        ]
    ).to_csv(output_path / "data_onboarding_actions.csv", index=False)
    pd.DataFrame([{"ticker": "AMD", "focus_command": "make focus-price TICKER=AMD"}]).to_csv(
        output_path / "price_import_worklist.csv",
        index=False,
    )
    pd.DataFrame([{"ticker": "NVDA", "focus_command": "make focus-fundamentals TICKER=NVDA"}]).to_csv(
        output_path / "fundamentals_peer_worklist.csv",
        index=False,
    )
    pd.DataFrame([{"ticker": "NVDA", "focus_command": "make sec-stage TICKERS=NVDA"}]).to_csv(
        output_path / "sec_stage_queue.csv",
        index=False,
    )
    pd.DataFrame([{"ticker": "META", "focus_command": "make focus-peers TICKER=META"}]).to_csv(
        output_path / "peer_mapping_queue.csv",
        index=False,
    )
    pd.DataFrame([{"ticker": "AMD", "current_unlock_stage": "prices"}]).to_csv(
        output_path / "ticker_unlock_ladder.csv",
        index=False,
    )
    pd.DataFrame([{"workflow_group": "price_unlock", "ticker_count": 1}]).to_csv(
        output_path / "unlock_priority_summary.csv",
        index=False,
    )

    bundles = (
        pd.read_csv(output_path / "command_bundles.csv")
        if (output_path / "command_bundles.csv").exists()
        else pd.DataFrame(
            [
                {
                    "bundle_name": "Price Coverage Bundle",
                    "primary_command": "make price-refresh TICKERS=AMD",
                }
            ]
        )
    )
    if "primary_command" not in bundles.columns:
        bundles["primary_command"] = "make price-refresh TICKERS=AMD"
    bundles["primary_command"] = bundles["primary_command"].map(dashboard.normalize_operator_command)
    bundles.to_csv(output_path / "command_bundles.csv", index=False)

    details = (
        pd.read_csv(output_path / "command_bundle_details.csv")
        if (output_path / "command_bundle_details.csv").exists()
        else pd.DataFrame(
            [
                {
                    "bundle_name": "Price Coverage Bundle",
                    "ticker": "AMD",
                    "exact_next_command": "make focus-price TICKER=AMD",
                    "primary_command": "make price-refresh TICKERS=AMD",
                }
            ]
        )
    )
    if "ticker" not in details.columns:
        details["ticker"] = "AMD"
    if "exact_next_command" not in details.columns:
        details["exact_next_command"] = details["ticker"].astype(str).str.upper().map(lambda ticker: f"make focus-price TICKER={ticker}")
    if "primary_command" not in details.columns:
        details["primary_command"] = "make price-refresh TICKERS=AMD"
    details["exact_next_command"] = details.apply(
        lambda row: f"make focus-price TICKER={str(row.get('ticker', 'AMD')).strip().upper() or 'AMD'}"
        if str(row.get("exact_next_command", "")).startswith("python3 -m src.data_update --tickers ")
        else dashboard.normalize_operator_command(row.get("exact_next_command", "")),
        axis=1,
    )
    details["primary_command"] = details["primary_command"].map(dashboard.normalize_operator_command)
    details.to_csv(output_path / "command_bundle_details.csv", index=False)

    runbook = (
        pd.read_csv(output_path / "command_bundle_runbook.csv")
        if (output_path / "command_bundle_runbook.csv").exists()
        else pd.DataFrame(
            [
                {
                    "bundle_name": "Price Coverage Bundle",
                    "command": "make price-refresh TICKERS=AMD",
                }
            ]
        )
    )
    if "command" not in runbook.columns:
        runbook["command"] = "make price-refresh TICKERS=AMD"
    runbook["command"] = runbook["command"].map(dashboard.normalize_operator_command)
    runbook.to_csv(output_path / "command_bundle_runbook.csv", index=False)
    return {}


def test_load_research_health_tables_refreshes_stale_wizard_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "run_research_health", _fake_research_health_outputs)
    pd.DataFrame(
        [
            {
                "Ticker": "AMD",
                "DataQualityScore": 10,
                "ReadinessStatus": "Needs Price Data",
                "MomentumReady": False,
                "MonthlyPicksReady": False,
                "DCFReady": False,
                "PeerReady": False,
                "EarningsAvailable": False,
                "AnalystEstimatesAvailable": False,
                "PriceHistoryDays": 0,
                "MissingDataFields": "prices",
                "NextBestAction": "old",
                "Reason": "old",
            }
        ]
    ).to_csv(tmp_path / "data_quality_wizard.csv", index=False)

    tables = dashboard.load_research_health_tables(tmp_path, allow_refresh=True)

    frame, message = tables["data_quality_wizard.csv"]
    assert message is None
    assert frame is not None
    assert "FocusCommand" in frame.columns
    assert "ExampleCommand" in frame.columns
    amd_row = frame.loc[frame["Ticker"] == "AMD"].iloc[0]
    if amd_row["FocusCommand"] == "make focus-price TICKER=AMD":
        assert "make price-normalize" in amd_row["ExampleCommand"]
        assert "make focus-price TICKER=AMD" in amd_row["NextBestAction"]
        assert "make price-refresh tickers=amd" in amd_row["NextBestAction"].lower()
    elif amd_row["FocusCommand"] == "make focus-fundamentals TICKER=AMD":
        assert amd_row["FocusCommand"] == "make focus-fundamentals TICKER=AMD"
        assert "make sec-stage TICKERS=AMD" in amd_row["ExampleCommand"]
        assert "make focus-fundamentals TICKER=AMD" in amd_row["NextBestAction"]
    else:
        assert amd_row["FocusCommand"] == "make templates"
        assert "python3 -m src.data_update" not in str(amd_row["NextBestAction"])


def test_load_research_health_tables_refreshes_stale_enrichment_wizard_actions(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "run_research_health", _fake_research_health_outputs)
    pd.DataFrame(
        [
            {
                "Ticker": "NVDA",
                "DataQualityScore": 65,
                "ReadinessStatus": "Needs Enrichment",
                "MomentumReady": True,
                "MonthlyPicksReady": True,
                "DCFReady": False,
                "PeerReady": False,
                "EarningsAvailable": False,
                "AnalystEstimatesAvailable": False,
                "PriceHistoryDays": 80,
                "MissingDataFields": "DCF inputs, peer mapping",
                "NextBestAction": "Run make focus-fundamentals TICKER=NVDA, or stage explicit local fundamentals with make sec-stage TICKERS=NVDA.",
                "FocusCommand": "make focus-fundamentals TICKER=NVDA",
                "ExampleCommand": "make onboarding",
                "Reason": "old",
            }
        ]
    ).to_csv(tmp_path / "data_quality_wizard.csv", index=False)

    tables = dashboard.load_research_health_tables(tmp_path, allow_refresh=True)

    frame, message = tables["data_quality_wizard.csv"]
    assert message is None
    assert frame is not None
    nvda_row = frame.loc[frame["Ticker"] == "NVDA"].iloc[0]
    assert nvda_row["FocusCommand"] != "make onboarding"
    assert "make onboarding" not in str(nvda_row["ExampleCommand"])
    assert str(nvda_row["FocusCommand"]).startswith(("make focus-", "make templates"))


def test_load_data_onboarding_tables_refreshes_stale_coverage_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "write_onboarding_outputs", _fake_onboarding_outputs)
    pd.DataFrame(
        [
            {
                "ticker": "AMD",
                "has_prices": False,
                "price_history_days": 0,
                "has_fundamentals": False,
                "dcf_ready": False,
                "has_peer_mapping": False,
                "peer_ready": False,
                "has_earnings": False,
                "has_analyst_estimates": False,
                "usable_for_momentum": False,
                "usable_for_monthly_picks": False,
                "usable_for_dcf": False,
                "usable_for_peer_relative": False,
                "missing_required_for_momentum": "prices",
                "missing_required_for_dcf": "fundamentals row",
                "missing_required_for_peer_relative": "peer mapping",
                "next_best_action": "old",
            }
        ]
    ).to_csv(tmp_path / "ticker_data_coverage.csv", index=False)

    tables = dashboard.load_data_onboarding_tables(tmp_path, allow_refresh=True)

    frame, message = tables["ticker_data_coverage.csv"]
    assert message is None
    assert frame is not None
    assert {"target_file", "focus_command", "example_command"} <= set(frame.columns)
    amd_row = frame.loc[frame["ticker"] == "AMD"].iloc[0]
    if amd_row["focus_command"] == "make focus-price TICKER=AMD":
        assert "make price-normalize" in amd_row["example_command"]
    elif amd_row["focus_command"] == "make focus-fundamentals TICKER=AMD":
        assert amd_row["focus_command"] == "make focus-fundamentals TICKER=AMD"
        assert "make sec-stage TICKERS=AMD" in amd_row["example_command"]
    else:
        assert amd_row["focus_command"] == "make templates"
        assert "python3 -m src.data_update" not in str(amd_row["next_best_action"])


def test_load_data_onboarding_tables_refreshes_stale_optional_context_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "write_onboarding_outputs", _fake_onboarding_outputs)
    pd.DataFrame(
        [
            {
                "priority": 5,
                "ticker": "AMD",
                "has_earnings": False,
                "has_analyst_estimates": False,
                "earnings_context_ready": False,
                "estimate_context_ready": False,
                "missing_optional_context": "earnings, analyst_estimates",
                "recommended_action": "old",
                "target_file": "data/imports/earnings.csv and data/imports/analyst_estimates.csv",
                "example_command": "make templates",
                "safe_next_step": "old",
            }
        ]
    ).to_csv(tmp_path / "optional_context_worklist.csv", index=False)

    tables = dashboard.load_data_onboarding_tables(tmp_path, allow_refresh=True)

    frame, message = tables["optional_context_worklist.csv"]
    assert message is None
    assert frame is not None
    assert "focus_command" in frame.columns
    amd_row = frame.loc[frame["ticker"] == "AMD"].iloc[0]
    assert amd_row["focus_command"] == "make templates"


def test_load_data_onboarding_tables_refreshes_stale_coverage_wizard_actions(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "write_onboarding_outputs", _fake_onboarding_outputs)
    pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "unlock_goal": "Unlock Monthly Picks",
                "blocking_dataset": "prices",
                "current_status": "0 local price rows",
                "why_it_matters": "old",
                "recommended_action": "Run make focus-price TICKER=AMD, or run python3 -m src.data_update --tickers AMD and normalize verified downloaded OHLCV files into data/imports/prices.csv.",
                "target_file": "data/imports/prices.csv",
                "focus_command": "make focus-price TICKER=AMD",
                "example_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "safe_next_step": "old",
            },
            {
                "priority": 2,
                "ticker": "NVDA",
                "unlock_goal": "Unlock DCF",
                "blocking_dataset": "fundamentals",
                "current_status": "DCF inputs incomplete",
                "why_it_matters": "old",
                "recommended_action": "Run make focus-fundamentals TICKER=NVDA, or stage explicit local fundamentals with make sec-stage TICKERS=NVDA.",
                "target_file": "data/imports/fundamentals.csv",
                "focus_command": "make focus-fundamentals TICKER=NVDA",
                "example_command": "make onboarding",
                "safe_next_step": "old",
            },
            {
                "priority": 3,
                "ticker": "META",
                "unlock_goal": "Unlock Peer Relative",
                "blocking_dataset": "peers",
                "current_status": "Peer-relative inputs incomplete",
                "why_it_matters": "old",
                "recommended_action": "Run make focus-peers TICKER=META, or run make templates, then fill data/imports/peers.csv manually with transparent peer mappings.",
                "target_file": "data/imports/peers.csv",
                "focus_command": "make focus-peers TICKER=META",
                "example_command": "make onboarding",
                "safe_next_step": "old",
            },
        ]
    ).to_csv(tmp_path / "data_coverage_wizard.csv", index=False)

    tables = dashboard.load_data_onboarding_tables(tmp_path, allow_refresh=True)

    frame, message = tables["data_coverage_wizard.csv"]
    assert message is None
    assert frame is not None

    amd_price_rows = frame.loc[(frame["ticker"] == "AMD") & (frame["blocking_dataset"] == "prices")]

    if not amd_price_rows.empty:
        amd_row = amd_price_rows.iloc[0]
        assert "make focus-price TICKER=AMD" in str(amd_row["recommended_action"])
        assert "make price-refresh TICKERS=AMD" in str(amd_row["recommended_action"])
        assert amd_row["focus_command"] == "make focus-price TICKER=AMD"
        assert "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual" == amd_row["example_command"]
    assert not frame["recommended_action"].astype(str).str.contains("python3 -m src.data_update --tickers AMD").any()
    stale_followups = {"make onboarding"}
    assert not set(frame["example_command"].astype(str)) & stale_followups
    assert frame["focus_command"].astype(str).str.startswith(("make focus-", "make templates")).any()


def test_load_data_onboarding_tables_refreshes_stale_bundle_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "write_onboarding_outputs", _fake_onboarding_outputs)
    pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "ticker_count": 2,
                "tickers": "AMD,AVGO",
                "goal_summary": "old",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "bundle_shortcut_command": "make bundle-prices",
                "detail_shortcut_command": "make detail-prices",
                "runbook_shortcut_command": "make runbook-prices",
                "primary_command": "python3 -m src.data_update --tickers AMD,AVGO",
                "follow_up_command": "make price-status",
                "target_file": "data/imports/prices.csv",
                "why_it_matters": "old",
                "safe_next_step": "old",
            }
        ]
    ).to_csv(tmp_path / "command_bundles.csv", index=False)
    pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "ticker": "AMD",
                "is_holding": True,
                "theme": "AI Infra",
                "sector_etf": "SMH",
                "current_unlock_stage": "prices",
                "target_goal": "Unlock Monthly Picks",
                "rows_needed": 21,
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "fallback_manual_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "exact_next_command": "python3 -m src.data_update --tickers AMD",
                "recommended_action": "old",
                "primary_command": "python3 -m src.data_update --tickers AMD,AVGO",
                "follow_up_command": "make price-status",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "old",
            }
        ]
    ).to_csv(tmp_path / "command_bundle_details.csv", index=False)
    pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "python3 -m src.data_update --tickers AMD,AVGO",
                "target_file": "data/imports/prices.csv",
                "tickers": "AMD,AVGO",
                "goal_summary": "old",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "fallback_manual_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "why_it_matters": "old",
                "safe_next_step": "old",
            }
        ]
    ).to_csv(tmp_path / "command_bundle_runbook.csv", index=False)

    tables = dashboard.load_data_onboarding_tables(tmp_path, allow_refresh=True)

    bundle_frame, bundle_message = tables["command_bundles.csv"]
    detail_frame, detail_message = tables["command_bundle_details.csv"]
    runbook_frame, runbook_message = tables["command_bundle_runbook.csv"]

    assert bundle_message is None
    assert detail_message is None
    assert runbook_message is None
    assert bundle_frame is not None
    assert detail_frame is not None
    assert runbook_frame is not None
    assert not bundle_frame["primary_command"].astype(str).str.startswith("python3 -m src.data_update --tickers ").any()
    assert not detail_frame["exact_next_command"].astype(str).str.startswith("python3 -m src.data_update --tickers ").any()
    assert not runbook_frame["command"].astype(str).str.startswith("python3 -m src.data_update --tickers ").any()
    assert bundle_frame["primary_command"].astype(str).str.startswith(("make price-refresh TICKERS=", "make sec-stage TICKERS=")).any()
    assert detail_frame["exact_next_command"].astype(str).str.startswith(("make focus-price", "make focus-fundamentals", "make focus-peers")).any()


def test_load_data_onboarding_tables_refreshes_env_prefixed_sec_bundle_commands(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "write_onboarding_outputs", _fake_onboarding_outputs)
    pd.DataFrame(
        [
            {
                "bundle_name": "Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "ticker_count": 1,
                "tickers": "NVDA",
                "goal_summary": "old",
                "target_history_rows": 0,
                "suggested_start_date": "",
                "bundle_shortcut_command": "make bundle-fundamentals",
                "detail_shortcut_command": "make detail-fundamentals",
                "runbook_shortcut_command": "make runbook-fundamentals",
                "primary_command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=NVDA",
                "follow_up_command": "make imports-validate",
                "target_file": "data/imports/fundamentals.csv",
                "why_it_matters": "old",
                "safe_next_step": "old",
            }
        ]
    ).to_csv(tmp_path / "command_bundles.csv", index=False)

    tables = dashboard.load_data_onboarding_tables(tmp_path, allow_refresh=True)

    bundle_frame, bundle_message = tables["command_bundles.csv"]
    assert bundle_message is None
    assert bundle_frame is not None
    assert not bundle_frame["primary_command"].astype(str).str.startswith("SEC_USER_AGENT=").any()
    assert bundle_frame["primary_command"].astype(str).str.startswith("make sec-stage TICKERS=").any()


def test_onboarding_tables_handle_missing_outputs_and_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "write_onboarding_outputs", _fake_onboarding_outputs)
    tables = dashboard.load_data_onboarding_tables(tmp_path / "missing-onboarding-outputs", allow_refresh=True)

    for filename in (
        "ticker_data_coverage.csv",
        "price_import_worklist.csv",
        "fundamentals_peer_worklist.csv",
        "optional_context_worklist.csv",
        "sec_stage_queue.csv",
        "peer_mapping_queue.csv",
        "ticker_unlock_ladder.csv",
        "unlock_priority_summary.csv",
    ):
        frame, message = tables[filename]
        assert frame is not None
        assert message is None
    assert dashboard.summarize_ticker_coverage(None)["usable_price_tickers"] == 0
    assert dashboard.summarize_price_worklist(None)["priority_1"] == 0
    assert dashboard.summarize_fundamentals_peer_worklist(None)["fundamentals_priority_1"] == 0
    assert dashboard.summarize_optional_context_worklist(None)["missing_both"] == 0
    assert dashboard.summarize_sec_stage_queue(None)["priority_1"] == 0
    assert dashboard.summarize_peer_mapping_queue(None)["priority_1"] == 0
    assert dashboard.summarize_ticker_unlock_ladder(None)["price_stage"] == 0
    assert dashboard.summarize_unlock_priority_summary(None)["holdings_groups"] == 0


def test_summarize_price_worklist_counts_readiness_levels():
    worklist = pd.DataFrame(
        {
            "next_price_goal": ["Unlock Track Record", "Unlock Monthly Picks", "Reach Preferred 1Y History"],
            "next_target_history_rows": [63, 21, 252],
            "rows_needed_for_next_goal": [42, 21, 189],
            "suggested_start_date": ["2025-10-01", "2026-01-01", "2025-01-01"],
            "momentum_ready": [True, False, True],
            "track_record_ready": [False, False, True],
            "preferred_history_ready": [False, False, False],
            "priority": [1, 2, 1],
        }
    )

    summary = dashboard.summarize_price_worklist(worklist)

    assert summary["momentum_ready"] == 2
    assert summary["track_record_ready"] == 1
    assert summary["preferred_history_ready"] == 0
    assert summary["priority_1"] == 2


def test_summarize_fundamentals_peer_worklist_counts_blockers():
    worklist = pd.DataFrame(
        {
            "dcf_ready": [True, False, False],
            "peer_ready": [False, False, True],
            "priority": [2, 1, 4],
        }
    )

    summary = dashboard.summarize_fundamentals_peer_worklist(worklist)

    assert summary["dcf_ready"] == 1
    assert summary["peer_ready"] == 1
    assert summary["fundamentals_priority_1"] == 1
    assert summary["peer_priority_2"] == 1


def test_summarize_optional_context_worklist_counts_missing_optional_coverage():
    worklist = pd.DataFrame(
        {
            "has_earnings": [True, False, False],
            "has_analyst_estimates": [False, False, True],
            "priority": [6, 5, 6],
        }
    )

    summary = dashboard.summarize_optional_context_worklist(worklist)

    assert summary["earnings_ready"] == 1
    assert summary["estimates_ready"] == 1
    assert summary["missing_both"] == 1
    assert summary["missing_one"] == 2


def test_summarize_sec_stage_queue_counts_priority_and_missing_rows():
    worklist = pd.DataFrame(
        {
            "priority": [1, 2, 2],
            "is_holding": [True, False, True],
            "has_fundamentals": [False, True, False],
        }
    )

    summary = dashboard.summarize_sec_stage_queue(worklist)

    assert summary["priority_1"] == 1
    assert summary["priority_2"] == 2
    assert summary["holdings"] == 2
    assert summary["missing_fundamentals"] == 2


def test_summarize_peer_mapping_queue_counts_priority_and_missing_mappings():
    worklist = pd.DataFrame(
        {
            "priority": [1, 2, 4],
            "is_holding": [True, False, True],
            "has_peer_mapping": [False, True, False],
            "peer_ready": [False, False, False],
            "focus_command": ["make focus-peers TICKER=NVDA", "make imports-validate", "make focus-peers TICKER=TSLA"],
            "target_file": ["data/imports/peers.csv", "data/imports/peers.csv", "data/imports/peers.csv"],
        }
    )

    summary = dashboard.summarize_peer_mapping_queue(worklist)

    assert summary["priority_1"] == 1
    assert summary["priority_2"] == 1
    assert summary["holdings"] == 2
    assert summary["missing_peer_mapping"] == 2
    assert summary["mapped_peer_follow_through"] == 1
    assert summary["staged_peer_import"] == 1


def test_summarize_ticker_unlock_ladder_counts_stages():
    worklist = pd.DataFrame(
        {
            "current_unlock_stage": ["prices", "fundamentals", "peers", "optional_context", "ready"],
        }
    )

    summary = dashboard.summarize_ticker_unlock_ladder(worklist)

    assert summary["price_stage"] == 1
    assert summary["fundamentals_stage"] == 1
    assert summary["peer_stage"] == 1
    assert summary["optional_stage"] == 1
    assert summary["ready_stage"] == 1


def test_summarize_unlock_priority_summary_counts_group_types_and_stages():
    worklist = pd.DataFrame(
        {
            "group_type": ["holdings", "theme", "theme", "sector_etf"],
            "top_priority_stage": ["prices", "fundamentals", "prices", "peers"],
        }
    )

    summary = dashboard.summarize_unlock_priority_summary(worklist)

    assert summary["holdings_groups"] == 1
    assert summary["theme_groups"] == 2
    assert summary["sector_groups"] == 1
    assert summary["price_led_groups"] == 2
    assert summary["fundamentals_led_groups"] == 1


def test_research_health_tables_handle_missing_outputs_and_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "run_research_health", _fake_research_health_outputs)
    tables = dashboard.load_research_health_tables(tmp_path, allow_refresh=True)

    wizard_frame, wizard_message = tables["data_quality_wizard.csv"]
    liquidity_frame, liquidity_message = tables["liquidity_risk.csv"]
    correlation_frame, correlation_message = tables["correlation_risk.csv"]

    assert wizard_frame is not None
    assert liquidity_frame is not None
    assert correlation_frame is not None
    assert wizard_message is None
    assert liquidity_message is None
    assert correlation_message is None
    assert "FocusCommand" in wizard_frame.columns

    summary = dashboard.summarize_research_health_tables(
        pd.DataFrame({"ReadinessStatus": ["Research Ready", "Needs Price Data"]}),
        pd.DataFrame({"LiquidityStatus": ["Liquid", "Thin / Needs Review"]}),
        pd.DataFrame({"CorrelationStatus": ["High Co-movement", "Low Co-movement"]}),
    )

    assert summary["research_ready"] == 1
    assert summary["needs_price_data"] == 1
    assert summary["liquid"] == 1
    assert summary["thin_liquidity"] == 1
    assert summary["high_correlation"] == 1


def test_action_queue_loader_and_summary_handle_missing_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "write_action_queue_output", _fake_action_queue_outputs)
    frame, message = dashboard.load_action_queue(tmp_path, allow_refresh=True)

    assert frame is not None
    assert message is None
    assert "focus_command" in frame.columns
    assert "example_command" in frame.columns

    summary = dashboard.action_queue_summary(
        pd.DataFrame({"urgency": ["critical", "high", "medium", "critical"]})
    )
    assert summary["critical"] == 2
    assert summary["high"] == 1
    assert summary["medium"] == 1


def test_top_priority_signals_are_compact_and_sorted():
    queue = pd.DataFrame(
        [
            {"priority": 2, "urgency": "high", "action_type": "fundamentals", "ticker": "NVDA", "title": "Improve fundamentals", "reason": "Need SEC import draft workflow.", "focus_command": "make focus-fundamentals TICKER=NVDA", "example_command": "make sec-stage"},
            {"priority": 1, "urgency": "critical", "action_type": "prices", "ticker": "AMD", "title": "Repair prices", "reason": "No local prices.", "recommended_action": "Normalize verified downloaded OHLCV rows, then run make price-validate, make price-preview, and make price-apply.", "focus_command": "make focus-price TICKER=AMD", "example_command": "make price-refresh"},
        ]
    )

    signals = dashboard.top_priority_signals(queue, limit=2)

    assert signals[0]["title"] == "make focus-price TICKER=AMD"
    assert "P1" in signals[0]["badges"]
    assert signals[0]["command"] == "make focus-price TICKER=AMD"
    assert "normalize verified downloaded ohlcv rows" in signals[0]["body"].lower()
    assert signals[1]["title"] == "make focus-fundamentals TICKER=NVDA"


def test_top_priority_signals_use_lane_front_doors_when_commands_are_missing():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "peers",
                "ticker": "AMD",
                "title": "Research peers",
                "reason": "Peer mappings are missing.",
                "recommended_action": "Add manually researched mappings through the local import draft flow.",
                "focus_command": "",
                "example_command": "",
            },
            {
                "priority": 2,
                "urgency": "high",
                "action_type": "unknown",
                "ticker": "",
                "title": "Review queue",
                "reason": "A portfolio-wide workflow step is still pending.",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
            },
        ]
    )

    signals = dashboard.top_priority_signals(queue, limit=2)

    assert signals[0]["title"] == "make focus-peers TICKER=AMD"
    assert signals[0]["command"] == "make focus-peers TICKER=AMD"
    assert signals[1]["title"] == "make action-queue-check TOP_N=10"
    assert signals[1]["command"] == "make action-queue-check TOP_N=10"


def test_top_priority_signals_use_review_fallback_when_row_copy_is_missing():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "AMD",
                "title": "Repair prices",
                "reason": "",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
            }
        ]
    )

    signals = dashboard.top_priority_signals(queue, limit=1)

    assert signals[0]["title"] == "make focus-price TICKER=AMD"
    assert "review price path." in signals[0]["body"].lower()
    assert "not available" not in signals[0]["body"].lower()


def test_top_priority_signals_use_command_family_fallbacks_when_row_copy_is_missing():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "fundamentals",
                "ticker": "NVDA",
                "title": "Review fundamentals import draft",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make imports-validate",
                "example_command": "",
            },
            {
                "priority": 2,
                "urgency": "high",
                "action_type": "peers",
                "ticker": "",
                "title": "Run peer bundle",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make bundle-peers",
                "example_command": "",
            },
            {
                "priority": 3,
                "urgency": "high",
                "action_type": "peers",
                "ticker": "TSLA",
                "title": "Open peer runbook",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make runbook-peers",
                "example_command": "",
            },
        ]
    )

    signals = dashboard.top_priority_signals(queue, limit=3)

    assert signals[0]["title"] == "make imports-validate"
    assert "make imports-preview" in signals[0]["body"].lower()
    assert "make imports-apply" in signals[0]["body"].lower()
    assert signals[1]["title"] == "make bundle-peers"
    assert "highest-leverage local bundle first" in signals[1]["body"].lower()
    assert signals[2]["title"] == "make runbook-peers"
    assert "ordered lane runbook" in signals[2]["body"].lower()
    assert "not available" not in " ".join(signal["body"] for signal in signals).lower()


def test_top_priority_signals_keep_staged_follow_through_visible():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "fundamentals",
                "ticker": "NVDA",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            },
            {
                "priority": 2,
                "urgency": "high",
                "action_type": "peers",
                "ticker": "TSLA",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            },
            {
                "priority": 3,
                "urgency": "high",
                "action_type": "prices",
                "ticker": "AMD",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make price-validate",
                "example_command": "",
                "target_file": "data/imports/prices.csv",
            },
        ]
    )

    signals = dashboard.top_priority_signals(queue, limit=3)

    assert signals[0]["command"] == "make imports-validate"
    assert "make imports-preview" in signals[0]["body"].lower()
    assert "make imports-apply" in signals[0]["body"].lower()
    assert signals[1]["command"] == "make imports-validate"
    assert "make imports-preview" in signals[1]["body"].lower()
    assert "make imports-apply" in signals[1]["body"].lower()
    assert signals[2]["command"] == "make price-validate"
    assert "make price-preview" in signals[2]["body"].lower()
    assert "make price-apply" in signals[2]["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in " ".join(signal["body"] for signal in signals).lower()


def test_operator_summary_helpers_normalize_legacy_status_copy():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "fundamentals",
                "ticker": "NVDA",
                "reason": "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local fundamentals.",
                "recommended_action": "",
            }
        ]
    )
    payload = {
        "top_onboarding_actions": [
            {
                "priority": 1,
                "dataset": "fundamentals",
                "ticker": "NVDA",
                "reason": "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local fundamentals.",
                "recommended_action": "",
            }
        ]
    }
    actions = pd.DataFrame(
        [
            {
                "priority": 1,
                "dataset": "fundamentals",
                "ticker": "NVDA",
                "reason": "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local fundamentals.",
                "recommended_action": "",
            }
        ]
    )

    signals = dashboard.top_priority_signals(queue, limit=1)
    status_actions = dashboard.project_status_action_cards(payload)
    action_cards = dashboard.data_health_action_path_cards(actions, queue)

    assert "make status-check TOP_N=5" in signals[0]["body"]
    assert "make status-check TOP_N=5" in status_actions[0][1]
    assert "make status-check TOP_N=5" in action_cards[1]["body"]


def test_workflow_health_score_reflects_action_pressure():
    strong_score, strong_label = dashboard.workflow_health_score(
        {"critical": 0, "high": 0, "medium": 1},
        {"needs_price_data": 0, "thin_liquidity": 0, "high_correlation": 0},
    )
    weak_score, weak_label = dashboard.workflow_health_score(
        {"critical": 8, "high": 4, "medium": 0},
        {"needs_price_data": 6, "thin_liquidity": 2, "high_correlation": 1},
    )

    assert strong_score == 100
    assert strong_label == "Ready"
    assert weak_score < strong_score
    assert weak_label in {"Partial", "Needs Data"}


def test_project_status_helpers_turn_payload_into_cards_and_commands():
    payload = {
        "summary": {
            "data_sources_total": 10,
            "data_sources_available": 4,
            "data_gaps": 12,
            "tickers_total": 20,
            "tickers_with_prices": 9,
            "tickers_dcf_ready": 3,
            "tickers_peer_ready": 2,
            "critical_actions": 5,
            "onboarding_actions": 18,
        },
        "top_onboarding_actions": [
            {
                "priority": 1,
                "dataset": "prices",
                "ticker": "NVDA",
                "reason": "Short local price history.",
                "recommended_action": "Normalize verified downloaded OHLCV rows, then run make price-validate, make price-preview, and make price-apply.",
                "focus_command": "make focus-price TICKER=NVDA",
                "example_command": "make price-refresh",
            }
        ],
        "recommended_next_commands": ["make onboarding", "make verify"],
    }

    cards = dashboard.project_status_metric_cards(payload)
    actions = dashboard.project_status_action_cards(payload)
    commands = dashboard.project_status_command_rows(payload)
    rendered = " ".join(str(value) for card in cards for value in card)

    assert "4/10" in rendered
    assert "9/20" in rendered
    assert actions[0][0] == "P1 prices - NVDA"
    assert "normalize verified downloaded ohlcv rows" in actions[0][1].lower()
    assert actions[0][2] == "make focus-price TICKER=NVDA"
    assert actions[0][3] == "danger"
    assert commands[0]["Command"] == "make status-check TOP_N=5"


def test_project_status_cockpit_is_readable_and_research_safe():
    payload = {
        "summary": {
            "tickers_total": 12,
            "tickers_with_prices": 3,
            "tickers_dcf_ready": 0,
            "tickers_peer_ready": 0,
            "critical_actions": 9,
            "data_gaps": 25,
        }
    }

    html = dashboard.project_status_cockpit_html(payload, 44, "Needs Data")

    assert "Research Cockpit" in html
    assert "3/12" in html
    assert "0/12" in html
    assert "missing inputs are labeled instead of guessed" in html
    assert "buy" not in html.lower()
    assert "sell" not in html.lower()


def test_project_status_read_only_fallbacks_use_status_check():
    actions = dashboard.project_status_action_cards(None)
    html = dashboard.project_status_cockpit_html(None, 0, "Unknown")

    assert actions[0][0] == "Project status unavailable"
    assert actions[0][2] == "make status-check TOP_N=5"
    assert "read-only status command" in actions[0][1].lower()
    assert "make status-check top_n=5" in html.lower()
    assert "buy" not in html.lower()
    assert "sell" not in html.lower()


def test_project_status_action_cards_use_lane_front_doors_when_commands_are_missing():
    payload = {
        "top_onboarding_actions": [
            {
                "priority": 1,
                "dataset": "fundamentals",
                "ticker": "AMD",
                "reason": "DCF inputs are still missing.",
                "recommended_action": "Stage candidate fundamentals and preview them before apply.",
                "focus_command": "",
                "example_command": "",
            }
        ]
    }

    actions = dashboard.project_status_action_cards(payload)

    assert actions[0][0] == "P1 fundamentals - AMD"
    assert actions[0][2] == "make focus-fundamentals TICKER=AMD"


def test_project_status_action_cards_use_review_fallback_when_row_copy_is_missing():
    payload = {
        "top_onboarding_actions": [
            {
                "priority": 1,
                "dataset": "peers",
                "ticker": "TSLA",
                "reason": "",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
            }
        ]
    }

    actions = dashboard.project_status_action_cards(payload)

    assert actions[0][0] == "P1 peers - TSLA"
    assert actions[0][2] == "make focus-peers TICKER=TSLA"
    assert "review peer path." in actions[0][1].lower()
    assert "not available" not in actions[0][1].lower()


def test_project_status_action_cards_use_command_family_fallbacks_when_row_copy_is_missing():
    payload = {
        "top_onboarding_actions": [
            {
                "priority": 1,
                "dataset": "fundamentals",
                "ticker": "NVDA",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make imports-validate",
                "example_command": "",
            },
            {
                "priority": 2,
                "dataset": "peers",
                "ticker": "",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make bundle-peers",
                "example_command": "",
            },
            {
                "priority": 3,
                "dataset": "peers",
                "ticker": "TSLA",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make runbook-peers",
                "example_command": "",
            },
        ]
    }

    actions = dashboard.project_status_action_cards(payload)

    assert actions[0][2] == "make imports-validate"
    assert "make imports-preview" in actions[0][1].lower()
    assert "make imports-apply" in actions[0][1].lower()
    assert actions[1][2] == "make bundle-peers"
    assert "highest-leverage local bundle first" in actions[1][1].lower()
    assert actions[2][2] == "make runbook-peers"
    assert "ordered lane runbook" in actions[2][1].lower()
    assert "not available" not in " ".join(action[1] for action in actions).lower()


def test_project_status_action_cards_keep_staged_import_follow_through_visible():
    payload = {
        "top_onboarding_actions": [
            {
                "priority": 1,
                "dataset": "fundamentals",
                "ticker": "NVDA",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            },
            {
                "priority": 2,
                "dataset": "peers",
                "ticker": "TSLA",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            },
            {
                "priority": 3,
                "dataset": "prices",
                "ticker": "AMD",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make price-validate",
                "example_command": "",
                "target_file": "data/imports/prices.csv",
            },
        ]
    }

    actions = dashboard.project_status_action_cards(payload)

    assert actions[0][2] == "make imports-validate"
    assert "make imports-preview" in actions[0][1].lower()
    assert "make imports-apply" in actions[0][1].lower()
    assert actions[1][2] == "make imports-validate"
    assert "make imports-preview" in actions[1][1].lower()
    assert "make imports-apply" in actions[1][1].lower()
    assert actions[2][2] == "make price-validate"
    assert "make price-preview" in actions[2][1].lower()
    assert "make price-apply" in actions[2][1].lower()
    assert "use local import draft workflows if the free refresh fails" not in " ".join(action[1] for action in actions).lower()


def test_project_status_command_rows_prefer_structured_rows():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Fix top prices blocker (NVDA)",
                "Command": "make focus-price TICKER=NVDA",
                "Reason": "Short local price history still blocks downstream work.",
                "SourceContext": "data/imports/prices.csv",
                "FreshnessContext": "2026-05-21",
            },
            {
                "Step": "Run Price Coverage Bundle (Broader Queue)",
                "Command": "make runbook-prices-broader",
                "Reason": "Advance broader local price coverage next.",
            },
        ],
        "recommended_next_commands": ["make onboarding", "make verify"],
    }

    rows = dashboard.project_status_command_rows(payload)

    assert rows[0]["Step"] == "Fix top prices blocker (NVDA)"
    assert rows[0]["Command"] == "make focus-price TICKER=NVDA"
    assert rows[0]["Reason"] == "Short local price history still blocks downstream work."
    assert rows[0]["SourceContext"] == "data/imports/prices.csv"
    assert rows[0]["FreshnessContext"] == "2026-05-21"
    assert rows[1]["Command"] == "make runbook-prices-broader"


def test_project_status_command_rows_use_status_check_when_structured_command_is_missing():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Read-only status snapshot",
                "Command": "",
                "Reason": "Rebuild the local status snapshot before choosing a deeper workflow path.",
            }
        ]
    }

    rows = dashboard.project_status_command_rows(payload)

    assert rows[0]["Step"] == "Read-only status snapshot"
    assert rows[0]["Command"] == "make status-check TOP_N=5"
    assert rows[0]["Reason"] == "Rebuild the local status snapshot before choosing a deeper workflow path."


def test_overview_landing_cards_surface_workflow_and_gap_context():
    payload = {
        "summary": {
            "tickers_total": 12,
            "tickers_with_prices": 3,
            "tickers_dcf_ready": 0,
            "tickers_peer_ready": 0,
            "data_gaps": 25,
        }
    }
    cards = dashboard.overview_landing_cards(payload, {"critical": 4, "high": 7}, "2026-05-12", 12, 4)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 4
    assert "12 research rows" in rendered
    assert "4 current monthly candidates" in rendered
    assert "3/12" in rendered
    assert "0 dcf-ready" in rendered
    assert cards[0]["command"] == "make monthly"
    assert cards[1]["command"] == "make runbook-prices-broader"
    assert cards[2]["command"] == "make runbook-fundamentals-broader"
    assert cards[3]["command"] == "make action-queue-check TOP_N=10"
    assert "make action-queue-check top_n=10" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_holdings_unlock_cards_surface_portfolio_blockers():
    holdings = pd.DataFrame(
        [
            {"Ticker": "NVDA", "PrimaryPurpose": "Momentum Leader"},
            {"Ticker": "TSLA", "PrimaryPurpose": "Speculative Optionality"},
        ]
    )
    ladder = pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "current_unlock_stage": "fundamentals",
                "next_unlock_goal": "Unlock DCF",
                "recommended_action": "Stage verified fundamentals.",
                "focus_command": "make focus-fundamentals TICKER=NVDA",
                "example_command": "make sec-stage TICKERS=NVDA",
                "price_stage_status": "momentum_ready_short_history",
            },
            {
                "ticker": "TSLA",
                "current_unlock_stage": "prices",
                "next_unlock_goal": "Unlock Monthly Picks",
                "recommended_action": "Add more verified local price history.",
                "focus_command": "make focus-price TICKER=TSLA",
                "example_command": "make price-refresh",
                "price_stage_status": "partial_price_history",
            },
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "group_type": "holdings",
                "group_name": "Current Holdings",
                "ticker_count": 2,
                "holdings_count": 2,
                "top_priority_stage": "prices",
                "next_unlock_goal": "Unlock Monthly Picks",
                "representative_tickers": "TSLA, NVDA",
                "focus_command": "make status",
                "example_command": "make runbook-prices",
            }
        ]
    )

    cards = dashboard.holdings_unlock_cards(holdings, ladder, summary, limit=2)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "HOLDINGS FIRST"
    assert "unlock monthly picks" in rendered
    assert "nvda" in rendered
    assert "tsla" in rendered
    assert cards[0]["command"] == "make runbook-prices"
    assert any(card.get("command") == "make focus-price TICKER=TSLA" for card in cards)
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_holdings_unlock_cards_handle_missing_inputs_gracefully():
    cards = dashboard.holdings_unlock_cards(None, None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "no holdings unlock board yet" in rendered
    assert "make onboarding" in rendered
    assert cards[0]["command"] == "make onboarding"
    assert "buy" not in rendered


def test_holdings_unlock_cards_use_review_fallback_when_action_is_missing():
    holdings = pd.DataFrame([{"Ticker": "AMD", "PrimaryPurpose": "Core Compounder"}])
    ladder = pd.DataFrame(
        [
            {
                "ticker": "AMD",
                "current_unlock_stage": "fundamentals",
                "next_unlock_goal": "Unlock DCF",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "price_stage_status": "momentum_ready_short_history",
            }
        ]
    )

    cards = dashboard.holdings_unlock_cards(holdings, ladder, None, limit=1)

    assert cards[0]["kicker"] == "AMD"
    assert "review fundamentals path." in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_holdings_unlock_cards_use_runbook_fallback_when_action_is_missing():
    holdings = pd.DataFrame([{"Ticker": "AMD", "PrimaryPurpose": "Core Compounder"}])
    ladder = pd.DataFrame(
        [
            {
                "ticker": "AMD",
                "current_unlock_stage": "peers",
                "next_unlock_goal": "Unlock Peer Relative",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "make runbook-peers",
                "price_stage_status": "momentum_ready_short_history",
            }
        ]
    )

    cards = dashboard.holdings_unlock_cards(holdings, ladder, None, limit=1)

    assert cards[0]["kicker"] == "AMD"
    assert cards[0]["command"] == "make runbook-peers"
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_holdings_unlock_cards_keep_staged_import_front_doors_when_target_files_are_present():
    holdings = pd.DataFrame(
        [
            {"Ticker": "AMD", "PrimaryPurpose": "Core Compounder"},
            {"Ticker": "NVDA", "PrimaryPurpose": "Momentum Leader"},
            {"Ticker": "TSLA", "PrimaryPurpose": "Speculative Optionality"},
        ]
    )
    ladder = pd.DataFrame(
        [
            {
                "ticker": "AMD",
                "current_unlock_stage": "prices",
                "next_unlock_goal": "Unlock Monthly Picks",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/prices.csv",
                "price_stage_status": "partial_price_history",
            },
            {
                "ticker": "NVDA",
                "current_unlock_stage": "fundamentals",
                "next_unlock_goal": "Unlock DCF",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
                "price_stage_status": "momentum_ready_short_history",
            },
            {
                "ticker": "TSLA",
                "current_unlock_stage": "peers",
                "next_unlock_goal": "Unlock Peer Relative",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
                "price_stage_status": "momentum_ready_short_history",
            },
        ]
    )

    cards = dashboard.holdings_unlock_cards(holdings, ladder, None, limit=3)
    price_card = next(card for card in cards if card["kicker"] == "AMD")
    fundamentals_card = next(card for card in cards if card["kicker"] == "NVDA")
    peer_card = next(card for card in cards if card["kicker"] == "TSLA")

    assert price_card["command"] == "make price-validate"
    assert "make price-preview" in price_card["body"].lower()
    assert "make price-apply" in price_card["body"].lower()
    assert fundamentals_card["command"] == "make imports-validate"
    assert "fundamentals import draft" in fundamentals_card["body"].lower()
    assert peer_card["command"] == "make imports-validate"
    assert "peer import draft" in peer_card["body"].lower()


def test_holdings_unlock_cards_upgrade_generic_staged_price_note_to_explicit_follow_through():
    holdings = pd.DataFrame([{"Ticker": "AMD", "PrimaryPurpose": "Core Compounder"}])
    ladder = pd.DataFrame(
        [
            {
                "ticker": "AMD",
                "current_unlock_stage": "prices",
                "next_unlock_goal": "Unlock Monthly Picks",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/prices.csv",
                "price_stage_status": "partial_price_history",
            }
        ]
    )

    cards = dashboard.holdings_unlock_cards(holdings, ladder, None, limit=1)

    assert cards[0]["command"] == "make price-validate"
    assert "make price-preview" in cards[0]["body"].lower()
    assert "make price-apply" in cards[0]["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in cards[0]["body"].lower()


def test_holdings_deep_research_cards_surface_sec_and_peer_blockers():
    holdings = pd.DataFrame(
        [
            {"Ticker": "NVDA", "PrimaryPurpose": "Momentum Leader"},
            {"Ticker": "TSLA", "PrimaryPurpose": "Speculative Optionality"},
        ]
    )
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI",
                "recommended_action": "Stage or add richer verified fundamentals to close the remaining DCF input gaps.",
                "example_command": "make sec-stage TICKERS=NVDA",
                "price_history_days": 25,
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "Add manually researched peer mappings for this ticker and keep peer-relative comparison transparent.",
                "example_command": "make templates",
            }
        ]
    )

    cards = dashboard.holdings_deep_research_cards(holdings, sec_queue, peer_queue, limit=4)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert any(card["title"] == "Unlock DCF" for card in cards)
    assert any(card["title"] == "Unlock Peer Relative" for card in cards)
    assert "nvda" in rendered
    assert "tsla" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_holdings_deep_research_cards_use_lane_front_doors_when_commands_are_missing():
    holdings = pd.DataFrame(
        [
            {"Ticker": "NVDA", "PrimaryPurpose": "Momentum Leader"},
            {"Ticker": "TSLA", "PrimaryPurpose": "Speculative Optionality"},
        ]
    )
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI",
                "recommended_action": "Stage or add richer verified fundamentals to close the remaining DCF input gaps.",
                "focus_command": "",
                "example_command": "",
                "price_history_days": 25,
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "Add manually researched peer mappings for this ticker and keep peer-relative comparison transparent.",
                "focus_command": "",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.holdings_deep_research_cards(holdings, sec_queue, peer_queue, limit=4)
    dcf_card = next(card for card in cards if card["title"] == "Unlock DCF")
    peer_card = next(card for card in cards if card["title"] == "Unlock Peer Relative")

    assert dcf_card["command"] == "make focus-fundamentals TICKER=NVDA"
    assert peer_card["command"] == "make focus-peers TICKER=TSLA"


def test_holdings_deep_research_cards_handle_missing_inputs_gracefully():
    cards = dashboard.holdings_deep_research_cards(None, None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "no holdings deep-research board yet" in rendered
    assert cards[0]["command"] == "make onboarding"
    assert "make onboarding" in rendered
    assert "buy" not in rendered


def test_holdings_deep_research_cards_fall_back_to_onboarding_when_queues_are_missing():
    holdings = pd.DataFrame(
        [
            {"Ticker": "NVDA", "PrimaryPurpose": "Momentum Leader"},
            {"Ticker": "TSLA", "PrimaryPurpose": "Speculative Optionality"},
        ]
    )

    cards = dashboard.holdings_deep_research_cards(holdings, None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 1
    assert cards[0]["title"] == "No holdings DCF / peer queue yet"
    assert cards[0]["command"] == "make onboarding"
    assert "make onboarding" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_holdings_deep_research_cards_use_review_fallback_when_action_is_missing():
    holdings = pd.DataFrame([{"Ticker": "AMD", "PrimaryPurpose": "Core Compounder"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "theme": "Semis",
                "price_history_days": 84,
                "recommended_action": "",
            }
        ]
    )

    cards = dashboard.holdings_deep_research_cards(holdings, sec_queue, None, limit=1)

    assert cards[0]["kicker"] == "AMD"
    assert "review fundamentals path." in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_holdings_deep_research_cards_use_runbook_fallback_when_action_is_missing():
    holdings = pd.DataFrame([{"Ticker": "AMD", "PrimaryPurpose": "Core Compounder"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "theme": "Semis",
                "price_history_days": 84,
                "recommended_action": "",
                "focus_command": "make runbook-fundamentals",
            }
        ]
    )

    cards = dashboard.holdings_deep_research_cards(holdings, sec_queue, None, limit=1)

    assert cards[0]["kicker"] == "AMD"
    assert cards[0]["command"] == "make runbook-fundamentals"
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_holdings_deep_research_cards_use_peer_review_fallback_when_action_is_missing():
    holdings = pd.DataFrame([{"Ticker": "TSLA", "PrimaryPurpose": "Speculative Optionality"}])
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "",
            }
        ]
    )

    cards = dashboard.holdings_deep_research_cards(holdings, None, peer_queue, limit=1)

    assert cards[0]["kicker"] == "TSLA"
    assert "review peer path." in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_holdings_deep_research_cards_use_peer_runbook_fallback_when_action_is_missing():
    holdings = pd.DataFrame([{"Ticker": "TSLA", "PrimaryPurpose": "Speculative Optionality"}])
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "",
                "focus_command": "make runbook-peers",
            }
        ]
    )

    cards = dashboard.holdings_deep_research_cards(holdings, None, peer_queue, limit=1)

    assert cards[0]["kicker"] == "TSLA"
    assert cards[0]["command"] == "make runbook-peers"
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_holdings_deep_research_cards_keep_staged_import_front_doors_when_commands_are_missing():
    holdings = pd.DataFrame(
        [
            {"Ticker": "NVDA", "PrimaryPurpose": "Momentum Leader"},
            {"Ticker": "TSLA", "PrimaryPurpose": "Speculative Optionality"},
        ]
    )
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
                "price_history_days": 25,
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )

    cards = dashboard.holdings_deep_research_cards(holdings, sec_queue, peer_queue, limit=4)
    fundamentals_card = next(card for card in cards if card["kicker"] == "NVDA")
    peer_card = next(card for card in cards if card["kicker"] == "TSLA")

    assert fundamentals_card["title"] == "Review fundamentals import draft"
    assert fundamentals_card["command"] == "make imports-validate"
    assert "fundamentals import draft" in fundamentals_card["body"].lower()
    assert peer_card["title"] == "Review peer import draft"


def test_holdings_deep_research_cards_upgrade_generic_staged_notes_to_explicit_follow_through():
    holdings = pd.DataFrame(
        [
            {"Ticker": "NVDA", "PrimaryPurpose": "Momentum Leader"},
            {"Ticker": "TSLA", "PrimaryPurpose": "Speculative Optionality"},
        ]
    )
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
                "price_history_days": 25,
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )

    cards = dashboard.holdings_deep_research_cards(holdings, sec_queue, peer_queue, limit=4)
    fundamentals_card = next(card for card in cards if card["kicker"] == "NVDA")
    peer_card = next(card for card in cards if card["kicker"] == "TSLA")

    assert "make imports-preview" in fundamentals_card["body"].lower()
    assert "make imports-apply" in fundamentals_card["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in fundamentals_card["body"].lower()
    assert "make imports-preview" in peer_card["body"].lower()
    assert "make imports-apply" in peer_card["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in peer_card["body"].lower()
    assert peer_card["command"] == "make imports-validate"
    assert "peer import draft ready" in peer_card["body"].lower()


def test_holdings_unlock_cards_handle_missing_inputs_gracefully():
    cards = dashboard.holdings_unlock_cards(None, None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "no holdings unlock board yet" in rendered
    assert cards[0]["command"] == "make onboarding"
    assert "make onboarding" in rendered
    assert "buy" not in rendered


def test_theme_unlock_cards_surface_grouped_theme_priorities():
    summary = pd.DataFrame(
        [
            {
                "group_type": "theme",
                "group_name": "AI Semiconductors",
                "ticker_count": 3,
                "holdings_count": 1,
                "top_priority_stage": "prices",
                "next_unlock_goal": "Unlock Monthly Picks",
                "recommended_action": "Fill verified local price history first.",
                "focus_command": "make status",
                "example_command": "make runbook-prices",
            },
            {
                "group_type": "sector_etf",
                "group_name": "SMH",
                "ticker_count": 8,
                "holdings_count": 1,
                "top_priority_stage": "fundamentals",
                "next_unlock_goal": "Unlock DCF",
                "recommended_action": "Stage or add verified fundamentals.",
                "focus_command": "make status",
                "example_command": "make runbook-fundamentals",
            },
        ]
    )

    cards = dashboard.theme_unlock_cards(summary, limit=2)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "THEME FIRST"
    assert "ai semiconductors" in rendered
    assert "smh" in rendered
    assert "unlock monthly picks" in rendered
    assert cards[0]["command"] == "make runbook-prices"
    assert any(card.get("command") == "make runbook-fundamentals" for card in cards)
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_theme_unlock_cards_handle_missing_inputs_gracefully():
    cards = dashboard.theme_unlock_cards(None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "no theme unlock board yet" in rendered
    assert cards[0]["command"] == "make onboarding"
    assert "make onboarding" in rendered
    assert "buy" not in rendered


def test_theme_unlock_cards_fall_back_to_universe_preview_when_only_holdings_context_exists():
    summary = pd.DataFrame(
        [
            {
                "group_type": "holdings",
                "group_name": "Current Holdings",
                "ticker_count": 2,
                "holdings_count": 2,
                "top_priority_stage": "fundamentals",
                "next_unlock_goal": "Unlock DCF",
                "recommended_action": "Run make status, then follow the printed fundamentals focus or runbook path for this group.",
                "focus_command": "make status",
                "example_command": "make runbook-fundamentals",
            }
        ]
    )

    cards = dashboard.theme_unlock_cards(summary)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 1
    assert cards[0]["title"] == "No grouped theme unlocks yet"
    assert cards[0]["command"] == "make universe-preview"
    assert "make universe-preview" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_theme_unlock_cards_use_review_fallback_when_action_is_missing():
    summary = pd.DataFrame(
        [
            {
                "group_type": "theme",
                "group_name": "AI Semiconductors",
                "ticker_count": 3,
                "holdings_count": 1,
                "top_priority_stage": "peers",
                "next_unlock_goal": "Unlock Peer Relative",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.theme_unlock_cards(summary, limit=1)

    assert cards[1]["kicker"] == "AI Semiconductors"
    assert cards[1]["command"] == "make runbook-peers-broader"
    assert "local import draft workflow next" in cards[1]["body"].lower()
    assert "not available" not in cards[1]["body"].lower()


def test_theme_unlock_cards_use_runbook_fallback_when_action_is_missing():
    summary = pd.DataFrame(
        [
            {
                "group_type": "theme",
                "group_name": "AI Semiconductors",
                "ticker_count": 3,
                "holdings_count": 1,
                "top_priority_stage": "peers",
                "next_unlock_goal": "Unlock Peer Relative",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "make runbook-peers",
            }
        ]
    )

    cards = dashboard.theme_unlock_cards(summary, limit=1)

    assert cards[1]["kicker"] == "AI Semiconductors"
    assert cards[1]["command"] == "make runbook-peers"
    assert "local import draft workflow next" in cards[1]["body"].lower()


def test_theme_unlock_cards_keep_staged_import_front_doors_when_target_files_are_present():
    summary = pd.DataFrame(
        [
            {
                "group_type": "theme",
                "group_name": "AI Semiconductors",
                "ticker_count": 3,
                "holdings_count": 1,
                "top_priority_stage": "prices",
                "next_unlock_goal": "Unlock Monthly Picks",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/prices.csv",
            },
            {
                "group_type": "sector_etf",
                "group_name": "SMH",
                "ticker_count": 8,
                "holdings_count": 1,
                "top_priority_stage": "fundamentals",
                "next_unlock_goal": "Unlock DCF",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            },
            {
                "group_type": "theme",
                "group_name": "EV Leaders",
                "ticker_count": 4,
                "holdings_count": 1,
                "top_priority_stage": "peers",
                "next_unlock_goal": "Unlock Peer Relative",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            },
        ]
    )

    cards = dashboard.theme_unlock_cards(summary, limit=3)
    price_card = next(card for card in cards if card["kicker"] == "AI Semiconductors")
    fundamentals_card = next(card for card in cards if card["kicker"] == "SMH")
    peer_card = next(card for card in cards if card["kicker"] == "EV Leaders")

    assert price_card["command"] == "make price-validate"
    assert "make price-preview" in price_card["body"].lower()
    assert "make price-apply" in price_card["body"].lower()
    assert fundamentals_card["command"] == "make imports-validate"
    assert "fundamentals import draft" in fundamentals_card["body"].lower()
    assert peer_card["command"] == "make imports-validate"
    assert "peer import draft" in peer_card["body"].lower()


def test_theme_unlock_cards_upgrade_generic_staged_price_note_to_explicit_follow_through():
    summary = pd.DataFrame(
        [
            {
                "group_type": "theme",
                "group_name": "AI Semiconductors",
                "ticker_count": 3,
                "holdings_count": 1,
                "top_priority_stage": "prices",
                "next_unlock_goal": "Unlock Monthly Picks",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/prices.csv",
            }
        ]
    )

    cards = dashboard.theme_unlock_cards(summary, limit=1)

    assert cards[1]["command"] == "make price-validate"
    assert "make price-preview" in cards[1]["body"].lower()
    assert "make price-apply" in cards[1]["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in cards[1]["body"].lower()
    assert "not available" not in cards[1]["body"].lower()


def test_unlock_cards_use_stage_front_doors_when_commands_are_missing():
    holdings = pd.DataFrame(
        [
            {"Ticker": "NVDA", "PrimaryPurpose": "Momentum Leader"},
        ]
    )
    ladder = pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "current_unlock_stage": "fundamentals",
                "next_unlock_goal": "Unlock DCF",
                "recommended_action": "Stage verified fundamentals.",
                "focus_command": "",
                "example_command": "",
                "price_stage_status": "momentum_ready_short_history",
            },
        ]
    )
    holdings_summary = pd.DataFrame(
        [
            {
                "group_type": "holdings",
                "group_name": "Current Holdings",
                "ticker_count": 1,
                "holdings_count": 1,
                "top_priority_stage": "fundamentals",
                "next_unlock_goal": "Unlock DCF",
                "representative_tickers": "NVDA",
                "focus_command": "",
                "example_command": "",
            }
        ]
    )
    theme_summary = pd.DataFrame(
        [
            {
                "group_type": "theme",
                "group_name": "AI Semiconductors",
                "ticker_count": 3,
                "holdings_count": 1,
                "top_priority_stage": "peers",
                "next_unlock_goal": "Unlock Peer Relative",
                "recommended_action": "Build transparent peer context.",
                "focus_command": "",
                "example_command": "",
            }
        ]
    )

    holding_cards = dashboard.holdings_unlock_cards(holdings, ladder, holdings_summary, limit=2)
    theme_cards = dashboard.theme_unlock_cards(theme_summary, limit=2)

    assert holding_cards[0]["command"] == "make runbook-fundamentals-broader"
    assert any(card.get("command") == "make focus-fundamentals TICKER=NVDA" for card in holding_cards)
    assert theme_cards[0]["command"] == "make runbook-peers-broader"
    assert any(card.get("command") == "make runbook-peers-broader" for card in theme_cards)


def test_theme_deep_research_cards_surface_sec_and_peer_theme_blockers():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "is_holding": True,
                "recommended_action": "Stage or add richer verified fundamentals to close the remaining DCF input gaps.",
            },
            {
                "priority": 2,
                "ticker": "AMD",
                "theme": "AI Semiconductors",
                "is_holding": False,
                "recommended_action": "Run SEC import draft workflow for fundamentals so DCF assumptions can be reviewed from explicit local inputs.",
            },
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "SMH",
                "theme": "Semiconductor ETF",
                "is_holding": False,
                "recommended_action": "Add manually researched peer mappings for this ticker and keep peer-relative comparison transparent.",
            }
        ]
    )

    cards = dashboard.theme_deep_research_cards(sec_queue, peer_queue, limit=4)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert any(card["title"] == "Unlock DCF" for card in cards)
    assert any(card["title"] == "Unlock Peer Relative" for card in cards)
    assert any(card.get("command") == "make focus-fundamentals TICKER=NVDA" for card in cards)
    assert any(card.get("command") == "make focus-peers TICKER=SMH" for card in cards)
    assert "ai semiconductors" in rendered
    assert "semiconductor etf" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_theme_deep_research_cards_handle_missing_inputs_gracefully():
    cards = dashboard.theme_deep_research_cards(None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "no theme deep-research board yet" in rendered
    assert cards[0]["command"] == "make onboarding"
    assert "make onboarding" in rendered
    assert "buy" not in rendered


def test_theme_deep_research_cards_use_review_fallback_when_action_is_missing():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "theme": "Semis",
                "is_holding": False,
                "recommended_action": "",
            }
        ]
    )

    cards = dashboard.theme_deep_research_cards(sec_queue, None, limit=1)

    assert cards[0]["kicker"] == "Semis"
    assert "review fundamentals path." in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_theme_deep_research_cards_use_runbook_fallback_when_action_is_missing():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "theme": "Semis",
                "is_holding": False,
                "recommended_action": "",
                "focus_command": "make runbook-fundamentals",
            }
        ]
    )

    cards = dashboard.theme_deep_research_cards(sec_queue, None, limit=1)

    assert cards[0]["kicker"] == "Semis"
    assert cards[0]["command"] == "make runbook-fundamentals"
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_theme_deep_research_cards_use_peer_review_fallback_when_action_is_missing():
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "SMH",
                "theme": "Semiconductor ETF",
                "is_holding": False,
                "recommended_action": "",
            }
        ]
    )

    cards = dashboard.theme_deep_research_cards(None, peer_queue, limit=1)

    assert cards[0]["kicker"] == "Semiconductor ETF"
    assert "review peer path." in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_theme_deep_research_cards_use_peer_runbook_fallback_when_action_is_missing():
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "SMH",
                "theme": "Semiconductor ETF",
                "is_holding": False,
                "recommended_action": "",
                "focus_command": "make runbook-peers",
            }
        ]
    )

    cards = dashboard.theme_deep_research_cards(None, peer_queue, limit=1)

    assert cards[0]["kicker"] == "Semiconductor ETF"
    assert cards[0]["command"] == "make runbook-peers"
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_theme_deep_research_cards_keep_staged_import_front_doors_when_commands_are_missing():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "is_holding": True,
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "SMH",
                "theme": "Semiconductor ETF",
                "is_holding": False,
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )

    cards = dashboard.theme_deep_research_cards(sec_queue, peer_queue, limit=4)
    fundamentals_card = next(card for card in cards if card["kicker"] == "AI Semiconductors")
    peer_card = next(card for card in cards if card["kicker"] == "Semiconductor ETF")

    assert fundamentals_card["title"] == "Review fundamentals import draft"
    assert fundamentals_card["command"] == "make imports-validate"
    assert "fundamentals import draft" in fundamentals_card["body"].lower()
    assert "make imports-preview" in fundamentals_card["body"].lower()
    assert "make imports-apply" in fundamentals_card["body"].lower()
    assert peer_card["title"] == "Review peer import draft"
    assert peer_card["command"] == "make imports-validate"
    assert "peer import draft" in peer_card["body"].lower()
    assert "make imports-preview" in peer_card["body"].lower()
    assert "make imports-apply" in peer_card["body"].lower()


def test_theme_deep_research_cards_upgrade_generic_staged_notes_to_explicit_follow_through():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "is_holding": True,
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "SMH",
                "theme": "Semiconductor ETF",
                "is_holding": False,
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )

    cards = dashboard.theme_deep_research_cards(sec_queue, peer_queue, limit=4)
    fundamentals_card = next(card for card in cards if card["kicker"] == "AI Semiconductors")
    peer_card = next(card for card in cards if card["kicker"] == "Semiconductor ETF")

    assert "make imports-preview" in fundamentals_card["body"].lower()
    assert "make imports-apply" in fundamentals_card["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in fundamentals_card["body"].lower()
    assert "make imports-preview" in peer_card["body"].lower()
    assert "make imports-apply" in peer_card["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in peer_card["body"].lower()


def test_overview_research_pressure_cards_compare_price_fundamentals_and_peers():
    price_worklist = pd.DataFrame(
        {
            "priority": [1, 1, 2],
            "momentum_ready": [False, True, True],
            "track_record_ready": [False, False, True],
        }
    )
    sec_queue = pd.DataFrame(
        {
            "priority": [1, 2, 2],
            "is_holding": [True, False, True],
            "has_fundamentals": [False, True, False],
        }
    )
    peer_queue = pd.DataFrame(
        {
            "priority": [1, 2, 4],
            "is_holding": [True, False, True],
            "has_peer_mapping": [False, True, False],
            "peer_ready": [False, False, False],
            "focus_command": ["make focus-peers TICKER=NVDA", "make imports-validate", "make focus-peers TICKER=TSLA"],
            "target_file": ["data/imports/peers.csv", "data/imports/peers.csv", "data/imports/peers.csv"],
        }
    )
    unlock_summary = pd.DataFrame(
        {
            "group_type": ["theme", "sector_etf", "holdings"],
            "top_priority_stage": ["prices", "prices", "fundamentals"],
        }
    )

    cards = dashboard.overview_research_pressure_cards(price_worklist, sec_queue, peer_queue, unlock_summary)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["kicker"] == "PRICE PRESSURE"
    assert cards[1]["kicker"] == "DCF PRESSURE"
    assert cards[2]["kicker"] == "PEER PRESSURE"
    assert cards[0]["command"] == "make runbook-prices-broader"
    assert cards[1]["command"] == "make runbook-fundamentals-broader"
    assert cards[2]["command"] == "make runbook-peers-broader"
    assert "2 urgent price gaps" in rendered
    assert "1 holdings-first dcf unlocks" in rendered
    assert "2 missing peer mappings" in rendered
    assert "1 mapped follow-through" in rendered
    assert "1 peer import draft already need make imports-validate, make imports-preview, and make imports-apply" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_deep_research_leverage_cards_rank_sec_and_peer_lanes():
    holdings = pd.DataFrame([{"Ticker": "NVDA"}, {"Ticker": "TSLA"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "recommended_action": "Stage or add richer verified fundamentals to close the remaining DCF input gaps.",
            },
            {
                "priority": 2,
                "ticker": "AMD",
                "theme": "AI Semiconductors",
                "recommended_action": "Run SEC import draft workflow for fundamentals so DCF assumptions can be reviewed from explicit local inputs.",
            },
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "Add manually researched peer mappings for this ticker and keep peer-relative comparison transparent.",
            }
        ]
    )

    cards = dashboard.overview_deep_research_leverage_cards(holdings, sec_queue, peer_queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["kicker"] == "BEST DEEP WORK NEXT"
    assert "sec fundamentals path" in rendered
    assert "manual peer path" in rendered
    assert "ai semiconductors" in rendered
    assert "unlocks the most local research value next" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_deep_research_leverage_cards_use_lane_front_doors_when_commands_are_missing():
    holdings = pd.DataFrame([{"Ticker": "NVDA"}, {"Ticker": "TSLA"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "recommended_action": "Stage or add richer verified fundamentals to close the remaining DCF input gaps.",
                "focus_command": "",
                "example_command": "",
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "Add manually researched peer mappings for this ticker and keep peer-relative comparison transparent.",
                "focus_command": "",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.overview_deep_research_leverage_cards(holdings, sec_queue, peer_queue)
    dcf_card = next(card for card in cards if card["kicker"] == "DCF LEVERAGE")
    peer_card = next(card for card in cards if card["kicker"] == "PEER LEVERAGE")

    assert cards[0]["command"] == "make focus-fundamentals TICKER=NVDA"
    assert dcf_card["command"] == "make focus-fundamentals TICKER=NVDA"
    assert peer_card["command"] == "make focus-peers TICKER=TSLA"


def test_overview_deep_research_leverage_cards_use_staged_peer_import_title_when_queue_is_staged():
    holdings = pd.DataFrame([{"Ticker": "TSLA"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 2,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "recommended_action": "Stage or add richer verified fundamentals to close the remaining DCF input gaps.",
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "has_peer_mapping": True,
                "peer_ready": False,
                "recommended_action": "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local peer inputs.",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )

    cards = dashboard.overview_deep_research_leverage_cards(holdings, sec_queue, peer_queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "peer import draft path" in rendered
    assert "make imports-validate" in rendered
    assert "import draft" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_deep_research_leverage_cards_handle_missing_inputs_gracefully():
    cards = dashboard.overview_deep_research_leverage_cards(None, None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 1
    assert "no deep-research leverage view yet" in rendered
    assert cards[0]["command"] == "make onboarding"
    assert "make onboarding" in rendered


def test_overview_deep_research_leverage_cards_use_review_fallback_when_action_is_missing():
    holdings = pd.DataFrame([{"Ticker": "NVDA"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "recommended_action": "",
            }
        ]
    )

    cards = dashboard.overview_deep_research_leverage_cards(holdings, sec_queue, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    dcf_card = next(card for card in cards if card["kicker"] == "DCF LEVERAGE")

    assert "review fundamentals path." in dcf_card["body"].lower()
    assert "not available" not in dcf_card["body"].lower()
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_deep_research_leverage_cards_use_runbook_fallback_when_action_is_missing():
    holdings = pd.DataFrame([{"Ticker": "NVDA"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "recommended_action": "",
                "focus_command": "make runbook-fundamentals",
            }
        ]
    )

    cards = dashboard.overview_deep_research_leverage_cards(holdings, sec_queue, None)
    dcf_card = next(card for card in cards if card["kicker"] == "DCF LEVERAGE")

    assert dcf_card["command"] == "make runbook-fundamentals"
    assert "local import draft workflow next" in dcf_card["body"].lower()
    assert "not available" not in dcf_card["body"].lower()


def test_overview_deep_research_leverage_cards_use_peer_review_fallback_when_action_is_missing():
    holdings = pd.DataFrame([{"Ticker": "TSLA"}])
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "",
            }
        ]
    )

    cards = dashboard.overview_deep_research_leverage_cards(holdings, None, peer_queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    peer_card = next(card for card in cards if card["kicker"] == "PEER LEVERAGE")

    assert "review peer path." in peer_card["body"].lower()
    assert "not available" not in peer_card["body"].lower()
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_deep_research_leverage_cards_use_peer_runbook_fallback_when_action_is_missing():
    holdings = pd.DataFrame([{"Ticker": "TSLA"}])
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "",
                "focus_command": "make runbook-peers",
            }
        ]
    )

    cards = dashboard.overview_deep_research_leverage_cards(holdings, None, peer_queue)
    peer_card = next(card for card in cards if card["kicker"] == "PEER LEVERAGE")

    assert peer_card["command"] == "make runbook-peers"
    assert "ordered lane runbook" in peer_card["body"].lower()
    assert "not available" not in peer_card["body"].lower()


def test_overview_deep_research_leverage_cards_keep_staged_import_paths_when_commands_are_missing():
    holdings = pd.DataFrame([{"Ticker": "NVDA"}, {"Ticker": "TSLA"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )

    cards = dashboard.overview_deep_research_leverage_cards(holdings, sec_queue, peer_queue)
    fundamentals_card = next(card for card in cards if card["kicker"] == "DCF LEVERAGE")
    peer_card = next(card for card in cards if card["kicker"] == "PEER LEVERAGE")

    assert fundamentals_card["title"] == "Fundamentals import draft path"
    assert fundamentals_card["command"] == "make imports-validate"
    assert "fundamentals import draft" in fundamentals_card["body"].lower()
    assert "make imports-preview" in fundamentals_card["body"].lower()
    assert "make imports-apply" in fundamentals_card["body"].lower()
    assert peer_card["title"] == "Peer import draft path"
    assert peer_card["command"] == "make imports-validate"
    assert "peer import draft" in peer_card["body"].lower()
    assert "make imports-preview" in peer_card["body"].lower()
    assert "make imports-apply" in peer_card["body"].lower()


def test_overview_deep_research_leverage_cards_upgrade_generic_staged_notes_to_explicit_follow_through():
    holdings = pd.DataFrame([{"Ticker": "NVDA"}, {"Ticker": "TSLA"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )

    cards = dashboard.overview_deep_research_leverage_cards(holdings, sec_queue, peer_queue)
    fundamentals_card = next(card for card in cards if card["kicker"] == "DCF LEVERAGE")
    peer_card = next(card for card in cards if card["kicker"] == "PEER LEVERAGE")

    assert "make imports-preview" in fundamentals_card["body"].lower()
    assert "make imports-apply" in fundamentals_card["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in fundamentals_card["body"].lower()
    assert "make imports-preview" in peer_card["body"].lower()
    assert "make imports-apply" in peer_card["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in peer_card["body"].lower()


def test_overview_deep_research_priority_bridge_cards_surface_name_level_shortlist():
    holdings = pd.DataFrame([{"Ticker": "NVDA"}, {"Ticker": "TSLA"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "recommended_action": "Stage or add richer verified fundamentals to close the remaining DCF input gaps.",
            },
            {
                "priority": 2,
                "ticker": "AMD",
                "theme": "AI Semiconductors",
                "recommended_action": "Run SEC import draft workflow for fundamentals so DCF assumptions can be reviewed from explicit local inputs.",
            },
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "Add manually researched peer mappings for this ticker and keep peer-relative comparison transparent.",
            }
        ]
    )

    cards = dashboard.overview_deep_research_priority_bridge_cards(holdings, sec_queue, peer_queue, limit=3)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["kicker"] == "NVDA"
    assert "unlock dcf" in rendered
    assert "unlock peer relative" in rendered
    assert "next page: data health" in rendered
    assert cards[0]["command"] == "make focus-fundamentals TICKER=NVDA"
    assert "current holding" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_deep_research_priority_bridge_cards_keep_staged_peer_command_when_present():
    holdings = pd.DataFrame([{"Ticker": "TSLA"}])
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "has_peer_mapping": True,
                "peer_ready": False,
                "recommended_action": "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local peer inputs.",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )

    cards = dashboard.overview_deep_research_priority_bridge_cards(holdings, None, peer_queue, limit=1)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "TSLA"
    assert cards[0]["title"] == "Review peer import draft"
    assert cards[0]["command"] == "make imports-validate"
    assert "review peer import draft" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_deep_research_priority_bridge_cards_use_review_fallback_when_action_is_missing():
    holdings = pd.DataFrame([{"Ticker": "AMD"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "theme": "Semis",
                "recommended_action": "",
            }
        ]
    )

    cards = dashboard.overview_deep_research_priority_bridge_cards(holdings, sec_queue, None, limit=1)

    assert cards[0]["kicker"] == "AMD"
    assert "review fundamentals path." in cards[0]["body"].lower()
    assert cards[0]["command_reason"].lower() == "review fundamentals path."
    assert "not available" not in cards[0]["body"].lower()


def test_overview_deep_research_priority_bridge_cards_use_runbook_fallback_when_action_is_missing():
    holdings = pd.DataFrame([{"Ticker": "AMD"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "theme": "Semis",
                "recommended_action": "",
                "focus_command": "make runbook-fundamentals",
            }
        ]
    )

    cards = dashboard.overview_deep_research_priority_bridge_cards(holdings, sec_queue, None, limit=1)

    assert cards[0]["kicker"] == "AMD"
    assert cards[0]["command"] == "make runbook-fundamentals"
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "ordered lane runbook" in cards[0]["command_reason"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_deep_research_priority_bridge_cards_use_peer_review_fallback_when_action_is_missing():
    holdings = pd.DataFrame([{"Ticker": "TSLA"}])
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "",
            }
        ]
    )

    cards = dashboard.overview_deep_research_priority_bridge_cards(holdings, None, peer_queue, limit=1)

    assert cards[0]["kicker"] == "TSLA"
    assert "review peer path." in cards[0]["body"].lower()
    assert cards[0]["command_reason"].lower() == "review peer path."
    assert "not available" not in cards[0]["body"].lower()


def test_overview_deep_research_priority_bridge_cards_use_peer_runbook_fallback_when_action_is_missing():
    holdings = pd.DataFrame([{"Ticker": "TSLA"}])
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "",
                "focus_command": "make runbook-peers",
            }
        ]
    )

    cards = dashboard.overview_deep_research_priority_bridge_cards(holdings, None, peer_queue, limit=1)

    assert cards[0]["kicker"] == "TSLA"
    assert cards[0]["command"] == "make runbook-peers"
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "ordered lane runbook" in cards[0]["command_reason"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_deep_research_priority_bridge_cards_keep_staged_import_paths_when_commands_are_missing():
    holdings = pd.DataFrame([{"Ticker": "NVDA"}, {"Ticker": "TSLA"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )

    cards = dashboard.overview_deep_research_priority_bridge_cards(holdings, sec_queue, peer_queue, limit=3)
    fundamentals_card = next(card for card in cards if card["kicker"] == "NVDA")
    peer_card = next(card for card in cards if card["kicker"] == "TSLA")

    assert fundamentals_card["title"] == "Review fundamentals import draft"
    assert fundamentals_card["command"] == "make imports-validate"
    assert "fundamentals import draft" in fundamentals_card["body"].lower()
    assert "make imports-preview" in fundamentals_card["command_reason"].lower()
    assert peer_card["title"] == "Review peer import draft"
    assert peer_card["command"] == "make imports-validate"
    assert "peer import draft" in peer_card["body"].lower()


def test_overview_deep_research_priority_bridge_cards_upgrade_generic_staged_notes_to_explicit_follow_through():
    holdings = pd.DataFrame([{"Ticker": "NVDA"}, {"Ticker": "TSLA"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )

    cards = dashboard.overview_deep_research_priority_bridge_cards(holdings, sec_queue, peer_queue, limit=3)
    fundamentals_card = next(card for card in cards if card["kicker"] == "NVDA")
    peer_card = next(card for card in cards if card["kicker"] == "TSLA")

    assert "make imports-preview" in fundamentals_card["body"].lower()
    assert "make imports-apply" in fundamentals_card["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in fundamentals_card["body"].lower()
    assert "make imports-preview" in fundamentals_card["command_reason"].lower()
    assert "make imports-preview" in peer_card["body"].lower()
    assert "make imports-apply" in peer_card["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in peer_card["body"].lower()
    assert "make imports-preview" in peer_card["command_reason"].lower()
    assert "make imports-preview" in peer_card["command_reason"].lower()


def test_overview_deep_research_priority_bridge_cards_handle_missing_inputs_gracefully():
    cards = dashboard.overview_deep_research_priority_bridge_cards(None, None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 1
    assert "no deep-research shortlist yet" in rendered
    assert cards[0]["command"] == "make onboarding"
    assert "make onboarding" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_deep_research_handoff_cards_stitch_name_command_and_tab():
    holdings = pd.DataFrame([{"Ticker": "NVDA"}, {"Ticker": "TSLA"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "recommended_action": "Stage or add richer verified fundamentals to close the remaining DCF input gaps.",
                "example_command": "make sec-stage TICKERS=NVDA",
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "Add manually researched peer mappings for this ticker and keep peer-relative comparison transparent.",
                "example_command": "make templates",
            }
        ]
    )
    payload = {"recommended_next_commands": ["make onboarding", "make verify", "make dashboard"]}
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "fundamentals",
                "ticker": "NVDA",
                "title": "Stage fundamentals",
                "reason": "DCF inputs are still incomplete.",
                "recommended_action": "Run SEC import draft workflow for fundamentals, then validate and preview before applying.",
                "example_command": "make sec-stage-queue",
            }
        ]
    )

    cards = dashboard.overview_deep_research_handoff_cards(holdings, sec_queue, peer_queue, payload, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["title"] == "NVDA"
    assert cards[0]["command"] == "make sec-stage TICKERS=NVDA"
    assert "make sec-stage tickers=nvda" in rendered
    assert "stage or add richer verified fundamentals" in rendered
    assert cards[2]["title"] == "Data Health"
    assert "single-stock report" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_deep_research_handoff_cards_keep_staged_peer_reason_and_command():
    holdings = pd.DataFrame([{"Ticker": "TSLA"}])
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "has_peer_mapping": True,
                "peer_ready": False,
                "recommended_action": "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local peer inputs.",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )
    payload = {"recommended_next_commands": ["make status", "make verify", "make dashboard-smoke"]}

    cards = dashboard.overview_deep_research_handoff_cards(holdings, None, peer_queue, payload, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "TSLA"
    assert cards[0]["command"] == "make imports-validate"
    assert cards[1]["title"] == "make imports-validate"
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "make status-check top_n=5" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_deep_research_handoff_cards_keep_staged_fundamentals_reason_and_command_when_commands_are_missing():
    holdings = pd.DataFrame([{"Ticker": "NVDA"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )
    payload = {"recommended_next_commands": ["make status", "make verify", "make dashboard-smoke"]}

    cards = dashboard.overview_deep_research_handoff_cards(holdings, sec_queue, None, payload, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "NVDA"
    assert cards[0]["command"] == "make imports-validate"
    assert cards[1]["title"] == "make imports-validate"
    assert "fundamentals import draft" in cards[1]["body"].lower()
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_deep_research_handoff_cards_keep_runbook_fundamentals_reason_and_command():
    holdings = pd.DataFrame([{"Ticker": "NVDA"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "recommended_action": "",
                "focus_command": "make runbook-fundamentals",
                "example_command": "",
            }
        ]
    )
    payload = {"recommended_next_commands": ["make status", "make verify", "make dashboard-smoke"]}

    cards = dashboard.overview_deep_research_handoff_cards(holdings, sec_queue, None, payload, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "NVDA"
    assert cards[0]["command"] == "make runbook-fundamentals"
    assert cards[1]["title"] == "make runbook-fundamentals"
    assert "local import draft workflow next" in cards[1]["body"].lower()
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_deep_research_handoff_cards_keep_runbook_peer_reason_and_command():
    holdings = pd.DataFrame([{"Ticker": "TSLA"}])
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "",
                "focus_command": "make runbook-peers",
                "example_command": "",
            }
        ]
    )
    payload = {"recommended_next_commands": ["make status", "make verify", "make dashboard-smoke"]}

    cards = dashboard.overview_deep_research_handoff_cards(holdings, None, peer_queue, payload, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "TSLA"
    assert cards[0]["command"] == "make runbook-peers"
    assert cards[1]["title"] == "make runbook-peers"
    assert "local import draft workflow next" in cards[1]["body"].lower()
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_deep_research_handoff_cards_fall_back_to_safe_command():
    cards = dashboard.overview_deep_research_handoff_cards(None, None, None, None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["title"] == "No deep-research shortlist yet"
    assert cards[0]["command"] == "make onboarding"
    assert cards[1]["title"] == "make onboarding"
    assert cards[2]["title"] == "Data Health"
    assert "refresh the onboarding outputs" in rendered
    assert "sec stage and peer-mapping queues" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_ready_blocked_cards_surface_usable_and_blocked_names():
    coverage = pd.DataFrame(
        [
            {"ticker": "NVDA", "usable_for_momentum": True, "dcf_ready": True, "peer_ready": False},
            {"ticker": "TSLA", "usable_for_momentum": True, "dcf_ready": False, "peer_ready": False},
            {"ticker": "AMD", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
        ]
    )
    ladder = pd.DataFrame(
        [
            {"ticker": "NVDA", "current_unlock_stage": "peers", "next_unlock_goal": "Unlock Peer Relative"},
            {"ticker": "TSLA", "current_unlock_stage": "fundamentals", "next_unlock_goal": "Unlock DCF"},
            {"ticker": "AMD", "current_unlock_stage": "prices", "next_unlock_goal": "Unlock Monthly Picks"},
        ]
    )
    holdings = pd.DataFrame([{"Ticker": "NVDA"}, {"Ticker": "TSLA"}])

    cards = dashboard.overview_ready_blocked_cards(coverage, ladder, holdings, limit=2)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 2
    assert cards[0]["kicker"] == "READY NOW"
    assert cards[1]["kicker"] == "BLOCKED NOW"
    assert cards[0]["command"] == "make monthly"
    assert cards[1]["command"] == "make runbook-prices-broader"
    assert "nvda" in rendered
    assert "amd" in rendered
    assert "usable names" in rendered
    assert "still blocked" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_ready_blocked_cards_handle_missing_inputs_gracefully():
    cards = dashboard.overview_ready_blocked_cards(None, None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "no readiness shortlist yet" in rendered
    assert cards[0]["command"] == "make onboarding"
    assert "make onboarding" in rendered
    assert "buy" not in rendered


def test_overview_ready_blocked_cards_tolerate_ladder_without_stage_columns():
    coverage = pd.DataFrame(
        [
            {"ticker": "META", "price_ready": True, "momentum_ready": True},
            {"ticker": "AIAI", "price_ready": True, "momentum_ready": False},
            {"ticker": "APLD", "price_ready": False, "momentum_ready": False},
        ]
    )
    ladder_like = pd.DataFrame(
        [
            {"ticker": "META", "decision_bucket": "Blocked by Data"},
            {"ticker": "APLD", "decision_bucket": "Blocked by Data"},
        ]
    )
    holdings = pd.DataFrame([{"Ticker": "META"}])

    cards = dashboard.overview_ready_blocked_cards(coverage, ladder_like, holdings, limit=2)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 2
    assert cards[0]["title"] == "2 usable names"
    assert cards[0]["command"] == "make monthly"
    assert cards[1]["title"] == "1 names still blocked"
    assert cards[1]["command"] == "make runbook-prices-broader"
    assert "meta" in rendered
    assert "apld" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_best_current_name_cards_route_ready_names_to_next_page():
    coverage = pd.DataFrame(
        [
            {"ticker": "NVDA", "usable_for_momentum": True, "dcf_ready": True, "peer_ready": False},
            {"ticker": "TSLA", "usable_for_momentum": True, "dcf_ready": False, "peer_ready": False},
            {"ticker": "AMD", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
        ]
    )
    holdings = pd.DataFrame([{"Ticker": "NVDA"}])

    cards = dashboard.overview_best_current_name_cards(coverage, holdings, limit=2)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 2
    assert cards[0]["kicker"] == "NVDA"
    assert cards[0]["title"] == "Single-Stock Report"
    assert cards[0]["command"] == "make stock-report-md TICKER=NVDA"
    assert cards[1]["title"] == "Monthly Picks"
    assert cards[1]["command"] == "make monthly"
    assert "holding" in rendered
    assert "deeper single-name review" in rendered
    assert "make verify" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_best_current_name_cards_handle_missing_inputs_gracefully():
    cards = dashboard.overview_best_current_name_cards(None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "READY NAME STATUS"
    assert "no current ready names yet" in rendered
    assert cards[0]["command"] == "make onboarding"
    assert "make onboarding" in rendered
    assert "buy" not in rendered


def test_overview_best_current_name_cards_handle_metadata_only_coverage_gracefully():
    coverage = pd.DataFrame(
        [
            {"ticker": "NVDA", "name": "Nvidia", "asset_type": "company", "metadata_ready": True},
            {"ticker": "QQQ", "name": "Nasdaq 100 ETF", "asset_type": "etf", "metadata_ready": True},
        ]
    )

    cards = dashboard.overview_best_current_name_cards(coverage, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 1
    assert cards[0]["title"] == "No current ready names yet"
    assert cards[0]["command"] == "make onboarding"
    assert "refresh local coverage" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_best_current_name_cards_support_price_coverage_schema():
    coverage = pd.DataFrame(
        [
            {"ticker": "AIAI", "price_ready": True, "momentum_ready": False},
            {"ticker": "NVDA", "price_ready": True, "momentum_ready": True},
            {"ticker": "APLD", "price_ready": False, "momentum_ready": False},
        ]
    )
    holdings = pd.DataFrame([{"Ticker": "NVDA"}])

    cards = dashboard.overview_best_current_name_cards(coverage, holdings, limit=2)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["NVDA", "AIAI"]
    assert cards[0]["title"] == "Monthly Picks"
    assert cards[0]["command"] == "make monthly"
    assert "current momentum-style research" in rendered
    assert "no current ready names yet" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_best_current_name_cards_use_actionable_empty_state_when_no_names_are_ready():
    coverage = pd.DataFrame(
        [
            {"ticker": "TSLA", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
            {"ticker": "AMD", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
        ]
    )

    cards = dashboard.overview_best_current_name_cards(coverage, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 1
    assert cards[0]["kicker"] == "READY NAME STATUS"
    assert cards[0]["title"] == "No current ready names yet"
    assert cards[0]["command"] == "make onboarding"
    assert "refresh local coverage" in rendered
    assert "price-ready names" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_ready_name_handoff_cards_route_stock_report_names_to_ticker_report_then_tab():
    coverage = pd.DataFrame(
        [
            {"ticker": "NVDA", "usable_for_momentum": True, "dcf_ready": True, "peer_ready": False},
            {"ticker": "TSLA", "usable_for_momentum": True, "dcf_ready": False, "peer_ready": False},
        ]
    )
    holdings = pd.DataFrame([{"Ticker": "NVDA"}])
    payload = {"recommended_next_commands": ["make onboarding", "make verify", "make dashboard"]}
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "NVDA",
                "title": "Repair prices",
                "reason": "Need more local rows.",
                "example_command": "make price-worklist",
            }
        ]
    )

    cards = dashboard.overview_ready_name_handoff_cards(coverage, holdings, payload, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["title"] == "NVDA"
    assert cards[0]["command"] == "make stock-report-md TICKER=NVDA"
    assert cards[1]["title"] == "make stock-report-md TICKER=NVDA"
    assert cards[2]["title"] == "Single-Stock Report"
    assert "strongest currently usable local name" in rendered
    assert "ticker-targeted stock report" in rendered
    assert "make verify" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_ready_name_handoff_cards_route_partial_names_to_monthly_picks():
    coverage = pd.DataFrame(
        [
            {"ticker": "TSLA", "usable_for_momentum": True, "dcf_ready": False, "peer_ready": False},
            {"ticker": "AMD", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
        ]
    )
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "high",
                "action_type": "fundamentals",
                "ticker": "TSLA",
                "title": "Refresh onboarding",
                "reason": "Need richer local context.",
                "example_command": "make onboarding",
            }
        ]
    )

    cards = dashboard.overview_ready_name_handoff_cards(coverage, None, None, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["title"] == "TSLA"
    assert cards[0]["command"] == "make monthly"
    assert cards[1]["title"] == "make monthly"
    assert cards[2]["title"] == "Monthly Picks"
    assert "monthly picks" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_ready_name_handoff_cards_use_monthly_front_door_without_queue_guidance():
    coverage = pd.DataFrame(
        [
            {"ticker": "TSLA", "usable_for_momentum": True, "dcf_ready": False, "peer_ready": False},
            {"ticker": "AMD", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
        ]
    )

    cards = dashboard.overview_ready_name_handoff_cards(coverage, None, None, None)

    assert cards[0]["title"] == "TSLA"
    assert cards[0]["command"] == "make monthly"
    assert cards[1]["title"] == "make monthly"
    assert cards[2]["title"] == "Monthly Picks"


def test_overview_ready_name_handoff_cards_handle_missing_inputs_gracefully():
    cards = dashboard.overview_ready_name_handoff_cards(None, None, None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["kicker"] == "READY NAME"
    assert cards[0]["title"] == "No current ready names yet"
    assert cards[1]["title"] == "make onboarding"
    assert cards[2]["title"] == "Data Health"
    assert "no locally ready name yet" in cards[0]["body"].lower()
    assert "clear blockers before treating any name as ready" in cards[0]["body"].lower()
    assert "next read matches the current local workflow state" in cards[2]["body"].lower()
    assert "for no current ready names yet" not in cards[2]["body"].lower()
    assert "refresh local coverage and onboarding outputs" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_ready_name_handoff_cards_use_runbook_fallback_when_no_ready_name_exists():
    coverage = pd.DataFrame(
        [
            {"ticker": "TSLA", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
            {"ticker": "AMD", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
        ]
    )
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Open peer runbook",
                "Command": "make runbook-peers",
                "Reason": "",
            }
        ]
    }

    cards = dashboard.overview_ready_name_handoff_cards(coverage, None, payload, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "No current ready names yet"
    assert cards[1]["title"] == "make onboarding"
    assert cards[2]["title"] == "Data Health"
    assert "no locally ready name yet" in cards[0]["body"].lower()
    assert "clear blockers before treating any name as ready" in cards[0]["body"].lower()
    assert "refresh local coverage and onboarding outputs" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_current_top_surfaces_cards_compose_ready_blocked_command_and_page():
    coverage = pd.DataFrame(
        [
            {"ticker": "NVDA", "usable_for_momentum": True, "dcf_ready": True, "peer_ready": False},
            {"ticker": "TSLA", "usable_for_momentum": True, "dcf_ready": False, "peer_ready": False},
        ]
    )
    holdings = pd.DataFrame([{"Ticker": "NVDA"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "theme": "AI Semiconductors",
                "recommended_action": "Stage or add richer verified fundamentals to close the remaining DCF input gaps.",
                "example_command": "make sec-stage TICKERS=NVDA",
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "recommended_action": "Add manually researched peer mappings for this ticker and keep peer-relative comparison transparent.",
                "example_command": "make templates",
            }
        ]
    )
    payload = {"recommended_next_commands": ["make onboarding", "make verify", "make dashboard"]}
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "NVDA",
                "title": "Repair prices",
                "reason": "NVDA update failed during remote refresh.",
                "recommended_action": "Normalize verified downloaded OHLCV rows, then run make price-validate, make price-preview, and make price-apply.",
                "example_command": "make price-worklist",
            }
        ]
    )

    cards = dashboard.overview_current_top_surfaces_cards(coverage, holdings, sec_queue, peer_queue, payload, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 4
    assert cards[0]["title"] == "NVDA"
    assert cards[0]["command"] == "make stock-report-md TICKER=NVDA"
    assert cards[1]["title"] == "NVDA"
    assert cards[1]["command"] == "make sec-stage TICKERS=NVDA"
    assert cards[2]["title"] == "make stock-report-md TICKER=NVDA"
    assert cards[3]["title"] == "Single-Stock Report"
    assert "normalize verified downloaded ohlcv rows" in rendered
    assert "best currently usable local name" in rendered
    assert "next page" in rendered
    assert "best next page" in rendered
    assert "top deeper-research blocker" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_current_top_surfaces_cards_handle_missing_inputs_gracefully():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "AIAI",
                "title": "Repair prices",
                "reason": "Only 9 verified local price rows are present.",
                "example_command": "make focus-price TICKER=AIAI",
            }
        ]
    )

    cards = dashboard.overview_current_top_surfaces_cards(None, None, None, None, None, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 4
    assert cards[0]["title"] == "No current ready names yet"
    assert cards[0]["command"] == "make onboarding"
    assert cards[1]["title"] == "No deep-research shortlist yet"
    assert cards[1]["command"] == "make onboarding"
    assert cards[2]["title"] == "make focus-price TICKER=AIAI"
    assert cards[3]["title"] == "Data Health"
    assert "no locally ready name yet" in cards[0]["body"].lower()
    assert "no deep-research shortlist yet" in cards[1]["body"].lower()
    assert "refresh the sec stage and peer-mapping queues" in cards[1]["body"].lower()
    assert "highest-leverage blocker" in cards[0]["body"].lower()
    assert "next read matches the current local workflow state" in cards[3]["body"].lower()
    assert "for no current ready names yet" not in cards[3]["body"].lower()
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_current_top_surfaces_cards_use_monthly_front_door_for_monthly_page():
    coverage = pd.DataFrame(
        [
            {"ticker": "TSLA", "usable_for_momentum": True, "dcf_ready": False, "peer_ready": False},
            {"ticker": "AMD", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
        ]
    )
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "high",
                "action_type": "fundamentals",
                "ticker": "TSLA",
                "title": "Refresh onboarding",
                "reason": "Need richer local context.",
                "example_command": "make onboarding",
            }
        ]
    )

    cards = dashboard.overview_current_top_surfaces_cards(coverage, None, None, None, None, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "TSLA"
    assert cards[0]["command"] == "make monthly"
    assert cards[2]["title"] == "make monthly"
    assert cards[3]["title"] == "Monthly Picks"
    assert "make monthly" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_current_top_surfaces_cards_use_monthly_front_door_without_queue_guidance():
    coverage = pd.DataFrame(
        [
            {"ticker": "TSLA", "usable_for_momentum": True, "dcf_ready": False, "peer_ready": False},
            {"ticker": "AMD", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
        ]
    )

    cards = dashboard.overview_current_top_surfaces_cards(coverage, None, None, None, None, None)

    assert cards[0]["title"] == "TSLA"
    assert cards[0]["command"] == "make monthly"
    assert cards[2]["title"] == "make monthly"
    assert cards[3]["title"] == "Monthly Picks"


def test_overview_current_top_surfaces_cards_prefer_staged_peer_handoff_reason():
    coverage = pd.DataFrame(
        [
            {"ticker": "NVDA", "usable_for_momentum": True, "dcf_ready": True, "peer_ready": False},
            {"ticker": "TSLA", "usable_for_momentum": True, "dcf_ready": False, "peer_ready": False},
        ]
    )
    holdings = pd.DataFrame([{"Ticker": "NVDA"}, {"Ticker": "TSLA"}])
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "theme": "EV",
                "has_peer_mapping": True,
                "peer_ready": False,
                "recommended_action": "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local peer inputs.",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Refresh local snapshot",
                "Command": "make status",
                "Reason": "Repo-native next step from the current read-only project status snapshot.",
            }
        ]
    }

    cards = dashboard.overview_current_top_surfaces_cards(coverage, holdings, None, peer_queue, payload, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[2]["title"] == "make stock-report-md TICKER=NVDA"
    assert cards[1]["command"] == "make imports-validate"
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "make status-check top_n=5" in rendered


def test_overview_current_top_surfaces_cards_prefer_ready_name_reason_without_queue_guidance():
    coverage = pd.DataFrame(
        [
            {"ticker": "NVDA", "usable_for_momentum": True, "dcf_ready": True, "peer_ready": False},
            {"ticker": "AMD", "usable_for_momentum": True, "dcf_ready": False, "peer_ready": False},
        ]
    )
    holdings = pd.DataFrame([{"Ticker": "NVDA"}, {"Ticker": "AMD"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "theme": "Semiconductors",
                "recommended_action": "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local fundamentals.",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Refresh local snapshot",
                "Command": "make status",
                "Reason": "Repo-native next step from the current read-only project status snapshot.",
            }
        ]
    }

    cards = dashboard.overview_current_top_surfaces_cards(coverage, holdings, sec_queue, None, payload, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[2]["title"] == "make stock-report-md TICKER=NVDA"
    assert cards[0]["command"] == "make stock-report-md TICKER=NVDA"
    assert "ticker-targeted stock report" in cards[2]["body"].lower()
    assert "single-stock report" in cards[2]["body"].lower()
    assert "make imports-apply" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_current_top_surfaces_cards_keep_staged_fundamentals_context_in_blocked_and_tab_cards():
    coverage = pd.DataFrame(
        [
            {"ticker": "NVDA", "usable_for_momentum": True, "dcf_ready": True, "peer_ready": False},
            {"ticker": "AMD", "usable_for_momentum": True, "dcf_ready": False, "peer_ready": False},
        ]
    )
    holdings = pd.DataFrame([{"Ticker": "NVDA"}, {"Ticker": "AMD"}])
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "theme": "Semiconductors",
                "recommended_action": "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local fundamentals.",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Refresh local snapshot",
                "Command": "make status",
                "Reason": "Repo-native next step from the current read-only project status snapshot.",
            }
        ]
    }

    cards = dashboard.overview_current_top_surfaces_cards(coverage, holdings, sec_queue, None, payload, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[1]["title"] == "AMD"
    assert cards[1]["command"] == "make imports-validate"
    assert "review fundamentals import draft" in cards[1]["body"].lower()
    assert "make imports-apply" in cards[1]["body"].lower()
    assert "make status-check top_n=5" in rendered
    assert cards[3]["title"] == "Single-Stock Report"
    assert "open single-stock report after the command step" in cards[3]["body"].lower()
    assert "nvda" in cards[3]["body"].lower()
    assert "live local" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_current_top_surfaces_cards_use_runbook_fallback_when_no_ready_name_exists():
    coverage = pd.DataFrame(
        [
            {"ticker": "TSLA", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
            {"ticker": "AMD", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
        ]
    )
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Open peer runbook",
                "Command": "make runbook-peers",
                "Reason": "",
            }
        ]
    }

    cards = dashboard.overview_current_top_surfaces_cards(coverage, None, None, None, payload, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "No current ready names yet"
    assert cards[0]["command"] == "make onboarding"
    assert cards[1]["command"] == "make runbook-peers"
    assert cards[2]["title"] == "make runbook-peers"
    assert cards[3]["title"] == "Data Health"
    assert "ordered lane runbook" in rendered
    assert "local import draft workflow" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_market_context_cards_surface_local_theme_strength():
    market_direction = pd.DataFrame(
        [
            {
                "Theme": "AI Semiconductors",
                "ETF": "SMH",
                "ThemeStatus": "Strong Rotation",
                "Return1M": 0.14,
                "RelativeReturnVsSPY": 0.09,
                "RelativeReturnVsQQQ": 0.04,
            },
            {
                "Theme": "Platforms",
                "ETF": "QQQ",
                "ThemeStatus": "Early Rotation",
                "Return1M": 0.08,
                "RelativeReturnVsSPY": 0.03,
                "RelativeReturnVsQQQ": 0.01,
            },
        ]
    )

    cards = dashboard.overview_market_context_cards(market_direction, limit=2)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "MARKET CONTEXT"
    assert cards[0]["command"] == "make pipeline"
    assert cards[1]["command"] == "make pipeline"
    assert "strong rotation" in rendered
    assert "ai semiconductors" in rendered
    assert "vs spy 9.0%" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_market_context_cards_handle_missing_inputs_gracefully():
    cards = dashboard.overview_market_context_cards(None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "no local market direction context yet" in rendered
    assert cards[0]["command"] == "make pipeline"
    assert "make pipeline" in rendered
    assert "buy" not in rendered


def test_overview_market_context_cards_keep_pipeline_visible_when_theme_rows_are_unusable():
    market_direction = pd.DataFrame(
        [
            {
                "Theme": "AI Semiconductors",
                "ETF": "SMH",
                "ThemeStatus": "Strong Rotation",
                "Return1M": None,
                "RelativeReturnVsSPY": None,
                "RelativeReturnVsQQQ": None,
            }
        ]
    )

    cards = dashboard.overview_market_context_cards(market_direction)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Insufficient local theme performance"
    assert cards[0]["command"] == "make pipeline"
    assert "make pipeline" in rendered


def test_overview_benchmark_pressure_cards_surface_price_gap_and_spy_context():
    market_direction = pd.DataFrame(
        [
            {
                "Theme": "AI Semiconductors",
                "RelativeReturnVsSPY": 0.09,
            }
        ]
    )
    price_status = pd.DataFrame({"status": ["parse_error", "fetched", "source_unavailable"]})
    payload = {"summary": {"tickers_total": 12, "tickers_with_prices": 3}}

    cards = dashboard.overview_benchmark_pressure_cards(market_direction, price_status, payload)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 2
    assert cards[0]["command"] == "make runbook-prices-broader"
    assert cards[1]["command"] == "make pipeline"
    assert "missing local prices" in rendered
    assert "9/12" in rendered
    assert "ai semiconductors" in rendered
    assert "9.0%" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_benchmark_pressure_cards_keep_price_status_visible_when_prices_are_present():
    market_direction = pd.DataFrame(
        [
            {
                "Theme": "AI Semiconductors",
                "RelativeReturnVsSPY": 0.09,
            }
        ]
    )
    price_status = pd.DataFrame({"status": ["fetched", "fetched"]})
    payload = {"summary": {"tickers_total": 12, "tickers_with_prices": 12}}

    cards = dashboard.overview_benchmark_pressure_cards(market_direction, price_status, payload)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Local prices present"
    assert cards[0]["command"] == "make price-status TOP_N=10"
    assert cards[1]["command"] == "make pipeline"
    assert "make price-status top_n=10" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_benchmark_pressure_cards_handle_missing_inputs_gracefully():
    cards = dashboard.overview_benchmark_pressure_cards(None, None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "local prices present" in rendered or "ticker coverage is not available yet" in rendered
    assert cards[0]["command"] == "make runbook-prices-broader"
    assert cards[1]["command"] == "make pipeline"
    assert "make runbook-prices-broader" in rendered
    assert "make pipeline" in rendered
    assert "buy" not in rendered


def test_onboarding_notice_copy_uses_onboarding_front_door_for_generated_artifacts():
    bundle_body, bundle_command = dashboard.onboarding_notice_copy("command_bundles")
    price_body, price_command = dashboard.onboarding_notice_copy("price_worklist")
    unlock_body, unlock_command = dashboard.onboarding_notice_copy("unlock_priority_summary")

    assert bundle_command == "make onboarding"
    assert "generate holdings-first local command bundles" in bundle_body.lower()
    assert price_command == "make onboarding"
    assert "safe manual-import path" in price_body.lower()
    assert unlock_command == "make onboarding"
    assert "grouped unlock priorities by holdings, theme, and sector etf" in unlock_body.lower()


def test_artifact_notice_copy_uses_narrow_front_doors_for_specific_artifacts():
    action_body, action_command = dashboard.artifact_notice_copy("action_queue")
    health_body, health_command = dashboard.artifact_notice_copy("research_health")
    sources_body, sources_command = dashboard.artifact_notice_copy("data_source_status")

    assert action_command == "make action-queue"
    assert "research action queue" in action_body.lower()
    assert health_command == "make research-health"
    assert "research health outputs are not available yet" in health_body.lower()
    assert sources_command == "make data-sources"
    assert "local source registry" in sources_body.lower()


def test_overview_next_command_cards_prioritize_project_status_commands():
    payload = {
        "recommended_next_commands": ["make onboarding", "make verify", "make dashboard"],
    }
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "NVDA",
                "title": "Repair prices",
                "reason": "Need more local rows.",
                "example_command": "make price-worklist",
            }
        ]
    )

    cards = dashboard.overview_next_command_cards(payload, queue, limit=3)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["title"] == "make status-check TOP_N=5"
    assert "make verify" in rendered
    assert "make dashboard-smoke" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_next_command_cards_normalize_legacy_dashboard_command_rows():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Refresh local snapshot",
                "Command": "make dashboard",
                "Reason": "Open the dashboard after refreshing the local operator outputs.",
            }
        ]
    }

    cards = dashboard.overview_next_command_cards(payload, None, limit=1)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "make dashboard-smoke"
    assert "dashboard-smoke" in rendered
    assert "smoke-check" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_next_command_cards_use_structured_project_status_rows():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Fix top prices blocker (NVDA)",
                "Command": "make focus-price TICKER=NVDA",
                "Reason": "Short local price history still blocks downstream work.",
            },
            {
                "Step": "Run Price Coverage Bundle (Broader Queue)",
                "Command": "make runbook-prices-broader",
                "Reason": "Advance broader local price coverage next.",
            },
            {
                "Step": "Deterministic verification",
                "Command": "make verify",
                "Reason": "Confirm local outputs still pass.",
            },
        ]
    }

    cards = dashboard.overview_next_command_cards(payload, None, limit=3)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "make focus-price TICKER=NVDA"
    assert cards[0]["kicker"] == "Fix top prices blocker (NVDA)"
    assert cards[1]["title"] == "make runbook-prices-broader"
    assert "short local price history" in rendered
    assert "advance broader local price coverage" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_next_command_cards_use_command_family_fallback_when_reason_is_missing():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Fix top peers blocker (TSLA)",
                "Command": "make focus-peers TICKER=TSLA",
                "Reason": "",
            }
        ]
    }

    cards = dashboard.overview_next_command_cards(payload, None, limit=1)

    assert cards[0]["title"] == "make focus-peers TICKER=TSLA"
    assert "single-name shortcut" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_next_command_cards_use_bundle_and_import_fallbacks_when_reasons_are_missing():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Review fundamentals import draft",
                "Command": "make imports-validate",
                "Reason": "",
            },
            {
                "Step": "Run highest-leverage price bundle",
                "Command": "make bundle-prices",
                "Reason": "",
            },
        ]
    }

    cards = dashboard.overview_next_command_cards(payload, None, limit=2)

    assert cards[0]["title"] == "make imports-validate"
    assert "staged flow" in [badge.lower() for badge in cards[0]["badges"]]
    assert "make imports-preview" in cards[0]["body"].lower()
    assert "make imports-apply" in cards[0]["body"].lower()
    assert cards[1]["title"] == "make bundle-prices"
    assert "bundle first" in [badge.lower() for badge in cards[1]["badges"]]
    assert "highest-leverage local bundle first" in cards[1]["body"].lower()
    assert "not available" not in cards[1]["body"].lower()


def test_overview_next_command_cards_keep_staged_follow_through_visible_when_reasons_are_generic():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Review fundamentals import draft",
                "Command": "make imports-validate",
                "Reason": "Use local import draft workflows if the free refresh fails.",
            },
            {
                "Step": "Advance price import draft",
                "Command": "make price-validate",
                "Reason": "Use local import draft workflows if the free refresh fails.",
            },
        ]
    }

    cards = dashboard.overview_next_command_cards(payload, None, limit=2)

    assert cards[0]["title"] == "make imports-validate"
    assert "make imports-preview" in cards[0]["body"].lower()
    assert "make imports-apply" in cards[0]["body"].lower()
    assert cards[1]["title"] == "make price-validate"
    assert "make price-preview" in cards[1]["body"].lower()
    assert "make price-apply" in cards[1]["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in " ".join(card["body"] for card in cards).lower()


def test_overview_next_command_cards_use_runbook_fallback_when_reason_is_missing():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Run broader peer workflow",
                "Command": "make runbook-peers-broader",
                "Reason": "",
            }
        ]
    }

    cards = dashboard.overview_next_command_cards(payload, None, limit=1)

    assert cards[0]["title"] == "make runbook-peers-broader"
    assert "runbook" in [badge.lower() for badge in cards[0]["badges"]]
    assert "use the ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_next_command_cards_fall_back_to_action_queue():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "NVDA",
                "title": "Repair prices",
                "reason": "NVDA update failed during remote refresh.",
                "recommended_action": "Normalize verified downloaded OHLCV rows, then run make price-validate, make price-preview, and make price-apply.",
                "example_command": "make price-worklist",
            }
        ]
    )

    cards = dashboard.overview_next_command_cards(None, queue, limit=2)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "make price-worklist" in rendered
    assert cards[0]["title"] == "make price-worklist"
    assert "normalize verified downloaded ohlcv rows" in rendered
    assert "buy" not in rendered


def test_overview_next_command_cards_use_onboarding_front_door_without_guidance():
    cards = dashboard.overview_next_command_cards(None, None, limit=1)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "make onboarding"
    assert cards[0]["command"] == "make onboarding"
    assert "refresh local coverage, onboarding outputs, and operator guidance" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_workflow_path_cards_use_action_queue_then_verify_then_dashboard():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "NVDA",
                "title": "Repair prices",
                "reason": "Need more local rows.",
                "example_command": "make price-worklist",
            }
        ]
    )
    payload = {"recommended_next_commands": ["make onboarding", "make verify", "make dashboard-smoke"]}

    cards = dashboard.overview_workflow_path_cards(payload, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["title"] == "make price-worklist"
    assert cards[1]["title"] == "make verify"
    assert cards[2]["title"] == "make dashboard-smoke"
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_workflow_path_cards_use_runbook_fallback_when_action_queue_drives_step_one():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "peers",
                "ticker": "TSLA",
                "title": "Open peer runbook",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make runbook-peers",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.overview_workflow_path_cards(None, queue)

    assert cards[0]["title"] == "make runbook-peers"
    assert "staged flow" in [badge.lower() for badge in cards[0]["badges"]]
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_workflow_path_cards_use_imports_and_bundle_fallbacks_when_action_queue_drives_step_one():
    imports_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "fundamentals",
                "ticker": "NVDA",
                "title": "Review fundamentals import draft",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make imports-validate",
                "example_command": "",
            }
        ]
    )
    bundle_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "peers",
                "ticker": "",
                "title": "Run peer bundle",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make bundle-peers",
                "example_command": "",
            }
        ]
    )

    imports_cards = dashboard.overview_workflow_path_cards(None, imports_queue)
    bundle_cards = dashboard.overview_workflow_path_cards(None, bundle_queue)

    assert imports_cards[0]["title"] == "make imports-validate"
    assert "staged flow" in [badge.lower() for badge in imports_cards[0]["badges"]]
    assert "make imports-preview" in imports_cards[0]["body"].lower()
    assert "make imports-apply" in imports_cards[0]["body"].lower()
    assert bundle_cards[0]["title"] == "make bundle-peers"
    assert "bundle first" in [badge.lower() for badge in bundle_cards[0]["badges"]]
    assert "highest-leverage local bundle first" in bundle_cards[0]["body"].lower()
    assert "not available" not in " ".join(str(value) for card in imports_cards + bundle_cards for value in card.values()).lower()


def test_overview_workflow_path_cards_use_explicit_import_follow_through_when_imports_drive_step_one_without_queue():
    payload = {"recommended_next_commands": ["make imports-validate", "make verify", "make dashboard-smoke"]}

    cards = dashboard.overview_workflow_path_cards(payload, None)

    assert cards[0]["title"] == "make imports-validate"
    assert "staged flow" in [badge.lower() for badge in cards[0]["badges"]]
    assert "make imports-preview" in cards[0]["body"].lower()
    assert "make imports-apply" in cards[0]["body"].lower()
    assert "not available" not in " ".join(str(value) for card in cards for value in card.values()).lower()


def test_overview_workflow_path_cards_surface_top_staged_follow_through_when_queue_row_has_target_file():
    fundamentals_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "fundamentals",
                "ticker": "NVDA",
                "title": "Review fundamentals import draft",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )
    prices_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "AMD",
                "title": "Review price import drafts",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make price-validate",
                "example_command": "",
                "target_file": "data/imports/prices.csv",
            }
        ]
    )

    fundamentals_cards = dashboard.overview_workflow_path_cards(None, fundamentals_queue)
    prices_cards = dashboard.overview_workflow_path_cards(None, prices_queue)

    assert fundamentals_cards[0]["title"] == "make imports-validate"
    assert "make imports-preview" in fundamentals_cards[0]["body"].lower()
    assert "make imports-apply" in fundamentals_cards[0]["body"].lower()
    assert prices_cards[0]["title"] == "make price-validate"
    assert "make price-preview" in prices_cards[0]["body"].lower()
    assert "make price-apply" in prices_cards[0]["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in " ".join(
        str(value) for card in fundamentals_cards + prices_cards for value in card.values()
    ).lower()


def test_overview_workflow_path_cards_use_structured_project_status_steps():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Fix top prices blocker (META)",
                "Command": "make focus-price TICKER=META",
                "Reason": "Provider rows could not be parsed cleanly, so price coverage is still the top blocker.",
                "SourceContext": "data/imports/prices.csv",
                "FreshnessContext": "2026-05-21",
            },
            {
                "Step": "Review fundamentals import draft",
                "Command": "make imports-validate",
                "Reason": "Fundamentals import drafts already exist in data/imports/fundamentals.csv and should be validated before preview/apply.",
            },
            {
                "Step": "Deterministic verification",
                "Command": "make verify",
                "Reason": "Confirm local outputs still pass after the fundamentals import drafts follow-through.",
            },
        ]
    }
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "META",
                "title": "Repair prices",
                "reason": "Need more local rows.",
                "example_command": "make price-worklist",
            }
        ]
    )

    cards = dashboard.overview_workflow_path_cards(payload, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["title"] == "make focus-price TICKER=META"
    assert cards[1]["title"] == "make imports-validate"
    assert cards[2]["title"] == "make verify"
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "source: data/imports/prices.csv" in rendered
    assert "freshness: 2026-05-21" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_workflow_path_cards_use_command_family_fallback_when_reason_is_missing():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Review peer import draft",
                "Command": "make imports-validate",
                "Reason": "",
            }
        ]
    }

    cards = dashboard.overview_workflow_path_cards(payload, None)

    assert cards[0]["title"] == "make imports-validate"
    assert "staged flow" in [badge.lower() for badge in cards[0]["badges"]]
    assert "make imports-preview" in cards[0]["body"].lower()
    assert "make imports-apply" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_workflow_path_cards_keep_structured_staged_follow_through_visible_when_reason_is_generic():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Review fundamentals import draft",
                "Command": "make imports-validate",
                "Reason": "Use local import draft workflows if the free refresh fails.",
            },
            {
                "Step": "Advance price import draft",
                "Command": "make price-validate",
                "Reason": "Use local import draft workflows if the free refresh fails.",
            },
        ]
    }

    cards = dashboard.overview_workflow_path_cards(payload, None)

    assert cards[0]["title"] == "make imports-validate"
    assert "make imports-preview" in cards[0]["body"].lower()
    assert "make imports-apply" in cards[0]["body"].lower()
    assert cards[1]["title"] == "make price-validate"
    assert "make price-preview" in cards[1]["body"].lower()
    assert "make price-apply" in cards[1]["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in " ".join(
        card["body"] for card in cards[:2]
    ).lower()


def test_overview_workflow_path_cards_use_bundle_fallback_when_reason_is_missing():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Run highest-leverage price bundle",
                "Command": "make bundle-prices",
                "Reason": "",
            }
        ]
    }

    cards = dashboard.overview_workflow_path_cards(payload, None)

    assert cards[0]["title"] == "make bundle-prices"
    assert "bundle first" in [badge.lower() for badge in cards[0]["badges"]]
    assert "highest-leverage local bundle first" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_workflow_path_cards_use_runbook_fallback_when_reason_is_missing():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Open peer runbook",
                "Command": "make runbook-peers",
                "Reason": "",
            }
        ]
    }

    cards = dashboard.overview_workflow_path_cards(payload, None)

    assert cards[0]["title"] == "make runbook-peers"
    assert "staged flow" in [badge.lower() for badge in cards[0]["badges"]]
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_workflow_path_cards_use_status_check_when_structured_command_is_missing():
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Read-only status snapshot",
                "Command": "",
                "Reason": "Rebuild the local status snapshot before choosing a deeper workflow path.",
            }
        ]
    }

    cards = dashboard.overview_workflow_path_cards(payload, None)

    assert cards[0]["title"] == "make status-check TOP_N=5"
    assert cards[0]["command"] == "make status-check TOP_N=5"
    assert "local status snapshot" in cards[0]["body"].lower()


def test_overview_workflow_path_cards_fall_back_to_safe_defaults():
    cards = dashboard.overview_workflow_path_cards(None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "make status-check TOP_N=5"
    assert cards[1]["title"] == "make verify"
    assert cards[2]["title"] == "make dashboard-smoke"
    assert "buy" not in rendered


def test_overview_workflow_reason_card_uses_action_queue_context():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "NVDA",
                "title": "Repair prices",
                "reason": "NVDA update failed during remote refresh.",
                "recommended_action": "Normalize verified downloaded OHLCV rows, then run make price-validate, make price-preview, and make price-apply.",
                "example_command": "make price-worklist",
            }
        ]
    )

    card = dashboard.overview_workflow_reason_card(None, queue)
    rendered = " ".join(str(value) for value in card.values()).lower()

    assert card["title"] == "make price-worklist"
    assert "nvda" in rendered
    assert "normalize verified downloaded ohlcv rows" in rendered
    assert "make price-validate" in rendered
    assert "make price-preview" in rendered
    assert "make price-apply" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_workflow_reason_card_uses_review_fallback_when_queue_copy_is_missing():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "peers",
                "ticker": "TSLA",
                "title": "Research peers",
                "reason": "",
                "recommended_action": "",
                "example_command": "",
            }
        ]
    )

    card = dashboard.overview_workflow_reason_card(None, queue)
    rendered = " ".join(str(value) for value in card.values()).lower()

    assert card["title"] == "make focus-peers TICKER=TSLA"
    assert "tsla" in rendered
    assert "review peer path." in rendered
    assert "not available" not in rendered


def test_overview_workflow_reason_card_uses_imports_and_bundle_fallbacks_when_queue_copy_is_missing():
    imports_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "fundamentals",
                "ticker": "NVDA",
                "title": "Review fundamentals import draft",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make imports-validate",
                "example_command": "",
            }
        ]
    )
    bundle_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "peers",
                "ticker": "",
                "title": "Run peer bundle",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make bundle-peers",
                "example_command": "",
            }
        ]
    )

    imports_card = dashboard.overview_workflow_reason_card(None, imports_queue)
    bundle_card = dashboard.overview_workflow_reason_card(None, bundle_queue)

    assert imports_card["title"] == "make imports-validate"
    assert "nvda" in " ".join(str(value) for value in imports_card.values()).lower()
    assert "make imports-preview" in " ".join(str(value) for value in imports_card.values()).lower()
    assert "make imports-apply" in " ".join(str(value) for value in imports_card.values()).lower()
    assert bundle_card["title"] == "make bundle-peers"
    assert "highest-leverage local bundle first" in " ".join(str(value) for value in bundle_card.values()).lower()
    assert "not available" not in " ".join(str(value) for value in imports_card.values()).lower()
    assert "not available" not in " ".join(str(value) for value in bundle_card.values()).lower()


def test_overview_workflow_reason_card_uses_runbook_fallback_when_queue_copy_is_missing():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "peers",
                "ticker": "TSLA",
                "title": "Open peer runbook",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make runbook-peers",
                "example_command": "",
            }
        ]
    )

    card = dashboard.overview_workflow_reason_card(None, queue)
    rendered = " ".join(str(value) for value in card.values()).lower()

    assert card["title"] == "make runbook-peers"
    assert "tsla" in rendered
    assert "ordered lane runbook" in rendered
    assert "not available" not in rendered


def test_overview_workflow_reason_card_falls_back_to_status_snapshot():
    payload = {"summary": {"data_gaps": 12, "critical_actions": 4}}

    card = dashboard.overview_workflow_reason_card(payload, None)
    rendered = " ".join(str(value) for value in card.values()).lower()

    assert card["title"] == "make status-check TOP_N=5"
    assert "4 critical actions" in rendered
    assert "12 visible data gaps" in rendered
    assert "buy" not in rendered


def test_overview_workflow_reason_card_uses_actionable_empty_state_copy():
    card = dashboard.overview_workflow_reason_card(None, None)
    rendered = " ".join(str(value) for value in card.values()).lower()

    assert card["title"] == "make status-check TOP_N=5"
    assert "run make status-check top_n=5 first" in rendered
    assert "local blocker triage" in rendered
    assert "verification and ui review" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_workflow_reason_card_uses_bundle_fallback_when_structured_summary_is_thin():
    payload = {
        "summary": {"data_gaps": 0, "critical_actions": 0},
        "recommended_next_command_rows": [
            {
                "Step": "Run highest-leverage price bundle",
                "Command": "make bundle-prices",
                "Reason": "",
            }
        ],
    }

    card = dashboard.overview_workflow_reason_card(payload, None)
    rendered = " ".join(str(value) for value in card.values()).lower()

    assert card["title"] == "make bundle-prices"
    assert "bundle first" in [badge.lower() for badge in card["badges"]]
    assert "highest-leverage local bundle first" in rendered
    assert "not available" not in rendered


def test_overview_workflow_reason_card_uses_runbook_fallback_when_structured_summary_is_thin():
    payload = {
        "summary": {"data_gaps": 0, "critical_actions": 0},
        "recommended_next_command_rows": [
            {
                "Step": "Open peer runbook",
                "Command": "make runbook-peers",
                "Reason": "",
            }
        ],
    }

    card = dashboard.overview_workflow_reason_card(payload, None)
    rendered = " ".join(str(value) for value in card.values()).lower()

    assert card["title"] == "make runbook-peers"
    assert "local import draft workflow" in rendered
    assert "not available" not in rendered


def test_overview_handoff_cards_link_to_deeper_tabs_without_trade_language():
    cards = dashboard.overview_handoff_cards()
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["title"] == "Data Health"
    assert cards[0]["command"] == "make onboarding"
    assert cards[1]["title"] == "Single-Stock Report"
    assert cards[1]["command"] == "make stock-report-md TICKER=NVDA"
    assert cards[2]["title"] == "Monthly Picks"
    assert cards[2]["command"] == "make monthly"
    assert "blocking the local research workflow" in rendered
    assert "single-name deep dive" in rendered
    assert "track-record readiness" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_best_local_research_path_cards_stitch_name_command_and_page():
    coverage = pd.DataFrame(
        [
            {"ticker": "NVDA", "usable_for_momentum": True, "dcf_ready": True, "peer_ready": False},
            {"ticker": "TSLA", "usable_for_momentum": True, "dcf_ready": False, "peer_ready": False},
        ]
    )
    holdings = pd.DataFrame([{"Ticker": "NVDA"}])
    payload = {"recommended_next_commands": ["make onboarding", "make verify", "make dashboard"]}
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "NVDA",
                "title": "Repair prices",
                "reason": "NVDA update failed during remote refresh.",
                "recommended_action": "Normalize verified downloaded OHLCV rows, then run make price-validate, make price-preview, and make price-apply.",
                "example_command": "make price-worklist",
            }
        ]
    )

    cards = dashboard.overview_best_local_research_path_cards(coverage, holdings, payload, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["title"] == "NVDA"
    assert cards[1]["title"] == "make stock-report-md TICKER=NVDA"
    assert cards[1]["badges"] == ["single name", "ready flow"]
    assert cards[2]["title"] == "Single-Stock Report"
    assert "best current name" in rendered
    assert "next command" in rendered
    assert "next page" in rendered
    assert "ticker-targeted stock report" in rendered
    assert "make verify" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_best_local_research_path_cards_use_monthly_front_door_for_monthly_page():
    coverage = pd.DataFrame(
        [
            {"ticker": "TSLA", "usable_for_momentum": True, "dcf_ready": False, "peer_ready": False},
            {"ticker": "AMD", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
        ]
    )
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "high",
                "action_type": "fundamentals",
                "ticker": "TSLA",
                "title": "Refresh onboarding",
                "reason": "Need richer local context.",
                "example_command": "make onboarding",
            }
        ]
    )

    cards = dashboard.overview_best_local_research_path_cards(coverage, None, None, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "TSLA"
    assert cards[1]["title"] == "make monthly"
    assert cards[2]["title"] == "Monthly Picks"
    assert "make monthly" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_best_local_research_path_cards_use_monthly_front_door_without_queue_guidance():
    coverage = pd.DataFrame(
        [
            {"ticker": "TSLA", "usable_for_momentum": True, "dcf_ready": False, "peer_ready": False},
            {"ticker": "AMD", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
        ]
    )

    cards = dashboard.overview_best_local_research_path_cards(coverage, None, None, None)

    assert cards[0]["title"] == "TSLA"
    assert cards[1]["title"] == "make monthly"
    assert cards[2]["title"] == "Monthly Picks"


def test_overview_best_local_research_path_cards_fall_back_gracefully():
    cards = dashboard.overview_best_local_research_path_cards(None, None, None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["title"] == "No current ready names yet"
    assert cards[0]["command"] == "make onboarding"
    assert cards[1]["title"] == "make onboarding"
    assert cards[2]["title"] == "Data Health"
    assert "no locally ready name yet" in cards[0]["body"].lower()
    assert "clear the highest-leverage blocker" in cards[0]["body"].lower()
    assert "no current ready names yet" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_best_local_research_path_cards_use_runbook_fallback_when_no_ready_name_exists():
    coverage = pd.DataFrame(
        [
            {"ticker": "TSLA", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
            {"ticker": "AMD", "usable_for_momentum": False, "dcf_ready": False, "peer_ready": False},
        ]
    )
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Open peer runbook",
                "Command": "make runbook-peers",
                "Reason": "",
            }
        ]
    }

    cards = dashboard.overview_best_local_research_path_cards(coverage, None, payload, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "No current ready names yet"
    assert cards[0]["command"] == "make runbook-peers"
    assert cards[1]["title"] == "make runbook-peers"
    assert cards[2]["title"] == "Data Health"
    assert "ordered lane runbook" in rendered
    assert "local import draft workflow" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_interpretation_guardrail_card_flags_partial_workflow():
    payload = {
        "summary": {
            "tickers_total": 12,
            "tickers_with_prices": 3,
            "tickers_dcf_ready": 0,
            "tickers_peer_ready": 0,
            "data_gaps": 19,
        }
    }

    card = dashboard.overview_interpretation_guardrail_card(
        payload,
        {"critical": 2, "high": 4, "medium": 0},
        {"needs_price_data": 6, "thin_liquidity": 1, "high_correlation": 0},
    )
    rendered = " ".join(str(value) for value in card.values()).lower()

    assert "workflow" in card["title"].lower()
    assert card["command"] == "make status-check TOP_N=5"
    assert "the workflow is usable, but some outputs should still be treated as partial" in rendered
    assert "19 visible data gaps remain" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_interpretation_guardrail_card_flags_needs_data_workflow():
    payload = {
        "summary": {
            "tickers_total": 12,
            "tickers_with_prices": 3,
            "tickers_dcf_ready": 0,
            "tickers_peer_ready": 0,
            "data_gaps": 19,
        }
    }

    card = dashboard.overview_interpretation_guardrail_card(
        payload,
        {"critical": 8, "high": 4, "medium": 0},
        {"needs_price_data": 6, "thin_liquidity": 2, "high_correlation": 1},
    )
    rendered = " ".join(str(value) for value in card.values()).lower()

    assert "needs data workflow" in rendered
    assert card["command"] == "make onboarding"
    assert "coverage is still the main blocker" in rendered
    assert "3/12 tickers have usable prices" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_interpretation_guardrail_card_supports_ready_workflow():
    payload = {
        "summary": {
            "tickers_total": 10,
            "tickers_with_prices": 10,
            "tickers_dcf_ready": 8,
            "tickers_peer_ready": 7,
            "data_gaps": 0,
        }
    }

    card = dashboard.overview_interpretation_guardrail_card(
        payload,
        {"critical": 0, "high": 0, "medium": 0},
        {"needs_price_data": 0, "thin_liquidity": 0, "high_correlation": 0},
    )
    rendered = " ".join(str(value) for value in card.values()).lower()

    assert "ready workflow" in rendered
    assert card["command"] == "make dashboard-smoke"
    assert "10/10 tickers have prices" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_coverage_hotspot_cards_surface_dataset_pressure():
    queue = pd.DataFrame(
        [
            {"priority": 1, "action_type": "prices", "ticker": "NVDA"},
            {"priority": 1, "action_type": "prices", "ticker": "AMD"},
            {"priority": 2, "action_type": "fundamentals", "ticker": "MSFT"},
            {"priority": 3, "action_type": "peers", "ticker": "NVDA"},
            {"priority": 4, "action_type": "earnings", "ticker": "AVGO"},
        ]
    )

    cards = dashboard.overview_coverage_hotspot_cards(queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Prices"
    assert cards[0]["command"] == "make runbook-prices-broader"
    assert any(card["title"] == "Fundamentals" for card in cards)
    assert any(card.get("command") == "make runbook-fundamentals-broader" for card in cards)
    assert any(card["title"] == "Peers" for card in cards)
    assert any(card.get("command") == "make runbook-peers-broader" for card in cards)
    assert "2 action rows and 2 affected tickers" in rendered
    assert "examples:" in rendered
    assert "nvda" in rendered
    assert "amd" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_coverage_hotspot_cards_handle_missing_queue():
    cards = dashboard.overview_coverage_hotspot_cards(None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 1
    assert "no hotspot queue yet" in rendered
    assert cards[0]["command"] == "make action-queue"
    assert "make action-queue" in rendered
    assert "prices, fundamentals, peers, or optional context" in rendered


def test_overview_coverage_hotspot_cards_use_onboarding_for_optional_context():
    queue = pd.DataFrame(
        [
            {"priority": 1, "action_type": "earnings", "ticker": "AVGO"},
            {"priority": 2, "action_type": "analyst_estimates", "ticker": "AMD"},
        ]
    )

    cards = dashboard.overview_coverage_hotspot_cards(queue)

    assert cards[0]["title"] == "Earnings"
    assert cards[0]["command"] == "make onboarding"
    assert cards[1]["title"] == "Analyst Estimates"
    assert cards[1]["command"] == "make onboarding"


def test_overview_coverage_hotspot_cards_use_action_queue_check_for_unknown_action_type():
    queue = pd.DataFrame(
        [
            {"priority": 1, "action_type": "source_registry", "ticker": ""},
        ]
    )

    cards = dashboard.overview_coverage_hotspot_cards(queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Source Registry"
    assert cards[0]["command"] == "make action-queue-check TOP_N=10"
    assert "visible local workflow pressure" in rendered


def test_monthly_pick_card_html_is_product_style_and_clean():
    html = dashboard.monthly_pick_card_html(
        {
            "Rank": 1,
            "Ticker": "NVDA",
            "Theme": "AI Semiconductors",
            "Sector": "SMH",
            "PrimaryPurpose": "Momentum Leader",
            "CompositeScore": 52.98,
            "MomentumScore": 61.52,
            "SetupStatus": "Watch",
            "FinalState": "Review Thesis",
            "Reason": "Composite score uses transparent local components. Missing or incomplete fields reduced data confidence.",
            "MissingDataFields": "Return3M, fundamentals unavailable, peers",
        }
    )

    assert "pick-card" in html
    assert "Rank 1" in html
    assert "NVDA" in html
    assert "52.98" in html
    assert "Needs SEC enrichment" in html
    assert "Needs peers.csv" in html
    assert "nan" not in html.lower()
    assert "none" not in html.lower()


def test_monthly_picks_landing_cards_show_history_and_gap_context():
    picks = pd.DataFrame(
        [
            {"Month": "2026-05", "MissingDataFields": "Return3M"},
            {"Month": "2026-05", "MissingDataFields": ""},
        ]
    )
    track = pd.DataFrame([{"Month": "2026-04"}])
    equity = pd.DataFrame()
    cards = dashboard.monthly_picks_landing_cards(picks, track, equity, 5, "2026-05-12", 12)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 4
    assert "2026-05" in rendered
    assert "2 of 5" in rendered
    assert "needs history" in rendered
    assert "1 rows with gaps" in rendered
    assert "data-gated review queue" in rendered
    assert "not as advice or a conclusion list" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_monthly_picks_quality_cards_explain_candidate_boundary_without_recommendations():
    empty_cards = dashboard.monthly_picks_quality_cards(pd.DataFrame(), None, None, 5)
    partial_picks = pd.DataFrame(
        [
            {"Month": "2026-05", "MissingDataFields": "Return3M"},
            {"Month": "2026-05", "MissingDataFields": ""},
        ]
    )
    partial_cards = dashboard.monthly_picks_quality_cards(partial_picks, None, None, 5)
    track = pd.DataFrame([{"Month": "2026-04"}])
    equity = pd.DataFrame([{"Month": "2026-04", "PicksEquity": 1.0, "BenchmarkEquity": 1.0}])
    full_cards = dashboard.monthly_picks_quality_cards(pd.DataFrame([{"MissingDataFields": ""}] * 5), track, equity, 5)
    rendered = " ".join(
        str(value)
        for card in empty_cards + partial_cards + full_cards
        for value in card.values()
    ).lower()

    assert empty_cards[0]["title"] == "Candidate review is locked"
    assert partial_cards[0]["title"] == "Partial candidate set"
    assert full_cards[0]["title"] == "Candidate set is filled"
    assert "monthly picks has no supported local candidates yet" in rendered
    assert "2 of 5 conservative slots are filled" in rendered
    assert "weaker names are not forced into the list" in rendered
    assert "no allocation conclusion" in rendered
    assert "position sizing" in rendered
    assert "external account actions" in rendered
    assert "direct portfolio actions" in rendered
    assert "track record limited" in rendered
    assert "track record ready" in rendered
    assert "missing fields stay visible" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_monthly_picks_function_quality_cards_explain_score_limits_and_provenance():
    cards = dashboard.monthly_picks_function_quality_cards()
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["WHAT IT CAN DO", "WHAT IT CANNOT DO", "LOGIC SOURCE", "BEST USE"]
    assert "rank a local research-candidate queue" in rendered
    assert "transparent local score components" in rendered
    assert "triage aids for deeper single-stock review" in rendered
    assert "price, setup, liquidity, and optional fundamentals" in rendered
    assert "no automatic portfolio decision" in rendered
    assert "does not provide allocation, position sizing, account actions, or direct recommendations" in rendered
    assert "empty slots and missing fields stay visible" in rendered
    assert "project scoring logic" in rendered
    assert "src/monthly_picks.py" in rendered
    assert "libraries support data/ui" in rendered
    assert "shipped scoring comes from project code and local data" in rendered
    assert "plugins can help development review" not in rendered
    assert "make stock-report-md ticker=..." in rendered
    assert "valuation readiness" in rendered
    assert "source freshness" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_monthly_picks_next_step_cards_cover_generation_coverage_history_and_review():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "NVDA",
                "title": "Repair prices",
                "reason": "Need more local rows.",
                "example_command": "make price-worklist",
            }
        ]
    )

    cards = dashboard.monthly_picks_next_step_cards(None, None, None, 5, queue)
    assert cards[0]["title"] == "Refresh monthly context"
    assert cards[0]["command"] == "make monthly"
    assert "make monthly" in cards[0]["body"]

    picks = pd.DataFrame([{"Month": "2026-05", "MissingDataFields": "Return3M"}] * 4)
    cards = dashboard.monthly_picks_next_step_cards(picks, None, None, 5, queue)
    assert cards[0]["title"] == "Improve candidate coverage"
    assert "make price-worklist" in cards[0]["body"]

    full_picks = pd.DataFrame([{"Month": "2026-05", "MissingDataFields": ""}] * 5)
    cards = dashboard.monthly_picks_next_step_cards(full_picks, None, None, 5, queue)
    assert cards[0]["title"] == "Improve track-record coverage"
    assert cards[0]["command"] == "make price-worklist"

    track = pd.DataFrame([{"Month": "2026-04"}])
    equity = pd.DataFrame([{"Month": "2026-04", "PicksEquity": 1.0, "BenchmarkEquity": 1.0}])
    cards = dashboard.monthly_picks_next_step_cards(full_picks, track, equity, 5, queue)
    assert cards[0]["title"] == "Review current candidates"
    assert cards[0]["command"] == "make dashboard-smoke"
    assert "dashboard-smoke" in cards[0]["body"]


def test_monthly_picks_track_record_gap_points_to_blocker_command():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "NVDA",
                "title": "Repair prices",
                "reason": "Need more local rows.",
                "example_command": "make price-worklist",
            }
        ]
    )
    full_picks = pd.DataFrame([{"Month": "2026-05", "MissingDataFields": ""}] * 5)

    cards = dashboard.monthly_picks_next_step_cards(full_picks, None, None, 5, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "improve track-record coverage" in rendered
    assert "make price-worklist" in rendered


def test_monthly_picks_track_record_gap_uses_track_record_front_door_without_blocker_queue():
    full_picks = pd.DataFrame([{"Month": "2026-05", "MissingDataFields": ""}] * 5)

    cards = dashboard.monthly_picks_next_step_cards(full_picks, None, None, 5, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Improve track-record coverage"
    assert cards[0]["command"] == "make track-record"
    assert "make track-record" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_monthly_picks_coverage_gap_uses_data_wizard_without_blocker_queue():
    picks = pd.DataFrame([{"Month": "2026-05", "MissingDataFields": "Return3M"}] * 4)

    cards = dashboard.monthly_picks_next_step_cards(picks, None, None, 5, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Improve candidate coverage"
    assert cards[0]["command"] == "make data-wizard TOP_N=10"
    assert "make data-wizard top_n=10" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_monthly_picks_empty_candidates_use_dry_run_loop_not_random_ticker():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "AIAI",
                "title": "Repair prices",
                "reason": "Need more local rows.",
                "focus_command": "make focus-price TICKER=AIAI",
            }
        ]
    )

    cards = dashboard.monthly_picks_next_step_cards(pd.DataFrame(), None, None, 5, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values())

    assert cards[0]["title"] == "Improve candidate coverage"
    assert cards[0]["command"] == "make price-refresh-loop DRY_RUN=1"
    assert "make price-refresh-loop DRY_RUN=1" in rendered
    assert "preview the capped broad coverage plan" in rendered
    assert "make focus-price TICKER=AIAI" not in rendered


def test_monthly_picks_coverage_gap_uses_data_wizard_with_empty_queue():
    picks = pd.DataFrame([{"Month": "2026-05", "MissingDataFields": "Return3M"}] * 4)

    cards = dashboard.monthly_picks_next_step_cards(picks, None, None, 5, pd.DataFrame())

    assert cards[0]["title"] == "Improve candidate coverage"
    assert cards[0]["command"] == "make data-wizard TOP_N=10"


def test_monthly_picks_track_record_gap_uses_track_record_front_door_with_empty_queue():
    full_picks = pd.DataFrame([{"Month": "2026-05", "MissingDataFields": ""}] * 5)

    cards = dashboard.monthly_picks_next_step_cards(full_picks, None, None, 5, pd.DataFrame())

    assert cards[0]["title"] == "Improve track-record coverage"
    assert cards[0]["command"] == "make track-record"


def test_stock_report_brief_html_summarizes_readiness_without_advice():
    html = dashboard.stock_report_brief_html(
        {
            "ticker": "NVDA",
            "provider_name": "LocalCSVMarketDataProvider",
            "generated_at": "2026-05-21T12:00:00Z",
            "valuation_snapshot": {"status": "partial", "coverage": "DCF only"},
            "valuation_readiness": {
                "dcf_ready": True,
                "peer_ready": False,
                "earnings_available": False,
                "analyst_estimates_available": False,
            },
            "missing_data_warnings": ["Needs peers.csv", "Needs earnings.csv"],
        }
    )

    assert "NVDA research snapshot" in html
    assert "saved price, fundamentals, readiness, and decision rows" in html
    assert "provider data and existing research-output context" not in html
    assert "DCF Ready" in html
    assert "Peers Need Data" in html
    assert "peer fundamentals or peer price/market-cap context" in html
    assert "Earnings Missing" in html
    assert "2" in html
    assert "buy" not in html.lower()
    assert "sell" not in html.lower()


def test_onboarding_summary_counts_core_and_optional_gaps():
    coverage = pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "usable_for_momentum": True,
                "dcf_ready": True,
                "peer_ready": True,
                "has_earnings": False,
                "has_analyst_estimates": False,
                "missing_required_for_momentum": "",
                "missing_required_for_dcf": "",
                "missing_required_for_peer_relative": "",
            },
            {
                "ticker": "AMD",
                "usable_for_momentum": False,
                "dcf_ready": False,
                "peer_ready": False,
                "has_earnings": False,
                "has_analyst_estimates": False,
                "missing_required_for_momentum": "prices",
                "missing_required_for_dcf": "fundamentals row",
                "missing_required_for_peer_relative": "peer mapping",
            },
        ]
    )

    summary = dashboard.summarize_ticker_coverage(coverage)

    assert summary["usable_price_tickers"] == 1
    assert summary["dcf_ready_tickers"] == 1
    assert summary["peer_ready_tickers"] == 1
    assert summary["optional_only_missing_tickers"] == 1


def test_stock_report_helpers_format_missing_values_cleanly():
    frame = dashboard.stock_report_key_value_frame(
        {"price": None, "return": float("nan"), "volume": 12345},
        [
            ("price", "Price", "currency"),
            ("return", "Return", "percent"),
            ("volume", "Volume", "integer"),
        ],
    )

    assert frame.iloc[0]["Value"] == "Not available"
    assert frame.iloc[1]["Value"] == "Not enough history"
    assert frame.iloc[2]["Value"] == "12,345"
    assert not frame["Value"].astype(str).str.lower().str.contains("nan|none|null").any()


def test_stock_report_summary_cards_are_readable_and_research_only():
    payload = {
        "ticker": "NVDA",
        "provider_name": "LocalCSVMarketDataProvider",
        "price_snapshot": {"price": 100.0, "volume": None, "market_time": None},
        "performance": {"one_month": 0.12, "three_month": None, "one_year": 0.4},
        "valuation_snapshot": {"status": "insufficient_data", "coverage": "limited"},
        "valuation_readiness": {
            "dcf_ready": True,
            "peer_ready": False,
            "earnings_available": False,
            "analyst_estimates_available": False,
        },
        "missing_data_warnings": ["peers missing"],
    }

    cards = dashboard.stock_report_summary_cards(payload)
    rendered = " ".join(str(value) for card in cards for value in card.values())

    assert len(cards) == 4
    assert "$100.00" in rendered
    assert "Insufficient data" in rendered
    assert "insufficient_data" not in rendered
    assert "Peers needed" in rendered
    assert "buy" not in rendered.lower()
    assert "sell" not in rendered.lower()


def test_stock_report_analysis_quality_cards_classify_supported_scope():
    monitor_cards = dashboard.stock_report_analysis_quality_cards(
        {
            "asset_type": "etf",
            "valuation_snapshot": {"status": "excluded"},
            "valuation_readiness": {"price_ready": True, "dcf_ready": False, "peer_ready": False},
            "missing_data_warnings": ["DCF excluded"],
        }
    )
    standalone_cards = dashboard.stock_report_analysis_quality_cards(
        {
            "asset_type": "company",
            "valuation_snapshot": {"status": "calculated"},
            "valuation_readiness": {"price_ready": True, "dcf_ready": True, "peer_ready": False},
            "missing_data_warnings": ["Peers missing"],
        }
    )
    price_only_cards = dashboard.stock_report_analysis_quality_cards(
        {
            "asset_type": "company",
            "valuation_snapshot": {"status": "insufficient_data"},
            "valuation_readiness": {"price_ready": True, "dcf_ready": False, "peer_ready": False},
            "missing_data_warnings": ["Fundamentals missing"],
        }
    )
    rendered = " ".join(
        str(value)
        for card in monitor_cards + standalone_cards + price_only_cards
        for value in card.values()
    ).lower()

    assert "monitor-only context" in rendered
    assert "excluded, not failed" in rendered
    assert "standalone dcf review" in rendered
    assert "peer-relative valuation remains limited" in rendered
    assert "price/setup review only" in rendered
    assert "company valuation stays blocked" in rendered
    assert "visible warnings reduce data confidence" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_dcf_calculation_path_cards_explain_ready_blocked_and_excluded_states():
    ready_cards = dashboard.stock_report_dcf_calculation_path_cards(
        {
            "asset_type": "company",
            "valuation_snapshot": {
                "status": "calculated",
                "dcf_result": {
                    "status": "calculated",
                    "assumptions": {
                        "revenue_growth": 0.1,
                        "fcf_margin": 0.2,
                        "wacc": 0.09,
                        "terminal_growth": 0.03,
                    },
                },
                "sensitivity_table": {"status": "calculated"},
            },
            "valuation_readiness": {"dcf_ready": True},
        }
    )
    blocked_cards = dashboard.stock_report_dcf_calculation_path_cards(
        {
            "asset_type": "company",
            "valuation_snapshot": {"status": "insufficient_data", "dcf_result": {"status": "insufficient_data"}},
            "valuation_readiness": {"dcf_ready": False, "dcf_missing_fields": ["revenue", "shares_outstanding"]},
        }
    )
    excluded_cards = dashboard.stock_report_dcf_calculation_path_cards(
        {
            "asset_type": "etf",
            "valuation_snapshot": {"status": "excluded", "dcf_result": {"status": "excluded"}},
            "valuation_readiness": {"dcf_ready": False},
        }
    )
    rendered = " ".join(
        str(value)
        for card in ready_cards + blocked_cards + excluded_cards
        for value in card.values()
    ).lower()

    assert [card["kicker"] for card in ready_cards] == ["DCF PATH", "FORMULA", "ASSUMPTIONS"]
    assert "ready for scenario math" in rendered
    assert "standalone dcf is calculated locally from trusted price and fundamentals inputs" in rendered
    assert "base fcf -> projected fcf" in rendered
    assert "discounted terminal value" in rendered
    assert "fair value per share" in rendered
    assert "not a price target" in rendered
    assert "blocked by missing inputs" in rendered
    assert "withholds dcf math until trusted company inputs pass readiness checks" in rendered
    assert "missing: revenue, shares outstanding" in rendered
    assert "formula path withheld" in rendered
    assert "excluded, not failed" in rendered
    assert "asset-type gate excludes company dcf" in rendered
    assert "use monitor context" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_valuation_boundary_cards_explain_source_product_and_locked_logic():
    ready_payload = {
        "asset_type": "company",
        "valuation_readiness": {"dcf_ready": True, "peer_ready": True},
        "valuation_snapshot": {
            "dcf_result": {"status": "calculated"},
            "relative_valuation": {"status": "calculated", "peer_count": 2},
        },
    }
    blocked_payload = {
        "asset_type": "company",
        "valuation_readiness": {"dcf_ready": False, "peer_ready": False},
        "valuation_snapshot": {
            "dcf_result": {"status": "insufficient_data"},
            "relative_valuation": {"status": "calculated", "peer_count": 2},
        },
    }
    trend_only_payload = {
        "asset_type": "company",
        "valuation_readiness": {"dcf_ready": True, "peer_ready": False, "peer_trend_comparison_ready": True},
        "valuation_snapshot": {
            "dcf_result": {"status": "calculated"},
            "relative_valuation": {"status": "peer_data_unavailable", "peer_count": 2},
        },
    }
    etf_payload = {
        "asset_type": "etf",
        "valuation_readiness": {"dcf_ready": False, "peer_ready": False},
        "valuation_snapshot": {
            "dcf_result": {"status": "excluded"},
            "relative_valuation": {"status": "calculated", "peer_count": 2},
        },
    }

    ready_cards = dashboard.stock_report_valuation_boundary_cards(ready_payload)
    blocked_cards = dashboard.stock_report_valuation_boundary_cards(blocked_payload)
    trend_only_cards = dashboard.stock_report_valuation_boundary_cards(trend_only_payload)
    etf_cards = dashboard.stock_report_valuation_boundary_cards(etf_payload)
    rendered = " ".join(
        str(value)
        for card in ready_cards + blocked_cards + trend_only_cards + etf_cards
        for value in card.values()
    ).lower()

    assert [card["kicker"] for card in ready_cards] == ["SOURCE ROWS", "INTRINSIC VALUE", "RELATIVE VALUE", "BOUNDARY"]
    assert "inputs do not decide conclusions" in rendered
    assert "project readiness gates decide what can be analyzed" in rendered
    assert "dcf scenario math is available" in rendered
    assert "this product calculates assumptions, sensitivity, and fair value/share locally" in rendered
    assert "peer valuation available" in rendered
    assert "source-backed peer mappings and peer valuation inputs are ready" in rendered
    assert "dcf remains locked" in rendered
    assert "projected fcf, terminal value, equity value, fair value/share, and sensitivity withheld" in rendered
    assert "peer valuation withheld" in rendered
    assert "peer trend available; valuation withheld" in rendered
    assert "mapped peer price history can support peer trend context" in rendered
    assert "peer-relative valuation, premium/discount, and peer dcf comparison stay withheld" in rendered
    assert "dcf excluded for monitor context" in rendered
    assert "operating-company dcf is excluded, not failed" in rendered
    assert "missing data never becomes a valuation opinion" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_peer_relative_comparison_frame_is_readiness_gated():
    relative = {
        "status": "calculated",
        "peer_count": 2,
        "subject_multiples": {"pe": 20.0, "ps": 8.0},
        "peer_median_multiples": {"pe": 25.0, "ps": 10.0},
        "relative_discount_premium_by_metric": {"pe": -0.2, "ps": -0.2},
    }
    ready_payload = {
        "asset_type": "company",
        "valuation_readiness": {"dcf_ready": True, "peer_ready": True},
        "valuation_snapshot": {"relative_valuation": relative},
    }
    blocked_payload = {
        "asset_type": "company",
        "valuation_readiness": {"dcf_ready": True, "peer_ready": False},
        "valuation_snapshot": {"relative_valuation": relative},
    }
    etf_payload = {
        "asset_type": "etf",
        "valuation_readiness": {"dcf_ready": False, "peer_ready": False},
        "valuation_snapshot": {"relative_valuation": relative},
    }

    ready_frame = dashboard.stock_report_peer_relative_comparison_frame(ready_payload)
    blocked_frame = dashboard.stock_report_peer_relative_comparison_frame(blocked_payload)
    ready_summary = dashboard.stock_report_peer_relative_summary(ready_payload)
    blocked_summary = dashboard.stock_report_peer_relative_summary(blocked_payload)
    etf_summary = dashboard.stock_report_peer_relative_summary(etf_payload)
    rendered = " ".join(ready_frame.astype(str).to_numpy().flatten()).lower()

    assert dashboard.stock_report_peer_relative_display_ready(ready_payload) is True
    assert dashboard.stock_report_peer_relative_display_ready(blocked_payload) is False
    assert ready_summary["peer_status"] == "calculated"
    assert ready_summary["relative_score"] == "Not available"
    assert blocked_summary["peer_status"] == "Withheld"
    assert blocked_summary["peer_group"] == "Not reader-ready"
    assert blocked_summary["relative_score"] == "Locked"
    assert "withheld until trusted peer mappings" in str(blocked_summary["note"]).lower()
    assert etf_summary["peer_status"] == "Withheld"
    assert "excluded for etf/index/fund monitor context" in str(etf_summary["note"]).lower()
    assert list(ready_frame.columns) == ["Metric", "Subject", "Peer Median", "Discount / Premium"]
    assert "p/e" in rendered
    assert "25" in rendered
    assert blocked_frame.empty
    assert "withheld until trusted peer mappings and peer valuation inputs pass readiness" in dashboard.stock_report_peer_relative_empty_message(blocked_payload).lower()
    assert "excluded for etf/index/fund monitor context" in dashboard.stock_report_peer_relative_empty_message(etf_payload).lower()
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_fundamentals_quality_cards_explain_dcf_input_readiness():
    ready_cards = dashboard.stock_report_fundamentals_quality_cards(
        {
            "ticker": "NVDA",
            "valuation_readiness": {"dcf_ready": True, "fundamentals_ready": True},
            "financial_summary": {
                "revenue": 100_000_000,
                "free_cash_flow": 20_000_000,
                "fcf_margin": 0.2,
                "shares_outstanding": 10_000_000,
                "operating_margin": 0.3,
                "profit_margin": 0.25,
                "cash": 5_000_000,
                "debt": 2_000_000,
            },
        }
    )
    partial_cards = dashboard.stock_report_fundamentals_quality_cards(
        {
            "ticker": "META",
            "valuation_readiness": {"dcf_ready": False, "fundamentals_ready": True},
            "financial_summary": {
                "revenue": 100_000_000,
                "free_cash_flow": 20_000_000,
                "shares_outstanding": 10_000_000,
            },
        }
    )
    locked_cards = dashboard.stock_report_fundamentals_quality_cards(
        {
            "valuation_readiness": {"dcf_ready": False, "fundamentals_ready": False},
            "financial_summary": {"revenue": 100_000_000},
        }
    )
    rendered = " ".join(
        str(value)
        for card in ready_cards + partial_cards + locked_cards
        for value in card.values()
    ).lower()

    assert [card["kicker"] for card in ready_cards] == ["FUNDAMENTALS QUALITY", "QUALITY CONTEXT", "LOGIC SOURCE"]
    assert "dcf inputs ready" in rendered
    assert "review assumptions and source freshness" in rendered
    assert "partial fundamentals context" in rendered
    assert "missing: fcf margin" in rendered
    assert "fundamentals need data" in rendered
    assert "should not infer valuation from unavailable fundamentals" in rendered
    assert "margins, cash, and debt help explain business quality only when present" in rendered
    assert "fundamentals rules stay in project code" in rendered
    assert "support tools are not analysis logic" in rendered
    assert "fundamentals rules stay in project code; support tools are not analysis logic" in rendered
    assert ready_cards[0]["command"] == "make focus-fundamentals TICKER=NVDA"
    assert partial_cards[0]["command"] == "make focus-fundamentals TICKER=META"
    assert locked_cards[0]["command"] == "make status-check TOP_N=5"
    assert "ticker=..." not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_evaluation_summary_frame_explains_supported_withheld_and_next_step():
    monitor_frame = dashboard.stock_report_evaluation_summary_frame(
        {
            "asset_type": "etf",
            "valuation_snapshot": {"status": "excluded"},
            "valuation_readiness": {"price_ready": True, "dcf_ready": False, "peer_ready": False},
            "missing_data_warnings": ["DCF excluded"],
        }
    )
    dcf_frame = dashboard.stock_report_evaluation_summary_frame(
        {
            "asset_type": "company",
            "valuation_snapshot": {"status": "calculated"},
            "valuation_readiness": {"price_ready": True, "dcf_ready": True, "peer_ready": False},
            "missing_data_warnings": ["Peers missing"],
        }
    )
    full_frame = dashboard.stock_report_evaluation_summary_frame(
        {
            "asset_type": "company",
            "valuation_snapshot": {"status": "calculated"},
            "valuation_readiness": {"price_ready": True, "dcf_ready": True, "peer_ready": True},
            "missing_data_warnings": [],
        }
    )
    price_frame = dashboard.stock_report_evaluation_summary_frame(
        {
            "asset_type": "company",
            "valuation_snapshot": {"status": "insufficient_data"},
            "valuation_readiness": {"price_ready": True, "dcf_ready": False, "peer_ready": False},
            "missing_data_warnings": ["Fundamentals missing"],
        }
    )
    unlock_frame = dashboard.stock_report_evaluation_summary_frame(
        {
            "asset_type": "company",
            "valuation_snapshot": {"status": "insufficient_data"},
            "valuation_readiness": {"price_ready": False, "dcf_ready": False, "peer_ready": False},
            "missing_data_warnings": ["Price history missing"],
        }
    )
    rendered = " ".join(
        " ".join(frame.astype(str).to_numpy().flatten()).lower()
        for frame in (monitor_frame, dcf_frame, full_frame, price_frame, unlock_frame)
    )

    assert list(monitor_frame.columns) == ["Question", "Answer"]
    assert monitor_frame.iloc[0].to_dict() == {"Question": "Evaluation mode", "Answer": "Monitor-only context"}
    assert dcf_frame.iloc[0].to_dict() == {"Question": "Evaluation mode", "Answer": "Standalone DCF review"}
    assert full_frame.iloc[0].to_dict() == {"Question": "Evaluation mode", "Answer": "DCF-ready review"}
    assert price_frame.iloc[0].to_dict() == {"Question": "Evaluation mode", "Answer": "Price/setup review only"}
    assert unlock_frame.iloc[0].to_dict() == {"Question": "Evaluation mode", "Answer": "Data-unlock only"}
    assert "what this report can support" in rendered
    assert "monitor-only context" in rendered
    assert "standalone dcf review" in rendered
    assert "dcf-ready review" in rendered
    assert "price/setup review only" in rendered
    assert "data-unlock only" in rendered
    assert "operating-company dcf and peer valuation are excluded, not failed" in rendered
    assert "standalone dcf assumptions" in rendered
    assert "peer-relative valuation remains withheld" in rendered
    assert "data-unlock workflow only" in rendered
    assert "conclusions stay unavailable until price coverage starts" in rendered
    assert "missing inputs reduce data confidence" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_evaluation_summary_cards_surface_trust_boundary_before_tables():
    cards = dashboard.stock_report_evaluation_summary_cards(
        {
            "asset_type": "company",
            "valuation_snapshot": {"status": "calculated"},
            "valuation_readiness": {"price_ready": True, "dcf_ready": True, "peer_ready": False},
            "missing_data_warnings": ["Peers missing"],
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["MODE", "SUPPORTED", "WITHHELD", "NEXT REVIEW", "DATA CONFIDENCE"]
    assert "evaluation mode" in rendered
    assert "standalone dcf review" in rendered
    assert "what this report can support" in rendered
    assert "standalone dcf assumptions" in rendered
    assert "what remains withheld" in rendered
    assert "peer-relative valuation remains withheld" in rendered
    assert "best next review step" in rendered
    assert "review the dcf assumptions first" in rendered
    assert "missing inputs reduce data confidence" in rendered
    next_card = next(card for card in cards if card["kicker"] == "NEXT REVIEW")
    assert next_card["command"] == "make focus-peers TICKER=NVDA"
    assert "copy-only" in next_card["badges"]
    assert "research-only" in rendered
    assert "data-gated" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_evaluation_summary_cards_route_next_review_command_by_mode():
    peer_locked_cards = dashboard.stock_report_evaluation_summary_cards(
        {
            "ticker": "NVDA",
            "asset_type": "company",
            "valuation_snapshot": {"status": "calculated"},
            "valuation_readiness": {"price_ready": True, "dcf_ready": True, "peer_ready": False},
            "missing_data_warnings": ["Peers missing"],
        }
    )
    fundamentals_cards = dashboard.stock_report_evaluation_summary_cards(
        {
            "ticker": "META",
            "asset_type": "company",
            "valuation_snapshot": {"status": "insufficient_data"},
            "valuation_readiness": {"price_ready": True, "dcf_ready": False, "peer_ready": False},
            "missing_data_warnings": ["Fundamentals missing"],
        }
    )
    etf_cards = dashboard.stock_report_evaluation_summary_cards(
        {
            "ticker": "QQQ",
            "asset_type": "etf",
            "valuation_snapshot": {"status": "excluded"},
            "valuation_readiness": {"price_ready": True, "dcf_ready": False, "peer_ready": False},
            "missing_data_warnings": ["DCF excluded"],
        }
    )
    price_cards = dashboard.stock_report_evaluation_summary_cards(
        {
            "ticker": "APLD",
            "asset_type": "company",
            "valuation_snapshot": {"status": "insufficient_data"},
            "valuation_readiness": {"price_ready": False, "dcf_ready": False, "peer_ready": False},
            "missing_data_warnings": ["Price history missing"],
        }
    )

    def next_command(cards: list[dict[str, object]]) -> str:
        return str(next(card for card in cards if card["kicker"] == "NEXT REVIEW")["command"])

    assert next_command(peer_locked_cards) == "make focus-peers TICKER=NVDA"
    assert next_command(fundamentals_cards) == "make focus-fundamentals TICKER=META"
    assert next_command(etf_cards) == "make stock-report-md TICKER=QQQ"
    assert next_command(price_cards) == "make focus-price TICKER=APLD"

    rendered = " ".join(
        str(value)
        for cards in (peer_locked_cards, fundamentals_cards, etf_cards, price_cards)
        for card in cards
        for value in card.values()
    ).lower()
    assert "copy-only" in rendered
    assert "peer-relative valuation remains withheld" in rendered
    assert "company valuation remains blocked" in rendered
    assert "operating-company dcf and peer valuation are excluded" in rendered
    assert "price coverage starts" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_at_a_glance_cards_match_markdown_report_flow():
    payload = {
        "ticker": "META",
        "asset_type": "company",
        "valuation_snapshot": {"status": "insufficient_data", "dcf_result": {"status": "insufficient_data"}},
        "valuation_readiness": {
            "price_ready": True,
            "dcf_ready": False,
            "peer_ready": False,
            "earnings_available": False,
            "analyst_estimates_available": False,
        },
        "missing_data_warnings": ["Fundamentals missing"],
    }
    coverage = pd.DataFrame(
        [
            {"dataset": "prices", "ticker_present": True},
            {"dataset": "fundamentals", "ticker_present": False, "target_file": "data/fundamentals.csv"},
            {"dataset": "peers", "ticker_present": False, "target_file": "data/peers.csv"},
        ]
    )

    cards = dashboard.stock_report_at_a_glance_cards(payload, coverage, {"peer_dataset_present": False})
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "AT A GLANCE",
        "VALUATION STATE",
        "WITHHELD",
        "METHOD",
        "NEXT LOCAL STEP",
    ]
    assert cards[0]["title"] == "Price/setup review only"
    assert "price/setup review and missing-data diagnosis" in rendered
    assert "dcf: insufficient data" in rendered
    assert "peer context: locked until trusted peer inputs are ready" in rendered
    assert "optional context: locked until trusted optional rows exist" in rendered
    assert "what not to infer" in rendered
    assert "company valuation remains blocked" in rendered
    assert "project gates and dcf math" in rendered
    assert "what this means" in rendered
    assert "source rows supply data" in rendered
    assert "projected cash flows" in rendered
    assert "discounted terminal value" in rendered
    assert "fair value per share" in rendered
    assert "stays locked instead of becoming a weak conclusion" in rendered
    assert cards[-1]["command"] == "make focus-fundamentals TICKER=META"
    assert "copy the command" in rendered
    assert "copy-only" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_mode_guide_cards_compare_all_modes_and_mark_current():
    cards = dashboard.stock_report_mode_guide_cards(
        {
            "asset_type": "company",
            "valuation_snapshot": {"status": "calculated"},
            "valuation_readiness": {"price_ready": True, "dcf_ready": True, "peer_ready": False},
            "missing_data_warnings": ["Peers missing"],
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 5
    assert [card["title"] for card in cards] == [
        "DCF-ready review",
        "Standalone DCF review",
        "Price/setup review only",
        "Monitor-only context",
        "Data-unlock only",
    ]
    assert cards[1]["kicker"] == "CURRENT MODE"
    assert cards[1]["badges"] == ["current"]
    assert "company dcf can be reviewed, but peer-relative valuation remains blocked" in rendered
    assert "operating-company dcf is excluded, not failed" in rendered
    assert "reference state for tickers with no trusted local inputs yet" in rendered
    assert "pause analysis for this ticker" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_mode_guide_cards_use_strict_copy_for_current_data_unlock_mode():
    cards = dashboard.stock_report_mode_guide_cards(
        {
            "asset_type": "company",
            "valuation_snapshot": {"status": "blocked"},
            "valuation_readiness": {"price_ready": False, "dcf_ready": False, "peer_ready": False},
            "missing_data_warnings": ["No local price rows were found."],
        }
    )
    current_cards = [card for card in cards if card["kicker"] == "CURRENT MODE"]

    assert len(current_cards) == 1
    assert current_cards[0]["title"] == "Data-unlock only"
    assert current_cards[0]["body"] == "Pause analysis for this ticker until the first trusted local input is available."


def test_stock_report_function_quality_frame_explains_current_function_scope_and_source():
    frame = dashboard.stock_report_function_quality_frame(
        {
            "asset_type": "company",
            "price_snapshot": {"price": 100.0},
            "performance": {"one_month": 0.12},
            "financial_summary": {"free_cash_flow": 10_000_000, "shares_outstanding": 1_000_000},
            "valuation_snapshot": {"status": "calculated"},
            "valuation_readiness": {"peer_ready": False, "earnings_available": False, "analyst_estimates_available": False},
        }
    )
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert list(frame.columns) == ["Function", "Current Status", "What To Trust"]
    assert "readiness gate" in rendered
    assert "strongest layer" in rendered
    assert "price / setup" in rendered
    assert "ready for local trend/setup review" in rendered
    assert "fundamentals / dcf" in rendered
    assert "ready for standalone dcf assumptions and sensitivity review" in rendered
    assert "peer comparison" in rendered
    assert "blocked until source-backed peer mappings" in rendered
    assert "logic source" in rendered
    assert "project rules" in rendered
    assert "shipped analysis comes from project code and local data" in rendered
    assert "source rows provide inputs" in rendered
    assert "what can be analyzed now and what remains locked" in rendered
    assert "plugins can help development review" not in rendered
    assert "no open source was used" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_methodology_frame_explains_steps_and_dcf_gate():
    frame = dashboard.stock_report_methodology_frame(
        {
            "asset_type": "company",
            "price_snapshot": {"price": 100.0},
            "performance": {"one_month": 0.12},
            "financial_summary": {"revenue": 100_000_000, "free_cash_flow": 10_000_000, "shares_outstanding": 1_000_000},
            "valuation_snapshot": {"status": "calculated"},
            "valuation_readiness": {"dcf_ready": True, "peer_ready": False},
        }
    )
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert list(frame.columns) == ["Step", "Method", "Plain Meaning"]
    assert "1. readiness gate" in rendered
    assert "2. fundamental review" in rendered
    assert "3. dcf calculation" in rendered
    assert "base fcf" in rendered
    assert "discounted terminal value" in rendered
    assert "fair value per share" in rendered
    assert "4. peer context" in rendered
    assert "blocked until source-backed peer mappings" in rendered
    assert "5. report explanation" in rendered
    assert "explained instead of filled" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_function_quality_frame_infers_etf_monitor_context_from_screener_context():
    frame = dashboard.stock_report_function_quality_frame(
        {
            "ticker": "QQQ",
            "price_snapshot": {"price": 570.0},
            "performance": {"one_month": 0.08},
            "financial_summary": {},
            "valuation_snapshot": {"status": "insufficient_data"},
            "valuation_readiness": {"peer_ready": False},
            "screener_context": {
                "purpose_classification": {
                    "finalprimarypurpose": "ETF / Defensive / Hedge",
                    "theme": "Nasdaq 100 ETF",
                }
            },
        }
    )
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert dashboard.stock_report_inferred_asset_type(
        {
            "screener_context": {
                "purpose_classification": {
                    "finalprimarypurpose": "ETF / Defensive / Hedge",
                    "theme": "Nasdaq 100 ETF",
                }
            }
        }
    ) == "etf"
    assert "excluded for etf/index/fund monitor context, not failed" in rendered
    assert "peer comparison" in rendered
    assert "excluded for monitor context" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_valuation_workflow_guidance_cards_explain_ready_blocked_and_excluded_states():
    cards = dashboard.valuation_workflow_guidance_cards(23, 3513, 2)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Use only ready valuation rows"
    assert "23 company row(s) currently have dcf-ready inputs" in rendered
    assert "blocked rows are not weak valuation calls" in rendered
    assert "trusted price, fundamentals, free cash flow or margin" in rendered
    assert "operating-company dcf is excluded rather than failed" in rendered
    assert "make sec-stage-queue top_n=25" in rendered
    assert "make stock-report-md ticker=qqq" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_valuation_plain_language_cards_explain_ready_locked_and_excluded_states():
    ready = pd.DataFrame({"ticker": ["NVDA", "A"]})
    blocked = pd.DataFrame({"ticker": ["META", "AMD", "COHR", "APLD"]})
    excluded = pd.DataFrame({"ticker": ["QQQ", "SMH"]})

    cards = dashboard.valuation_plain_language_cards(ready, blocked, excluded)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "WHAT THIS MEANS",
        "WHAT YOU CAN ANALYZE NOW",
        "WHAT IS STILL LOCKED",
        "WHAT IS EXCLUDED",
    ]
    assert "2 ready / 4 locked / 2 excluded" in rendered
    assert "readiness-gated valuation page" in rendered
    assert "dcf-ready examples: nvda, a" in rendered
    assert "review dcf assumptions, scenario math, sensitivity, and source freshness" in rendered
    assert "peer trend is a separate context layer when mapped peer price history is ready" in rendered
    assert "peer valuation stays locked until source-backed peer valuation inputs pass readiness" in rendered
    assert "locked examples: meta, amd, cohr +1 more" in rendered
    assert "company valuation stays locked until trusted price, fundamentals" in rendered
    assert "missing inputs are not negative signals" in rendered
    assert "monitor examples: qqq, smh" in rendered
    assert "operating-company dcf is excluded, not failed" in rendered
    assert cards[1]["command"] == "make stock-report-md TICKER=NVDA"
    assert cards[2]["command"] == "make focus-fundamentals TICKER=META"
    assert cards[3]["command"] == "make stock-report-md TICKER=QQQ"
    assert "make focus-fundamentals ticker=meta" in rendered
    assert "make stock-report-md ticker=qqq" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_value_re_rating_page_uses_context_not_ready_conclusion_language():
    source = Path("src/dashboard.py").read_text(encoding="utf-8").lower()

    assert "value / re-rating at a glance" in source
    assert "what you can analyze now" in source
    assert "what is still locked" in source
    assert "valuation method path" in source
    assert "intrinsic vs relative value" in source
    assert "where standalone dcf ends, where peer valuation begins" in source
    assert "valuation_boundary_explainer_cards()" in source
    assert "how source rows become dcf context without becoming a hidden conclusion" in source
    assert "valuation_method_path_cards()" in source
    assert "operating-company valuation context is shown only for dcf-ready companies" in source
    assert "instead of showing ranked valuation context" in source
    assert "operating-company valuation conclusions are shown only for dcf-ready companies" not in source


def test_valuation_legacy_output_note_explains_compatibility_filename():
    note = dashboard.valuation_legacy_output_note().lower()

    assert "outputs/undervalued_candidates.csv" in note
    assert "legacy filename" in note
    assert "valuation-readiness and re-rating context" in note
    assert "not an automatic undervalued-stock list" in note
    assert "missing trusted inputs remain blocked" in note
    assert "broker" not in note
    assert "order" not in note
    assert "trading" not in note
    assert "buy" not in note
    assert "sell" not in note


def test_valuation_legacy_diagnostic_frame_adds_reader_boundary_to_raw_values():
    frame = pd.DataFrame(
        {
            "Ticker": ["NVDA", "META", "APLD"],
            "ValuationStatus": ["ready", "not_ready", "ready"],
            "FinalValueCategory": ["Watch", "Insufficient Data", "Avoid"],
            "MissingDataFields": ["", "shares_outstanding", "free_cash_flow"],
            "Reason": ["Ready row.", "Missing shares.", "Missing FCF."],
        }
    )

    diagnostic = dashboard.valuation_legacy_diagnostic_frame(frame)
    rendered = " ".join(diagnostic.astype(str).to_numpy().flatten()).lower()

    assert "ReaderBoundary" in diagnostic.columns
    assert diagnostic.loc[diagnostic["Ticker"].eq("NVDA"), "ReaderBoundary"].iloc[0].startswith("Ready-row context only")
    assert "no valuation conclusion; compatibility fields stay blocked" in rendered
    assert diagnostic.loc[diagnostic["Ticker"].eq("META"), "ReaderBoundary"].iloc[0].startswith("No valuation conclusion")
    assert diagnostic.loc[diagnostic["Ticker"].eq("APLD"), "ReaderBoundary"].iloc[0].startswith("No valuation conclusion")
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_valuation_decision_guide_cards_turn_operator_table_into_plain_language():
    ready = pd.DataFrame({"ticker": ["NVDA"]})
    blocked = pd.DataFrame(
        {
            "ticker": ["AMD", "META"],
            "missing_dcf_fields": ["free_cash_flow, shares_outstanding", "free_cash_flow"],
        }
    )
    excluded = pd.DataFrame({"ticker": ["QQQ"]})

    cards = dashboard.valuation_decision_guide_cards(ready, blocked, excluded)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["READY TO REVIEW", "LOCKED BY DATA", "MONITOR ONLY"]
    assert "1 dcf-ready review" in rendered
    assert "examples: nvda" in rendered
    assert "assumptions, scenarios, and sensitivity as research context" in rendered
    assert "unsupported recommendations and allocation instructions remain withheld" in rendered
    assert "2 locked by missing inputs" in rendered
    assert "examples: amd, meta" in rendered
    assert "company valuation is locked until missing inputs are filled" in rendered
    assert "free_cash_flow" in rendered
    assert "no undervalued or overvalued conclusion is shown" in rendered
    assert "1 monitor-only context" in rendered
    assert "examples: qqq" in rendered
    assert "support market, theme, liquidity, or risk monitoring" in rendered
    assert "operating-company dcf is excluded, not failed" in rendered
    assert "make dcf-readiness" in rendered
    assert "make sec-stage-queue top_n=25" in rendered
    assert "make stock-report-md ticker=qqq" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_valuation_quick_read_cards_prioritize_ready_dcf_review_without_overclaiming():
    ready = pd.DataFrame({"ticker": ["NVDA"]})
    blocked = pd.DataFrame({"ticker": ["META"], "missing_dcf_fields": ["free_cash_flow"]})
    excluded = pd.DataFrame({"ticker": ["QQQ"], "asset_type": ["etf"]})

    cards = dashboard.valuation_quick_read_cards(ready, blocked, excluded)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["FIRST READ", "ANALYZE NOW", "STILL LOCKED", "EXCLUDED"]
    assert cards[0]["title"] == "Review DCF-ready companies first"
    assert cards[0]["command"] == "make stock-report-md TICKER=NVDA"
    assert cards[1]["command"] == "make stock-report-md TICKER=NVDA"
    assert cards[2]["command"] == "make focus-fundamentals TICKER=META"
    assert cards[3]["command"] == "make stock-report-md TICKER=QQQ"
    assert "start with nvda" in rendered
    assert "assumption, scenario, sensitivity, and source/freshness review" in rendered
    assert "not price targets" in rendered
    assert "1 dcf-ready company row(s)" in rendered
    assert "open nvda for dcf assumptions" in rendered
    assert "peer trend can be reviewed only when mapped peer price history is ready" in rendered
    assert "peer-relative valuation still needs trusted peer valuation inputs" in rendered
    assert "1 company row(s) need inputs" in rendered
    assert "for meta, fair value/share" in rendered
    assert "free cash flow pass readiness" in rendered
    assert "fair value/share, intrinsic-value interpretation, and re-rating context" in rendered
    assert "1 etf/index/fund row(s)" in rendered
    assert "qqq use monitor context because operating-company dcf does not apply" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_valuation_quick_read_cards_prioritize_missing_inputs_when_no_ready_rows():
    cards = dashboard.valuation_quick_read_cards(
        pd.DataFrame(),
        pd.DataFrame({"ticker": ["META"], "missing_dcf_fields": ["free_cash_flow, shares_outstanding"]}),
        pd.DataFrame({"ticker": ["QQQ"], "asset_type": ["etf"]}),
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Fix missing valuation inputs first"
    assert cards[0]["command"] == "make focus-fundamentals TICKER=META"
    assert cards[1]["title"] == "0 DCF-ready company row(s)"
    assert cards[1]["command"] == "make dcf-readiness"
    assert cards[2]["command"] == "make focus-fundamentals TICKER=META"
    assert "start with meta" in rendered
    assert "no operating-company dcf assumptions or sensitivity should be reviewed yet" in rendered
    assert "use the locked-input and monitor-context cards until trusted dcf rows exist" in rendered
    assert "open the next dcf-ready ticker" not in rendered
    assert "free cash flow, shares outstanding" in rendered
    assert "until free cash flow, shares outstanding pass readiness" in rendered
    assert "missing inputs are not undervalued, overvalued, or weak-company conclusions" in rendered


def test_valuation_quick_read_cards_keep_etf_rows_monitor_only_when_no_company_rows():
    cards = dashboard.valuation_quick_read_cards(
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame({"ticker": ["QQQ"], "asset_type": ["etf"]}),
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Use monitor context only"
    assert cards[0]["command"] == "make stock-report-md TICKER=QQQ"
    assert cards[1]["title"] == "0 DCF-ready company row(s)"
    assert cards[1]["command"] == "make dcf-readiness"
    assert cards[3]["command"] == "make stock-report-md TICKER=QQQ"
    assert "start with qqq" in rendered
    assert "no operating-company dcf assumptions or sensitivity should be reviewed yet" in rendered
    assert "open the next dcf-ready ticker" not in rendered
    assert "qqq use monitor context because operating-company dcf does not apply" in rendered
    assert "operating-company dcf is excluded, not failed" in rendered
    assert "monitor only" in rendered


def test_valuation_quick_read_cards_handle_missing_readiness_without_fake_counts():
    cards = dashboard.valuation_quick_read_cards(None, None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Generate DCF readiness first"
    assert cards[0]["command"] == "make dcf-readiness"
    assert "no valuation readiness rows are loaded" in rendered
    assert "current-only and blocked" in rendered


def test_valuation_function_quality_cards_explain_supported_scope_without_overclaiming():
    ready = pd.DataFrame({"ticker": ["NVDA"]})
    blocked = pd.DataFrame({"ticker": ["AMD", "META"]})
    excluded = pd.DataFrame({"ticker": ["QQQ"]})

    cards = dashboard.valuation_function_quality_cards(ready, blocked, excluded)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["VALUATION QUALITY", "BLOCKED IS NOT NEGATIVE", "MONITOR CONTEXT", "PEER VALUATION"]
    assert "dcf is useful only for ready companies" in rendered
    assert "1 company row(s) have enough trusted local dcf inputs" in rendered
    assert "research context, not a recommendation" in rendered
    assert "2 company row(s) still need inputs" in rendered
    assert "missing-data state" in rendered
    assert "not an undervalued, overvalued, or weak-company conclusion" in rendered
    assert "operating-company dcf is intentionally excluded" in rendered
    assert "separate from standalone dcf" in rendered
    assert "dcf-ready company can still have peer-relative valuation withheld" in rendered
    assert "source-backed peer mappings and peer valuation inputs are ready" in rendered
    assert "make peer-mapping-queue top_n=10" in rendered
    assert "make sec-stage-queue top_n=25" in rendered
    assert "make stock-report-md ticker=qqq" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_valuation_function_quality_frame_explains_scope_counts_and_provenance():
    ready = pd.DataFrame({"ticker": ["NVDA"]})
    blocked = pd.DataFrame({"ticker": ["AMD", "META"]})
    excluded = pd.DataFrame({"ticker": ["QQQ", "SMH"]})

    frame = dashboard.valuation_function_quality_frame(ready, blocked, excluded)
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert list(frame.columns) == [
        "Valuation Area",
        "Quality Verdict",
        "Best Use Today",
        "Current Coverage",
        "Supported Today",
        "Not Supported Yet",
        "Logic Source",
    ]
    assert "dcf-ready companies" in rendered
    assert "good for dcf-ready companies only" in rendered
    assert "review assumptions, scenarios, and sensitivity with trusted local inputs" in rendered
    assert "1 row(s)" in rendered
    assert "reviewing assumptions, scenarios, and sensitivity" in rendered
    assert "blocked companies" in rendered
    assert "not valuation-ready" in rendered
    assert "use as a missing-input worklist" in rendered
    assert "2 row(s)" in rendered
    assert "finding the exact missing data" in rendered
    assert "calling a company undervalued, overvalued, or weak" in rendered
    assert "etf / index / fund rows" in rendered
    assert "good for monitor context only" in rendered
    assert "2 row(s)" in rendered
    assert "operating-company dcf or peer valuation" in rendered
    assert "peer-relative valuation" in rendered
    assert "coverage-limited until peers are trusted" in rendered
    assert "source-backed peer mappings and peer metrics" in rendered
    assert "guessed peer relationships" in rendered
    assert "dependencies" in rendered
    assert "support layer, not valuation logic" in rendered
    assert "support layer only" in rendered
    assert "valuation rules live in this repository" in rendered
    assert "replacing project valuation rules or trusted local valuation inputs" in rendered
    assert "no open source was used" not in rendered
    assert "100% original" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_valuation_method_path_cards_explain_dcf_without_black_box_language():
    cards = dashboard.valuation_method_path_cards()
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["METHOD PATH", "DCF MATH", "RELATIVE VALUE", "OUTPUT BOUNDARY"]
    assert "inputs before valuation" in rendered
    assert "trusted local price and company fundamentals" in rendered
    assert "missing free cash flow, margin, shares, or price keeps valuation locked" in rendered
    assert "fcf -> discounted value -> fair value/share" in rendered
    assert "revenue times fcf margin" in rendered
    assert "growth, wacc" in rendered
    assert "terminal growth" in rendered
    assert "cash/debt adjustment" in rendered
    assert "peer valuation is separate" in rendered
    assert "standalone dcf can be ready while peer-relative valuation stays locked" in rendered
    assert "source-backed peer mappings" in rendered
    assert "context, not a conclusion" in rendered
    assert "blocked rows withhold valuation" in rendered
    assert "operating-company dcf is excluded, not failed" in rendered
    assert "make stock-report-md ticker=nvda" in rendered
    assert "make peer-mapping-queue top_n=10" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_valuation_boundary_explainer_cards_separate_intrinsic_relative_and_excluded():
    cards = dashboard.valuation_boundary_explainer_cards()
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["INTRINSIC VALUE", "RELATIVE VALUE", "LOCKED OR EXCLUDED"]
    assert "standalone dcf is local scenario math" in rendered
    assert "project free cash flow" in rendered
    assert "discount those cash flows and terminal value" in rendered
    assert "adjust for cash/debt" in rendered
    assert "assumption review, not a final call" in rendered
    assert "peer valuation is a separate gate" in rendered
    assert "source-backed peer mappings and peer valuation inputs" in rendered
    assert "dcf-ready stock can still be peer-blocked" in rendered
    assert "missing data is not a valuation opinion" in rendered
    assert "operating-company dcf is excluded, not failed" in rendered
    assert "make stock-report-md ticker=nvda" in rendered
    assert "make peer-mapping-queue top_n=10" in rendered
    assert "make stock-report-md ticker=qqq" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_valuation_method_contract_frame_makes_dcf_formula_auditable_without_overclaiming():
    frame = dashboard.valuation_method_contract_frame()
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert list(frame.columns) == ["Step", "Plain Meaning", "Required Local Fields", "Output Boundary"]
    assert frame["Step"].tolist() == [
        "Input contract",
        "Base cash flow",
        "Scenario projection",
        "Fair value math",
        "ETF / fund boundary",
    ]
    assert "trusted local price and company fundamentals" in rendered
    assert "price, revenue, free cash flow or fcf margin, shares outstanding" in rendered
    assert "free_cash_flow, or revenue plus fcf_margin" in rendered
    assert "bear, base, and bull scenarios project fcf" in rendered
    assert "discounted" in rendered
    assert "adjusted for cash/debt or net debt" in rendered
    assert "divided by shares outstanding" in rendered
    assert "peer-relative valuation remains separate" in rendered
    assert "dcf is excluded, not failed" in rendered
    assert "price target or direct recommendation" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_orientation_cards_frame_unlock_workflow_without_execution_language():
    cards = dashboard.data_health_orientation_cards(
        {
            "price_ready": 586,
            "fundamentals_ready": 23,
            "dcf_ready": 23,
            "peer_ready": 3,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "WHAT THIS MEANS",
        "WHAT YOU CAN ANALYZE NOW",
        "WHAT IS STILL LOCKED",
    ]
    assert cards[0]["title"] == "Use this page to unlock analysis"
    assert "not an error page" in rendered
    assert "what you can analyze now" in rendered
    assert "what is still locked" in rendered
    assert "what this means" in rendered
    assert "586 price-ready / 23 fundamentals-ready / 23 dcf-ready" in rendered
    assert "price coverage unlocks setup review first" in rendered
    assert "trusted fundamentals unlock company-level valuation" in rendered
    assert "3 peer-ready / 0 earnings / 0 estimates" in rendered
    assert "the app does not infer these inputs" in rendered
    assert "make status-check top_n=5" in rendered
    assert "make templates" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_quick_read_cards_prioritize_first_unlock_lane_without_execution_language():
    cards = dashboard.data_health_quick_read_cards(
        {
            "price_ready": 240,
            "fundamentals_ready": 23,
            "dcf_ready": 23,
            "peer_ready": 3,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["FIRST READ", "ANALYZE NOW", "STILL LOCKED"]
    assert cards[0]["title"] == "Unlock fundamentals before valuation"
    assert cards[0]["command"] == "make sec-stage-queue TOP_N=25"
    assert "217 price-ready row(s) still need trusted fundamentals" in rendered
    assert "not a negative company signal" in rendered
    assert "inspect the queue first" in rendered
    assert "trusted manual rows only when sources are ready" in rendered
    assert "240 price / 23 dcf / 3 peer-ready" in rendered
    assert "what you can analyze now" in rendered
    assert "assumption and sensitivity review" in rendered
    assert "do not read locked sections as weak conclusions" in rendered
    assert "0 earnings / 0 estimates" in rendered
    assert "what is still locked" in rendered
    assert "missing optional rows are not hidden analysis" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_quick_read_cards_switch_to_peer_unlock_when_dcf_ready_outpaces_peers():
    cards = dashboard.data_health_quick_read_cards(
        {
            "price_ready": 25,
            "fundamentals_ready": 25,
            "dcf_ready": 25,
            "peer_ready": 4,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Add trusted peers for DCF-ready names"
    assert cards[0]["command"] == "make peer-mapping-queue TOP_N=10"
    assert "21 dcf-ready row(s) still have peer-relative valuation locked" in rendered
    assert "peer premium/discount stays withheld" in rendered
    assert "peer valuation inputs exist" in rendered
    assert "source-backed peer rows" in rendered


def test_data_health_quick_read_cards_keep_optional_context_locked_after_core_lanes():
    cards = dashboard.data_health_quick_read_cards(
        {
            "price_ready": 10,
            "fundamentals_ready": 10,
            "dcf_ready": 10,
            "peer_ready": 10,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Optional context is intentionally locked"
    assert cards[0]["command"] == "make optional-context-worklist TOP_N=10"
    assert "empty optional coverage should not weaken ready price, dcf, or peer analysis" in rendered


def test_data_health_quick_read_cards_start_with_price_when_no_price_ready_rows():
    cards = dashboard.data_health_quick_read_cards({"price_ready": 0, "dcf_ready": 0, "peer_ready": 0})
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Start with trusted price coverage"
    assert cards[0]["command"] == "make price-refresh-loop DRY_RUN=1"
    assert "no price-ready rows means setup, dcf, peer, earnings, and estimate analysis should stay locked" in rendered
    assert "scalable dry run first" in rendered
    assert "instead of repeating 25-ticker refreshes by hand" in rendered
    assert "make stock-report ticker" not in rendered


def test_data_health_analysis_unlock_cards_map_data_lanes_to_supported_analysis():
    cards = dashboard.data_health_analysis_unlock_cards(
        {
            "price_ready": 586,
            "dcf_ready": 23,
            "peer_ready": 3,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["PRICE UNLOCK", "DCF UNLOCK", "PEER UNLOCK", "OPTIONAL CONTEXT"]
    assert "586 price-ready" in rendered
    assert "function status: usable" in rendered
    assert "setup, trend, liquidity, and market-context review" in rendered
    assert "dry-run the capped refresh loop first" in rendered
    assert "instead of repeating small worklists by hand" in rendered
    assert "23 dcf-ready" in rendered
    assert "function status: good for dcf-ready companies only" in rendered
    assert "company-level assumptions and sensitivity review" in rendered
    assert "not automatic valuation conclusions" in rendered
    assert "3 peer-ready" in rendered
    assert "function status: workflow-ready but coverage-limited" in rendered
    assert "peer-relative context" in rendered
    assert "missing peers stay blocked instead of guessed" in rendered
    assert "0 earnings / 0 estimates" in rendered
    assert "function status: intentionally locked until trusted rows exist" in rendered
    assert "empty optional files are not a broken analysis path" in rendered
    assert "make price-refresh-loop dry_run=1" in rendered
    assert "make sec-stage-queue top_n=25" in rendered
    assert "make peer-mapping-queue top_n=10" in rendered
    assert "make optional-context-worklist top_n=10" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_supported_ladder_cards_explain_analysis_levels_without_overclaiming():
    cards = dashboard.data_health_supported_ladder_cards(
        {
            "price_ready": 586,
            "fundamentals_ready": 23,
            "dcf_ready": 23,
            "peer_ready": 3,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["LEVEL 1", "LEVEL 2", "LEVEL 3", "LEVEL 4"]
    assert "586 ready for setup review" in rendered
    assert "stop at setup/risk review if fundamentals are missing" in rendered
    assert "price/setup" in rendered
    assert "not valuation" in rendered
    assert "23 fundamentals / 23 dcf-ready" in rendered
    assert "assumption and sensitivity review" in rendered
    assert "valuation stays locked, not negative or weak" in rendered
    assert "3 ready for peer context" in rendered
    assert "source-backed peer mappings and peer metrics" in rendered
    assert "sector fallback is not trusted peer valuation" in rendered
    assert "0 earnings / 0 estimates" in rendered
    assert "locked instead of producing unsupported conclusions" in rendered
    assert "make stock-report-md ticker=nvda" in rendered
    assert "make stock-report ticker=nvda" not in rendered
    assert "make dcf-readiness" in rendered
    assert "make peer-mapping-queue top_n=10" in rendered
    assert "make optional-context-worklist top_n=10" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_valuation_unlock_snapshot_surfaces_fundamentals_and_peer_queues():
    readiness = pd.DataFrame(
        [
            {
                "ticker": "A",
                "asset_type": "company",
                "price_ready": True,
                "fundamentals_ready": True,
                "dcf_ready": True,
                "peer_ready": False,
                "in_active_universe": True,
            },
            {
                "ticker": "CRDO",
                "asset_type": "company",
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "in_active_universe": True,
            },
            {
                "ticker": "BROAD",
                "asset_type": "company",
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "in_active_universe": False,
            },
            {
                "ticker": "NVDA",
                "asset_type": "company",
                "price_ready": True,
                "fundamentals_ready": True,
                "dcf_ready": True,
                "peer_ready": True,
                "in_active_universe": True,
            },
            {
                "ticker": "QQQ",
                "asset_type": "etf",
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "in_active_universe": True,
            },
        ]
    )
    cards = dashboard.data_health_valuation_unlock_snapshot_cards(
        readiness,
        {
            "price_ready": 5,
            "dcf_ready": 2,
            "peer_ready": 1,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        },
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "WHAT YOU CAN ANALYZE NOW",
        "FUNDAMENTALS STILL LOCKED",
        "PEER VALUATION STILL LOCKED",
        "OPTIONAL / EXCLUDED CONTEXT",
    ]
    assert "5 setup / 2 dcf / 1 peer" in rendered
    assert "2 price-ready companies" in rendered
    assert "1 active-universe row(s) already have price coverage" in rendered
    assert "data/imports/fundamentals.csv" in rendered
    assert "validate, preview, and apply" in rendered
    assert "do not treat missing fundamentals as a negative company signal" in rendered
    assert "1 dcf-ready company" in rendered
    assert "data/imports/peers.csv" in rendered
    assert "source-backed mappings" in rendered
    assert "run validate, preview, apply before peer valuation appears" in rendered
    assert "standalone dcf can be reviewed without pretending peer valuation is ready" in rendered
    assert "0 earnings / 0 estimates / 1 monitor proxies" in rendered
    assert "operating-company dcf is excluded, not failed" in rendered
    assert "make focus-fundamentals ticker=crdo" in rendered
    assert "make focus-peers ticker=a" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_valuation_unlock_snapshot_handles_missing_readiness_without_fake_counts():
    cards = dashboard.data_health_valuation_unlock_snapshot_cards(None, {"price_ready": 5, "dcf_ready": 2})
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 1
    assert "readiness report not loaded" in rendered
    assert "missing readiness output means analysis should stay current-only and blocked" in rendered
    assert "make readiness" in rendered


def test_data_health_page_header_frames_unlock_workflow_not_diagnostics():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")

    assert "See what trusted local inputs are ready, what analysis is still locked, and which safe unlock workflow to copy next." in source
    assert "Data Health Quick Read" in source
    assert "Which unlock lane should you inspect first, before opening detailed tables." in source
    assert "Supported Analysis Ladder" in source
    assert "Valuation Unlock Snapshot" in source
    assert "Plain-English valuation queues before the full command center details." in source
    assert "When Is A Stock Ready Enough?" not in source
    assert "Validation, source availability, price refresh diagnostics, and onboarding actions in one place." not in source


def test_data_health_page_does_not_block_initial_render_on_project_status_build():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")

    assert 'if selected_page == "Overview":' in source
    assert 'if selected_page in {"Overview", "Data Health"}:' not in source
    assert "Data Health is using saved local results first so the page stays responsive" in source
    assert "Copy `make project-status` when you want to refresh the next-step summary" in source
    assert "rendering from existing local CSV outputs" not in source
    assert "separate project-status summary files" not in source


def test_stock_report_local_context_cards_summarize_local_and_peer_readiness():
    coverage = pd.DataFrame(
        [
            {"ticker_present": True, "validation_status": "valid"},
            {"ticker_present": True, "validation_status": "valid_with_warnings"},
            {"ticker_present": False, "validation_status": "missing_file"},
        ]
    )
    peer_summary = {
        "peer_dataset_present": False,
        "peer_count": 0,
        "peer_fundamentals_available": 0,
        "peer_market_context_available": 1,
    }

    cards = dashboard.stock_report_local_context_cards(coverage, peer_summary)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 4
    assert "2 available" in rendered
    assert "missing" in rendered
    assert "no fabrication" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_local_context_cards_show_staged_peer_import_state():
    coverage = pd.DataFrame(
        [
            {
                "dataset": "peers",
                "ticker_present": True,
                "validation_status": "valid",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )
    peer_summary = {
        "peer_dataset_present": False,
        "peer_count": 2,
        "peer_fundamentals_available": 0,
        "peer_market_context_available": 0,
    }

    cards = dashboard.stock_report_local_context_cards(coverage, peer_summary)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "staged" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    peer_mapping_card = next(card for card in cards if card["kicker"] == "PEER MAPPING")
    assert peer_mapping_card["command"] == "make imports-validate"
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_local_context_cards_use_peer_front_door_when_commands_are_missing():
    coverage = pd.DataFrame(
        [
            {
                "dataset": "peers",
                "ticker": "NVDA",
                "ticker_present": False,
                "validation_status": "valid_with_warnings",
                "focus_command": "",
                "example_command": "",
            }
        ]
    )
    peer_summary = {
        "peer_dataset_present": False,
        "peer_count": 0,
        "peer_fundamentals_available": 0,
        "peer_market_context_available": 0,
    }

    cards = dashboard.stock_report_local_context_cards(coverage, peer_summary)
    peer_mapping_card = next(card for card in cards if card["kicker"] == "PEER MAPPING")

    assert peer_mapping_card["title"] == "Missing"
    assert peer_mapping_card["command"] == "make focus-peers TICKER=NVDA"


def test_stock_report_local_context_cards_use_staged_peer_front_door_when_commands_are_missing():
    coverage = pd.DataFrame(
        [
            {
                "dataset": "peers",
                "ticker": "NVDA",
                "ticker_present": True,
                "validation_status": "valid",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )
    peer_summary = {
        "peer_dataset_present": False,
        "peer_count": 2,
        "peer_fundamentals_available": 0,
        "peer_market_context_available": 0,
    }

    cards = dashboard.stock_report_local_context_cards(coverage, peer_summary)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    peer_mapping_card = next(card for card in cards if card["kicker"] == "PEER MAPPING")

    assert peer_mapping_card["title"] == "Staged"
    assert peer_mapping_card["command"] == "make imports-validate"
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered


def test_stock_report_next_step_cards_prioritize_missing_prices_first():
    payload = {
        "ticker": "NVDA",
        "valuation_readiness": {
            "dcf_ready": False,
            "peer_ready": False,
            "earnings_available": False,
            "analyst_estimates_available": False,
        },
        "missing_data_warnings": ["prices missing"],
    }
    coverage = pd.DataFrame(
        [
            {"dataset": "prices", "ticker_present": False},
            {"dataset": "fundamentals", "ticker_present": False},
        ]
    )

    cards = dashboard.stock_report_next_step_cards(payload, coverage, {"peer_dataset_present": False})
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Fix price coverage"
    assert cards[-1]["title"] == "Locked"
    assert cards[-1]["command"] == "make templates"
    assert "make focus-price ticker=nvda" in rendered
    assert "missing optional context: earnings, analyst estimates" in rendered
    assert "lower priority" in rendered
    assert "data gaps" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_next_step_cards_route_to_fundamentals_then_peers_then_review():
    payload = {
        "ticker": "NVDA",
        "valuation_readiness": {
            "dcf_ready": False,
            "peer_ready": False,
            "earnings_available": False,
            "analyst_estimates_available": False,
        },
        "missing_data_warnings": ["fundamentals missing"],
    }
    coverage = pd.DataFrame(
        [
            {"dataset": "prices", "ticker_present": True},
            {"dataset": "fundamentals", "ticker_present": False},
        ]
    )
    cards = dashboard.stock_report_next_step_cards(payload, coverage, {"peer_dataset_present": False})
    assert cards[0]["title"] == "Stage fundamentals"
    assert cards[0]["command"] == "make focus-fundamentals TICKER=NVDA"

    coverage = pd.DataFrame(
        [
            {"dataset": "prices", "ticker_present": True},
            {
                "dataset": "fundamentals",
                "ticker_present": False,
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "target_file": "data/imports/fundamentals.csv",
            },
        ]
    )
    cards = dashboard.stock_report_next_step_cards(payload, coverage, {"peer_dataset_present": False})
    assert cards[0]["title"] == "Review fundamentals import draft"
    assert cards[0]["command"] == "make imports-validate"
    assert "fundamentals import drafts" in cards[0]["body"].lower()

    payload["valuation_readiness"]["dcf_ready"] = True
    coverage = pd.DataFrame(
        [
            {"dataset": "prices", "ticker_present": True},
            {"dataset": "fundamentals", "ticker_present": True},
        ]
    )
    cards = dashboard.stock_report_next_step_cards(payload, coverage, {"peer_dataset_present": False})
    assert cards[0]["title"] == "Add peer mappings"
    assert cards[0]["command"] == "make focus-peers TICKER=NVDA"

    coverage = pd.DataFrame(
        [
            {"dataset": "prices", "ticker_present": True},
            {"dataset": "fundamentals", "ticker_present": True},
            {
                "dataset": "peers",
                "ticker_present": True,
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "target_file": "data/imports/peers.csv",
            },
        ]
    )
    cards = dashboard.stock_report_next_step_cards(payload, coverage, {"peer_dataset_present": False})
    assert cards[0]["title"] == "Review peer import draft"
    assert cards[0]["command"] == "make imports-validate"
    assert "peer mapping import drafts" in cards[0]["body"].lower()

    payload["valuation_readiness"]["peer_ready"] = True
    cards = dashboard.stock_report_next_step_cards(payload, coverage, {"peer_dataset_present": True})
    assert cards[0]["title"] == "Review full report"
    assert cards[0]["command"] == "make stock-report-md TICKER=NVDA"
    assert cards[-1]["kicker"] == "OPTIONAL CONTEXT"
    assert cards[-1]["command"] == "make templates"


def test_stock_report_next_step_cards_keep_etf_reports_in_monitor_context():
    payload = {
        "ticker": "QQQ",
        "asset_type": "etf",
        "valuation_snapshot": {"status": "excluded"},
        "valuation_readiness": {
            "dcf_ready": False,
            "peer_ready": False,
            "earnings_available": False,
            "analyst_estimates_available": False,
        },
        "missing_data_warnings": ["DCF excluded for ETF monitor context."],
    }
    coverage = pd.DataFrame(
        [
            {"dataset": "prices", "ticker_present": True},
            {"dataset": "fundamentals", "ticker_present": False},
            {"dataset": "peers", "ticker_present": False},
        ]
    )

    cards = dashboard.stock_report_next_step_cards(payload, coverage, {"peer_dataset_present": False})
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Review ETF / market proxy"
    assert cards[0]["command"] == "make stock-report-md TICKER=QQQ"
    assert "operating-company dcf and peer-relative valuation are excluded" in rendered
    assert "stage fundamentals" not in rendered
    assert "add peer mappings" not in rendered
    assert "make focus-peers ticker=qqq" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_next_step_cards_use_payload_price_readiness_when_coverage_missing():
    etf_payload = {
        "ticker": "QQQ",
        "asset_type": "etf",
        "readiness": {"price_ready": True},
        "valuation_snapshot": {"status": "excluded"},
        "valuation_readiness": {
            "dcf_ready": False,
            "peer_ready": False,
            "earnings_available": False,
            "analyst_estimates_available": False,
        },
        "missing_data_warnings": ["DCF excluded for ETF monitor context."],
    }
    company_payload = {
        "ticker": "COHR",
        "readiness": {"price_ready": True},
        "valuation_snapshot": {"status": "ready"},
        "valuation_readiness": {
            "dcf_ready": True,
            "peer_ready": False,
            "earnings_available": False,
            "analyst_estimates_available": False,
        },
        "missing_data_warnings": ["peers: needs at least 2 source-backed peer mappings"],
    }

    etf_cards = dashboard.stock_report_next_step_cards(etf_payload, None, {"peer_dataset_present": False})
    company_cards = dashboard.stock_report_next_step_cards(company_payload, None, {"peer_dataset_present": False})
    rendered = " ".join(str(value) for card in etf_cards + company_cards for value in card.values()).lower()

    assert etf_cards[0]["title"] == "Review ETF / market proxy"
    assert etf_cards[0]["command"] == "make stock-report-md TICKER=QQQ"
    assert etf_cards[1]["badges"] == ["DCF excluded", "monitor context"]
    assert company_cards[0]["title"] == "Add peer mappings"
    assert company_cards[0]["command"] == "make focus-peers TICKER=COHR"
    assert company_cards[-1]["kicker"] == "OPTIONAL CONTEXT"
    assert "fix price coverage" not in rendered
    assert "make focus-price ticker=qqq" not in rendered
    assert "make focus-price ticker=cohr" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_next_step_cards_infer_price_ready_from_report_payload_without_coverage_table():
    payload = {
        "ticker": "NVDA",
        "asset_type": "company",
        "price_snapshot": {"price": 215.33, "volume": 168_346_300},
        "performance": {"one_month": 0.079, "three_month": 0.165},
        "financial_summary": {"revenue": 250_000_000_000, "free_cash_flow": 90_000_000_000, "shares_outstanding": 7_400_000_000},
        "valuation_snapshot": {"status": "calculated", "dcf_result": {"status": "calculated"}},
        "valuation_readiness": {
            "dcf_ready": True,
            "peer_ready": True,
            "earnings_available": False,
            "analyst_estimates_available": False,
        },
        "missing_data_warnings": ["earnings has no local row for this ticker.", "analyst estimates has no local row for this ticker."],
    }

    cards = dashboard.stock_report_next_step_cards(payload, None, {"peer_dataset_present": True})
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Review full report"
    assert cards[0]["command"] == "make stock-report-md TICKER=NVDA"
    assert cards[-1]["kicker"] == "OPTIONAL CONTEXT"
    assert "optional context" in rendered
    assert "trusted local csvs exist" in rendered
    assert "fix price coverage" not in rendered
    assert "make focus-price ticker=nvda" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_next_step_cards_use_staged_import_front_doors_when_commands_are_missing():
    payload = {
        "ticker": "NVDA",
        "valuation_readiness": {
            "dcf_ready": False,
            "peer_ready": False,
            "earnings_available": False,
            "analyst_estimates_available": False,
        },
        "missing_data_warnings": [],
    }
    coverage = pd.DataFrame(
        [
            {"dataset": "prices", "ticker_present": True},
            {
                "dataset": "fundamentals",
                "ticker_present": False,
                "target_file": "data/imports/fundamentals.csv",
            },
        ]
    )
    cards = dashboard.stock_report_next_step_cards(payload, coverage, {"peer_dataset_present": False})
    assert cards[0]["title"] == "Review fundamentals import draft"
    assert cards[0]["command"] == "make imports-validate"

    payload["valuation_readiness"]["dcf_ready"] = True
    coverage = pd.DataFrame(
        [
            {"dataset": "prices", "ticker_present": True},
            {"dataset": "fundamentals", "ticker_present": True},
            {
                "dataset": "peers",
                "ticker_present": True,
                "target_file": "data/imports/peers.csv",
            },
        ]
    )
    cards = dashboard.stock_report_next_step_cards(payload, coverage, {"peer_dataset_present": False})
    assert cards[0]["title"] == "Review peer import draft"
    assert cards[0]["command"] == "make imports-validate"


def test_stock_report_price_chart_frame_sorts_and_cleans_history():
    history = pd.DataFrame(
        {
            "date": ["2026-05-03", "2026-05-01", "2026-05-03", "bad-date"],
            "close": ["101.5", "99.0", "102.0", "103.0"],
            "volume": [100, 110, 120, 130],
        }
    )

    chart = dashboard.stock_report_price_chart_frame(history)

    assert list(chart.columns) == ["Close"]
    assert list(chart.index.strftime("%Y-%m-%d")) == ["2026-05-01", "2026-05-03"]
    assert chart.iloc[-1]["Close"] == 102.0


def test_stock_report_price_chart_frame_handles_missing_columns():
    chart = dashboard.stock_report_price_chart_frame(pd.DataFrame({"ticker": ["NVDA"]}))

    assert chart.empty
    assert list(chart.columns) == ["Close"]


def test_monthly_pick_score_chart_frame_prefers_ranked_candidates_and_scores():
    picks = pd.DataFrame(
        {
            "Ticker": ["amd", "nvda", "amd", "avgo"],
            "Rank": [2, 1, 3, None],
            "CompositeScore": [78, 91, 65, 74],
            "MomentumScore": [80, 95, 61, 70],
            "QualityScore": [55, 88, 40, None],
            "ValuationContextScore": [30, 44, 20, 26],
        }
    )

    chart = dashboard.monthly_pick_score_chart_frame(picks, max_rows=3)

    assert list(chart.index) == ["NVDA", "AMD", "AVGO"]
    assert "ValuationScore" in chart.columns
    assert chart.loc["AMD", "CompositeScore"] == 78


def test_monthly_pick_score_chart_frame_returns_empty_without_score_columns():
    picks = pd.DataFrame({"Ticker": ["NVDA"], "Theme": ["AI"]})

    chart = dashboard.monthly_pick_score_chart_frame(picks)

    assert chart.empty


def test_stock_report_technical_context_cards_are_readable_and_research_only():
    payload = {
        "screener_context": {
            "momentum_leaders": {
                "SetupStatus": "Watch",
                "RSPercentile": 92,
                "RelativeReturnVsSPY": 0.18,
                "RelativeReturnVsQQQ": 0.11,
                "DistanceFrom10EMA": 0.04,
                "DistanceFrom21EMA": 0.08,
                "DistanceFrom50SMA": -0.03,
                "VolumeRatio": 1.2,
                "ATRorVolatilityPct": 0.025,
                "ATRorVolatilitySource": "volatility_proxy",
            },
            "final_watchlist": {
                "FinalState": "Review Thesis",
                "SetupStatus": "Watch",
            },
        }
    }

    cards = dashboard.stock_report_technical_context_cards(payload)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 4
    assert "watch" in rendered
    assert "review thesis" in rendered
    assert "vs spy 18.0%" in rendered
    assert "above 10 ema" in rendered
    assert "volatility proxy approximation" in rendered
    assert "proxy values are approximations" in rendered
    assert "volume 1.2x" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_technical_context_cards_do_not_append_units_to_missing_volume():
    cards = dashboard.stock_report_technical_context_cards({"screener_context": {}})
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "volume ratio not available" in rendered
    assert "not availablex" not in rendered
    assert "nan" not in rendered


def test_stock_report_technical_context_frame_formats_missing_values_cleanly():
    frame = dashboard.stock_report_technical_context_frame({"screener_context": {}})

    assert list(frame.columns) == ["Metric", "Value"]
    rendered = " ".join(frame["Value"].astype(str)).lower()
    assert "not available" in rendered
    assert "none" not in rendered
    assert "nan" not in rendered


def test_single_stock_report_intro_cards_explain_output_before_generation():
    cards = dashboard.single_stock_report_intro_cards()
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "WHAT THIS MEANS",
        "WHAT YOU CAN ANALYZE NOW",
        "WHAT IS STILL LOCKED",
        "OUTPUT BOUNDARY",
        "COPY NEXT",
    ]
    assert "ready, blocked, or excluded first" in rendered
    assert "inputs are separated from calculations" in rendered
    assert "local/provider rows supply prices and fundamentals" in rendered
    assert "runs dcf math when inputs are complete" in rendered
    assert "peer valuation, earnings, and analyst-estimate context stay locked" in rendered
    assert "etf/index/fund dcf is excluded, not failed" in rendered
    assert "no hidden final call" in rendered
    assert "source inputs, product calculations, blocked sections" in rendered
    assert "does not convert partial data into a portfolio action" in rendered
    assert "start with a demo or one selected ticker" in rendered
    assert "for a visitor demo, copy the markdown report command" in rendered
    assert "read the at a glance and reader guide before opening detailed tables" in rendered
    assert "make stock-report-md ticker=nvda" in rendered
    assert "make stock-report-md ticker=apld" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_stock_report_source_frame_hides_raw_missing_values():
    frame = dashboard.stock_report_source_frame(
        [
            {
                "provider": "local",
                "freshness": None,
                "retrieved_at": "2026-05-21T10:00:00Z",
                "official": False,
                "notes": ["CSV fallback"],
            }
        ]
    )

    assert frame.iloc[0]["Freshness"] == "Not available"
    assert frame.iloc[0]["Retrieved"] == "2026-05-21"
    assert frame.iloc[0]["Official"] == "No"
    assert "CSV fallback" in frame.iloc[0]["Notes"]


def test_stock_report_source_detail_summary_frame_replaces_raw_json_dump():
    frame = dashboard.stock_report_source_detail_summary_frame(
        {
            "ticker": "NVDA",
            "provider_name": "local",
            "generated_at": "2026-06-04T12:00:00Z",
            "valuation_readiness": {
                "price_ready": True,
                "dcf_ready": True,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "peer_count": 2,
            },
            "data_freshness": [{"provider": "local:prices.csv"}, {"provider": "local:fundamentals.csv"}],
            "missing_data_warnings": ["No local earnings row."],
        }
    )

    assert list(frame.columns) == ["Detail", "Value"]
    rendered = " ".join(frame.astype(str).to_numpy().ravel()).lower()
    assert "nvda" in rendered
    assert "local" in rendered
    assert "2026-06-04" in rendered
    assert "ready feature flags" in rendered
    assert "blocked feature flags" in rendered
    assert "source rows" in rendered
    assert "missing-data warnings" in rendered
    assert "report data download" in rendered
    assert "optional structured local data file" in rendered
    assert "most readers can use this page or the markdown report" in rendered
    assert "machine-readable local report file" not in rendered
    assert "price_ready" not in rendered
    assert "data_freshness" not in rendered


def test_stock_report_detail_frames_are_readable_not_raw_json():
    frame = dashboard.stock_report_detail_frame(
        {
            "market_time": "2026-05-21T12:00:00Z",
            "price": 123.45,
            "source_notes": ["local CSV"],
            "official": False,
            "missing": None,
        }
    )

    assert list(frame.columns) == ["Field", "Value"]
    assert "2026-05-21" in frame["Value"].tolist()
    assert "123.45" in frame["Value"].tolist()
    assert "local CSV" in frame["Value"].tolist()
    assert "No" in frame["Value"].tolist()
    assert "Not available" in frame["Value"].tolist()


def test_stock_report_notes_frame_summarizes_warning_sections():
    frame = dashboard.stock_report_notes_frame(
        {"warnings": ["high growth normalized"], "notes": ["informational only"]},
        {"peer_missing_data_warnings": ["peers.csv missing"], "missing_fields": ["peer_ticker"]},
    )

    assert list(frame.columns) == ["Section", "Details"]
    rendered = " ".join(frame["Details"].astype(str)).lower()
    assert "high growth normalized" in rendered
    assert "peers.csv missing" in rendered


def test_stock_report_missing_data_text_stays_friendly():
    text = dashboard.stock_report_missing_data_text(["fundamentals unavailable, peers, Return1M"])

    assert "Needs SEC enrichment" in text
    assert "Needs peers.csv" in text
    assert "Not enough price history" in text


def test_data_health_overview_cards_prioritize_price_and_actions():
    validation = pd.DataFrame(
        {
            "validation_status": ["valid", "valid_with_warnings", "missing_file"],
        }
    )
    price_status = pd.DataFrame({"status": ["parse_error", "fetched"]})
    action_queue = pd.DataFrame({"urgency": ["critical", "high", "medium"]})
    coverage = pd.DataFrame(
        {
            "usable_for_momentum": [True, False],
            "dcf_ready": [True, False],
            "peer_ready": [False, False],
            "has_earnings": [False, False],
            "has_analyst_estimates": [False, False],
            "missing_required_for_momentum": ["", "prices"],
            "missing_required_for_dcf": ["", "fundamentals"],
            "missing_required_for_peer_relative": ["peer mapping", "peer mapping"],
        }
    )

    cards = dashboard.data_health_overview_cards(validation, price_status, action_queue, coverage)
    rendered = " ".join(str(value) for card in cards for value in card.values())

    assert len(cards) == 4
    assert "2 usable datasets" in rendered
    assert "1 price issue" in rendered
    assert "1 critical actions" in rendered
    assert "1 price-ready tickers" in rendered
    assert cards[0]["command"] == "make validate-data"
    assert cards[1]["command"] == "make price-status TOP_N=10"
    assert cards[2]["command"] == "make action-queue-check TOP_N=10"
    assert cards[3]["command"] == "make data-wizard TOP_N=10"
    assert "make price-status top_n=10" in rendered.lower()
    assert "make action-queue-check top_n=10" in rendered.lower()
    assert "make data-wizard top_n=10" in rendered.lower()


def test_data_health_overview_cards_without_price_status_use_runbook_first_guidance():
    validation = pd.DataFrame({"validation_status": ["valid", "missing_file"]})
    action_queue = pd.DataFrame({"urgency": ["critical"]})
    coverage = pd.DataFrame({"usable_for_momentum": [False]})

    cards = dashboard.data_health_overview_cards(validation, None, action_queue, coverage)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "price status not ready yet" in rendered
    assert "price status not generated" not in rendered
    assert cards[0]["command"] == "make validate-data"
    assert cards[1]["command"] == "make runbook-prices-broader"
    assert cards[2]["command"] == "make action-queue-check TOP_N=10"
    assert cards[3]["command"] == "make data-wizard TOP_N=10"
    assert "make runbook-prices-broader" in rendered
    assert "make focus-price" in rendered
    assert "manual import option" in rendered
    assert "make price-normalize" in rendered
    assert "make price-validate" in rendered
    assert "make price-preview" in rendered
    assert "make price-apply" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_overview_cards_surface_healthy_price_status_command_paths():
    validation = pd.DataFrame({"validation_status": ["valid", "valid_with_warnings"]})
    price_status = pd.DataFrame({"status": ["fetched", "skipped_fresh"]})
    action_queue = pd.DataFrame({"urgency": ["high", "medium"]})
    coverage = pd.DataFrame(
        {
            "usable_for_momentum": [True, True],
            "dcf_ready": [True, False],
            "peer_ready": [True, False],
            "has_earnings": [False, False],
            "has_analyst_estimates": [False, False],
            "missing_required_for_momentum": ["", ""],
            "missing_required_for_dcf": ["", "fundamentals"],
            "missing_required_for_peer_relative": ["", "peer mapping"],
        }
    )

    cards = dashboard.data_health_overview_cards(validation, price_status, action_queue, coverage)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["command"] == "make validate-data"
    assert cards[1]["command"] == "make price-status TOP_N=10"
    assert cards[2]["command"] == "make action-queue-check TOP_N=10"
    assert cards[3]["command"] == "make data-wizard TOP_N=10"
    assert "latest price refresh did not report blocking source errors" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_overview_cards_handle_empty_validation_rows():
    validation = pd.DataFrame({"validation_status": []})
    price_status = pd.DataFrame({"status": ["fetched"]})
    action_queue = pd.DataFrame({"urgency": ["medium"]})
    coverage = pd.DataFrame({"usable_for_momentum": [False]})

    cards = dashboard.data_health_overview_cards(validation, price_status, action_queue, coverage)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "No validation rows"
    assert cards[0]["command"] == "make validate-data"
    assert cards[1]["command"] == "make price-status TOP_N=10"
    assert cards[2]["command"] == "make action-queue-check TOP_N=10"
    assert cards[3]["command"] == "make data-wizard TOP_N=10"
    assert "run local validation to inspect configured csv datasets" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_overview_cards_surface_top_staged_action_follow_through():
    validation = pd.DataFrame({"validation_status": ["valid", "valid_with_warnings"]})
    price_status = pd.DataFrame({"status": ["fetched"]})
    action_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "fundamentals",
                "ticker": "NVDA",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )
    coverage = pd.DataFrame({"usable_for_momentum": [True], "dcf_ready": [False], "peer_ready": [False]})

    cards = dashboard.data_health_overview_cards(validation, price_status, action_queue, coverage)
    action_card = next(card for card in cards if card["kicker"] == "NEXT ACTIONS")

    assert action_card["command"] == "make imports-validate"
    assert "make imports-preview" in action_card["body"].lower()
    assert "make imports-apply" in action_card["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in action_card["body"].lower()


def test_data_health_tab_summary_cards_cover_price_and_staged_imports():
    validation = pd.DataFrame({"validation_status": ["valid", "missing_file"]})
    coverage = pd.DataFrame(
        {
            "usable_for_momentum": [True, False],
            "dcf_ready": [False, False],
            "peer_ready": [False, False],
            "has_earnings": [False, False],
            "has_analyst_estimates": [False, False],
            "missing_required_for_momentum": ["", "prices"],
            "missing_required_for_dcf": ["fundamentals", "fundamentals"],
            "missing_required_for_peer_relative": ["peer mapping", "peer mapping"],
        }
    )
    status = pd.DataFrame({"availability_status": ["available", "partial", "manual_only"]})
    price_status = pd.DataFrame({"status": ["fetched", "parse_error", "failed"]})
    staged_imports = {"files": [{"file_name": "fundamentals.csv"}]}

    coverage_cards = dashboard.data_health_tab_summary_cards("Coverage", validation, coverage, status, price_status, staged_imports)
    price_cards = dashboard.data_health_tab_summary_cards("Price Refresh", validation, coverage, status, price_status, staged_imports)
    staged_cards = dashboard.data_health_tab_summary_cards("Import Review", validation, coverage, status, price_status, staged_imports)
    rendered = " ".join(
        str(value)
        for group in [coverage_cards, price_cards, staged_cards]
        for card in group
        for value in card.values()
    ).lower()

    assert coverage_cards[0]["command"] == "make runbook-prices-broader"
    assert coverage_cards[1]["command"] == "make runbook-fundamentals-broader"
    assert coverage_cards[2]["command"] == "make runbook-peers-broader"
    assert coverage_cards[3]["command"] == "make onboarding"
    assert price_cards[0]["command"] == "make price-status TOP_N=10"
    assert staged_cards[0]["kicker"] == "IMPORT DRAFTS"
    assert "local import drafts waiting for review" in rendered
    assert price_cards[1]["command"] == "make price-status TOP_N=10"
    assert price_cards[2]["command"] == "make price-status TOP_N=10"
    assert staged_cards[0]["command"] == "make imports-preview"
    assert "1" in rendered
    assert "make price-status top_n=10" in rendered
    assert "manual import option" in rendered
    assert "make price-normalize" in rendered
    assert "make price-validate" in rendered
    assert "make price-preview" in rendered
    assert "make price-apply" in rendered
    assert "preview first" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_tab_summary_cards_cover_sources_and_validation_fallbacks():
    validation = pd.DataFrame({"validation_status": ["valid", "valid_with_warnings", "missing_file"]})
    status = pd.DataFrame({"availability_status": ["available", "partial", "manual_only"]})

    source_cards = dashboard.data_health_tab_summary_cards("Sources", validation, None, status, None, {})
    validation_cards = dashboard.data_health_tab_summary_cards("Validation", validation, None, status, None, {})
    rendered = " ".join(
        str(value)
        for group in [source_cards, validation_cards]
        for card in group
        for value in card.values()
    ).lower()

    assert source_cards[0]["command"] == "make data-sources"
    assert source_cards[1]["command"] == "make data-sources"
    assert validation_cards[0]["command"] == "make validate-data"
    assert validation_cards[1]["command"] == "make validate-data"
    assert "status registry" in rendered
    assert "schema checks" in rendered
    assert "partial safe" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_fix_first_cards_prioritize_actions():
    actions = pd.DataFrame(
        [
            {
                "priority": 2,
                "dataset": "fundamentals",
                "ticker": "MSFT",
                "reason": "Needs verified local fundamentals.",
                "recommended_action": "Run SEC import draft workflow, then validate and preview.",
                "focus_command": "make focus-fundamentals TICKER=MSFT",
                "example_command": "make sec-stage TICKERS=MSFT",
            },
            {
                "priority": 1,
                "dataset": "prices",
                "ticker": "NVDA",
                "reason": "Short local price history.",
                "recommended_action": "Normalize verified downloaded OHLCV rows.",
                "focus_command": "make focus-price TICKER=NVDA",
                "example_command": "make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual",
            },
        ]
    )

    cards = dashboard.data_health_fix_first_cards(actions)
    rendered = " ".join(str(value) for card in cards for value in card).lower()

    assert cards[0][0] == "P1 prices - NVDA"
    assert cards[0][3] == "danger"
    assert "make focus-price ticker=nvda" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_fix_first_cards_fall_back_to_onboarding_refresh():
    cards = dashboard.data_health_fix_first_cards(None)
    rendered = " ".join(str(value) for card in cards for value in card).lower()

    assert len(cards) == 1
    assert cards[0][0] == "No fix-first actions yet"
    assert cards[0][2] == "make onboarding"
    assert "make onboarding" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_fix_first_cards_use_lane_front_doors_when_commands_are_missing():
    actions = pd.DataFrame(
        [
            {
                "priority": 1,
                "dataset": "peers",
                "ticker": "AMD",
                "reason": "Peer mappings are missing.",
                "recommended_action": "Research a peer set and stage it through the imports workflow.",
                "focus_command": "",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.data_health_fix_first_cards(actions)

    assert cards[0][0] == "P1 peers - AMD"
    assert cards[0][2] == "make focus-peers TICKER=AMD"


def test_data_health_fix_first_cards_normalize_legacy_status_copy():
    actions = pd.DataFrame(
        [
            {
                "priority": 1,
                "dataset": "fundamentals",
                "ticker": "NVDA",
                "reason": "Local fundamentals still need staged validation.",
                "recommended_action": "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the fundamentals import drafts.",
                "focus_command": "make focus-fundamentals TICKER=NVDA",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.data_health_fix_first_cards(actions)

    assert "make status-check TOP_N=5" in cards[0][1]


def test_data_health_fix_first_cards_use_staged_flow_fallback_when_row_copy_is_missing():
    actions = pd.DataFrame(
        [
            {
                "priority": 1,
                "dataset": "fundamentals",
                "ticker": "NVDA",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make imports-validate",
                "example_command": "",
            },
            {
                "priority": 2,
                "dataset": "peers",
                "ticker": "TSLA",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make runbook-peers",
                "example_command": "",
            },
            {
                "priority": 3,
                "dataset": "peers",
                "ticker": "",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make bundle-peers",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.data_health_fix_first_cards(actions)

    assert cards[0][0] == "P1 fundamentals - NVDA"
    assert cards[0][2] == "make imports-validate"
    assert "make imports-preview" in cards[0][1].lower()
    assert "make imports-apply" in cards[0][1].lower()
    assert cards[1][2] == "make runbook-peers"
    assert "ordered lane runbook" in cards[1][1].lower()
    assert cards[2][2] == "make bundle-peers"
    assert "highest-leverage local bundle first" in cards[2][1].lower()
    assert "not available" not in cards[0][1].lower()
    assert "not available" not in " ".join(card[1] for card in cards).lower()


def test_data_health_fix_first_cards_keep_staged_follow_through_visible_when_target_files_are_present():
    actions = pd.DataFrame(
        [
            {
                "priority": 1,
                "dataset": "fundamentals",
                "ticker": "NVDA",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            },
            {
                "priority": 2,
                "dataset": "peers",
                "ticker": "TSLA",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            },
            {
                "priority": 3,
                "dataset": "prices",
                "ticker": "AMD",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make price-validate",
                "example_command": "",
                "target_file": "data/imports/prices.csv",
            },
        ]
    )

    cards = dashboard.data_health_fix_first_cards(actions)

    assert cards[0][2] == "make imports-validate"
    assert "make imports-preview" in cards[0][1].lower()
    assert "make imports-apply" in cards[0][1].lower()
    assert cards[1][2] == "make imports-validate"
    assert "make imports-preview" in cards[1][1].lower()
    assert "make imports-apply" in cards[1][1].lower()
    assert cards[2][2] == "make price-validate"
    assert "make price-preview" in cards[2][1].lower()
    assert "make price-apply" in cards[2][1].lower()
    assert "use local import draft workflows if the free refresh fails" not in " ".join(card[1] for card in cards).lower()


def test_data_health_action_path_cards_surface_best_and_lane_commands():
    actions = pd.DataFrame(
        [
            {
                "priority": 1,
                "dataset": "prices",
                "ticker": "NVDA",
                "reason": "No verified local price history is present yet.",
                "recommended_action": "Normalize verified downloaded OHLCV rows, then run make price-validate, make price-preview, and make price-apply.",
                "focus_command": "make focus-price TICKER=NVDA",
                "example_command": "make price-worklist",
            },
            {
                "priority": 2,
                "dataset": "fundamentals",
                "ticker": "AMD",
                "reason": "DCF inputs are still incomplete.",
                "recommended_action": "Run SEC import draft workflow for fundamentals, then validate and preview before applying.",
                "focus_command": "make focus-fundamentals TICKER=AMD",
                "example_command": "make sec-stage TICKERS=AMD",
            },
            {
                "priority": 2,
                "dataset": "peers",
                "ticker": "TSLA",
                "reason": "No local peer mapping is configured for this ticker.",
                "recommended_action": "Add manually researched peers and keep peer-relative comparison transparent.",
                "focus_command": "make focus-peers TICKER=TSLA",
                "example_command": "make templates",
            },
        ]
    )
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "NVDA",
                "title": "Repair prices",
                "reason": "NVDA update failed during remote refresh.",
                "recommended_action": "Normalize verified downloaded OHLCV rows, then run make price-validate, make price-preview, and make price-apply.",
                "focus_command": "make focus-price TICKER=NVDA",
                "example_command": "make price-worklist",
            }
        ]
    )

    cards = dashboard.data_health_action_path_cards(actions, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 4
    assert cards[0]["kicker"] == "BEST NEXT"
    assert cards[0]["title"] == "make focus-price TICKER=NVDA"
    assert cards[0]["command"] == "make focus-price TICKER=NVDA"
    assert "price path" in rendered
    assert "fundamentals path" in rendered
    assert "peer path" in rendered
    assert "no verified local price history is present yet" in rendered
    assert "normalize verified downloaded ohlcv rows" in rendered
    assert "dcf inputs are still incomplete" in rendered
    assert "make focus-fundamentals ticker=amd" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_action_path_cards_handle_missing_inputs_gracefully():
    cards = dashboard.data_health_action_path_cards(None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 1
    assert "no action paths yet" in rendered
    assert cards[0]["command"] == "make onboarding"
    assert "make onboarding" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_action_path_cards_use_lane_and_queue_front_doors_when_commands_are_missing():
    actions = pd.DataFrame(
        [
            {
                "priority": 2,
                "dataset": "fundamentals",
                "ticker": "AMD",
                "reason": "DCF inputs are still incomplete.",
                "recommended_action": "Run SEC import draft workflow for fundamentals, then validate and preview before applying.",
            }
        ]
    )
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "NVDA",
                "title": "Repair prices",
                "reason": "NVDA update failed during remote refresh.",
            }
        ]
    )

    cards = dashboard.data_health_action_path_cards(actions, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "make focus-price TICKER=NVDA"
    assert cards[0]["command"] == "make focus-price TICKER=NVDA"
    assert any(card.get("command") == "make focus-fundamentals TICKER=AMD" for card in cards)
    assert "make focus-price ticker=nvda" in rendered
    assert "make focus-fundamentals ticker=amd" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_action_path_cards_use_review_fallback_when_row_copy_is_missing():
    actions = pd.DataFrame(
        [
            {
                "priority": 2,
                "dataset": "peers",
                "ticker": "AMD",
                "reason": "",
                "recommended_action": "",
            }
        ]
    )
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "prices",
                "ticker": "NVDA",
                "title": "Repair prices",
                "reason": "",
                "recommended_action": "",
            }
        ]
    )

    cards = dashboard.data_health_action_path_cards(actions, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "make focus-price TICKER=NVDA"
    assert "review price path." in cards[0]["body"].lower()
    assert any("review peer path." in str(card.get("body", "")).lower() for card in cards)
    assert "not available" not in rendered


def test_data_health_action_path_cards_use_command_family_fallbacks_when_row_copy_is_missing():
    actions = pd.DataFrame(
        [
            {
                "priority": 2,
                "dataset": "fundamentals",
                "ticker": "NVDA",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make imports-validate",
                "example_command": "",
            },
            {
                "priority": 3,
                "dataset": "peers",
                "ticker": "TSLA",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make runbook-peers",
                "example_command": "",
            }
        ]
    )
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "fundamentals",
                "ticker": "NVDA",
                "title": "Review fundamentals import draft",
                "reason": "",
                "recommended_action": "",
                "focus_command": "make imports-validate",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.data_health_action_path_cards(actions, queue)

    assert cards[0]["title"] == "make imports-validate"
    assert "make imports-preview" in cards[0]["body"].lower()
    assert "make imports-apply" in cards[0]["body"].lower()
    assert any("ordered lane runbook" in str(card.get("body", "")).lower() for card in cards[1:])
    assert any(card.get("command") == "make runbook-peers" for card in cards[1:])
    assert "not available" not in " ".join(str(value) for card in cards for value in card.values()).lower()


def test_data_health_action_path_cards_keep_staged_follow_through_visible_when_target_files_are_present():
    actions = pd.DataFrame(
        [
            {
                "priority": 2,
                "dataset": "fundamentals",
                "ticker": "NVDA",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            },
            {
                "priority": 3,
                "dataset": "peers",
                "ticker": "TSLA",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            },
            {
                "priority": 4,
                "dataset": "prices",
                "ticker": "AMD",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make price-validate",
                "example_command": "",
                "target_file": "data/imports/prices.csv",
            },
        ]
    )
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "urgency": "critical",
                "action_type": "fundamentals",
                "ticker": "NVDA",
                "title": "Review fundamentals import draft",
                "reason": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )

    cards = dashboard.data_health_action_path_cards(actions, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "make imports-validate"
    assert "make imports-preview" in cards[0]["body"].lower()
    assert any(card.get("command") == "make imports-validate" and "make imports-preview" in str(card.get("body", "")).lower() for card in cards[1:3])
    assert any(card.get("command") == "make price-validate" and "make price-preview" in str(card.get("body", "")).lower() for card in cards)
    assert "use local import draft workflows if the free refresh fails" not in rendered


def test_data_health_command_bundle_cards_surface_holdings_first_commands():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "ticker_count": 2,
                "tickers": "AMD,AVGO",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 42 verified rows still needed across this bundle",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "bundle_shortcut_command": "make bundle-prices",
                "detail_shortcut_command": "make detail-prices",
                "runbook_shortcut_command": "make runbook-prices",
                "fallback_manual_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "primary_command": "python3 -m src.data_update --tickers AMD,AVGO",
                "follow_up_command": "make price-status",
                "target_file": "data/imports/prices.csv",
                "why_it_matters": "These tickers still block monthly picks because local price history is too short.",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            },
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "ticker_count": 1,
                "tickers": "NVDA",
                "goal_summary": "Advance explicit local DCF readiness for the listed tickers",
                "bundle_shortcut_command": "make bundle-fundamentals",
                "detail_shortcut_command": "make detail-fundamentals",
                "runbook_shortcut_command": "make runbook-fundamentals",
                "primary_command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=NVDA",
                "follow_up_command": "make imports-validate",
                "target_file": "data/imports/fundamentals.csv",
                "why_it_matters": "This holding is the best next candidate for explicit local DCF inputs.",
                "safe_next_step": "Keep SEC enrichment import draft and review-only until make imports-validate, make imports-preview, and make imports-apply confirm the merge.",
            },
        ]
    )

    cards = dashboard.data_health_command_bundle_cards(bundles)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "PRICES"
    assert "holdings first" in rendered
    assert "unlock monthly picks" in rendered
    assert "21 target rows" in rendered
    assert "start by 2025-12-01" in rendered
    assert "make bundle-prices" in rendered
    assert "make bundle-fundamentals" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_command_bundle_cards_use_review_fallback_when_summaries_are_missing():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "ticker_count": 1,
                "tickers": "TSLA",
                "goal_summary": "",
                "why_it_matters": "",
                "bundle_shortcut_command": "",
                "detail_shortcut_command": "",
                "runbook_shortcut_command": "make runbook-peers",
                "primary_command": "",
            }
        ]
    )

    cards = dashboard.data_health_command_bundle_cards(bundles)

    assert cards[0]["command"] == "make runbook-peers"
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_data_health_command_bundle_cards_use_staged_follow_through_when_summaries_are_missing():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "why_it_matters": "",
                "bundle_shortcut_command": "",
                "detail_shortcut_command": "",
                "runbook_shortcut_command": "make runbook-fundamentals",
                "primary_command": "",
                "target_file": "data/imports/fundamentals.csv",
                "safe_next_step": "Keep SEC enrichment import draft and review-only until make imports-validate, make imports-preview, and make imports-apply confirm the merge.",
            }
        ]
    )

    cards = dashboard.data_health_command_bundle_cards(bundles)

    assert cards[0]["command"] == "make runbook-fundamentals"
    assert "make imports-preview" in cards[0]["body"].lower()
    assert "make imports-apply" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_data_health_command_bundle_cards_use_price_staged_follow_through_when_summaries_are_missing():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "ticker_count": 2,
                "tickers": "AMD,AVGO",
                "goal_summary": "",
                "why_it_matters": "",
                "bundle_shortcut_command": "",
                "detail_shortcut_command": "",
                "runbook_shortcut_command": "make runbook-prices",
                "primary_command": "",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "",
            }
        ]
    )

    cards = dashboard.data_health_command_bundle_cards(bundles)

    assert cards[0]["command"] == "make runbook-prices"
    assert "make price-validate" in cards[0]["body"].lower()
    assert "make price-preview" in cards[0]["body"].lower()
    assert "make price-apply" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_data_health_command_bundle_cards_upgrade_generic_price_staged_note_to_explicit_follow_through():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "ticker_count": 2,
                "tickers": "AMD,AVGO",
                "goal_summary": "",
                "why_it_matters": "",
                "bundle_shortcut_command": "",
                "detail_shortcut_command": "",
                "runbook_shortcut_command": "make runbook-prices",
                "primary_command": "",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            }
        ]
    )

    cards = dashboard.data_health_command_bundle_cards(bundles)

    assert cards[0]["command"] == "make runbook-prices"
    assert "make price-validate" in cards[0]["body"].lower()
    assert "make price-preview" in cards[0]["body"].lower()
    assert "make price-apply" in cards[0]["body"].lower()


def test_data_health_onboarding_fallback_cards_use_status_refresh():
    bundle_cards = dashboard.data_health_command_bundle_cards(None)
    runbook_cards = dashboard.data_health_command_bundle_runbook_cards(None)
    target_cards = dashboard.data_health_price_target_cards(None)

    rendered = " ".join(
        str(value)
        for card_group in (bundle_cards, runbook_cards, target_cards)
        for card in card_group
        for value in card.values()
    ).lower()

    assert bundle_cards[0]["command"] == "make onboarding"
    assert bundle_cards[0]["title"] == "No command bundles yet"
    assert runbook_cards[0]["command"] == "make onboarding"
    assert runbook_cards[0]["title"] == "No bundle runbook yet"
    assert target_cards[0]["command"] == "make onboarding"
    assert target_cards[0]["title"] == "No price-history targets yet"
    assert "run make onboarding to refresh the onboarding outputs" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_command_bundle_runbook_cards_surface_lane_steps_safely():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "python3 -m src.data_update --tickers AMD,AVGO",
                "target_file": "data/imports/prices.csv",
                "tickers": "AMD,AVGO",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 42 verified rows still needed across this bundle",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "fallback_manual_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "why_it_matters": "These tickers still block monthly picks because local price history is too short.",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            },
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 2,
                "step_label": "If refresh fails, normalize first CSV",
                "command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "target_file": "data/imports/prices.csv",
                "tickers": "AMD,AVGO",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 42 verified rows still needed across this bundle",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "fallback_manual_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "why_it_matters": "These tickers still block monthly picks because local price history is too short.",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            },
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 3,
                "step_label": "If import drafts were used, validate prices",
                "command": "make price-validate",
                "target_file": "data/imports/prices.csv",
                "tickers": "AMD,AVGO",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 42 verified rows still needed across this bundle",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "fallback_manual_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "why_it_matters": "These tickers still block monthly picks because local price history is too short.",
                "safe_next_step": "Validate normalized price import drafts before preview so schema and duplicate issues surface early.",
            },
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 4,
                "step_label": "If import drafts were used, preview merge",
                "command": "make price-preview",
                "target_file": "data/imports/prices.csv",
                "tickers": "AMD,AVGO",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 42 verified rows still needed across this bundle",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "fallback_manual_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "why_it_matters": "These tickers still block monthly picks because local price history is too short.",
                "safe_next_step": "Preview the price import draft merge before apply and confirm the affected tickers and row counts look correct.",
            },
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 5,
                "step_label": "If import drafts were used, apply merge",
                "command": "make price-apply",
                "target_file": "data/imports/prices.csv",
                "tickers": "AMD,AVGO",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 42 verified rows still needed across this bundle",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "fallback_manual_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "why_it_matters": "These tickers still block monthly picks because local price history is too short.",
                "safe_next_step": "Apply the price import draft merge only after validation and preview look correct.",
            },
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 6,
                "step_label": "Review follow-up output",
                "command": "make price-status",
                "target_file": "data/imports/prices.csv",
                "tickers": "AMD,AVGO",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 42 verified rows still needed across this bundle",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "fallback_manual_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "why_it_matters": "These tickers still block monthly picks because local price history is too short.",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            },
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 7,
                "step_label": "Refresh status outputs",
                "command": "make price-status",
                "target_file": "data/imports/prices.csv",
                "tickers": "AMD,AVGO",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 42 verified rows still needed across this bundle",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "fallback_manual_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "why_it_matters": "These tickers still block monthly picks because local price history is too short.",
                "safe_next_step": "Reopen Data Health or Overview after refreshing outputs.",
            },
        ]
    )

    cards = dashboard.data_health_command_bundle_runbook_cards(runbook)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "PRICES RUNBOOK"
    assert "run bundle command" in rendered
    assert "unlock monthly picks" in rendered
    assert "21 target rows" in rendered
    assert "start by 2025-12-01" in rendered
    assert "make price-normalize input=data/raw/prices/amd.csv ticker=amd source=yahoo_manual" in rendered
    assert "make price-validate" in rendered
    assert "make price-preview" in rendered
    assert "make price-apply" in rendered
    assert "make price-status" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_command_bundle_runbook_cards_surface_peer_manual_step():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "make templates",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance transparent peer-relative readiness for the listed tickers",
            },
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "step_order": 2,
                "step_label": "Fill peer mappings manually",
                "command": "data/imports/peers.csv",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance transparent peer-relative readiness for the listed tickers",
            },
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "step_order": 3,
                "step_label": "Refresh status outputs",
                "command": "make status",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance transparent peer-relative readiness for the listed tickers",
            },
        ]
    )

    cards = dashboard.data_health_command_bundle_runbook_cards(runbook)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "fill peer mappings manually" in rendered
    assert "data/imports/peers.csv" in rendered
    assert "make status-check top_n=5" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_command_bundle_runbook_cards_use_staged_follow_through_when_goal_summary_is_missing():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Review import draft",
                "command": "make imports-validate",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "target_file": "data/imports/fundamentals.csv",
                "safe_next_step": "Keep SEC enrichment import draft and review-only until make imports-validate, make imports-preview, and make imports-apply confirm the merge.",
            }
        ]
    )

    cards = dashboard.data_health_command_bundle_runbook_cards(runbook)

    assert cards[0]["command"] == "make imports-validate"
    assert "make imports-preview" in cards[0]["body"].lower()
    assert "make imports-apply" in cards[0]["body"].lower()
    assert "review import draft" in cards[0]["body"].lower()


def test_data_health_command_bundle_runbook_cards_use_price_staged_follow_through_when_goal_summary_is_missing():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Review import draft",
                "command": "make price-validate",
                "tickers": "AMD,AVGO",
                "goal_summary": "",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "",
            }
        ]
    )

    cards = dashboard.data_health_command_bundle_runbook_cards(runbook)

    assert cards[0]["command"] == "make price-validate"
    assert "make price-preview" in cards[0]["body"].lower()
    assert "make price-apply" in cards[0]["body"].lower()
    assert "review import draft" in cards[0]["body"].lower()


def test_data_health_command_bundle_runbook_cards_upgrade_generic_price_staged_note_to_explicit_follow_through():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Review import draft",
                "command": "make price-validate",
                "tickers": "AMD,AVGO",
                "goal_summary": "",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            }
        ]
    )

    cards = dashboard.data_health_command_bundle_runbook_cards(runbook)

    assert cards[0]["command"] == "make price-validate"
    assert "make price-preview" in cards[0]["body"].lower()
    assert "make price-apply" in cards[0]["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in cards[0]["body"].lower()


def test_data_health_command_bundle_runbook_cards_use_staged_command_when_steps_are_blank():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Review import draft",
                "command": "",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "target_file": "data/imports/fundamentals.csv",
                "safe_next_step": "Keep SEC enrichment import draft and review-only until make imports-validate, make imports-preview, and make imports-apply confirm the merge.",
            }
        ]
    )

    cards = dashboard.data_health_command_bundle_runbook_cards(runbook)

    assert cards[0]["command"] == "make imports-validate"
    assert "review import draft: make imports-validate" in cards[0]["body"].lower()
    assert "make imports-preview" in cards[0]["body"].lower()
    assert "no runbook steps available" not in cards[0]["body"].lower()


def test_data_health_command_bundle_runbook_cards_use_price_staged_command_when_steps_are_blank():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Review import draft",
                "command": "",
                "tickers": "AMD,AVGO",
                "goal_summary": "",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "",
            }
        ]
    )

    cards = dashboard.data_health_command_bundle_runbook_cards(runbook)

    assert cards[0]["command"] == "make price-validate"
    assert "review import draft: make price-validate" in cards[0]["body"].lower()
    assert "make price-preview" in cards[0]["body"].lower()
    assert "make price-apply" in cards[0]["body"].lower()
    assert "no runbook steps available" not in cards[0]["body"].lower()


def test_data_health_command_bundle_runbook_cards_use_why_it_matters_when_goal_summary_is_missing():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Fill peer mappings manually",
                "command": "data/imports/peers.csv",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "why_it_matters": "These tickers are closest to peer-relative coverage once manually researched mappings are added locally.",
            }
        ]
    )

    cards = dashboard.data_health_command_bundle_runbook_cards(runbook)

    assert "closest to peer-relative coverage" in cards[0]["body"].lower()
    assert "fill peer mappings manually: data/imports/peers.csv" in cards[0]["body"].lower()


def test_data_health_command_bundle_runbook_cards_use_runbook_fallback_when_summaries_are_missing():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Open peer runbook",
                "command": "make runbook-peers",
                "tickers": "TSLA",
                "goal_summary": "",
                "why_it_matters": "",
            }
        ]
    )

    cards = dashboard.data_health_command_bundle_runbook_cards(runbook)

    assert cards[0]["command"] == "make runbook-peers"
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_data_health_price_target_cards_surface_exact_history_targets_safely():
    worklist = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "META",
                "price_history_days": 0,
                "next_price_goal": "Unlock Monthly Picks",
                "next_target_history_rows": 21,
                "rows_needed_for_next_goal": 21,
                "suggested_start_date": "2026-01-01",
                "example_command": "make price-normalize INPUT=data/raw/prices/META.csv TICKER=META SOURCE=yahoo_manual",
            },
            {
                "priority": 2,
                "ticker": "NVDA",
                "price_history_days": 22,
                "next_price_goal": "Unlock Track Record",
                "next_target_history_rows": 63,
                "rows_needed_for_next_goal": 41,
                "suggested_start_date": "2025-10-01",
                "example_command": "make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual",
            },
        ]
    )

    cards = dashboard.data_health_price_target_cards(worklist)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "UNLOCK MONTHLY PICKS"
    assert "21 rows still needed" in rendered
    assert "suggested start: 2026-01-01" in rendered
    assert "price-normalize" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_price_target_cards_keep_staged_price_follow_through_visible():
    worklist = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "META",
                "price_history_days": 0,
                "next_price_goal": "Unlock Monthly Picks",
                "next_target_history_rows": 21,
                "rows_needed_for_next_goal": 21,
                "suggested_start_date": "2026-01-01",
                "focus_command": "make focus-price TICKER=META",
                "example_command": "make price-normalize INPUT=data/raw/prices/META.csv TICKER=META SOURCE=yahoo_manual",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "Run make price-validate and make price-preview before make price-apply; do not fabricate missing history.",
            }
        ]
    )

    cards = dashboard.data_health_price_target_cards(worklist)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["command"] == "make focus-price TICKER=META"
    assert "price-normalize" in rendered
    assert "make price-validate" in rendered
    assert "make price-preview" in rendered
    assert "make price-apply" in rendered
    assert "do not fabricate missing history" in rendered


def test_data_health_price_target_cards_upgrade_generic_staged_note_to_explicit_follow_through():
    worklist = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "META",
                "price_history_days": 0,
                "next_price_goal": "Unlock Monthly Picks",
                "next_target_history_rows": 21,
                "rows_needed_for_next_goal": 21,
                "suggested_start_date": "2026-01-01",
                "focus_command": "make focus-price TICKER=META",
                "example_command": "make price-normalize INPUT=data/raw/prices/META.csv TICKER=META SOURCE=yahoo_manual",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            }
        ]
    )

    cards = dashboard.data_health_price_target_cards(worklist)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["command"] == "make focus-price TICKER=META"
    assert "price-normalize" in rendered
    assert "make price-validate" in rendered
    assert "make price-preview" in rendered
    assert "make price-apply" in rendered


def test_price_target_cards_use_price_front_doors_when_commands_are_missing():
    worklist = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "META",
                "price_history_days": 0,
                "next_price_goal": "Unlock Monthly Picks",
                "next_target_history_rows": 21,
                "rows_needed_for_next_goal": 21,
                "suggested_start_date": "2026-01-01",
                "example_command": "",
                "focus_command": "",
            },
            {
                "priority": 2,
                "ticker": "",
                "price_history_days": 0,
                "next_price_goal": "Reach Preferred 1Y History",
                "next_target_history_rows": 252,
                "rows_needed_for_next_goal": 189,
                "suggested_start_date": "2025-01-01",
                "example_command": "",
                "focus_command": "",
            },
        ]
    )

    data_health_cards = dashboard.data_health_price_target_cards(worklist)
    overview_cards = dashboard.overview_price_target_cards(worklist)

    assert data_health_cards[0]["command"] == "make focus-price TICKER=META"
    assert overview_cards[0]["command"] == "make focus-price TICKER=META"
    assert data_health_cards[1]["command"] == "make runbook-prices-broader"
    assert overview_cards[1]["command"] == "make runbook-prices-broader"


def test_data_health_deep_research_target_cards_surface_dcf_and_peer_targets_safely():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "is_holding": True,
                "theme": "AI Semis",
                "price_history_days": 63,
                "missing_required_for_dcf": "fundamentals row",
                "recommended_action": "Run SEC import draft workflow for fundamentals so DCF assumptions can be reviewed from explicit local inputs.",
                "example_command": "make sec-stage TICKERS=NVDA",
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "is_holding": True,
                "theme": "EV",
                "dcf_ready": True,
                "missing_required_for_peer_relative": "peer mapping",
                "recommended_action": "Add manually researched peer mappings for this ticker and keep peer-relative comparison transparent.",
                "example_command": "make templates",
            }
        ]
    )

    cards = dashboard.data_health_deep_research_target_cards(sec_queue, peer_queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "DCF TARGET"
    assert "peer target" in rendered
    assert "make focus-fundamentals ticker=nvda" in rendered
    assert "make focus-peers ticker=tsla" in rendered
    assert "fundamentals row" in rendered
    assert "peer mapping" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_deep_research_target_cards_preserve_staged_fundamentals_command():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "is_holding": True,
                "theme": "AI Semis",
                "price_history_days": 63,
                "missing_required_for_dcf": "fundamentals import drafts still need make imports-validate, make imports-preview, and make imports-apply",
                "recommended_action": "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local fundamentals.",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )

    cards = dashboard.data_health_deep_research_target_cards(sec_queue, pd.DataFrame())

    assert cards[0]["command"] == "make imports-validate"
    assert "make imports-apply" in cards[0]["body"].lower()
    assert "make status-check top_n=5" in cards[0]["body"].lower()


def test_data_health_deep_research_target_cards_use_review_fallback_when_action_is_missing():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "is_holding": False,
                "theme": "Semis",
                "price_history_days": 84,
                "missing_required_for_dcf": "fundamentals row",
                "recommended_action": "",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.data_health_deep_research_target_cards(sec_queue, pd.DataFrame())

    assert "review fundamentals path." in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_data_health_deep_research_target_cards_use_runbook_fallback_when_action_is_missing():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "is_holding": False,
                "theme": "Semis",
                "price_history_days": 84,
                "missing_required_for_dcf": "fundamentals row",
                "recommended_action": "",
                "focus_command": "make runbook-fundamentals",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.data_health_deep_research_target_cards(sec_queue, pd.DataFrame())

    assert cards[0]["command"] == "make runbook-fundamentals"
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_data_health_deep_research_target_cards_use_peer_review_fallback_when_action_is_missing():
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "is_holding": False,
                "theme": "EV",
                "dcf_ready": False,
                "missing_required_for_peer_relative": "peer mapping",
                "recommended_action": "",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.data_health_deep_research_target_cards(pd.DataFrame(), peer_queue)

    assert "review peer path." in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_data_health_deep_research_target_cards_use_peer_runbook_fallback_when_action_is_missing():
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "is_holding": False,
                "theme": "EV",
                "dcf_ready": False,
                "missing_required_for_peer_relative": "peer mapping",
                "recommended_action": "",
                "focus_command": "make runbook-peers",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.data_health_deep_research_target_cards(pd.DataFrame(), peer_queue)

    assert cards[0]["command"] == "make runbook-peers"
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_data_health_deep_research_target_cards_keep_staged_import_paths_when_commands_are_missing():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "is_holding": True,
                "theme": "AI Semis",
                "price_history_days": 63,
                "missing_required_for_dcf": "fundamentals import drafts still need validate/preview/apply",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "is_holding": True,
                "theme": "EV",
                "dcf_ready": True,
                "missing_required_for_peer_relative": "peer import drafts still need validate/preview/apply",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )

    cards = dashboard.data_health_deep_research_target_cards(sec_queue, peer_queue)

    assert cards[0]["command"] == "make imports-validate"
    assert "fundamentals import draft" in cards[0]["body"].lower()
    assert cards[1]["command"] == "make imports-validate"
    assert "peer import draft" in cards[1]["body"].lower()


def test_overview_price_target_cards_surface_exact_history_targets_safely():
    worklist = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "META",
                "price_history_days": 0,
                "next_price_goal": "Unlock Monthly Picks",
                "next_target_history_rows": 21,
                "rows_needed_for_next_goal": 21,
                "suggested_start_date": "2026-01-01",
                "example_command": "make price-normalize INPUT=data/raw/prices/META.csv TICKER=META SOURCE=yahoo_manual",
            },
            {
                "priority": 2,
                "ticker": "NVDA",
                "price_history_days": 22,
                "next_price_goal": "Unlock Track Record",
                "next_target_history_rows": 63,
                "rows_needed_for_next_goal": 41,
                "suggested_start_date": "2025-10-01",
                "example_command": "make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual",
            },
        ]
    )

    cards = dashboard.overview_price_target_cards(worklist)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "UNLOCK MONTHLY PICKS"
    assert "21 rows still needed" in rendered
    assert "target: 21 rows" in rendered
    assert "start from: 2026-01-01" in rendered
    assert "price-normalize" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_price_target_cards_keep_staged_price_follow_through_visible():
    worklist = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "META",
                "price_history_days": 0,
                "next_price_goal": "Unlock Monthly Picks",
                "next_target_history_rows": 21,
                "rows_needed_for_next_goal": 21,
                "suggested_start_date": "2026-01-01",
                "focus_command": "make focus-price TICKER=META",
                "example_command": "make price-normalize INPUT=data/raw/prices/META.csv TICKER=META SOURCE=yahoo_manual",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "Run make price-validate and make price-preview before make price-apply; do not fabricate missing history.",
            }
        ]
    )

    cards = dashboard.overview_price_target_cards(worklist)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["command"] == "make focus-price TICKER=META"
    assert "price-normalize" in rendered
    assert "make price-validate" in rendered
    assert "make price-preview" in rendered
    assert "make price-apply" in rendered
    assert "do not fabricate missing history" in rendered


def test_overview_price_target_cards_upgrade_generic_staged_note_to_explicit_follow_through():
    worklist = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "META",
                "price_history_days": 0,
                "next_price_goal": "Unlock Monthly Picks",
                "next_target_history_rows": 21,
                "rows_needed_for_next_goal": 21,
                "suggested_start_date": "2026-01-01",
                "focus_command": "make focus-price TICKER=META",
                "example_command": "make price-normalize INPUT=data/raw/prices/META.csv TICKER=META SOURCE=yahoo_manual",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            }
        ]
    )

    cards = dashboard.overview_price_target_cards(worklist)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["command"] == "make focus-price TICKER=META"
    assert "price-normalize" in rendered
    assert "make price-validate" in rendered
    assert "make price-preview" in rendered
    assert "make price-apply" in rendered


def test_overview_deep_research_target_cards_surface_dcf_and_peer_targets_safely():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "is_holding": True,
                "theme": "AI Semis",
                "price_history_days": 63,
                "missing_required_for_dcf": "fundamentals row",
                "recommended_action": "Run SEC import draft workflow for fundamentals so DCF assumptions can be reviewed from explicit local inputs.",
                "example_command": "make sec-stage TICKERS=NVDA",
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "is_holding": True,
                "theme": "EV",
                "dcf_ready": True,
                "missing_required_for_peer_relative": "peer mapping",
                "recommended_action": "Add manually researched peer mappings for this ticker and keep peer-relative comparison transparent.",
                "example_command": "make templates",
            }
        ]
    )

    cards = dashboard.overview_deep_research_target_cards(sec_queue, peer_queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "UNLOCK DCF"
    assert "unlock peers" in rendered
    assert "fundamentals row" in rendered
    assert "peer mapping" in rendered
    assert "make focus-fundamentals ticker=nvda" in rendered
    assert "make focus-peers ticker=tsla" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_deep_research_target_cards_preserve_staged_fundamentals_command():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "is_holding": True,
                "theme": "AI Semis",
                "price_history_days": 63,
                "missing_required_for_dcf": "fundamentals import drafts still need make imports-validate, make imports-preview, and make imports-apply",
                "recommended_action": "Run make imports-validate, then make imports-preview, then make imports-apply, then make status to confirm the live local fundamentals.",
                "focus_command": "make imports-validate",
                "example_command": "make imports-preview",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )

    cards = dashboard.overview_deep_research_target_cards(sec_queue, pd.DataFrame())

    assert cards[0]["command"] == "make imports-validate"
    assert "make imports-apply" in cards[0]["body"].lower()
    assert "make status-check top_n=5" in cards[0]["body"].lower()


def test_overview_deep_research_target_cards_use_review_fallback_when_action_is_missing():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "is_holding": False,
                "theme": "Semis",
                "price_history_days": 84,
                "missing_required_for_dcf": "fundamentals row",
                "recommended_action": "",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.overview_deep_research_target_cards(sec_queue, pd.DataFrame())

    assert "review fundamentals path." in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_deep_research_target_cards_use_runbook_fallback_when_action_is_missing():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "is_holding": False,
                "theme": "Semis",
                "price_history_days": 84,
                "missing_required_for_dcf": "fundamentals row",
                "recommended_action": "",
                "focus_command": "make runbook-fundamentals",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.overview_deep_research_target_cards(sec_queue, pd.DataFrame())

    assert cards[0]["command"] == "make runbook-fundamentals"
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_deep_research_target_cards_use_peer_review_fallback_when_action_is_missing():
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "is_holding": False,
                "theme": "EV",
                "dcf_ready": False,
                "missing_required_for_peer_relative": "peer mapping",
                "recommended_action": "",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.overview_deep_research_target_cards(pd.DataFrame(), peer_queue)

    assert "review peer path." in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_deep_research_target_cards_use_peer_runbook_fallback_when_action_is_missing():
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "is_holding": False,
                "theme": "EV",
                "dcf_ready": False,
                "missing_required_for_peer_relative": "peer mapping",
                "recommended_action": "",
                "focus_command": "make runbook-peers",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.overview_deep_research_target_cards(pd.DataFrame(), peer_queue)

    assert cards[0]["command"] == "make runbook-peers"
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_deep_research_target_cards_keep_staged_import_paths_when_commands_are_missing():
    sec_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "is_holding": True,
                "theme": "AI Semis",
                "price_history_days": 63,
                "missing_required_for_dcf": "fundamentals import drafts still need validate/preview/apply",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            }
        ]
    )
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "is_holding": True,
                "theme": "EV",
                "dcf_ready": True,
                "missing_required_for_peer_relative": "peer import drafts still need validate/preview/apply",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            }
        ]
    )

    cards = dashboard.overview_deep_research_target_cards(sec_queue, peer_queue)

    assert cards[0]["command"] == "make imports-validate"
    assert "fundamentals import draft" in cards[0]["body"].lower()
    assert cards[1]["command"] == "make imports-validate"
    assert "peer import draft" in cards[1]["body"].lower()


def test_deep_research_target_fallback_cards_use_onboarding_refresh():
    data_health_cards = dashboard.data_health_deep_research_target_cards(None, None)
    overview_cards = dashboard.overview_deep_research_target_cards(None, None)
    price_cards = dashboard.overview_price_target_cards(None)

    rendered = " ".join(
        str(value)
        for card_group in (data_health_cards, overview_cards, price_cards)
        for card in card_group
        for value in card.values()
    ).lower()

    assert data_health_cards[0]["command"] == "make onboarding"
    assert data_health_cards[0]["title"] == "No DCF or peer targets yet"
    assert overview_cards[0]["command"] == "make onboarding"
    assert overview_cards[0]["title"] == "No DCF or peer targets yet"
    assert price_cards[0]["command"] == "make onboarding"
    assert price_cards[0]["title"] == "No price-history targets yet"
    assert "run make onboarding" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_bundle_empty_states_use_operator_facing_titles():
    bundle_cards = dashboard.overview_command_bundle_cards(None)
    handoff_cards = dashboard.overview_bundle_handoff_cards(None, None, None)
    runbook_cards = dashboard.overview_bundle_runbook_cards(None)

    assert bundle_cards[0]["title"] == "No command bundles yet"
    assert handoff_cards[0]["title"] == "No bundle guidance yet"
    assert runbook_cards[0]["title"] == "No bundle runbook yet"
    assert bundle_cards[0]["command"] == "make onboarding"
    assert handoff_cards[0]["command"] == "make onboarding"
    assert runbook_cards[0]["command"] == "make onboarding"


def test_data_coverage_wizard_cards_show_unlock_goals_without_raw_missing_values():
    wizard = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "unlock_goal": "Unlock Monthly Picks",
                "blocking_dataset": "prices",
                "current_status": "0 local price rows",
                "why_it_matters": "Monthly ranking needs verified local price history.",
                "recommended_action": "Refresh NVDA prices, or normalize verified downloaded OHLCV rows into data/imports/prices.csv before make price-validate, make price-preview, and make price-apply.",
                "focus_command": "make focus-price TICKER=NVDA",
                "example_command": "python3 -m src.data_update --tickers NVDA",
            },
            {
                "priority": 2,
                "ticker": "NVDA",
                "unlock_goal": "Unlock DCF",
                "blocking_dataset": "fundamentals",
                "current_status": "free_cash_flow, shares_outstanding",
                "why_it_matters": "DCF needs cash-flow inputs.",
                "recommended_action": "Run SEC import draft workflow for candidate fundamentals, then validate and preview before applying.",
                "focus_command": "make focus-fundamentals TICKER=NVDA",
                "example_command": "make sec-stage TICKERS=NVDA",
            },
        ]
    )

    cards = dashboard.data_coverage_wizard_cards(wizard)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "unlock-guide rows" in rendered
    assert "monthly" in rendered
    assert "valuation" in rendered
    assert "not blocking" in rendered
    assert "current blocker: 0 local price rows" in rendered
    assert "normalize verified downloaded ohlcv rows" in rendered
    assert "make focus-price ticker=nvda" in rendered
    assert "nan" not in rendered
    assert "none" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_coverage_wizard_cards_handle_missing_output():
    cards = dashboard.data_coverage_wizard_cards(None)
    rendered = " ".join(str(value) for card in cards for value in card.values())

    assert cards[0]["kicker"] == "UNLOCK GUIDE"
    assert "Unlock guide not ready yet" in rendered
    assert "Not generated" not in rendered
    assert "local unlock guide" in rendered
    assert cards[0]["command"] == "make data-wizard TOP_N=10"
    assert "make data-wizard" in rendered


def test_dashboard_uses_unlock_guide_labels_for_user_visible_wizard_outputs():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")

    for phrase in (
        "Data Coverage Unlock Guide",
        "Data Quality Unlock Guide",
        "Data Quality Unlock Guide rows",
        "Coverage unlock guide has not been generated",
        "Data Coverage Unlock Guide Rows",
    ):
        assert phrase in source

    for old_label in (
        '"data_coverage_wizard.csv": "Data Coverage Wizard"',
        '"data_quality_wizard.csv": "Data Quality Wizard"',
        "Data Coverage Wizard Rows",
        "Coverage wizard has not been generated",
    ):
        assert old_label not in source


def test_data_coverage_wizard_cards_use_lane_front_doors_when_commands_are_missing():
    wizard = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AMD",
                "unlock_goal": "Unlock DCF",
                "blocking_dataset": "fundamentals",
                "current_status": "shares_outstanding missing",
                "why_it_matters": "DCF needs shares and cash-flow inputs.",
                "recommended_action": "Stage candidate fundamentals before validating and previewing the import.",
                "focus_command": "",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.data_coverage_wizard_cards(wizard)
    valuation_card = next(card for card in cards if card["kicker"] == "VALUATION")

    assert valuation_card["title"] == "1 blocker"
    assert valuation_card["command"] == "make focus-fundamentals TICKER=AMD"
    assert "make focus-fundamentals TICKER=AMD" in valuation_card["badges"]


def test_data_coverage_wizard_cards_use_review_fallback_when_row_copy_is_missing():
    wizard = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "unlock_goal": "Unlock Peer Relative",
                "blocking_dataset": "peers",
                "current_status": "",
                "why_it_matters": "",
                "recommended_action": "",
                "focus_command": "",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.data_coverage_wizard_cards(wizard)
    peer_card = next(card for card in cards if card["kicker"] == "PEERS")

    assert peer_card["title"] == "1 blocker"
    assert peer_card["command"] == "make focus-peers TICKER=TSLA"
    assert "review peer path." in peer_card["body"].lower()
    assert "not available" not in peer_card["body"].lower()


def test_data_coverage_wizard_cards_use_staged_flow_fallback_when_row_copy_is_missing():
    wizard = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "unlock_goal": "Unlock DCF",
                "blocking_dataset": "fundamentals",
                "current_status": "",
                "why_it_matters": "",
                "recommended_action": "",
                "focus_command": "make imports-validate",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.data_coverage_wizard_cards(wizard)
    valuation_card = next(card for card in cards if card["kicker"] == "VALUATION")

    assert valuation_card["title"] == "1 blocker"
    assert valuation_card["command"] == "make imports-validate"
    assert "make imports-preview" in valuation_card["body"].lower()
    assert "make imports-apply" in valuation_card["body"].lower()
    assert "not available" not in valuation_card["body"].lower()


def test_data_coverage_wizard_cards_use_runbook_fallback_when_row_copy_is_missing():
    wizard = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "TSLA",
                "unlock_goal": "Unlock Peer Relative",
                "blocking_dataset": "peers",
                "current_status": "",
                "why_it_matters": "",
                "recommended_action": "",
                "focus_command": "make runbook-peers",
                "example_command": "",
            }
        ]
    )

    cards = dashboard.data_coverage_wizard_cards(wizard)
    peer_card = next(card for card in cards if card["kicker"] == "PEERS")

    assert peer_card["title"] == "1 blocker"
    assert peer_card["command"] == "make runbook-peers"
    assert "ordered lane runbook" in peer_card["body"].lower()
    assert "not available" not in peer_card["body"].lower()


def test_data_coverage_wizard_cards_keep_staged_follow_through_visible_when_target_files_are_present():
    wizard = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "NVDA",
                "unlock_goal": "Unlock DCF",
                "blocking_dataset": "fundamentals",
                "current_status": "",
                "why_it_matters": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/fundamentals.csv",
            },
            {
                "priority": 1,
                "ticker": "TSLA",
                "unlock_goal": "Unlock Peer Relative",
                "blocking_dataset": "peers",
                "current_status": "",
                "why_it_matters": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make imports-validate",
                "example_command": "",
                "target_file": "data/imports/peers.csv",
            },
            {
                "priority": 1,
                "ticker": "AMD",
                "unlock_goal": "Unlock Monthly Picks",
                "blocking_dataset": "prices",
                "current_status": "",
                "why_it_matters": "",
                "recommended_action": "Use local import draft workflows if the free refresh fails.",
                "focus_command": "make price-validate",
                "example_command": "",
                "target_file": "data/imports/prices.csv",
            },
        ]
    )

    cards = dashboard.data_coverage_wizard_cards(wizard)
    valuation_card = next(card for card in cards if card["kicker"] == "VALUATION")
    peer_card = next(card for card in cards if card["kicker"] == "PEERS")
    monthly_card = next(card for card in cards if card["kicker"] == "MONTHLY")

    assert valuation_card["command"] == "make imports-validate"
    assert "make imports-preview" in valuation_card["body"].lower()
    assert "make imports-apply" in valuation_card["body"].lower()
    assert peer_card["command"] == "make imports-validate"
    assert "make imports-preview" in peer_card["body"].lower()
    assert "make imports-apply" in peer_card["body"].lower()
    assert monthly_card["command"] == "make price-validate"
    assert "make price-preview" in monthly_card["body"].lower()
    assert "make price-apply" in monthly_card["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in " ".join(card["body"] for card in cards).lower()


def test_universe_preset_cards_include_preview_commands():
    cards = dashboard.universe_preset_cards()
    rendered = " ".join(str(value) for card in cards for value in card.values())

    assert cards
    assert "make universe-preview" in rendered
    assert "apply-import" not in rendered


def test_universe_workflow_cards_explain_preview_first_and_manual_fallback():
    cards = dashboard.universe_workflow_cards(
        {
            "current_universe": {
                "row_count": 12,
                "duplicate_ticker_count": 1,
                "missing_theme_count": 2,
                "unclassified_theme_count": 1,
                "missing_sector_etf_count": 3,
            },
            "staged_universe": {"row_count": 4, "path": "data/imports/universe.csv"},
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card).lower()

    assert cards[0][0] == "Current universe"
    assert cards[0][3] == "warning"
    assert "4 staged ticker rows" in rendered
    assert "make universe-preview" in rendered
    assert "make universe-apply" in rendered
    assert "custom_universe.csv" in rendered
    assert "make templates" in rendered


def test_universe_action_path_cards_surface_preview_review_and_apply_guidance():
    cards = dashboard.universe_action_path_cards(
        {
            "current_universe": {
                "row_count": 12,
                "duplicate_ticker_count": 1,
                "missing_theme_count": 2,
                "unclassified_theme_count": 1,
            },
            "staged_universe": {"exists": True, "row_count": 4},
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[0]["title"] == "Apply universe draft"
    assert cards[0]["command"] == "make universe-apply"
    assert cards[2]["command"] == "make universe-apply"
    assert "12 current rows" in rendered
    assert "apply stays copy-only" in rendered
    assert "cli-only" not in rendered
    assert "terminal-only" not in rendered
    assert "make universe-preview" in rendered
    assert "make universe-apply" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_universe_manager_summary_cards_surface_make_preview_and_apply():
    cards = dashboard.universe_manager_summary_cards(
        {
            "row_count": 12,
            "duplicate_ticker_count": 1,
            "missing_theme_count": 2,
            "unclassified_theme_count": 1,
        },
        {"exists": True, "row_count": 4},
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 3
    assert cards[1]["command"] == "make universe-apply"
    assert cards[2]["command"] == "make universe-preview"
    assert "make universe-preview" in rendered
    assert "make universe-apply" in rendered
    assert "import draft present" in rendered


def test_staged_universe_status_frame_hides_raw_json_shape():
    frame = dashboard.staged_universe_status_frame(
        {
            "row_count": 4,
            "path": "data/imports/universe.csv",
            "validation": {"status": "valid_with_warnings", "warnings": ["manual review recommended"]},
        }
    )

    assert list(frame.columns) == ["Field", "Value"]
    assert "Import draft file" in frame["Field"].tolist()
    assert "data/imports/universe.csv" in frame["Value"].tolist()
    assert "valid_with_warnings" in frame["Value"].tolist()
    assert "manual review recommended" in frame["Value"].tolist()


def test_staged_universe_detail_frame_uses_readable_table_not_raw_json():
    frame = dashboard.staged_universe_detail_frame(
        {
            "row_count": 4,
            "path": "data/imports/universe.csv",
            "validation": {
                "status": "valid_with_warnings",
                "warnings": ["manual review recommended"],
                "missing_required_columns": ["sector"],
                "extra_columns": ["notes"],
                "duplicate_tickers": ["NVDA"],
            },
        }
    )
    rendered = " ".join(frame.astype(str).to_numpy().ravel()).lower()

    assert list(frame.columns) == ["Field", "Value"]
    assert "missing required columns" in rendered
    assert "sector" in rendered
    assert "extra columns" in rendered
    assert "notes" in rendered
    assert "duplicate tickers" in rendered
    assert "nvda" in rendered
    assert "{" not in rendered
    assert "}" not in rendered


def test_dashboard_uses_readable_universe_import_review_details():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")

    assert "Universe import review details" in source
    assert "staged_universe_detail_frame" in source
    assert "st.json(staged_universe" not in source
    assert "st.json(staged" not in source
    assert "Advanced universe import details" not in source
    assert "Universe Import Review" in source
    assert "Files that stay local" in source
    assert "These working files are intentionally ignored so local refreshes and previews do not clutter the public project." in source
    assert "Staged universe review details (JSON)" not in source
    assert "Runtime Artifact Hygiene" not in source
    assert "Advanced staged universe details (JSON)" not in source
    assert "Raw staged universe diagnostics" not in source


def test_dashboard_import_copy_uses_plain_language_for_standard_files():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    visible_source = source.replace("canonical_import_file", "")

    assert "Standard Import File" in source
    assert "standard import file" in source
    assert "standard import files" in source
    assert "Local import drafts waiting for review before any standard local file update." in source
    assert "main universe file" in source
    assert "canonical import" not in visible_source.lower()
    assert "canonical rows" not in visible_source.lower()
    assert "canonical csv" not in visible_source.lower()
    assert "canonical universe" not in visible_source.lower()


def test_output_tab_summary_cards_explain_rows_status_and_gaps():
    frame = pd.DataFrame(
        {
            "Ticker": ["NVDA", "AMD", "MSFT"],
            "Theme": ["AI", "AI", "Cloud"],
            "FinalState": ["Watch", "Watch", "Review Thesis"],
            "MissingDataFields": ["", "Return1M", None],
            "Reason": ["Clear setup context.", "Needs price history.", "Review valuation context."],
        }
    )

    cards = dashboard.output_tab_summary_cards("Final Watchlist", frame)
    rendered = " ".join(str(value) for card in cards for value in card.values())

    assert len(cards) == 4
    assert "3 rows" in rendered
    assert "Watch" in rendered
    assert "1 row" in rendered
    assert "AI" in rendered


def test_output_tab_function_quality_cards_explain_broad_page_limits():
    market_cards = dashboard.output_tab_function_quality_cards("Market Direction")
    momentum_cards = dashboard.output_tab_function_quality_cards("Momentum Leaders")
    portfolio_cards = dashboard.output_tab_function_quality_cards("Portfolio Review")
    rendered = " ".join(
        str(value)
        for card in market_cards + momentum_cards + portfolio_cards
        for value in card.values()
    ).lower()

    assert [card["kicker"] for card in market_cards] == ["WHAT IT CAN DO", "WHAT IT CANNOT DO"]
    assert [card["kicker"] for card in momentum_cards] == ["WHAT IT CAN DO", "WHAT IT CANNOT DO"]
    assert [card["kicker"] for card in portfolio_cards] == ["WHAT IT CAN DO", "WHAT IT CANNOT DO"]
    assert "show theme and etf context" in rendered
    assert "no market timing instruction" in rendered
    assert "surface local setup strength" in rendered
    assert "no automatic timing call" in rendered
    assert "review holding purpose and risk" in rendered
    assert "no portfolio action instruction" in rendered
    assert "does not rebalance" in rendered
    assert "research context only" in rendered
    assert "trade timing" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_dashboard_readiness_summary_counts_ready_blocked_and_credentials(monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.setenv("SEC_USER_AGENT", "tester@example.com")
    coverage = pd.DataFrame(
        {
            "ticker": ["NVDA", "AMD", "QQQ"],
            "has_prices": [True, False, True],
            "usable_for_momentum": [True, False, True],
            "peer_ready": [False, True, False],
        }
    )
    dcf = pd.DataFrame(
        {
            "ticker": ["NVDA", "AMD", "QQQ"],
            "asset_type": ["company", "company", "etf"],
            "is_dcf_ready": [True, False, False],
        }
    )
    earnings = pd.DataFrame({"ticker": ["NVDA"], "has_trusted_earnings": [True]})
    estimates = pd.DataFrame({"ticker": ["NVDA"], "has_trusted_analyst_estimates": [False]})

    summary = dashboard.dashboard_readiness_summary(coverage, dcf, earnings, estimates)
    cards = dashboard.readiness_panel_cards(summary)
    rendered = " ".join(str(value) for card in cards for value in card.values())

    assert summary["universe_count"] == 3
    assert summary["master_universe"] == 3
    assert summary["active_universe"] == 3
    assert summary["price_ready"] == 2
    assert summary["momentum_ready"] == 2
    assert summary["dcf_ready"] == 1
    assert summary["dcf_excluded"] == 1
    assert summary["peer_ready"] == 1
    assert summary["earnings_ready"] == 1
    assert summary["analyst_ready"] == 0
    assert summary["analyst_estimates_ready"] == 0
    assert summary["missing_credentials"] == ["STOOQ_API_KEY"]
    assert summary["configured_credentials"] == ["SEC_USER_AGENT"]
    assert "Missing: STOOQ_API_KEY" in rendered
    assert "Configured: SEC_USER_AGENT" in rendered
    assert "Only workflows that require the missing credential are blocked" in rendered
    assert "make price-coverage TOP_N=25" in rendered
    assert "Import draft folders available" in rendered
    assert "Price import draft folder: data/staged/prices/" in rendered
    assert "data/staged/earnings/" in rendered
    assert "review before apply" in rendered
    assert "staged review/apply" not in rendered.lower()


def test_market_wide_readiness_summary_prefers_central_dcf_count(monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    readiness = pd.DataFrame(
        {
            "ticker": ["NVDA", "QQQ", "ZZZ"],
            "in_master_universe": [True, True, True],
            "in_active_universe": [True, True, False],
            "price_ready": [True, True, False],
            "momentum_ready": [True, True, False],
            "market_direction_ready": [True, True, False],
            "liquidity_ready": [True, False, False],
            "correlation_ready": [True, False, False],
            "fundamentals_ready": [True, False, False],
            "dcf_ready": [True, False, False],
            "peer_ready": [False, False, False],
            "earnings_ready": [False, False, False],
            "analyst_estimates_ready": [False, False, False],
            "overall_readiness_state": ["partial", "partial", "blocked"],
            "excluded_features": ["", "dcf", ""],
        }
    )
    coverage = pd.DataFrame(
        {
            "ticker": ["NVDA", "QQQ", "ZZZ"],
            "has_prices": [True, True, False],
            "usable_for_momentum": [True, True, False],
            "peer_ready": [False, False, False],
        }
    )
    decisions = pd.DataFrame({"ticker": ["NVDA", "ZZZ"], "decision_bucket": ["Monitor", "Blocked by Data"]})

    summary = dashboard.market_wide_readiness_summary(readiness, coverage, decisions)

    assert summary["master_count"] == 3
    assert summary["master_universe"] == 3
    assert summary["active_count"] == 2
    assert summary["active_universe"] == 2
    assert summary["price_ready"] == 2
    assert summary["market_direction_ready"] == 2
    assert summary["dcf_ready"] == 1
    assert summary["dcf_excluded"] == 1
    assert summary["fundamentals_ready"] == 1
    assert summary["blocked_by_data"] == 1
    assert summary["blocked"] == 1
    assert summary["partial"] == 2
    assert summary["analyst_estimates_ready"] == 0
    assert summary["decision_buckets"] == {"Monitor": 1, "Blocked by Data": 1}
    assert summary["missing_credentials"] == ["STOOQ_API_KEY", "SEC_USER_AGENT"]

    readiness_only_summary = dashboard.market_wide_readiness_summary(readiness, None, decisions)
    assert readiness_only_summary["universe_count"] == 3
    assert readiness_only_summary["price_ready"] == 2
    assert readiness_only_summary["momentum_ready"] == 2
    assert readiness_only_summary["peer_ready"] == 0


def test_universe_layer_cards_separate_scope_from_analysis_readiness():
    summary = {
        "master_universe": 3538,
        "active_universe": 12,
        "price_ready": 240,
        "dcf_ready": 23,
        "peer_ready": 3,
        "blocked_by_data": 3298,
        "decision_buckets": {"Research Now": 23, "Monitor": 2, "Blocked by Data": 3513},
    }

    cards = dashboard.universe_layer_cards(summary)
    rendered = " ".join(str(value) for card in cards for value in card.values())

    assert "3,538 tracked ticker(s)" in rendered
    assert "12 focused ticker(s)" in rendered
    assert "240 price / 23 DCF / 3 peer" in rendered
    assert "module-specific" in rendered
    assert "does not mean every analysis module is ready" in rendered
    assert "research-only" in rendered
    assert "buy" not in rendered.lower()
    assert "sell" not in rendered.lower()


def test_universe_layer_frame_gives_plain_language_next_steps():
    summary = {
        "master_count": 3538,
        "active_count": 12,
        "price_ready": 240,
        "dcf_ready": 23,
        "peer_ready": 3,
        "earnings_ready": 0,
        "analyst_estimates_ready": 0,
        "blocked": 3298,
        "decision_buckets": {"Research Now": 23, "Monitor": 2},
    }

    frame = dashboard.universe_layer_frame(summary)
    rendered = " ".join(frame.astype(str).to_numpy().ravel().tolist())

    assert frame["Layer"].tolist() == [
        "Master universe",
        "Active research list",
        "Price and momentum ready",
        "Company valuation ready",
        "Optional context ready",
        "Research decision layer",
    ]
    assert "3,538 tracked ticker(s)" in rendered
    assert "23 DCF-ready / 3 peer-ready ticker(s)" in rendered
    assert "Leave unavailable until trusted local CSV rows exist" in rendered
    assert "do not infer missing valuation inputs" in rendered


def test_methodology_ladder_explains_local_analysis_without_recommendations():
    frame = dashboard.methodology_ladder_frame()
    rendered = " ".join(frame.astype(str).to_numpy().ravel().tolist())

    assert frame["Step"].tolist() == [
        "1. Readiness gate",
        "2. Supported calculations",
        "3. Blocked or excluded analysis",
        "4. Decision wording",
        "5. Report explanation",
    ]
    assert "Checks whether local or provider-assisted rows for prices, fundamentals, DCF inputs, peers, earnings, and estimates are complete enough" in rendered
    assert "input rows do not decide the conclusion by themselves" in rendered
    assert "project calculations" in rendered
    assert "data-confidence limits" in rendered
    assert "without importing third-party analyst opinions" in rendered
    assert "Withholds missing analysis instead of guessing fields" in rendered
    assert "Research Now, Monitor, or Blocked by Data" in rendered
    assert "src/stock_report.py" in rendered
    assert "buy" not in rendered.lower()
    assert "sell" not in rendered.lower()


def test_roadmap_milestone_status_frame_keeps_trusted_data_gaps_honest():
    summary = {
        "master_universe": 3538,
        "fundamentals_ready": 23,
        "dcf_ready": 23,
        "peer_ready": 3,
    }

    frame = dashboard.roadmap_milestone_status_frame(summary)
    rendered = " ".join(frame.astype(str).to_numpy().ravel().tolist())

    assert frame["Roadmap Area"].tolist() == [
        "Product workflow",
        "Fundamentals / DCF data unlock",
        "Peer readiness",
        "Decision clarity",
        "Verification",
    ]
    assert "Implemented" in rendered
    assert "Waiting on trusted data" in rendered
    assert "23/3,538 fundamentals-ready" in rendered
    assert "23/3,538 DCF-ready" in rendered
    assert "3/3,538 peer-ready" in rendered
    assert "counts should improve only after SEC import draft workflow or trusted manual CSV imports" in rendered
    assert "make sec-stage-queue TOP_N=25" in rendered
    assert "make peer-mapping-queue TOP_N=25" in rendered
    assert "buy" not in rendered.lower()
    assert "sell" not in rendered.lower()


def test_roadmap_milestone_status_cards_surface_safe_commands():
    cards = dashboard.roadmap_milestone_status_cards(
        {
            "master_universe": 3538,
            "fundamentals_ready": 23,
            "dcf_ready": 23,
            "peer_ready": 3,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 5
    assert cards[0]["command"] == "make dashboard-smoke"
    assert any(card["command"] == "make verify" for card in cards)
    assert "data-honest" in rendered
    assert "waiting on trusted data" in rendered
    assert "source-backed peer rows" in rendered
    assert "unsupported" not in rendered


def test_market_wide_readiness_summary_uses_current_report_ready_columns(monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    readiness = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "in_master_universe": [True, True, True],
            "in_active_universe": [True, False, False],
            "price_ready": [True, True, False],
            "momentum_ready": [True, False, False],
            "peer_ready": [True, False, False],
            "overall_readiness_state": ["partial", "partial", "blocked"],
        }
    )
    current_schema_coverage = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "price_ready": [False, False, False],
            "momentum_ready": [False, False, False],
        }
    )

    summary = dashboard.market_wide_readiness_summary(readiness, current_schema_coverage, pd.DataFrame())
    audit = dashboard.product_page_logic_audit_frame(summary, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    readiness_row = audit.loc[audit["check"].eq("Readiness before conclusions")].iloc[0]

    assert summary["price_ready"] == 2
    assert summary["momentum_ready"] == 1
    assert summary["peer_ready"] == 1
    assert "2 price-covered ticker(s)" in readiness_row["evidence"]


def test_dashboard_readiness_summary_supports_current_coverage_schema_without_ticker_readiness(monkeypatch):
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    coverage = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "price_ready": [True, True, False],
            "momentum_ready": [True, False, False],
            "peer_ready": [False, True, False],
        }
    )

    summary = dashboard.dashboard_readiness_summary(coverage, None, None, None)

    assert summary["price_ready"] == 2
    assert summary["momentum_ready"] == 1
    assert summary["peer_ready"] == 1


def test_filter_market_readiness_frame_defaults_active_and_limits_rows():
    readiness = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC", "DDD"],
            "in_master_universe": [True, True, True, True],
            "in_active_universe": [True, True, False, False],
            "price_ready": [True, False, False, True],
            "momentum_ready": [True, False, False, True],
            "dcf_ready": [False, False, False, True],
            "fundamentals_ready": [False, False, False, True],
            "peer_ready": [False, False, False, True],
            "earnings_ready": [False, False, False, False],
            "analyst_estimates_ready": [False, False, False, False],
            "asset_type": ["company", "company", "company", "company"],
            "blocked_features": ["fundamentals", "price", "price", ""],
            "missing_data": ["free_cash_flow", "price", "price", ""],
        }
    )

    filtered = dashboard.filter_market_readiness_frame(readiness, row_limit=1)

    assert filtered["ticker"].tolist() == ["AAA"]


def test_filter_market_readiness_frame_normalizes_stale_peer_next_actions():
    readiness = pd.DataFrame(
        {
            "ticker": ["COHR", "CRDO", "AMD"],
            "in_master_universe": [True, True, True],
            "in_active_universe": [True, True, True],
            "price_ready": [True, True, True],
            "fundamentals_ready": [True, False, True],
            "dcf_ready": [True, False, True],
            "peer_ready": [False, False, True],
            "earnings_ready": [False, False, False],
            "analyst_estimates_ready": [False, False, False],
            "asset_type": ["company", "company", "company"],
            "ready_features": ["price, fundamentals, dcf", "price", "price, fundamentals, dcf, peer"],
            "partial_features": ["peer", "", ""],
            "blocked_features": ["earnings, analyst_estimates", "fundamentals, dcf, peer", "earnings, analyst_estimates"],
            "missing_data": [
                "peers: needs at least 2 source-backed peer mappings; earnings: trusted local CSV input",
                "dcf: revenue, fcf_margin; peers: needs at least 2 source-backed peer mappings",
                "earnings: trusted local CSV input",
            ],
            "next_action": [
                "Optional context missing for COHR; leave unavailable unless trusted local CSVs exist.",
                "Import trusted fundamentals for CRDO.",
                "Optional context missing for AMD; leave unavailable unless trusted local CSVs exist.",
            ],
        }
    )

    filtered = dashboard.filter_market_readiness_frame(readiness, row_limit=None)
    cohr = filtered.loc[filtered["ticker"].eq("COHR"), "next_action"].iloc[0]
    crdo = filtered.loc[filtered["ticker"].eq("CRDO"), "next_action"].iloc[0]
    amd = filtered.loc[filtered["ticker"].eq("AMD"), "next_action"].iloc[0]

    assert "data/imports/peers.csv" in cohr
    assert "make imports-validate" in cohr
    assert "optional context" not in cohr.lower()
    assert crdo == "Import trusted fundamentals for CRDO."
    assert amd == "Optional context missing for AMD; leave unavailable unless trusted local CSVs exist."


def test_filter_market_readiness_frame_default_limit_stays_operator_sized():
    readiness = pd.DataFrame(
        {
            "ticker": [f"T{i:03d}" for i in range(75)],
            "in_master_universe": [True] * 75,
            "in_active_universe": [False] * 75,
            "price_ready": [False] * 75,
            "momentum_ready": [False] * 75,
            "dcf_ready": [False] * 75,
            "fundamentals_ready": [False] * 75,
            "peer_ready": [False] * 75,
            "earnings_ready": [False] * 75,
            "analyst_estimates_ready": [False] * 75,
            "asset_type": ["company"] * 75,
        }
    )

    filtered = dashboard.filter_market_readiness_frame(readiness, scope="All master universe")

    assert len(filtered) == dashboard.DEFAULT_MARKET_ROW_LIMIT == 50
    assert filtered["ticker"].tolist() == [f"T{i:03d}" for i in range(50)]


def test_filter_market_readiness_frame_supports_broad_blocked_price_and_asset_filters():
    readiness = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "QQQ"],
            "in_master_universe": [True, True, True],
            "in_active_universe": [False, False, True],
            "price_ready": [False, True, True],
            "momentum_ready": [False, True, True],
            "dcf_ready": [False, True, False],
            "fundamentals_ready": [False, True, False],
            "peer_ready": [False, True, False],
            "earnings_ready": [False, False, False],
            "analyst_estimates_ready": [False, False, False],
            "asset_type": ["company", "company", "etf"],
            "sector": ["Technology", "Financials", "ETF"],
            "theme": ["AI", "Fintech", "Market proxy"],
            "blocked_features": ["price", "", ""],
            "missing_data": ["price", "", ""],
        }
    )

    blocked_price = dashboard.filter_market_readiness_frame(
        readiness,
        scope="All master universe",
        readiness_filter="Blocked by price",
        row_limit=None,
    )
    etfs = dashboard.filter_market_readiness_frame(
        readiness,
        scope="All master universe",
        asset_filter="ETFs / index proxies",
        row_limit=None,
    )
    companies = dashboard.filter_market_readiness_frame(
        readiness,
        scope="All master universe",
        asset_filter="Companies only",
        sector="Technology",
        ticker_search="aa",
        row_limit=None,
    )

    assert blocked_price["ticker"].tolist() == ["AAA"]
    assert etfs["ticker"].tolist() == ["QQQ"]
    assert companies["ticker"].tolist() == ["AAA"]


def test_market_next_action_cards_are_safe_copyable_make_commands():
    readiness = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC", "DDD"],
            "in_active_universe": [True, True, True, False],
            "price_ready": [False, True, True, False],
            "fundamentals_ready": [False, False, True, False],
            "peer_ready": [False, False, True, False],
            "earnings_ready": [False, False, False, False],
            "analyst_estimates_ready": [False, False, False, False],
            "asset_type": ["company", "company", "company", "company"],
        }
    )

    cards = dashboard.market_next_action_cards(readiness, pd.DataFrame({"ticker": ["AAA"]}))
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "make price-refresh-loop dry_run=1" in rendered
    assert "dry run" in rendered
    assert "make sec-stage-queue top_n=25" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "make optional-context-worklist top_n=25" in rendered
    assert "make onboarding top_n=10" in rendered
    assert "make templates" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_next_action_console_groups_feature_actions_with_source_notes():
    readiness = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC", "QQQ"],
            "in_active_universe": [True, True, True, True],
            "price_ready": [False, True, True, True],
            "fundamentals_ready": [False, False, True, False],
            "dcf_ready": [False, False, True, False],
            "peer_ready": [False, False, False, False],
            "earnings_ready": [False, False, False, False],
            "analyst_estimates_ready": [False, False, False, False],
            "asset_type": ["company", "company", "company", "etf"],
        }
    )
    payload = {
        "recommended_next_command_rows": [
            {
                "Step": "Refresh next capped missing-price batch",
                "Command": "make price-refresh-loop DRY_RUN=1",
                "Reason": "Advance the broad-universe price frontier safely.",
                "SourceContext": "data/imports/prices.csv fallback plus optional Yahoo refresh",
                "FreshnessContext": "capped refresh; verify source/freshness after merge",
            }
        ]
    }

    console = dashboard.build_next_action_console_frame(readiness, None, payload, limit=8)
    cards = dashboard.next_action_console_cards(console)
    rendered = " ".join(str(value) for value in list(console.to_dict("records")) + cards for value in value.values()).lower()
    card_kickers = {str(card["kicker"]).title() for card in cards}

    assert set(console["action_category"]).issuperset(
        {
            "Price Coverage Batch",
            "Fundamentals / DCF Unlock",
            "Peer Mapping Unlock",
            "Earnings Import Setup",
            "Analyst Estimates Import Setup",
            "Import Validation / Rejected Rows",
            "Single-Stock Review",
        }
    )
    assert card_kickers.issuperset(
        {
            "Price Coverage Batch",
            "Fundamentals / Dcf Unlock",
            "Peer Mapping Unlock",
            "Earnings Import Setup",
            "Analyst Estimates Import Setup",
            "Import Validation / Rejected Rows",
            "Single-Stock Review",
        }
    )
    assert len(cards) <= 8
    assert "make price-refresh-loop dry_run=1" in rendered
    assert "dry-run the loop instead of repeating 25-ticker refreshes manually" in rendered
    assert "make sec-stage-queue top_n=25" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "make imports-validate" in rendered
    assert "rejected-row reports" in rendered
    assert "when to use" in rendered
    assert "check after" in rendered
    assert "can analyze now" in rendered
    assert "still locked" in rendered
    assert "copy next" in rendered
    assert "peer trend needs mapped peer price history" in rendered
    assert "peer valuation needs trusted peer mappings and peer metrics" in rendered
    assert "the report withholds unsupported valuation, peer, earnings, and estimate sections" in rendered
    assert "dry-run-first capped yahoo refresh loops" in rendered
    assert "capped refresh; verify source/freshness after merge" in rendered
    assert "output_to_check" in console.columns
    assert "when_to_use" in console.columns
    assert "single-stock report" in rendered
    assert "active universe" in rendered
    assert "scope" in console.columns
    single_row = console.loc[console["action_category"].eq("Single-Stock Review")].iloc[0]
    assert str(single_row["command"]).startswith("make stock-report-md TICKER=")
    assert "source_freshness_note" in " ".join(console.columns)
    assert "scope" in console.columns
    assert "dashboard does not execute" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_next_action_console_plain_english_states_cover_unlock_lanes():
    price_state = dashboard.next_action_console_plain_english_state("Price Coverage Batch")
    fundamentals_state = dashboard.next_action_console_plain_english_state("Fundamentals / DCF Unlock")
    peer_state = dashboard.next_action_console_plain_english_state("Peer Mapping Unlock")
    earnings_state = dashboard.next_action_console_plain_english_state("Earnings Import Setup")
    estimates_state = dashboard.next_action_console_plain_english_state("Analyst Estimates Import Setup")
    single_state = dashboard.next_action_console_plain_english_state("Single-Stock Review")
    rendered = " ".join(
        value
        for state in [price_state, fundamentals_state, peer_state, earnings_state, estimates_state, single_state]
        for value in state.values()
    ).lower()

    assert "setup, momentum, liquidity, and market-context review" in rendered
    assert "dcf interpretation stay locked" in rendered
    assert "peer trend needs mapped peer price history" in rendered
    assert "peer valuation needs trusted peer mappings and peer metrics" in rendered
    assert "earnings context stays unavailable until trusted local rows pass validate, preview, and apply" in rendered
    assert "consensus is context, not a conclusion" in rendered
    assert "source freshness, dcf boundary, peer boundary, and optional-context gaps" in rendered
    assert "unsupported valuation, peer, earnings, and estimate sections" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_next_action_console_prioritizes_active_samples_without_hiding_broad_counts():
    readiness = pd.DataFrame(
        {
            "ticker": ["AAA", "COHR", "LITE", "A", "QQQ"],
            "in_active_universe": [False, True, True, False, True],
            "price_ready": [True, True, True, True, True],
            "fundamentals_ready": [False, True, True, True, True],
            "dcf_ready": [False, True, True, True, False],
            "peer_ready": [False, False, False, False, False],
            "earnings_ready": [False, False, False, False, False],
            "analyst_estimates_ready": [False, False, False, False, False],
            "asset_type": ["company", "company", "company", "company", "etf"],
            "decision_bucket": ["Blocked by Data", "Research Now", "Research Now", "Research Now", "Monitor"],
        }
    )

    console = dashboard.build_next_action_console_frame(readiness, None, None, limit=8)
    rendered = " ".join(str(value) for value in console.to_numpy().ravel()).lower()
    peer_row = console.loc[console["action_category"].eq("Peer Mapping Unlock")].iloc[0]
    fundamentals_row = console.loc[console["action_category"].eq("Fundamentals / DCF Unlock")].iloc[0]
    single_row = console.loc[console["action_category"].eq("Single-Stock Review")].iloc[0]

    assert peer_row["ticker_count"] == 3
    assert peer_row["scope"] == "active first, then broad universe"
    assert peer_row["sample_tickers"].split(",")[:2] == ["COHR", "LITE"]
    assert fundamentals_row["ticker_count"] == 1
    assert fundamentals_row["sample_tickers"] == "AAA"
    assert single_row["command"] == "make stock-report-md TICKER=COHR"
    assert single_row["sample_tickers"].split(",")[:3] == ["COHR", "LITE", "QQQ"]
    assert "one ticker explained in plain language" in single_row["when_to_use"].lower()
    assert "markdown report" in single_row["output_to_check"].lower()
    assert "dashboard does not execute" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_next_action_console_sanitizes_uncapped_batch_commands():
    assert dashboard.safe_action_console_command("Price Coverage Batch", "make price-refresh") == "make price-refresh-loop DRY_RUN=1"
    assert dashboard.safe_action_console_command("Price Coverage Batch", "make price-refresh-loop DRY_RUN=1") == "make price-refresh-loop DRY_RUN=1"
    assert dashboard.safe_action_console_command("Price Coverage Batch", "make price-refresh TICKERS=NVDA") == "make price-refresh TICKERS=NVDA"
    assert dashboard.safe_action_console_command("Fundamentals / DCF Unlock", "make sec-stage") == "make sec-stage-queue TOP_N=25"
    assert dashboard.safe_action_console_command("Peer Mapping Unlock", "make templates") == "make peer-mapping-queue TOP_N=25"
    assert dashboard.safe_action_console_command("Import Validation / Rejected Rows", "make imports-apply") == "make imports-apply"
    assert dashboard.safe_action_console_command("Single-Stock Review", "make stock-report") == "make stock-report-md TICKER=META"
    assert dashboard.safe_action_console_command("Single-Stock Review", "make stock-report TICKER=NVDA") == "make stock-report-md TICKER=NVDA"


def test_import_validation_rejected_row_cards_show_safe_manual_workflow():
    cards = dashboard.import_validation_rejected_row_cards()
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "data/staged/" in rendered
    assert "data/imports/" in rendered
    assert "data/rejected/price_import_rejected.csv" in rendered
    assert "data/rejected/fundamentals_import_rejected.csv" in rendered
    assert "data/rejected/peers_import_rejected.csv" in rendered
    assert "data/rejected/earnings_import_rejected.csv" in rendered
    assert "data/rejected/analyst_estimates_import_rejected.csv" in rendered
    assert "data/rejected/universe_rejected.csv" in rendered
    assert "clean/header-only" in rendered
    assert "missing report" in rendered
    assert "regenerate missing reports" in rendered
    assert "dashboard displays this command for copying" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_import_health_frame_counts_header_only_and_rejected_rows(tmp_path: Path):
    for folder in [
        "data/rejected",
        "data/imports",
        "data/staged/prices",
        "data/staged/fundamentals",
        "data/staged/earnings",
        "data/staged/analyst_estimates",
        "data/staged/universe",
    ]:
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)

    (tmp_path / "data/imports/prices.csv").write_text("ticker,date,close\nAAA,2026-01-01,10\n", encoding="utf-8")
    (tmp_path / "data/staged/prices/manual.csv").write_text("ticker,date,close\nBBB,2026-01-01,20\n", encoding="utf-8")
    (tmp_path / "data/rejected/price_import_rejected.csv").write_text("ticker,error\n", encoding="utf-8")
    (tmp_path / "data/rejected/fundamentals_import_rejected.csv").write_text("ticker,error\nBAD,missing source\n", encoding="utf-8")

    frame = dashboard.import_health_frame(tmp_path)
    by_dataset = frame.set_index("dataset")

    assert by_dataset.loc["prices", "canonical_import_rows"] == 1
    assert by_dataset.loc["prices", "staged_file_count"] == 1
    assert by_dataset.loc["prices", "rejected_status"] == "clean/header-only"
    assert by_dataset.loc["fundamentals", "rejected_status"] == "has rejected rows"
    assert by_dataset.loc["fundamentals", "rejected_row_count"] == 1
    assert by_dataset.loc["peers", "rejected_status"] == "missing report"
    assert by_dataset.loc["prices", "copy_only_note"] == "Dashboard displays copyable commands only and does not run imports."
    assert set(["make imports-validate", "make imports-preview", "make imports-apply"]).issubset(
        set(frame[["validation_command", "preview_command", "apply_command"]].stack().tolist())
    )


def test_import_validation_rejected_row_cards_surface_missing_report_paths():
    frame = pd.DataFrame(
        [
            {
                "dataset": "prices",
                "rejected_report": "data/rejected/price_import_rejected.csv",
                "rejected_row_count": 0,
                "rejected_status": "clean/header-only",
                "staged_file_count": 0,
            },
            {
                "dataset": "peers",
                "rejected_report": "data/rejected/peers_import_rejected.csv",
                "rejected_row_count": 0,
                "rejected_status": "missing report",
                "staged_file_count": 0,
            },
        ]
    )

    cards = dashboard.import_validation_rejected_row_cards(frame)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    rejected_card = next(card for card in cards if card["kicker"] == "REJECTED ROWS")

    assert rejected_card["title"] == "1 clean/header-only, 1 missing report(s)"
    assert "data/rejected/peers_import_rejected.csv" in rendered
    assert "missing report path(s)" in rendered
    assert "regenerate missing reports" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_active_universe_unlock_cockpit_joins_import_health_and_copy_only_commands():
    readiness = pd.DataFrame(
        [
            {
                "ticker": "META",
                "asset_type": "company",
                "in_active_universe": True,
                "overall_readiness_state": "partial",
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "blocked_features": "fundamentals, dcf, peer, earnings, analyst_estimates",
                "next_action": "Complete trusted fundamentals for META.",
            },
            {
                "ticker": "APLD",
                "asset_type": "company",
                "in_active_universe": True,
                "overall_readiness_state": "blocked",
                "price_ready": False,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "blocked_features": "price, fundamentals, dcf, peer",
                "next_action": "Import price rows through the preview-first workflow or refresh the price provider for APLD.",
            },
            {
                "ticker": "BROAD",
                "asset_type": "company",
                "in_active_universe": False,
                "overall_readiness_state": "blocked",
                "price_ready": False,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "blocked_features": "price",
                "next_action": "Should not render.",
            },
            {
                "ticker": "QQQ",
                "asset_type": "etf",
                "in_active_universe": True,
                "overall_readiness_state": "partial",
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "blocked_features": "fundamentals, dcf, peer, earnings, analyst_estimates",
                "next_action": "Add source-backed peer mappings and peer metrics for QQQ.",
            },
        ]
    )
    decisions = pd.DataFrame(
        [
            {
                "ticker": "META",
                "decision_bucket": "Blocked by Data",
                "decision_subtype": "Blocked by Data - Missing Fundamentals",
                "primary_blocker": "fundamentals",
                "next_best_action": "Run make focus-fundamentals TICKER=META.",
            },
            {
                "ticker": "APLD",
                "decision_bucket": "Blocked by Data",
                "decision_subtype": "Blocked by Data - Missing Price",
                "primary_blocker": "price",
                "next_best_action": "Run make focus-price TICKER=APLD.",
            },
            {
                "ticker": "QQQ",
                "decision_bucket": "Monitor",
                "decision_subtype": "ETF / Index Proxy - Peer Inputs Missing",
                "primary_blocker": "peers",
                "next_best_action": "Add source-backed peer mappings and peer metrics for QQQ.",
            },
        ]
    )
    import_health = pd.DataFrame(
        [
            {
                "dataset": "prices",
                "canonical_import_file": "data/imports/prices.csv",
                "rejected_report": "data/rejected/price_import_rejected.csv",
                "rejected_status": "clean/header-only",
                "rejected_row_count": 0,
            },
            {
                "dataset": "fundamentals",
                "canonical_import_file": "data/imports/fundamentals.csv",
                "rejected_report": "data/rejected/fundamentals_import_rejected.csv",
                "rejected_status": "has rejected rows",
                "rejected_row_count": 2,
            },
            {
                "dataset": "peers",
                "canonical_import_file": "data/imports/peers.csv",
                "rejected_report": "data/rejected/peers_import_rejected.csv",
                "rejected_status": "missing report",
                "rejected_row_count": 0,
            },
        ]
    )

    cockpit = dashboard.build_active_universe_unlock_frame(readiness, decisions, import_health)
    cards = dashboard.active_universe_unlock_cards(cockpit)
    rendered = " ".join(str(value) for value in cockpit.astype(str).to_numpy().ravel().tolist() + [str(value) for card in cards for value in card.values()]).lower()

    assert list(cockpit["ticker"]) == ["APLD", "META", "QQQ"]
    assert "BROAD" not in set(cockpit["ticker"])
    assert cockpit.loc[cockpit["ticker"].eq("APLD"), "exact_command"].iloc[0] == "make focus-price TICKER=APLD"
    assert cockpit.loc[cockpit["ticker"].eq("APLD"), "queue_group"].iloc[0] == "Needs price coverage first"
    assert cockpit.loc[cockpit["ticker"].eq("META"), "exact_command"].iloc[0] == "make focus-fundamentals TICKER=META"
    assert cockpit.loc[cockpit["ticker"].eq("META"), "queue_group"].iloc[0] == "Price-ready but fundamentals missing"
    assert cockpit.loc[cockpit["ticker"].eq("QQQ"), "exact_command"].iloc[0] == "make stock-report-md TICKER=QQQ"
    assert cockpit.loc[cockpit["ticker"].eq("QQQ"), "queue_group"].iloc[0] == "Monitor context / DCF excluded"
    assert cockpit.loc[cockpit["ticker"].eq("QQQ"), "import_dataset"].iloc[0] == "monitor_context"
    assert cockpit.loc[cockpit["ticker"].eq("META"), "trusted_input_needed"].iloc[0].startswith(
        "Trusted fundamentals for META"
    )
    assert cockpit.loc[cockpit["ticker"].eq("META"), "validation_sequence"].iloc[0].startswith(
        "make focus-fundamentals TICKER=META"
    )
    assert cockpit.loc[cockpit["ticker"].eq("QQQ"), "trusted_input_needed"].iloc[0].startswith(
        "No peer import is required"
    )
    assert cockpit.loc[cockpit["ticker"].eq("QQQ"), "validation_sequence"].iloc[0].startswith(
        "make stock-report-md TICKER=QQQ"
    )
    assert "operating-company dcf and peer valuation stay excluded" in rendered
    assert "queue groups:" in rendered
    assert "needs price coverage first: 1" in rendered
    assert "price-ready but fundamentals missing: 1" in rendered
    assert "monitor context / dcf excluded: 1" in rendered
    assert "monitor context: 1" in rendered
    assert "monitor_context: 1" not in rendered
    assert "monitor-context row(s) use stock-report review instead of import files" in rendered
    assert "no import file is required for monitor context" in rendered
    assert "data/rejected/price_import_rejected.csv" in rendered
    assert "data/rejected/fundamentals_import_rejected.csv" in rendered
    assert "data/rejected/peers_import_rejected.csv" not in rendered
    assert "clean/header-only" in rendered
    assert "has rejected rows" in rendered
    assert "copy-only command" in rendered
    assert "active universe" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_active_universe_drilldown_surfaces_missing_fields_and_validation_paths():
    readiness = pd.DataFrame(
        [
            {
                "ticker": "META",
                "asset_type": "company",
                "in_active_universe": True,
                "overall_readiness_state": "partial",
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "blocked_features": "fundamentals, dcf, peer, earnings, analyst_estimates",
                "missing_data": "fundamentals: shares_outstanding",
                "next_action": "Complete trusted fundamentals for META.",
                "updated_at": "2026-05-31T00:00:00+00:00",
            },
            {
                "ticker": "QQQ",
                "asset_type": "etf",
                "in_active_universe": True,
                "overall_readiness_state": "partial",
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "blocked_features": "fundamentals, dcf, peer, earnings, analyst_estimates",
                "missing_data": "peer mapping",
                "next_action": "Add source-backed peer mappings and peer metrics for QQQ.",
                "updated_at": "2026-05-31T00:00:00+00:00",
            },
            {
                "ticker": "BROAD",
                "asset_type": "company",
                "in_active_universe": False,
                "overall_readiness_state": "blocked",
                "price_ready": False,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "blocked_features": "price",
                "missing_data": "price rows",
                "next_action": "Should not render.",
            },
        ]
    )
    decisions = pd.DataFrame(
        [
            {
                "ticker": "META",
                "decision_bucket": "Blocked by Data",
                "decision_subtype": "Blocked by Data - Missing Fundamentals",
                "primary_blocker": "fundamentals",
                "next_best_action": "Run make focus-fundamentals TICKER=META.",
            },
            {
                "ticker": "QQQ",
                "decision_bucket": "Monitor",
                "decision_subtype": "ETF / Index Proxy - Peer Inputs Missing",
                "primary_blocker": "peers",
                "next_best_action": "Add source-backed peer mappings and peer metrics for QQQ.",
            },
        ]
    )
    import_health = pd.DataFrame(
        [
            {
                "dataset": "fundamentals",
                "staged_folder": "data/staged/fundamentals/",
                "canonical_import_file": "data/imports/fundamentals.csv",
                "rejected_report": "data/rejected/fundamentals_import_rejected.csv",
                "rejected_status": "clean/header-only",
                "rejected_row_count": 0,
            },
            {
                "dataset": "peers",
                "staged_folder": "",
                "canonical_import_file": "data/imports/peers.csv",
                "rejected_report": "data/rejected/peers_import_rejected.csv",
                "rejected_status": "missing report",
                "rejected_row_count": 0,
            },
        ]
    )
    dcf = pd.DataFrame(
        [
            {
                "ticker": "META",
                "missing_dcf_fields": "shares_outstanding, revenue",
                "reason_not_ready": "missing shares_outstanding, revenue",
            },
            {
                "ticker": "QQQ",
                "missing_dcf_fields": "fundamentals unavailable",
                "reason_not_ready": "ETF/index proxies are excluded from operating-company DCF.",
            },
        ]
    )
    peers = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "missing_peer_reason": "needs at least 2 source-backed peer mappings",
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": False,
                "next_peer_action": "Add at least 2 source-backed peer mappings for QQQ in data/imports/peers.csv.",
            }
        ]
    )
    earnings = pd.DataFrame({"ticker": ["META", "QQQ"], "missing_fields": ["trusted_local_earnings_row", "trusted_local_earnings_row"]})
    estimates = pd.DataFrame(
        {"ticker": ["META", "QQQ"], "missing_fields": ["trusted_local_analyst_estimate_row", "trusted_local_analyst_estimate_row"]}
    )
    coverage = pd.DataFrame({"ticker": ["META", "QQQ"], "price_rows": [300, 25], "missing_price_reason": ["", ""]})

    drilldown = dashboard.build_active_universe_drilldown_frame(
        readiness,
        decisions,
        import_health,
        dcf,
        peers,
        earnings,
        estimates,
        coverage,
    )
    rendered = " ".join(drilldown.astype(str).to_numpy().ravel().tolist()).lower()

    assert list(drilldown["ticker"]) == ["META", "QQQ"]
    assert "BROAD" not in set(drilldown["ticker"])
    assert drilldown.loc[drilldown["ticker"].eq("META"), "blocker_area"].iloc[0] == "fundamentals"
    assert "shares_outstanding" in drilldown.loc[drilldown["ticker"].eq("META"), "missing_fields"].iloc[0]
    assert "data/staged/fundamentals/" in rendered
    assert "data/imports/fundamentals.csv" in rendered
    assert "make focus-fundamentals ticker=meta" in rendered
    assert drilldown.loc[drilldown["ticker"].eq("QQQ"), "blocker_area"].iloc[0] == "monitor_context"
    assert "operating-company dcf and peer-relative valuation are excluded" in rendered
    assert "no peer import is required for etf/index/fund monitor context" in rendered
    assert "make stock-report-md ticker=qqq" in rendered
    assert "make focus-peers ticker=qqq" not in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "copy-only drilldown" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_active_unlock_queue_group_labels_dcf_ready_peer_blocked_rows():
    row = pd.Series(
        {
            "asset_type": "company",
            "price_ready": True,
            "fundamentals_ready": True,
            "dcf_ready": True,
            "peer_ready": False,
        }
    )

    assert dashboard.active_unlock_queue_group(row, "peers") == "DCF-ready but peer-blocked"
    assert dashboard.active_unlock_queue_group(row, "fundamentals") == "Fundamentals / DCF unlock"


def test_feature_readiness_cards_show_feature_level_product_status():
    feature_summary = pd.DataFrame(
        [
            {
                "feature": "price",
                "ready_count": 240,
                "partial_count": 0,
                "blocked_count": 3298,
                "excluded_count": 0,
                "total_count": 3538,
                "top_blocker": "needs price rows",
                "next_action": "make price-worklist TOP_N=25",
                "dashboard_section": "Price Coverage",
            },
            {
                "feature": "dcf",
                "ready_count": 23,
                "partial_count": 0,
                "blocked_count": 3513,
                "excluded_count": 2,
                "total_count": 3538,
                "top_blocker": "missing fundamentals",
                "next_action": "make dcf-readiness",
                "dashboard_section": "Value / Re-rating",
            },
        ]
    )

    cards = dashboard.feature_readiness_cards(feature_summary)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "dcf: 23/3538 ready" in rendered
    assert "price: 240/3538 ready" in rendered
    assert "make price-refresh-loop dry_run=1" in rendered
    assert "avoids repeating small worklists manually" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trade" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "sell" not in rendered


def test_readiness_product_cards_use_plain_missing_output_language():
    feature_cards = dashboard.feature_readiness_cards(None)
    peer_cards = dashboard.peer_readiness_product_cards(None)
    rendered = " ".join(str(value) for card in feature_cards + peer_cards for value in card.values()).lower()

    assert feature_cards[0]["title"] == "Feature readiness not ready yet"
    assert peer_cards[0]["title"] == "Peer readiness not ready yet"
    assert feature_cards[0]["command"] == "make readiness"
    assert peer_cards[0]["command"] == "make readiness"
    assert "not generated" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_feature_readiness_cards_show_optional_context_as_locked_workflow():
    feature_summary = pd.DataFrame(
        [
            {
                "feature": "earnings",
                "ready_count": 0,
                "partial_count": 0,
                "blocked_count": 3538,
                "excluded_count": 0,
                "total_count": 3538,
                "top_blocker": "earnings: trusted local CSV input",
                "next_action": "make import-earnings",
                "dashboard_section": "Optional Context",
            },
            {
                "feature": "analyst_estimates",
                "ready_count": 0,
                "partial_count": 0,
                "blocked_count": 3538,
                "excluded_count": 0,
                "total_count": 3538,
                "top_blocker": "analyst_estimates: trusted local CSV input",
                "next_action": "make import-analyst-estimates",
                "dashboard_section": "Optional Context",
            },
        ]
    )

    cards = dashboard.feature_readiness_cards(feature_summary)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "earnings: 0/3538 ready" in rendered
    assert "analyst_estimates: 0/3538 ready" in rendered
    assert "intentionally locked" in rendered
    assert "schema-only templates" in rendered
    assert "data/staged/earnings/" in rendered
    assert "data/imports/earnings.csv" in rendered
    assert "data/staged/analyst_estimates/" in rendered
    assert "data/imports/analyst_estimates.csv" in rendered
    assert "make templates" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trade" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_readiness_recent_progress_cards_show_current_only_baseline_without_prior_snapshot():
    readiness = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "QQQ"],
            "in_active_universe": [True, False, True],
            "price_ready": [True, False, True],
            "dcf_ready": [True, False, False],
            "peer_ready": [False, False, True],
            "earnings_ready": [False, False, False],
            "analyst_estimates_ready": [False, False, False],
            "blocked_features": ["peer, earnings, analyst_estimates", "price, dcf, peer", "earnings, analyst_estimates"],
            "overall_readiness_state": ["partial", "blocked", "partial"],
            "updated_at": ["2026-05-28T00:00:00+00:00", "2026-05-28T00:00:00+00:00", "2026-05-28T00:00:00+00:00"],
        }
    )
    feature_summary = pd.DataFrame(
        {
            "feature": ["price", "peer"],
            "blocked_count": [1, 2],
        }
    )

    cards = dashboard.readiness_recent_progress_cards(readiness, feature_summary_frame=feature_summary)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "2/3 price-ready" in rendered
    assert "current-only baseline" in rendered
    assert "no prior snapshot" in rendered
    assert "make readiness-snapshot" in rendered
    assert "ticker_readiness_report.previous.csv" in rendered
    assert "snapshot -> targeted update -> compare" in rendered
    assert "targeted refresh or import" in rendered
    assert "peer: 2" in rendered
    assert "copyable commands only" in rendered
    assert "external actions" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_readiness_recent_progress_cards_compare_prior_snapshot_and_newly_ready_tickers():
    current = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "in_active_universe": [True, True, False],
            "price_ready": [True, True, False],
            "dcf_ready": [False, True, False],
            "peer_ready": [False, False, False],
            "earnings_ready": [False, False, False],
            "analyst_estimates_ready": [False, False, False],
            "blocked_features": ["dcf, peer", "peer", "price, dcf, peer"],
            "overall_readiness_state": ["partial", "partial", "blocked"],
            "updated_at": ["2026-05-29T00:00:00+00:00", "2026-05-29T00:00:00+00:00", "2026-05-29T00:00:00+00:00"],
        }
    )
    previous = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "price_ready": [True, False, False],
            "dcf_ready": [False, False, False],
            "peer_ready": [False, False, False],
            "earnings_ready": [False, False, False],
            "analyst_estimates_ready": [False, False, False],
        }
    )

    change_frame = dashboard.build_readiness_change_frame(current, previous)
    cards = dashboard.readiness_recent_progress_cards(
        current,
        previous,
        previous_snapshot_label="data/reports/ticker_readiness_report.previous.csv",
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    price_row = change_frame.loc[change_frame["feature"].eq("Price")].iloc[0]
    dcf_row = change_frame.loc[change_frame["feature"].eq("DCF")].iloc[0]

    assert int(price_row["delta_ready"]) == 1
    assert price_row["newly_ready_tickers"] == "BBB"
    assert int(dcf_row["delta_ready"]) == 1
    assert "price +1" in rendered
    assert "dcf +1" in rendered
    assert "newly ready tickers: bbb" in rendered
    assert "previous vs current" in rendered
    assert "data/reports/ticker_readiness_report.previous.csv" in rendered
    assert "snapshot -> targeted update -> compare" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_peer_readiness_product_cards_surface_specific_peer_blockers():
    peer_readiness = pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "peer_ready": True,
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
                "peer_blocker_type": "peer_valuation_blocked",
                "peer_count": 2,
                "ready_peer_count": 2,
                "next_peer_action": "Import DCF-ready fundamentals for mapped peers: AMD.",
            },
            {
                "ticker": "META",
                "peer_ready": False,
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "peer_count": 0,
                "ready_peer_count": 0,
                "next_peer_action": "Add at least 2 source-backed peer mappings for META in data/imports/peers.csv.",
            },
        ]
    )
    queue = pd.DataFrame({"ticker": ["META"], "priority": [1]})

    cards = dashboard.peer_readiness_product_cards(peer_readiness, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "1/2 ready" in rendered
    assert "missing peer mapping" in rendered
    assert "make focus-peers ticker=meta" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_peer_mapping_studio_filters_dcf_ready_peer_blockers_and_keeps_commands_safe():
    peer_readiness = pd.DataFrame(
        [
            {
                "ticker": "A",
                "peer_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "mapping_status": "missing_mapping",
                "peer_count": 0,
                "ready_peer_count": 0,
                "next_peer_action": "Add at least 2 source-backed peer mappings for A in data/imports/peers.csv.",
            },
            {
                "ticker": "META",
                "peer_ready": False,
                "peer_blocker_type": "peer_fundamentals_missing",
                "mapping_status": "mapped",
                "peer_count": 2,
                "ready_peer_count": 2,
                "peer_missing_fundamentals_tickers": "GOOGL, AMZN",
                "next_peer_action": "Import trusted fundamentals for mapped peers: GOOGL, AMZN.",
            },
            {
                "ticker": "NVDA",
                "peer_ready": True,
                "peer_blocker_type": "",
                "mapping_status": "mapped",
                "peer_trend_comparison_ready": True,
                "peer_count": 2,
                "ready_peer_count": 2,
            },
        ]
    )
    readiness = pd.DataFrame(
        [
            {"ticker": "A", "name": "Agilent", "asset_type": "company", "dcf_ready": True, "price_ready": True, "in_active_universe": False},
            {"ticker": "META", "name": "Meta", "asset_type": "company", "dcf_ready": True, "price_ready": True, "in_active_universe": True},
            {"ticker": "NVDA", "name": "Nvidia", "asset_type": "company", "dcf_ready": True, "price_ready": True, "in_active_universe": True},
        ]
    )
    unlock = pd.DataFrame(
        [
            {
                "ticker": "A",
                "priority": 1,
                "unlock_stage": "add_source_backed_peer_mappings",
                "workflow_group": "dcf_ready_peer_mapping",
                "workflow_scope": "master_universe",
                "next_action_summary": "Add at least two trusted, source-backed peer rows; fallback sector/industry context is not trusted peer data.",
                "peer_trend_status": "peer_trend_blocked",
                "peer_valuation_status": "peer_valuation_blocked",
                "next_input_file": "data/imports/peers.csv",
                "validation_sequence": "make templates -> make imports-validate -> make imports-preview -> make imports-apply",
                "focus_command": "make focus-peers TICKER=A",
                "example_command": "make peer-mapping-queue TOP_N=25",
                "copy_only_note": "Copy commands only; review import draft rows before applying local CSV changes.",
            },
            {
                "ticker": "META",
                "priority": 1,
                "unlock_stage": "add_peer_fundamentals",
                "workflow_group": "peer_valuation_unlock",
                "workflow_scope": "active_universe",
                "next_action_summary": "Add trusted peer fundamentals before showing peer valuation conclusions.",
                "peer_trend_status": "peer_trend_possible",
                "peer_valuation_status": "peer_valuation_blocked",
                "next_input_file": "data/imports/fundamentals.csv or data/staged/fundamentals/",
                "validation_sequence": "make focus-fundamentals TICKER=<peer> -> make imports-validate",
                "focus_command": "make focus-peers TICKER=META",
                "example_command": "make peer-mapping-queue TOP_N=25",
                "copy_only_note": "Copy commands only; review import draft rows before applying local CSV changes.",
            },
        ]
    )

    studio = dashboard.build_peer_mapping_studio_frame(
        peer_readiness,
        readiness,
        unlock,
        filter_mode="DCF-ready but peer-blocked",
        row_limit=10,
    )
    missing_mapping = dashboard.build_peer_mapping_studio_frame(
        peer_readiness,
        readiness,
        unlock,
        filter_mode="Missing peer mapping",
        row_limit=10,
    )
    fundamentals = dashboard.build_peer_mapping_studio_frame(
        peer_readiness,
        readiness,
        unlock,
        filter_mode="Peer fundamentals missing",
        ticker_search="googl",
        row_limit=10,
    )
    trend_ready = dashboard.build_peer_mapping_studio_frame(
        peer_readiness,
        readiness,
        unlock,
        filter_mode="Peer trend comparison ready",
        row_limit=10,
    )

    assert list(studio["ticker"]) == ["META", "A"]
    assert list(missing_mapping["ticker"]) == ["A"]
    assert list(fundamentals["ticker"]) == ["META"]
    assert list(trend_ready["ticker"]) == ["NVDA"]
    columns = dashboard.peer_mapping_studio_table_columns(studio)
    rendered = " ".join(str(value) for value in studio[columns].to_numpy().ravel()).lower()
    assert "unlock_stage" in columns
    assert "workflow_group" in columns
    assert "workflow_scope" in columns
    assert "next_action_summary" in columns
    assert "peer_trend_status" in columns
    assert "peer_valuation_status" in columns
    assert "next_input_file" in columns
    assert "validation_sequence" in columns
    assert "copy_only_note" in columns
    assert "peer_trend_possible" in rendered
    assert "peer_valuation_blocked" in rendered
    assert "fallback sector/industry context is not trusted peer data" in rendered
    assert "showing peer valuation conclusions" in rendered
    assert "data/imports/fundamentals.csv" in rendered
    assert "make focus-peers ticker=a" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_first_peer_mapping_unlock_frame_prioritizes_source_backed_mapping_workflow():
    worklist = pd.DataFrame(
        [
            {
                "ticker": "A",
                "priority": 2,
                "workflow_group": "peer_metric_follow_through",
            },
            {
                "ticker": "META",
                "priority": 1,
                "workflow_group": "dcf_ready_peer_mapping",
            },
        ]
    )

    frame = dashboard.first_peer_mapping_unlock_frame(worklist)
    rendered = " ".join(frame.astype(str).to_numpy().ravel()).lower()

    assert frame["Step"].tolist() == [
        "1. Pick the next peer-limited company",
        "2. Add source-backed mappings only",
        "3. Validate before applying",
        "4. Rebuild peer readiness",
    ]
    assert frame.iloc[0]["Copy Command"] == "make focus-peers TICKER=META"
    assert frame.iloc[1]["Copy Command"] == "make templates"
    assert frame.iloc[1]["Trusted Input"] == "data/imports/peers.csv"
    assert "sector or industry fallback is not trusted peer data" in rendered
    assert "make imports-validate && make imports-preview && make imports-apply" in rendered
    assert "make readiness && make peer-mapping-queue top_n=25" in rendered
    assert "peer readiness should improve only after mapped rows pass validation" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_first_peer_mapping_unlock_cards_keep_peer_valuation_gated():
    cards = dashboard.first_peer_mapping_unlock_cards(next_ticker="COHR")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["command"] == "make focus-peers TICKER=COHR"
    assert cards[1]["command"] == "make templates"
    assert cards[2]["command"] == "make imports-validate && make imports-preview && make imports-apply && make readiness && make peer-mapping-queue TOP_N=25"
    assert "no guessed peers" in rendered
    assert "fallback is not input" in rendered
    assert "do not show peer-relative valuation until source-backed mappings" in rendered
    assert "after a rebuild" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_peer_mapping_studio_fills_missing_worklist_metadata_for_active_dcf_blockers():
    peer_readiness = pd.DataFrame(
        [
            {
                "ticker": "COHR",
                "peer_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "mapping_status": "missing_mapping",
                "peer_count": 0,
                "ready_peer_count": 0,
                "next_peer_action": "Add at least 2 source-backed peer mappings for COHR in data/imports/peers.csv.",
            },
            {
                "ticker": "A",
                "peer_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "mapping_status": "missing_mapping",
                "peer_count": 0,
                "ready_peer_count": 0,
                "next_peer_action": "Add at least 2 source-backed peer mappings for A in data/imports/peers.csv.",
            },
        ]
    )
    readiness = pd.DataFrame(
        [
            {"ticker": "COHR", "name": "Coherent", "asset_type": "company", "dcf_ready": True, "price_ready": True, "in_active_universe": True},
            {"ticker": "A", "name": "Agilent", "asset_type": "company", "dcf_ready": True, "price_ready": True, "in_active_universe": False},
        ]
    )
    unlock = pd.DataFrame(
        [
            {
                "ticker": "A",
                "priority": 1,
                "workflow_group": "dcf_ready_peer_mapping",
                "workflow_scope": "master_universe",
                "next_action_summary": "Add at least two trusted, source-backed peer rows; fallback sector/industry context is not trusted peer data.",
                "focus_command": "make focus-peers TICKER=A",
            }
        ]
    )

    studio = dashboard.build_peer_mapping_studio_frame(
        peer_readiness,
        readiness,
        unlock,
        filter_mode="DCF-ready but peer-blocked",
        row_limit=10,
    )
    rendered = " ".join(str(value) for value in studio.to_numpy().ravel()).lower()

    assert list(studio["ticker"]) == ["COHR", "A"]
    assert studio.loc[studio["ticker"].eq("COHR"), "priority"].iloc[0] == 1
    assert studio.loc[studio["ticker"].eq("COHR"), "workflow_scope"].iloc[0] == "active_universe"
    assert studio.loc[studio["ticker"].eq("COHR"), "workflow_group"].iloc[0] == "dcf_ready_peer_mapping"
    assert studio.loc[studio["ticker"].eq("COHR"), "focus_command"].iloc[0] == "make focus-peers TICKER=COHR"
    assert "source-backed peer" in studio.loc[studio["ticker"].eq("COHR"), "next_action"].iloc[0]
    assert "optional context" not in studio.loc[studio["ticker"].eq("COHR"), "next_action"].iloc[0].lower()
    assert "data/imports/peers.csv" in rendered
    assert "make imports-validate" in rendered
    assert "fallback sector/industry context is not trusted peer data" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_peer_unlock_operator_cards_group_priorities_scope_and_next_input():
    worklist = pd.DataFrame(
        [
            {
                "ticker": "A",
                "priority": 1,
                "workflow_group": "dcf_ready_peer_mapping",
                "workflow_scope": "master_universe",
                "next_action_summary": "Add at least two trusted, source-backed peer rows; fallback sector/industry context is not trusted peer data.",
                "next_input_file": "data/imports/peers.csv",
                "validation_sequence": "make templates -> make imports-validate -> make imports-preview -> make imports-apply",
                "focus_command": "make focus-peers TICKER=A",
            },
            {
                "ticker": "META",
                "priority": 1,
                "workflow_group": "dcf_ready_peer_mapping",
                "workflow_scope": "active_universe",
                "next_action_summary": "Add source-backed peers for active universe DCF workflow.",
                "next_input_file": "data/imports/peers.csv",
                "validation_sequence": "make templates -> make imports-validate -> make imports-preview -> make imports-apply",
                "focus_command": "make focus-peers TICKER=META",
            },
            {
                "ticker": "APLD",
                "priority": 3,
                "workflow_group": "peer_mapping_after_price",
                "workflow_scope": "master_universe",
                "next_action_summary": "Add prices first, then peer mappings.",
                "next_input_file": "data/imports/peers.csv",
                "validation_sequence": "make templates -> make imports-validate",
                "focus_command": "make focus-peers TICKER=APLD",
            },
        ]
    )

    cards = dashboard.peer_unlock_operator_cards(worklist)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "p1: 2" in rendered
    assert "p3: 1" in rendered
    assert "active universe: 1" in rendered
    assert "master universe: 2" in rendered
    assert "active-universe queue: 0" in rendered
    assert "dcf-ready but peer-blocked: 0" in rendered
    assert "meta" in rendered
    assert "data/imports/peers.csv" in rendered
    assert "make imports-preview" in rendered
    assert "dcf ready peer mapping" in rendered
    assert "peer trend can use mapped peer price history" in rendered
    assert "peer valuation waits for source-backed peer mappings and peer valuation inputs" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_peer_unlock_operator_cards_keep_etf_rows_in_monitor_context():
    worklist = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "priority": 1,
                "workflow_group": "dcf_ready_peer_mapping",
                "workflow_scope": "active_universe",
                "next_action_summary": "Add source-backed peers for QQQ.",
                "next_input_file": "data/imports/peers.csv",
                "validation_sequence": "make templates -> make imports-validate",
                "focus_command": "make focus-peers TICKER=QQQ",
            },
            {
                "ticker": "COHR",
                "priority": 1,
                "workflow_group": "dcf_ready_peer_mapping",
                "workflow_scope": "active_universe",
                "next_action_summary": "Add source-backed peers for COHR.",
                "next_input_file": "data/imports/peers.csv",
                "validation_sequence": "make templates -> make imports-validate -> make imports-preview -> make imports-apply",
                "focus_command": "make focus-peers TICKER=COHR",
            },
        ]
    )
    readiness = pd.DataFrame(
        [
            {"ticker": "QQQ", "asset_type": "etf", "in_active_universe": True},
            {"ticker": "COHR", "asset_type": "company", "in_active_universe": True, "dcf_ready": True, "peer_ready": False},
        ]
    )

    cards = dashboard.peer_unlock_operator_cards(worklist, readiness)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "cohr" in rendered
    assert "active-universe queue: 2" in rendered
    assert "dcf-ready but peer-blocked: 1" in rendered
    assert "make focus-peers ticker=cohr" in rendered
    assert "monitor proxy context" in rendered
    assert "make stock-report-md ticker=qqq" in rendered
    assert "make focus-peers ticker=qqq" not in rendered
    assert "ticker=<ticker>" not in rendered
    assert "peer valuation remains excluded" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trade" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_peer_mapping_studio_keeps_etf_missing_mappings_in_monitor_context():
    peer_readiness = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "peer_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "mapping_status": "missing_mapping",
                "peer_count": 0,
                "ready_peer_count": 0,
            },
            {
                "ticker": "COHR",
                "peer_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "mapping_status": "missing_mapping",
                "peer_count": 0,
                "ready_peer_count": 0,
            },
        ]
    )
    readiness = pd.DataFrame(
        [
            {"ticker": "QQQ", "asset_type": "etf", "in_active_universe": True, "dcf_ready": False, "price_ready": True},
            {"ticker": "COHR", "asset_type": "company", "in_active_universe": True, "dcf_ready": True, "price_ready": True},
        ]
    )
    unlock = pd.DataFrame(
        [
            {"ticker": "QQQ", "priority": 1, "focus_command": "make focus-peers TICKER=QQQ"},
            {"ticker": "COHR", "priority": 1, "focus_command": "make focus-peers TICKER=COHR"},
        ]
    )

    studio = dashboard.build_peer_mapping_studio_frame(
        peer_readiness,
        readiness,
        unlock,
        filter_mode="Missing peer mapping",
        row_limit=10,
    )
    qqq = studio.loc[studio["ticker"].eq("QQQ")].iloc[0]
    rendered = " ".join(str(value) for value in studio.to_numpy().ravel()).lower()

    assert qqq["workflow_group"] == "monitor_proxy_context"
    assert qqq["focus_command"] == "make stock-report-md TICKER=QQQ"
    assert qqq["validation_sequence"].startswith("make stock-report-md TICKER=QQQ")
    assert qqq["next_action"] == "ETF/index/fund rows use stock-report monitoring context; fallback sector or peer context is not trusted peer data."
    assert qqq["peer_valuation_status"] == "operating_company_dcf_excluded"
    assert "make focus-peers ticker=cohr" in rendered
    assert "make focus-peers ticker=qqq" not in rendered
    assert "ticker=<ticker>" not in rendered
    assert "fallback sector or peer context is not trusted peer data" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trade" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_fundamentals_dcf_diagnostic_cards_surface_price_ready_missing_fundamentals_and_paths(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    readiness = pd.DataFrame(
        [
            {
                "ticker": "META",
                "asset_type": "company",
                "in_active_universe": True,
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "next_action": "Complete trusted fundamentals for META; missing fields: shares_outstanding.",
            },
            {
                "ticker": "A",
                "asset_type": "company",
                "in_active_universe": False,
                "price_ready": True,
                "fundamentals_ready": True,
                "dcf_ready": True,
                "peer_ready": False,
                "next_action": "Add source-backed peer mappings and peer metrics for A.",
            },
            {
                "ticker": "QQQ",
                "asset_type": "etf",
                "in_active_universe": True,
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "next_action": "ETF/index proxy excluded from DCF.",
            },
        ]
    )
    dcf = pd.DataFrame(
        [
            {
                "ticker": "META",
                "asset_type": "company",
                "missing_dcf_fields": "shares_outstanding; free_cash_flow|revenue",
                "sec_user_agent_configured": True,
            },
            {"ticker": "A", "asset_type": "company", "missing_dcf_fields": "", "sec_user_agent_configured": True},
            {"ticker": "QQQ", "asset_type": "etf", "missing_dcf_fields": "", "sec_user_agent_configured": True},
        ]
    )

    cards = dashboard.fundamentals_dcf_diagnostic_cards(readiness, dcf)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    input_card = next(card for card in cards if card["kicker"] == "INPUT PATH")
    field_gap_card = next(card for card in cards if card["kicker"] == "DCF FIELD GAPS")

    assert "1 price-ready companies" in rendered
    assert "1 active-universe" in rendered
    assert "active fundamentals targets: meta" in rendered
    assert "meta" in rendered
    assert "shares_outstanding" in rendered
    assert "free_cash_flow" in rendered
    assert "revenue" in rendered
    assert field_gap_card["command"] == "make focus-fundamentals TICKER=META"
    assert "field-level blockers from the dcf readiness report, not company conclusions" in rendered
    assert "inspect meta with `make focus-fundamentals ticker=meta`" in rendered
    assert "before rerunning `make dcf-readiness`" in rendered
    assert "data/imports/fundamentals.csv or reviewed sec stage draft" in rendered
    assert "validation sequence: make imports-validate -> make imports-preview -> make imports-apply -> make dcf-readiness" in rendered
    assert "rejected-row report: data/rejected/fundamentals_import_rejected.csv" in rendered
    assert "excluded from operating-company dcf rather than failed valuation" in rendered
    assert "1 dcf-ready companies" in rendered
    assert input_card["title"] == "SEC import draft workflow"
    assert input_card["command"] == "make sec-stage TICKERS=META"
    assert "make sec-stage tickers=meta" in rendered
    assert "tickers=<ticker>" not in rendered
    assert "data/imports/fundamentals.csv" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "before claiming readiness improved" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_dcf_metric_counts_split_blocked_companies_from_exclusions():
    dcf = pd.DataFrame(
        [
            {"ticker": "NVDA", "asset_type": "company", "is_dcf_ready": True},
            {"ticker": "META", "asset_type": "company", "is_dcf_ready": False},
            {"ticker": "QQQ", "asset_type": "etf", "is_dcf_ready": False},
            {"ticker": "SMH", "asset_type": "fund", "is_dcf_ready": False},
        ]
    )

    counts = dashboard.data_health_dcf_metric_counts(dcf)

    assert counts == {"ready": 1, "blocked_company": 1, "excluded": 2}


def test_data_health_dcf_metric_counts_treat_missing_asset_type_as_company():
    dcf = pd.DataFrame(
        [
            {"ticker": "NVDA", "is_dcf_ready": True},
            {"ticker": "META", "is_dcf_ready": False},
        ]
    )

    counts = dashboard.data_health_dcf_metric_counts(dcf)

    assert counts == {"ready": 1, "blocked_company": 1, "excluded": 0}


def test_fundamentals_peer_unlock_story_cards_bridge_dcf_and_peer_workflow():
    readiness = pd.DataFrame(
        [
            {
                "ticker": "META",
                "asset_type": "company",
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "excluded_features": "",
            },
            {
                "ticker": "A",
                "asset_type": "company",
                "price_ready": True,
                "fundamentals_ready": True,
                "dcf_ready": True,
                "peer_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "excluded_features": "",
            },
            {
                "ticker": "NVDA",
                "asset_type": "company",
                "price_ready": True,
                "fundamentals_ready": True,
                "dcf_ready": True,
                "peer_ready": True,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "excluded_features": "",
            },
            {
                "ticker": "QQQ",
                "asset_type": "etf",
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "excluded_features": "dcf",
            },
        ]
    )
    peer_readiness = pd.DataFrame([{"ticker": "A"}, {"ticker": "NVDA"}])

    cards = dashboard.fundamentals_peer_unlock_story_cards(readiness, peer_readiness)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "WHAT THIS MEANS",
        "WHAT YOU CAN ANALYZE NOW",
        "FUNDAMENTALS STILL LOCKED",
        "PEER VALUATION STILL LOCKED",
        "OPTIONAL CONTEXT",
    ]
    assert "fundamentals unlock dcf; peers unlock relative context" in rendered
    assert "1 dcf + peer-ready company row(s)" in rendered
    assert "examples: nvda" in rendered
    assert "1 price-ready company row(s)" in rendered
    assert "examples: meta" in rendered
    assert "add trusted fundamentals before dcf math" in rendered
    assert "1 dcf-ready peer-blocked row(s)" in rendered
    assert "examples: a" in rendered
    assert "peer readiness rows loaded: 2" in rendered
    assert "sector fallback is not trusted peer valuation" in rendered
    assert "3 company row(s) still optional-context locked" in rendered
    assert "make sec-stage-queue top_n=25" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "make optional-context-worklist top_n=25" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_fundamentals_unlock_frame_explains_missing_inputs_before_raw_worklist():
    worklist = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "META",
                "in_active_universe": True,
                "has_fundamentals": "False",
                "missing_required_for_dcf": "free_cash_flow, shares_outstanding",
                "focus_command": "make focus-fundamentals TICKER=META",
            },
            {
                "priority": 2,
                "ticker": "NVDA",
                "in_active_universe": False,
                "has_fundamentals": True,
                "missing_required_for_dcf": "",
                "focus_command": "make stock-report-md TICKER=NVDA",
            },
        ]
    )

    frame = dashboard.data_health_fundamentals_unlock_frame(worklist)
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert list(frame.columns) == [
        "Ticker",
        "Priority Scope",
        "Current State",
        "What You Can Analyze Now",
        "What Is Still Locked",
        "Missing Trusted Inputs",
        "Trusted Input Path",
        "What This Unlocks",
        "No-Conclusion Boundary",
        "Next Safe Sequence",
        "Copy-Only Command",
        "Validation Path",
    ]
    assert frame["Ticker"].tolist() == ["META"]
    assert frame.iloc[0]["Priority Scope"] == "Priority 1; active universe"
    assert frame.iloc[0]["Copy-Only Command"] == "make focus-fundamentals TICKER=META"
    assert "price/setup context may be ready, but company fundamentals are still locked" in rendered
    assert "use ready price/setup/risk context only" in rendered
    assert "do not read company valuation yet" in rendered
    assert "fair value/share, and peer-relative valuation stay locked" in rendered
    assert "free cash flow, shares outstanding" in rendered
    assert "data/imports/fundamentals.csv or reviewed sec stage draft" in rendered
    assert "dcf readiness checks" in rendered
    assert "do not label the ticker undervalued, overvalued, or dcf-ready" in rendered
    assert "make sec-stage tickers=meta" in rendered
    assert "fill `data/imports/fundamentals.csv` with trusted manual rows" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "make dcf-readiness" in rendered
    assert "make imports-validate -> make imports-preview -> make imports-apply -> make dcf-readiness" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_fundamentals_unlock_cards_summarize_next_row_before_table():
    unlock_frame = pd.DataFrame(
        [
            {
                "Ticker": "META",
                "Priority Scope": "Priority 1; active universe",
                "What Is Still Locked": "Fundamental quality, DCF assumptions, fair value/share, and peer-relative valuation stay locked until trusted fundamentals pass readiness.",
                "Missing Trusted Inputs": "free cash flow, shares outstanding",
                "Trusted Input Path": "data/imports/fundamentals.csv or reviewed SEC stage draft",
                "No-Conclusion Boundary": "Do not label the ticker undervalued, overvalued, or DCF-ready until trusted fundamentals and DCF readiness pass.",
                "Next Safe Sequence": "1. Inspect `make focus-fundamentals TICKER=META`. 2. Use `make sec-stage TICKERS=META` when SEC_USER_AGENT is configured, or fill `data/imports/fundamentals.csv` with trusted manual rows. 3. Run `make imports-validate`, `make imports-preview`, `make imports-apply`, then `make dcf-readiness`.",
                "Copy-Only Command": "make focus-fundamentals TICKER=META",
                "Validation Path": "make imports-validate -> make imports-preview -> make imports-apply -> make dcf-readiness",
            }
        ]
    )

    cards = dashboard.data_health_fundamentals_unlock_cards(unlock_frame)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["FUNDAMENTALS QUEUE", "NEXT FUNDAMENTALS ROW", "TRUSTED INPUT PATH"]
    assert "1 row(s) need trusted fundamentals" in rendered
    assert "first row: priority 1; active universe" in rendered
    assert "open this before interpreting company valuation" in rendered
    assert "price/setup can be reviewed" in rendered
    assert "meta" in rendered
    assert "free cash flow, shares outstanding" in rendered
    assert "fair value/share, and peer-relative valuation stay locked" in rendered
    assert "boundary: do not label the ticker undervalued, overvalued, or dcf-ready" in rendered
    assert "make sec-stage tickers=meta" in rendered
    assert "trusted manual rows" in rendered
    assert "data/imports/fundamentals.csv or reviewed sec stage draft" in rendered
    assert "make focus-fundamentals ticker=meta" in rendered
    assert "make imports-validate && make imports-preview && make imports-apply" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_fundamentals_unlock_cards_handle_empty_queue_without_fake_counts():
    cards = dashboard.data_health_fundamentals_unlock_cards(pd.DataFrame())
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 1
    assert "no fundamentals unlock rows" in rendered
    assert "regenerate readiness before assuming coverage improved" in rendered
    assert cards[0]["command"] == "make readiness"


def test_data_health_peer_unlock_frame_explains_source_backed_peer_requirements():
    peer_queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "A",
                "workflow_scope": "master_universe",
                "workflow_group": "peer_valuation_unlock",
                "peer_trend_status": "peer_trend_possible",
                "peer_valuation_status": "peer_valuation_blocked",
                "has_peer_mapping": "False",
                "peer_ready": False,
                "missing_required_for_peer_relative": "peer mapping, peer fundamentals",
                "focus_command": "make focus-peers TICKER=A",
            },
            {
                "priority": 2,
                "ticker": "CRDO",
                "workflow_scope": "active_universe",
                "workflow_group": "peer_valuation_unlock",
                "peer_trend_status": "peer_trend_possible",
                "peer_valuation_status": "peer_valuation_blocked",
                "has_peer_mapping": "True",
                "peer_ready": False,
                "missing_required_for_peer_relative": "peer fundamentals",
                "next_input_file": "data/imports/fundamentals.csv or data/staged/fundamentals/",
                "validation_sequence": "make focus-fundamentals TICKER=<peer> -> make imports-validate",
                "focus_command": "make focus-peers TICKER=CRDO",
            },
            {
                "priority": 2,
                "ticker": "NVDA",
                "workflow_scope": "master_universe",
                "has_peer_mapping": True,
                "peer_ready": True,
                "missing_required_for_peer_relative": "",
                "focus_command": "make stock-report-md TICKER=NVDA",
            },
        ]
    )

    frame = dashboard.data_health_peer_unlock_frame(peer_queue)
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert list(frame.columns) == [
        "Ticker",
        "Priority Scope",
        "Current State",
        "Peer Trend State",
        "Peer Valuation State",
        "What You Can Analyze Now",
        "What Is Still Locked",
        "Trusted Peer Requirement",
        "Trusted Input Path",
        "What This Unlocks",
        "No-Conclusion Boundary",
        "Next Safe Sequence",
        "Copy-Only Command",
        "Validation Path",
    ]
    assert frame["Ticker"].tolist() == ["CRDO", "A"]
    assert frame.iloc[0]["Priority Scope"] == "Priority 2; active universe"
    assert frame.iloc[0]["Copy-Only Command"] == "make focus-peers TICKER=CRDO"
    assert "peer workflow is split: trend can be possible before peer valuation is ready" in rendered
    assert "peer trend possible" in rendered
    assert "peer valuation blocked" in rendered
    assert "peer trend context may be reviewed from mapped peer price history" in rendered
    assert "peer-relative premium/discount, peer valuation comparison, and peer dcf comparison stay locked" in rendered
    assert "peer mapping, peer fundamentals" in rendered
    assert "peer fundamentals" in rendered
    assert "data/imports/fundamentals.csv or data/staged/fundamentals/" in rendered
    assert "data/imports/peers.csv with source-backed peer mappings" in rendered
    assert "peer trend context first and peer valuation only after peer valuation inputs also pass" in rendered
    assert "do not show peer-relative valuation, peer premium/discount, or peer dcf comparison" in rendered
    assert "make templates" in rendered
    assert "add source-backed peer rows in `data/imports/peers.csv`" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "make readiness" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "make focus-fundamentals ticker=<peer> -> make imports-validate" in rendered
    assert "fill data/imports/peers.csv" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_peer_unlock_cards_summarize_next_row_before_table():
    unlock_frame = pd.DataFrame(
        [
            {
                "Ticker": "A",
                "Priority Scope": "Priority 1; active universe",
                "Peer Trend State": "peer trend possible",
                "Peer Valuation State": "peer valuation blocked",
                "What Is Still Locked": "Peer-relative premium/discount, peer valuation comparison, and peer DCF comparison stay locked until source-backed peer inputs pass readiness.",
                "Trusted Peer Requirement": "peer mapping, peer fundamentals",
                "Trusted Input Path": "data/imports/peers.csv with source-backed peer mappings",
                "No-Conclusion Boundary": "Do not show peer-relative valuation, peer premium/discount, or peer DCF comparison until trusted peer inputs pass readiness.",
                "Next Safe Sequence": "1. Inspect `make focus-peers TICKER=A`. 2. Run `make templates`, then add source-backed peer rows in `data/imports/peers.csv`. 3. Run `make imports-validate`, `make imports-preview`, and `make imports-apply`. 4. Run `make readiness` and `make peer-mapping-queue TOP_N=25` before reading peer valuation.",
                "Copy-Only Command": "make focus-peers TICKER=A",
                "Validation Path": "make templates -> fill data/imports/peers.csv -> make imports-validate -> make imports-preview -> make imports-apply -> make readiness -> make peer-mapping-queue TOP_N=25",
            }
        ]
    )

    cards = dashboard.data_health_peer_unlock_cards(unlock_frame)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["PEER QUEUE", "NEXT PEER ROW", "TRUSTED PEER PATH"]
    assert "1 row(s) need trusted peer inputs" in rendered
    assert "first row: priority 1; active universe" in rendered
    assert "prioritize active-universe and dcf-ready peer blockers before broad peer work" in rendered
    assert "open this before reading peer-relative valuation" in rendered
    assert "peer premium/discount stays locked" in rendered
    assert "trend: peer trend possible" in rendered
    assert "valuation: peer valuation blocked" in rendered
    assert "trusted peer requirement: peer mapping, peer fundamentals" in rendered
    assert "boundary: do not show peer-relative valuation, peer premium/discount, or peer dcf comparison" in rendered
    assert "add source-backed peer rows in `data/imports/peers.csv`" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "make readiness" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "data/imports/peers.csv with source-backed peer mappings" in rendered
    assert "make focus-peers ticker=a" in rendered
    assert cards[2]["command"] == "make templates && make imports-validate && make imports-preview && make imports-apply && make readiness && make peer-mapping-queue TOP_N=25"
    assert "fallback valuation" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_peer_unlock_cards_handle_empty_queue_without_fake_counts():
    cards = dashboard.data_health_peer_unlock_cards(None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 1
    assert "no peer unlock rows" in rendered
    assert "regenerate readiness before assuming peer valuation is available" in rendered
    assert cards[0]["command"] == "make readiness"


def test_first_fundamentals_unlock_frame_prefers_manual_path_without_sec_user_agent():
    frame = dashboard.first_fundamentals_unlock_frame(False, "META")
    rendered = " ".join(frame.astype(str).to_numpy().ravel()).lower()

    assert frame["Step"].tolist() == [
        "1. Pick the next company",
        "2. Choose the trusted input path",
        "3. Validate before applying",
        "4. Rebuild readiness",
    ]
    assert frame.iloc[0]["Copy Command"] == "make focus-fundamentals TICKER=META"
    assert frame.iloc[1]["Copy Command"] == "make templates"
    assert frame.iloc[1]["Trusted Input"] == "data/imports/fundamentals.csv"
    assert "sec_user_agent is missing" in rendered
    assert "data/imports/fundamentals.csv manual rows" in rendered
    assert "make imports-validate && make imports-preview && make imports-apply" in rendered
    assert "readiness counts should improve only after trusted rows pass validation" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_first_fundamentals_unlock_cards_use_sec_path_when_configured():
    cards = dashboard.first_fundamentals_unlock_cards(True, "NVDA")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["command"] == "make focus-fundamentals TICKER=NVDA"
    assert cards[1]["command"] == "make sec-stage TICKERS=NVDA"
    assert cards[2]["command"] == "make imports-validate && make imports-preview && make imports-apply"
    assert "sec company facts draft rows in data/staged/fundamentals/" in rendered
    assert "canonical reviewed import file is data/imports/fundamentals.csv" in rendered
    assert "do not treat fundamentals_ready or dcf_ready as improved" in rendered
    assert "no fabricated data" in rendered


def test_fundamentals_dcf_function_quality_frame_explains_scope_and_provenance():
    readiness = pd.DataFrame(
        [
            {
                "ticker": "META",
                "asset_type": "company",
                "in_active_universe": True,
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
            },
            {
                "ticker": "A",
                "asset_type": "company",
                "in_active_universe": False,
                "price_ready": True,
                "fundamentals_ready": True,
                "dcf_ready": True,
                "peer_ready": False,
            },
            {
                "ticker": "QQQ",
                "asset_type": "etf",
                "in_active_universe": True,
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
            },
        ]
    )
    dcf = pd.DataFrame(
        [
            {"ticker": "META", "asset_type": "company", "missing_dcf_fields": "shares_outstanding; free_cash_flow|revenue"},
            {"ticker": "A", "asset_type": "company", "missing_dcf_fields": ""},
            {"ticker": "QQQ", "asset_type": "etf", "missing_dcf_fields": ""},
        ]
    )

    frame = dashboard.fundamentals_dcf_function_quality_frame(readiness, dcf)
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert list(frame.columns) == [
        "Function Area",
        "Current Coverage",
        "Supported Today",
        "Not Supported Yet",
        "Logic Source",
        "Next Step",
    ]
    assert "trusted fundamentals" in rendered
    assert "1 fundamentals-ready company row(s)" in rendered
    assert "price-ready but missing fundamentals" in rendered
    assert "1 company row(s); 1 active-universe row(s)" in rendered
    assert "prioritizing which real fundamentals to stage" in rendered
    assert "creating placeholder values" in rendered
    assert "dcf-ready companies" in rendered
    assert "assumption and sensitivity review" in rendered
    assert "missing dcf fields" in rendered
    assert "shares_outstanding: 1" in rendered
    assert "free_cash_flow: 1" in rendered
    assert "revenue: 1" in rendered
    assert "treating missing inputs as a negative company signal" in rendered
    assert "dcf-ready but peer-blocked" in rendered
    assert "peer-relative valuation stays withheld" in rendered
    assert "fallback sector context is not trusted peer valuation" in rendered
    assert "etf / index / fund rows" in rendered
    assert "1 row(s) excluded from operating-company dcf" in rendered
    assert "project asset-type gating" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_fundamentals_dcf_unlock_copy_uses_guide_language_not_diagnostics():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")

    assert "Fundamentals / DCF Unlock Guide" in source
    assert "waiting on peer context" in source
    assert "Run make readiness before reviewing the fundamentals and DCF unlock guide." in source
    assert "Fundamentals / DCF Unlock Diagnostics" not in source
    assert "fundamentals and DCF unlock diagnostics" not in source


def test_peer_mapping_studio_summary_cards_and_scope_toggles_are_actionable():
    peer_readiness = pd.DataFrame(
        [
            {
                "ticker": "A",
                "peer_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
            },
            {
                "ticker": "META",
                "peer_ready": False,
                "peer_blocker_type": "peer_fundamentals_missing",
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": False,
            },
            {
                "ticker": "NVDA",
                "peer_ready": True,
                "peer_blocker_type": "",
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": True,
            },
        ]
    )
    readiness = pd.DataFrame(
        [
            {"ticker": "A", "dcf_ready": True, "in_active_universe": False},
            {"ticker": "META", "dcf_ready": True, "in_active_universe": True},
            {"ticker": "NVDA", "dcf_ready": True, "in_active_universe": True},
        ]
    )
    unlock = pd.DataFrame(
        [
            {"ticker": "A", "priority": 1, "focus_command": "make focus-peers TICKER=A"},
            {"ticker": "META", "priority": 1, "focus_command": "make focus-peers TICKER=META"},
        ]
    )

    cards = dashboard.peer_mapping_studio_summary_cards(peer_readiness, readiness)
    rendered_cards = " ".join(str(value) for card in cards for value in card.values()).lower()
    active_only = dashboard.build_peer_mapping_studio_frame(
        peer_readiness,
        readiness,
        unlock,
        filter_mode="DCF-ready but peer-blocked",
        active_universe_only=True,
        dcf_ready_only=True,
        row_limit=10,
    )

    assert list(active_only["ticker"]) == ["META"]
    assert "dcf peer blockers" in rendered_cards
    assert "missing mappings" in rendered_cards
    assert "valuation blocked" in rendered_cards
    assert "make peer-mapping-queue top_n=25" in rendered_cards
    assert "make templates" in rendered_cards
    assert "broker" not in rendered_cards
    assert "order" not in rendered_cards
    assert "buy" not in rendered_cards
    assert "sell" not in rendered_cards


def test_peer_analysis_boundary_cards_separate_trend_valuation_and_input_path():
    peer_readiness = pd.DataFrame(
        [
            {
                "ticker": "A",
                "peer_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
            },
            {
                "ticker": "META",
                "peer_ready": False,
                "peer_blocker_type": "peer_fundamentals_missing",
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": False,
            },
            {
                "ticker": "COHR",
                "peer_ready": False,
                "peer_blocker_type": "peer_price_missing",
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
            },
            {
                "ticker": "NVDA",
                "peer_ready": True,
                "peer_blocker_type": "",
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": True,
            },
        ]
    )
    readiness = pd.DataFrame(
        [
            {"ticker": "A", "dcf_ready": True, "in_active_universe": False},
            {"ticker": "META", "dcf_ready": True, "in_active_universe": True},
            {"ticker": "COHR", "dcf_ready": False, "in_active_universe": True},
            {"ticker": "NVDA", "dcf_ready": True, "in_active_universe": True},
        ]
    )

    cards = dashboard.peer_analysis_boundary_cards(peer_readiness, readiness)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "WHAT PEERS CAN SUPPORT NOW",
        "WHAT IS STILL LOCKED",
        "DCF-READY BUT PEER-BLOCKED",
        "TRUSTED INPUT PATH",
    ]
    assert "2 trend-ready / 1 valuation-ready" in rendered
    assert "peer trend context can be reviewed" in rendered
    assert "peer valuation is separate" in rendered
    assert "3 peer valuation row(s) locked" in rendered
    assert "missing mappings: 1" in rendered
    assert "peer price gaps: 1" in rendered
    assert "peer fundamentals gaps: 1" in rendered
    assert "locked peer valuation is not a company conclusion" in rendered
    assert "2 company row(s)" in rendered
    assert "1 active-universe row(s) can have standalone dcf reviewed" in rendered
    assert "peer-relative valuation stays withheld" in rendered
    assert "data/imports/peers.csv" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "sector or industry fallback is context, not trusted peer valuation data" in rendered
    assert "make focus-peers ticker=meta" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_peer_analysis_boundary_cards_handle_missing_report_without_fake_peer_counts():
    cards = dashboard.peer_analysis_boundary_cards(None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert len(cards) == 1
    assert "peer readiness not loaded" in rendered
    assert "missing peer output means peer analysis stays locked" in rendered
    assert "make readiness" in rendered


def test_peer_function_quality_frame_explains_trend_vs_valuation_and_provenance():
    peer_readiness = pd.DataFrame(
        [
            {
                "ticker": "A",
                "peer_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
            },
            {
                "ticker": "META",
                "peer_ready": False,
                "peer_blocker_type": "peer_fundamentals_missing",
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
            },
            {
                "ticker": "NVDA",
                "peer_ready": True,
                "peer_blocker_type": "",
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": True,
                "peer_dcf_comparison_ready": True,
            },
            {
                "ticker": "COHR",
                "peer_ready": False,
                "peer_blocker_type": "peer_price_missing",
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
            },
        ]
    )
    worklist = pd.DataFrame([{"ticker": "A"}, {"ticker": "META"}])

    frame = dashboard.peer_function_quality_frame(peer_readiness, worklist)
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert list(frame.columns) == [
        "Peer Area",
        "Current Coverage",
        "Supported Today",
        "Not Supported Yet",
        "Logic Source",
        "Next Step",
    ]
    assert "source-backed mappings" in rendered
    assert "1 ticker(s) missing mappings; 2 unlock row(s) queued" in rendered
    assert "data/imports/peers.csv" in rendered
    assert "peer-selection rules stay in this repository" in rendered
    assert "peer trend comparison" in rendered
    assert "2 ticker(s) trend-ready" in rendered
    assert "peer-relative valuation or quality conclusions" in rendered
    assert "peer valuation comparison" in rendered
    assert "1 ticker(s) valuation-ready; 3 still blocked" in rendered
    assert "withheld, not inferred" in rendered
    assert "peer dcf comparison" in rendered
    assert "1 ticker(s) dcf-peer-ready" in rendered
    assert "peer data follow-through" in rendered
    assert "1 price-gap ticker(s); 1 fundamentals-gap ticker(s)" in rendered
    assert "sector or industry fallback" in rendered
    assert "dependencies" in rendered
    assert "replacing source-backed peer mappings or project peer-readiness rules" in rendered
    assert "peer logic runs from this repository" in rendered
    assert "copied peer-selection skills" not in rendered
    assert "no hidden peer-selection engine" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_peer_readiness_product_cards_prioritize_peer_unlock_worklist_active_scope():
    peer_readiness = pd.DataFrame(
        [
            {
                "ticker": "A",
                "peer_ready": False,
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "next_peer_action": "Add at least 2 source-backed peer mappings for A in data/imports/peers.csv.",
            },
            {
                "ticker": "COHR",
                "peer_ready": False,
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "next_peer_action": "Add at least 2 source-backed peer mappings for COHR in data/imports/peers.csv.",
            },
        ]
    )
    worklist = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "A",
                "workflow_scope": "master_universe",
                "next_action_summary": "Broad master-universe peer mapping follow-up.",
            },
            {
                "priority": 1,
                "ticker": "COHR",
                "workflow_scope": "active_universe",
                "next_action_summary": "Add active source-backed peer mappings first.",
            },
        ]
    )

    cards = dashboard.peer_readiness_product_cards(peer_readiness, pd.DataFrame({"ticker": ["A", "COHR"]}), worklist)
    next_card = next(card for card in cards if card["kicker"] == "NEXT PEER TARGET")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert next_card["title"] == "COHR"
    assert next_card["command"] == "make focus-peers TICKER=COHR"
    assert "active source-backed peer mappings first" in rendered
    assert "broad master-universe peer mapping follow-up" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_decision_workflow_summary_cards_explain_buckets_without_trade_language():
    decisions = pd.DataFrame(
        [
            {
                "ticker": "A",
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - DCF Ready But Peer Blocked",
                "primary_blocker": "peers",
                "data_confidence": "medium",
                "next_best_action": "Add source-backed peer mappings and peer metrics for A.",
            },
            {
                "ticker": "APLD",
                "decision_bucket": "Blocked by Data",
                "decision_subtype": "Blocked by Data - Missing Price",
                "primary_blocker": "price",
                "data_confidence": "low",
                "next_best_action": "Run make price-refresh-loop DRY_RUN=1.",
            },
            {
                "ticker": "QQQ",
                "decision_bucket": "Monitor",
                "decision_subtype": "Monitor - ETF Market Proxy",
                "primary_blocker": "none",
                "data_confidence": "limited",
                "next_best_action": "Use as market proxy; DCF is excluded.",
            },
        ]
    )

    cards = dashboard.decision_workflow_summary_cards(decisions)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "1 research / 1 blocked" in rendered
    assert "research candidate - dcf ready but peer blocked" in rendered
    assert "price: 1" in rendered
    assert "readiness-gated" in rendered
    assert "not execution guidance" in rendered
    assert "coverage signal, not conviction" in rendered
    assert "medium: 1" in rendered
    assert "low: 1" in rendered
    assert "data confidence describes local input coverage" in rendered
    assert "falls when core, peer, earnings, or estimate context is missing" in rendered
    assert "make research-health top_n=10" in rendered
    assert "make focus-peers ticker=a" in rendered
    assert "data/imports/peers.csv" in rendered
    assert "peer mappings and peer metrics" not in rendered
    assert "trade" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_decision_interpretation_ladder_explains_reading_order_without_recommendations():
    frame = dashboard.decision_interpretation_ladder_frame()
    rendered = " ".join(frame.astype(str).to_numpy().ravel()).lower()

    assert frame["Step"].tolist() == [
        "1. Read the bucket",
        "2. Read the subtype",
        "3. Read the blocker",
        "4. Read data confidence",
        "5. Copy the next action",
    ]
    assert "workflow states, not direct actions" in rendered
    assert "subtype explains why the broad bucket exists" in rendered
    assert "do not interpret valuation, peers, earnings, or estimates until the blocker is resolved" in rendered
    assert "data confidence is a data-quality state" in rendered
    assert "not a dashboard action or recommendation" in rendered
    assert "make onboarding TOP_N=10".lower() in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_decision_interpretation_ladder_cards_keep_next_action_copy_only():
    cards = dashboard.decision_interpretation_ladder_cards()
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["command"] == "make project-status"
    assert cards[1]["command"] == "make onboarding TOP_N=10"
    assert cards[2]["command"] == "make status-check TOP_N=5"
    assert "decision reading order" in rendered
    assert "blocker before conclusion" in rendered
    assert "next action is copy-only" in rendered
    assert "manual terminal workflow" in rendered
    assert "research-only" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_final_decision_quality_cards_explain_bucket_boundaries_without_recommendations():
    decisions = pd.DataFrame(
        [
            {"ticker": "A", "decision_bucket": "Research Now"},
            {"ticker": "QQQ", "decision_bucket": "Monitor"},
            {"ticker": "APLD", "decision_bucket": "Blocked by Data"},
            {"ticker": "AMD", "decision_bucket": "Blocked by Data"},
        ]
    )

    cards = dashboard.final_decision_quality_cards(decisions)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["RESEARCH NOW", "MONITOR", "BLOCKED BY DATA", "LOGIC SOURCE"]
    assert "1 row(s)" in str(cards[0]["title"])
    assert "ready for deeper research workflow only" in rendered
    assert "review-queue label" in rendered
    assert "not a direct action, allocation instruction, or recommendation" in rendered
    assert "market, theme, etf/index, liquidity, or risk context" in rendered
    assert "blocked rows are data-unlock work" in rendered
    assert "not weak-company conclusions" in rendered
    assert "project readiness gates" in rendered
    assert "local readiness, blocker, and source/freshness outputs in project code" in rendered
    assert "shipped decisions come from project code and local data" in rendered
    assert "plugins can help development review" not in rendered
    assert "not hidden recommendation engines" not in rendered
    assert "make onboarding top_n=10" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_final_decision_quality_cards_handle_missing_outputs():
    cards = dashboard.final_decision_quality_cards(None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Decision outputs not ready yet"
    assert cards[0]["command"] == "make pipeline"
    assert "run the local pipeline" in rendered
    assert "not generated" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_final_decision_table_guide_cards_explain_columns_before_rows():
    decisions = pd.DataFrame(
        [
            {
                "ticker": "A",
                "decision_bucket": "Research Now",
                "confidence": "medium-high",
                "primary_blocker": "peers",
                "next_action": "Add source-backed peer mappings.",
            },
            {
                "ticker": "APLD",
                "decision_bucket": "Blocked by Data",
                "confidence": "low",
                "primary_blocker": "price",
                "next_action": "Refresh local price coverage.",
            },
            {
                "ticker": "QQQ",
                "decision_bucket": "Monitor",
                "confidence": "limited",
                "primary_blocker": "none",
                "next_action": "Review as monitor context.",
            },
        ]
    )

    cards = dashboard.final_decision_table_guide_cards(decisions)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["BUCKET", "DATA CONFIDENCE", "BLOCKER", "NEXT ACTION"]
    assert "workflow state, not a call" in rendered
    assert "deeper review, monitor context, or data-unlock work" in rendered
    assert "2 low-data-confidence row(s)" in rendered
    assert "data confidence is input coverage, not conviction or recommendation strength" in rendered
    assert "it falls when core inputs, peer context" in rendered
    assert "top blocker:" in rendered
    assert "use primary_blocker, missing_data, blocked_features, and excluded_features" in rendered
    assert "3 row(s) with next steps" in rendered
    assert "copyable local workflow steps" in rendered
    assert "do not execute anything from the dashboard" in rendered
    assert "make research-health top_n=10" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_final_decision_table_guide_cards_prefer_data_confidence_column():
    decisions = pd.DataFrame(
        [
            {
                "ticker": "A",
                "decision_bucket": "Research Now",
                "confidence": "high",
                "data_confidence": "limited",
                "primary_blocker": "peers",
                "next_best_action": "Add source-backed peer mappings.",
            },
            {
                "ticker": "APLD",
                "decision_bucket": "Blocked by Data",
                "confidence": "high",
                "data_confidence": "low",
                "primary_blocker": "price",
                "next_best_action": "Run make price-refresh-loop DRY_RUN=1.",
            },
        ]
    )

    cards = dashboard.final_decision_table_guide_cards(decisions)
    confidence_card = next(card for card in cards if card["kicker"] == "DATA CONFIDENCE")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert confidence_card["title"] == "2 low-data-confidence row(s)"
    assert "data confidence is input coverage, not conviction or recommendation strength" in rendered
    assert "it falls when core inputs" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_decision_workflow_summary_cards_use_plain_missing_output_language():
    cards = dashboard.decision_workflow_summary_cards(None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Decision workflow not ready yet"
    assert cards[0]["command"] == "make pipeline"
    assert "not generated" not in rendered
    assert "run make pipeline" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_decision_workflow_summary_cards_route_price_blocker_to_refresh_loop_dry_run():
    decisions = pd.DataFrame(
        [
            {
                "ticker": "APLD",
                "decision_bucket": "Blocked by Data",
                "decision_subtype": "Blocked by Data - Missing Price",
                "primary_blocker": "price",
                "data_confidence": "low",
                "next_best_action": "Run a safe price worklist.",
            }
        ]
    )

    cards = dashboard.decision_workflow_summary_cards(decisions)
    next_card = next(card for card in cards if card["kicker"] == "NEXT DECISION ACTION")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert next_card["title"] == "Price coverage worklist"
    assert next_card["command"] == "make focus-price TICKER=APLD"
    assert "make price-refresh-loop dry_run=1" in rendered
    assert "review the planned batches" in rendered
    assert "manually run 25" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_decision_workflow_summary_cards_prioritize_active_peer_unlocks():
    decisions = pd.DataFrame(
        [
            {
                "ticker": "A",
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - DCF Ready But Peer Blocked",
                "primary_blocker": "peers",
                "next_best_action": "Add source-backed peer mappings for A.",
            },
            {
                "ticker": "COHR",
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - DCF Ready But Peer Blocked",
                "primary_blocker": "peers",
                "next_best_action": "Optional context missing for COHR; leave unavailable unless trusted local CSVs exist.",
            },
            {
                "ticker": "NVDA",
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - Optional Context Locked",
                "primary_blocker": "earnings",
                "next_best_action": "Optional context missing for NVDA; leave unavailable unless trusted local CSVs exist.",
            },
        ]
    )
    readiness = pd.DataFrame(
        [
            {"ticker": "A", "in_active_universe": False, "dcf_ready": True, "peer_ready": False},
            {"ticker": "COHR", "in_active_universe": True, "dcf_ready": True, "peer_ready": False},
            {"ticker": "NVDA", "in_active_universe": True, "dcf_ready": True, "peer_ready": True},
        ]
    )

    cards = dashboard.decision_workflow_summary_cards(decisions, readiness)
    next_card = next(card for card in cards if card["kicker"] == "NEXT DECISION ACTION")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert next_card["title"] == "Peer mapping for COHR"
    assert next_card["command"] == "make focus-peers TICKER=COHR"
    assert "data/imports/peers.csv" in str(next_card["body"])
    assert "make imports-validate" in str(next_card["body"])
    assert "make focus-peers ticker=cohr" in rendered
    assert "optional context missing for cohr" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trade" not in rendered
    assert "buy" not in rendered


def test_decision_next_action_title_names_the_work_not_only_the_ticker():
    assert dashboard.decision_next_action_title(pd.Series({"ticker": "A", "primary_blocker": "peers"})) == "Peer mapping for A"
    assert dashboard.decision_next_action_title(pd.Series({"ticker": "META", "primary_blocker": "fundamentals"})) == "Fundamentals for META"
    assert dashboard.decision_next_action_title(pd.Series({"ticker": "APLD", "primary_blocker": "price"})) == "Price coverage worklist"
    assert dashboard.decision_next_action_title(
        pd.Series({"ticker": "QQQ", "primary_blocker": "", "asset_type": "etf"})
    ) == "Monitor context for QQQ"


def test_final_watchlist_expander_uses_product_language_not_legacy_label():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")

    assert 'st.expander("Full research-state table"' in source
    assert "Legacy final watchlist output" not in source


def test_final_decision_table_surfaces_row_level_decision_boundary():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")

    final_decision_section = source[source.index("def render_final_decision_tab") : source.index("def get_local_provider")]

    assert '"decision_boundary"' in final_decision_section
    assert final_decision_section.index('"decision_bucket"') < final_decision_section.index('"decision_boundary"')


def test_decision_workflow_summary_cards_surface_research_now_optional_context_lock():
    decisions = pd.DataFrame(
        [
            {
                "ticker": "AMD",
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - Optional Context Locked",
                "primary_blocker": "earnings",
                "blocked_features": "earnings, analyst_estimates",
                "next_best_action": "Optional context missing for AMD; leave unavailable unless trusted local CSVs exist.",
            },
            {
                "ticker": "NVDA",
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - Optional Context Locked",
                "primary_blocker": "earnings",
                "blocked_features": "earnings, analyst_estimates",
                "next_best_action": "Optional context missing for NVDA; leave unavailable unless trusted local CSVs exist.",
            },
        ]
    )

    cards = dashboard.decision_workflow_summary_cards(decisions)
    optional_card = next(card for card in cards if card["kicker"] == "OPTIONAL CONTEXT LOCK")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert optional_card["title"] == "2 research row(s)"
    assert optional_card["command"] == "make optional-context-worklist TOP_N=25"
    assert "amd, nvda" in rendered
    assert "optional context locked row(s): amd, nvda" in rendered
    assert "supported core or dcf context" in rendered
    assert "earnings or analyst-estimate context remains unavailable" in rendered
    assert "trusted local csv rows" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_optional_context_unlock_cards_show_schema_and_safe_import_commands():
    cards = dashboard.optional_context_unlock_cards()
    empty_message = dashboard.optional_context_empty_state_message("earnings")
    estimate_empty_message = dashboard.optional_context_empty_state_message("analyst-estimate")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "ticker, fiscal_period, report_date" in rendered
    assert "ticker, period, eps_estimate" in rendered
    assert "make import-earnings" in rendered
    assert "make import-analyst-estimates" in rendered
    assert "data/imports/earnings.csv" in rendered
    assert "data/imports/analyst_estimates.csv" in rendered
    assert "data/staged/earnings/" in rendered
    assert "data/staged/analyst_estimates/" in rendered
    assert "make templates" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "make optional-context-readiness" in rendered
    assert "make onboarding top_n=10" in rendered
    assert "templates are not data" in rendered
    assert "schema only" in rendered
    assert "data/rejected/earnings_import_rejected.csv" in rendered
    assert "data/rejected/analyst_estimates_import_rejected.csv" in rendered
    assert "missing trusted local csv input" in rendered
    assert "make imports-validate" in empty_message
    assert "make imports-preview" in empty_message
    assert "make imports-apply" in empty_message
    assert "Run `make templates` for schema-only files; templates are not data." in empty_message
    assert "make onboarding TOP_N=10" in empty_message
    assert "data/staged/earnings/" in empty_message
    assert "data/imports/earnings.csv" in empty_message
    assert "make import-earnings" in empty_message
    assert "data/rejected/earnings_import_rejected.csv" in empty_message
    assert "data/staged/analyst_estimates/" in estimate_empty_message
    assert "data/imports/analyst_estimates.csv" in estimate_empty_message
    assert "make import-analyst-estimates" in estimate_empty_message
    assert "data/rejected/analyst_estimates_import_rejected.csv" in estimate_empty_message
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_import_workflow_caption_spells_out_validation_preview_apply_commands():
    caption = dashboard.import_workflow_caption("data/staged/earnings/", "make import-earnings")

    assert caption == (
        "Manual import: data/staged/earnings/ -> make import-earnings -> "
        "make imports-validate -> make imports-preview -> make imports-apply."
    )
    assert "imports-validate/preview/apply" not in caption
    assert "broker" not in caption.lower()
    assert "order" not in caption.lower()
    assert "buy" not in caption.lower()
    assert "sell" not in caption.lower()


def test_data_health_import_captions_use_exact_copyable_commands():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")

    assert 'import_workflow_caption("data/staged/fundamentals/", "make import-fundamentals")' in source
    assert 'import_workflow_caption("data/staged/earnings/", "make import-earnings")' in source
    assert 'import_workflow_caption("data/staged/analyst_estimates/", "make import-analyst-estimates")' in source
    assert "make imports-validate/preview/apply" not in source


def test_stock_report_optional_context_boundary_cards_explain_locked_and_available_states():
    locked_cards = dashboard.stock_report_optional_context_boundary_cards(
        {
            "valuation_readiness": {"earnings_available": False, "analyst_estimates_available": False},
            "earnings_summary": {},
            "analyst_estimate_summary": {},
        }
    )
    ready_cards = dashboard.stock_report_optional_context_boundary_cards(
        {
            "valuation_readiness": {"earnings_available": True, "analyst_estimates_available": True},
            "earnings_summary": {"next_earnings_date": "2026-07-24"},
            "analyst_estimate_summary": {"target_mean_price": 390.0},
        }
    )
    locked_rendered = " ".join(str(value) for card in locked_cards for value in card.values()).lower()
    ready_rendered = " ".join(str(value) for card in ready_cards for value in card.values()).lower()
    rendered = f"{locked_rendered} {ready_rendered}"

    assert [card["kicker"] for card in locked_cards] == ["OPTIONAL CONTEXT", "EARNINGS", "ANALYST ESTIMATES", "UNLOCK PATH"]
    assert "earnings locked / estimates locked" in locked_rendered
    assert "earnings available / estimates available" in ready_rendered
    assert "optional context can add timing, consensus, and revision context" in rendered
    assert "never overrides readiness gates or creates a valuation conclusion by itself" in rendered
    assert "locked means missing trusted local csv input, not broken analysis" in locked_rendered
    assert "leaves earnings context locked instead of using placeholders" in locked_rendered
    assert "data/staged/earnings/" in locked_rendered
    assert "data/imports/earnings.csv" in locked_rendered
    assert "data/rejected/earnings_import_rejected.csv" in locked_rendered
    assert "data/staged/analyst_estimates/" in locked_rendered
    assert "data/imports/analyst_estimates.csv" in locked_rendered
    assert "data/rejected/analyst_estimates_import_rejected.csv" in locked_rendered
    assert locked_cards[1]["command"] == "make templates && make import-earnings && make imports-validate && make imports-preview && make imports-apply && make optional-context-readiness && make onboarding TOP_N=10"
    assert locked_cards[2]["command"] == "make templates && make import-analyst-estimates && make imports-validate && make imports-preview && make imports-apply && make optional-context-readiness && make onboarding TOP_N=10"
    assert locked_cards[3]["command"] == "make templates && make imports-validate && make imports-preview && make imports-apply && make optional-context-readiness && make onboarding TOP_N=10"
    assert ready_cards[1]["command"] == ""
    assert ready_cards[2]["command"] == ""
    assert "next date: 2026-07-24" in ready_rendered
    assert "mean target: $390.00" in ready_rendered
    assert "schema-only templates" in rendered
    assert "validate, preview, apply, and rebuild readiness" in rendered
    assert "make optional-context-readiness" in rendered
    assert "make onboarding top_n=10" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_first_optional_context_unlock_frame_keeps_optional_rows_locked_until_trusted():
    frame = dashboard.first_optional_context_unlock_frame("analyst_estimates")
    rendered = " ".join(frame.astype(str).to_numpy().ravel()).lower()

    assert frame["Step"].tolist() == [
        "1. Confirm optional context is worth adding",
        "2. Create schema-only templates",
        "3. Stage trusted analyst estimates rows",
        "4. Validate before applying",
        "5. Rebuild optional readiness",
    ]
    assert frame.iloc[0]["Copy Command"] == "make optional-context-worklist TOP_N=25"
    assert frame.iloc[1]["Copy Command"] == "make templates"
    assert frame.iloc[2]["Copy Command"] == "make import-analyst-estimates"
    assert "data/staged/analyst_estimates/" in rendered
    assert "data/imports/analyst_estimates.csv" in rendered
    assert "data/rejected/analyst_estimates_import_rejected.csv" in rendered
    assert "templates are blank aids, not synthetic data or coverage" in rendered
    assert "leave unknown fields blank instead of guessing" in rendered
    assert "optional readiness should improve only after rows pass validation" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_first_optional_context_unlock_cards_are_recommendation_free():
    cards = dashboard.first_optional_context_unlock_cards("earnings")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["command"] == "make optional-context-worklist TOP_N=25"
    assert cards[1]["command"] == "make import-earnings"
    assert cards[2]["command"] == "make imports-validate && make imports-preview && make imports-apply && make optional-context-readiness && make onboarding TOP_N=10"
    assert "data/staged/earnings/" in rendered
    assert "data/imports/earnings.csv" in rendered
    assert "rejected-row report: rejected rows: data/rejected/earnings_import_rejected.csv" in rendered
    assert "rebuild proof: make optional-context-readiness && make onboarding top_n=10" in rendered
    assert "trusted source only" in rendered
    assert "no estimates fabricated" in rendered
    assert "not a recommendation" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_market_blocker_summary_cards_surface_safe_top_n_worklists():
    readiness = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "QQQ"],
            "in_active_universe": [True, True, True],
            "price_ready": [False, True, True],
            "fundamentals_ready": [False, False, False],
            "peer_ready": [False, False, True],
            "earnings_ready": [False, False, False],
            "analyst_estimates_ready": [False, False, False],
            "asset_type": ["company", "company", "etf"],
            "excluded_features": ["", "", "dcf"],
        }
    )

    cards = dashboard.market_blocker_summary_cards(readiness)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "make price-refresh-loop dry_run=1" in rendered
    assert "capped price refresh plan" in rendered
    assert "make sec-stage-queue top_n=25" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "make optional-context-worklist top_n=25" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_market_next_action_cards_use_capped_worklist_front_doors():
    readiness = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "COHR", "QQQ"],
            "in_active_universe": [False, True, True, True],
            "price_ready": [False, True, True, True],
            "fundamentals_ready": [False, False, True, False],
            "peer_ready": [False, False, False, False],
            "earnings_ready": [False, False, False, False],
            "analyst_estimates_ready": [False, False, False, False],
            "asset_type": ["company", "company", "company", "etf"],
        }
    )
    action_queue = pd.DataFrame({"ticker": ["AAA", "BBB"], "action": ["prices", "fundamentals"]})

    cards = dashboard.market_next_action_cards(readiness, action_queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "make price-worklist top_n=25" not in rendered
    assert "make sec-stage-queue top_n=25" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "make optional-context-worklist top_n=25" in rendered
    assert "make onboarding top_n=10" in rendered
    assert "tickers=aaa" not in rendered
    assert "make templates" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_readiness_snapshot_handles_company_etf_and_missing():
    readiness = pd.DataFrame(
        {
            "ticker": ["NVDA", "QQQ"],
            "name": ["Nvidia", "Invesco QQQ"],
            "asset_type": ["company", "etf"],
            "price_ready": [True, True],
            "momentum_ready": [True, True],
            "dcf_ready": [True, False],
            "peer_ready": [True, False],
            "earnings_ready": [False, False],
            "analyst_estimates_ready": [False, False],
            "overall_readiness_state": ["partial", "partial"],
            "excluded_features": ["", "dcf"],
            "missing_data": ["earnings", "fundamentals"],
            "next_action": ["Review valuation assumptions.", "Use as market proxy."],
        }
    )
    decisions = pd.DataFrame(
        {
            "ticker": ["NVDA", "QQQ"],
            "decision_bucket": ["Research Now", "Monitor"],
            "decision_subtype": ["Research Candidate - DCF Ready But Peer Blocked", "Monitor - ETF Market Proxy"],
            "primary_blocker": ["peers", "none"],
            "confidence": ["medium", "medium"],
            "data_confidence": ["medium-high", "limited"],
            "main_reason": ["DCF-ready with missing optional context.", "ETF market proxy."],
            "next_best_action": ["Review valuation assumptions.", "Use as market proxy."],
            "purpose_alignment": [
                "Purpose alignment: Core Compounder is reviewable from ready local inputs.",
                "Purpose alignment: ETF / Defensive / Hedge is evaluated as market/risk context.",
            ],
            "unsupported_analysis": [
                "Unsupported analysis: peer-relative valuation remains withheld until peer rows are ready.",
                "Unsupported analysis: operating-company DCF and peer valuation are excluded.",
            ],
            "invalidation_condition": [
                "Invalidate if peer mapping remains unresolved for the intended relative-valuation read.",
                "Invalidate market-proxy usefulness if liquidity, correlation, or theme trend no longer supports the intended monitoring role.",
            ],
        }
    )
    dcf = pd.DataFrame(
        {
            "ticker": ["NVDA", "QQQ"],
            "reason_not_ready": ["", "DCF excluded for etf."],
        }
    )
    peers = pd.DataFrame(
        {
            "ticker": ["NVDA", "QQQ"],
            "peer_blocker_type": ["", "missing_peer_mapping"],
            "mapping_status": ["mapped", "missing_mapping"],
            "peer_count": [2, 0],
            "ready_peer_count": [2, 0],
            "peer_trend_comparison_ready": [True, False],
            "peer_valuation_comparison_ready": [False, False],
            "next_peer_action": ["Peer trend comparison ready.", "Add source-backed peers for QQQ."],
        }
    )

    company = dashboard.single_stock_readiness_snapshot("NVDA", readiness, decisions_frame=decisions, dcf_readiness_frame=dcf, peer_readiness_frame=peers)
    etf = dashboard.single_stock_readiness_snapshot("QQQ", readiness, decisions_frame=decisions, dcf_readiness_frame=dcf, peer_readiness_frame=peers)
    missing = dashboard.single_stock_readiness_snapshot("ZZZ", readiness)

    assert company["dcf_status"] == "ready"
    assert company["decision_bucket"] == "Research Now"
    assert company["decision_subtype"] == "Research Candidate - DCF Ready But Peer Blocked"
    assert company["primary_blocker"] == "peers"
    assert company["data_confidence"] == "medium-high"
    assert etf["data_confidence"] == "limited"
    assert "Operator summary:" in company["operator_summary"]
    assert "Next blocker: peers" in company["operator_summary"]
    assert "peer-relative valuation remains withheld" in company["operator_summary"]
    assert company["peer_count"] == 2
    assert company["peer_trend_comparison_ready"] is True
    assert company["ready_features"] == ""
    assert etf["dcf_status"] == "excluded"
    assert etf["decision_subtype"] == "Monitor - ETF Market Proxy"
    assert etf["peer_blocker_type"] == "monitor_context"
    assert etf["peer_mapping_status"] == "monitor_context"
    assert "no peer import is required" in etf["next_peer_action"].lower()
    assert etf["next_action"] == "Review QQQ as ETF/index/fund monitor context; operating-company DCF and peer valuation stay excluded."
    assert "Operator summary: Monitor context" in etf["operator_summary"]
    assert "operating-company DCF and peer valuation are excluded" in etf["operator_summary"]
    assert "excluded" in str(etf["dcf_reason"]).lower()
    assert "DCF is excluded" in etf["one_minute_summary"]
    assert "source-backed peers" not in etf["one_minute_summary"].lower()
    assert "primary blocker: peers" not in etf["one_minute_summary"].lower()
    assert "peer workflow" not in etf["one_minute_summary"].lower()
    assert missing["status"] == "missing"


def test_single_stock_status_cards_surface_badges_sources_and_next_actions():
    snapshot = {
        "ticker": "NVDA",
        "status": "partial",
        "decision_subtype": "Research Candidate - DCF Ready But Peer Blocked",
        "confidence": "medium",
        "data_confidence": "medium-high",
        "main_reason": "Core data is ready for a supported research pass.",
        "next_action": "Add source-backed peer mappings and peer metrics for NVDA.",
        "ready_features": "price, momentum, dcf",
        "blocked_features": "peer, earnings, analyst_estimates",
        "excluded_features": "portfolio",
        "missing_data": "peers: needs mappings",
        "price_ready": True,
        "dcf_status": "ready",
        "peer_ready": False,
        "peer_blocker_type": "missing_peer_mapping",
        "next_peer_action": "Add at least 2 source-backed peer mappings for NVDA.",
        "peer_trend_comparison_ready": False,
        "peer_valuation_comparison_ready": False,
        "price_first_date": "2025-01-01",
        "price_last_date": "2026-05-22",
        "updated_at": "2026-05-28T00:00:00+00:00",
    }

    cards = dashboard.single_stock_status_cards(snapshot)
    detail = dashboard.single_stock_detail_frame(snapshot)
    status_card = next(card for card in cards if card["kicker"] == "TICKER STATUS")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "nvda: partial" in rendered
    assert "Operator summary" in detail["Field"].tolist()
    assert "one-minute read" in rendered
    assert "decision: research candidate - dcf ready but peer blocked" in rendered
    assert "data confidence: medium-high" in rendered
    assert "confidence: medium" not in status_card["badges"]
    assert "ready: price, momentum, dcf" in rendered
    assert "missing_peer_mapping" in rendered
    assert "make focus-peers ticker=nvda" in rendered
    assert "add source-backed peer mappings and peer metrics for nvda." not in rendered
    assert "2025-01-01 to 2026-05-22" in rendered
    assert "trusted local csv input" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_status_cards_fall_back_to_legacy_confidence_for_old_outputs():
    snapshot = {
        "ticker": "META",
        "status": "partial",
        "decision_subtype": "Research Candidate - Optional Context Locked",
        "confidence": "medium",
        "main_reason": "Core data is ready for a supported research pass.",
        "next_action": "Optional context missing for META.",
        "ready_features": "price, momentum, fundamentals, dcf, peer",
        "blocked_features": "earnings, analyst_estimates",
        "excluded_features": "",
        "missing_data": "earnings: trusted local CSV input",
        "price_ready": True,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "dcf_status": "ready",
        "peer_ready": True,
    }

    cards = dashboard.single_stock_status_cards(snapshot)
    status_card = next(card for card in cards if card["kicker"] == "TICKER STATUS")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "data confidence: medium" in rendered
    assert "confidence: medium" not in status_card["badges"]
    assert "make optional-context-worklist top_n=25" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_status_cards_route_core_data_ready_optional_lock_to_worklist():
    snapshot = {
        "ticker": "AMD",
        "status": "partial",
        "decision_subtype": "Research Candidate - Optional Context Locked",
        "confidence": "medium",
        "main_reason": "Core data is ready for a supported research pass.",
        "next_action": "Optional context missing for AMD; leave unavailable unless trusted local CSVs exist.",
        "ready_features": "price, momentum, fundamentals, dcf, peer",
        "blocked_features": "earnings, analyst_estimates",
        "excluded_features": "portfolio",
        "missing_data": "earnings: trusted local CSV input; analyst_estimates: trusted local CSV input",
        "price_ready": True,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "dcf_status": "ready",
        "peer_ready": True,
        "peer_trend_comparison_ready": True,
        "peer_valuation_comparison_ready": True,
        "price_first_date": "2025-01-01",
        "price_last_date": "2026-05-22",
        "updated_at": "2026-05-28T00:00:00+00:00",
    }

    cards = dashboard.single_stock_status_cards(snapshot)
    status_card = next(card for card in cards if card["kicker"] == "TICKER STATUS")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert status_card["command"] == "make optional-context-worklist TOP_N=25"
    assert "research candidate - optional context locked" in rendered
    assert "optional context missing for amd" in rendered
    assert "trusted local csv input" in rendered
    assert "make templates" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_reader_guide_frame_separates_ready_locked_and_next_step():
    snapshot = {
        "ticker": "A",
        "asset_type": "company",
        "price_ready": True,
        "dcf_status": "ready",
        "peer_ready": False,
        "peer_trend_comparison_ready": True,
        "peer_valuation_comparison_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "next_action": "Add source-backed peer mappings before peer-relative valuation.",
    }

    frame = dashboard.single_stock_reader_guide_frame(snapshot)
    cards = dashboard.single_stock_reader_guide_cards(snapshot)
    rendered = " ".join(frame.astype(str).to_numpy().flatten().tolist() + [str(value) for card in cards for value in card.values()]).lower()

    assert list(frame.columns) == ["Question", "Answer", "Trusted Input Needed", "Copy-Only Command"]
    assert [card["kicker"] for card in cards] == ["ANALYZE NOW", "LOCKED / EXCLUDED", "NEXT STEP"]
    assert "standalone dcf assumptions, scenario math, sensitivity, source freshness, and peer trend context" in rendered
    assert "mapped peer price history can be reviewed" in rendered
    assert "peer-relative valuation, premium/discount, and peer dcf comparison remain locked" in rendered
    assert "trusted input needed:" in rendered
    assert "trusted peer mappings in data/imports/peers.csv plus peer inputs when needed" in rendered
    assert "use only current local/provider rows that already passed readiness" in rendered
    assert "data/imports/peers.csv" in rendered
    assert "make focus-peers ticker=a" in rendered
    assert "make stock-report-md ticker=a" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_reader_guide_handles_etf_and_price_blocked_states():
    etf = {
        "ticker": "QQQ",
        "asset_type": "etf",
        "price_ready": True,
        "dcf_status": "excluded",
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "next_action": "Review QQQ as ETF/index/fund monitor context.",
    }
    blocked = {
        "ticker": "APLD",
        "asset_type": "company",
        "price_ready": False,
        "dcf_status": "blocked",
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "next_action": "Add trusted price rows first.",
    }

    etf_frame = dashboard.single_stock_reader_guide_frame(etf)
    blocked_frame = dashboard.single_stock_reader_guide_frame(blocked)
    etf_cards = dashboard.single_stock_reader_guide_cards(etf)
    blocked_cards = dashboard.single_stock_reader_guide_cards(blocked)
    etf_rendered = " ".join(
        etf_frame.astype(str).to_numpy().flatten().tolist() + [str(value) for card in etf_cards for value in card.values()]
    ).lower()
    blocked_rendered = " ".join(
        blocked_frame.astype(str).to_numpy().flatten().tolist() + [str(value) for card in blocked_cards for value in card.values()]
    ).lower()

    assert "market, theme, liquidity, or risk monitor context" in etf_rendered
    assert "operating-company dcf and peer valuation are excluded" in etf_rendered
    assert "trusted input needed: no company dcf input is required" in etf_rendered
    assert "make stock-report-md ticker=qqq" in etf_rendered
    assert "trusted price rows exist" in blocked_rendered
    assert "trusted input needed: trusted local price history" in blocked_rendered
    assert "prices, momentum, dcf, peer context" in blocked_rendered
    assert "make focus-price ticker=apld" in blocked_rendered
    assert "broker" not in etf_rendered + blocked_rendered
    assert "order" not in etf_rendered + blocked_rendered
    assert "trading" not in etf_rendered + blocked_rendered
    assert "buy" not in etf_rendered + blocked_rendered
    assert "sell" not in etf_rendered + blocked_rendered


def test_single_stock_quick_read_cards_route_dcf_ready_peer_locked():
    snapshot = {
        "ticker": "NVDA",
        "status": "partial",
        "asset_type": "company",
        "price_ready": True,
        "dcf_status": "ready",
        "peer_ready": False,
        "peer_trend_comparison_ready": True,
        "peer_valuation_comparison_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "one_minute_summary": "NVDA is partial; DCF inputs are ready, but peer context is locked.",
    }

    cards = dashboard.single_stock_quick_read_cards(snapshot)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["FIRST READ", "ANALYZE NOW", "STILL LOCKED", "COPY ONLY"]
    assert cards[0]["title"] == "Standalone DCF is reviewable; peers are still locked."
    assert cards[0]["command"] == "make focus-peers TICKER=NVDA"
    assert "dcf assumptions, sensitivity, source freshness, company setup, and peer trend context" in rendered
    assert "mapped peer price history" in rendered
    assert "peer-relative valuation, premium/discount, and peer dcf comparison wait" in rendered
    assert "does not run refreshes, imports, or external account actions" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_quick_read_cards_cover_monitor_blocked_and_optional_states():
    etf = {
        "ticker": "QQQ",
        "status": "partial",
        "asset_type": "etf",
        "price_ready": True,
        "dcf_status": "excluded",
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
    }
    blocked = {
        "ticker": "APLD",
        "status": "blocked",
        "asset_type": "company",
        "price_ready": False,
        "dcf_status": "blocked",
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
    }
    optional = {
        "ticker": "A",
        "status": "partial",
        "asset_type": "company",
        "price_ready": True,
        "dcf_status": "ready",
        "peer_ready": True,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
    }

    etf_rendered = " ".join(str(value) for card in dashboard.single_stock_quick_read_cards(etf) for value in card.values()).lower()
    blocked_rendered = " ".join(str(value) for card in dashboard.single_stock_quick_read_cards(blocked) for value in card.values()).lower()
    optional_rendered = " ".join(str(value) for card in dashboard.single_stock_quick_read_cards(optional) for value in card.values()).lower()

    assert "use this as monitor context" in etf_rendered
    assert "operating-company dcf and peer valuation are excluded, not failed" in etf_rendered
    assert "make stock-report-md ticker=qqq" in etf_rendered
    assert "start with trusted price history" in blocked_rendered
    assert "make focus-price ticker=apld" in blocked_rendered
    assert "core analysis is reviewable; optional context is locked" in optional_rendered
    assert "make optional-context-worklist top_n=25" in optional_rendered
    rendered = etf_rendered + blocked_rendered + optional_rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_methodology_bridge_cards_explain_source_vs_product_logic():
    snapshot = {
        "ticker": "NVDA",
        "asset_type": "company",
        "price_ready": True,
        "dcf_status": "ready",
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
    }

    cards = dashboard.single_stock_methodology_bridge_cards(snapshot)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["SOURCE INPUTS", "PRODUCT LOGIC", "DCF BOUNDARY", "PEERS / OPTIONAL"]
    assert "local/provider rows feed the report" in rendered
    assert "local csvs or labeled provider-assisted rows" in rendered
    assert "this app decides what can appear" in rendered
    assert "runs supported calculations locally" in rendered
    assert "without inventing missing inputs" in rendered
    assert "dcf ready for assumption review" in rendered
    assert "free-cash-flow assumptions, wacc, terminal growth" in rendered
    assert "fair value per share" in rendered
    assert "peer-relative valuation remains blocked" in rendered
    assert "trusted optional csv rows pass validation" in rendered
    assert "make stock-report-md ticker=nvda" in rendered
    assert "make focus-peers ticker=nvda" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_methodology_bridge_cards_cover_excluded_and_blocked_states():
    etf = {
        "ticker": "QQQ",
        "asset_type": "etf",
        "price_ready": True,
        "dcf_status": "excluded",
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
    }
    blocked = {
        "ticker": "APLD",
        "asset_type": "company",
        "price_ready": False,
        "dcf_status": "blocked",
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
    }

    etf_rendered = " ".join(str(value) for card in dashboard.single_stock_methodology_bridge_cards(etf) for value in card.values()).lower()
    blocked_rendered = " ".join(str(value) for card in dashboard.single_stock_methodology_bridge_cards(blocked) for value in card.values()).lower()

    assert "dcf excluded, not failed" in etf_rendered
    assert "operating-company dcf does not apply" in etf_rendered
    assert "operating-company peer valuation is excluded" in etf_rendered
    assert "make stock-report-md ticker=qqq" in etf_rendered
    assert "analysis locked until price rows exist" in blocked_rendered
    assert "withholds setup, dcf, and peer interpretation" in blocked_rendered
    assert "make focus-price ticker=apld" in blocked_rendered
    assert "no inference" in blocked_rendered
    assert "broker" not in etf_rendered + blocked_rendered
    assert "order" not in etf_rendered + blocked_rendered
    assert "trading" not in etf_rendered + blocked_rendered
    assert "buy" not in etf_rendered + blocked_rendered
    assert "sell" not in etf_rendered + blocked_rendered


def test_single_stock_source_audit_frame_surfaces_paths_credentials_and_safe_commands(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "Research Tester tester@example.com")
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    snapshot = {
        "ticker": "NVDA",
        "price_ready": True,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "dcf_status": "ready",
        "dcf_reason": "DCF inputs are present.",
        "peer_ready": False,
        "peer_blocker_type": "missing_peer_mapping",
        "next_peer_action": "Add source-backed peers.",
        "price_first_date": "2025-01-01",
        "price_last_date": "2026-05-22",
        "price_rows": 300,
    }

    audit = dashboard.single_stock_source_audit_frame(snapshot)
    cards = dashboard.single_stock_source_audit_cards(snapshot)
    rendered = " ".join(audit.astype(str).stack().tolist() + [str(value) for card in cards for value in card.values()]).lower()

    assert [card["kicker"] for card in cards] == ["PRICES", "FUNDAMENTALS / DCF", "PEERS", "EARNINGS", "ANALYST ESTIMATES"]
    assert "data/prices.csv" in rendered
    assert "data/staged/earnings/" in rendered
    assert "data/rejected/analyst_estimates_import_rejected.csv" in rendered
    assert "sec_user_agent=present" in rendered.replace(" ", "")
    assert "stooq_api_key=missing" in rendered.replace(" ", "")
    assert "make stock-report-md ticker=nvda" in rendered
    assert "make import-earnings" in rendered
    assert "make import-analyst-estimates" in rendered
    assert "missing trusted local csv input" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_source_audit_routes_missing_prices_to_focus_price_first(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    snapshot = {
        "ticker": "APLD",
        "price_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "dcf_status": "blocked",
        "dcf_reason": "Missing price and fundamentals.",
        "peer_ready": False,
        "peer_blocker_type": "missing_peer_mapping",
        "next_peer_action": "Wait for trusted price and DCF inputs.",
        "price_rows": 0,
    }

    audit = dashboard.single_stock_source_audit_frame(snapshot)
    cards = dashboard.single_stock_source_audit_cards(snapshot)
    rendered = " ".join(audit.astype(str).stack().tolist() + [str(value) for card in cards for value in card.values()]).lower()
    price_row = audit.loc[audit["Area"].eq("Prices")].iloc[0]

    assert price_row["Status"] == "blocked"
    assert price_row["Next command"] == "make focus-price TICKER=APLD"
    assert "make focus-price ticker=apld" in rendered
    assert "make price-refresh tickers=apld" not in rendered
    assert "make import-analyst-estimates" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_peer_path_keeps_etf_monitor_context_on_stock_report(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "Research Tester tester@example.com")
    snapshot = {
        "ticker": "QQQ",
        "asset_type": "etf",
        "status": "partial",
        "decision_subtype": "Monitor - ETF Market Proxy",
        "confidence": "medium",
        "main_reason": "ETF monitor context.",
        "next_action": "Add source-backed peer mappings and peer metrics for QQQ.",
        "ready_features": "price, momentum",
        "blocked_features": "peer, earnings, analyst_estimates",
        "excluded_features": "dcf",
        "missing_data": "peers: needs mappings",
        "price_ready": True,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "dcf_status": "excluded",
        "dcf_reason": "DCF excluded for etf.",
        "peer_ready": False,
        "peer_blocker_type": "missing_peer_mapping",
        "next_peer_action": "Add at least 2 source-backed peer mappings for QQQ.",
    }

    status_cards = dashboard.single_stock_status_cards(snapshot)
    audit = dashboard.single_stock_source_audit_frame(snapshot)
    audit_cards = dashboard.single_stock_source_audit_cards(snapshot)
    rendered = " ".join(
        [str(value) for card in status_cards + audit_cards for value in card.values()]
        + audit.astype(str).stack().tolist()
    ).lower()
    peer_status_card = next(card for card in status_cards if card["kicker"] == "PEER PATH")
    peer_audit_row = audit.loc[audit["Area"].eq("Peers")].iloc[0]

    assert peer_status_card["title"] == "monitor context"
    assert peer_status_card["command"] == "make stock-report-md TICKER=QQQ"
    assert peer_audit_row["Status"] == "monitor context"
    assert peer_audit_row["Next command"] == "make stock-report-md TICKER=QQQ"
    assert "operating-company peer valuation is excluded" in rendered
    assert "make focus-peers ticker=qqq" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_single_stock_peer_path_waits_for_fundamentals_before_peer_unlock(monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "Research Tester tester@example.com")
    snapshot = {
        "ticker": "CRDO",
        "asset_type": "company",
        "status": "partial",
        "decision_subtype": "Blocked by Data - Missing Fundamentals",
        "confidence": "low",
        "main_reason": "Company research is blocked by missing DCF data.",
        "next_action": "Import trusted fundamentals for CRDO.",
        "ready_features": "price, momentum",
        "blocked_features": "dcf, peer, earnings, analyst_estimates",
        "excluded_features": "portfolio",
        "missing_data": "dcf: revenue, fcf_margin; peers: needs mappings",
        "price_ready": True,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "dcf_status": "blocked",
        "dcf_reason": "missing revenue, fcf_margin.",
        "peer_ready": False,
        "peer_blocker_type": "missing_peer_mapping",
        "next_peer_action": "Add at least 2 source-backed peer mappings for CRDO.",
    }

    status_cards = dashboard.single_stock_status_cards(snapshot)
    audit = dashboard.single_stock_source_audit_frame(snapshot)
    rendered = " ".join([str(value) for card in status_cards for value in card.values()] + audit.astype(str).stack().tolist()).lower()
    peer_status_card = next(card for card in status_cards if card["kicker"] == "PEER PATH")
    peer_audit_row = audit.loc[audit["Area"].eq("Peers")].iloc[0]

    assert peer_status_card["title"] == "blocked until fundamentals / DCF"
    assert peer_status_card["command"] == "make stock-report-md TICKER=CRDO"
    assert peer_audit_row["Status"] == "blocked until fundamentals / DCF"
    assert peer_audit_row["Next command"] == "make sec-stage TICKERS=CRDO"
    assert "peer-relative valuation should wait" in rendered
    assert "make focus-peers ticker=crdo" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_dashboard_splits_momentum_to_ready_and_blocked_rows():
    momentum = pd.DataFrame(
        {
            "Ticker": ["NVDA", "AMD"],
            "Close": [120.0, None],
            "SetupStatus": ["Watch", "No Setup"],
            "Reason": ["Supported.", "Price data is missing."],
        }
    )
    coverage = pd.DataFrame({"ticker": ["NVDA", "AMD"], "usable_for_momentum": [True, False]})

    ready, blocked = dashboard.split_momentum_readiness(momentum, coverage)

    assert ready["Ticker"].tolist() == ["NVDA"]
    assert blocked["Ticker"].tolist() == ["AMD"]


def test_dashboard_splits_dcf_ready_blocked_and_excluded_rows():
    dcf = pd.DataFrame(
        {
            "ticker": ["NVDA", "AMD", "QQQ"],
            "asset_type": ["company", "company", "etf"],
            "is_dcf_ready": [True, False, False],
        }
    )

    ready, blocked, excluded = dashboard.split_dcf_readiness(dcf)

    assert ready["ticker"].tolist() == ["NVDA"]
    assert blocked["ticker"].tolist() == ["AMD"]
    assert excluded["ticker"].tolist() == ["QQQ"]


def test_valuation_readiness_operator_frame_summarizes_ready_blocked_and_excluded_rows():
    ready = pd.DataFrame({"ticker": ["NVDA"], "missing_dcf_fields": [""]})
    blocked = pd.DataFrame(
        {
            "ticker": ["AMD", "META"],
            "missing_dcf_fields": ["free_cash_flow, shares_outstanding", "shares_outstanding, fcf_margin"],
        }
    )
    excluded = pd.DataFrame({"ticker": ["QQQ"], "asset_type": ["etf"]})

    frame = dashboard.valuation_readiness_operator_frame(ready, blocked, excluded)
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert list(frame.columns) == [
        "Evaluation Mode",
        "Valuation State",
        "Count",
        "Example Tickers",
        "What It Means",
        "What Stays Withheld",
        "Next Command",
    ]
    assert frame["Count"].tolist() == [1, 2, 1]
    assert frame["Evaluation Mode"].tolist() == ["DCF-ready review", "Locked by missing inputs", "Monitor-only context"]
    assert frame["Example Tickers"].tolist() == ["NVDA", "AMD, META", "QQQ"]
    assert "ready company rows" in rendered
    assert "dcf-ready review" in rendered
    assert "review assumptions, scenarios, and sensitivity" in rendered
    assert "blocked company rows" in rendered
    assert "locked by missing inputs" in rendered
    assert "most common blockers: shares_outstanding" in rendered
    assert "no undervalued or overvalued conclusion is shown for blocked rows" in rendered
    assert "etf / fund monitor rows" in rendered
    assert "monitor-only context" in rendered
    assert "operating-company dcf is excluded, not failed" in rendered
    assert "make sec-stage-queue top_n=25" in rendered
    assert "make stock-report-md ticker=qqq" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_valuation_blocked_unlock_frame_plain_language_and_copy_only_commands():
    blocked = pd.DataFrame(
        {
            "ticker": ["META", "APLD"],
            "missing_dcf_fields": ["free_cash_flow, shares_outstanding", "price, revenue"],
            "reason_not_ready": ["", ""],
            "has_price": [True, "False"],
        }
    )

    frame = dashboard.valuation_blocked_unlock_frame(blocked)
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert list(frame.columns) == [
        "Ticker",
        "Current State",
        "Valuation Boundary",
        "Missing Trusted Inputs",
        "What This Means",
        "Next Trusted Input",
        "Next Safe Sequence",
        "Validation Path",
        "Copy-Only Command",
    ]
    assert frame["Ticker"].tolist() == ["META", "APLD"]
    assert frame.loc[frame["Ticker"].eq("META"), "Copy-Only Command"].iloc[0] == "make focus-fundamentals TICKER=META"
    assert frame.loc[frame["Ticker"].eq("APLD"), "Copy-Only Command"].iloc[0] == "make focus-price TICKER=APLD"
    assert "no intrinsic, peer-relative, undervalued, or overvalued conclusion until trusted inputs pass readiness" in rendered
    assert "free cash flow, shares outstanding" in rendered
    assert "no fair value, undervalued, or overvalued conclusion" in rendered
    assert "trusted company fundamentals" in rendered
    assert "trusted local price rows" in rendered
    assert "make sec-stage tickers=meta" in rendered
    assert "data/imports/fundamentals.csv" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "make price-refresh-loop dry_run=1" in rendered
    assert "data/imports/prices.csv" in rendered
    assert "make price-validate" in rendered
    assert "make price-preview" in rendered
    assert "make price-apply" in rendered
    assert "make dcf-readiness" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_valuation_excluded_context_frame_explains_excluded_not_failed():
    excluded = pd.DataFrame({"ticker": ["QQQ"], "asset_type": ["etf"]})

    frame = dashboard.valuation_excluded_context_frame(excluded)
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert list(frame.columns) == ["Ticker", "Asset Type", "Current State", "Valuation Boundary", "What This Means", "Copy-Only Command"]
    assert frame.iloc[0]["Ticker"] == "QQQ"
    assert frame.iloc[0]["Copy-Only Command"] == "make stock-report-md TICKER=QQQ"
    assert "operating-company dcf excluded" in rendered
    assert "dcf excluded, not failed; peer-relative company valuation is not shown for monitor-context rows" in rendered
    assert "dcf is excluded, not failed" in rendered
    assert "market, theme, liquidity, or risk review" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_dashboard_splits_risk_context_by_price_ready_status():
    liquidity = pd.DataFrame(
        {
            "Ticker": ["NVDA", "AMD"],
            "LiquidityStatus": ["Liquid", "Insufficient Price Data"],
        }
    )

    ready, unavailable = dashboard.split_risk_context_by_price_ready(liquidity, {"Insufficient Price Data"})

    assert ready["Ticker"].tolist() == ["NVDA"]
    assert unavailable["Ticker"].tolist() == ["AMD"]


def test_market_direction_chart_frame_keeps_supported_numeric_rows_only():
    frame = pd.DataFrame(
        {
            "Theme": ["AI Semis", "Robotics", "Infra"],
            "Return1M": [0.12, None, None],
            "RelativeReturnVsSPY": [0.08, -0.03, None],
            "RelativeReturnVsQQQ": [0.04, None, None],
        }
    )

    chart = dashboard.market_direction_chart_frame(frame, max_rows=2)

    assert list(chart.index) == ["AI Semis", "Robotics"]
    assert "RelativeReturnVsSPY" in chart.columns


def test_momentum_setup_distribution_frame_counts_statuses_cleanly():
    frame = pd.DataFrame({"SetupStatus": ["Watch", "No Setup", "Watch", None, ""]})

    chart = dashboard.momentum_setup_distribution_frame(frame)

    assert chart.loc["Watch", "Count"] == 2
    assert chart.loc["No Setup", "Count"] == 1
    assert chart.loc["Not available", "Count"] == 2


def test_momentum_relative_strength_chart_frame_ranks_supported_tickers():
    frame = pd.DataFrame(
        {
            "Ticker": ["amd", "nvda", "amd", "avgo"],
            "RSPercentile": [70, 95, 60, None],
            "RelativeReturnVsSPY": [0.05, 0.18, 0.02, 0.07],
            "RelativeReturnVsQQQ": [0.01, 0.11, -0.01, 0.03],
        }
    )

    chart = dashboard.momentum_relative_strength_chart_frame(frame, max_rows=3)

    assert list(chart.index) == ["NVDA", "AMD", "AVGO"]
    assert chart.loc["AMD", "RSPercentile"] == 70


def test_output_tab_chart_sections_are_research_only_and_targeted():
    market_sections = dashboard.output_tab_chart_sections(
        "Market Direction",
        pd.DataFrame({"Theme": ["AI"], "RelativeReturnVsSPY": [0.12], "RelativeReturnVsQQQ": [0.08]}),
    )
    momentum_sections = dashboard.output_tab_chart_sections(
        "Momentum Leaders",
        pd.DataFrame({"Ticker": ["NVDA"], "SetupStatus": ["Watch"], "RSPercentile": [92], "RelativeReturnVsSPY": [0.18], "RelativeReturnVsQQQ": [0.11]}),
    )
    rendered = " ".join(
        " ".join(str(value) for value in section[:2]) for section in market_sections + momentum_sections
    ).lower()

    assert len(market_sections) == 1
    assert len(momentum_sections) == 2
    assert "relative return" in rendered
    assert "watch-only" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_categorical_count_frame_normalizes_missing_values():
    frame = pd.DataFrame({"ReviewState": ["Review Thesis", "", None, "Review Thesis"]})

    chart = dashboard.categorical_count_frame(frame, "ReviewState", "ReviewState")

    assert chart.loc["Review Thesis", "Count"] == 2
    assert chart.loc["Not available", "Count"] == 2


def test_portfolio_review_risk_chart_frame_combines_review_and_concentration():
    frame = pd.DataFrame(
        {
            "ReviewState": ["Review Thesis", "Keep", "Review Thesis"],
            "ConcentrationRisk": [False, True, False],
        }
    )

    chart = dashboard.portfolio_review_risk_chart_frame(frame)

    assert "ReviewStateCount" in chart.columns
    assert "ConcentrationRiskCount" in chart.columns
    assert chart.loc["Review Thesis", "ReviewStateCount"] == 2
    assert chart.loc["No concentration risk", "ConcentrationRiskCount"] == 2


def test_final_watchlist_score_chart_frame_orders_ranked_names():
    frame = pd.DataFrame(
        {
            "Ticker": ["amd", "nvda", "qqq", "amd"],
            "WatchlistRank": [3, 2, 1, 4],
            "WatchlistScore": [41.0, 55.0, 68.0, 10.0],
            "RelativeOpportunityScore": [None, 22.0, None, 5.0],
        }
    )

    chart = dashboard.final_watchlist_score_chart_frame(frame, max_rows=3)

    assert list(chart.index) == ["QQQ", "NVDA", "AMD"]
    assert chart.loc["AMD", "WatchlistScore"] == 41.0


def test_output_tab_chart_sections_include_portfolio_and_watchlist_views():
    portfolio_sections = dashboard.output_tab_chart_sections(
        "Portfolio Review",
        pd.DataFrame({"ReviewState": ["Review Thesis"], "ConcentrationRisk": [False]}),
    )
    watchlist_sections = dashboard.output_tab_chart_sections(
        "Final Watchlist",
        pd.DataFrame({"Ticker": ["NVDA"], "FinalState": ["Review Thesis"], "WatchlistScore": [40.0], "WatchlistRank": [2]}),
    )
    rendered = " ".join(
        " ".join(str(value) for value in section[:2]) for section in portfolio_sections + watchlist_sections
    ).lower()

    assert len(portfolio_sections) == 1
    assert len(watchlist_sections) == 2
    assert "concentration-risk" in rendered or "concentration" in rendered
    assert "watchlist" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_dominant_value_and_non_empty_count_handle_empty_fields():
    frame = pd.DataFrame(
        {
            "Status": ["", None, "Partial", "Partial"],
            "Missing": ["nan", "Return1M", "", "Not available"],
        }
    )

    value, count = dashboard.dominant_value(frame, ["Status"])

    assert value == "Partial"
    assert count == 2
    assert dashboard.non_empty_count(frame, ["Missing"]) == 1


def test_presentation_frame_uses_readable_labels_and_values():
    frame = pd.DataFrame(
        {
            "Ticker": ["NVDA"],
            "Return1M": [0.1234],
            "WatchlistScore": [81.25],
            "MissingDataFields": ["Return1M, peers"],
            "ReasonSummary": ["Transparent local context."],
        }
    )

    display = dashboard.presentation_frame(frame)

    assert list(display.columns) == ["Ticker", "1M Return", "Watchlist Score", "Missing Data", "Reason"]
    assert display.iloc[0]["1M Return"] == "12.3%"
    assert display.iloc[0]["Watchlist Score"] == "81.2"
    assert "Not enough price history" in display.iloc[0]["Missing Data"]
    assert "Needs peers.csv" in display.iloc[0]["Missing Data"]


def test_presentation_frame_handles_duplicate_source_columns_safely():
    frame = pd.DataFrame([["NVDA", "Short reason", "Long reason"]], columns=["Ticker", "ReasonSummary", "ReasonSummary"])

    display = dashboard.presentation_frame(frame)

    assert list(display.columns) == ["Ticker", "Reason", "Reason (2)"]
    assert display.iloc[0]["Reason"] == "Short reason."
    assert display.iloc[0]["Reason (2)"] == "Long reason."


def test_display_column_label_humanizes_unknown_columns():
    assert dashboard.display_column_label("avg_volume_20d") == "Avg Volume 20D"
    assert dashboard.display_column_label("PeerRelativeStatus") == "Peer Relative"


def test_sidebar_guide_rows_are_actionable_and_research_safe():
    status_rows = dashboard.status_legend_rows()
    missing_rows = dashboard.missing_data_guide_rows()
    workflow_rows = dashboard.workflow_command_rows()
    navigation_cards = dashboard.dashboard_navigation_cards()
    empty_rows = dashboard.empty_state_command_rows()
    rendered = " ".join(str(row) for row in status_rows + missing_rows + workflow_rows).lower()
    nav_rendered = " ".join(str(item) for card in navigation_cards for item in card).lower()
    empty_rendered = " ".join(str(row) for row in empty_rows).lower()

    assert any(row["Label"] == "Research Ready" for row in status_rows)
    assert any("price history" in row["Dashboard Label"].lower() for row in missing_rows)
    assert any(row["Command"] == "make help" for row in workflow_rows)
    assert any(row["Command"] == "make status-check TOP_N=5" for row in workflow_rows)
    assert any(row["Command"] == "make data-wizard TOP_N=5" for row in workflow_rows)
    assert any(row["Command"] == "make focus-price TICKER=NVDA" for row in workflow_rows)
    assert any(row["Command"] == "make focus-fundamentals TICKER=NVDA" for row in workflow_rows)
    assert any(row["Command"] == "make focus-peers TICKER=NVDA" for row in workflow_rows)
    assert any(row["Command"] == "make runbook-prices-broader" for row in workflow_rows)
    assert any(row["Command"] == "make verify" for row in workflow_rows)
    assert any(row["Command"] == "make validate-all" for row in workflow_rows)
    assert any(row["Command"] == "make dashboard-smoke" for row in workflow_rows)
    assert any(row["Command"] == "make daily" for row in workflow_rows)
    assert "trusted daily price history before reading momentum, risk, or track-record context" in rendered
    assert "without first unlocking more data" in rendered
    assert "valuation-style analysis" in rendered
    assert "make runbook-prices-broader" in rendered
    assert "overview page" in nav_rendered
    assert "monthly picks page" in nav_rendered
    assert "research queue, not a conclusion list" in nav_rendered
    assert "use this first" in nav_rendered
    assert "analyze one stock" in nav_rendered
    assert "ready, blocked, excluded, or monitor-only" in nav_rendered
    assert "unlock missing data" in nav_rendered
    assert "blocking analysis instead of being inferred" in nav_rendered
    assert "make status-check top_n=5" in rendered
    fundamentals_row = next(row for row in missing_rows if row["Dashboard Label"] == "Missing company fundamentals")
    peers_row = next(row for row in missing_rows if row["Dashboard Label"] == "Missing peer mapping")
    earnings_row = next(row for row in missing_rows if row["Dashboard Label"] == "Earnings unavailable")
    estimates_row = next(row for row in missing_rows if row["Dashboard Label"] == "Analyst estimates unavailable")
    assert "make status-check TOP_N=5" in fundamentals_row["What to do"]
    assert "make status-check TOP_N=5" in peers_row["What to do"]
    assert "Leave locked unless you have trusted earnings rows" in earnings_row["What to do"]
    assert "data/staged/earnings/" in earnings_row["What to do"]
    assert "make import-earnings" in earnings_row["What to do"]
    assert "data/rejected/earnings_import_rejected.csv" in earnings_row["What to do"]
    assert "Leave locked unless you have trusted analyst-estimate rows" in estimates_row["What to do"]
    assert "data/staged/analyst_estimates/" in estimates_row["What to do"]
    assert "make import-analyst-estimates" in estimates_row["What to do"]
    assert "data/rejected/analyst_estimates_import_rejected.csv" in estimates_row["What to do"]
    assert "make data-wizard top_n=5" in rendered
    assert "data health page" in nav_rendered
    assert "make runbook-prices-broader" in empty_rendered
    assert "make runbook-fundamentals-broader" in empty_rendered
    assert "make runbook-peers-broader" in empty_rendered
    assert "make focus-price" in empty_rendered
    assert "run make templates, then fill data/imports/peers.csv" in empty_rendered
    assert "price-normalize" in empty_rendered
    assert "make focus-fundamentals" in empty_rendered
    assert "make imports-validate" in empty_rendered
    assert "make imports-preview" in empty_rendered
    assert "make imports-apply" in empty_rendered
    assert "make price-validate" in empty_rendered
    assert "make price-preview" in empty_rendered
    assert "make price-apply" in empty_rendered
    assert "make runbook-fundamentals-broader" in rendered
    assert "make runbook-peers-broader" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "peers.csv" in empty_rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "peer fundamentals or price blocker" in empty_rendered
    assert "peer fundamentals or peer price follow-through" in rendered
    assert "staged peer fundamentals" not in rendered


def test_sidebar_guide_cards_render_plain_language_without_tables():
    status_html = dashboard.sidebar_guide_cards_html(dashboard.status_legend_rows(), "Label", "Meaning")
    missing_html = dashboard.sidebar_guide_cards_html(
        dashboard.missing_data_guide_rows(),
        "Dashboard Label",
        "What to do",
    )
    rendered = (status_html + missing_html).lower()

    assert "sidebar-guide-card" in rendered
    assert "sidebar-guide-label" in rendered
    assert "sidebar-guide-body" in rendered
    assert "<table" not in rendered
    assert "<th" not in rendered
    assert "research ready" in rendered
    assert "the app intentionally skipped analysis instead of filling gaps with guesses" in rendered
    assert "make imports-validate" in rendered
    assert "missing peer mapping" in rendered
    assert "data/imports/peers.csv" in rendered
    assert "needs peers.csv" not in rendered


def test_sidebar_guide_cards_escape_untrusted_copy():
    html = dashboard.sidebar_guide_cards_html(
        [{"Label": "<Ready>", "Meaning": "Use <trusted> rows."}],
        "Label",
        "Meaning",
    )

    assert "&lt;Ready&gt;" in html
    assert "&lt;trusted&gt;" in html


def test_sidebar_relative_path_context_uses_public_safe_relative_paths(tmp_path: Path):
    context = dashboard.sidebar_relative_path_context(tmp_path, tmp_path / "data", tmp_path / "outputs")

    assert context == {
        "project_root": ".",
        "data_dir": "data",
        "outputs_dir": "outputs",
    }
    assert str(tmp_path) not in " ".join(context.values())


def test_sidebar_local_file_context_lines_use_plain_relative_labels(tmp_path: Path):
    lines = dashboard.sidebar_local_file_context_lines(tmp_path, tmp_path / "data", tmp_path / "outputs")
    rendered = "\n".join(lines)

    assert lines == [
        "App folder: .",
        "Trusted input CSVs: data",
        "Generated reports: outputs",
    ]
    assert "Project root:" not in rendered
    assert "Data dir:" not in rendered
    assert "Outputs dir:" not in rendered
    assert str(tmp_path) not in rendered


def test_priority_now_falls_back_to_status_first_ready_path():
    class ReadyCatalog:
        def load_dataframe(self, name: str):
            if name == "fundamentals":
                return pd.DataFrame(
                    [
                        {"ticker": "NVDA", "free_cash_flow": 10},
                        {"ticker": "MSFT", "free_cash_flow": 12},
                    ]
                )
            if name == "peers":
                return pd.DataFrame([{"ticker": "NVDA", "peer_ticker": "MSFT"}])
            return pd.DataFrame()

    payload = {"top_onboarding_actions": []}
    actions = dashboard.priority_now_fallback_actions(payload, missing_warning_count=0, catalog=ReadyCatalog())

    rendered = " ".join(str(item) for row in actions for item in row).lower()
    assert "workflow looks ready" in rendered
    assert "make status-check top_n=5" in rendered
    assert "dashboard-smoke" in rendered
    assert "place_order" not in rendered
    assert "submit_order" not in rendered
    assert "execute_trade" not in rendered


def test_priority_now_fallback_actions_use_wizard_and_peer_runbook_front_doors():
    class StubCatalog:
        def load_dataframe(self, name: str):
            if name == "fundamentals":
                return pd.DataFrame([{"ticker": "NVDA"}, {"ticker": "TSLA"}])
            if name == "peers":
                return pd.DataFrame()
            return pd.DataFrame()

    actions = dashboard.priority_now_fallback_actions(None, missing_warning_count=3, catalog=StubCatalog())
    rendered = " ".join(str(item) for row in actions for item in row).lower()

    assert any(row[0] == "Data gaps are visible" and row[2] == "make data-wizard TOP_N=10" for row in actions)
    assert any(row[0] == "Peer context needs local research" and row[2] == "make runbook-peers-broader" for row in actions)
    assert "make data-wizard top_n=10" in rendered
    assert "make runbook-peers-broader" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_normalize_operator_command_rewrites_legacy_price_and_universe_commands():
    assert (
        dashboard.normalize_operator_command("SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=nvda, msft")
        == "make sec-stage TICKERS=NVDA,MSFT"
    )
    assert (
        dashboard.normalize_operator_command("python3 -m src.data_update --tickers amd, nvda")
        == "make price-refresh TICKERS=AMD,NVDA"
    )
    assert (
        dashboard.normalize_operator_command("python3 -m src.universe_builder --apply-import")
        == "make universe-apply"
    )
    assert (
        dashboard.normalize_operator_command("python3 -m src.universe_builder --preview --preset sp500_smh --max-tickers 50")
        == "make universe-preview"
    )
    assert (
        dashboard.normalize_operator_command("python3 -m src.universe_builder --preview --sources sp500,nasdaq,smh,holdings --max-tickers 100")
        == "make universe-preview"
    )
    assert (
        dashboard.normalize_operator_command("python3 -m src.universe_builder --write-import --preset sp500_smh --max-tickers 50")
        == "make universe-apply"
    )


def test_preferred_row_command_rewrites_legacy_price_refresh_example_command():
    row = {
        "focus_command": "",
        "example_command": "python3 -m src.data_update --tickers amd, nvda",
    }

    assert dashboard.preferred_row_command(row) == "make price-refresh TICKERS=AMD,NVDA"


def test_preferred_bundle_command_rewrites_legacy_sec_user_agent_command():
    row = {
        "bundle_shortcut_command": "",
        "primary_command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=nvda, msft",
    }

    assert dashboard.preferred_bundle_command(row) == "make sec-stage TICKERS=NVDA,MSFT"


def test_preferred_bundle_command_falls_back_to_runbook_and_detail_shortcuts():
    runbook_only = {
        "runbook_shortcut_command": "make runbook-prices",
    }
    detail_only = {
        "detail_shortcut_command": "make detail-prices",
    }

    assert dashboard.preferred_bundle_command(runbook_only) == "make runbook-prices"
    assert dashboard.preferred_bundle_command(detail_only) == "make detail-prices"


def test_preferred_bundle_command_falls_back_to_lane_runbooks_when_bundle_commands_are_missing():
    assert dashboard.preferred_bundle_command({"lane": "prices"}) == "make runbook-prices-broader"
    assert dashboard.preferred_bundle_command({"lane": "fundamentals"}) == "make runbook-fundamentals-broader"
    assert dashboard.preferred_bundle_command({"lane": "peers"}) == "make runbook-peers-broader"


def test_dashboard_tab_titles_and_navigation_labels_stay_consistent():
    assert dashboard.DASHBOARD_TAB_TITLES[0] == "Overview"
    assert dashboard.DASHBOARD_TAB_TITLES[1] == "Monthly Picks"
    assert dashboard.DASHBOARD_TAB_TITLES[7] == "Single-Stock Report"
    assert dashboard.DASHBOARD_TAB_TITLES[8] == "Data Health"
    assert dashboard.USER_PAGE_TITLES[0] == "Home"

    navigation = " ".join(str(item) for card in dashboard.dashboard_navigation_cards() for item in card)
    assert "Home page" in navigation
    assert "Overview page" in navigation
    assert "Monthly Picks page" in navigation
    assert "Single-Stock Report page" in navigation
    assert "Data Health page" in navigation


def test_dashboard_column_labels_cover_bundle_goal_fields():
    assert dashboard.COLUMN_LABELS["GoalSummary"] == "Goal Summary"
    assert dashboard.COLUMN_LABELS["TargetGoal"] == "Target Goal"
    assert dashboard.COLUMN_LABELS["RowsNeeded"] == "Rows Needed"
    assert dashboard.COLUMN_LABELS["TargetHistoryRows"] == "Target History Rows"
    assert dashboard.COLUMN_LABELS["SuggestedStartDate"] == "Suggested Start Date"
    assert dashboard.COLUMN_LABELS["FallbackManualCommand"] == "Fallback Manual Command"
    assert dashboard.COLUMN_LABELS["ExactNextCommand"] == "Exact Next Command"
    assert dashboard.COLUMN_LABELS["FocusCommand"] == "Focus Command"
    assert dashboard.COLUMN_LABELS["ExampleCommand"] == "Example Command"


def test_unlock_table_helpers_surface_command_columns():
    ladder = pd.DataFrame(
        [
            {
                "ticker": "AMD",
                "current_unlock_stage": "prices",
                "next_unlock_goal": "Unlock Monthly Picks",
                "price_stage_status": "missing_prices",
                "dcf_stage_status": "dcf_blocked",
                "peer_stage_status": "peer_mapping_missing",
                "optional_context_status": "missing_optional_context",
                "recommended_action": "Run make focus-price TICKER=AMD.",
                "focus_command": "make focus-price TICKER=AMD",
                "example_command": "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual",
                "target_file": "data/imports/prices.csv",
            }
        ]
    )
    summary = pd.DataFrame(
        [
            {
                "group_type": "holdings",
                "group_name": "Current Holdings",
                "ticker_count": 3,
                "holdings_count": 3,
                "top_priority_stage": "prices",
                "next_unlock_goal": "Unlock Monthly Picks",
                "representative_tickers": "META, NVDA, TSLA",
                "recommended_action": "Run make status, then follow the printed price focus or runbook path for this group.",
                "focus_command": "make status",
                "example_command": "make runbook-prices",
            }
        ]
    )

    assert dashboard.unlock_ladder_table_columns(ladder, include_statuses=True) == [
        "ticker",
        "current_unlock_stage",
        "next_unlock_goal",
        "price_stage_status",
        "dcf_stage_status",
        "peer_stage_status",
        "optional_context_status",
        "recommended_action",
        "focus_command",
        "example_command",
        "target_file",
    ]
    assert dashboard.unlock_ladder_table_columns(ladder, include_statuses=False) == [
        "ticker",
        "current_unlock_stage",
        "next_unlock_goal",
        "recommended_action",
        "focus_command",
        "example_command",
        "target_file",
    ]
    assert dashboard.unlock_priority_summary_table_columns(summary) == [
        "group_type",
        "group_name",
        "ticker_count",
        "holdings_count",
        "top_priority_stage",
        "next_unlock_goal",
        "representative_tickers",
        "recommended_action",
        "focus_command",
        "example_command",
    ]


def test_price_refresh_fallback_message_uses_runbook_and_normalize_flow():
    plain = dashboard.price_refresh_fallback_message()
    warned = dashboard.price_refresh_fallback_message(include_remote_failure_prefix=True)

    assert "make runbook-prices-broader" in plain
    assert "make focus-price" in plain
    assert "make price-normalize" in plain
    assert "make price-validate" in plain
    assert warned.startswith("Remote price refresh had source issues.")


def test_price_refresh_cli_note_message_uses_runbook_and_normalize_flow():
    note = dashboard.price_refresh_cli_note_message()

    assert note.startswith("Terminal-only:")
    assert "make runbook-prices-broader" in note
    assert "make focus-price" in note
    assert "make price-normalize" in note


def test_data_gap_report_notice_uses_data_sources_front_door():
    body, command = dashboard.data_gap_report_notice(None)

    assert "local gap report has not been generated yet" in body.lower()
    assert command == "make data-sources"


def test_overview_command_bundle_cards_surface_bundle_commands_safely():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; Unlock Track Record for 1 ticker; 57 verified rows still needed across this bundle",
                "target_history_rows": 63,
                "suggested_start_date": "2025-10-01",
                "bundle_shortcut_command": "make bundle-prices",
                "detail_shortcut_command": "make detail-prices",
                "runbook_shortcut_command": "make runbook-prices",
                "primary_command": "python3 -m src.data_update --tickers META,NVDA,TSLA",
                "follow_up_command": "make price-status",
                "target_file": "data/imports/prices.csv",
                "why_it_matters": "These tickers still block broader local research because price history is missing or too short.",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            }
        ]
    )

    cards = dashboard.overview_command_bundle_cards(bundles)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "PRICES BUNDLE"
    assert "holdings first" in rendered
    assert "unlock monthly picks" in rendered
    assert "63 target rows" in rendered
    assert "start by 2025-10-01" in rendered
    assert "make bundle-prices" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_command_bundle_cards_use_bundle_native_shortcuts_when_primary_is_missing():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; Unlock Track Record for 1 ticker; 57 verified rows still needed across this bundle",
                "target_history_rows": 63,
                "suggested_start_date": "2025-10-01",
                "bundle_shortcut_command": "",
                "detail_shortcut_command": "",
                "runbook_shortcut_command": "make runbook-prices",
                "primary_command": "",
            }
        ]
    )

    cards = dashboard.overview_command_bundle_cards(bundles)

    assert cards[0]["command"] == "make runbook-prices"


def test_overview_command_bundle_cards_use_review_fallback_when_summaries_are_missing():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "ticker_count": 1,
                "tickers": "TSLA",
                "goal_summary": "",
                "why_it_matters": "",
                "bundle_shortcut_command": "",
                "detail_shortcut_command": "",
                "runbook_shortcut_command": "make runbook-peers",
                "primary_command": "",
            }
        ]
    )

    cards = dashboard.overview_command_bundle_cards(bundles)

    assert cards[0]["command"] == "make runbook-peers"
    assert "ordered lane runbook" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_command_bundle_cards_use_staged_follow_through_when_summaries_are_missing():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "why_it_matters": "",
                "bundle_shortcut_command": "",
                "detail_shortcut_command": "",
                "runbook_shortcut_command": "make runbook-fundamentals",
                "primary_command": "",
                "target_file": "data/imports/fundamentals.csv",
                "safe_next_step": "Keep SEC enrichment import draft and review-only until make imports-validate, make imports-preview, and make imports-apply confirm the merge.",
            }
        ]
    )

    cards = dashboard.overview_command_bundle_cards(bundles)

    assert cards[0]["command"] == "make runbook-fundamentals"
    assert "make imports-preview" in cards[0]["body"].lower()
    assert "make imports-apply" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_command_bundle_cards_use_price_staged_follow_through_when_summaries_are_missing():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "ticker_count": 2,
                "tickers": "AMD,AVGO",
                "goal_summary": "",
                "why_it_matters": "",
                "bundle_shortcut_command": "",
                "detail_shortcut_command": "",
                "runbook_shortcut_command": "make runbook-prices",
                "primary_command": "",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "",
            }
        ]
    )

    cards = dashboard.overview_command_bundle_cards(bundles)

    assert cards[0]["command"] == "make runbook-prices"
    assert "make price-validate" in cards[0]["body"].lower()
    assert "make price-preview" in cards[0]["body"].lower()
    assert "make price-apply" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_command_bundle_cards_upgrade_generic_price_staged_note_to_explicit_follow_through():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "ticker_count": 2,
                "tickers": "AMD,AVGO",
                "goal_summary": "",
                "why_it_matters": "",
                "bundle_shortcut_command": "",
                "detail_shortcut_command": "",
                "runbook_shortcut_command": "make runbook-prices",
                "primary_command": "",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            }
        ]
    )

    cards = dashboard.overview_command_bundle_cards(bundles)

    assert cards[0]["command"] == "make runbook-prices"
    assert "make price-validate" in cards[0]["body"].lower()
    assert "make price-preview" in cards[0]["body"].lower()
    assert "make price-apply" in cards[0]["body"].lower()


def test_bundle_cards_and_handoff_use_lane_runbooks_when_bundle_commands_are_missing():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance transparent peer-relative readiness for the listed tickers",
                "bundle_shortcut_command": "",
                "detail_shortcut_command": "",
                "runbook_shortcut_command": "",
                "primary_command": "",
                "follow_up_command": "",
            }
        ]
    )

    bundle_cards = dashboard.overview_command_bundle_cards(bundles)
    handoff_cards = dashboard.overview_bundle_handoff_cards(bundles, None, None)

    assert bundle_cards[0]["command"] == "make runbook-peers-broader"
    assert handoff_cards[0]["command"] == "make runbook-peers-broader"


def test_overview_onboarding_fallback_cards_use_status_refresh():
    bundle_cards = dashboard.overview_command_bundle_cards(None)
    handoff_cards = dashboard.overview_bundle_handoff_cards(None, None, None)
    runbook_cards = dashboard.overview_bundle_runbook_cards(None)

    rendered = " ".join(
        str(value)
        for card_group in (bundle_cards, handoff_cards, runbook_cards)
        for card in card_group
        for value in card.values()
    ).lower()

    assert bundle_cards[0]["command"] == "make onboarding"
    assert handoff_cards[0]["command"] == "make onboarding"
    assert runbook_cards[0]["command"] == "make onboarding"
    assert "run make onboarding" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_bundle_runbook_cards_use_first_usable_step_command_when_lead_row_is_blank():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Explain lane",
                "command": "",
                "tickers": "NVDA",
                "goal_summary": "Advance transparent peer-relative readiness for the listed tickers",
            },
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "step_order": 2,
                "step_label": "Run bundle command",
                "command": "make templates",
                "tickers": "NVDA",
                "goal_summary": "Advance transparent peer-relative readiness for the listed tickers",
            },
        ]
    )

    data_health_cards = dashboard.data_health_command_bundle_runbook_cards(runbook)
    overview_cards = dashboard.overview_bundle_runbook_cards(runbook)

    assert data_health_cards[0]["command"] == "make templates"
    assert overview_cards[0]["command"] == "make templates"


def test_bundle_runbook_cards_use_first_usable_step_command_for_fallback_copy():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Explain lane",
                "command": "",
                "tickers": "NVDA",
                "goal_summary": "",
                "why_it_matters": "",
            },
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "step_order": 2,
                "step_label": "Open peer runbook",
                "command": "make runbook-peers",
                "tickers": "NVDA",
                "goal_summary": "",
                "why_it_matters": "",
            },
        ]
    )

    data_health_cards = dashboard.data_health_command_bundle_runbook_cards(runbook)
    overview_cards = dashboard.overview_bundle_runbook_cards(runbook)

    assert data_health_cards[0]["command"] == "make runbook-peers"
    assert "ordered lane runbook" in data_health_cards[0]["body"].lower()
    assert overview_cards[0]["command"] == "make runbook-peers"
    assert "ordered lane runbook" in overview_cards[0]["body"].lower()
    assert "not available" not in " ".join(str(value) for card in data_health_cards + overview_cards for value in card.values()).lower()


def test_bundle_runbook_cards_normalize_top_level_command_from_first_usable_step():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "python3 -m src.data_update --tickers META",
                "tickers": "META",
                "goal_summary": "Unlock Monthly Picks for 1 ticker; 21 verified rows still needed across this bundle",
            }
        ]
    )

    data_health_cards = dashboard.data_health_command_bundle_runbook_cards(runbook)
    overview_cards = dashboard.overview_bundle_runbook_cards(runbook)

    assert data_health_cards[0]["command"] == "make price-refresh TICKERS=META"
    assert overview_cards[0]["command"] == "make price-refresh TICKERS=META"


def test_overview_bundle_runbook_cards_surface_lane_steps_safely():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "python3 -m src.data_update --tickers META",
                "tickers": "META",
                "goal_summary": "Unlock Monthly Picks for 1 ticker; 21 verified rows still needed across this bundle",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "fallback_manual_command": "make price-normalize INPUT=data/raw/prices/META.csv TICKER=META SOURCE=yahoo_manual",
            },
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 2,
                "step_label": "If refresh fails, normalize first CSV",
                "command": "make price-normalize INPUT=data/raw/prices/META.csv TICKER=META SOURCE=yahoo_manual",
                "tickers": "META",
                "goal_summary": "Unlock Monthly Picks for 1 ticker; 21 verified rows still needed across this bundle",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "fallback_manual_command": "make price-normalize INPUT=data/raw/prices/META.csv TICKER=META SOURCE=yahoo_manual",
            },
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 3,
                "step_label": "Review follow-up output",
                "command": "make price-status",
                "tickers": "META",
                "goal_summary": "Unlock Monthly Picks for 1 ticker; 21 verified rows still needed across this bundle",
                "target_history_rows": 21,
                "suggested_start_date": "2025-12-01",
                "fallback_manual_command": "make price-normalize INPUT=data/raw/prices/META.csv TICKER=META SOURCE=yahoo_manual",
            },
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=NVDA",
                "tickers": "NVDA",
                "goal_summary": "Advance explicit local DCF readiness for the listed tickers",
                "target_history_rows": 0,
                "suggested_start_date": "",
            },
        ]
    )

    cards = dashboard.overview_bundle_runbook_cards(runbook)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "PRICES LANE"
    assert "run bundle command" in rendered
    assert "unlock monthly picks" in rendered
    assert "21 target rows" in rendered
    assert "make status-check top_n=5" not in rendered
    assert "start by 2025-12-01" in rendered
    assert "make price-normalize input=data/raw/prices/meta.csv ticker=meta source=yahoo_manual" in rendered
    assert "make sec-stage tickers=nvda" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_bundle_runbook_cards_use_staged_follow_through_when_goal_summary_is_missing():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Review import draft",
                "command": "make imports-validate",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "target_file": "data/imports/fundamentals.csv",
                "safe_next_step": "Keep SEC enrichment import draft and review-only until make imports-validate, make imports-preview, and make imports-apply confirm the merge.",
            }
        ]
    )

    cards = dashboard.overview_bundle_runbook_cards(runbook)

    assert cards[0]["command"] == "make imports-validate"
    assert "make imports-preview" in cards[0]["body"].lower()
    assert "make imports-apply" in cards[0]["body"].lower()
    assert "review import draft" in cards[0]["body"].lower()


def test_overview_bundle_runbook_cards_use_price_staged_follow_through_when_goal_summary_is_missing():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Review import draft",
                "command": "make price-validate",
                "tickers": "AMD,AVGO",
                "goal_summary": "",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "",
            }
        ]
    )

    cards = dashboard.overview_bundle_runbook_cards(runbook)

    assert cards[0]["command"] == "make price-validate"
    assert "make price-preview" in cards[0]["body"].lower()
    assert "make price-apply" in cards[0]["body"].lower()
    assert "review import draft" in cards[0]["body"].lower()


def test_overview_bundle_runbook_cards_upgrade_generic_price_staged_note_to_explicit_follow_through():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Review import draft",
                "command": "make price-validate",
                "tickers": "AMD,AVGO",
                "goal_summary": "",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            }
        ]
    )

    cards = dashboard.overview_bundle_runbook_cards(runbook)

    assert cards[0]["command"] == "make price-validate"
    assert "make price-preview" in cards[0]["body"].lower()
    assert "make price-apply" in cards[0]["body"].lower()
    assert "use local import draft workflows if the free refresh fails" not in cards[0]["body"].lower()


def test_overview_bundle_runbook_cards_use_staged_command_when_steps_are_blank():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Review import draft",
                "command": "",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "target_file": "data/imports/fundamentals.csv",
                "safe_next_step": "Keep SEC enrichment import draft and review-only until make imports-validate, make imports-preview, and make imports-apply confirm the merge.",
            }
        ]
    )

    cards = dashboard.overview_bundle_runbook_cards(runbook)

    assert cards[0]["command"] == "make imports-validate"
    assert "review import draft: make imports-validate" in cards[0]["body"].lower()
    assert "make imports-preview" in cards[0]["body"].lower()


def test_overview_bundle_runbook_cards_use_price_staged_command_when_steps_are_blank():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Review import draft",
                "command": "",
                "tickers": "AMD,AVGO",
                "goal_summary": "",
                "target_file": "data/imports/prices.csv",
                "safe_next_step": "",
            }
        ]
    )

    cards = dashboard.overview_bundle_runbook_cards(runbook)

    assert cards[0]["command"] == "make price-validate"
    assert "review import draft: make price-validate" in cards[0]["body"].lower()
    assert "make price-preview" in cards[0]["body"].lower()
    assert "make price-apply" in cards[0]["body"].lower()


def test_overview_bundle_runbook_cards_use_why_it_matters_when_goal_summary_is_missing():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Fill peer mappings manually",
                "command": "data/imports/peers.csv",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "why_it_matters": "These tickers are closest to peer-relative coverage once manually researched mappings are added locally.",
            }
        ]
    )

    cards = dashboard.overview_bundle_runbook_cards(runbook)

    assert "closest to peer-relative coverage" in cards[0]["body"].lower()
    assert "fill peer mappings manually: data/imports/peers.csv" in cards[0]["body"].lower()


def test_overview_bundle_runbook_cards_use_runbook_fallback_when_summaries_are_missing():
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Open peer runbook",
                "command": "make runbook-peers",
                "tickers": "TSLA",
                "goal_summary": "",
                "why_it_matters": "",
            }
        ]
    )

    cards = dashboard.overview_bundle_runbook_cards(runbook)

    assert cards[0]["command"] == "make runbook-peers"
    assert "local import draft workflow next" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_bundle_handoff_cards_surface_follow_through_safely():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance explicit local DCF readiness for the listed tickers",
                "primary_command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=META,NVDA,TSLA",
                "follow_up_command": "make imports-validate",
                "target_file": "data/imports/fundamentals.csv",
                "why_it_matters": "These tickers are the best next candidates for explicit local DCF inputs.",
                "safe_next_step": "Keep SEC enrichment import draft and review-only until make imports-validate, make imports-preview, and make imports-apply confirm the merge.",
            }
        ]
    )
    details = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "ticker": "META",
                "is_holding": True,
                "theme": "AI Platforms",
                "sector_etf": "QQQ",
                "current_unlock_stage": "fundamentals",
            }
        ]
    )
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=META,NVDA,TSLA",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance explicit local DCF readiness for the listed tickers",
                "target_file": "data/imports/fundamentals.csv",
                "why_it_matters": "These tickers are the best next candidates for explicit local DCF inputs.",
                "safe_next_step": "Keep SEC enrichment import draft and review-only until make imports-validate, make imports-preview, and make imports-apply confirm the merge.",
            },
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 2,
                "step_label": "Review follow-up output",
                "command": "make imports-validate",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance explicit local DCF readiness for the listed tickers",
                "target_file": "data/imports/fundamentals.csv",
                "why_it_matters": "These tickers are the best next candidates for explicit local DCF inputs.",
                "safe_next_step": "Keep SEC enrichment import draft and review-only until make imports-validate, make imports-preview, and make imports-apply confirm the merge.",
            },
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 3,
                "step_label": "Refresh status outputs",
                "command": "make status",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance explicit local DCF readiness for the listed tickers",
                "target_file": "data/imports/fundamentals.csv",
                "why_it_matters": "These tickers are the best next candidates for explicit local DCF inputs.",
                "safe_next_step": "Reopen Data Health or Overview after refreshing outputs.",
            },
        ]
    )

    cards = dashboard.overview_bundle_handoff_cards(bundles, details, runbook)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "FUNDAMENTALS HANDOFF"
    assert "dcf readiness" in rendered
    assert "make sec-stage" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "make status-check top_n=5" in rendered
    assert "meta" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_bundle_handoff_cards_normalize_explicit_follow_through_command():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 57 verified rows still needed across this bundle",
                "primary_command": "make bundle-prices",
                "follow_up_command": "python3 -m src.data_update --tickers META,NVDA,TSLA",
            }
        ]
    )

    cards = dashboard.overview_bundle_handoff_cards(bundles, None, None)

    assert cards[1]["title"] == "make price-refresh TICKERS=META,NVDA,TSLA"
    assert cards[1]["command"] == "make price-refresh TICKERS=META,NVDA,TSLA"


def test_overview_bundle_handoff_cards_use_runbook_follow_through_when_bundle_field_is_missing():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance explicit local DCF readiness for the listed tickers",
                "primary_command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=META,NVDA,TSLA",
                "follow_up_command": "",
            }
        ]
    )
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=META,NVDA,TSLA",
            },
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 2,
                "step_label": "Review follow-up output",
                "command": "make imports-validate",
            },
        ]
    )

    cards = dashboard.overview_bundle_handoff_cards(bundles, None, runbook)

    assert cards[1]["title"] == "make imports-validate"
    assert cards[1]["command"] == "make imports-validate"


def test_overview_bundle_handoff_cards_use_staged_follow_through_when_bundle_row_is_sparse():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance explicit local DCF readiness for the listed tickers",
                "primary_command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=META,NVDA,TSLA",
                "follow_up_command": "",
                "target_file": "data/imports/fundamentals.csv",
                "safe_next_step": "Keep SEC enrichment import draft and review-only until make imports-validate, make imports-preview, and make imports-apply confirm the merge.",
            }
        ]
    )

    cards = dashboard.overview_bundle_handoff_cards(bundles, None, None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[1]["title"] == "make imports-validate"
    assert cards[1]["command"] == "make imports-validate"
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered


def test_overview_bundle_handoff_cards_use_staged_summary_when_goal_summary_is_missing():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "why_it_matters": "",
                "primary_command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=META,NVDA,TSLA",
                "follow_up_command": "",
                "target_file": "data/imports/fundamentals.csv",
                "safe_next_step": "Keep SEC enrichment import draft and review-only until make imports-validate, make imports-preview, and make imports-apply confirm the merge.",
            }
        ]
    )

    cards = dashboard.overview_bundle_handoff_cards(bundles, None, None)

    assert cards[0]["command"] == "make sec-stage TICKERS=META,NVDA,TSLA"
    assert "make imports-preview" in cards[0]["body"].lower()
    assert "make imports-apply" in cards[0]["body"].lower()
    assert "start with make sec-stage tickers=meta,nvda,tsla" in cards[0]["body"].lower()
    assert cards[1]["command"] == "make imports-validate"


def test_overview_bundle_handoff_cards_use_runbook_fallback_when_summaries_are_missing():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "ticker_count": 1,
                "tickers": "TSLA",
                "goal_summary": "",
                "why_it_matters": "",
                "bundle_shortcut_command": "",
                "detail_shortcut_command": "",
                "runbook_shortcut_command": "make runbook-peers",
                "primary_command": "",
                "follow_up_command": "",
            }
        ]
    )

    cards = dashboard.overview_bundle_handoff_cards(bundles, None, None)

    assert cards[0]["command"] == "make runbook-peers"
    assert "local import draft workflow next" in cards[0]["body"].lower()
    assert "not available" not in cards[0]["body"].lower()


def test_overview_bundle_handoff_cards_normalize_refresh_command_from_runbook():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance explicit local DCF readiness for the listed tickers",
                "primary_command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=META,NVDA,TSLA",
                "follow_up_command": "make imports-validate",
            }
        ]
    )
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "SEC_USER_AGENT='Name email@example.com' make sec-stage TICKERS=META,NVDA,TSLA",
            },
            {
                "bundle_name": "SEC Fundamentals Bundle",
                "lane": "fundamentals",
                "scope": "holdings_first",
                "step_order": 2,
                "step_label": "Refresh status outputs",
                "command": "make status",
            },
        ]
    )

    cards = dashboard.overview_bundle_handoff_cards(bundles, None, runbook)

    assert cards[2]["title"] == "Refresh status outputs"
    assert cards[2]["command"] == "make status-check TOP_N=5"


def test_overview_bundle_handoff_cards_use_monthly_front_door_for_price_bundle_refresh():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 57 verified rows still needed across this bundle",
                "primary_command": "make bundle-prices",
                "follow_up_command": "make price-status",
                "target_file": "data/imports/prices.csv",
                "why_it_matters": "These tickers still block broader local research because price history is missing or too short.",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            }
        ]
    )
    details = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "ticker": "META",
                "is_holding": True,
                "theme": "AI Platforms",
                "sector_etf": "QQQ",
                "current_unlock_stage": "prices",
            }
        ]
    )
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "make bundle-prices",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 57 verified rows still needed across this bundle",
                "target_file": "data/imports/prices.csv",
            },
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 2,
                "step_label": "Review follow-up output",
                "command": "make price-status",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 57 verified rows still needed across this bundle",
                "target_file": "data/imports/prices.csv",
            },
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 3,
                "step_label": "Refresh status outputs",
                "command": "make status",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Unlock Monthly Picks for 2 tickers; 57 verified rows still needed across this bundle",
                "target_file": "data/imports/prices.csv",
            },
        ]
    )

    cards = dashboard.overview_bundle_handoff_cards(bundles, details, runbook)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[2]["title"] == "Refresh monthly context"
    assert cards[2]["command"] == "make monthly"
    assert "make price-validate" in rendered
    assert "make price-preview" in rendered
    assert "make price-apply" in rendered
    assert "make monthly" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_overview_bundle_handoff_cards_use_monthly_front_door_when_goal_summary_is_missing():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "primary_command": "make bundle-prices",
                "follow_up_command": "make price-status",
                "target_file": "data/imports/prices.csv",
                "why_it_matters": "These tickers still block Monthly Picks because price history is missing or too short.",
                "safe_next_step": "Use local import draft workflows if the free refresh fails.",
            }
        ]
    )
    details = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "ticker": "META",
                "is_holding": True,
                "theme": "AI Platforms",
                "sector_etf": "QQQ",
                "current_unlock_stage": "prices",
            }
        ]
    )
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "make bundle-prices",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "target_file": "data/imports/prices.csv",
            },
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 2,
                "step_label": "Review follow-up output",
                "command": "make price-status",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "target_file": "data/imports/prices.csv",
            },
            {
                "bundle_name": "Price Coverage Bundle",
                "lane": "prices",
                "scope": "holdings_first",
                "step_order": 3,
                "step_label": "Refresh status outputs",
                "command": "make status",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "",
                "target_file": "data/imports/prices.csv",
            },
        ]
    )

    cards = dashboard.overview_bundle_handoff_cards(bundles, details, runbook)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[2]["title"] == "Refresh monthly context"
    assert cards[2]["command"] == "make monthly"
    assert "make price-validate" in rendered
    assert "make price-preview" in rendered
    assert "make price-apply" in rendered
    assert "make monthly" in rendered


def test_overview_bundle_handoff_cards_surface_peer_manual_follow_through():
    bundles = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "ticker_count": 3,
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance transparent peer-relative readiness for the listed tickers",
                "primary_command": "make templates",
                "follow_up_command": "data/imports/peers.csv",
                "target_file": "data/imports/peers.csv",
                "why_it_matters": "These tickers are closest to peer-relative coverage once manually researched peer mappings are added locally.",
                "safe_next_step": "Fill only manually researched peers for the listed tickers, then run make imports-validate, make imports-preview, and make imports-apply before make status refreshes readiness and action outputs.",
            }
        ]
    )
    details = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "ticker": "META",
                "is_holding": True,
                "theme": "AI Platforms",
                "sector_etf": "QQQ",
                "current_unlock_stage": "peers",
            }
        ]
    )
    runbook = pd.DataFrame(
        [
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "step_order": 1,
                "step_label": "Run bundle command",
                "command": "make templates",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance transparent peer-relative readiness for the listed tickers",
                "target_file": "data/imports/peers.csv",
                "why_it_matters": "These tickers are closest to peer-relative coverage once manually researched peer mappings are added locally.",
                "safe_next_step": "Fill only manually researched peers for the listed tickers, then run make imports-validate, make imports-preview, and make imports-apply before make status refreshes readiness and action outputs.",
            },
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "step_order": 2,
                "step_label": "Fill peer mappings manually",
                "command": "data/imports/peers.csv",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance transparent peer-relative readiness for the listed tickers",
                "target_file": "data/imports/peers.csv",
                "why_it_matters": "These tickers are closest to peer-relative coverage once manually researched peer mappings are added locally.",
                "safe_next_step": "Fill only manually researched peers for the listed tickers, then run make imports-validate, make imports-preview, and make imports-apply before make status refreshes readiness and action outputs.",
            },
            {
                "bundle_name": "Peer Mapping Bundle",
                "lane": "peers",
                "scope": "holdings_first",
                "step_order": 3,
                "step_label": "Refresh status outputs",
                "command": "make status",
                "tickers": "META,NVDA,TSLA",
                "goal_summary": "Advance transparent peer-relative readiness for the listed tickers",
                "target_file": "data/imports/peers.csv",
                "why_it_matters": "These tickers are closest to peer-relative coverage once manually researched peer mappings are added locally.",
                "safe_next_step": "Refresh the operator outputs and reopen Data Health or Overview to confirm the updated local coverage state.",
            },
        ]
    )

    cards = dashboard.overview_bundle_handoff_cards(bundles, details, runbook)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "PEERS HANDOFF"
    assert cards[1]["command"] == "data/imports/peers.csv"
    assert cards[2]["command"] == "make status-check TOP_N=5"
    assert "make templates" in rendered
    assert "data/imports/peers.csv" in rendered
    assert "make imports-validate" in rendered
    assert "make imports-preview" in rendered
    assert "make imports-apply" in rendered
    assert "make status-check top_n=5" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_active_research_brief_frame_surfaces_evaluation_without_execution_language():
    readiness = pd.DataFrame(
        [
            {"ticker": "META", "in_active_universe": True},
            {"ticker": "QQQ", "in_active_universe": True},
            {"ticker": "BROAD", "in_active_universe": False},
        ]
    )
    decisions = pd.DataFrame(
        [
            {
                "ticker": "META",
                "asset_type": "company",
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - DCF Ready But Peer Blocked",
                "primary_blocker": "peers",
                "purpose_thesis": "Purpose: Core Compounder. Available data supports a research brief, not a recommendation.",
                "purpose_alignment": "Purpose alignment needs review: current local outputs show `Review Thesis` for Core Compounder.",
                "setup_evaluation": "Setup status: Watch; final state: Watch.",
                "valuation_evaluation": "DCF inputs are ready, but interpretation is constrained by insufficient peer context.",
                "supported_analysis": "Supported analysis: price history, setup and momentum context, standalone DCF scenario analysis.",
                "unsupported_analysis": "Unsupported analysis: peer-relative valuation or opportunity-cost comparison.",
                "risk_watchpoint": "Risk watchpoint: peer-relative context is incomplete.",
                "invalidation_condition": "Invalidate the research brief if fundamentals or DCF inputs no longer pass readiness checks.",
                "next_research_question": "Which source-backed peers should be added to test valuation comparison?",
                "review_priority_reason": "High review priority: core company data is ready, but peer-relative context is still limiting valuation interpretation.",
                "confidence_explanation": "Data confidence is medium-high because core price, fundamentals, and DCF are ready.",
            },
            {
                "ticker": "QQQ",
                "asset_type": "etf",
                "decision_bucket": "Monitor",
                "decision_subtype": "Monitor - ETF Market Proxy",
                "primary_blocker": "none",
                "purpose_thesis": "Purpose: ETF / Defensive / Hedge. Use as market, theme, liquidity, or risk context.",
                "purpose_alignment": "Purpose alignment: ETF / Defensive / Hedge is evaluated as market/risk context.",
                "setup_evaluation": "Setup status: Setup Forming; final state: Setup Forming.",
                "valuation_evaluation": "Operating-company DCF is excluded for this asset type.",
                "supported_analysis": "Supported analysis: price history, ETF/index monitoring, not operating-company valuation.",
                "unsupported_analysis": "Unsupported analysis: operating-company DCF conclusions.",
                "risk_watchpoint": "Risk watchpoint: monitor liquidity, correlation, and theme exposure.",
                "invalidation_condition": "Invalidate market-proxy usefulness if liquidity or theme trend no longer supports the intended monitoring role.",
                "next_research_question": "What market context is this proxy intended to monitor?",
                "review_priority_reason": "Monitor priority: use this proxy for market, theme, liquidity, or risk context.",
                "confidence_explanation": "Data confidence is medium because monitoring uses ready market data.",
            },
            {
                "ticker": "BROAD",
                "decision_bucket": "Blocked by Data",
                "decision_subtype": "Blocked by Data - Missing Price",
                "purpose_thesis": "Inactive broad-universe row should not appear.",
            },
        ]
    )

    brief = dashboard.active_research_brief_frame(readiness, decisions, limit=12)
    cards = dashboard.active_research_brief_cards(brief)
    rendered = " ".join(str(value) for value in brief.to_numpy().ravel()).lower()
    rendered_cards = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert list(brief["ticker"]) == ["META", "QQQ"]
    assert "BROAD" not in set(brief["ticker"])
    assert brief.loc[brief["ticker"].eq("META"), "exact_command"].iloc[0] == "make stock-report-md TICKER=META"
    assert brief.loc[brief["ticker"].eq("META"), "purpose_family"].iloc[0] == "Compounder"
    assert brief.loc[brief["ticker"].eq("META"), "purpose_status"].iloc[0] == "Purpose review needed"
    assert "Operator summary: Purpose review needed" in brief.loc[brief["ticker"].eq("META"), "evaluation_summary"].iloc[0]
    assert "Next blocker: peers" in brief.loc[brief["ticker"].eq("META"), "evaluation_summary"].iloc[0]
    assert "Invalidation:" in brief.loc[brief["ticker"].eq("META"), "evaluation_summary"].iloc[0]
    assert brief.loc[brief["ticker"].eq("META"), "unlock_command"].iloc[0] == "make focus-peers TICKER=META"
    assert brief.loc[brief["ticker"].eq("QQQ"), "purpose_family"].iloc[0] == "ETF / Hedge"
    qqq_summary = brief.loc[brief["ticker"].eq("QQQ"), "evaluation_summary"].iloc[0].lower()
    assert "monitor role: market, theme, liquidity, or risk proxy" in qqq_summary
    assert "operating-company dcf and peer valuation are excluded" in qqq_summary
    assert "next blocker: peers" not in qqq_summary
    assert "research brief" in rendered
    assert "operator summary" in rendered
    assert "purpose alignment needs review" in rendered
    assert "supported analysis" in rendered
    assert "unsupported analysis" in rendered
    assert "peer-relative context is incomplete" in rendered
    assert "operating-company dcf is excluded" in rendered
    assert cards[0]["title"] == "2 active ticker(s)"
    assert "operator summary plus purpose, setup, valuation, supported and unsupported analysis" in rendered_cards
    assert "purpose check" in rendered_cards
    assert "purpose groups" in rendered_cards
    assert "next question" in rendered_cards
    assert "make focus-peers ticker=meta" in rendered_cards
    assert "peer-limited" in rendered_cards
    assert "make stock-report-md ticker=meta" in rendered_cards
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered_cards
    assert "order" not in rendered_cards
    assert "trading" not in rendered_cards
    assert "buy" not in rendered_cards
    assert "sell" not in rendered_cards


def test_active_research_brief_frame_builds_schema_light_fallbacks_without_overclaiming():
    readiness = pd.DataFrame(
        [
            {"ticker": "META", "in_active_universe": True},
            {"ticker": "QQQ", "in_active_universe": True},
            {"ticker": "AMD", "in_active_universe": True},
            {"ticker": "BROAD", "in_active_universe": False},
        ]
    )
    decisions = pd.DataFrame(
        [
            {
                "ticker": "META",
                "asset_type": "company",
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - DCF Ready But Peer Blocked",
                "primary_blocker": "peers",
                "supporting_features": "price history; fundamentals; standalone dcf",
                "blocked_features": "peer mapping",
                "missing_data": "peers: needs at least 2 source-backed peer mappings; earnings: trusted local CSV input",
                "next_best_action": "make focus-peers TICKER=META",
                "data_confidence": "medium",
                "readiness_score": 72,
            },
            {
                "ticker": "QQQ",
                "asset_type": "etf",
                "decision_bucket": "Monitor",
                "decision_subtype": "Monitor - ETF Market Proxy",
                "primary_blocker": "peers",
                "excluded_features": "operating-company dcf",
                "data_confidence": "medium",
            },
            {
                "ticker": "AMD",
                "asset_type": "company",
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - Optional Context Locked",
                "primary_blocker": "earnings",
                "supporting_features": "price history; fundamentals; standalone dcf",
                "missing_data": "earnings; analyst estimates",
                "next_action": "make templates",
                "data_confidence": "medium",
            },
            {
                "ticker": "BROAD",
                "decision_bucket": "Blocked by Data",
                "decision_subtype": "Inactive row",
            },
        ]
    )
    purposes = pd.DataFrame(
        [
            {"Ticker": "META", "FinalPrimaryPurpose": "Core Compounder"},
            {"Ticker": "QQQ", "FinalPrimaryPurpose": "ETF / Defensive / Hedge"},
            {"Ticker": "AMD", "FinalPrimaryPurpose": "Momentum Leader"},
        ]
    )

    brief = dashboard.active_research_brief_frame(readiness, decisions, purposes, limit=12)
    cards = dashboard.active_research_brief_cards(brief)
    rendered = " ".join(str(value) for value in brief.to_numpy().ravel()).lower()
    rendered_cards = " ".join(str(value) for card in cards for value in card.values()).lower()

    rich_columns = [
        "purpose_thesis",
        "evaluation_summary",
        "purpose_alignment",
        "setup_evaluation",
        "valuation_evaluation",
        "supported_analysis",
        "unsupported_analysis",
        "risk_watchpoint",
        "invalidation_condition",
        "next_research_question",
        "review_priority_reason",
        "confidence_explanation",
    ]

    assert list(brief["ticker"]) == ["META", "QQQ", "AMD"]
    assert "BROAD" not in set(brief["ticker"])
    assert not brief[rich_columns].apply(lambda column: column.astype(str).str.lower().eq("not available")).any().any()
    assert brief.loc[brief["ticker"].eq("META"), "purpose_family"].iloc[0] == "Compounder"
    assert "operator summary" in brief.loc[brief["ticker"].eq("META"), "evaluation_summary"].iloc[0].lower()
    assert "next blocker: peers" in brief.loc[brief["ticker"].eq("META"), "evaluation_summary"].iloc[0].lower()
    assert "invalidation:" in brief.loc[brief["ticker"].eq("META"), "evaluation_summary"].iloc[0].lower()
    assert brief.loc[brief["ticker"].eq("META"), "unlock_command"].iloc[0] == "make focus-peers TICKER=META"
    assert brief.loc[brief["ticker"].eq("META"), "data_confidence"].iloc[0] == "medium"
    assert brief.loc[brief["ticker"].eq("QQQ"), "unlock_command"].iloc[0] == "make stock-report-md TICKER=QQQ"
    qqq_summary = brief.loc[brief["ticker"].eq("QQQ"), "evaluation_summary"].iloc[0].lower()
    assert "monitor role: market, theme, liquidity, or risk proxy" in qqq_summary
    assert "operating-company dcf and peer valuation are excluded" in qqq_summary
    assert "next blocker: peers" not in qqq_summary
    assert (
        brief.loc[brief["ticker"].eq("QQQ"), "next_research_question"].iloc[0]
        == "What market, theme, liquidity, or risk context should QQQ monitor, and what would invalidate that proxy role?"
    )
    assert "source-backed peers should be added for qqq" not in rendered
    assert cards[0]["command"] == "make stock-report-md TICKER=META"
    assert cards[3]["command"] == "make focus-peers TICKER=META"
    assert cards[4]["title"] == "1 peer-limited brief(s)"
    assert "peer-relative valuation is withheld" in rendered
    assert "operating-company dcf is excluded" in rendered
    assert "earnings and analyst-estimate context stays locked" in rendered
    assert "peers: needs at least 2 source-backed peer mappings" in rendered
    assert "trusted local csv input" in rendered
    assert "only ready local inputs are used" in rendered
    assert "which source-backed peers should be added for meta before peer-relative valuation is reviewed?" in rendered_cards
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered_cards
    assert "order" not in rendered_cards
    assert "trading" not in rendered_cards
    assert "buy" not in rendered_cards
    assert "sell" not in rendered_cards


def test_active_evaluation_lane_detail_groups_runbook_without_overclaiming():
    queue = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "META",
                "evaluation_lane": "Review standalone thesis, then unlock peers",
                "exact_command": "make stock-report TICKER=META",
                "review_command": "make stock-report TICKER=META",
                "data_unlock_command": "make focus-peers TICKER=META",
                "validation_sequence": "make templates -> fill data/imports/peers.csv with source-backed rows -> make imports-validate -> make imports-preview -> make imports-apply",
                "withheld_conclusion": "Peer-relative valuation is withheld until source-backed peer mappings and metrics are ready.",
                "next_operator_step": "Open META's stock report first; then add source-backed peer rows.",
                "reason": "Core data is ready, but peer-relative context is limiting valuation interpretation.",
                "copy_only_note": "Copy-only command.",
            },
            {
                "priority": 1,
                "ticker": "TSLA",
                "evaluation_lane": "Review standalone thesis, then unlock peers",
                "exact_command": "make stock-report TICKER=TSLA",
                "review_command": "make stock-report TICKER=TSLA",
                "data_unlock_command": "make focus-peers TICKER=TSLA",
                "validation_sequence": "make templates -> fill data/imports/peers.csv with source-backed rows -> make imports-validate -> make imports-preview -> make imports-apply",
                "withheld_conclusion": "Peer-relative valuation is withheld until source-backed peer mappings and metrics are ready.",
                "next_operator_step": "Open TSLA's stock report first; then add source-backed peer rows.",
                "reason": "Core data is ready, but peer-relative context is limiting valuation interpretation.",
                "copy_only_note": "Copy-only command.",
            },
            {
                "priority": 2,
                "ticker": "AMD",
                "evaluation_lane": "Review supported thesis; optional context locked",
                "exact_command": "make stock-report TICKER=AMD",
                "review_command": "make stock-report TICKER=AMD",
                "data_unlock_command": "make templates",
                "validation_sequence": "make templates -> fill trusted earnings or analyst estimates CSV -> make imports-validate -> make imports-preview -> make imports-apply",
                "withheld_conclusion": "Earnings and analyst-estimate context is withheld; core supported analysis may still be reviewed.",
                "next_operator_step": "Open AMD's stock report now; optional context stays withheld.",
                "reason": "Core data is ready.",
                "copy_only_note": "Copy-only command.",
            },
            {
                "priority": 4,
                "ticker": "QQQ",
                "evaluation_lane": "Monitor ETF / market proxy",
                "exact_command": "make stock-report TICKER=QQQ",
                "review_command": "make stock-report TICKER=QQQ",
                "data_unlock_command": "",
                "validation_sequence": "make stock-report TICKER=<ticker> -> compare purpose, supported analysis, unsupported analysis, and source/freshness notes",
                "withheld_conclusion": "Operating-company DCF is excluded for ETF/index-proxy monitoring.",
                "next_operator_step": "Open QQQ's stock report and compare market-proxy context.",
                "reason": "ETF monitor context.",
                "copy_only_note": "Copy-only command.",
            },
        ]
    )

    detail = dashboard.build_active_evaluation_lane_detail_frame(queue)
    cards = dashboard.active_evaluation_lane_detail_cards(detail)
    rendered = " ".join(str(value) for value in detail.to_numpy().ravel()).lower()
    rendered_cards = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert list(detail["evaluation_lane"]) == [
        "Review standalone thesis, then unlock peers",
        "Review supported thesis; optional context locked",
        "Monitor ETF / market proxy",
    ]
    assert detail.iloc[0]["ticker_count"] == 2
    assert detail.iloc[0]["sample_tickers"] == "META, TSLA"
    assert detail.iloc[0]["primary_command"] == "make stock-report TICKER=META"
    assert detail.iloc[0]["data_unlock_command"] == "make focus-peers TICKER=META"
    assert "core data is ready" in detail.iloc[0]["operator_summary"].lower()
    assert "peer-relative valuation is withheld" in detail.iloc[0]["operator_summary"].lower()
    assert detail.iloc[2]["data_unlock_command"] == ""
    assert "make imports-validate" in rendered
    assert "peer-relative valuation is withheld" in rendered
    assert "operating-company dcf is excluded" in rendered
    assert "3 lane(s), 4 ticker(s)" in rendered_cards
    assert "peer-relative valuation is withheld" in rendered_cards
    assert "no overclaiming" in rendered_cards
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered_cards
    assert "order" not in rendered_cards
    assert "trading" not in rendered_cards
    assert "buy" not in rendered_cards
    assert "sell" not in rendered_cards


def test_product_page_logic_audit_checks_readiness_gating_and_queue_safety():
    summary = {
        "blocked_by_data": 3298,
        "price_ready": 240,
    }
    decisions = pd.DataFrame(
        [
            {
                "ticker": "META",
                "asset_type": "company",
                "decision_bucket": "Blocked by Data",
                "primary_blocker": "fundamentals",
                "missing_data": "dcf: free_cash_flow",
                "excluded_features": "",
            },
            {
                "ticker": "NVDA",
                "asset_type": "company",
                "decision_bucket": "Research Now",
                "primary_blocker": "earnings",
                "missing_data": "earnings: trusted local CSV input",
                "excluded_features": "portfolio",
            },
            {
                "ticker": "QQQ",
                "asset_type": "etf",
                "decision_bucket": "Monitor",
                "primary_blocker": "peers",
                "missing_data": "peers: source-backed mappings",
                "excluded_features": "dcf",
            },
        ]
    )
    queue = pd.DataFrame(
        [
            {"ticker": "NVDA", "evaluation_lane": "Review supported thesis; optional context locked"},
            {"ticker": "QQQ", "evaluation_lane": "Monitor ETF / market proxy"},
        ]
    )
    detail = pd.DataFrame(
        [
            {
                "evaluation_lane": "Review supported thesis; optional context locked",
                "ticker_count": 1,
                "validation_sequence": "make templates -> make imports-validate -> make imports-preview -> make imports-apply",
                "copy_only_note": "Copy-only lane guide; the dashboard does not execute refreshes or imports.",
                "withheld_conclusion": "Earnings and analyst-estimate context is withheld; core supported analysis may still be reviewed.",
            },
            {
                "evaluation_lane": "Monitor ETF / market proxy",
                "ticker_count": 1,
                "validation_sequence": "make stock-report TICKER=QQQ -> compare source/freshness notes",
                "copy_only_note": "Copy-only lane guide; the dashboard does not execute refreshes or imports.",
                "withheld_conclusion": "Operating-company DCF is excluded for ETF/index-proxy monitoring.",
            },
        ]
    )
    peer_studio = pd.DataFrame(
        [
            {
                "ticker": "META",
                "workflow_group": "dcf_ready_peer_mapping",
                "next_action": "Add source-backed peer mappings for META in data/imports/peers.csv.",
                "next_action_summary": "Add source-backed peer mappings for META.",
                "focus_command": "make focus-peers TICKER=META",
            },
            {
                "ticker": "QQQ",
                "workflow_group": "monitor_proxy_context",
                "next_action": "ETF/index/fund rows use stock-report monitoring context.",
                "next_action_summary": "ETF/index/fund rows use stock-report monitoring context.",
                "focus_command": "make stock-report TICKER=QQQ",
            },
        ]
    )
    active_unlock = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "exact_command": "make stock-report TICKER=QQQ",
                "validation_sequence": "make stock-report TICKER=QQQ -> review monitor context",
                "next_best_action": "Review QQQ as ETF/index/fund monitor context.",
                "copy_only_note": "Copy-only command; the dashboard does not execute imports or refreshes.",
            }
        ]
    )
    purpose_drilldown = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "exact_command": "make stock-report TICKER=QQQ",
                "unlock_command": "make stock-report TICKER=QQQ",
                "next_research_question": "What market context should QQQ monitor?",
                "copy_only_note": "Copy-only command; the dashboard does not execute imports or refreshes.",
            }
        ]
    )
    next_action_console = pd.DataFrame(
        [
            {
                "action_category": "Single-Stock Review",
                "command": "make stock-report TICKER=QQQ",
                "why_it_matters": "Use one ticker drilldown to verify readiness and source/freshness notes.",
                "safety_note": "Ticker-targeted command; copy into a terminal when ready. The dashboard does not execute it.",
            }
        ]
    )
    readiness_explorer = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "price_ready": True,
                "next_action": "Review monitor context.",
            }
        ]
    )
    additional_visible = {
        "feature readiness cards": pd.DataFrame(
            [
                {
                    "kicker": "FEATURE READINESS",
                    "body": "Optional context remains locked until trusted local rows exist.",
                    "command": "make templates",
                }
            ]
        ),
        "decision workflow cards": pd.DataFrame(
            [
                {
                    "kicker": "DECISION BUCKETS",
                    "body": "Buckets are readiness-gated research workflow labels.",
                    "command": "make project-status",
                }
            ]
        ),
        "peer readiness cards": pd.DataFrame(
            [
                {
                    "kicker": "PEER READY",
                    "body": "Peer blockers remain source-backed and specific.",
                    "command": "make peer-mapping-queue TOP_N=25",
                }
            ]
        ),
        "fundamentals dcf cards": pd.DataFrame(
            [
                {
                    "kicker": "FUNDAMENTALS GAP",
                    "body": "Trusted fundamentals are required before valuation interpretation.",
                    "command": "make sec-stage-queue TOP_N=25",
                }
            ]
        ),
        "import validation cards": pd.DataFrame(
            [
                {
                    "kicker": "IMPORT GUARDRAIL",
                    "body": "Validate trusted local CSV rows before applying them.",
                    "command": "make imports-validate",
                }
            ]
        ),
        "next best action cards": pd.DataFrame(
            [
                {
                    "kicker": "REFRESH REPORTS",
                    "body": "Regenerate readiness after imports.",
                    "command": "make readiness",
                }
            ]
        ),
        "single stock status cards": pd.DataFrame(
            [
                {
                    "kicker": "TICKER STATUS",
                    "body": "Review monitor context and source/freshness notes.",
                    "command": "make stock-report TICKER=QQQ",
                }
            ]
        ),
        "single stock source table": pd.DataFrame(
            [
                {
                    "Area": "Prices",
                    "Freshness": "Local rows are available.",
                    "Next command": "make stock-report TICKER=QQQ",
                }
            ]
        ),
    }

    audit = dashboard.product_page_logic_audit_frame(
        summary,
        decisions,
        queue,
        detail,
        peer_studio,
        active_unlock,
        purpose_drilldown,
        next_action_console,
        readiness_explorer,
        additional_visible,
    )
    cards = dashboard.product_page_logic_audit_cards(audit)
    rendered = " ".join(str(value) for value in audit.to_numpy().ravel()).lower()
    rendered_cards = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert set(audit["status"]) == {"pass"}
    assert "readiness before conclusions" in rendered
    assert "research now gating" in rendered
    assert "etf / index dcf exclusion" in rendered
    assert "active queue lane runbooks" in rendered
    assert "unsupported conclusions withheld" in rendered
    assert "peer action alignment" in rendered
    assert "purpose drilldown actionability" in rendered
    assert "exact copyable commands" in rendered
    assert "research-only language" in rendered
    assert "row-limited active workflow" in rendered
    assert "readiness explorer default limit" in rendered
    assert cards[0]["title"] == "11 pass / 0 review"
    assert "exact copyable commands" in cards[0]["body"]
    assert "research-only language" in cards[0]["body"]
    assert "purpose drilldown" in cards[0]["body"]
    assert "next action console" in cards[0]["body"]
    assert "import validation" in cards[0]["body"]
    assert "blocker queues" in cards[0]["body"]
    assert "next-best-action cards" in cards[0]["body"]
    assert "readiness explorer" in cards[0]["body"]
    assert "single-stock drilldown" in cards[0]["body"]
    assert "feature/decision/peer/fundamentals cards" in cards[0]["body"]
    assert cards[1]["title"] == "No review items"
    assert cards[1]["command"] == "make project-status"
    assert "readiness-first" in rendered_cards
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered_cards
    assert "order" not in rendered_cards
    assert "trading" not in rendered_cards
    assert "buy" not in rendered_cards
    assert "sell" not in rendered_cards


def test_product_page_logic_audit_flags_placeholder_copyable_commands():
    summary = {"blocked_by_data": 1, "price_ready": 1}
    decisions = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "asset_type": "etf",
                "decision_bucket": "Monitor",
                "primary_blocker": "peers",
                "missing_data": "",
                "excluded_features": "dcf",
            }
        ]
    )
    queue = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "evaluation_lane": "Monitor ETF / market proxy",
                "exact_command": "make stock-report TICKER=QQQ",
                "validation_sequence": "make stock-report TICKER=<ticker> -> compare source/freshness notes",
            }
        ]
    )
    detail = pd.DataFrame(
        [
            {
                "evaluation_lane": "Monitor ETF / market proxy",
                "validation_sequence": "make stock-report TICKER=<ticker> -> compare source/freshness notes",
                "copy_only_note": "Copy-only lane guide; the dashboard does not execute refreshes or imports.",
                "withheld_conclusion": "Operating-company DCF is excluded for ETF/index-proxy monitoring.",
            }
        ]
    )
    active_unlock = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "exact_command": "make stock-report TICKER=<ticker>",
                "validation_sequence": "make stock-report TICKER=<ticker> -> review monitor context",
            }
        ]
    )
    purpose_drilldown = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "exact_command": "make stock-report TICKER=<ticker>",
                "unlock_command": "make stock-report TICKER=<ticker>",
            }
        ]
    )
    next_action_console = pd.DataFrame(
        [
            {
                "action_category": "Single-Stock Review",
                "command": "make stock-report TICKER=<ticker>",
                "why_it_matters": "Use one ticker drilldown.",
            }
        ]
    )
    additional_visible = {
        "feature readiness cards": pd.DataFrame(
            [
                {
                    "kicker": "FEATURE READINESS",
                    "command": "make focus-fundamentals TICKER=<ticker>",
                    "body": "Open the row.",
                }
            ]
        ),
        "next best action cards": pd.DataFrame(
            [
                {
                    "kicker": "SINGLE STOCK",
                    "command": "make stock-report TICKER=<ticker>",
                    "body": "Open the ticker report.",
                }
            ]
        ),
        "single stock source table": pd.DataFrame(
            [
                {
                    "Area": "Prices",
                    "Next command": "make stock-report TICKER=<ticker>",
                }
            ]
        ),
    }

    audit = dashboard.product_page_logic_audit_frame(
        summary,
        decisions,
        queue,
        detail,
        active_unlock_frame=active_unlock,
        purpose_drilldown_frame=purpose_drilldown,
        next_action_console_frame=next_action_console,
        additional_visible_frames=additional_visible,
    )
    placeholder_check = audit.loc[audit["check"].eq("Exact copyable commands")].iloc[0]
    rendered = " ".join(str(value) for value in audit.to_numpy().ravel()).lower()

    assert placeholder_check["status"] == "review"
    assert "placeholder ticker commands" in str(placeholder_check["evidence"]).lower()
    assert "exact ticker commands" in str(placeholder_check["operator_action"]).lower()
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_product_page_logic_audit_flags_peer_limited_drilldown_without_unlock_command():
    summary = {"blocked_by_data": 1, "price_ready": 1}
    decisions = pd.DataFrame(
        [
            {
                "ticker": "COHR",
                "asset_type": "company",
                "decision_bucket": "Research Now",
                "primary_blocker": "peers",
                "missing_data": "peers: source-backed mappings",
                "excluded_features": "",
            }
        ]
    )
    purpose_drilldown = pd.DataFrame(
        [
            {
                "ticker": "COHR",
                "purpose_family": "Compounder",
                "primary_blocker": "peers",
                "exact_command": "make stock-report TICKER=COHR",
                "unlock_command": "make stock-report TICKER=COHR",
            }
        ]
    )

    audit = dashboard.product_page_logic_audit_frame(
        summary,
        decisions,
        pd.DataFrame([{"ticker": "COHR"}]),
        pd.DataFrame(),
        purpose_drilldown_frame=purpose_drilldown,
    )
    drilldown_check = audit.loc[audit["check"].eq("Purpose drilldown actionability")].iloc[0]
    rendered = " ".join(str(value) for value in audit.to_numpy().ravel()).lower()

    assert drilldown_check["status"] == "review"
    assert "1 of 1 peer-limited company drilldown row" in str(drilldown_check["evidence"]).lower()
    assert "focus-peers unlock commands" in str(drilldown_check["operator_action"]).lower()
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_product_page_logic_audit_flags_uncapped_readiness_explorer_default():
    summary = {"blocked_by_data": 1, "price_ready": 1}
    readiness_explorer = pd.DataFrame(
        {
            "ticker": [f"T{i:03d}" for i in range(dashboard.DEFAULT_MARKET_ROW_LIMIT + 1)],
            "next_action": ["Review local readiness."] * (dashboard.DEFAULT_MARKET_ROW_LIMIT + 1),
        }
    )

    audit = dashboard.product_page_logic_audit_frame(
        summary,
        pd.DataFrame(),
        pd.DataFrame([{"ticker": "AAA"}]),
        pd.DataFrame(),
        readiness_explorer_frame=readiness_explorer,
    )
    explorer_check = audit.loc[audit["check"].eq("Readiness explorer default limit")].iloc[0]

    assert explorer_check["status"] == "review"
    assert "default cap" in str(explorer_check["evidence"]).lower()
    assert "full-table dumps" in str(explorer_check["operator_action"]).lower()


def test_product_page_logic_audit_flags_execution_or_direct_recommendation_language():
    summary = {"blocked_by_data": 1, "price_ready": 1}
    decisions = pd.DataFrame(
        [
            {
                "ticker": "BAD",
                "asset_type": "company",
                "decision_bucket": "Research Now",
                "primary_blocker": "earnings",
                "missing_data": "earnings: trusted local CSV input",
                "excluded_features": "portfolio",
                "next_action": "Open broker workflow to buy now.",
            }
        ]
    )
    queue = pd.DataFrame(
        [
            {
                "ticker": "BAD",
                "evaluation_lane": "Review supported thesis; optional context locked",
                "next_operator_step": "Open broker workflow to buy now.",
                "exact_command": "make stock-report TICKER=BAD",
            }
        ]
    )
    detail = pd.DataFrame(
        [
            {
                "evaluation_lane": "Review supported thesis; optional context locked",
                "validation_sequence": "make stock-report TICKER=BAD -> compare source/freshness notes",
                "copy_only_note": "Copy-only lane guide; the dashboard does not execute refreshes or imports.",
                "withheld_conclusion": "Earnings and analyst-estimate context is withheld.",
            }
        ]
    )
    active_unlock = pd.DataFrame(
        [
            {
                "ticker": "BAD",
                "next_best_action": "Open broker workflow to buy now.",
                "exact_command": "make stock-report TICKER=BAD",
            }
        ]
    )
    purpose_drilldown = pd.DataFrame(
        [
            {
                "ticker": "BAD",
                "next_research_question": "Open broker workflow to buy now.",
                "exact_command": "make stock-report TICKER=BAD",
            }
        ]
    )
    next_action_console = pd.DataFrame(
        [
            {
                "action_category": "Single-Stock Review",
                "command": "make stock-report TICKER=BAD",
                "why_it_matters": "Open broker workflow to buy now.",
            }
        ]
    )
    additional_visible = {
        "decision workflow cards": pd.DataFrame(
            [
                {
                    "kicker": "DECISION BUCKETS",
                    "body": "Open broker workflow to buy now.",
                    "command": "make project-status",
                }
            ]
        ),
        "blocker queue cards": pd.DataFrame(
            [
                {
                    "kicker": "PRICE",
                    "body": "Open broker workflow to buy now.",
                    "command": "make readiness",
                }
            ]
        ),
        "single stock status cards": pd.DataFrame(
            [
                {
                    "kicker": "TICKER STATUS",
                    "body": "Open broker workflow to buy now.",
                    "command": "make stock-report TICKER=BAD",
                }
            ]
        ),
    }

    audit = dashboard.product_page_logic_audit_frame(
        summary,
        decisions,
        queue,
        detail,
        active_unlock_frame=active_unlock,
        purpose_drilldown_frame=purpose_drilldown,
        next_action_console_frame=next_action_console,
        additional_visible_frames=additional_visible,
    )
    language_check = audit.loc[audit["check"].eq("Research-only language")].iloc[0]

    assert language_check["status"] == "review"
    assert "prohibited execution/recommendation language" in str(language_check["evidence"]).lower()
    assert "direct recommendation wording" in str(language_check["operator_action"]).lower()


def test_product_page_logic_audit_allows_company_names_with_restricted_words():
    summary = {"blocked_by_data": 1, "price_ready": 1}
    decisions = pd.DataFrame(
        [
            {
                "ticker": "BBY",
                "name": "Best Buy",
                "asset_type": "company",
                "decision_bucket": "Blocked by Data",
                "primary_blocker": "fundamentals",
                "missing_data": "dcf: free_cash_flow",
                "excluded_features": "portfolio",
                "next_action": "Import trusted fundamentals for BBY.",
            },
            {
                "ticker": "JCTC",
                "name": "Jewett-Cameron Trading Company - Common Shares",
                "asset_type": "company",
                "decision_bucket": "Blocked by Data",
                "primary_blocker": "fundamentals",
                "missing_data": "dcf: free_cash_flow",
                "excluded_features": "portfolio",
                "next_action": "Import trusted fundamentals for JCTC.",
            },
        ]
    )
    detail = pd.DataFrame(
        [
            {
                "evaluation_lane": "Unlock fundamentals / DCF",
                "validation_sequence": "make focus-fundamentals TICKER=BBY -> make imports-validate",
                "copy_only_note": "Copy-only lane guide; the dashboard does not execute refreshes or imports.",
                "withheld_conclusion": "Valuation is withheld until trusted fundamentals are ready.",
            }
        ]
    )
    queue = pd.DataFrame(
        [
            {
                "ticker": "BBY",
                "evaluation_lane": "Unlock fundamentals / DCF",
                "next_operator_step": "Import trusted fundamentals for BBY.",
                "exact_command": "make focus-fundamentals TICKER=BBY",
            }
        ]
    )

    audit = dashboard.product_page_logic_audit_frame(summary, decisions, queue, detail)
    language_check = audit.loc[audit["check"].eq("Research-only language")].iloc[0]

    assert language_check["status"] == "pass"
    assert "0 row" in str(language_check["evidence"]).lower()


def test_product_page_logic_audit_flags_research_now_with_critical_blockers():
    summary = {"blocked_by_data": 1, "price_ready": 1}
    decisions = pd.DataFrame(
        [
            {
                "ticker": "BAD",
                "asset_type": "company",
                "decision_bucket": "Research Now",
                "primary_blocker": "fundamentals",
                "missing_data": "free_cash_flow",
                "excluded_features": "",
            },
            {
                "ticker": "QQQ",
                "asset_type": "etf",
                "decision_bucket": "Monitor",
                "primary_blocker": "none",
                "missing_data": "",
                "excluded_features": "",
            },
        ]
    )

    audit = dashboard.product_page_logic_audit_frame(summary, decisions, pd.DataFrame(), pd.DataFrame())
    rendered = " ".join(str(value) for value in audit.to_numpy().ravel()).lower()

    research_gate = audit.loc[audit["check"].eq("Research Now gating")].iloc[0]
    etf_gate = audit.loc[audit["check"].eq("ETF / index DCF exclusion")].iloc[0]

    assert research_gate["status"] == "review"
    assert "1 research now row" in str(research_gate["evidence"]).lower()
    assert etf_gate["status"] == "review"
    assert "lack visible dcf exclusion" in str(etf_gate["evidence"]).lower()
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_product_page_logic_audit_flags_stale_peer_action_text():
    summary = {"blocked_by_data": 1, "price_ready": 1}
    decisions = pd.DataFrame(
        [
            {
                "ticker": "COHR",
                "asset_type": "company",
                "decision_bucket": "Research Now",
                "primary_blocker": "peers",
                "missing_data": "peers: source-backed mappings",
                "excluded_features": "",
            }
        ]
    )
    queue = pd.DataFrame([{"ticker": "COHR", "evaluation_lane": "Review standalone thesis, then unlock peers"}])
    detail = pd.DataFrame(
        [
            {
                "evaluation_lane": "Review standalone thesis, then unlock peers",
                "validation_sequence": "make focus-peers TICKER=COHR -> make imports-validate -> make imports-preview -> make imports-apply",
                "copy_only_note": "Copy-only lane guide; the dashboard does not execute refreshes or imports.",
                "withheld_conclusion": "Peer valuation context is withheld until source-backed peer rows exist.",
            }
        ]
    )
    stale_peer_studio = pd.DataFrame(
        [
            {
                "ticker": "COHR",
                "workflow_group": "dcf_ready_peer_mapping",
                "next_action": "Optional context missing for COHR; leave unavailable unless trusted local CSVs exist.",
                "next_action_summary": "Optional context missing for COHR.",
                "focus_command": "make focus-peers TICKER=COHR",
            }
        ]
    )

    audit = dashboard.product_page_logic_audit_frame(summary, decisions, queue, detail, stale_peer_studio)
    peer_alignment = audit.loc[audit["check"].eq("Peer action alignment")].iloc[0]
    rendered = " ".join(str(value) for value in audit.to_numpy().ravel()).lower()

    assert peer_alignment["status"] == "review"
    assert "1 of 1 peer focus row" in str(peer_alignment["evidence"]).lower()
    assert "source-backed peer mapping guidance" in str(peer_alignment["operator_action"]).lower()
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_product_page_logic_audit_requires_visible_peer_action_text():
    summary = {"blocked_by_data": 1, "price_ready": 1}
    decisions = pd.DataFrame(
        [
            {
                "ticker": "COHR",
                "asset_type": "company",
                "decision_bucket": "Research Now",
                "primary_blocker": "peers",
                "missing_data": "peers: source-backed mappings",
                "excluded_features": "",
            }
        ]
    )
    queue = pd.DataFrame([{"ticker": "COHR", "evaluation_lane": "Review standalone thesis, then unlock peers"}])
    detail = pd.DataFrame(
        [
            {
                "evaluation_lane": "Review standalone thesis, then unlock peers",
                "validation_sequence": "make focus-peers TICKER=COHR -> make imports-validate -> make imports-preview -> make imports-apply",
                "copy_only_note": "Copy-only lane guide; the dashboard does not execute refreshes or imports.",
                "withheld_conclusion": "Peer valuation context is withheld until source-backed peer rows exist.",
            }
        ]
    )
    blank_action_peer_studio = pd.DataFrame(
        [
            {
                "ticker": "COHR",
                "workflow_group": "dcf_ready_peer_mapping",
                "next_action": "",
                "next_action_summary": "",
                "focus_command": "make focus-peers TICKER=COHR",
            }
        ]
    )

    audit = dashboard.product_page_logic_audit_frame(summary, decisions, queue, detail, blank_action_peer_studio)
    peer_alignment = audit.loc[audit["check"].eq("Peer action alignment")].iloc[0]
    rendered = " ".join(str(value) for value in audit.to_numpy().ravel()).lower()

    assert peer_alignment["status"] == "review"
    assert "1 of 1 peer focus row" in str(peer_alignment["evidence"]).lower()
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_active_evaluation_queue_ranks_active_next_steps_without_execution_language():
    active_briefs = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "decision_bucket": "Monitor",
                "decision_subtype": "Monitor - ETF Market Proxy",
                "purpose_family": "ETF / Hedge",
                "primary_blocker": "peers",
                "data_confidence": "medium",
                "next_research_question": "What market context is this proxy intended to monitor?",
                "review_priority_reason": "Monitor priority: use this proxy for market, theme, liquidity, or risk context.",
                "exact_command": "make stock-report TICKER=QQQ",
                "unlock_command": "make focus-peers TICKER=QQQ",
            },
            {
                "ticker": "AMD",
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - Optional Context Locked",
                "purpose_family": "Compounder",
                "primary_blocker": "earnings",
                "data_confidence": "medium",
                "next_research_question": "Does the supported local evidence still match the compounder purpose?",
                "review_priority_reason": "Core company data is ready; optional earnings context is still unavailable.",
                "exact_command": "make stock-report TICKER=AMD",
                "unlock_command": "make templates",
            },
            {
                "ticker": "META",
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - DCF Ready But Peer Blocked",
                "purpose_family": "Compounder",
                "primary_blocker": "peers",
                "data_confidence": "medium",
                "next_research_question": "Which source-backed peers should be added?",
                "review_priority_reason": "High review priority: core company data is ready, but peer-relative context is still limiting valuation interpretation.",
                "exact_command": "make stock-report TICKER=META",
                "unlock_command": "make focus-peers TICKER=META",
            },
            {
                "ticker": "APLD",
                "decision_bucket": "Blocked by Data",
                "decision_subtype": "Blocked by Data - Missing Fundamentals",
                "purpose_family": "Speculative",
                "primary_blocker": "fundamentals",
                "data_confidence": "low",
                "next_research_question": "Which trusted fundamentals are available?",
                "review_priority_reason": "Data unlock comes before valuation interpretation.",
                "exact_command": "make stock-report TICKER=APLD",
                "unlock_command": "make focus-fundamentals TICKER=APLD",
            },
        ]
    )
    readiness = pd.DataFrame(
        [
            {"ticker": "META", "overall_readiness_state": "partial", "updated_at": "2026-06-01T00:00:00Z"},
            {"ticker": "AMD", "overall_readiness_state": "partial", "updated_at": "2026-06-01T00:00:00Z"},
            {"ticker": "QQQ", "overall_readiness_state": "partial", "updated_at": "2026-06-01T00:00:00Z"},
            {"ticker": "APLD", "overall_readiness_state": "blocked", "updated_at": "2026-06-01T00:00:00Z"},
        ]
    )

    queue = dashboard.build_active_evaluation_queue_frame(active_briefs, readiness, limit=12)
    cards = dashboard.active_evaluation_queue_cards(queue)
    rendered = " ".join(str(value) for value in queue.to_numpy().ravel()).lower()
    rendered_cards = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert list(queue["ticker"]) == ["META", "AMD", "QQQ", "APLD"]
    assert queue.iloc[0]["evaluation_lane"] == "Review standalone thesis, then unlock peers"
    assert queue.iloc[0]["data_confidence"] == "medium"
    assert queue.iloc[0]["exact_command"] == "make stock-report-md TICKER=META"
    assert queue.iloc[0]["data_unlock_command"] == "make focus-peers TICKER=META"
    assert queue.iloc[0]["review_command"] == "make stock-report-md TICKER=META"
    assert queue.iloc[0]["validation_sequence"].startswith("make focus-peers TICKER=META")
    assert "priority rationale" in queue.iloc[0]["reason"].lower()
    assert "core company evidence is reviewable" in queue.iloc[0]["reason"].lower()
    assert queue.iloc[1]["evaluation_lane"] == "Review supported thesis; optional context locked"
    assert queue.iloc[1]["exact_command"] == "make stock-report-md TICKER=AMD"
    assert queue.iloc[1]["data_unlock_command"] == "make templates"
    assert queue.iloc[2]["evaluation_lane"] == "Monitor ETF / market proxy"
    assert queue.iloc[2]["exact_command"] == "make stock-report-md TICKER=QQQ"
    assert queue.iloc[2]["data_unlock_command"] == ""
    assert queue.iloc[2]["validation_sequence"].startswith("make stock-report-md TICKER=QQQ")
    assert "monitor context" in queue.iloc[2]["reason"].lower()
    assert "peer valuation stay excluded" in queue.iloc[2]["reason"].lower()
    assert "primary blocker: peers" not in queue.iloc[2]["reason"].lower()
    assert queue.iloc[3]["evaluation_lane"] == "Unlock fundamentals / DCF"
    assert queue.iloc[3]["data_confidence"] == "low"
    assert queue.iloc[3]["exact_command"] == "make focus-fundamentals TICKER=APLD"
    assert queue.iloc[3]["validation_sequence"].startswith("make focus-fundamentals TICKER=APLD")
    assert "ticker=<ticker>" not in rendered
    assert "data/imports/peers.csv" in rendered
    assert "make imports-validate" in rendered
    assert "earnings and analyst-estimate context is withheld" in rendered
    assert "operating-company dcf is excluded" in rendered
    assert "readiness state partial" in rendered
    assert cards[0]["title"] == "4 active ticker(s) ranked"
    assert "priority rationale" in cards[1]["body"].lower()
    assert "peer-relative valuation is withheld" in cards[1]["body"].lower()
    assert "+1 more lane(s)" in cards[2]["title"]
    assert "not an action list" in rendered_cards
    assert "recommendation" not in rendered_cards
    assert "no dashboard execution" in rendered_cards
    assert "make stock-report-md ticker=meta" in rendered_cards
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered_cards
    assert "order" not in rendered_cards
    assert "trading" not in rendered_cards
    assert "buy" not in rendered_cards
    assert "sell" not in rendered_cards


def test_purpose_evaluation_summary_cards_are_copy_only_and_data_honest():
    summary = pd.DataFrame(
        [
            {
                "purpose_family": "Compounder",
                "decision_bucket": "Research Now",
                "total_count": 3,
                "active_universe_count": 2,
                "research_now_count": 3,
                "monitor_count": 0,
                "blocked_count": 0,
                "purpose_review_needed_count": 1,
                "data_unlock_first_count": 0,
                "peer_limited_count": 2,
                "fundamentals_limited_count": 0,
                "optional_context_locked_count": 0,
                "top_unlock_command": "make focus-peers TICKER=META",
                "top_next_research_question": "Which source-backed peers should be added?",
                "sample_tickers": "META, NVDA",
            },
            {
                "purpose_family": "ETF / Hedge",
                "decision_bucket": "Monitor",
                "total_count": 1,
                "active_universe_count": 1,
                "research_now_count": 0,
                "monitor_count": 1,
                "blocked_count": 0,
                "purpose_review_needed_count": 0,
                "data_unlock_first_count": 0,
                "peer_limited_count": 0,
                "fundamentals_limited_count": 0,
                "optional_context_locked_count": 0,
                "top_unlock_command": "make stock-report TICKER=QQQ",
                "top_next_research_question": "What market context is this proxy intended to monitor?",
                "sample_tickers": "QQQ",
            },
        ]
    )

    cards = dashboard.purpose_evaluation_summary_cards(summary)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "4 ticker(s) grouped"
    assert "research now: 3" in rendered
    assert "active group" in rendered
    assert "make focus-peers ticker=meta" in rendered
    assert "schema-only until trusted rows" in rendered
    assert "no overclaiming" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_purpose_evaluation_drilldown_cards_surface_next_row_without_execution_language():
    drilldown = pd.DataFrame(
        [
            {
                "ticker": "META",
                "is_active_universe": True,
                "purpose_family": "Compounder",
                "decision_bucket": "Research Now",
                "primary_blocker": "peers",
                "next_research_question": "Which source-backed peers should be added?",
                "purpose_alignment": "Purpose alignment needs review.",
                "unsupported_analysis": "Unsupported analysis: peer-relative valuation.",
                "exact_command": "make stock-report TICKER=META",
                "unlock_command": "make focus-peers TICKER=META",
            },
            {
                "ticker": "NVDA",
                "is_active_universe": True,
                "purpose_family": "Momentum",
                "decision_bucket": "Research Now",
                "primary_blocker": "earnings",
                "next_research_question": "Does relative strength still support the momentum purpose?",
                "unsupported_analysis": "Unsupported analysis: earnings and analyst estimate trend context.",
                "exact_command": "make stock-report TICKER=NVDA",
                "unlock_command": "make templates",
            },
            {
                "ticker": "QQQ",
                "is_active_universe": True,
                "purpose_family": "ETF / Hedge",
                "decision_bucket": "Monitor",
                "primary_blocker": "peers",
                "next_research_question": "What market context is this proxy intended to monitor?",
                "unsupported_analysis": "Unsupported analysis: operating-company DCF.",
                "exact_command": "make stock-report TICKER=QQQ",
                "unlock_command": "make stock-report TICKER=QQQ",
            },
        ]
    )

    cards = dashboard.purpose_evaluation_drilldown_cards(drilldown)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "3 row(s), 3 active"
    assert cards[1]["command"] == "make stock-report-md TICKER=META"
    assert cards[2]["title"] == "1 peer-limited, 1 optional-context-limited"
    assert "which source-backed peers should be added" in rendered
    assert "make stock-report-md ticker=meta" in rendered
    assert "peer valuation remains blocked" in rendered
    assert "trusted csv rows" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
