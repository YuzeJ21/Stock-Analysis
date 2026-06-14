from pathlib import Path

from src.readiness_ops import (
    build_data_coverage_expansion_plan,
    build_peer_readiness_summary,
    build_coverage_frontier,
    build_readiness_ops_lanes,
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
    assert "peer trend can be ready before peer valuation comparison is ready" in summary.source_context


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
