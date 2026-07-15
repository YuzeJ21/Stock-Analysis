from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.earnings_nowcast_report import build_fixture_walkthrough, build_nowcast_packet, render_nowcast_packet


FIXTURE_ROOT = Path("tests/fixtures/earnings_nowcast")
CUTOFF = "2026-01-31T23:59:59Z"


def test_fixture_packet_is_reproducible_and_never_claims_real_company_evidence():
    first = build_nowcast_packet(FIXTURE_ROOT, ticker="SYN1", as_of_timestamp=CUTOFF)
    second = build_nowcast_packet(FIXTURE_ROOT, ticker="SYN1", as_of_timestamp=CUTOFF)

    assert first == second
    rendered = render_nowcast_packet(first)
    assert "synthetic test evidence" in rendered.lower()
    assert "investment advice" in rendered.lower()
    assert "beat probability" not in rendered.lower()
    assert first["calibration"]["probability_available"] is False


def test_fixture_packet_contains_readiness_forecast_provenance_and_signal_boundaries():
    packet = build_nowcast_packet(FIXTURE_ROOT, ticker="SYN1", as_of_timestamp=CUTOFF)

    assert packet["readiness"]["state"] == "baseline_ready"
    assert packet["forecast"]["revenue_midpoint"] is not None
    assert packet["forecast"]["model_version"] == "deterministic-v1"
    assert len(packet["forecast"]["input_snapshot_hash"]) == 64
    assert packet["signals"]["supported"]
    assert packet["signals"]["candidate_context_only"]
    assert "published_after_cutoff" in packet["signals"]["blockers"]
    assert packet["boundaries"]["numeric_signal_adjustments"] == "not_permitted"


def test_fixture_cohort_contains_five_synthetic_tickers_with_eight_quarters_each():
    rows = (FIXTURE_ROOT / "quarterly_actuals.csv").read_text(encoding="utf-8").splitlines()[1:]
    counts = {ticker: 0 for ticker in ("SYN1", "SYN2", "SYN3", "SYN4", "SYN5")}
    for row in rows:
        counts[row.split(",", 1)[0]] += 1

    assert counts == {ticker: 8 for ticker in counts}


def test_cli_is_deterministic_json():
    command = [
        sys.executable,
        "-m",
        "src.earnings_nowcast_report",
        "--root",
        ".",
        "--ticker",
        "SYN1",
        "--as-of",
        CUTOFF,
        "--fixture",
    ]
    first = subprocess.run(command, check=True, capture_output=True, text=True).stdout
    second = subprocess.run(command, check=True, capture_output=True, text=True).stdout

    assert first == second
    assert json.loads(first)["evidence_scope"] == "synthetic_test_evidence_only"


def test_missing_input_directory_is_environment_unavailable():
    with pytest.raises(FileNotFoundError, match="Nowcast input directory"):
        build_nowcast_packet(Path("tests/fixtures/does-not-exist"), ticker="SYN1", as_of_timestamp=CUTOFF)


def test_packet_selects_latest_consensus_available_at_cutoff_not_a_later_revision(tmp_path):
    fixture_copy = tmp_path / "nowcast"
    shutil.copytree(FIXTURE_ROOT, fixture_copy)
    consensus_path = fixture_copy / "consensus_snapshots.csv"
    with consensus_path.open("a", encoding="utf-8") as handle:
        handle.write(
            "SYN1,2026-Q1,2026-02-15T12:00:00Z,999,9.99,synthetic_test_fixture,2026-02-15T12:01:00Z\n"
        )

    packet = build_nowcast_packet(fixture_copy, ticker="SYN1", as_of_timestamp=CUTOFF)

    assert packet["forecast"]["consensus_revenue"] == 112.0
    assert packet["forecast"]["consensus_eps"] == 1.0


def test_fixture_walkthrough_covers_six_distinct_test_only_scenarios():
    walkthrough = build_fixture_walkthrough(FIXTURE_ROOT, as_of_timestamp=CUTOFF)
    by_scenario = {row["scenario"]: row for row in walkthrough["scenarios"]}

    assert walkthrough["evidence_scope"] == "synthetic_test_evidence_only"
    assert set(by_scenario) == {
        "baseline_ready",
        "revenue_ready_eps_withheld",
        "candidate_peer_only",
        "post_cutoff_blocked",
        "excluded_non_company",
        "backtest_ready_uncalibrated",
    }
    assert by_scenario["baseline_ready"]["state"] == "baseline_ready"
    assert by_scenario["revenue_ready_eps_withheld"]["revenue_ready"] is True
    assert by_scenario["revenue_ready_eps_withheld"]["eps_ready"] is False
    assert by_scenario["candidate_peer_only"]["candidate_context_only"] > 0
    assert by_scenario["post_cutoff_blocked"]["state"] == "blocked"
    assert by_scenario["excluded_non_company"]["state"] == "excluded"
    assert by_scenario["backtest_ready_uncalibrated"]["valid_event_count"] > 0
    assert by_scenario["backtest_ready_uncalibrated"]["probability_available"] is False
    assert all(row["test_only"] is True for row in walkthrough["scenarios"])


def test_cli_fixture_walkthrough_is_read_only_json():
    command = [
        sys.executable,
        "-m",
        "src.earnings_nowcast_report",
        "--root",
        ".",
        "--as-of",
        CUTOFF,
        "--fixture",
        "--walkthrough",
    ]

    result = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)

    assert len(payload["scenarios"]) == 6
    assert payload["evidence_scope"] == "synthetic_test_evidence_only"
