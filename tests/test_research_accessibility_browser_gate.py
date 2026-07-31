from __future__ import annotations

from pathlib import Path
import subprocess


def test_forced_colors_observation_fails_closed_for_each_required_signal():
    from src.research_accessibility_browser_gate import (
        evaluate_forced_colors_observation,
    )

    passing = {
        "media_active": True,
        "skip_count": 1,
        "skip_focused": True,
        "skip_outline_style": "solid",
        "skip_outline_width_px": 3.0,
        "current_route_count": 1,
        "current_route_value": "page",
        "current_route_marker_width_px": 2.0,
        "boundary_count": 1,
        "boundary_visible": True,
        "boundary_border_width_px": 1.0,
        "heading_visible": True,
        "boundary_text_visible": True,
        "overflow_px": 0.0,
        "traceback_visible": False,
    }
    assertions = evaluate_forced_colors_observation(passing, primary_route=True)
    assert assertions and all(item["passed"] for item in assertions)

    mutations = (
        ("forced_colors_media_active", {"media_active": False}),
        ("forced_colors_skip_focus", {"skip_focused": False}),
        ("forced_colors_focus_outline", {"skip_outline_width_px": 0.0}),
        ("forced_colors_current_route", {"current_route_value": ""}),
        ("forced_colors_current_route_marker", {"current_route_marker_width_px": 0.0}),
        ("forced_colors_boundary", {"boundary_visible": False}),
        ("forced_colors_boundary_border", {"boundary_border_width_px": 0.0}),
        ("forced_colors_required_text", {"heading_visible": False}),
        ("forced_colors_no_overflow", {"overflow_px": 2.0}),
        ("forced_colors_no_traceback", {"traceback_visible": True}),
    )
    for name, changed in mutations:
        failed = evaluate_forced_colors_observation(
            {**passing, **changed},
            primary_route=True,
        )
        assert next(item for item in failed if item["name"] == name)["passed"] is False

    secondary = evaluate_forced_colors_observation(
        {
            **passing,
            "current_route_count": 0,
            "current_route_value": "",
            "current_route_marker_width_px": 0.0,
        },
        primary_route=False,
    )
    assert all(item["passed"] for item in secondary)


def test_reduced_motion_observation_fails_closed_for_each_required_signal():
    from src.research_accessibility_browser_gate import (
        evaluate_reduced_motion_observation,
    )

    passing = {
        "media_active": True,
        "target_count": 3,
        "max_animation_duration_ms": 0.01,
        "max_transition_duration_ms": 0.01,
        "max_animation_iterations": 1.0,
        "scroll_behavior": "auto",
        "heading_visible": True,
        "boundary_visible": True,
        "overflow_px": 0.0,
        "traceback_visible": False,
    }
    assertions = evaluate_reduced_motion_observation(passing)
    assert assertions and all(item["passed"] for item in assertions)

    mutations = (
        ("reduced_motion_media_active", {"media_active": False}),
        ("reduced_motion_targets", {"target_count": 0}),
        ("reduced_motion_animation_duration", {"max_animation_duration_ms": 250.0}),
        ("reduced_motion_transition_duration", {"max_transition_duration_ms": 250.0}),
        ("reduced_motion_animation_iterations", {"max_animation_iterations": 2.0}),
        ("reduced_motion_scroll_behavior", {"scroll_behavior": "smooth"}),
        ("reduced_motion_required_text", {"boundary_visible": False}),
        ("reduced_motion_no_overflow", {"overflow_px": 2.0}),
        ("reduced_motion_no_traceback", {"traceback_visible": True}),
    )
    for name, changed in mutations:
        failed = evaluate_reduced_motion_observation({**passing, **changed})
        assert next(item for item in failed if item["name"] == name)["passed"] is False


def test_accessibility_browser_gate_covers_both_viewports_and_all_six_research_routes():
    from src.research_accessibility_browser_gate import RESEARCH_ROUTES, VIEWPORTS

    assert VIEWPORTS == ((1280, 720), (390, 844))
    assert [route.name for route in RESEARCH_ROUTES] == [
        "Research Desk",
        "Discover",
        "Company Workbench",
        "Monitor",
        "Research Data Health",
        "Research Proof History",
    ]
    assert [
        (
            route.route,
            route.marker,
            route.expected_h1,
            route.requires_primary_navigation,
        )
        for route in RESEARCH_ROUTES
    ] == [
        (
            "/?mode=research&page=research-desk",
            "Weekly research summary",
            "Research Desk",
            True,
        ),
        (
            "/?mode=research&page=discover",
            "Which stock can I review?",
            "Discover",
            True,
        ),
        (
            "/?mode=research&page=company-workbench&ticker=NVDA&open=1",
            "Company Workbench",
            "Company Workbench",
            True,
        ),
        (
            "/?mode=research&page=monitor",
            "WEEKLY RESEARCH SUMMARY",
            "Monitor",
            True,
        ),
        (
            "/?mode=research&page=data-health&ticker=NVDA",
            "Data Health",
            "Data Health",
            False,
        ),
        (
            "/?mode=research&page=proof-history&ticker=NVDA",
            "Proof History",
            "Proof History",
            False,
        ),
    ]


def test_semantic_main_landmark_contract_requires_exact_unique_dom_state():
    from src.research_accessibility_browser_gate import (
        evaluate_semantic_main_landmark,
    )

    passed = evaluate_semantic_main_landmark(
        main_count=1,
        main_role="main",
        main_id="research-main",
        main_label="Stock research workspace",
        answer_count=1,
        h1_count=1,
        bridge_status="applied",
        phase="initial",
    )
    duplicate = evaluate_semantic_main_landmark(
        main_count=2,
        main_role="main",
        main_id="research-main",
        main_label="Stock research workspace",
        answer_count=1,
        h1_count=1,
        bridge_status="ambiguous",
        phase="rerender",
    )

    assert all(assertion["passed"] for assertion in passed)
    assert [assertion["name"] for assertion in passed] == [
        "semantic_main_initial_unique",
        "semantic_main_initial_metadata",
        "semantic_main_initial_answer",
        "semantic_main_initial_h1",
        "semantic_main_initial_bridge_status",
    ]
    assert all(assertion["passed"] is False for assertion in duplicate)


def test_skip_target_containment_requires_the_focused_target_inside_unique_main():
    from src.research_accessibility_browser_gate import (
        evaluate_skip_target_containment,
    )

    passed = evaluate_skip_target_containment(
        main_count=1,
        target_count=1,
        active_id="public-page-answer",
        target_inside_main=True,
    )
    outside = evaluate_skip_target_containment(
        main_count=1,
        target_count=1,
        active_id="public-page-answer",
        target_inside_main=False,
    )
    duplicate_main = evaluate_skip_target_containment(
        main_count=2,
        target_count=1,
        active_id="public-page-answer",
        target_inside_main=True,
    )

    assert passed["passed"] is True
    assert outside["passed"] is False
    assert duplicate_main["passed"] is False


def test_browser_error_contract_rejects_console_and_page_errors():
    from src.research_accessibility_browser_gate import evaluate_browser_errors

    assert evaluate_browser_errors([])["passed"] is True
    failed = evaluate_browser_errors(
        ["console error: bridge failed", "page error: unhandled exception"]
    )
    assert failed["passed"] is False
    assert "bridge failed" in str(failed["detail"])
    assert "unhandled exception" in str(failed["detail"])


def test_bridge_transport_contract_exposes_zero_footprint_result_fields():
    from src.research_accessibility_browser_gate import evaluate_bridge_transport

    passed = evaluate_bridge_transport(
        runtime_messages=("console info: Streamlit app ready",),
        bridge_iframe_count=0,
        bridge_focusable_count=0,
        bridge_heights=(0.0, 0.0),
    )

    assert passed["passed"] is True
    assert passed["deprecated_component_warning_count"] == 0
    assert passed["bridge_iframe_count"] == 0
    assert passed["bridge_focusable_count"] == 0
    assert passed["bridge_height"] == 0
    assert all(assertion["passed"] for assertion in passed["assertions"])


def test_bridge_transport_contract_fails_closed_for_each_legacy_or_visible_signal():
    from src.research_accessibility_browser_gate import evaluate_bridge_transport

    cases = (
        (
            {"runtime_messages": ("st.components.v1.html is deprecated",)},
            "deprecated_component_warning_count",
        ),
        ({"bridge_iframe_count": 1}, "bridge_iframe_count"),
        ({"bridge_focusable_count": 1}, "bridge_focusable_count"),
        ({"bridge_heights": (0.0, 1.25)}, "bridge_height"),
    )
    defaults = {
        "runtime_messages": (),
        "bridge_iframe_count": 0,
        "bridge_focusable_count": 0,
        "bridge_heights": (0.0,),
    }

    for changed, failed_field in cases:
        failed = evaluate_bridge_transport(**{**defaults, **changed})
        assert failed["passed"] is False
        assert failed[failed_field] > 0
        assert next(
            assertion
            for assertion in failed["assertions"]
            if assertion["name"] == failed_field
        )["passed"] is False


def test_bridge_transport_contract_rejects_non_integer_dom_counts_without_coercion():
    from src.research_accessibility_browser_gate import evaluate_bridge_transport

    defaults = {
        "runtime_messages": (),
        "bridge_iframe_count": 0,
        "bridge_focusable_count": 0,
        "bridge_heights": (0.0,),
    }
    for field in ("bridge_iframe_count", "bridge_focusable_count"):
        for malformed in (False, True, 0.5, -1, "0"):
            failed = evaluate_bridge_transport(
                **{**defaults, field: malformed}
            )
            assert failed["passed"] is False
            assert failed[field] == -1


def test_server_runtime_output_contract_fails_on_warning_or_unavailable_capture():
    from src.research_accessibility_browser_gate import (
        evaluate_server_runtime_output,
    )

    clean = evaluate_server_runtime_output(
        capture_status="captured_local_server",
        runtime_messages=("Streamlit server started",),
    )
    warned = evaluate_server_runtime_output(
        capture_status="captured_local_server",
        runtime_messages=("st.components.v1.html is deprecated",),
    )
    external = evaluate_server_runtime_output(
        capture_status="unavailable_external_base_url",
        runtime_messages=(),
    )

    assert clean["passed"] is True
    assert clean["deprecated_component_warning_count"] == 0
    assert warned["passed"] is False
    assert warned["deprecated_component_warning_count"] == 1
    assert external["passed"] is False
    assert external["deprecated_component_warning_count"] is None
    assert "unavailable" in str(external["detail"]).lower()


def test_local_server_context_captures_bounded_stdout_and_stderr(monkeypatch, tmp_path):
    import src.research_accessibility_browser_gate as gate

    class FakeOutput:
        def __init__(self):
            self.close_calls = 0

        def __iter__(self):
            return iter(
                (
                    "server ready\n",
                    "st.components.v1.html is deprecated\n",
                )
            )

        def close(self):
            self.close_calls += 1

    class FakeProcess:
        def __init__(self):
            self.stdout = FakeOutput()

        def terminate(self):
            return None

        def wait(self, timeout):
            return 0

        def kill(self):
            return None

    monkeypatch.setattr(gate, "_free_port", lambda: 43123)
    monkeypatch.setattr(gate, "_wait_for_health", lambda *args, **kwargs: None)
    process = FakeProcess()
    monkeypatch.setattr(gate.subprocess, "Popen", lambda *args, **kwargs: process)

    with gate._captured_local_demo_server(
        tmp_path,
        timeout_seconds=5,
    ) as server:
        assert server.base_url == "http://127.0.0.1:43123"

    assert tuple(server.runtime_messages) == (
        "server ready",
        "st.components.v1.html is deprecated",
    )
    assert server.capture_status == "captured_local_server"
    assert process.stdout.close_calls == 1


def test_bounded_server_capture_retains_warning_count_after_early_line_eviction():
    from collections import deque

    from src.research_accessibility_browser_gate import (
        MAX_SERVER_RUNTIME_LINES,
        RuntimeServerEvidence,
        evaluate_server_runtime_output,
    )

    server = RuntimeServerEvidence(
        base_url="http://127.0.0.1:43123",
        runtime_messages=deque(maxlen=MAX_SERVER_RUNTIME_LINES),
        capture_status="captured_local_server",
    )
    server.append("st.components.v1.html is deprecated")
    for index in range(MAX_SERVER_RUNTIME_LINES + 1):
        server.append(f"clean server line {index}")

    assert all(
        "st.components.v1.html" not in line
        for line in server.snapshot()
    )
    assert server.total_line_count == MAX_SERVER_RUNTIME_LINES + 2
    assert server.truncated_line_count == 2
    evidence = evaluate_server_runtime_output(
        capture_status=server.capture_status,
        runtime_messages=server.snapshot(),
        deprecated_component_warning_count=server.deprecated_warning_count(),
    )
    assert evidence["passed"] is False
    assert evidence["deprecated_component_warning_count"] == 1


def test_server_warning_count_inspects_full_line_before_storage_truncation():
    from collections import deque

    from src.research_accessibility_browser_gate import (
        MAX_SERVER_RUNTIME_LINE_LENGTH,
        MAX_SERVER_RUNTIME_LINES,
        RuntimeServerEvidence,
    )

    server = RuntimeServerEvidence(
        base_url="http://127.0.0.1:43123",
        runtime_messages=deque(maxlen=MAX_SERVER_RUNTIME_LINES),
        capture_status="captured_local_server",
    )
    server.append(
        ("x" * MAX_SERVER_RUNTIME_LINE_LENGTH)
        + " st.components.v1.html is deprecated"
    )

    assert len(server.snapshot()[0]) == MAX_SERVER_RUNTIME_LINE_LENGTH
    assert "st.components.v1.html" not in server.snapshot()[0]
    assert server.deprecated_warning_count() == 1


def test_server_reader_exception_marks_capture_failed_closed(monkeypatch, tmp_path):
    import src.research_accessibility_browser_gate as gate

    class ExplodingOutput:
        def __init__(self):
            self.close_calls = 0

        def __iter__(self):
            raise UnicodeDecodeError("utf-8", b"x", 0, 1, "invalid")

        def close(self):
            self.close_calls += 1

    class FakeProcess:
        def __init__(self):
            self.stdout = ExplodingOutput()

        def terminate(self):
            return None

        def wait(self, timeout):
            return 0

        def kill(self):
            return None

    monkeypatch.setattr(gate, "_free_port", lambda: 43123)
    monkeypatch.setattr(gate, "_wait_for_health", lambda *args, **kwargs: None)
    process = FakeProcess()
    monkeypatch.setattr(gate.subprocess, "Popen", lambda *args, **kwargs: process)

    with gate._captured_local_demo_server(
        tmp_path,
        timeout_seconds=5,
    ) as server:
        pass

    assert server.capture_status == "failed_reader_exception"
    assert process.stdout.close_calls == 1
    assert gate.evaluate_server_runtime_output(
        capture_status=server.capture_status,
        runtime_messages=server.snapshot(),
        deprecated_component_warning_count=server.deprecated_warning_count(),
    )["passed"] is False


def test_server_reader_join_timeout_marks_capture_incomplete(monkeypatch, tmp_path):
    import src.research_accessibility_browser_gate as gate

    class FakeOutput:
        def __init__(self):
            self.close_calls = 0

        def close(self):
            self.close_calls += 1

    class FakeProcess:
        def __init__(self):
            self.stdout = FakeOutput()

        def terminate(self):
            return None

        def wait(self, timeout):
            return 0

        def kill(self):
            return None

    class NeverFinishesThread:
        def __init__(self, **kwargs):
            self.target = kwargs["target"]

        def start(self):
            return None

        def join(self, timeout):
            assert timeout == 5

        def is_alive(self):
            return True

    monkeypatch.setattr(gate, "_free_port", lambda: 43123)
    monkeypatch.setattr(gate, "_wait_for_health", lambda *args, **kwargs: None)
    process = FakeProcess()
    monkeypatch.setattr(gate.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(gate.threading, "Thread", NeverFinishesThread)

    with gate._captured_local_demo_server(
        tmp_path,
        timeout_seconds=5,
    ) as server:
        pass

    assert server.capture_status == "incomplete_reader_shutdown"
    assert process.stdout.close_calls == 0
    assert gate.evaluate_server_runtime_output(
        capture_status=server.capture_status,
        runtime_messages=server.snapshot(),
        deprecated_component_warning_count=server.deprecated_warning_count(),
    )["passed"] is False


def test_bridge_transport_observation_measures_only_fixed_accessibility_bridges():
    from src.research_accessibility_browser_gate import (
        _bridge_transport_observation,
    )

    class FakePage:
        def evaluate(self, script):
            assert '[data-testid="stHtml"]' in script
            assert "__stockResearchMainObserver" in script
            assert "data-research-authoring-error-owned" in script
            assert "iframe" in script
            assert "getBoundingClientRect" in script
            assert "tabindex" in script
            return {
                "bridge_iframe_count": 0,
                "bridge_focusable_count": 0,
                "bridge_heights": [0, 0],
            }

    observed = _bridge_transport_observation(
        FakePage(),
        runtime_messages=("console info: ready",),
    )

    assert observed["passed"] is True
    assert observed["deprecated_component_warning_count"] == 0
    assert observed["bridge_iframe_count"] == 0
    assert observed["bridge_focusable_count"] == 0
    assert observed["bridge_height"] == 0


def test_route_result_includes_fail_closed_bridge_transport_fields(monkeypatch):
    import src.research_accessibility_browser_gate as gate

    class FakePage:
        url = "http://127.0.0.1:8501/?mode=research&page=data-health&ticker=NVDA"

        def on(self, event, handler):
            assert event in {"console", "pageerror"}

        def goto(self, url, *, wait_until, timeout):
            self.url = url

    class FakeContext:
        def __init__(self):
            self.page = FakePage()

        def new_page(self):
            return self.page

        def close(self):
            return None

    class FakeBrowser:
        def new_context(self, *, viewport):
            assert viewport == {"width": 390, "height": 844}
            return FakeContext()

    monkeypatch.setattr(gate, "_wait_for_visible_text", lambda *args, **kwargs: None)
    monkeypatch.setattr(gate, "_wait_for_dom_stability", lambda *args, **kwargs: None)
    monkeypatch.setattr(gate, "_wait_for_route_heading", lambda *args, **kwargs: None)
    monkeypatch.setattr(gate, "_semantic_main_assertions", lambda *args, **kwargs: [])
    monkeypatch.setattr(gate, "_runtime_dom_assertions", lambda *args, **kwargs: [])
    monkeypatch.setattr(gate, "_skip_link_assertions", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        gate, "_same_document_streamlit_rerun_assertions", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        gate,
        "_secondary_navigation_absence_assertion",
        lambda *args, **kwargs: {
            "name": "secondary_navigation_absent",
            "passed": True,
            "detail": "absent",
        },
    )
    monkeypatch.setattr(gate, "_navigation_assertion", lambda *args, **kwargs: {
        "name": "navigation",
        "passed": True,
        "detail": "present",
    })
    monkeypatch.setattr(gate, "_navigate_and_verify_route", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        gate,
        "_bridge_transport_observation",
        lambda page, *, runtime_messages, server_deprecated_warning_count=0: (
            gate.evaluate_bridge_transport(
                runtime_messages=runtime_messages,
                bridge_iframe_count=0,
                bridge_focusable_count=0,
                bridge_heights=(0,),
                server_deprecated_warning_count=server_deprecated_warning_count,
            )
        ),
    )

    result = gate._measure_route(
        FakeBrowser(),
        base_url="http://127.0.0.1:8501",
        route=gate.RESEARCH_ROUTES[4],
        viewport=(390, 844),
        timeout_seconds=5,
    )
    warned = gate._measure_route(
        FakeBrowser(),
        base_url="http://127.0.0.1:8501",
        route=gate.RESEARCH_ROUTES[4],
        viewport=(390, 844),
        timeout_seconds=5,
        server_deprecated_warning_count=1,
        server_runtime_output_status="captured_local_server",
    )

    assert result["passed"] is True
    assert result["deprecated_component_warning_count"] == 0
    assert result["bridge_iframe_count"] == 0
    assert result["bridge_focusable_count"] == 0
    assert result["bridge_height"] == 0
    assert warned["passed"] is False
    assert warned["deprecated_component_warning_count"] == 1
    assert warned["server_runtime_output_status"] == "captured_local_server"


def test_same_document_streamlit_rerun_contract_fails_closed_for_each_gap():
    from src.research_accessibility_browser_gate import (
        evaluate_same_document_streamlit_rerun,
    )

    passing_values = {
        "trigger_count": 1,
        "trigger_activated": True,
        "initial_observer_available": True,
        "token_before": "probe-1",
        "token_after": "probe-1",
        "same_document": True,
        "top_level_navigation_count": 0,
        "initial_script_state": "notRunning",
        "script_states": ("notRunning", "running", "notRunning"),
        "final_script_state": "notRunning",
        "observer_liveness_proved": True,
        "active_target": True,
        "bridge_status": "applied",
        "route_before": "/?mode=research&page=data-health&ticker=NVDA",
        "route_after": "/?mode=research&page=data-health&ticker=NVDA",
    }
    passed = evaluate_same_document_streamlit_rerun(**passing_values)

    assert all(assertion["passed"] for assertion in passed)
    assert [assertion["name"] for assertion in passed] == [
        "streamlit_rerun_trigger_available",
        "streamlit_rerun_trigger_activated",
        "streamlit_rerun_initial_observer_available",
        "streamlit_rerun_initial_script_idle",
        "streamlit_rerun_cycle_completed",
        "streamlit_rerun_same_document",
        "streamlit_rerun_no_top_level_navigation",
        "streamlit_rerun_observer_live",
        "streamlit_rerun_active_target",
        "streamlit_rerun_bridge_status",
        "streamlit_rerun_route_preserved",
    ]

    for assertion_name, changed in (
        ("streamlit_rerun_trigger_available", {"trigger_count": 0}),
        ("streamlit_rerun_trigger_activated", {"trigger_activated": False}),
        (
            "streamlit_rerun_initial_observer_available",
            {"initial_observer_available": False},
        ),
        (
            "streamlit_rerun_initial_script_idle",
            {"initial_script_state": "running"},
        ),
        (
            "streamlit_rerun_cycle_completed",
            {
                "script_states": ("notRunning", "rerunRequested", "notRunning"),
            },
        ),
        (
            "streamlit_rerun_cycle_completed",
            {
                "script_states": ("notRunning", "running"),
                "final_script_state": "running",
            },
        ),
        (
            "streamlit_rerun_same_document",
            {"token_after": "new-document", "same_document": False},
        ),
        (
            "streamlit_rerun_no_top_level_navigation",
            {"top_level_navigation_count": 1},
        ),
        (
            "streamlit_rerun_observer_live",
            {"observer_liveness_proved": False},
        ),
        ("streamlit_rerun_active_target", {"active_target": False}),
        ("streamlit_rerun_bridge_status", {"bridge_status": "missing"}),
        (
            "streamlit_rerun_route_preserved",
            {"route_after": "/?mode=research&page=discover"},
        ),
    ):
        failed_values = {**passing_values, **changed}
        failed = evaluate_same_document_streamlit_rerun(**failed_values)
        assert next(
            assertion
            for assertion in failed
            if assertion["name"] == assertion_name
        )["passed"] is False


def test_same_document_rerun_helper_uses_real_workspace_widget_event():
    from src.research_accessibility_browser_gate import (
        _same_document_streamlit_rerun_assertions,
    )

    class FakeRadio:
        def __init__(self, page):
            self.page = page

        def count(self):
            return 1

        def evaluate(self, script):
            assert "element.click()" in script
            assert "element.checked" in script
            self.page.used_dom_click = True
            self.page.rerun_triggered = True
            if self.page.simulate_top_navigation:
                self.page.frame_handler(self.page.main_frame)
            return True

    class FakePage:
        def __init__(self, *, simulate_top_navigation=False):
            self.main_frame = object()
            self.simulate_top_navigation = simulate_top_navigation
            self.frame_handler = None
            self.used_dom_click = False
            self.rerun_triggered = False
            self.evaluate_calls = 0
            self.wait_calls = 0

        def on(self, event, handler):
            assert event == "framenavigated"
            self.frame_handler = handler

        def get_by_role(self, role, *, name, exact):
            assert (role, name, exact) == (
                "radio",
                "Public visitor mode",
                True,
            )
            return FakeRadio(self)

        def evaluate(self, script):
            assert "__a11ySameDocumentRerunProbe" in script
            assert "__stockResearchMainObserver" in script
            self.evaluate_calls += 1
            if self.evaluate_calls == 1:
                assert "document: document" in script
                assert "data-test-script-state" in script
                assert "MutationObserver" in script
                return {
                    "token": "probe-1",
                    "initial_observer_available": True,
                    "initial_script_state": "notRunning",
                    "route": "/?mode=research&page=data-health&ticker=NVDA",
                }
            if self.evaluate_calls == 2:
                assert "__stockResearchMainTarget" in script
                assert "observer-probe-pending" in script
                assert "appendChild" in script
                return True
            assert "__stockResearchMainTarget" in script
            assert "scriptStateObserver.disconnect()" in script
            assert "observerProbeNode.remove()" in script
            return {
                "token": "probe-1",
                "same_document": True,
                "script_states": ["notRunning", "running", "notRunning"],
                "final_script_state": "notRunning",
                "observer_liveness_proved": self.rerun_triggered,
                "active_target": True,
                "bridge_status": "applied",
                "route": "/?mode=research&page=data-health&ticker=NVDA",
            }

        def wait_for_function(self, script, *, timeout):
            assert self.rerun_triggered is True
            assert "__a11ySameDocumentRerunProbe" in script
            self.wait_calls += 1
            if self.wait_calls == 1:
                assert 'states.indexOf("running")' in script
                assert 'states.indexOf("notRunning", runningIndex + 1)' in script
            else:
                assert "observerProbeNode" in script
                assert "data-research-main-bridge-status" in script
                assert '"applied"' in script
            assert timeout == 5_000

    page = FakePage()
    passed = _same_document_streamlit_rerun_assertions(
        page,
        timeout_seconds=5,
    )
    navigated_page = FakePage(simulate_top_navigation=True)
    failed = _same_document_streamlit_rerun_assertions(
        navigated_page,
        timeout_seconds=5,
    )

    assert page.used_dom_click is True
    assert page.wait_calls == 2
    assert all(assertion["passed"] for assertion in passed)
    assert next(
        assertion
        for assertion in failed
        if assertion["name"] == "streamlit_rerun_no_top_level_navigation"
    )["passed"] is False


def test_secondary_navigation_contract_requires_explicit_absence():
    from src.research_accessibility_browser_gate import (
        evaluate_secondary_navigation_absence,
    )

    absent = evaluate_secondary_navigation_absence(
        navigation_count=0,
        phase="initial",
    )
    present_after_rerender = evaluate_secondary_navigation_absence(
        navigation_count=1,
        phase="rerender",
    )

    assert absent == {
        "name": "secondary_workflow_navigation_absent_initial",
        "passed": True,
        "detail": "labelled primary workflow navigation count=0",
    }
    assert present_after_rerender["passed"] is False


def test_route_transition_target_is_deterministic_and_never_self():
    from src.research_accessibility_browser_gate import (
        RESEARCH_ROUTES,
        ROUND_TRIP_AWAY_ROUTE_NAMES,
        _route_transition_target,
    )

    assert ROUND_TRIP_AWAY_ROUTE_NAMES == {
        "Research Desk": "Discover",
        "Discover": "Company Workbench",
        "Company Workbench": "Monitor",
        "Monitor": "Research Data Health",
        "Research Data Health": "Research Proof History",
        "Research Proof History": "Research Desk",
    }
    assert [
        _route_transition_target(route).name
        for route in RESEARCH_ROUTES
    ] == [
        "Discover",
        "Company Workbench",
        "Monitor",
        "Research Data Health",
        "Research Proof History",
        "Research Desk",
    ]
    assert all(
        _route_transition_target(route) != route
        for route in RESEARCH_ROUTES
    )


def test_exact_route_url_contract_rejects_fragment_or_query_drift():
    from src.research_accessibility_browser_gate import evaluate_exact_route_url

    expected = (
        "http://127.0.0.1:8501/"
        "?mode=research&page=company-workbench&ticker=NVDA&open=1"
    )
    passed = evaluate_exact_route_url(
        actual_url=expected,
        expected_url=expected,
        phase="route_return",
    )
    fragment = evaluate_exact_route_url(
        actual_url=f"{expected}#public-page-answer",
        expected_url=expected,
        phase="route_return",
    )
    query_drift = evaluate_exact_route_url(
        actual_url=expected.replace("open=1", "open=0"),
        expected_url=expected,
        phase="route_return",
    )

    assert passed["passed"] is True
    assert passed["name"] == "exact_route_url_route_return"
    assert fragment["passed"] is False
    assert query_drift["passed"] is False


def test_route_transition_verifies_url_after_late_render_mutation(monkeypatch):
    import src.research_accessibility_browser_gate as gate

    expected = "http://127.0.0.1:8501/?mode=research&page=research-desk"
    events = []

    class FakePage:
        url = ""

        def goto(self, url, *, wait_until, timeout):
            assert wait_until == "domcontentloaded"
            assert timeout == 5_000
            self.url = url
            events.append("goto")

    def late_stability_drift(page, *, timeout_seconds):
        assert timeout_seconds == 5
        events.append("stability")
        page.url = f"{page.url}#late-render-drift"

    monkeypatch.setattr(
        gate,
        "_wait_for_visible_text",
        lambda page, marker, *, timeout_seconds: events.append("marker"),
    )
    monkeypatch.setattr(gate, "_wait_for_dom_stability", late_stability_drift)
    monkeypatch.setattr(
        gate,
        "_wait_for_route_heading",
        lambda page, route, *, timeout_seconds: events.append("h1"),
    )
    monkeypatch.setattr(gate, "_semantic_main_assertions", lambda page, *, phase: [])
    monkeypatch.setattr(gate, "_runtime_dom_assertions", lambda page, *, phase: [])
    monkeypatch.setattr(
        gate,
        "_navigation_assertion",
        lambda page, route: {
            "name": "labelled_workflow_navigation",
            "passed": True,
            "detail": "fake navigation",
        },
    )

    assertions = gate._navigate_and_verify_route(
        FakePage(),
        base_url="http://127.0.0.1:8501",
        route=gate.RESEARCH_ROUTES[0],
        phase="route_away",
        timeout_seconds=5,
    )

    assert events == ["goto", "marker", "stability", "h1"]
    assert next(
        assertion
        for assertion in assertions
        if assertion["name"] == "exact_route_url_route_away"
    )["passed"] is False
    assert expected in str(assertions[0]["detail"])


def test_browser_measurement_rechecks_landmark_after_rerun_and_route_transition():
    source = Path("src/research_accessibility_browser_gate.py").read_text(
        encoding="utf-8"
    )
    transition = source[source.index("def _navigate_and_verify_route(") :]
    transition = transition[: transition.index("\ndef _measure_route(")]
    measurement = source[source.index("def _measure_route(") :]
    measurement = measurement[
        : measurement.index("\ndef _repository_status_snapshot(")
    ]

    assert 'page.on("console"' in measurement
    assert 'page.on("pageerror"' in measurement
    assert '_semantic_main_assertions(page, phase="initial")' in measurement
    assert (
        '_semantic_main_assertions(page, phase="streamlit_rerun")'
        in measurement
    )
    assert '_semantic_main_assertions(page, phase="route_away")' in measurement
    assert '_semantic_main_assertions(page, phase="route_return")' in measurement
    assert '_wait_for_route_heading(page, route,' in measurement
    assert measurement.count("_wait_for_route_heading(") == 2
    assert "away_route," in measurement
    assert "_same_document_streamlit_rerun_assertions(" in measurement
    assert "away_route = _route_transition_target(route)" in measurement
    assert measurement.count("_navigate_and_verify_route(") == 2
    assert transition.count("page.goto(") == 1
    assert transition.index("_wait_for_route_heading(") < transition.index(
        "evaluate_exact_route_url("
    )
    assert 'phase="route_away"' in measurement
    assert 'phase="route_return"' in measurement
    assert (
        '_secondary_navigation_absence_assertion(page, phase="initial")'
        in measurement
    )
    assert (
        '_secondary_navigation_absence_assertion(page, phase="streamlit_rerun")'
        in measurement
    )
    assert (
        '_secondary_navigation_absence_assertion(page, phase="route_away")'
        in measurement
    )
    assert (
        '_secondary_navigation_absence_assertion(page, phase="route_return")'
        in measurement
    )
    assert '_runtime_dom_assertions(page, phase="route_away")' in measurement
    assert '_runtime_dom_assertions(page, phase="route_return")' in measurement
    assert measurement.count("page.goto(") == 1
    assert measurement.index(
        "_same_document_streamlit_rerun_assertions("
    ) < measurement.index("away_route = _route_transition_target(route)")


def test_discover_action_contract_uses_every_actual_row_and_fails_when_empty():
    from src.research_accessibility_browser_gate import (
        evaluate_discover_action_names,
    )

    passed = evaluate_discover_action_names(
        ["Open NVDA review", "Open AVGO review", "Open BRK.B review"]
    )
    empty = evaluate_discover_action_names([])
    duplicate = evaluate_discover_action_names(
        ["Open NVDA review", "Open NVDA review"]
    )

    assert passed == {
        "passed": True,
        "actual_count": 3,
        "detail": "3 eligible Discover actions have unique ticker-specific names",
    }
    assert empty["passed"] is False
    assert empty["actual_count"] == 0
    assert "no eligible Discover actions" in str(empty["detail"])
    assert duplicate["passed"] is False
    assert "unique" in str(duplicate["detail"])


def test_discover_row_contract_requires_three_visible_answers_and_ticker_action():
    from src.research_accessibility_browser_gate import evaluate_discover_rows

    passed = evaluate_discover_rows(
        (
            {
                "ticker": "NVDA",
                "labels": ("WHY REVIEWABLE", "USABLE NOW", "PRINCIPAL BLOCKER"),
                "values": (
                    "Saved readiness supports review.",
                    "SEC quarterly actuals.",
                    "Point-in-time consensus is missing.",
                ),
                "action_name": "Open NVDA review",
                "action_ticker": "NVDA",
                "action_height": 44.0,
                "visible": True,
            },
            {
                "ticker": "AVGO",
                "labels": ("Why reviewable", "Usable now", "Principal blocker"),
                "values": (
                    "Saved readiness supports review.",
                    "Historical valuation context.",
                    "No principal blocker is recorded.",
                ),
                "action_name": "Open AVGO review",
                "action_ticker": "AVGO",
                "action_height": 48.0,
                "visible": True,
            },
        )
    )
    missing_answer = evaluate_discover_rows(
        (
            {
                "ticker": "NVDA",
                "labels": ("Why reviewable", "Usable now"),
                "values": ("Saved readiness supports review.", ""),
                "action_name": "Open NVDA review",
                "action_ticker": "NVDA",
                "action_height": 44.0,
                "visible": True,
            },
        )
    )

    assert passed["passed"] is True
    assert passed["actual_count"] == 2
    assert missing_answer["passed"] is False
    assert "three visible non-empty answers" in str(missing_answer["detail"])


def test_monitor_row_contract_preserves_cohort_order_and_rejects_rank_fields():
    from src.research_accessibility_browser_gate import evaluate_monitor_rows

    passed = evaluate_monitor_rows(
        (
            {
                "cohort_order": 0,
                "ticker": "BBB",
                "attention": "Scheduled",
                "reason": "Reviewed catalyst is scheduled for 2026-08-20.",
            },
            {
                "cohort_order": 1,
                "ticker": "AAA",
                "attention": "Monitor",
                "reason": "No saved research-process transition is due.",
            },
        ),
        primary_columns=("TICKER", "PROCESS ATTENTION", "WHY"),
        advanced_identity_count=2,
    )
    ranked = evaluate_monitor_rows(
        (
            {
                "cohort_order": 2,
                "ticker": "AAA",
                "attention": "Monitor",
                "reason": "No saved research-process transition is due.",
            },
            {
                "cohort_order": 1,
                "ticker": "BBB",
                "attention": "Scheduled",
                "reason": "Reviewed catalyst is scheduled for 2026-08-20.",
            },
        ),
        primary_columns=("Ticker", "Process attention", "Return score"),
        advanced_identity_count=2,
    )

    assert passed["passed"] is True
    assert ranked["passed"] is False
    assert "saved cohort order" in str(ranked["detail"])
    assert "rank/score/return" in str(ranked["detail"])


def test_state_harness_snapshot_rejects_hidden_duplicate_or_wrong_live_semantics():
    from src.research_accessibility_browser_gate import (
        evaluate_research_state_snapshot,
    )

    passed = evaluate_research_state_snapshot(
        static_states=(
            {"state": "loading", "visible": True, "role": "group", "live": "", "busy": "true"},
            {"state": "empty", "visible": True, "role": "group", "live": "", "busy": ""},
            {"state": "withheld", "visible": True, "role": "group", "live": "", "busy": ""},
            {"state": "stale", "visible": True, "role": "group", "live": "", "busy": ""},
            {"state": "failure", "visible": True, "role": "group", "live": "", "busy": ""},
            {"state": "validation", "visible": True, "role": "group", "live": "", "busy": ""},
        ),
        transition_state="preview_ready",
        transition_nodes=(
            {
                "visible": True,
                "role": "status",
                "live": "polite",
                "atomic": "true",
                "text": "Preview ready TEST1",
            },
        ),
    )
    duplicate = evaluate_research_state_snapshot(
        static_states=passed["static_states"],
        transition_state="preview_ready",
        transition_nodes=(
            {
                "visible": True,
                "role": "status",
                "live": "polite",
                "atomic": "true",
                "text": "Preview ready TEST1",
            },
            {
                "visible": False,
                "role": "status",
                "live": "polite",
                "atomic": "true",
                "text": "Hidden duplicate TEST1",
            },
        ),
    )

    assert passed["passed"] is True
    assert duplicate["passed"] is False
    assert "exactly one visible transition node" in str(duplicate["detail"])


def test_state_harness_rerender_requires_one_visible_non_live_message():
    from src.research_accessibility_browser_gate import (
        evaluate_research_state_rerender,
    )

    passed = evaluate_research_state_rerender(
        (
            {
                "visible": True,
                "role": "group",
                "live": "",
                "atomic": "",
                "text": "Preview ready TEST1",
            },
        )
    )
    repeated_live = evaluate_research_state_rerender(
        (
            {
                "visible": True,
                "role": "status",
                "live": "polite",
                "atomic": "true",
                "text": "Preview ready TEST1",
            },
        )
    )

    assert passed["passed"] is True
    assert repeated_live["passed"] is False
    assert "non-live" in str(repeated_live["detail"])


def test_repository_snapshot_contract_rejects_any_harness_write():
    from src.research_accessibility_browser_gate import (
        evaluate_repository_snapshot_unchanged,
    )

    assert evaluate_repository_snapshot_unchanged(
        before="M data/generated.csv\0",
        after="M data/generated.csv\0",
    )["passed"] is True
    changed = evaluate_repository_snapshot_unchanged(
        before="M data/generated.csv\0",
        after="M data/generated.csv\0?? evidence.json\0",
    )
    assert changed["passed"] is False
    assert "repository status changed" in str(changed["detail"])


def test_repository_snapshot_detects_content_change_in_already_dirty_file(tmp_path):
    from src.research_accessibility_browser_gate import (
        _repository_content_snapshot,
    )

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    tracked = tmp_path / "tracked.csv"
    tracked.write_text("version,1\n", encoding="utf-8")
    subprocess.run(["git", "add", "--", "tracked.csv"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=tmp_path,
        check=True,
    )
    tracked.write_text("version,2\n", encoding="utf-8")
    before = _repository_content_snapshot(tmp_path)
    status_before = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    tracked.write_text("version,3\n", encoding="utf-8")
    after = _repository_content_snapshot(tmp_path)
    status_after = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert status_before == status_after == " M tracked.csv\n"
    assert before != after


def test_gate_fails_closed_when_explicit_browser_runtime_is_missing(tmp_path):
    from src.research_accessibility_browser_gate import (
        run_research_accessibility_browser_gate,
    )

    payload = run_research_accessibility_browser_gate(
        tmp_path,
        chrome_executable=tmp_path / "missing-chrome",
    )

    assert payload["verdict"] == "failed"
    assert payload["results"] == []
    assert "browser runtime" in " ".join(payload["failures"]).lower()


def test_focused_skip_geometry_must_be_fully_inside_the_horizontal_viewport():
    from src.research_accessibility_browser_gate import evaluate_skip_geometry

    assert evaluate_skip_geometry(
        {"x": 16, "y": 8, "width": 174, "height": 44},
        viewport_width=390,
        viewport_height=844,
    ) == {
        "passed": True,
        "detail": (
            "focused skip geometry x=16.0..190.0, y=8.0..52.0 "
            "within 390x844 viewport"
        ),
    }
    assert evaluate_skip_geometry(
        {"x": -320, "y": 8, "width": 174, "height": 44},
        viewport_width=390,
        viewport_height=844,
    )["passed"] is False
    assert evaluate_skip_geometry(
        {"x": 350, "y": 8, "width": 174, "height": 44},
        viewport_width=390,
        viewport_height=844,
    )["passed"] is False
    assert evaluate_skip_geometry(
        {"x": 16, "y": 8, "width": 0, "height": 44},
        viewport_width=390,
        viewport_height=844,
    )["passed"] is False
    assert evaluate_skip_geometry(
        {"x": 16, "y": -1, "width": 174, "height": 44},
        viewport_width=390,
        viewport_height=844,
    )["passed"] is False
    assert evaluate_skip_geometry(
        {"x": 16, "y": 820, "width": 174, "height": 44},
        viewport_width=390,
        viewport_height=844,
    )["passed"] is False


def test_explicit_base_url_accepts_only_loopback_root_urls():
    from src.research_accessibility_browser_gate import validated_loopback_base_url

    assert validated_loopback_base_url("http://127.0.0.1:8501") == (
        "http://127.0.0.1:8501"
    )
    assert validated_loopback_base_url("http://localhost:8501/") == (
        "http://localhost:8501"
    )
    assert validated_loopback_base_url("http://[::1]:8501") == (
        "http://[::1]:8501"
    )
    for invalid in (
        "https://example.com",
        "http://0.0.0.0:8501",
        "http://127.0.0.1:8501/unrelated",
        "http://127.0.0.1:8501?mode=research",
        "file:///tmp/dashboard.html",
    ):
        assert validated_loopback_base_url(invalid) is None


def test_gate_rejects_non_loopback_before_browser_discovery(tmp_path):
    from src.research_accessibility_browser_gate import (
        run_research_accessibility_browser_gate,
    )

    payload = run_research_accessibility_browser_gate(
        tmp_path,
        base_url="https://example.com",
        chrome_executable=tmp_path / "missing-chrome",
    )

    assert payload["verdict"] == "failed"
    assert payload["commit"] == ""
    assert payload["data_profile"] == "unverified"
    assert "loopback" in " ".join(payload["failures"]).lower()


def test_demo_identity_requires_product_title_brand_and_demo_profile():
    from src.research_accessibility_browser_gate import evaluate_demo_app_identity

    passed = evaluate_demo_app_identity(
        page_title="Stock Research Command Center",
        brand_text="Stock Research Command Center",
        profile_label="Demo",
        profile_caption="Data profile: demo",
    )
    wrong_profile = evaluate_demo_app_identity(
        page_title="Stock Research Command Center",
        brand_text="Stock Research Command Center",
        profile_label="Local Research",
        profile_caption="Data profile: local",
    )
    wrong_app = evaluate_demo_app_identity(
        page_title="Another dashboard",
        brand_text="Another dashboard",
        profile_label="Demo",
        profile_caption="Data profile: demo",
    )

    assert passed["passed"] is True
    assert wrong_profile["passed"] is False
    assert wrong_app["passed"] is False


def test_repository_hygiene_allows_only_unstaged_generated_churn():
    from scripts.diff_hygiene import StatusEntry
    from src.research_accessibility_browser_gate import evaluate_repository_hygiene

    generated = StatusEntry("M", "data/reports/ticker_readiness_report.csv")
    product = StatusEntry("M", "src/dashboard.py")

    clean_product = evaluate_repository_hygiene([generated], staged_entries=[])
    dirty_product = evaluate_repository_hygiene(
        [generated, product], staged_entries=[]
    )
    staged_generated = evaluate_repository_hygiene(
        [generated], staged_entries=[generated]
    )

    assert clean_product["passed"] is True
    assert clean_product["excluded_generated_paths"] == [
        "data/reports/ticker_readiness_report.csv"
    ]
    assert clean_product["dirty_product_paths"] == []
    assert dirty_product["passed"] is False
    assert dirty_product["dirty_product_paths"] == ["src/dashboard.py"]
    assert staged_generated["passed"] is False
    assert staged_generated["staged_paths"] == [
        "data/reports/ticker_readiness_report.csv"
    ]


def test_viewport_geometry_rejects_off_canvas_zero_size_and_short_route_links():
    from src.research_accessibility_browser_gate import evaluate_viewport_geometry

    viewport = (390, 844)
    assert evaluate_viewport_geometry(
        {"x": 8, "y": 120, "width": 120, "height": 44},
        viewport=viewport,
        expected_min_height=44,
        label="Discover",
    )["passed"] is True
    for rectangle in (
        {"x": -180, "y": 120, "width": 120, "height": 44},
        {"x": 400, "y": 120, "width": 120, "height": 44},
        {"x": 8, "y": 120, "width": 0, "height": 44},
        {"x": 8, "y": 120, "width": 120, "height": 0},
        {"x": 8, "y": 120, "width": 120, "height": 43},
    ):
        assert evaluate_viewport_geometry(
            rectangle,
            viewport=viewport,
            expected_min_height=44,
            label="Discover",
        )["passed"] is False


def test_skip_gate_uses_one_physical_tab_instead_of_dom_order_or_focus_substitution():
    source = Path("src/research_accessibility_browser_gate.py").read_text(
        encoding="utf-8"
    )

    assert 'page.keyboard.press("Tab")' in source
    assert "_visible_application_focus_order" not in source
    assert "skip_links.first.focus()" not in source
    assert "document.activeElement === element" in source


def test_makefile_exposes_non_writing_browser_gate():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "research-accessibility-browser-check:" in makefile
    assert "python3 -m src.research_accessibility_browser_gate" in makefile


def test_browser_gate_source_has_no_artifact_writer_or_screenshot_capture():
    source = Path("src/research_accessibility_browser_gate.py").read_text(
        encoding="utf-8"
    )
    lowered = source.lower()

    for forbidden in (
        "write_text(",
        "write_bytes(",
        "json.dump(",
        ".screenshot(",
        "page.screenshot",
    ):
        assert forbidden not in lowered
    assert "STOCK_RESEARCH_DATA_PROFILE" in source
    assert '"demo"' in source
