from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_default_performance_contract_covers_the_guided_public_workflow():
    from src.public_performance_gate import DEFAULT_ROUTE_SPECS, DEFAULT_VIEWPORTS

    assert [route.name for route in DEFAULT_ROUTE_SPECS] == [
        "Home",
        "Stock Selector",
        "Single-Stock Report",
        "Data Health",
        "Proof History",
    ]
    assert [route.critical for route in DEFAULT_ROUTE_SPECS] == [False, True, True, True, False]
    assert [(viewport.width, viewport.height) for viewport in DEFAULT_VIEWPORTS] == [
        (1280, 720),
        (390, 844),
    ]
    assert all(route.first_useful_marker for route in DEFAULT_ROUTE_SPECS)
    assert all(route.full_markers for route in DEFAULT_ROUTE_SPECS)


def test_research_performance_contract_covers_the_commercial_beta_workflow():
    from src.public_performance_gate import RESEARCH_ROUTE_SPECS

    assert [route.name for route in RESEARCH_ROUTE_SPECS] == [
        "Research Desk",
        "Discover",
        "Company Workbench",
        "Monitor",
    ]
    assert all(route.critical for route in RESEARCH_ROUTE_SPECS)
    assert RESEARCH_ROUTE_SPECS[0].first_useful_marker == "Weekly research summary"
    assert RESEARCH_ROUTE_SPECS[0].full_markers == (
        "Weekly research summary",
        "What should I review next?",
        "Open Discover",
        "Advanced Evidence",
        "Research-only",
    )
    assert RESEARCH_ROUTE_SPECS[1].first_useful_marker == "Which stock can I review?"
    assert RESEARCH_ROUTE_SPECS[1].full_markers == (
        "Discover",
        "Search this review queue",
        "Advanced: cohort readiness context",
        "Research-only",
    )
    assert RESEARCH_ROUTE_SPECS[2].full_markers == (
        "Company Workbench",
        "Advanced: selected-company lane coverage",
        "What Changed",
        "Research Decision Lab",
        "Business Trend",
        "Valuation",
        "Forward View",
        "What Remains Withheld",
        "Research Conclusion",
        "Next Research Task",
        "Research-only",
    )
    assert RESEARCH_ROUTE_SPECS[3].first_useful_marker == "WEEKLY RESEARCH SUMMARY"
    assert RESEARCH_ROUTE_SPECS[3].full_markers == (
        "WEEKLY RESEARCH SUMMARY",
        "Research Discipline Review",
        "Research change monitor",
        "No unresolved evidence change is queued.",
        "Open Discover",
        "Advanced: five-company Earnings Nowcast readiness",
        "Research-only",
    )
    assert RESEARCH_ROUTE_SPECS[2].route == "/?mode=research&page=company-workbench&ticker=NVDA&open=1"
    assert RESEARCH_ROUTE_SPECS[2].first_useful_marker == "USE NOW"
    assert "Selected Company" not in RESEARCH_ROUTE_SPECS[2].full_markers
    assert "Forward View" in RESEARCH_ROUTE_SPECS[2].full_markers
    assert "What Remains Withheld" in RESEARCH_ROUTE_SPECS[2].full_markers
    assert RESEARCH_ROUTE_SPECS[3].full_markers[0] == "WEEKLY RESEARCH SUMMARY"


def test_nearest_rank_percentile_does_not_select_the_best_run():
    from src.public_performance_gate import nearest_rank_percentile

    assert nearest_rank_percentile([1.0, 2.0, 3.0, 4.0, 9.0], 90) == 9.0
    assert nearest_rank_percentile([4.0, 1.0, 3.0, 2.0], 50) == 2.0

    with pytest.raises(ValueError, match="at least one"):
        nearest_rank_percentile([], 90)


def test_performance_summary_and_gate_keep_cold_warm_and_failure_truth_separate():
    from src.public_performance_gate import (
        PerformanceThresholds,
        RouteTimingSample,
        evaluate_performance_gate,
        summarize_route_timings,
    )

    samples = [
        RouteTimingSample("Stock Selector", "1280x720", "cold", 0.4, 2.4, 8.0, True),
        RouteTimingSample("Stock Selector", "1280x720", "warm", 0.3, 1.8, 3.0, True),
        RouteTimingSample("Stock Selector", "1280x720", "warm", 0.4, 2.0, 4.0, True),
        RouteTimingSample("Stock Selector", "1280x720", "warm", 0.5, 2.2, 6.0, True),
        RouteTimingSample("Data Health", "390x844", "cold", None, None, None, False, "timeout"),
    ]

    summary = summarize_route_timings(samples)
    selector = next(row for row in summary if row["route"] == "Stock Selector")
    data_health = next(row for row in summary if row["route"] == "Data Health")

    assert selector["warm_full_settle_p90_seconds"] == 6.0
    assert selector["cold_full_settle_max_seconds"] == 8.0
    assert selector["success"] is True
    assert data_health["success"] is False
    assert data_health["failure_count"] == 1

    result = evaluate_performance_gate(
        summary,
        critical_routes={"Stock Selector", "Data Health"},
        thresholds=PerformanceThresholds(),
    )
    assert result.verdict == "failed"
    assert "Stock Selector: warm full-settle p90 6.000s exceeds 5.000s" in result.failures
    assert "Data Health: 1 failed timing run(s)" in result.failures


def test_performance_gate_fails_closed_when_required_samples_are_missing():
    from src.public_performance_gate import (
        PerformanceThresholds,
        RouteTimingSample,
        evaluate_performance_gate,
        summarize_route_timings,
    )

    summary = summarize_route_timings(
        [RouteTimingSample("Company Workbench", "390x844", "cold", 0.2, 1.2, 3.0, True)]
    )

    result = evaluate_performance_gate(
        summary,
        critical_routes={"Company Workbench"},
        thresholds=PerformanceThresholds(),
        min_cold_runs=1,
        min_warm_runs=5,
    )

    assert result.verdict == "failed"
    assert "Company Workbench: warm sample count 0 is below 5" in result.failures


def test_demo_snapshot_identity_uses_the_tracked_manifest_hashes(tmp_path):
    from src.public_performance_gate import demo_snapshot_identity

    manifest = tmp_path / "data" / "demo" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "files": {
                    "prices.csv": {"sha256": "bbb", "row_count": 20},
                    "fundamentals.csv": {"sha256": "aaa", "row_count": 10},
                }
            }
        ),
        encoding="utf-8",
    )

    identity = demo_snapshot_identity(tmp_path)

    assert identity["manifest_path"] == "data/demo/manifest.json"
    assert identity["file_count"] == 2
    assert identity["row_count"] == 30
    assert len(identity["sha256"]) == 64


def test_contract_payload_is_read_only_research_safe_and_browser_explicit(tmp_path):
    from src.public_performance_gate import RESEARCH_ROUTE_SPECS, performance_contract_payload

    manifest = tmp_path / "data" / "demo" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"files": {}}), encoding="utf-8")

    payload = performance_contract_payload(
        tmp_path,
        route_specs=RESEARCH_ROUTE_SPECS,
        workflow="research",
    )
    rendered = json.dumps(payload).lower()

    assert payload["mode"] == "contract_only"
    assert payload["workflow"] == "research"
    assert [row["name"] for row in payload["routes"]] == [
        "Research Desk",
        "Discover",
        "Company Workbench",
        "Monitor",
    ]
    assert payload["browser_requirement"] == "playwright plus a local chrome-compatible executable"
    assert payload["thresholds"]["warm_full_settle_seconds"] == 5.0
    assert payload["thresholds"]["cold_full_settle_seconds"] == 10.0
    assert "does not refresh data" in rendered
    assert "investment advice" in rendered
    assert "auto-trading" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_makefile_exposes_contract_and_real_browser_performance_commands():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "public-performance-contract:" in makefile
    assert "public-performance-gate:" in makefile
    assert "python3 -m src.public_performance_gate --contract" in makefile
    assert "python3 -m src.public_performance_gate --browser" in makefile
    assert "commercial-beta-performance-contract:" in makefile
    assert "commercial-beta-performance-gate:" in makefile
    assert "--workflow research --contract" in makefile
    assert "--workflow research --browser" in makefile


def test_find_chrome_executable_uses_only_an_executable_candidate(tmp_path):
    from src.public_performance_gate import find_chrome_executable

    missing = tmp_path / "missing-chrome"
    available = tmp_path / "chrome"
    available.write_text("browser", encoding="utf-8")
    available.chmod(0o755)

    assert find_chrome_executable((missing, available)) == available
    assert find_chrome_executable((missing,)) is None


def test_performance_result_payload_includes_commit_snapshot_samples_and_gate(tmp_path):
    from src.public_performance_gate import RouteTimingSample, performance_result_payload

    manifest = tmp_path / "data" / "demo" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"files": {}}), encoding="utf-8")
    samples = [
        RouteTimingSample("Stock Selector", "1280x720", "cold", 0.2, 1.2, 4.0, True),
        RouteTimingSample("Stock Selector", "1280x720", "warm", 0.2, 1.0, 2.0, True),
    ]

    payload = performance_result_payload(
        tmp_path,
        samples,
        commit="abc123",
        environment="test chrome",
        critical_routes={"Stock Selector"},
    )

    assert payload["mode"] == "browser"
    assert payload["verdict"] == "passed"
    assert payload["commit"] == "abc123"
    assert payload["environment"] == "test chrome"
    assert payload["demo_snapshot"]["sha256"]
    assert payload["samples"][0]["run_kind"] == "cold"
    assert payload["summary"][0]["warm_full_settle_p90_seconds"] == 2.0
    assert payload["failures"] == []


def test_pyproject_keeps_browser_runner_in_development_dependencies_only():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    requirements = Path("requirements.txt").read_text(encoding="utf-8")

    assert '"playwright>=1.52"' in pyproject
    assert "playwright" not in requirements.lower()


def test_visible_text_wait_uses_rendered_body_text_instead_of_hidden_duplicate_locators():
    from src.public_performance_gate import _wait_for_visible_text

    calls = []

    class FakePage:
        def wait_for_function(self, expression, *, arg, timeout):
            calls.append((expression, arg, timeout))

    _wait_for_visible_text(FakePage(), "Stock Selector", timeout_seconds=7.5)

    expression, marker, timeout = calls[0]
    assert "document.body.innerText.includes(marker)" in expression
    assert marker == "Stock Selector"
    assert timeout == 7500


def test_visible_text_wait_names_the_missing_marker_on_timeout():
    from src.public_performance_gate import _wait_for_visible_text

    class FailingPage:
        def wait_for_function(self, expression, *, arg, timeout):
            raise RuntimeError("browser timeout")

    with pytest.raises(TimeoutError, match="USE NOW"):
        _wait_for_visible_text(FailingPage(), "USE NOW", timeout_seconds=3)


def test_horizontal_overflow_check_uses_document_widths():
    from src.public_performance_gate import _horizontal_overflow_pixels

    class FakePage:
        def evaluate(self, expression):
            assert "scrollWidth" in expression
            assert "clientWidth" in expression
            return 14

    assert _horizontal_overflow_pixels(FakePage()) == 14


def test_reviewed_performance_baseline_documents_reproducible_evidence_boundary():
    readme = Path("README.md").read_text(encoding="utf-8")
    baseline = Path("docs/PERFORMANCE_RELEASE_GATE.md").read_text(encoding="utf-8")

    assert "[Performance Release Gate](docs/PERFORMANCE_RELEASE_GATE.md)" in readme
    assert "fb86bd3edef72a1e35064ecc03ca8e7fb63ec34a" in baseline
    assert "4f6f28d3a6b2df3c3c459fad325d75e2f2ee45dc398616e3c638ead91819549d" in baseline
    assert "2026-07-14" in baseline
    assert "1280x720" in baseline
    assert "390x844" in baseline
    assert "make public-performance-gate" in baseline
    assert "/tmp/stock-command-center-public-performance.json" in baseline
    assert "60 recorded route samples" in baseline
    assert "product performance evidence only" in baseline.lower()
    assert "not data-freshness proof" in baseline.lower()
    assert "make commercial-beta-performance-contract" in baseline
    assert "make commercial-beta-performance-gate" in baseline
    assert "e930bd0e1b1062c029a7633a226db8dbc03a506b" in baseline
    assert "48 recorded route samples" in baseline
    assert "Company Workbench" in baseline
    assert "Research Desk" in baseline


def test_performance_progress_line_shows_route_viewport_run_and_outcome():
    from src.public_performance_gate import RouteTimingSample, performance_progress_line

    passed = RouteTimingSample("Data Health", "390x844", "warm", 0.2, 1.4, 2.5, True)
    failed = RouteTimingSample("Stock Selector", "1280x720", "cold", 0.3, None, None, False, "timeout")

    assert performance_progress_line(passed, index=4, total=60) == (
        "[4/60] Data Health 390x844 warm: passed; first=1.400s; full=2.500s"
    )
    assert performance_progress_line(failed, index=5, total=60) == (
        "[5/60] Stock Selector 1280x720 cold: failed; timeout"
    )


def test_performance_result_never_passes_without_browser_samples(tmp_path):
    from src.public_performance_gate import performance_result_payload

    manifest = tmp_path / "data" / "demo" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"files": {}}), encoding="utf-8")

    payload = performance_result_payload(
        tmp_path,
        [],
        commit="abc123",
        environment="test chrome",
        critical_routes={"Stock Selector"},
    )

    assert payload["verdict"] == "failed"
    assert payload["failures"] == ["No browser timing samples were recorded"]
