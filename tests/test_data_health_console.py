from types import SimpleNamespace

from src import data_health_console as console


def test_data_health_console_lane_aliases_and_nav_html():
    assert console.data_health_operator_lane_from_query("price") == "prices"
    assert console.data_health_operator_lane_from_query("fundamentals-dcf") == "fundamentals"
    assert console.data_health_operator_lane_from_query("proof-history") == "proof"
    assert console.data_health_operator_lane_from_query("unknown") == "prices"

    header = console.data_health_operator_queue_header_html()
    nav = console.data_health_operator_lane_nav_html("metrics")

    assert "Operator Queue" in header
    assert "Evidence and commands stay collapsed" in header
    assert "ops-lane-link active" in nav
    assert "lane=metrics" in nav
    assert "Fundamentals / DCF" in nav


def test_data_health_console_current_mode_strip_is_copy_only_and_research_safe():
    freshness = SimpleNamespace(
        status="current",
        message="Readiness artifacts are current relative to watched source files.",
        refresh_command="make readiness",
    )
    preflight = SimpleNamespace(packet_command="DRY_RUN=1 make reviewed-batch LANE=prices TOP_N=10")

    html = console.data_health_current_mode_strip_html(
        selected_lane_key="prices",
        queue_details_requested=False,
        batch_details_requested=False,
        metric_details_requested=False,
        proof_details_requested=False,
        readiness_freshness=freshness,
        batch_preflight=preflight,
        metric_detail_status={"next_action": "Open the Metrics evidence drawer."},
    ).lower()

    assert "ops-mode-strip" in html
    assert "prices" in html
    assert "fast view" in html
    assert "queue detail" in html
    assert "open batch execution review details" in html
    assert "copy-only" in html
    assert "research readiness" in html
    assert "buy" not in html
    assert "sell" not in html
    assert "broker" not in html
    assert "order routing" not in html


def test_data_health_console_stale_and_detail_modes_gate_next_action():
    stale = SimpleNamespace(
        status="stale",
        message="Generated readiness artifacts are stale.",
        refresh_command="make readiness",
    )
    current = SimpleNamespace(status="current", message="Current.", refresh_command="make readiness")
    preflight = SimpleNamespace(packet_command="DRY_RUN=1 make reviewed-batch LANE=peers TOP_N=10")

    stale_action = console.data_health_current_mode_next_action(
        "metrics",
        batch_details_requested=True,
        metric_detail_status={"next_action": "Open the Metrics evidence drawer."},
        proof_details_requested=False,
        readiness_freshness=stale,
        batch_preflight=preflight,
    )
    proof_action = console.data_health_current_mode_next_action(
        "proof",
        batch_details_requested=False,
        metric_detail_status={},
        proof_details_requested=False,
        readiness_freshness=current,
        batch_preflight=preflight,
    )
    batch_action = console.data_health_current_mode_next_action(
        "peers",
        batch_details_requested=True,
        metric_detail_status={},
        proof_details_requested=False,
        readiness_freshness=current,
        batch_preflight=preflight,
    )

    assert stale_action == "make readiness-preview TOP_N=20"
    assert proof_action == "Open Proof review details."
    assert batch_action == "DRY_RUN=1 make reviewed-batch LANE=peers TOP_N=10"
