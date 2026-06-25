from types import SimpleNamespace

from src import research_loop


def test_research_loop_strip_links_are_navigation_only_and_guardrail_safe():
    html = research_loop.research_loop_strip_html(
        current_step="Data Health source-proof lane",
        previous_proof="Readiness snapshot is current",
        next_action="Open Proof review details.",
        stop_rule="Stop before apply without reviewed proof",
        current_href="?mode=operator&page=data-health&lane=proof",
        proof_href="?mode=operator&page=data-health&lane=proof&drawer=proof",
        action_href="?mode=operator&page=data-health&lane=proof&drawer=proof",
        stop_href="?mode=operator&page=data-health&lane=proof&drawer=proof",
    ).lower()

    assert "research-loop-strip" in html
    assert html.count("research-loop-link") == 4
    assert "drawer=proof" in html
    assert "make " not in html
    assert "buy" not in html
    assert "sell" not in html
    assert "broker" not in html


def test_research_loop_contexts_keep_home_single_stock_and_data_health_connected():
    current = SimpleNamespace(status="current", message="Readiness artifacts are current.", refresh_command="make readiness")
    stale = SimpleNamespace(status="stale", message="Generated readiness artifacts are stale.", refresh_command="make readiness")
    summary = {"price_ready": 3538, "dcf_ready": 59, "peer_ready": 26}

    home = research_loop.home_research_loop_context(summary, current)
    home_stale = research_loop.home_research_loop_context(summary, stale)
    pre_report = research_loop.single_stock_research_loop_context("NVDA")
    loaded_report = research_loop.single_stock_research_loop_context(
        "NVDA",
        {
            "analysis_mode": "DCF-ready review",
            "valuation_readiness": {"status": "ready"},
        },
    )
    data_health = research_loop.data_health_research_loop_context(
        selected_lane_key="fundamentals",
        readiness_freshness=stale,
        next_action="Review fundamentals import draft",
        public_mode=False,
    )
    proof_lane = research_loop.data_health_research_loop_context(
        selected_lane_key="proof",
        readiness_freshness=current,
        next_action="Open Proof review details.",
        public_mode=False,
    )

    assert home["current_step"] == "Home readiness snapshot"
    assert home["current_note"] == "3,538 price-ready / 59 DCF-ready / 26 peer-ready"
    assert home["next_action"] == "Open a Single-Stock Report"
    assert home_stale["proof_note"] == "make readiness"
    assert pre_report["current_step"] == "Single-Stock Report"
    assert pre_report["next_action"] == "Open Review"
    assert loaded_report["current_step"] == "NVDA report review"
    assert loaded_report["next_action"] == "Review Detailed Review tabs after the readiness summary"
    assert loaded_report["proof_href"] == "?mode=public&page=data-health&drawer=proof"
    assert loaded_report["stop_href"] == "?mode=public&page=data-health&drawer=proof"
    assert proof_lane["current_step"] == "Proof lane shell"
    assert proof_lane["next_action"] == "Open Proof review details."
    assert data_health["current_note"] == "Fundamentals / DCF ROUTE MAP; artifact hygiene before staging"
    assert data_health["next_action"] == "Review fundamentals import file"
    assert data_health["action_href"] == "?mode=operator&page=data-health&lane=fundamentals&drawer=batch"
    rendered = " ".join(" ".join(value.values()) for value in [home, pre_report, loaded_report, data_health]).lower()
    assert "recommendation" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered
    assert "at a glance" not in rendered
    assert "reader guide" not in rendered

    public_data_health = research_loop.data_health_research_loop_context(
        selected_lane_key="proof",
        readiness_freshness=current,
        next_action="Open the public evidence drawer",
        public_mode=True,
    )
    public_rendered = " ".join(public_data_health.values()).lower()
    assert "commands stay copy-only" not in public_rendered
    assert "copy-only" not in public_rendered
    assert "validate and preview" not in public_rendered
    assert "evidence stays collapsed" in public_rendered


def test_data_health_research_loop_action_href_respects_copy_only_commands():
    assert research_loop.data_health_research_loop_action_href(
        "metrics",
        "Open Metrics review details.",
        public_mode=False,
    ) == "?mode=operator&page=data-health&lane=metrics&drawer=metrics"
    assert research_loop.data_health_research_loop_action_href(
        "proof",
        "Open Proof review details.",
        public_mode=False,
    ) == "?mode=operator&page=data-health&lane=proof&drawer=proof"
    assert research_loop.data_health_research_loop_action_href(
        "fundamentals",
        "make readiness",
        public_mode=False,
    ) == ""
    assert research_loop.data_health_research_loop_action_href(
        "fundamentals",
        "Open Batch execution review details.",
        public_mode=False,
    ) == "?mode=operator&page=data-health&lane=fundamentals&drawer=batch"
    assert research_loop.data_health_research_loop_action_href(
        "fundamentals",
        "Open Batch execution review details.",
        public_mode=True,
    ) == "?mode=public&page=data-health&drawer=proof"
