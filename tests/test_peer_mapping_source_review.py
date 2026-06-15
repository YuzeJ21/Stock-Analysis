from __future__ import annotations

import csv
import os
from pathlib import Path

from src.peer_mapping_source_review import (
    build_peer_mapping_source_review_packet,
    main,
    render_peer_mapping_source_review_markdown,
    render_peer_mapping_source_review_preview,
    write_peer_mapping_source_review_packet,
)


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


def test_peer_mapping_source_review_packet_builds_two_review_slots_per_candidate(tmp_path: Path):
    packet = build_peer_mapping_source_review_packet(_sample_root(tmp_path), top_n=1)
    rendered = render_peer_mapping_source_review_markdown(packet)

    assert packet.tickers == ("AAA",)
    assert len(packet.rows) == 2
    assert "Import schema: `ticker, peer_ticker, peer_group, sector, industry, source, as_of_date`" in rendered
    assert "relationship rationale" in rendered
    assert "memory, popularity, sector/theme similarity alone" in rendered
    assert "Do not fabricate peer mappings" in rendered
    assert "does not provide direct buy/sell instructions" in rendered


def test_peer_mapping_source_review_respects_explicit_ticker_scope(tmp_path: Path):
    packet = build_peer_mapping_source_review_packet(_sample_root(tmp_path), top_n=5, tickers="ZZZ,AAA")

    assert packet.tickers == ("ZZZ", "AAA")
    assert [row.ticker for row in packet.rows] == ["ZZZ", "ZZZ", "AAA", "AAA"]


def test_peer_mapping_source_review_preview_is_copy_safe(tmp_path: Path):
    packet = build_peer_mapping_source_review_packet(_sample_root(tmp_path), top_n=1)
    rendered = render_peer_mapping_source_review_preview(packet)
    lowered = rendered.lower()

    assert "status: preview" in rendered
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


def test_peer_mapping_source_review_blocks_on_stale_readiness(tmp_path: Path):
    root = _sample_root(tmp_path)
    source = root / "data" / "peers.csv"
    os.utime(source, (source.stat().st_atime + 1000, source.stat().st_mtime + 1000))

    packet = build_peer_mapping_source_review_packet(root, top_n=1)
    rendered = render_peer_mapping_source_review_markdown(packet)

    assert packet.freshness.status == "stale"
    assert "Packet status: `blocked_by_freshness`" in rendered
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
