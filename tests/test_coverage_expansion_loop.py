from pathlib import Path

from src.coverage_expansion_loop import (
    build_coverage_expansion_lane_board,
    build_coverage_expansion_loop,
    render_coverage_expansion_loop,
)
from src.readiness_ops import build_readiness_ops_lanes


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sample_root(tmp_path: Path, *, prior_snapshot: bool = False) -> Path:
    root = tmp_path
    _write(root / "data" / "prices.csv", "ticker,date,close\nAAA,2026-01-01,1\n")
    _write(root / "data" / "fundamentals.csv", "ticker,source\nAAA,manual\n")
    _write(root / "data" / "peers.csv", "ticker,peer_ticker,source\nAAA,BBB,manual\n")
    _write(root / "data" / "earnings.csv", "ticker,source\n")
    _write(root / "data" / "analyst_estimates.csv", "ticker,source\n")
    _write(
        root / "data" / "reports" / "ticker_readiness_report.csv",
        "\n".join(
            [
                "ticker,asset_type,price_ready,fundamentals_ready,dcf_ready,peer_ready,earnings_ready,analyst_estimates_ready,overall_readiness_state,blocked_features,excluded_features,missing_data",
                "AAA,company,false,false,false,false,false,false,blocked,price fundamentals dcf peer earnings analyst_estimates,,dcf: revenue; peers: needs at least 2 source-backed peer mappings",
                "BBB,company,true,false,false,false,false,false,blocked,fundamentals dcf peer earnings analyst_estimates,,dcf: revenue",
            ]
        )
        + "\n",
    )
    _write(
        root / "data" / "reports" / "feature_readiness_summary.csv",
        "\n".join(
            [
                "feature,ready_count,partial_count,blocked_count,excluded_count,total_count,top_blocker,next_action,unlock_command",
                "price,1,0,1,0,2,needs price rows,make price-worklist TOP_N=25,make price-worklist TOP_N=25",
                "fundamentals,0,0,2,0,2,missing fundamentals,make sec-stage-queue TOP_N=25,make sec-stage-queue TOP_N=25",
            ]
        )
        + "\n",
    )
    _write(
        root / "data" / "reports" / "peer_unlock_worklist.csv",
        "priority,ticker,workflow_group,missing_peer_reason\n1,AAA,peer_valuation_unlock,peer inputs\n",
    )
    _write(
        root / "data" / "reports" / "peer_readiness_report.csv",
        "ticker,peer_count,mapping_status,peer_blocker_type,peer_price_ready,peer_momentum_ready,peer_fundamentals_ready,peer_valuation_ready,peer_valuation_comparison_ready\nAAA,0,missing_mapping,missing_peer_mapping,false,false,false,false,false\n",
    )
    if prior_snapshot:
        _write(
            root / "data" / "reports" / "ticker_readiness_report.previous.csv",
            "ticker,overall_readiness_state\nAAA,blocked\n",
        )
    return root


def test_coverage_expansion_loop_blocks_until_preflight_snapshot_exists(tmp_path: Path):
    loop = build_coverage_expansion_loop(_sample_root(tmp_path), lane="auto", top_n=10)
    rendered = render_coverage_expansion_loop(loop)

    assert loop.status == "blocked_by_preflight"
    assert loop.selected_lane == "price_coverage"
    assert loop.lane_board[0].selected is True
    assert "prior readiness snapshot is missing" in rendered
    assert "make readiness-snapshot" in rendered
    assert "Lane readiness board" in rendered
    assert "Price Coverage | selected=yes" in rendered
    assert "dry-run and reviewed scope before any capped provider refresh" in rendered
    assert "does not refresh data, stage imports, apply rows" in rendered
    assert "investment advice" in rendered
    assert "buy/sell" not in rendered.lower()


def test_coverage_expansion_loop_prints_ready_copy_only_sequence(tmp_path: Path):
    loop = build_coverage_expansion_loop(
        _sample_root(tmp_path, prior_snapshot=True),
        lane="fundamentals",
        top_n=5,
    )
    rendered = render_coverage_expansion_loop(loop)

    assert loop.status == "ready_for_reviewed_dry_run"
    assert loop.selected_lane == "fundamentals_dcf"
    assert loop.reviewed_batch_lane == "fundamentals"
    assert any(row.selected and row.lane == "fundamentals_dcf" for row in loop.lane_board)
    assert "make reviewed-batch LANE=fundamentals TOP_N=5" in rendered
    assert "make sec-stage-queue TOP_N=5" in rendered
    assert "make imports-validate && make imports-preview" in rendered
    assert "source proof, validate, preview, rejected-row review, explicit apply decision, rebuilt readiness" in rendered
    assert "DRY_RUN=1 make reviewed-batch-proof-record" in rendered
    assert "generated-artifact" in rendered


def test_coverage_expansion_loop_reports_unknown_lane_without_fake_plan(tmp_path: Path):
    loop = build_coverage_expansion_loop(_sample_root(tmp_path), lane="not_a_lane", top_n=10)
    rendered = render_coverage_expansion_loop(loop)

    assert loop.status == "blocked_missing_lane"
    assert loop.planner_step is None
    assert loop.lane_board
    assert not any(row.selected for row in loop.lane_board)
    assert "No matching planner lane" in rendered
    assert "Run make readiness and make data-coverage-planner TOP_N=10" in rendered


def test_coverage_expansion_lane_board_keeps_locked_and_excluded_boundaries_visible(tmp_path: Path):
    lanes = build_readiness_ops_lanes(_sample_root(tmp_path))
    board = build_coverage_expansion_lane_board(lanes, selected_lane="earnings_locked", top_n=10)
    rendered = "\n".join(
        f"{row.label} {row.selected} {row.workflow_mode} {row.proceed_boundary} {row.next_safe_command}"
        for row in board
    )

    assert any(row.selected and row.lane == "earnings_locked" for row in board)
    assert "locked until trusted local rows exist" in rendered
    assert "excluded/not applicable stays visible" in rendered
    assert "make optional-context-worklist TOP_N=25" in rendered
    assert "buy" not in rendered.lower()
    assert "sell" not in rendered.lower()
    assert "broker" not in rendered.lower()
