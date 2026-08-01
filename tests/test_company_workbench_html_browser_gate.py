from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.company_workbench_html import (
    CompanyWorkbenchHtmlSnapshot,
    HtmlBriefAnswer,
    HtmlBriefDcfBridge,
    HtmlBriefEvidenceRow,
    HtmlBriefSafeReference,
    HtmlBriefScenario,
    HtmlBriefSection,
    HtmlBriefSensitivity,
    company_workbench_html_bytes,
)
from src.company_workbench_html_browser_gate import (
    REQUIRED_OBSERVATION_KEYS,
    evaluate_html_brief_observation,
    repository_fingerprint,
    run_company_workbench_html_browser_gate,
)


EXACT_CSP = (
    "default-src 'none'; script-src 'none'; connect-src 'none'; img-src 'none'; "
    "style-src 'unsafe-inline'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
)

ASSERTION_NAMES = {
    "observation_complete",
    "one_h1",
    "semantic_landmarks",
    "logical_headings",
    "skip_focus",
    "visible_focus",
    "tables_captioned",
    "csp_exact",
    "no_script",
    "no_event_handlers",
    "no_forms",
    "no_iframes",
    "no_remote_requests",
    "research_boundary_visible",
    "blockers_visible",
    "provenance_visible",
    "no_overflow",
    "forced_colors_non_color_cue",
    "reduced_motion_static",
    "print_boundary_visible",
    "print_provenance_visible",
    "no_console_errors",
    "no_page_errors",
    "pdf_in_memory",
}

DEPENDENT_ASSERTIONS = {
    "state": set(),
    "viewport": set(),
    "h1_count": {"one_h1"},
    "header_count": {"semantic_landmarks"},
    "main_count": {"semantic_landmarks"},
    "footer_count": {"semantic_landmarks"},
    "section_count": {"semantic_landmarks"},
    "heading_levels": {"logical_headings"},
    "skip_target_focused": {"skip_focus"},
    "visible_focus": {"visible_focus"},
    "table_count": {"tables_captioned"},
    "captioned_table_count": {"tables_captioned"},
    "csp": {"csp_exact"},
    "script_count": {"no_script"},
    "event_handler_count": {"no_event_handlers"},
    "form_count": {"no_forms"},
    "iframe_count": {"no_iframes"},
    "remote_request_count": {"no_remote_requests"},
    "boundary_visible": {"research_boundary_visible"},
    "blockers_visible": {"blockers_visible"},
    "provenance_visible": {"provenance_visible"},
    "overflow_px": {"no_overflow"},
    "forced_colors_non_color_cue": {"forced_colors_non_color_cue"},
    "reduced_motion_static": {"reduced_motion_static"},
    "print_boundary_visible": {"print_boundary_visible"},
    "print_provenance_visible": {"print_provenance_visible"},
    "console_errors": {"no_console_errors"},
    "page_errors": {"no_page_errors"},
    "pdf_byte_length": {"pdf_in_memory"},
    "pdf_header": {"pdf_in_memory"},
}


def _complete_observation() -> dict[str, object]:
    return {
        "state": "complete",
        "viewport": "1280x720",
        "h1_count": 1,
        "header_count": 1,
        "main_count": 1,
        "footer_count": 1,
        "section_count": 2,
        "heading_levels": (1, 2, 2),
        "skip_target_focused": True,
        "visible_focus": True,
        "table_count": 1,
        "captioned_table_count": 1,
        "csp": EXACT_CSP,
        "script_count": 0,
        "event_handler_count": 0,
        "form_count": 0,
        "iframe_count": 0,
        "remote_request_count": 0,
        "boundary_visible": True,
        "blockers_visible": True,
        "provenance_visible": True,
        "overflow_px": 0.0,
        "forced_colors_non_color_cue": True,
        "reduced_motion_static": True,
        "print_boundary_visible": True,
        "print_provenance_visible": True,
        "console_errors": (),
        "page_errors": (),
        "pdf_byte_length": 512,
        "pdf_header": "%PDF",
    }


def _assertion_map(observation: dict[str, object]):
    result = evaluate_html_brief_observation(observation)
    return result, {assertion.name: assertion for assertion in result.assertions}


def _synthetic_snapshot(state: str) -> CompanyWorkbenchHtmlSnapshot:
    normalized = {
        "complete": "available",
        "partial": "partial",
        "withheld": "withheld",
    }[state]
    blocker = ("Synthetic unavailable input remains withheld.",)
    bridge = HtmlBriefDcfBridge(
        state=normalized,
        enterprise_state=normalized,
        equity_state=normalized,
        per_share_state=normalized,
        explicit_total_state=normalized,
        projected_fcfs=(),
        discounted_fcfs=(),
        discounted_explicit_total=None,
        terminal_value=None,
        discounted_terminal_value=None,
        enterprise_value=None,
        cash=None,
        debt=None,
        net_debt=None,
        equity_value=None,
        shares_outstanding=None,
        shares_label="Synthetic share basis",
        share_basis_state=normalized,
        scenario_value_per_share=None,
        currency="",
        blockers=blocker,
    )
    scenarios = tuple(
        HtmlBriefScenario(
            name=name,
            state=normalized,
            modified=False,
            method_name="Synthetic test method",
            revenue_growth=None,
            fcf_margin=None,
            wacc=None,
            terminal_growth=None,
            forecast_years=None,
            bridge=bridge,
        )
        for name in ("Bear", "Base", "Bull")
    )
    section = HtmlBriefSection(
        key="synthetic",
        title="Synthetic evidence state",
        state=normalized,
        answer="Synthetic test evidence only.",
        facts=(),
        blockers=blocker,
    )
    evidence = HtmlBriefEvidenceRow(
        section="Synthetic provenance",
        state=normalized,
        source_id="synthetic-test-source",
        source_ref=HtmlBriefSafeReference("Synthetic source", ""),
        as_of="not recorded",
        retrieved_at="not recorded",
        rights_state=normalized,
        field_scope_state=normalized,
        model_identity="synthetic-model",
        input_identity="synthetic-input",
        blockers=blocker,
    )
    return CompanyWorkbenchHtmlSnapshot(
        ticker="TEST",
        profile_label="Synthetic test profile",
        review_cutoff="not recorded",
        source_as_of="not recorded",
        generated_at="not recorded",
        model_version="synthetic-test-v1",
        freshness_state=normalized,
        rights_state=normalized,
        boundary="Research-only, fail-closed portable brief; no recommendation, probability, or transaction action.",
        answers=(
            HtmlBriefAnswer(
                "Synthetic answer",
                "Synthetic answer",
                "Synthetic test answer only.",
                normalized,
                (),
            ),
        ),
        recency=section,
        readiness_lanes=(section,),
        scenarios=scenarios,
        sensitivity=HtmlBriefSensitivity(normalized, (), (), (), blocker),
        research_sections=(section,),
        decision_lanes=(section,),
        evidence_rows=(evidence,),
        blockers=blocker,
        identity=f"synthetic-{state}",
    )


def _synthetic_brief(state: str) -> bytes:
    return company_workbench_html_bytes(_synthetic_snapshot(state))


def test_evaluator_accepts_the_complete_typed_contract():
    result, assertions = _assertion_map(_complete_observation())

    assert REQUIRED_OBSERVATION_KEYS == tuple(_complete_observation())
    assert set(assertions) == ASSERTION_NAMES
    assert result.state == "complete"
    assert result.viewport == "1280x720"
    assert result.passed
    assert all(assertion.evidence for assertion in result.assertions)


@pytest.mark.parametrize(
    ("assertion_name", "changes"),
    (
        ("one_h1", {"h1_count": 2}),
        ("semantic_landmarks", {"main_count": 0}),
        ("logical_headings", {"heading_levels": (1, 3)}),
        ("skip_focus", {"skip_target_focused": False}),
        ("visible_focus", {"visible_focus": False}),
        ("tables_captioned", {"captioned_table_count": 0}),
        ("csp_exact", {"csp": "default-src 'none'"}),
        ("no_script", {"script_count": 1}),
        ("no_event_handlers", {"event_handler_count": 1}),
        ("no_forms", {"form_count": 1}),
        ("no_iframes", {"iframe_count": 1}),
        ("no_remote_requests", {"remote_request_count": 1}),
        ("research_boundary_visible", {"boundary_visible": False}),
        ("blockers_visible", {"blockers_visible": False}),
        ("provenance_visible", {"provenance_visible": False}),
        ("no_overflow", {"overflow_px": 1.01}),
        ("forced_colors_non_color_cue", {"forced_colors_non_color_cue": False}),
        ("reduced_motion_static", {"reduced_motion_static": False}),
        ("print_boundary_visible", {"print_boundary_visible": False}),
        ("print_provenance_visible", {"print_provenance_visible": False}),
        ("no_console_errors", {"console_errors": ("console failed",)}),
        ("no_page_errors", {"page_errors": ("page failed",)}),
        ("pdf_in_memory", {"pdf_header": "not-pdf"}),
        ("pdf_in_memory", {"pdf_byte_length": 0}),
    ),
)
def test_each_observed_defect_fails_its_named_assertion(assertion_name, changes):
    observation = _complete_observation()
    observation.update(changes)

    result, assertions = _assertion_map(observation)

    assert not result.passed
    assert not assertions[assertion_name].passed


@pytest.mark.parametrize("missing_key", tuple(_complete_observation()))
def test_each_missing_observation_fails_closed(missing_key):
    observation = _complete_observation()
    del observation[missing_key]

    result, assertions = _assertion_map(observation)

    assert not result.passed
    assert not assertions["observation_complete"].passed
    assert all(
        not assertions[name].passed for name in DEPENDENT_ASSERTIONS[missing_key]
    )


@pytest.mark.parametrize(
    ("key", "wrong_value"),
    (
        ("state", 1),
        ("viewport", None),
        ("h1_count", True),
        ("header_count", 1.0),
        ("main_count", "1"),
        ("footer_count", False),
        ("section_count", 2.0),
        ("heading_levels", [1, 2]),
        ("skip_target_focused", 1),
        ("visible_focus", "yes"),
        ("table_count", True),
        ("captioned_table_count", 1.0),
        ("csp", None),
        ("script_count", False),
        ("event_handler_count", 0.0),
        ("form_count", "0"),
        ("iframe_count", None),
        ("remote_request_count", False),
        ("boundary_visible", 1),
        ("blockers_visible", "true"),
        ("provenance_visible", None),
        ("overflow_px", 0),
        ("forced_colors_non_color_cue", 1),
        ("reduced_motion_static", "true"),
        ("print_boundary_visible", 1),
        ("print_provenance_visible", None),
        ("console_errors", []),
        ("page_errors", (1,)),
        ("pdf_byte_length", True),
        ("pdf_header", b"%PDF"),
    ),
)
def test_each_wrong_typed_observation_fails_closed(key, wrong_value):
    observation = _complete_observation()
    observation[key] = wrong_value

    result, assertions = _assertion_map(observation)

    assert not result.passed
    assert not assertions["observation_complete"].passed
    assert all(not assertions[name].passed for name in DEPENDENT_ASSERTIONS[key])


def test_repository_fingerprint_detects_tracked_untracked_delete_and_rename(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("first", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
    initial = repository_fingerprint(tmp_path)

    tracked.write_text("second", encoding="utf-8")
    tracked_changed = repository_fingerprint(tmp_path)
    assert tracked_changed != initial

    untracked = tmp_path / "visible.txt"
    untracked.write_text("one", encoding="utf-8")
    untracked_added = repository_fingerprint(tmp_path)
    assert untracked_added != tracked_changed
    untracked.write_text("two", encoding="utf-8")
    untracked_changed = repository_fingerprint(tmp_path)
    assert untracked_changed != untracked_added

    tracked.unlink()
    deleted = repository_fingerprint(tmp_path)
    assert deleted != untracked_changed

    untracked.rename(tmp_path / "renamed.txt")
    renamed = repository_fingerprint(tmp_path)
    assert renamed != deleted


def test_repository_fingerprint_hashes_link_type_and_target(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "target-a").write_text("same", encoding="utf-8")
    (tmp_path / "target-b").write_text("same", encoding="utf-8")
    link = tmp_path / "visible-link"
    link.symlink_to("target-a")
    before = repository_fingerprint(tmp_path)

    link.unlink()
    link.symlink_to("target-b")

    assert repository_fingerprint(tmp_path) != before


def test_actual_browser_matrix_accepts_injected_bytes_without_writing_repo():
    cases = {
        state: _synthetic_brief(state) for state in ("complete", "partial", "withheld")
    }

    results = run_company_workbench_html_browser_gate(cases, repo_root=Path.cwd())

    assert len(results) == 9
    assert {(result.state, result.viewport) for result in results} == {
        (state, viewport)
        for state in cases
        for viewport in ("1280x720", "390x844", "640x900")
    }
    assert all(result.passed for result in results), [
        (result.state, result.viewport, [a for a in result.assertions if not a.passed])
        for result in results
        if not result.passed
    ]


def test_make_target_runs_only_the_browser_gate_without_artifact_options():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    target = makefile.split("company-workbench-html-browser-check:", 1)[1].split(
        "\n\n", 1
    )[0]

    assert "PYTHONDONTWRITEBYTECODE=1" in target
    assert (
        "python3 -m pytest tests/test_company_workbench_html_browser_gate.py -q"
        in target
    )
    assert "tests/test_company_workbench_html_browser_gate.py tests/" not in target
    assert not any(
        option in target
        for option in ("--output", "--screenshot", "--json", "--html", "--pdf")
    )
