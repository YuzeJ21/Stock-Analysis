import csv
import os
from pathlib import Path

from src.reviewed_batch import (
    build_reviewed_batch_packet,
    main,
    readiness_freshness_status,
    render_packet_markdown,
    render_packet_preview,
    reviewed_batch_next_safe_action,
    reviewed_batch_packet_status,
    write_reviewed_batch_packet,
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
                "ticker,asset_type,default_purpose,market_cap_bucket",
                "AAA,company,Momentum Leader,Large",
                "BBB,company,Core Compounder,Mid",
                "CCC,company,Core Compounder,Mid",
                "QQQ,etf,ETF / Defensive / Hedge,ETF",
            ]
        )
        + "\n",
    )
    _write(
        root / "data" / "reports" / "ticker_readiness_report.csv",
        "\n".join(
            [
                "ticker,asset_type,price_ready,fundamentals_ready,dcf_ready,peer_ready,earnings_ready,analyst_estimates_ready,overall_readiness_state,blocked_features,excluded_features,missing_data",
                "AAA,company,false,false,false,false,false,false,blocked,price fundamentals dcf peer earnings analyst_estimates,,dcf: revenue; peers: needs at least 2 source-backed peer mappings",
                "BBB,company,false,false,false,false,false,false,blocked,price fundamentals dcf peer earnings analyst_estimates,,dcf: revenue; peers: needs at least 2 source-backed peer mappings",
                "CCC,company,false,true,true,false,false,false,partial,peer earnings analyst_estimates,,peers: needs at least 2 source-backed peer mappings",
                "QQQ,etf,true,false,false,false,false,false,partial,earnings analyst_estimates,dcf,earnings: trusted local CSV input",
            ]
        )
        + "\n",
    )
    _write(
        root / "data" / "reports" / "feature_readiness_summary.csv",
        "\n".join(
            [
                "feature,ready_count,partial_count,blocked_count,excluded_count,total_count,top_blocker,next_action,unlock_command",
                "price,1,0,3,0,4,needs price rows,make price-worklist TOP_N=25,make price-worklist TOP_N=25",
                "fundamentals,1,0,3,0,4,missing fundamentals,make sec-stage-queue TOP_N=25,make sec-stage-queue TOP_N=25",
            ]
        )
        + "\n",
    )
    _write(
        root / "data" / "reports" / "price_coverage_report.csv",
        "ticker,price_ready,missing_price_reason\nAAA,false,missing rows\nBBB,false,missing rows\nCCC,false,missing rows\n",
    )
    _write(
        root / "data" / "reports" / "fundamentals_coverage_report.csv",
        "ticker,fundamentals_ready,missing_fundamentals_fields\nAAA,false,revenue\nBBB,false,free_cash_flow\n",
    )
    _write(
        root / "data" / "reports" / "peer_unlock_worklist.csv",
        "priority,ticker,workflow_group,missing_peer_reason\n1,AAA,peer_valuation_unlock,peer inputs\n2,BBB,peer_mapping,peer mappings\n",
    )
    _write(
        root / "data" / "reports" / "earnings_readiness_report.csv",
        "ticker,has_trusted_earnings,row_count\nAAA,false,0\nBBB,false,0\n",
    )
    _write(
        root / "data" / "reports" / "analyst_estimates_readiness_report.csv",
        "ticker,has_trusted_analyst_estimates,row_count\nAAA,false,0\nBBB,false,0\n",
    )
    _write(root / "data" / "prices.csv", "ticker,date,close\nAAA,2026-01-01,1\nBBB,2026-01-01,2\n")
    _write(
        root / "data" / "fundamentals.csv",
        "\n".join(
            [
                "ticker,source,revenue,free_cash_flow,fcf_margin,shares_outstanding",
                "AAA,manual,100,20,0.20,",
                "BBB,manual,80,10,0.125,",
            ]
        )
        + "\n",
    )
    _write(root / "data" / "peers.csv", "ticker,peer_ticker,source\nAAA,BBB,manual\n")
    _write(root / "data" / "earnings.csv", "ticker,source\n")
    _write(root / "data" / "analyst_estimates.csv", "ticker,source\n")
    return root


def _mark_readiness_current(root: Path) -> None:
    for path in [
        root / "data" / "reports" / "ticker_readiness_report.csv",
        root / "data" / "reports" / "feature_readiness_summary.csv",
    ]:
        os.utime(path, (path.stat().st_atime + 2000, path.stat().st_mtime + 2000))


def test_reviewed_batch_reports_missing_readiness_artifacts(tmp_path: Path):
    status = readiness_freshness_status(tmp_path)
    packet = build_reviewed_batch_packet(tmp_path, lane="prices", top_n=2)
    rendered = render_packet_markdown(packet)

    assert status.status == "missing"
    assert "Missing readiness artifact" in rendered
    assert "Run make readiness" in rendered
    assert "Do not proceed if" in rendered


def test_reviewed_batch_reports_stale_readiness_artifacts(tmp_path: Path):
    root = _sample_root(tmp_path)
    source = root / "data" / "prices.csv"
    os.utime(source, (source.stat().st_atime + 1000, source.stat().st_mtime + 1000))

    packet = build_reviewed_batch_packet(root, lane="prices", top_n=2)
    rendered = render_packet_markdown(packet)

    assert packet.freshness.status == "stale"
    assert reviewed_batch_packet_status(packet) == "blocked_by_freshness"
    assert reviewed_batch_next_safe_action(packet) == "make readiness"
    assert "Readiness artifacts may be stale" in rendered
    assert "make readiness before relying on final counts" in rendered
    assert "Packet status: `blocked_by_freshness`" in rendered
    assert "Next safe action: `make readiness`" in rendered
    assert "## Blocked Preflight" in rendered
    assert "Treat this packet as a stale-readiness scaffold, not execution approval." in rendered


def test_reviewed_batch_lane_selection_and_top_n_cap(tmp_path: Path):
    root = _sample_root(tmp_path)
    _mark_readiness_current(root)

    packet = build_reviewed_batch_packet(root, lane="fundamentals", top_n=1)
    rendered = render_packet_markdown(packet)

    assert packet.selected_scope == "fundamentals_dcf"
    assert reviewed_batch_packet_status(packet) == "ready_for_review"
    assert reviewed_batch_next_safe_action(packet) == "make sec-stage-queue TOP_N=1"
    assert "Packet status: `ready_for_review`" in rendered
    assert len(packet.actions) == 1
    assert packet.actions[0].proposed_ticker == "AAA"
    assert "SEC_USER_AGENT is configured" in packet.actions[0].capped_execution_command
    assert packet.actions[0].validation_command == "make imports-validate"
    assert packet.actions[0].preview_command == "make imports-preview"
    assert "make imports-apply only after reviewed trusted fundamentals rows pass preview" == packet.actions[0].apply_command
    assert "data/rejected/fundamentals_import_rejected.csv" in packet.actions[0].expected_artifacts
    assert "SEC_USER_AGENT is not configured" in packet.actions[0].do_not_proceed_if
    assert "make fundamentals-batch-proof TOP_N=<n>" in rendered
    assert "make sec-stage TICKERS=<scope> only when SEC_USER_AGENT is configured" in rendered
    assert "rejected-row reports must be clear or explained" in rendered


def test_reviewed_batch_share_count_lane_uses_first_class_proof_queue(tmp_path: Path):
    root = _sample_root(tmp_path)
    _mark_readiness_current(root)

    packet = build_reviewed_batch_packet(root, lane="share_count", top_n=1)
    rendered = render_packet_markdown(packet)

    assert packet.selected_scope == "share_count_proof"
    assert reviewed_batch_packet_status(packet) == "ready_for_review"
    assert reviewed_batch_next_safe_action(packet) == "make share-count-proof-queue TOP_N=1"
    assert len(packet.actions) == 1
    action = packet.actions[0]
    assert action.lane == "share_count_proof"
    assert action.lane_label == "Share Count Proof"
    assert action.proposed_ticker == "AAA"
    assert action.dry_run_command == "make share-count-proof-queue TOP_N=1"
    assert "shares_outstanding rows pass preview" in action.apply_command
    assert "make reviewed-batch-compare LANE=share_count" in action.readiness_comparison_command
    assert "SEC/manual source proof does not explicitly verify shares_outstanding" in action.do_not_proceed_if
    assert "do not infer it from market cap, price, peers, or placeholders" in rendered
    assert "make dcf-readiness" in rendered
    assert "does not provide direct buy/sell instructions" in rendered


def test_reviewed_batch_supports_ticker_scope_and_optional_context(tmp_path: Path):
    packet = build_reviewed_batch_packet(_sample_root(tmp_path), lane="optional_context", tickers="BBB,CCC", top_n=5)
    rendered = render_packet_markdown(packet)

    assert packet.tickers == ("BBB", "CCC")
    assert {action.lane for action in packet.actions} == {"earnings_locked", "analyst_estimates_locked"}
    assert "trusted local optional rows" in rendered
    assert "make optional-context-worklist TOP_N=5" in rendered


def test_reviewed_batch_packet_includes_v2_proof_ledger_fields_and_peer_sub_lane_steps(tmp_path: Path):
    packet = build_reviewed_batch_packet(_sample_root(tmp_path), lane="peers", top_n=2)
    rendered = render_packet_markdown(packet)
    lowered = rendered.lower()
    actions_by_lane = {action.lane: action for action in packet.actions}

    assert "changed_readiness_counts" in rendered
    assert "changed_tickers" in rendered
    assert "generated_artifacts_reviewed" in rendered
    assert "final_outcome" in rendered
    assert "supported, still_blocked, skipped, excluded" in rendered
    assert "data/reviewed_batch_proofs.csv" in rendered
    assert "make reviewed-batch-compare LANE=peers" in rendered
    assert "make reviewed-batch-proof-record" in rendered
    assert "CHANGED_READINESS_COUNTS" in rendered
    assert "CHANGED_TICKERS" in rendered
    assert "record peer_mapping_ready, peer_price_ready, peer_momentum_ready" in lowered
    assert "peer_valuation_comparison_ready" in rendered
    assert "sector or industry fallback as context only" in lowered
    assert "make peer-batch-proof TOP_N=<n>" in rendered
    assert set(actions_by_lane) == {"peer_mapping", "peer_valuation_inputs"}
    assert "source-backed peer mapping rows" in actions_by_lane["peer_mapping"].apply_command
    assert "reviewed mapped-peer fundamentals, price, market-cap, or valuation-input rows" in actions_by_lane["peer_valuation_inputs"].apply_command
    assert "data/rejected/peers_import_rejected.csv" in actions_by_lane["peer_mapping"].expected_artifacts
    assert "data/rejected/fundamentals_import_rejected.csv" in actions_by_lane["peer_valuation_inputs"].expected_artifacts
    assert "peer relationship proof is unavailable" in actions_by_lane["peer_mapping"].do_not_proceed_if
    assert "mapped peers lack trusted fundamentals" in actions_by_lane["peer_valuation_inputs"].do_not_proceed_if
    assert "Follow the printed mapped-peer dependency" in rendered
    assert "make metric-readiness" in rendered
    assert "validate -> preview -> apply" in rendered


def test_reviewed_batch_metrics_lane_is_read_only_and_source_gated(tmp_path: Path):
    packet = build_reviewed_batch_packet(_sample_root(tmp_path), lane="metrics", top_n=2)
    rendered = render_packet_markdown(packet)
    lowered = rendered.lower()

    assert packet.selected_scope == "metric_readiness_review"
    assert len(packet.actions) == 2
    assert packet.actions[0].lane_label == "Metric Readiness Review"
    assert packet.actions[0].workflow_mode == "read_only_review"
    assert packet.actions[0].dry_run_command == "make metric-readiness-board TOP_N=2 TICKERS=AAA,BBB"
    assert packet.actions[0].apply_command.startswith("not_applicable")
    assert "make metric-readiness-board TOP_N=2 TICKERS=AAA,BBB BENCHMARKS=SPY,QQQ" in rendered
    assert "map each blocked metric to its source lane" in lowered
    assert "do not apply rows from the metrics packet" in lowered
    assert "prices, fundamentals, market cap, or peer-input proof" in lowered
    assert "not investment advice" in lowered
    assert "does not provide direct buy/sell instructions" in lowered
    assert "does not connect to brokers" in lowered


def test_reviewed_batch_writes_markdown_and_csv_without_advice(tmp_path: Path):
    root = _sample_root(tmp_path)
    packet = build_reviewed_batch_packet(root, lane="peers", top_n=2)
    md_output = tmp_path / "outputs" / "reviewed_batch_packet.md"
    csv_output = tmp_path / "outputs" / "reviewed_batch_packet.csv"

    write_reviewed_batch_packet(packet, md_output=md_output, csv_output=csv_output)
    rendered = md_output.read_text(encoding="utf-8")
    rows = list(csv.DictReader(csv_output.read_text(encoding="utf-8").splitlines()))

    assert "# Reviewed Batch Run Packet" in rendered
    assert "not investment advice" in rendered
    assert "does not provide direct buy/sell instructions" in rendered
    assert "Do not fabricate prices, fundamentals, peers, earnings, analyst estimates" in rendered
    assert "validate -> preview -> apply" in rendered
    assert rows
    assert rows[0]["batch_id"] == packet.batch_id
    assert rows[0]["dry_run_command"] == "make peer-mapping-queue TOP_N=2"
    assert rows[0]["readiness_comparison_command"].startswith("make reviewed-batch-compare LANE=peers")
    assert rows[0]["proof_record_command"].startswith("make reviewed-batch-proof-record")
    assert rows[0]["pre_run_readiness_snapshot"].startswith("record saved counts")
    assert rows[0]["changed_readiness_counts"] == "<before -> after counts, or none>"
    assert rows[0]["generated_artifacts_reviewed"] == "<kept evidence or excluded local churn>"
    assert rows[0]["final_outcome"] == "supported|still_blocked|skipped|excluded"


def test_reviewed_batch_preview_shows_next_action_without_writing_outputs(tmp_path: Path):
    root = _sample_root(tmp_path)
    _mark_readiness_current(root)
    packet = build_reviewed_batch_packet(root, lane="peers", top_n=2)

    rendered = render_packet_preview(packet)
    lowered = rendered.lower()

    assert "status: preview" in rendered
    assert "no Markdown or CSV artifacts were written" in rendered
    assert "top_action:" in rendered
    assert "dry_run_command: make peer-mapping-queue TOP_N=2" in rendered
    assert "validation_command: make imports-validate" in rendered
    assert "preview_command: make imports-preview" in rendered
    assert "proof_record_command: make reviewed-batch-proof-record" in rendered
    assert "do_not_proceed_if:" in rendered
    assert "not investment advice" not in lowered
    assert "buy" not in lowered
    assert "sell" not in lowered


def test_reviewed_batch_cli_prints_packet_status_and_next_safe_action(tmp_path: Path, capsys):
    root = _sample_root(tmp_path)
    source = root / "data" / "prices.csv"
    os.utime(source, (source.stat().st_atime + 1000, source.stat().st_mtime + 1000))

    rc = main(
        [
            "--root",
            str(root),
            "--lane",
            "fundamentals",
            "--top-n",
            "1",
            "--md-output",
            str(tmp_path / "outputs" / "packet.md"),
            "--csv-output",
            str(tmp_path / "outputs" / "packet.csv"),
        ]
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert "Packet status: blocked_by_freshness" in output
    assert "Next safe action: make readiness" in output


def test_reviewed_batch_cli_dry_run_does_not_write_packet_artifacts(tmp_path: Path, capsys):
    root = _sample_root(tmp_path)
    _mark_readiness_current(root)
    md_output = tmp_path / "outputs" / "packet.md"
    csv_output = tmp_path / "outputs" / "packet.csv"

    rc = main(
        [
            "--root",
            str(root),
            "--lane",
            "peers",
            "--top-n",
            "2",
            "--md-output",
            str(md_output),
            "--csv-output",
            str(csv_output),
            "--dry-run",
        ]
    )
    output = capsys.readouterr().out
    lowered = output.lower()

    assert rc == 0
    assert "Reviewed batch packet preview" in output
    assert "status: preview" in output
    assert "dry_run_command: make peer-mapping-queue TOP_N=2" in output
    assert not md_output.exists()
    assert not csv_output.exists()
    assert "buy" not in lowered
    assert "sell" not in lowered
