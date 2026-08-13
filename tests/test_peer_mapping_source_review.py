from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

from src.peer_mapping_source_review import (
    build_peer_mapping_writeback_guard,
    build_peer_mapping_source_review_packet,
    main,
    peer_mapping_packet_decision,
    peer_mapping_import_csv_header,
    peer_mapping_import_preview,
    peer_mapping_import_row_scaffold,
    peer_mapping_source_review_completion,
    peer_mapping_source_review_missing_fields,
    render_peer_mapping_writeback_guard,
    render_peer_mapping_source_review_markdown,
    render_peer_mapping_source_review_preview,
    write_peer_mapping_source_review_packet,
)
from src.reviewed_batch import FreshnessStatus


def _sample_root(tmp_path: Path) -> Path:
    root = tmp_path
    data = root / "data"
    reports = data / "reports"
    reports.mkdir(parents=True)
    for filename in ["prices.csv", "fundamentals.csv", "peers.csv", "earnings.csv", "analyst_estimates.csv"]:
        (data / filename).write_text("ticker\n", encoding="utf-8")
    (reports / "ticker_readiness_report.csv").write_text(
        "ticker,price_ready,dcf_ready,peer_ready,overall_readiness_state\n"
        "AAA,true,true,false,partial\n"
        "BBB,true,true,false,partial\n",
        encoding="utf-8",
    )
    (reports / "feature_readiness_summary.csv").write_text(
        "feature,ready,total\npeer_ready,0,2\n",
        encoding="utf-8",
    )
    (reports / "peer_readiness_report.csv").write_text(
        "ticker,mapping_status,peer_blocker_type,missing_peer_reason,next_peer_action\n"
        "AAA,missing_mapping,missing_peer_mapping,needs at least 2 source-backed peer mappings,Add peers.\n"
        "BBB,mapped,peer_fundamentals_missing,peer valuation still requires peer_valuation_ready,Add fundamentals.\n"
        "CCC,missing_mapping,missing_peer_mapping,needs at least 2 source-backed peer mappings,Add peers.\n",
        encoding="utf-8",
    )
    return root


def _sample_root_with_candidate_context(tmp_path: Path) -> Path:
    root = _sample_root(tmp_path)
    data = root / "data"
    reports = data / "reports"
    (data / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-01,AAA,10,100\n"
        "2026-01-01,DDD,20,100\n",
        encoding="utf-8",
    )
    (data / "universe.csv").write_text(
        "ticker,theme,sectoretf,defaultpurpose,marketcapbucket,source_detail,notes\n"
        "AAA,Unclassified,,Core Compounder,Unknown,Health Care,fixture\n"
        "DDD,Unclassified,,Core Compounder,Unknown,Health Care,fixture\n",
        encoding="utf-8",
    )
    (reports / "ticker_readiness_report.csv").write_text(
        "ticker,price_ready,dcf_ready,peer_ready,overall_readiness_state\n"
        "AAA,true,true,false,partial\n"
        "DDD,true,false,false,partial\n",
        encoding="utf-8",
    )
    return root


def _sample_root_with_active_peer_blocker(tmp_path: Path) -> Path:
    root = _sample_root(tmp_path)
    data = root / "data"
    reports = data / "reports"
    outputs = root / "outputs"
    outputs.mkdir(exist_ok=True)
    (outputs / "project_status_top_actions.csv").write_text(
        "priority,ticker,dataset,status,reason,recommended_action,target_file,focus_command,example_command\n"
        "3,CCC,peers,manual_input_needed,No local peer mapping is configured.,Run make focus-peers TICKER=CCC,data/imports/peers.csv,make focus-peers TICKER=CCC,make templates\n"
        "3,AAA,peers,manual_input_needed,No local peer mapping is configured.,Run make focus-peers TICKER=AAA,data/imports/peers.csv,make focus-peers TICKER=AAA,make templates\n",
        encoding="utf-8",
    )
    (data / "universe_active.csv").write_text(
        "ticker\n"
        "CCC\n",
        encoding="utf-8",
    )
    (data / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-01,AAA,10,100\n"
        "2026-01-01,CCC,12,100\n",
        encoding="utf-8",
    )
    (reports / "ticker_readiness_report.csv").write_text(
        "ticker,price_ready,dcf_ready,peer_ready,overall_readiness_state\n"
        "AAA,true,true,false,partial\n"
        "CCC,true,true,false,partial\n",
        encoding="utf-8",
    )
    return root


def test_peer_mapping_source_review_packet_builds_two_review_slots_per_candidate(tmp_path: Path):
    packet = build_peer_mapping_source_review_packet(_sample_root(tmp_path), top_n=1)
    rendered = render_peer_mapping_source_review_markdown(packet)
    decision = peer_mapping_packet_decision(packet)

    assert packet.tickers == ("AAA",)
    assert len(packet.rows) == 2
    assert decision.status == "needs_source_review_fields"
    assert decision.trusted_peer_proof_state == "locked"
    assert decision.candidate_context_state == "not_loaded"
    assert decision.next_safe_action == "Fill reviewed peer source-review fields for AAA / peer_1."
    assert "## First Peer Readiness Answer" in rendered
    assert "First answer status: `needs_source_review_fields`" in rendered
    assert "Trusted peer proof state: `locked`" in rendered
    assert "Import schema: `ticker, peer_ticker, peer_group, sector, industry, peer_role" in rendered
    assert "relationship rationale" in rendered
    assert "memory, popularity, sector/theme similarity alone" in rendered
    assert "Candidate context:" in rendered
    assert "Completion status: `needs_field_fills`" in rendered
    assert "Import row scaffold: `blocked until reviewed fields are filled" in rendered
    assert "Import preview status: `needs_field_fills`" in rendered
    assert "CSV row: `blocked until completion-ready`" in rendered
    assert "Do not fabricate peer mappings" in rendered
    assert "does not provide direct buy/sell instructions" in rendered


def test_peer_mapping_source_review_prioritizes_active_universe_blockers(tmp_path: Path):
    packet = build_peer_mapping_source_review_packet(_sample_root_with_active_peer_blocker(tmp_path), top_n=2)
    rendered = render_peer_mapping_source_review_preview(packet)

    assert packet.selection_source == "project_status_top_actions"
    assert packet.tickers[:2] == ("CCC", "AAA")
    assert [row.ticker for row in packet.rows[:4]] == ["CCC", "CCC", "AAA", "AAA"]
    assert "selection_source: project_status_top_actions" in rendered


def test_peer_mapping_source_review_surfaces_candidate_context_only_layer(tmp_path: Path):
    packet = build_peer_mapping_source_review_packet(_sample_root_with_candidate_context(tmp_path), top_n=1)
    packet = replace(packet, freshness=FreshnessStatus(status="current", message="readiness artifacts are current"))
    rendered = render_peer_mapping_source_review_markdown(packet)
    decision = peer_mapping_packet_decision(packet)

    assert packet.rows[0].candidate_context_state == "candidate_context_only"
    assert packet.rows[0].candidate_context_source == "source_detail_fallback"
    assert packet.rows[0].candidate_context_count == "1"
    assert packet.rows[0].candidate_context_peers == "DDD"
    assert "Candidate context state: `candidate_context_only`" in rendered
    assert "Candidate context source: `source_detail_fallback`" in rendered
    assert "Candidate context peers: `DDD`" in rendered
    assert "not trusted peer proof" in rendered.lower()
    assert decision.status == "candidate_context_only"
    assert decision.candidate_context_state == "candidate_context_only"
    assert "not trusted peer proof" in decision.boundary.lower()
    assert "First answer status: `candidate_context_only`" in rendered


def test_peer_mapping_source_review_respects_explicit_ticker_scope(tmp_path: Path):
    packet = build_peer_mapping_source_review_packet(_sample_root(tmp_path), top_n=5, tickers="ZZZ,AAA")

    assert packet.tickers == ("ZZZ", "AAA")
    assert [row.ticker for row in packet.rows] == ["ZZZ", "ZZZ", "AAA", "AAA"]


def test_peer_mapping_source_review_preview_is_copy_safe(tmp_path: Path):
    packet = build_peer_mapping_source_review_packet(_sample_root(tmp_path), top_n=1)
    rendered = render_peer_mapping_source_review_preview(packet)
    lowered = rendered.lower()

    assert "status: preview" in rendered
    assert "first_answer_status: needs_source_review_fields" in rendered
    assert "trusted_peer_proof_state: locked" in rendered
    assert "first_answer_next_safe_action: Fill reviewed peer source-review fields for AAA / peer_1." in rendered
    assert "no Markdown or CSV artifacts were written" in rendered
    assert "top_review_row:" in rendered
    assert "make focus-peers TICKER=AAA" in rendered
    assert "no direct buy/sell instructions" in lowered
    assert "recommendation" not in lowered


def test_peer_mapping_source_review_writes_markdown_and_csv(tmp_path: Path):
    root = _sample_root(tmp_path)
    packet = build_peer_mapping_source_review_packet(root, top_n=1)
    md_output = tmp_path / "outputs" / "peer_mapping_source_review.md"
    csv_output = tmp_path / "outputs" / "peer_mapping_source_review.csv"

    write_peer_mapping_source_review_packet(packet, md_output=md_output, csv_output=csv_output)
    rows = list(csv.DictReader(csv_output.read_text(encoding="utf-8").splitlines()))

    assert "# Peer Mapping Source Review Packet" in md_output.read_text(encoding="utf-8")
    assert len(rows) == 2
    assert rows[0]["target_file"] == "data/imports/peers.csv"
    assert rows[0]["source_proof_status"] == "needs_review"
    assert rows[0]["import_row_ready"] == "no"
    assert "candidate_context_state" in rows[0]
    assert "candidate_context_note" in rows[0]


def test_peer_mapping_source_review_completion_detects_placeholders(tmp_path: Path):
    packet = build_peer_mapping_source_review_packet(_sample_root(tmp_path), top_n=1)
    completion = peer_mapping_source_review_completion(packet.rows[0], packet.freshness)
    preview = peer_mapping_import_preview(packet.rows[0], packet.freshness)

    assert completion.status == "needs_field_fills"
    assert "proposed_peer_ticker" in completion.missing_fields
    assert "source_proof_status" in completion.missing_fields
    assert "import_row_ready" in completion.missing_fields
    assert "keep peer valuation locked" in completion.next_safe_action
    assert peer_mapping_import_row_scaffold(packet.rows[0]).startswith("blocked until reviewed fields are filled")
    assert preview.status == "needs_field_fills"
    assert preview.csv_header == (
        "ticker,peer_ticker,peer_group,sector,industry,peer_role,relationship_rationale,"
        "comparability_basis,valuation_anchor_eligible,source,as_of_date"
    )
    assert preview.csv_row == ""
    assert "Do not edit or apply" in preview.apply_boundary


def test_peer_mapping_source_review_completion_builds_ready_import_row_scaffold(tmp_path: Path):
    packet = build_peer_mapping_source_review_packet(_sample_root(tmp_path), top_n=1)
    reviewed_row = replace(
        packet.rows[0],
        proposed_peer_ticker="MSFT",
        peer_group="large-cap software",
        sector="Technology",
        industry="Software",
        peer_role="core_peer",
        source="https://example.com/peer-proof",
        as_of_date="2026-06-14",
        relationship_rationale="Source names comparable enterprise software exposure.",
        comparability_basis="business model; customer mix; growth and margin profile",
        valuation_anchor_eligible="yes",
        reviewer="local reviewer",
        review_date="2026-06-14",
        source_proof_status="reviewed",
        import_row_ready="yes",
    )
    completion = peer_mapping_source_review_completion(reviewed_row, packet.freshness)
    preview = peer_mapping_import_preview(reviewed_row, packet.freshness)
    ready_packet = replace(packet, rows=(reviewed_row,))
    decision = peer_mapping_packet_decision(ready_packet)

    assert peer_mapping_source_review_missing_fields(reviewed_row) == ()
    assert completion.status == "ready_for_import_row_scaffold"
    assert completion.import_row_scaffold == (
        "AAA,MSFT,large-cap software,Technology,Software,core_peer,"
        "Source names comparable enterprise software exposure.,"
        "business model; customer mix; growth and margin profile,yes,"
        "https://example.com/peer-proof,2026-06-14"
    )
    assert "validate and preview" in completion.next_safe_action
    assert peer_mapping_import_csv_header() == (
        "ticker,peer_ticker,peer_group,sector,industry,peer_role,relationship_rationale,"
        "comparability_basis,valuation_anchor_eligible,source,as_of_date"
    )
    assert preview.status == "ready_for_validate_preview"
    assert preview.csv_row == completion.import_row_scaffold
    assert preview.validation_command == "make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>"
    assert "make imports-apply IMPORT_TICKERS=<ticker> only after imports-preview" in preview.apply_boundary
    assert "make readiness" in preview.post_apply_proof
    assert decision.status == "ready_for_validate_preview"
    assert decision.next_safe_action == "Run make peer-mapping-writeback-guard for AAA / peer_1, then validate and preview."
    assert decision.trusted_peer_proof_state == "ready_for_guard"


def test_peer_mapping_source_review_blocks_invalid_role_or_anchor_decision(tmp_path: Path):
    packet = build_peer_mapping_source_review_packet(_sample_root(tmp_path), top_n=1)
    invalid_row = replace(
        packet.rows[0],
        proposed_peer_ticker="MSFT",
        peer_group="large-cap software",
        peer_role="favorite_peer",
        source="https://example.com/peer-proof",
        as_of_date="2026-06-14",
        relationship_rationale="Source names comparable enterprise software exposure.",
        comparability_basis="business model; customer mix; growth and margin profile",
        valuation_anchor_eligible="yes",
        reviewer="local reviewer",
        review_date="2026-06-14",
        source_proof_status="reviewed",
        import_row_ready="yes",
    )

    completion = peer_mapping_source_review_completion(invalid_row, packet.freshness)

    assert completion.status == "needs_field_fills"
    assert completion.missing_fields == ("peer_role_invalid",)
    assert completion.import_row_scaffold.startswith("blocked until reviewed fields are filled")


def test_peer_mapping_writeback_guard_allows_ready_non_duplicate_row(tmp_path: Path):
    root = _sample_root(tmp_path)
    packet = build_peer_mapping_source_review_packet(root, top_n=1)
    reviewed_row = replace(
        packet.rows[0],
        proposed_peer_ticker="MSFT",
        peer_group="large-cap software",
        sector="Technology",
        industry="Software",
        peer_role="core_peer",
        source="https://example.com/peer-proof",
        as_of_date="2026-06-14",
        relationship_rationale="Source names comparable enterprise software exposure.",
        comparability_basis="business model; customer mix; growth and margin profile",
        valuation_anchor_eligible="yes",
        reviewer="local reviewer",
        review_date="2026-06-14",
        source_proof_status="reviewed",
        import_row_ready="yes",
    )

    guard = build_peer_mapping_writeback_guard(root, reviewed_row)
    rendered = render_peer_mapping_writeback_guard(guard, reviewed_row)

    assert guard.status == "ready_for_validate_preview"
    assert guard.blocking_reasons == ()
    assert guard.duplicate_sources == ()
    assert guard.csv_header == (
        "ticker,peer_ticker,peer_group,sector,industry,peer_role,relationship_rationale,"
        "comparability_basis,valuation_anchor_eligible,source,as_of_date"
    )
    assert guard.csv_row == (
        "AAA,MSFT,large-cap software,Technology,Software,core_peer,"
        "Source names comparable enterprise software exposure.,"
        "business model; customer mix; growth and margin profile,yes,"
        "https://example.com/peer-proof,2026-06-14"
    )
    assert guard.proof_record_status == "ready_for_review_fields"
    assert "validation_result" in guard.proof_record_missing_fields
    assert "final_outcome" in guard.proof_record_missing_fields
    assert guard.proof_record_command.startswith("DRY_RUN=1 make reviewed-batch-proof-record")
    assert "LANE=peers" in guard.proof_record_command
    assert "BATCH_ID=RB-PEER-AAA-MSFT-20260614" in guard.proof_record_command
    assert "SOURCE_FILES='data/imports/peers.csv; https://example.com/peer-proof'" in guard.proof_record_command
    assert "status: ready_for_validate_preview" in rendered
    assert "proof_record_status: ready_for_review_fields" in rendered
    assert "proof_record_missing_fields: validation_result" in rendered
    assert "validation_command: make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>" in rendered
    assert "proof_record_command: DRY_RUN=1 make reviewed-batch-proof-record" in rendered
    assert "Copy this dry-run proof-record command only after" in rendered
    assert "does not edit files" in rendered
    assert "direct buy/sell instructions" in rendered


def test_peer_mapping_writeback_guard_blocks_duplicate_and_self_peer(tmp_path: Path):
    root = _sample_root(tmp_path)
    (root / "data" / "peers.csv").write_text(
        "ticker,peer_ticker,peer_group,sector,industry,source,as_of_date\n"
        "AAA,MSFT,large-cap software,Technology,Software,https://example.com/old,2026-06-01\n",
        encoding="utf-8",
    )
    packet = build_peer_mapping_source_review_packet(root, top_n=1)
    duplicate_row = replace(
        packet.rows[0],
        proposed_peer_ticker="MSFT",
        peer_group="large-cap software",
        peer_role="core_peer",
        source="https://example.com/peer-proof",
        as_of_date="2026-06-14",
        relationship_rationale="Source names comparable enterprise software exposure.",
        comparability_basis="business model; customer mix; growth and margin profile",
        valuation_anchor_eligible="yes",
        reviewer="local reviewer",
        review_date="2026-06-14",
        source_proof_status="reviewed",
        import_row_ready="yes",
    )
    self_peer_row = replace(duplicate_row, proposed_peer_ticker="AAA")

    duplicate_guard = build_peer_mapping_writeback_guard(root, duplicate_row)
    self_peer_guard = build_peer_mapping_writeback_guard(root, self_peer_row)

    assert duplicate_guard.status == "blocked"
    assert "duplicate_peer_pair" in duplicate_guard.blocking_reasons
    assert duplicate_guard.duplicate_sources == ("data/peers.csv",)
    assert duplicate_guard.csv_row == ""
    assert duplicate_guard.proof_record_status == "blocked_by_guard"
    assert duplicate_guard.proof_record_missing_fields == ("guard_blocking_reasons",)
    assert "FINAL_OUTCOME='<supported|candidate_context_only|still_blocked|skipped|excluded>'" in duplicate_guard.proof_record_command
    assert "Do not record a supported peer outcome" in duplicate_guard.proof_record_boundary
    assert self_peer_guard.status == "blocked"
    assert "self_peer" in self_peer_guard.blocking_reasons


def test_peer_mapping_writeback_guard_cli_is_copy_only(tmp_path: Path, capsys):
    root = _sample_root(tmp_path)
    rc = main(
        [
            "--root",
            str(root),
            "--guard-writeback",
            "--ticker",
            "AAA",
            "--peer-ticker",
            "MSFT",
            "--peer-group",
            "large-cap software",
            "--sector",
            "Technology",
            "--industry",
            "Software",
            "--peer-role",
            "core_peer",
            "--source",
            "https://example.com/peer-proof",
            "--as-of-date",
            "2026-06-14",
            "--relationship-rationale",
            "Source names comparable enterprise software exposure.",
            "--comparability-basis",
            "business model; customer mix; growth and margin profile",
            "--valuation-anchor-eligible",
            "yes",
            "--reviewer",
            "local reviewer",
            "--review-date",
            "2026-06-14",
            "--source-proof-status",
            "reviewed",
            "--import-row-ready",
            "yes",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert "Peer mapping write-back guard" in output
    assert "status: ready_for_validate_preview" in output
    assert (
        "csv_row: AAA,MSFT,large-cap software,Technology,Software,core_peer,"
        "Source names comparable enterprise software exposure.,"
        "business model; customer mix; growth and margin profile,yes,"
        "https://example.com/peer-proof,2026-06-14"
    ) in output
    assert "proof_record_command: DRY_RUN=1 make reviewed-batch-proof-record" in output
    assert "does not edit files" in output


def test_peer_mapping_source_review_blocks_on_stale_readiness(tmp_path: Path):
    root = _sample_root(tmp_path)
    (root / "data/peers.csv").write_text(
        "ticker,as_of_date\n,2026-07-16\n",
        encoding="utf-8",
    )
    (root / "data/reports/ticker_readiness_report.csv").write_text(
        "ticker,price_ready,dcf_ready,peer_ready,overall_readiness_state,generated_at\n"
        "AAA,true,true,false,partial,2026-07-15T19:30:00+00:00\n",
        encoding="utf-8",
    )
    (root / "data/reports/feature_readiness_summary.csv").write_text(
        "feature,ready,total,generated_at\npeer_ready,0,1,2026-07-15T19:30:00+00:00\n",
        encoding="utf-8",
    )

    packet = build_peer_mapping_source_review_packet(root, top_n=1)
    rendered = render_peer_mapping_source_review_markdown(packet)

    assert packet.freshness.status == "stale"
    assert "Packet status: `blocked_by_freshness`" in rendered
    assert "Completion status: `blocked_by_freshness`" in rendered
    assert "Import preview status: `blocked_by_freshness`" in rendered
    assert "make readiness" in rendered


def test_peer_mapping_source_review_cli_dry_run_does_not_write_outputs(tmp_path: Path, capsys):
    root = _sample_root(tmp_path)
    md_output = tmp_path / "outputs" / "packet.md"
    csv_output = tmp_path / "outputs" / "packet.csv"

    rc = main(
        [
            "--root",
            str(root),
            "--top-n",
            "1",
            "--md-output",
            str(md_output),
            "--csv-output",
            str(csv_output),
            "--dry-run",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 0
    assert "Peer mapping source review preview" in output
    assert not md_output.exists()
    assert not csv_output.exists()
