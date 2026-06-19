from pathlib import Path

from src import readiness_ops as readiness_ops_module
from src.readiness_ops import (
    build_fundamentals_peer_metrics_queue,
    build_fundamentals_peer_metrics_queue_from_lanes,
    build_data_coverage_proof_queues,
    build_data_coverage_expansion_plan,
    build_peer_readiness_summary,
    build_coverage_frontier,
    build_readiness_ops_lanes,
    render_data_coverage_proof_queues,
    render_fundamentals_peer_metrics_queue,
    render_data_coverage_expansion_plan,
    render_coverage_frontier,
    render_readiness_ops_center,
    render_readiness_ops_evidence,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sample_root(tmp_path: Path) -> Path:
    root = tmp_path
    _write(
        root / "data" / "universe.csv",
        "\n".join(
            [
                "ticker,default_purpose,market_cap_bucket",
                "AAA,Momentum Leader,Large",
                "BBB,Core Compounder,Mid",
                "QQQ,ETF / Defensive / Hedge,ETF",
            ]
        )
        + "\n",
    )
    _write(
        root / "data" / "fundamentals.csv",
        "\n".join(
            [
                "ticker,revenue,free_cash_flow,fcf_margin,shares_outstanding",
                "AAA,100,20,0.20,10",
                "BBB,80,10,0.125,",
            ]
        )
        + "\n",
    )
    _write(
        root / "data" / "prices.csv",
        "\n".join(
            [
                "ticker,date,close",
                "AAA,2026-01-01,100",
                "BBB,2026-01-01,50",
                "QQQ,2026-01-01,500",
            ]
        )
        + "\n",
    )
    _write(
        root / "data" / "reports" / "ticker_readiness_report.csv",
        "\n".join(
            [
                "ticker,asset_type,price_ready,fundamentals_ready,dcf_ready,peer_ready,earnings_ready,analyst_estimates_ready,overall_readiness_state,blocked_features,excluded_features,missing_data",
                "AAA,company,true,true,true,false,false,false,partial,peer earnings analyst_estimates,,peers: needs at least 2 source-backed peer mappings; earnings: trusted local CSV input; analyst_estimates: trusted local CSV input",
                "BBB,company,false,false,false,false,false,false,blocked,price fundamentals dcf peer earnings analyst_estimates,,dcf: revenue; peers: needs at least 2 source-backed peer mappings",
                "QQQ,etf,true,false,false,false,false,false,partial,earnings analyst_estimates,dcf,earnings: trusted local CSV input; analyst_estimates: trusted local CSV input",
            ]
        )
        + "\n",
    )
    _write(
        root / "data" / "reports" / "feature_readiness_summary.csv",
        "\n".join(
            [
                "feature,ready_count,partial_count,blocked_count,excluded_count,total_count,top_blocker,next_action,unlock_command",
                "price,2,0,1,0,3,needs price rows,make price-worklist TOP_N=25,make price-worklist TOP_N=25",
                "fundamentals,1,0,2,0,3,missing fundamentals,make sec-stage-queue TOP_N=25,make sec-stage-queue TOP_N=25",
            ]
        )
        + "\n",
    )
    _write(
        root / "data" / "reports" / "peer_unlock_worklist.csv",
        "priority,ticker,workflow_group,missing_peer_reason\n1,AAA,peer_valuation_unlock,peer valuation still requires inputs\n",
    )
    _write(
        root / "data" / "reports" / "peer_readiness_report.csv",
        "\n".join(
            [
                "ticker,peer_count,mapping_status,peer_blocker_type,peer_price_ready,peer_momentum_ready,peer_fundamentals_ready,peer_valuation_ready,peer_valuation_comparison_ready",
                "AAA,2,mapped,peer_fundamentals_missing,true,true,false,false,false",
                "BBB,0,missing_mapping,missing_peer_mapping,false,false,false,false,false",
                "QQQ,2,mapped,peer_valuation_blocked,true,true,true,false,false",
            ]
        )
        + "\n",
    )
    _write(root / "data" / "reviewed_data_proofs.csv", "proof_id,proof_date,lane\nRDP-1,2026-06-12,peer\n")
    return root


def test_readiness_ops_center_preserves_lane_states_and_locked_context(tmp_path: Path):
    lanes = build_readiness_ops_lanes(_sample_root(tmp_path))
    by_lane = {lane.lane: lane for lane in lanes}

    assert by_lane["price_coverage"].readiness_state == "partial"
    assert by_lane["price_coverage"].workflow_mode == "dry_run_first"
    assert by_lane["fundamentals_dcf"].workflow_mode == "preview_first_reviewed_apply"
    assert by_lane["share_count_proof"].workflow_mode == "preview_first_reviewed_apply"
    assert by_lane["share_count_proof"].blocked_count == 1
    assert by_lane["share_count_proof"].partial_count == 1
    assert "shares_outstanding proof" in by_lane["share_count_proof"].source_readiness
    assert by_lane["peer_mapping"].blocked_count == 2
    assert "Peer sub-states:" in by_lane["peer_mapping"].notes
    assert "peer_valuation_comparison=0" in by_lane["peer_valuation_inputs"].notes
    assert by_lane["earnings_locked"].workflow_mode == "locked_manual"
    assert by_lane["analyst_estimates_locked"].workflow_mode == "locked_manual"
    assert by_lane["excluded_not_applicable"].readiness_state == "excluded"
    assert "trusted local rows" in by_lane["earnings_locked"].notes


def test_fundamentals_peer_metrics_queue_summarizes_next_layer_without_fake_unlocks(tmp_path: Path):
    rows = build_fundamentals_peer_metrics_queue(_sample_root(tmp_path), top_n=2)
    rendered = render_fundamentals_peer_metrics_queue(rows)
    by_lane = {row.lane: row for row in rows}

    assert set(by_lane) >= {
        "fundamentals_dcf",
        "peer_mapping",
        "peer_valuation_inputs",
        "metrics_readiness",
        "earnings_locked",
        "analyst_estimates_locked",
    }
    assert by_lane["fundamentals_dcf"].source_mode == "SEC-stageable or trusted-local"
    assert "trusted fundamentals" in by_lane["fundamentals_dcf"].top_missing_input_families
    assert "source-backed peer mappings" in by_lane["peer_mapping"].top_missing_input_families
    assert "mapped peer prices" in by_lane["peer_valuation_inputs"].top_missing_input_families
    assert by_lane["metrics_readiness"].source_lane == "review_metrics"
    assert "SPY/QQQ" in by_lane["metrics_readiness"].proof_gate
    assert by_lane["earnings_locked"].source_mode == "optional trusted-local only"
    assert "not a ranking, recommendation, or trade instruction" in rendered
    assert "Validate -> preview" in rendered
    assert "Sharpe" in rendered
    assert "do not infer fundamentals" in rendered
    assert "buy" not in rendered.lower()
    assert "sell" not in rendered.lower()


def test_fundamentals_peer_metrics_queue_can_reuse_existing_lanes(tmp_path: Path):
    root = _sample_root(tmp_path)
    lanes = build_readiness_ops_lanes(root)
    direct_rows = build_fundamentals_peer_metrics_queue(root, top_n=2)
    reused_rows = build_fundamentals_peer_metrics_queue_from_lanes(lanes, root=root, top_n=2)

    assert [row.lane for row in reused_rows] == [row.lane for row in direct_rows]
    assert [row.readiness_state for row in reused_rows] == [row.readiness_state for row in direct_rows]
    assert [row.top_missing_input_families for row in reused_rows] == [
        row.top_missing_input_families for row in direct_rows
    ]


def test_readiness_queue_cli_does_not_prebuild_unneeded_frontier(tmp_path: Path, monkeypatch, capsys):
    lane_calls = []

    def fail_if_prebuilt(root):
        lane_calls.append(root)
        raise AssertionError("readiness queue should not prebuild ops lanes before routing")

    monkeypatch.setattr(readiness_ops_module, "build_readiness_ops_lanes", fail_if_prebuilt)
    monkeypatch.setattr(readiness_ops_module, "build_fundamentals_peer_metrics_queue", lambda root, top_n: [])

    assert readiness_ops_module.main(["--root", str(tmp_path), "--readiness-queue", "--top-n", "7"]) == 0

    assert lane_calls == []
    assert "No queue rows are available" in capsys.readouterr().out


def test_peer_readiness_summary_separates_mapping_trend_and_valuation_inputs(tmp_path: Path):
    summary = build_peer_readiness_summary(_sample_root(tmp_path))

    assert summary.peer_mapping_ready == 2
    assert summary.peer_price_ready == 2
    assert summary.peer_momentum_ready == 2
    assert summary.peer_fundamentals_ready == 1
    assert summary.peer_valuation_ready == 0
    assert summary.peer_valuation_comparison_ready == 0
    assert summary.missing_mapping == 1
    assert summary.missing_peer_fundamentals == 1
    assert summary.peer_valuation_blocked == 1
    assert summary.valuation_input_blockers == 2
    assert "peer trend can be ready before peer valuation comparison is ready" in summary.source_context


def test_peer_frontier_ranks_mapping_before_mapped_peer_inputs_when_mapping_is_prerequisite(tmp_path: Path):
    root = tmp_path
    _write(
        root / "data" / "reports" / "ticker_readiness_report.csv",
        "\n".join(
            [
                "ticker,asset_type,price_ready,fundamentals_ready,dcf_ready,peer_ready,earnings_ready,analyst_estimates_ready,overall_readiness_state,blocked_features,excluded_features,missing_data",
                "AAA,company,true,true,true,false,false,false,partial,peer,,peers: needs at least 2 source-backed peer mappings",
                "BBB,company,true,true,true,false,false,false,partial,peer,,peers: needs at least 2 source-backed peer mappings",
                "CCC,company,true,true,true,false,false,false,partial,peer,,peers: peer trend comparison ready; peer valuation still requires peer_valuation_ready",
                "DDD,company,true,true,true,true,false,false,partial,earnings analyst_estimates,,earnings: trusted local CSV input",
            ]
        )
        + "\n",
    )
    _write(
        root / "data" / "reports" / "feature_readiness_summary.csv",
        "\n".join(
            [
                "feature,ready_count,partial_count,blocked_count,excluded_count,total_count,top_blocker,next_action,unlock_command",
                "price,4,0,0,0,4,-,-,-",
                "fundamentals,4,0,0,0,4,-,-,-",
            ]
        )
        + "\n",
    )
    _write(
        root / "data" / "reports" / "peer_unlock_worklist.csv",
        "\n".join(
            [
                "priority,ticker,workflow_group,missing_peer_reason",
                "1,AAA,dcf_ready_peer_mapping,needs at least 2 source-backed peer mappings",
                "1,BBB,dcf_ready_peer_mapping,needs at least 2 source-backed peer mappings",
                "1,CCC,peer_valuation_unlock,peer valuation still requires inputs",
            ]
        )
        + "\n",
    )
    _write(
        root / "data" / "reports" / "peer_readiness_report.csv",
        "\n".join(
            [
                "ticker,peer_count,mapping_status,peer_blocker_type,peer_price_ready,peer_momentum_ready,peer_fundamentals_ready,peer_valuation_ready,peer_valuation_comparison_ready",
                "AAA,0,missing_mapping,missing_peer_mapping,false,false,false,false,false",
                "BBB,0,missing_mapping,missing_peer_mapping,false,false,false,false,false",
                "CCC,2,mapped,peer_fundamentals_missing,true,true,false,false,false",
                "DDD,2,mapped,ready,true,true,true,true,true",
            ]
        )
        + "\n",
    )

    lanes = build_readiness_ops_lanes(root)
    by_lane = {lane.lane: lane for lane in lanes}
    peer_frontier = build_coverage_frontier(
        [by_lane["peer_mapping"], by_lane["peer_valuation_inputs"]],
        top_n=2,
    )

    assert by_lane["peer_mapping"].unlock_impact == 2
    assert by_lane["peer_mapping"].workflow_mode == "preview_first_reviewed_apply"
    assert by_lane["peer_valuation_inputs"].unlock_impact == 1
    assert by_lane["peer_valuation_inputs"].ready_count == 1
    assert "mapped_peer_inputs=1" in by_lane["peer_valuation_inputs"].notes
    assert [row.lane for row in peer_frontier] == ["peer_mapping", "peer_valuation_inputs"]


def test_coverage_frontier_ranks_batch_lanes_without_implying_data_available(tmp_path: Path):
    lanes = build_readiness_ops_lanes(_sample_root(tmp_path))
    frontier = build_coverage_frontier(lanes, top_n=10)
    rendered = render_coverage_frontier(frontier)

    assert frontier[0].workflow_mode == "dry_run_first"
    assert "operations queue, not a security recommendation" in rendered
    assert "does not imply data is available" in rendered
    assert "make price-refresh-loop DRY_RUN=1" in rendered
    assert "make optional-context-worklist TOP_N=25" in rendered


def test_data_coverage_expansion_plan_keeps_batches_proof_gated_and_read_only(tmp_path: Path):
    lanes = build_readiness_ops_lanes(_sample_root(tmp_path))
    steps = build_data_coverage_expansion_plan(lanes, top_n=10)
    rendered = render_data_coverage_expansion_plan(steps)
    by_lane = {step.lane: step for step in steps}

    assert steps[0].lane == "price_coverage"
    assert by_lane["price_coverage"].next_safe_command == (
        "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo"
    )
    assert "dry-run first" in by_lane["price_coverage"].batch_scope
    assert "save readiness snapshot" in by_lane["price_coverage"].review_gate
    assert by_lane["fundamentals_dcf"].next_safe_command == "make fundamentals-batch-proof TOP_N=10"
    assert by_lane["share_count_proof"].next_safe_command == "make share-count-proof-queue TOP_N=10"
    assert "shares_outstanding is the gating input" in by_lane["share_count_proof"].batch_scope
    assert "do not infer" not in by_lane["share_count_proof"].review_gate.lower()
    assert "price, market cap, peers, or placeholders" in by_lane["share_count_proof"].stop_condition
    assert "does not create valuation by itself" in by_lane["share_count_proof"].outcome_boundary
    assert by_lane["peer_mapping"].next_safe_command == "make peer-batch-proof TOP_N=10"
    assert "not ticker-by-ticker" in rendered
    assert "does not refresh, import, apply, or rewrite local data" in rendered
    assert "no placeholder revenue" in rendered
    assert "make share-count-proof-queue TOP_N=10" in rendered
    assert "shares_outstanding" in rendered
    assert "sector fallback remains context only" in rendered
    assert "trusted local rows" in rendered
    assert "investment advice" in rendered
    assert "buy/sell" not in rendered.lower()


def test_data_coverage_proof_queues_connect_next_batches_without_applying_data(tmp_path: Path):
    rows = build_data_coverage_proof_queues(_sample_root(tmp_path), top_n=3)
    rendered = render_data_coverage_proof_queues(rows)
    by_key = {row.queue_key: row for row in rows}

    assert set(by_key) == {
        "dcf_input_batches",
        "shares_outstanding",
        "trusted_fundamentals",
        "peer_mapping",
        "peer_valuation_inputs",
    }
    assert by_key["dcf_input_batches"].next_safe_command == "make dcf-input-proof-queue TOP_N=3"
    assert by_key["dcf_input_batches"].proof_packet_command.startswith("make dcf-input-proof-handoff FAMILY=")
    assert by_key["shares_outstanding"].queued_rows == 1
    assert by_key["shares_outstanding"].proof_packet_command == "DRY_RUN=1 make reviewed-batch LANE=share_count TOP_N=3"
    assert "price, market cap, peers, or placeholders" in by_key["shares_outstanding"].stop_rule
    assert by_key["trusted_fundamentals"].proof_packet_command == "DRY_RUN=1 make fundamentals-batch-proof TOP_N=3"
    assert "source-review fields" in by_key["trusted_fundamentals"].review_gate
    assert by_key["peer_mapping"].next_safe_command == "DRY_RUN=1 make peer-mapping-source-review TOP_N=3"
    assert "sector or theme similarity stays fallback context only" in by_key["peer_mapping"].review_gate
    assert "peer fundamentals: 1" in by_key["peer_valuation_inputs"].top_blockers
    assert by_key["peer_valuation_inputs"].proof_packet_command == "DRY_RUN=1 make peer-batch-proof TOP_N=3"

    assert "Data Coverage Proof Queues" in rendered
    assert "does not refresh data, apply imports, record proof, or rewrite local CSVs" in rendered
    assert "DCF Input Proof Batches" in rendered
    assert "Shares Outstanding Proof" in rendered
    assert "Trusted Fundamentals Proof Queue" in rendered
    assert "Peer Mapping Proof Queue" in rendered
    assert "Peer Valuation Input Proof Queue" in rendered
    assert "validate -> preview" in rendered.lower()
    assert "missing inputs remain blocked" in rendered
    assert "trade instructions" in rendered
    assert "recommendations" in rendered


def test_readiness_ops_rendering_keeps_research_only_and_churn_boundaries(tmp_path: Path):
    lanes = build_readiness_ops_lanes(_sample_root(tmp_path))
    frontier = build_coverage_frontier(lanes, top_n=10)
    rendered = render_readiness_ops_center(lanes)
    evidence = render_readiness_ops_evidence(lanes, frontier)

    assert "Data Readiness Operations Center" in rendered
    assert "does not refresh, import, apply, or rewrite local data" in rendered
    assert "ready=" in rendered
    assert "partial=" in rendered
    assert "blocked=" in rendered
    assert "excluded=" in rendered
    assert "broad CSV/JSON churn stays out of commits" in evidence
    assert "earnings and analyst estimates remain locked" in evidence
