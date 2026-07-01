import json
from pathlib import Path

from src import readiness_ops as readiness_ops_module
from src.readiness_ops import (
    build_fundamentals_peer_metrics_queue,
    build_fundamentals_peer_metrics_queue_from_lanes,
    build_data_coverage_proof_queues,
    build_data_coverage_expansion_plan,
    build_peer_readiness_summary,
    build_reviewed_batch_ledger_summaries,
    build_coverage_frontier,
    build_readiness_ops_lanes,
    render_data_coverage_proof_queues,
    render_fundamentals_peer_metrics_queue,
    render_data_coverage_expansion_plan,
    render_coverage_frontier,
    render_readiness_ops_center,
    render_readiness_ops_evidence,
)
from src.dcf_input_proof_queue import DcfInputProofRow


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_session_source_preflight(
    root: Path,
    *,
    sec: str = "unavailable",
    yfinance_stage: str = "unavailable",
    fmp: str = "unavailable",
    alpha_vantage: str = "unavailable",
    finnhub: str = "unavailable",
    local_fundamentals: str = "available",
    fmp_reason: str = "provider_key_missing",
    alpha_reason: str = "provider_key_missing",
    finnhub_reason: str = "provider_key_missing",
) -> None:
    payload = {
        "generated_at": "2026-06-24T00:00:00+00:00",
        "project_root": str(root),
        "data_dir": str(root / "data"),
        "session_flags": [],
        "do_not_retry_paths": [],
        "available_lanes": [],
        "preferred_lane_order": [],
        "sources": {
            "sec": {
                "status": sec,
                "reason_code": "ok" if sec == "available" else "network_error",
                "detail": "SEC session fixture",
                "next_action": "",
            },
            "yfinance_stage": {
                "status": yfinance_stage,
                "reason_code": "probe_succeeded" if yfinance_stage == "available" else "probe_failed",
                "detail": "Yahoo staging fixture",
                "next_action": "",
            },
            "fmp": {
                "status": fmp,
                "reason_code": "configured" if fmp == "available" else fmp_reason,
                "detail": "FMP_API_KEY fixture",
                "next_action": "",
            },
            "alpha_vantage": {
                "status": alpha_vantage,
                "reason_code": "configured" if alpha_vantage == "available" else alpha_reason,
                "detail": "ALPHA_VANTAGE_API_KEY fixture",
                "next_action": "",
            },
            "finnhub": {
                "status": finnhub,
                "reason_code": "configured" if finnhub == "available" else finnhub_reason,
                "detail": "FINNHUB_API_KEY fixture",
                "next_action": "",
            },
            "local_fundamentals": {
                "status": local_fundamentals,
                "reason_code": "ok" if local_fundamentals == "available" else "missing_file",
                "detail": "local fundamentals fixture",
                "next_action": "",
                "row_count": 2 if local_fundamentals == "available" else 0,
                "ticker_count": 2 if local_fundamentals == "available" else 0,
                "share_count_fixable_ticker_count": 1,
                "fundamentals_fixable_ticker_count": 1,
            },
        },
    }
    _write(root / "outputs" / "session_source_preflight.json", json.dumps(payload))


def _write_reviewed_batch_proofs(root: Path) -> None:
    _write(
        root / "data" / "reviewed_batch_proofs.csv",
        "\n".join(
            [
                "batch_id,review_date,reviewer,lane,scope,tickers,command_run,validation_result,preview_result,apply_result,pre_run_readiness_snapshot,post_run_readiness_snapshot,changed_readiness_counts,changed_tickers,source_files,generated_artifacts_reviewed,final_outcome,notes",
                "RB-OPTIONAL-TOP2,2026-06-25,local reviewer,optional_context,Optional rows 1-2,\"AAA,BBB\",make optional-context-worklist TOP_N=2,imports-validate passed,imports-preview valid,not_run,3 rows,3 rows,none,none,data/imports/earnings.csv,headers reviewed,still_blocked,optional rows locked",
                "RB-OPTIONAL-TOP3,2026-06-25,local reviewer,optional_context,Optional rows 3-3,QQQ,make optional-context-worklist TOP_N=3,imports-validate passed,imports-preview valid,not_run,3 rows,3 rows,none,none,data/imports/analyst_estimates.csv,headers reviewed,still_blocked,optional rows locked",
                "RB-PEER-CANDIDATES,2026-06-25,local reviewer,peers,Peer candidate review,\"AAA,BBB\",make peer-mapping-source-review TOP_N=2,imports-validate passed,imports-preview valid,not_applied,3 rows,3 rows,none,none,data/imports/peers.csv,source-review output reviewed,candidate_context_only,candidate context only",
                "RB-PEER-VALUATION-INPUTS,2026-06-25,local reviewer,peer_valuation_inputs,Peer valuation input blockers,AAA,make peer-mapping-queue TOP_N=1,imports-validate passed,imports-preview valid,not_applied,3 rows,3 rows,none,none,data/reports/peer_readiness_report.csv,peer blockers reviewed,still_blocked,peer valuation inputs still blocked",
            ]
        )
        + "\n",
    )


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
    assert "configured FMP/Alpha Vantage/Finnhub fallbacks" in by_lane["price_coverage"].source_readiness
    assert by_lane["fundamentals_dcf"].workflow_mode == "preview_first_reviewed_apply"
    assert by_lane["fundamentals_dcf"].ready_count == 1
    assert by_lane["fundamentals_dcf"].blocked_count == 1
    assert by_lane["fundamentals_dcf"].excluded_count == 1
    assert by_lane["share_count_proof"].workflow_mode == "preview_first_reviewed_apply"
    assert by_lane["share_count_proof"].blocked_count == 1
    assert by_lane["share_count_proof"].partial_count == 1
    assert "shares_outstanding proof" in by_lane["share_count_proof"].source_readiness
    assert by_lane["peer_mapping"].blocked_count == 2
    assert by_lane["peer_mapping"].excluded_count == 1
    assert "Peer sub-states:" in by_lane["peer_mapping"].notes
    assert "peer_valuation_comparison=0" in by_lane["peer_valuation_inputs"].notes
    assert by_lane["earnings_locked"].workflow_mode == "optional_source_ladder"
    assert by_lane["analyst_estimates_locked"].workflow_mode == "optional_source_ladder"
    assert by_lane["earnings_locked"].next_safe_command == "make optional-context-source-ladder-queue TOP_N=10"
    assert "make imports-apply" not in by_lane["earnings_locked"].proof_command
    assert "make imports-apply" not in by_lane["analyst_estimates_locked"].proof_command
    assert "apply only after validation passes" in by_lane["earnings_locked"].generated_churn_policy
    assert "apply only after validation passes" in by_lane["analyst_estimates_locked"].generated_churn_policy
    assert by_lane["excluded_not_applicable"].readiness_state == "excluded"
    assert "trusted local or reviewed provider-assisted rows" in by_lane["earnings_locked"].notes


def test_readiness_ops_surfaces_reviewed_batch_ledger_progress_without_unlocking_lanes(tmp_path: Path):
    root = _sample_root(tmp_path)
    _write_reviewed_batch_proofs(root)

    summaries = build_reviewed_batch_ledger_summaries(root)
    lanes = build_readiness_ops_lanes(root)
    by_lane = {lane.lane: lane for lane in lanes}
    rendered = render_readiness_ops_center(lanes)
    frontier = build_coverage_frontier(lanes, top_n=10)
    frontier_rendered = render_coverage_frontier(frontier)

    assert summaries["optional_context"].record_count == 2
    assert summaries["optional_context"].unique_ticker_count == 3
    assert summaries["optional_context"].outcome_counts == {"still_blocked": 2}
    assert summaries["optional_context"].latest_batch_id == "RB-OPTIONAL-TOP3"
    assert summaries["peers"].outcome_counts == {"candidate_context_only": 1}
    assert summaries["peer_valuation_inputs"].outcome_counts == {"still_blocked": 1}
    assert by_lane["earnings_locked"].readiness_state == "blocked"
    assert by_lane["analyst_estimates_locked"].readiness_state == "blocked"
    assert "optional context has 2 reviewed record(s) across 3 unique ticker(s)" in by_lane["earnings_locked"].notes
    assert "outcomes still_blocked=2" in by_lane["analyst_estimates_locked"].notes
    assert "peer mapping has 1 reviewed record(s) across 2 unique ticker(s)" in by_lane["peer_mapping"].notes
    assert "peer valuation inputs has 1 reviewed record(s) across 1 unique ticker(s)" in by_lane["peer_valuation_inputs"].notes
    assert "candidate_context_only=1" in rendered
    assert "reviewed proof ledger covers current optional context scope" in by_lane["earnings_locked"].reviewed_proof_status
    assert "reviewed_proof_status: reviewed proof ledger covers current optional context scope" in frontier_rendered
    assert frontier[-1].lane in {"earnings_locked", "analyst_estimates_locked"}


def test_readiness_ops_uses_reviewed_price_ledger_to_stop_repeating_exhausted_refresh(tmp_path: Path):
    root = _sample_root(tmp_path)
    _write(
        root / "data" / "reviewed_batch_proofs.csv",
        "\n".join(
            [
                "batch_id,review_date,reviewer,lane,scope,tickers,command_run,validation_result,preview_result,apply_result,pre_run_readiness_snapshot,post_run_readiness_snapshot,changed_readiness_counts,changed_tickers,source_files,generated_artifacts_reviewed,final_outcome,notes",
                "RB-PRICE-CGCT,2026-06-30,codex,prices,final price partial,BBB,make price-refresh TICKERS=BBB PROVIDER=auto REFRESH=1,provider tried Stooq and Yahoo,Yahoo returned one row,not enough rows,price ready=2 partial=1,price ready=2 partial=1,none,BBB,data/prices.csv,reviewed,still_blocked,do not repeat normal refresh loops",
            ]
        )
        + "\n",
    )

    lanes = build_readiness_ops_lanes(root)
    by_lane = {lane.lane: lane for lane in lanes}
    frontier_rendered = render_coverage_frontier(build_coverage_frontier(lanes, top_n=10))

    assert by_lane["price_coverage"].reviewed_proof_status.startswith(
        "reviewed proof ledger covers current price coverage scope"
    )
    assert by_lane["price_coverage"].next_safe_command == "make price-history-proof-queue TOP_N=25"
    assert "reviewed proof already recorded" in frontier_rendered
    assert "do not repeat this proof loop" in frontier_rendered


def test_readiness_ops_routes_exhausted_dcf_ladders_to_provider_or_manual_activation(tmp_path: Path):
    root = _sample_root(tmp_path)
    reviewed_rows = [
        DcfInputProofRow(
            priority=1,
            ticker="BBB",
            scope="master universe",
            missing_input_family="fcf_margin",
            missing_dcf_fields="fcf_margin",
            ready_dcf_inputs="revenue, free_cash_flow, shares_outstanding",
            dcf_input_status="single-input blocker: fcf_margin",
            source_mode="SEC-stageable or trusted-local",
            next_safe_command="make focus-fundamentals TICKER=BBB",
            proof_packet_command="DRY_RUN=1 make reviewed-batch LANE=fundamentals TICKERS=BBB",
            validation_sequence="make imports-validate IMPORT_TICKERS=BBB && make imports-preview IMPORT_TICKERS=BBB",
            proof_after_update="make dcf-readiness && make readiness",
            stop_rule="Stop if trusted source rows do not prove required fields.",
            source_note=(
                "Reviewed proof ledger already records this ticker as non-actionable for the current source path; "
                "prefer unreviewed executable blockers unless new source-backed rows or changed blockers appear."
            ),
        )
    ]

    lanes = build_readiness_ops_lanes(root, dcf_input_rows=reviewed_rows)
    by_lane = {lane.lane: lane for lane in lanes}
    frontier_rendered = render_coverage_frontier(build_coverage_frontier(lanes, top_n=10))

    assert by_lane["fundamentals_dcf"].next_safe_command == "make session-source-preflight"
    assert by_lane["share_count_proof"].next_safe_command == "make session-source-preflight"
    assert "No unreviewed executable DCF/share-count blockers are available" in by_lane["fundamentals_dcf"].source_readiness
    assert "new provider data, keyed sources, or reviewed manual source rows" in frontier_rendered


def test_readiness_ops_routes_fundamentals_to_source_ladder_when_fallback_provider_is_available(tmp_path: Path):
    root = _sample_root(tmp_path)
    _write_session_source_preflight(root, fmp="available")

    lanes = build_readiness_ops_lanes(root)
    by_lane = {lane.lane: lane for lane in lanes}
    rendered = render_readiness_ops_center(lanes)

    assert by_lane["fundamentals_dcf"].next_safe_command == "make fundamentals-source-ladder-queue TOP_N=25"
    assert by_lane["share_count_proof"].next_safe_command == "make fundamentals-source-ladder-queue TOP_N=10"
    assert "FMP configured" in by_lane["fundamentals_dcf"].source_readiness
    assert "source ladder" in rendered


def test_readiness_ops_classifies_missing_fallback_keys_without_generic_blocker_copy(tmp_path: Path):
    root = _sample_root(tmp_path)
    _write_session_source_preflight(root)

    lanes = build_readiness_ops_lanes(root)
    by_lane = {lane.lane: lane for lane in lanes}

    assert by_lane["fundamentals_dcf"].next_safe_command == "make fundamentals-source-ladder-queue TOP_N=25"
    assert "FMP_API_KEY missing" in by_lane["fundamentals_dcf"].source_readiness
    assert "ALPHA_VANTAGE_API_KEY missing" in by_lane["share_count_proof"].source_readiness
    assert "FINNHUB_API_KEY missing" in by_lane["share_count_proof"].source_readiness
    assert "local reviewed rows available" in by_lane["share_count_proof"].source_readiness


def test_readiness_ops_routes_source_lanes_to_activation_when_no_source_path_is_executable(tmp_path: Path):
    root = _sample_root(tmp_path)
    payload = {
        "source_activation": {
            "status": "required",
            "reason_code": "no_executable_source_path",
            "detail": "do not run broad coverage batches",
            "next_action": "Configure provider keys.",
        },
        "sources": {
            "sec": {"status": "unavailable", "reason_code": "network_error", "detail": "dns failed"},
            "yfinance_stage": {"status": "unavailable", "reason_code": "probe_failed", "detail": "dns failed"},
            "fmp": {"status": "unavailable", "reason_code": "provider_key_missing", "detail": "FMP_API_KEY missing"},
            "alpha_vantage": {
                "status": "unavailable",
                "reason_code": "provider_key_missing",
                "detail": "ALPHA_VANTAGE_API_KEY missing",
            },
            "finnhub": {
                "status": "unavailable",
                "reason_code": "provider_key_missing",
                "detail": "FINNHUB_API_KEY missing",
            },
            "local_fundamentals": {
                "status": "available",
                "reason_code": "ok",
                "detail": "local fundamentals fixture",
                "row_count": 2,
                "ticker_count": 2,
                "share_count_fixable_ticker_count": 0,
                "fundamentals_fixable_ticker_count": 0,
            },
        },
    }
    _write(root / "outputs" / "session_source_preflight.json", json.dumps(payload))

    lanes = build_readiness_ops_lanes(root)
    by_lane = {lane.lane: lane for lane in lanes}
    rendered = render_readiness_ops_center(lanes)
    frontier = build_coverage_frontier(lanes, top_n=10)
    plan = build_data_coverage_expansion_plan(lanes, top_n=10)

    for lane_name in ("price_coverage", "fundamentals_dcf", "share_count_proof", "earnings_locked", "analyst_estimates_locked"):
        assert by_lane[lane_name].workflow_mode == "source_activation_required"
        assert by_lane[lane_name].next_safe_command == "make coverage-expansion-loop TOP_N=10"
        assert "Source activation required" in by_lane[lane_name].source_readiness

    assert "make price-refresh-loop" not in rendered
    assert "make fundamentals-source-ladder-queue" not in rendered
    assert "make optional-context-source-ladder-queue" not in rendered
    assert all(
        row.next_safe_command == "make coverage-expansion-loop TOP_N=10"
        for row in frontier
        if row.workflow_mode == "source_activation_required"
    )
    assert all(
        step.next_safe_command == "make coverage-expansion-loop TOP_N=10"
        for step in plan
        if step.workflow_mode == "source_activation_required"
    )


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
    assert by_lane["earnings_locked"].source_mode == "optional source ladder plus trusted-local fallback"
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
    assert "make optional-context-source-ladder-queue TOP_N=10" in rendered


def test_data_coverage_expansion_plan_keeps_batches_proof_gated_and_read_only(tmp_path: Path):
    lanes = build_readiness_ops_lanes(_sample_root(tmp_path))
    steps = build_data_coverage_expansion_plan(lanes, top_n=10)
    rendered = render_data_coverage_expansion_plan(steps)
    by_lane = {step.lane: step for step in steps}

    assert steps[0].lane == "price_coverage"
    assert by_lane["price_coverage"].next_safe_command == (
        "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto"
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
    assert "trusted-local or provider-assisted rows" in rendered
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
