import os
import sys
from pathlib import Path

import pandas as pd
import pytest

from src.decision_proof_queue import (
    DEFAULT_QUEUE_CSV,
    DEFAULT_QUEUE_MD,
    build_decision_proof_queue_drawer_summary_frame,
    build_decision_proof_queue_drawer_cards,
    build_decision_proof_queue_cards,
    build_decision_proof_queue_frame,
    main,
    render_decision_proof_queue_guidance,
    write_decision_proof_queue,
)
from src.reviewed_batch import FreshnessStatus


def _touch(path: Path, timestamp: int) -> None:
    os.utime(path, (timestamp, timestamp))


def test_decision_proof_queue_translates_decisions_without_recommendations():
    decisions = pd.DataFrame(
        [
            {
                "ticker": "META",
                "asset_type": "company",
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - DCF Ready But Peer Blocked",
                "primary_blocker": "peers",
                "data_confidence": "medium",
                "supported_analysis": "Supported analysis: price history, fundamentals, and standalone DCF scenario analysis.",
                "unsupported_analysis": "Unsupported analysis: peer-relative valuation until source-backed peer inputs exist.",
                "next_best_action": "Add source-backed peer mappings for META.",
            },
            {
                "ticker": "QQQ",
                "asset_type": "etf",
                "decision_bucket": "Monitor",
                "decision_subtype": "Monitor - ETF Market Proxy",
                "primary_blocker": "none",
                "data_confidence": "medium",
            },
            {
                "ticker": "APLD",
                "asset_type": "company",
                "decision_bucket": "Blocked by Data",
                "decision_subtype": "Blocked by Data - Missing Price",
                "primary_blocker": "price",
                "data_confidence": "low",
                "missing_data": "trusted price rows",
                "next_best_action": "Run make price-refresh-loop DRY_RUN=1.",
            },
        ]
    )
    readiness = pd.DataFrame(
        [
            {"ticker": "META", "in_active_universe": True, "dcf_ready": True, "peer_ready": False, "updated_at": "2026-06-01T00:00:00Z"},
            {"ticker": "QQQ", "in_active_universe": True, "updated_at": "2026-06-01T00:00:00Z"},
            {"ticker": "APLD", "in_active_universe": True, "updated_at": "2026-06-01T00:00:00Z"},
        ]
    )

    queue = build_decision_proof_queue_frame(decisions, readiness, limit=10)
    cards = build_decision_proof_queue_cards(queue)
    rendered = " ".join(str(value) for value in queue.to_numpy().ravel()).lower()
    rendered_cards = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert list(queue["ticker"]) == ["META", "APLD", "QQQ"]
    assert queue.iloc[0]["copy_only_command"] == "make focus-peers TICKER=META"
    assert "standalone dcf scenario analysis" in queue.iloc[0]["what_can_be_reviewed_now"].lower()
    assert "peer-relative valuation" in queue.iloc[0]["what_stays_locked"].lower()
    assert "make peer-mapping-queue top_n=25" in queue.iloc[0]["proof_after_unlock"].lower()
    assert queue.iloc[1]["copy_only_command"] == "make focus-price TICKER=APLD"
    assert queue.iloc[2]["copy_only_command"] == "make stock-report-md TICKER=QQQ"
    assert cards[0]["command"] == "make decision-proof-queue TOP_N=12"
    assert "what can be reviewed now" in rendered_cards
    assert "what proves an unlock" in rendered_cards
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_decision_proof_queue_writer_reports_missing_artifacts(tmp_path):
    result = write_decision_proof_queue(tmp_path)

    assert result.status == "missing"
    assert "make research-decisions" in result.message
    assert result.rows == 0
    assert not (tmp_path / DEFAULT_QUEUE_CSV).exists()
    assert not (tmp_path / DEFAULT_QUEUE_MD).exists()


def test_decision_proof_queue_drawer_cards_gate_stale_artifacts():
    freshness = FreshnessStatus(
        "stale",
        "Research decision output is older than the current ticker readiness report. Run make research-decisions before building the proof queue.",
        "make research-decisions",
    )

    cards = build_decision_proof_queue_drawer_cards(pd.DataFrame(), freshness)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["QUEUE STATUS", "NEXT SAFE ACTION", "FINISH THIS QUEUE"]
    assert cards[0]["command"] == "make research-decisions"
    assert cards[2]["command"] == "make research-decisions"
    assert "refresh before queue" in rendered
    assert "do not read old decision rows as current proof" in rendered
    assert "three-step proof refresh" in rendered
    assert "make decision-proof-queue top_n=12" in rendered
    assert "stale decision rows stay blocked proof" in rendered
    assert "recommendations" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_decision_proof_queue_guidance_renders_blocked_cards_without_advice():
    freshness = FreshnessStatus(
        "stale",
        "Readiness artifacts may be stale. Run make readiness before relying on final counts.",
        "make readiness",
    )
    cards = build_decision_proof_queue_drawer_cards(pd.DataFrame(), freshness)

    rendered = render_decision_proof_queue_guidance(cards).lower()

    assert "decision proof queue guidance" in rendered
    assert "refresh before queue" in rendered
    assert "three-step proof refresh" in rendered
    assert "copy-only command: make readiness" in rendered
    assert "make decision-proof-queue top_n=12" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_decision_proof_queue_drawer_cards_show_top_row_before_table():
    queue = pd.DataFrame(
        [
            {
                "ticker": "META",
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - DCF Ready But Peer Blocked",
                "primary_blocker": "peers",
                "data_confidence": "medium",
                "what_can_be_reviewed_now": "Standalone DCF scenario analysis can be reviewed.",
                "what_stays_locked": "Peer-relative valuation stays locked until source-backed peers exist.",
                "copy_only_command": "make focus-peers TICKER=META",
                "proof_after_unlock": "Proof after data changes: run `make peer-mapping-queue TOP_N=25`, `make readiness`, then `make stock-report-md TICKER=META`.",
            }
        ]
    )
    freshness = FreshnessStatus("current", "Readiness artifacts are current relative to watched source files.")

    cards = build_decision_proof_queue_drawer_cards(queue, freshness)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["QUEUE STATUS", "TOP PROOF ROW", "REVIEW NOW", "LOCKED", "PROOF AFTER UNLOCK"]
    assert cards[1]["command"] == "make focus-peers TICKER=META"
    assert "standalone dcf scenario analysis" in rendered
    assert "peer-relative valuation stays locked" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "not advice" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_decision_proof_queue_drawer_summary_frame_blocks_stale_artifacts():
    freshness = FreshnessStatus(
        "stale",
        "Research decision output is older than the current ticker readiness report. Run make research-decisions before building the proof queue.",
        "make research-decisions",
    )

    frame = build_decision_proof_queue_drawer_summary_frame(pd.DataFrame(), freshness)
    rendered = " ".join(str(value) for value in frame.to_numpy().ravel()).lower()

    assert list(frame["step"]) == [
        "Freshness status",
        "Top proof row",
        "What can be reviewed now",
        "What stays locked",
    ]
    assert frame.iloc[1]["status"] == "blocked by freshness gate"
    assert frame.iloc[1]["copy_only_command"] == "make research-decisions"
    assert "do not read stale decision rows as current proof" in rendered
    assert "make decision-proof-queue top_n=12" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_decision_proof_queue_drawer_summary_frame_shows_current_operator_loop():
    queue = pd.DataFrame(
        [
            {
                "ticker": "META",
                "decision_bucket": "Research Now",
                "decision_subtype": "Research Candidate - DCF Ready But Peer Blocked",
                "primary_blocker": "peers",
                "data_confidence": "medium",
                "what_can_be_reviewed_now": "Standalone DCF scenario analysis can be reviewed.",
                "what_stays_locked": "Peer-relative valuation stays locked until source-backed peers exist.",
                "copy_only_command": "make focus-peers TICKER=META",
                "proof_after_unlock": "Proof after data changes: run `make peer-mapping-queue TOP_N=25`, `make readiness`, then `make stock-report-md TICKER=META`.",
            }
        ]
    )
    freshness = FreshnessStatus("current", "Readiness artifacts are current relative to watched source files.")

    frame = build_decision_proof_queue_drawer_summary_frame(queue, freshness)
    rendered = " ".join(str(value) for value in frame.to_numpy().ravel()).lower()

    assert list(frame["step"]) == [
        "Freshness status",
        "Top proof row",
        "What can be reviewed now",
        "What stays locked",
        "Copy-only command",
        "Post-unlock proof command",
    ]
    assert frame.iloc[1]["copy_only_command"] == "make focus-peers TICKER=META"
    assert "standalone dcf scenario analysis can be reviewed" in rendered
    assert "peer-relative valuation stays locked" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "does not change account or execution state" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trade" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_decision_proof_queue_writer_blocks_stale_readiness(tmp_path):
    data = tmp_path / "data"
    reports = data / "reports"
    outputs = tmp_path / "outputs"
    reports.mkdir(parents=True)
    outputs.mkdir()
    (outputs / "research_decisions.csv").write_text("ticker,decision_bucket\nA,Research Now\n", encoding="utf-8")
    (reports / "ticker_readiness_report.csv").write_text("ticker,updated_at\nA,2026-06-01\n", encoding="utf-8")
    (reports / "feature_readiness_summary.csv").write_text("feature,status\nprice,ready\n", encoding="utf-8")
    source = data / "prices.csv"
    source.write_text("ticker,date,close\nA,2026-01-01,1\n", encoding="utf-8")
    for path in [
        data / "fundamentals.csv",
        data / "peers.csv",
        data / "earnings.csv",
        data / "analyst_estimates.csv",
    ]:
        path.write_text("", encoding="utf-8")
        _touch(path, 1000)
    _touch(outputs / "research_decisions.csv", 3000)
    _touch(reports / "ticker_readiness_report.csv", 2000)
    _touch(reports / "feature_readiness_summary.csv", 2000)
    _touch(source, 4000)

    result = write_decision_proof_queue(tmp_path)

    assert result.status == "stale"
    assert "Run make readiness" in result.message
    assert result.refresh_command == "make readiness"
    assert not (tmp_path / DEFAULT_QUEUE_CSV).exists()


def test_decision_proof_queue_cli_prints_blocked_guidance(tmp_path, capsys):
    data = tmp_path / "data"
    reports = data / "reports"
    outputs = tmp_path / "outputs"
    reports.mkdir(parents=True)
    outputs.mkdir()
    (outputs / "research_decisions.csv").write_text("ticker,decision_bucket\nA,Research Now\n", encoding="utf-8")
    (reports / "ticker_readiness_report.csv").write_text("ticker,updated_at\nA,2026-06-01\n", encoding="utf-8")
    (reports / "feature_readiness_summary.csv").write_text("feature,status\nprice,ready\n", encoding="utf-8")
    source = data / "prices.csv"
    source.write_text("ticker,date,close\nA,2026-01-01,1\n", encoding="utf-8")
    for path in [
        data / "fundamentals.csv",
        data / "peers.csv",
        data / "earnings.csv",
        data / "analyst_estimates.csv",
    ]:
        path.write_text("", encoding="utf-8")
        _touch(path, 1000)
    _touch(outputs / "research_decisions.csv", 3000)
    _touch(reports / "ticker_readiness_report.csv", 2000)
    _touch(reports / "feature_readiness_summary.csv", 2000)
    _touch(source, 4000)

    argv_before = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--top-n", "5"]
    try:
        with pytest.raises(SystemExit) as exc:
            main()
        output = capsys.readouterr().out.lower()
    finally:
        sys.argv = argv_before

    assert exc.value.code == 1
    assert "status: stale" in output
    assert "decision proof queue guidance" in output
    assert "rebuild the stale artifact first" in output
    assert "three-step proof refresh" in output
    assert "copy-only command: make readiness" in output
    assert "buy" not in output
    assert "sell" not in output


def test_decision_proof_queue_writer_writes_current_artifacts(tmp_path):
    data = tmp_path / "data"
    reports = data / "reports"
    outputs = tmp_path / "outputs"
    reports.mkdir(parents=True)
    outputs.mkdir()
    for path in [
        data / "prices.csv",
        data / "fundamentals.csv",
        data / "peers.csv",
        data / "earnings.csv",
        data / "analyst_estimates.csv",
    ]:
        path.write_text("", encoding="utf-8")
        _touch(path, 1000)
    (reports / "ticker_readiness_report.csv").write_text(
        "ticker,in_active_universe,dcf_ready,peer_ready,updated_at\nMETA,true,true,false,2026-06-01\n",
        encoding="utf-8",
    )
    (reports / "feature_readiness_summary.csv").write_text("feature,status\nprice,ready\n", encoding="utf-8")
    (outputs / "research_decisions.csv").write_text(
        (
            "ticker,asset_type,decision_bucket,decision_subtype,primary_blocker,data_confidence,"
            "supported_analysis,unsupported_analysis,next_best_action\n"
            "META,company,Research Now,Research Candidate - DCF Ready But Peer Blocked,peers,medium,"
            "standalone DCF scenario analysis,peer-relative valuation is locked,Add source-backed peers.\n"
        ),
        encoding="utf-8",
    )
    _touch(reports / "ticker_readiness_report.csv", 2000)
    _touch(reports / "feature_readiness_summary.csv", 2000)
    _touch(outputs / "research_decisions.csv", 3000)

    result = write_decision_proof_queue(tmp_path)

    assert result.status == "written"
    assert result.rows == 1
    assert (tmp_path / DEFAULT_QUEUE_CSV).exists()
    assert (tmp_path / DEFAULT_QUEUE_MD).exists()
    rendered = (tmp_path / DEFAULT_QUEUE_MD).read_text(encoding="utf-8").lower()
    assert "research-only queue" in rendered
    assert "decision labels are review states, not recommendations" in rendered
    assert "no broker integration" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
