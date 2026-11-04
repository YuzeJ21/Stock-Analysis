"""Dashboard coverage labels keep saved readiness and working plans separate."""

import json
from pathlib import Path

import pytest

import src.dashboard as dashboard


def _status_payload() -> dict[str, object]:
    return {
        "summary": {
            "tickers_total": 3541,
            "tickers_with_prices": 280,
            "tickers_dcf_ready": 170,
            "tickers_peer_ready": 10,
            "data_gaps": 100,
        },
        "coverage_populations": {
            "saved_readiness": {
                "status": "available",
                "total": 3538,
                "price_ready": 265,
                "momentum_ready": 262,
                "fundamentals_ready": 175,
                "dcf_ready": 169,
                "peer_ready": 9,
            },
            "working_universe": {
                "status": "available",
                "total": 3541,
                "has_prices": 280,
                "momentum_usable": 275,
            },
        },
    }


def test_project_status_and_overview_use_saved_readiness_population():
    """A working-universe summary must not supply saved-readiness fractions."""

    payload = _status_payload()
    cards = dict((label, value) for label, value, _ in dashboard.project_status_metric_cards(payload))
    cockpit = dashboard.project_status_cockpit_html(payload, 45, "Needs Data")
    landing = dashboard.overview_landing_cards(payload, {}, "2026-10-28", 1, 0)
    guardrail = dashboard.overview_interpretation_guardrail_card(
        payload, {"critical": 20}, {},
    )

    assert cards["Price Ready"] == "265/3538"
    assert cards["DCF Ready"] == "169/3538"
    assert cards["Peer Ready"] == "9/3538"
    assert "265/3538" in cockpit
    assert "169/3538" in cockpit
    assert "9/3538" in cockpit
    assert "280/3541" not in cockpit
    assert landing[1]["title"] == "265/3538"
    assert "169 DCF-ready" in landing[2]["title"]
    assert "9 tickers also have peer-relative context" in landing[2]["body"]
    assert "265/3538 tickers have usable prices" in guardrail["body"]
    assert "momentum requires its own history check" in landing[1]["body"].lower()
    assert "enough local price context for momentum" not in landing[1]["body"].lower()


def test_unavailable_saved_readiness_does_not_inherit_ambiguous_summary():
    """An explicit unavailable population must never become a plausible ratio."""

    payload = _status_payload()
    payload["coverage_populations"]["saved_readiness"] = {
        "status": "unavailable",
        "total": None,
        "price_ready": None,
        "momentum_ready": None,
        "fundamentals_ready": None,
        "dcf_ready": None,
        "peer_ready": None,
    }

    cards = dict((label, value) for label, value, _ in dashboard.project_status_metric_cards(payload))
    cockpit = dashboard.project_status_cockpit_html(payload, 45, "Needs Data")
    landing = dashboard.overview_landing_cards(payload, {}, "2026-10-28", 1, 0)
    guardrail = dashboard.overview_interpretation_guardrail_card(
        payload, {"critical": 20}, {},
    )

    assert cards["Price Ready"] == "Not available"
    assert cards["DCF Ready"] == "Not available"
    assert cards["Peer Ready"] == "Not available"
    assert "Not available" in cockpit
    assert "280/3541" not in cockpit
    assert landing[1]["title"] == "Not available"
    assert "280/3541" not in guardrail["body"]
    assert "Not available" in guardrail["body"]


def test_unavailable_saved_readiness_does_not_label_workflow_score_as_readiness():
    """A healthy workflow score cannot claim saved research readiness."""

    payload = _status_payload()
    payload["coverage_populations"]["saved_readiness"] = {
        "status": "unavailable", "total": None, "price_ready": None,
        "momentum_ready": None, "fundamentals_ready": None,
        "dcf_ready": None, "peer_ready": None,
    }

    cockpit = dashboard.project_status_cockpit_html(payload, 100, "Ready")
    guardrail = dashboard.overview_interpretation_guardrail_card(payload, {}, {})

    assert "Workflow health" in cockpit
    assert "Ready review readiness" not in cockpit
    assert "Workflow health" in guardrail["title"]
    assert "Ready review readiness" not in guardrail["title"]
    assert "100/100" in guardrail["title"]


def test_partial_legacy_summary_does_not_invent_dcf_or_peer_zeroes():
    """Missing legacy fields are unknown even when its price pair exists."""

    payload = {"summary": {"tickers_total": 100, "tickers_with_prices": 20}}

    cards = dict((label, value) for label, value, _ in dashboard.project_status_metric_cards(payload))

    assert cards["Price Ready"] == "Not available"
    assert cards["DCF Ready"] == "Not available"
    assert cards["Peer Ready"] == "Not available"


def test_direct_legacy_status_does_not_display_unverified_coverage_fractions():
    """Direct callers cannot infer a shared cohort from old mixed summary keys."""

    payload = {
        "summary": {
            "tickers_total": 3541,
            "tickers_with_prices": 280,
            "tickers_dcf_ready": 169,
            "tickers_peer_ready": 9,
        }
    }

    cards = dict((label, value) for label, value, _ in dashboard.project_status_metric_cards(payload))
    cockpit = dashboard.project_status_cockpit_html(payload, 40, "Needs Data")
    landing = dashboard.overview_landing_cards(payload, {}, "2026-10-28", 1, 0)
    pressure = dashboard.overview_benchmark_pressure_cards(None, None, payload)
    plan = dashboard.price_refresh_operator_plan_cards(
        {"master_universe": 3541, "price_ready": 280},
    )

    assert cards["Price Ready"] == "Not available"
    assert cards["DCF Ready"] == "Not available"
    assert cards["Peer Ready"] == "Not available"
    assert "280/3541" not in cockpit
    assert landing[1]["title"] == "Not available"
    assert "unavailable" in pressure[0]["title"].lower()
    assert "command" not in pressure[0]
    assert len(plan) == 1
    assert "command" not in plan[0]
    assert "separate reviewed status rebuild" in plan[0]["body"].lower()


def test_working_universe_drives_price_gap_and_refresh_plan():
    """Price planning uses the working cohort, including its own numerator."""

    payload = _status_payload()
    pressure = dashboard.overview_benchmark_pressure_cards(None, None, payload)
    plan = dashboard.price_refresh_operator_plan_cards(
        {"master_universe": 999, "price_ready": 999},
        project_status_payload=payload,
    )

    assert "3,261/3,541" in pressure[0]["body"] or "3261/3541" in pressure[0]["body"]
    assert "3,261 ticker(s)" in plan[0]["body"]
    assert "MAX_CANDIDATES=3300" in plan[1]["command"]
    assert "3,273" not in plan[0]["body"]


def test_unavailable_working_universe_stops_numeric_price_plan():
    """An unknown working cohort must not create a numeric refresh target."""

    payload = _status_payload()
    payload["coverage_populations"]["working_universe"] = {
        "status": "unavailable",
        "total": None,
        "has_prices": None,
        "momentum_usable": None,
    }

    pressure = dashboard.overview_benchmark_pressure_cards(None, None, payload)
    plan = dashboard.price_refresh_operator_plan_cards(
        {"master_universe": 999, "price_ready": 999},
        project_status_payload=payload,
    )

    assert "unavailable" in pressure[0]["title"].lower()
    assert "999" not in pressure[0]["body"]
    assert "command" not in pressure[0]
    assert len(plan) == 1
    assert "unavailable" in plan[0]["title"].lower()
    assert "command" not in plan[0]


def test_partial_working_universe_stops_numeric_price_plan():
    """An available label cannot turn a missing working count into zero."""

    payload = _status_payload()
    payload["coverage_populations"]["working_universe"]["has_prices"] = None

    plan = dashboard.price_refresh_operator_plan_cards(
        {"master_universe": 999, "price_ready": 999},
        project_status_payload=payload,
    )

    assert len(plan) == 1
    assert "unavailable" in plan[0]["title"].lower()
    assert "command" not in plan[0]


def test_data_health_lane_answers_use_explicit_saved_readiness_counts():
    """Lane answers must not prefer a conflicting aggregate summary."""

    payload = _status_payload()
    freshness = dashboard.FreshnessStatus("current", "Saved readiness is current.", "make readiness")
    prices = dashboard.data_health_selected_lane_answer_cards(
        "prices", freshness, project_status_payload=payload,
        saved_readiness_summary={"price_ready": 999},
    )
    peers = dashboard.data_health_selected_lane_answer_cards(
        "peers", freshness, project_status_payload=payload,
        saved_readiness_summary={"peer_ready": 999},
    )

    assert "265 tickers have price rows" in prices[0]["body"]
    assert "9 tickers have mapped peer trend context" in peers[0]["body"]


def test_legacy_status_load_hydrates_saved_report_counts(tmp_path: Path, monkeypatch):
    """A saved legacy status must use the selected saved readiness cohort."""

    monkeypatch.delenv("STOCK_RESEARCH_DATA_PROFILE", raising=False)
    report_dir = tmp_path / "data" / "reports"
    report_dir.mkdir(parents=True)
    (report_dir / "ticker_readiness_report.csv").write_text(
        "ticker,price_ready,momentum_ready,fundamentals_ready,dcf_ready,peer_ready\n"
        "AAA,True,True,False,False,False\n"
        "BBB,True,False,True,True,False\n"
        "CCC,False,False,True,False,True\n"
        ",True,True,True,True,True\n",
        encoding="utf-8",
    )
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    (outputs_dir / "project_status.json").write_text(
        json.dumps({"summary": {"tickers_total": 4, "tickers_with_prices": 4}}),
        encoding="utf-8",
    )

    loaded = dashboard.load_saved_project_status_payload(tmp_path)

    assert loaded["coverage_populations"]["saved_readiness"] == {
        "status": "available",
        "total": 3,
        "price_ready": 2,
        "momentum_ready": 1,
        "fundamentals_ready": 2,
        "dcf_ready": 1,
        "peer_ready": 1,
        "source": "data/reports/ticker_readiness_report.csv",
        "profile_key": "default",
        "data_dir": str(tmp_path / "data"),
        "loaded_from_current_profile": True,
    }
    assert loaded["coverage_populations"]["working_universe"]["status"] == "unavailable"
    cards = dashboard.project_status_metric_cards(loaded)
    assert dict((label, value) for label, value, _ in cards)["Price Ready"] == "2/3"
    assert "selected-profile saved readiness report read at page load; freshness checked separately" in cards[2][2].lower()
    assert "freshness checked separately" in dashboard.project_status_cockpit_html(loaded, 45, "Needs Data").lower()


def test_legacy_status_load_marks_missing_saved_report_unavailable(tmp_path: Path, monkeypatch):
    """Absent saved evidence cannot inherit old summary counts."""

    monkeypatch.delenv("STOCK_RESEARCH_DATA_PROFILE", raising=False)
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    (outputs_dir / "project_status.json").write_text(
        json.dumps({"summary": {"tickers_total": 40, "tickers_with_prices": 40}}),
        encoding="utf-8",
    )

    loaded = dashboard.load_saved_project_status_payload(tmp_path)

    assert loaded["coverage_populations"]["saved_readiness"]["status"] == "unavailable"
    assert loaded["coverage_populations"]["saved_readiness"]["total"] is None
    assert dict((label, value) for label, value, _ in dashboard.project_status_metric_cards(loaded))["Price Ready"] == "Not available"


def test_legacy_status_load_marks_empty_saved_report_unavailable(tmp_path: Path, monkeypatch):
    """A header-only report cannot establish a saved-readiness population."""

    monkeypatch.delenv("STOCK_RESEARCH_DATA_PROFILE", raising=False)
    report_dir = tmp_path / "data" / "reports"
    report_dir.mkdir(parents=True)
    (report_dir / "ticker_readiness_report.csv").write_text(
        "ticker,price_ready,momentum_ready,fundamentals_ready,dcf_ready,peer_ready\n",
        encoding="utf-8",
    )
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    (outputs_dir / "project_status.json").write_text(
        json.dumps({"summary": {"tickers_total": 10, "tickers_with_prices": 10}}),
        encoding="utf-8",
    )

    loaded = dashboard.load_saved_project_status_payload(tmp_path)

    assert loaded["coverage_populations"]["saved_readiness"]["status"] == "unavailable"
    assert loaded["coverage_populations"]["saved_readiness"]["total"] is None


def test_local_profile_never_reads_default_project_status(tmp_path: Path, monkeypatch):
    """A default status file cannot leak coverage into the Local profile."""

    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    (outputs_dir / "project_status.json").write_text(
        json.dumps({"summary": {"tickers_total": 4, "tickers_with_prices": 4}}),
        encoding="utf-8",
    )

    assert dashboard.load_saved_project_status_payload(tmp_path) is None


def test_local_profile_hydrates_only_local_status_and_report(tmp_path: Path, monkeypatch):
    """The selected profile supplies both the status location and saved cohort."""

    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "project_status.json").write_text(
        json.dumps({"summary": {"tickers_total": 4, "tickers_with_prices": 4}}),
        encoding="utf-8",
    )
    local_outputs = tmp_path / "outputs" / "local"
    local_outputs.mkdir()
    (local_outputs / "project_status.json").write_text(
        json.dumps({"summary": {"tickers_total": 2, "tickers_with_prices": 2}}),
        encoding="utf-8",
    )
    local_report = tmp_path / "data" / "local" / "reports"
    local_report.mkdir(parents=True)
    (local_report / "ticker_readiness_report.csv").write_text(
        "ticker,price_ready,momentum_ready,fundamentals_ready,dcf_ready,peer_ready\n"
        "LOCAL,True,False,False,False,False\n",
        encoding="utf-8",
    )

    loaded = dashboard.load_saved_project_status_payload(tmp_path)

    assert loaded["coverage_populations"]["saved_readiness"]["total"] == 1
    assert loaded["coverage_populations"]["saved_readiness"]["source"] == "data/local/reports/ticker_readiness_report.csv"
    assert loaded["coverage_populations"]["saved_readiness"]["profile_key"] == "local"
    assert dict((label, value) for label, value, _ in dashboard.project_status_metric_cards(loaded))["Price Ready"] == "1/1"


def test_loader_rejects_explicit_population_from_another_profile(tmp_path: Path, monkeypatch):
    """Profile metadata cannot authorize coverage from a different profile."""

    monkeypatch.delenv("STOCK_RESEARCH_DATA_PROFILE", raising=False)
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    payload = _status_payload()
    payload["coverage_populations"]["saved_readiness"]["profile_key"] = "local"
    payload["coverage_populations"]["saved_readiness"]["data_dir"] = "data/local"
    (outputs_dir / "project_status.json").write_text(json.dumps(payload), encoding="utf-8")

    assert dashboard.load_saved_project_status_payload(tmp_path) is None


def test_loader_rehydrates_unbound_explicit_populations_from_current_report(tmp_path: Path, monkeypatch):
    """Old explicit sections without profile metadata cannot bypass current proof."""

    monkeypatch.delenv("STOCK_RESEARCH_DATA_PROFILE", raising=False)
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    (outputs_dir / "project_status.json").write_text(json.dumps(_status_payload()), encoding="utf-8")
    report_dir = tmp_path / "data" / "reports"
    report_dir.mkdir(parents=True)
    (report_dir / "ticker_readiness_report.csv").write_text(
        "ticker,price_ready,momentum_ready,fundamentals_ready,dcf_ready,peer_ready\n"
        "AAA,True,False,False,False,False\n"
        "BBB,False,False,True,False,False\n",
        encoding="utf-8",
    )

    loaded = dashboard.load_saved_project_status_payload(tmp_path)

    assert loaded["coverage_populations"]["saved_readiness"]["total"] == 2
    assert loaded["coverage_populations"]["saved_readiness"]["price_ready"] == 1
    assert loaded["coverage_populations"]["working_universe"]["status"] == "unavailable"


def test_loader_replaces_bound_saved_snapshot_with_current_report(tmp_path: Path, monkeypatch):
    """A modern status snapshot cannot keep stale saved-readiness counts."""

    monkeypatch.delenv("STOCK_RESEARCH_DATA_PROFILE", raising=False)
    data_dir = tmp_path / "data"
    report_dir = data_dir / "reports"
    report_dir.mkdir(parents=True)
    (report_dir / "ticker_readiness_report.csv").write_text(
        "ticker,price_ready,momentum_ready,fundamentals_ready,dcf_ready,peer_ready\n"
        "AAA,True,True,False,False,False\n"
        "BBB,False,False,True,False,False\n",
        encoding="utf-8",
    )
    payload = _status_payload()
    payload["profile_key"] = "default"
    payload["data_dir"] = str(data_dir)
    for population in payload["coverage_populations"].values():
        population["profile_key"] = "default"
        population["data_dir"] = str(data_dir)
    payload["coverage_populations"]["saved_readiness"].update(
        {"total": 1, "price_ready": 1, "momentum_ready": 1}
    )
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    (outputs_dir / "project_status.json").write_text(json.dumps(payload), encoding="utf-8")

    loaded = dashboard.load_saved_project_status_payload(tmp_path)

    saved = loaded["coverage_populations"]["saved_readiness"]
    working = loaded["coverage_populations"]["working_universe"]
    assert saved["status"] == "available"
    assert saved["total"] == 2
    assert saved["price_ready"] == 1
    assert saved["loaded_from_current_profile"] is True
    assert working["status"] == "available"
    assert working["total"] == 3541
    assert working["has_prices"] == 280
    assert dict((label, value) for label, value, _ in dashboard.project_status_metric_cards(loaded))["Price Ready"] == "1/2"


def test_loader_marks_bound_saved_snapshot_unavailable_when_current_report_missing(tmp_path: Path, monkeypatch):
    """Missing current saved proof cannot borrow old explicit saved counts."""

    monkeypatch.delenv("STOCK_RESEARCH_DATA_PROFILE", raising=False)
    payload = _status_payload()
    payload["profile_key"] = "default"
    payload["data_dir"] = str(tmp_path / "data")
    for population in payload["coverage_populations"].values():
        population["profile_key"] = "default"
        population["data_dir"] = str(tmp_path / "data")
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    (outputs_dir / "project_status.json").write_text(json.dumps(payload), encoding="utf-8")

    loaded = dashboard.load_saved_project_status_payload(tmp_path)

    assert loaded["coverage_populations"]["saved_readiness"]["status"] == "unavailable"
    assert loaded["coverage_populations"]["saved_readiness"]["total"] is None
    assert loaded["coverage_populations"]["working_universe"]["has_prices"] == 280


def test_loader_reconciles_stored_stage_evidence_with_current_saved_report(tmp_path: Path, monkeypatch):
    """Home stage cards cannot repeat an old peer fraction beside current metrics."""

    monkeypatch.delenv("STOCK_RESEARCH_DATA_PROFILE", raising=False)
    data_dir = tmp_path / "data"
    report_dir = data_dir / "reports"
    report_dir.mkdir(parents=True)
    (report_dir / "ticker_readiness_report.csv").write_text(
        "ticker,price_ready,momentum_ready,fundamentals_ready,dcf_ready,peer_ready\n"
        "AAA,True,True,True,True,False\n"
        "BBB,False,False,False,False,False\n",
        encoding="utf-8",
    )
    payload = _status_payload()
    payload["profile_key"] = "default"
    payload["data_dir"] = str(data_dir)
    for population in payload["coverage_populations"].values():
        population["profile_key"] = "default"
        population["data_dir"] = str(data_dir)
    payload["remaining_public_stage_rows"] = [
        {
            "Stage": "Peer readiness upgrade",
            "State": "blocked_by_data",
            "Diagnostic State": "source_review_needed",
            "Next Action": "Review peer source proof.",
            "Evidence": "Saved peer-ready: 1/2 peer-ready; stale snapshot wording.",
        },
        {
            "Stage": "Coverage depth",
            "State": "partial",
            "Diagnostic State": "price_gap_remaining",
            "Next Action": "Inspect current coverage.",
            "Evidence": "Saved readiness: price 2/2; peer 1/2; stale snapshot wording.",
        },
    ]
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    status_path = outputs_dir / "project_status.json"
    status_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = dashboard.load_saved_project_status_payload(tmp_path)
    rows = loaded["remaining_public_stage_rows"]
    cards = dashboard.project_status_remaining_stage_cards(loaded)

    assert loaded["coverage_populations"]["saved_readiness"]["peer_ready"] == 0
    assert "Saved peer-ready: 0/2" in rows[0]["Evidence"]
    assert "peer 0/2" in rows[1]["Evidence"]
    assert "1/2 peer-ready" not in " ".join(card["body"] for card in cards)
    assert rows[0]["State"] == "blocked_by_data"
    assert rows[0]["Diagnostic State"] == "source_review_needed"
    assert rows[0]["Next Action"] == "Review peer source proof."
    assert rows[1]["State"] == "partial"
    assert rows[1]["Next Action"] == "Inspect current coverage."
    assert "1/2 peer-ready" in status_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("second_row", "expected"),
    [
        (
            "BBB,True,False,True,True\n",
            {"price_ready": 2, "momentum_ready": 1, "fundamentals_ready": 1, "dcf_ready": 1, "peer_ready": None},
        ),
        (
            "BBB,True,False,True,True,not_ready\n",
            {"price_ready": 2, "momentum_ready": 1, "fundamentals_ready": 1, "dcf_ready": 1, "peer_ready": 0},
        ),
        (
            "BBB,maybe,False,False,False,False\n",
            {"price_ready": None, "momentum_ready": 1, "fundamentals_ready": 0, "dcf_ready": 0, "peer_ready": 0},
        ),
    ],
)
def test_loader_withholds_only_unverified_saved_flag_counts(
    tmp_path: Path, monkeypatch, second_row: str, expected: dict[str, int | None],
):
    """A malformed field cannot erase independently verified saved lanes."""

    monkeypatch.delenv("STOCK_RESEARCH_DATA_PROFILE", raising=False)
    report_dir = tmp_path / "data" / "reports"
    report_dir.mkdir(parents=True)
    (report_dir / "ticker_readiness_report.csv").write_text(
        "ticker,price_ready,momentum_ready,fundamentals_ready,dcf_ready,peer_ready\n"
        "AAA,True,True,False,False,False\n"
        + second_row,
        encoding="utf-8",
    )
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir()
    (outputs_dir / "project_status.json").write_text(json.dumps({"summary": {}}), encoding="utf-8")

    loaded = dashboard.load_saved_project_status_payload(tmp_path)

    saved = loaded["coverage_populations"]["saved_readiness"]
    assert saved["status"] == "available"
    assert saved["total"] == 2
    for field, value in expected.items():
        assert saved[field] == value
