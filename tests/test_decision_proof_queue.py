import os
from pathlib import Path

import pandas as pd

from src.decision_proof_queue import (
    DEFAULT_QUEUE_CSV,
    DEFAULT_QUEUE_MD,
    build_decision_proof_queue_cards,
    build_decision_proof_queue_frame,
    write_decision_proof_queue,
)


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
