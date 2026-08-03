from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from src import dashboard
from src import reviewed_batch_proof
from src.readiness_ops import PeerReadinessSummary, build_readiness_ops_lanes


CONCRETE_PROFILES = {"default", "demo", "local"}
PROFILE_TOKEN = re.compile(r"\bPROFILE=([^\s&`.,;]+)")
ROOT = Path(__file__).resolve().parents[1]
TASK_8_RUNTIME_FILES = (
    "src/dashboard.py",
    "src/data_health_batch_console.py",
    "src/data_health_coverage_delta.py",
    "src/data_health_coverage_proof_summary.py",
    "src/data_health_dcf_source_commands.py",
    "src/data_health_dcf_source_packet.py",
    "src/data_health_proof_checklist.py",
    "src/data_health_proof_console.py",
    "src/data_health_proof_ctas.py",
    "src/data_health_proof_planner.py",
    "src/data_health_queue_outcome.py",
    "src/data_health_recent_progress.py",
    "src/data_health_trusted_fundamentals_writer.py",
    "src/data_health_trusted_pilot_console.py",
    "src/dcf_input_proof_queue.py",
    "src/dcf_readiness.py",
    "src/decision_proof_queue.py",
    "src/peer_mapping_source_review.py",
    "src/price_history_proof_queue.py",
    "src/readiness_comparison.py",
    "src/readiness_queue_dashboard.py",
    "src/research_decisions.py",
    "src/reviewed_batch.py",
    "src/reviewed_batch_command_builder.py",
    "src/reviewed_batch_preflight.py",
    "src/reviewed_batch_proof.py",
    "src/reviewed_data_proof.py",
    "src/share_count_proof_queue.py",
    "src/stock_report.py",
    "src/auto_refresh_orchestrator.py",
    "src/coverage_expansion_loop.py",
    "src/data_health_peer_analysis.py",
    "src/data_health_overview_console.py",
    "src/public_home_workflow.py",
    "src/readiness_ops.py",
    "src/source_activation_guide.py",
    "src/trusted_data_pilot.py",
)
SOURCE_PROFILE_TOKEN = re.compile(r"\bPROFILE=(\{[^}\n]+\}|[^\s&`.,;]+)")
SOURCE_LANE_TOKEN = re.compile(r"\bLANE=(\{[^}\n]+\}|[^\s&`.,;]+)")
WRITE_PROOF_LANES = {
    "fundamentals",
    "fundamentals_dcf",
    "optional_context",
    "optional_context_locked",
    "peer_mapping",
    "peer_valuation_inputs",
    "peers",
    "price_history",
    "prices",
    "share_count",
    "shares_outstanding",
}
POST_APPLY_READINESS_TOKENS = {
    "fundamentals": ("make dcf-readiness",),
    "fundamentals_dcf": ("make dcf-readiness",),
    "share_count": ("make dcf-readiness",),
    "shares_outstanding": ("make dcf-readiness",),
    "optional_context": ("make optional-context-readiness",),
    "optional_context_locked": ("make optional-context-readiness",),
}
PROFILE_VALUE_PROVIDERS = {
    "_active_data_profile_name",
    "resolve_readiness_proof_profile",
}
PROFILE_OBJECT_PROVIDERS = {
    "_reviewed_batch_profile",
    "resolve_data_profile",
    "validate_readiness_source_boundary",
}
PROFILE_TUPLE_PROVIDERS = {"_selected_profile_paths"}
PROFILE_NORMALIZERS = {"lower", "str", "strip", "upper"}


@dataclass(frozen=True)
class RuntimeStringObject:
    """One maximal string value assembled by a source expression."""

    line_number: int
    rendered: str
    context: tuple[str, ...] = ()
    approved_profiles: tuple[str, ...] = ()


def _parse_inventory_source(source: str) -> ast.Module:
    try:
        return ast.parse(source)
    except SyntaxError:
        repaired = source.replace('"\n"', '"\\n"').replace("'\n'", "'\\n'")
        if repaired == source:
            raise
        return ast.parse(repaired)


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _is_join_expression(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "join"
        and len(node.args) == 1
        and isinstance(node.args[0], (ast.List, ast.Tuple))
        and _is_string_expression(node.func.value)
    )


def _is_string_expression(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _is_string_expression(node.left) or _is_string_expression(node.right)
    return _is_join_expression(node)


def _dynamic_fragment(node: ast.AST) -> str:
    return "{" + ast.unparse(node) + "}"


def _render_string_expression(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                parts.append(_dynamic_fragment(value.value))
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = (
            _render_string_expression(node.left)
            if _is_string_expression(node.left)
            else _dynamic_fragment(node.left)
        )
        right = (
            _render_string_expression(node.right)
            if _is_string_expression(node.right)
            else _dynamic_fragment(node.right)
        )
        return left + right
    if _is_join_expression(node):
        assert isinstance(node, ast.Call)
        assert isinstance(node.func, ast.Attribute)
        assert isinstance(node.args[0], (ast.List, ast.Tuple))
        separator = _render_string_expression(node.func.value)
        rendered_items = [
            _render_string_expression(item) if _is_string_expression(item) else _dynamic_fragment(item)
            for item in node.args[0].elts
        ]
        return separator.join(rendered_items)
    return _dynamic_fragment(node)


def _assignment_target_names(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(name for item in node.elts for name in _assignment_target_names(item))
    if isinstance(node, ast.Attribute):
        return (ast.unparse(node),)
    return ()


def _expression_context(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> tuple[str, ...]:
    labels: list[str] = []
    child = node
    parent = parents.get(child)
    while parent is not None and not isinstance(parent, ast.stmt):
        if isinstance(parent, ast.keyword) and parent.arg:
            labels.append(parent.arg)
        elif isinstance(parent, ast.Dict):
            for key, value in zip(parent.keys, parent.values):
                if value is child and isinstance(key, ast.Constant) and isinstance(key.value, str):
                    labels.append(key.value)
        elif isinstance(parent, ast.Call) and child in parent.args:
            labels.append(ast.unparse(parent.func))
        child = parent
        parent = parents.get(child)
    if isinstance(parent, (ast.Assign, ast.AnnAssign)):
        targets = parent.targets if isinstance(parent, ast.Assign) else [parent.target]
        labels.extend(name for target in targets for name in _assignment_target_names(target))
    return tuple(labels)


def _enclosing_scope(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.AST | None:
    current = parents.get(node)
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return current
        current = parents.get(current)
    return None


def _scope_chain(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> tuple[ast.AST | None, ...]:
    """Return module through nested lexical scopes for one expression."""

    scopes: list[ast.AST] = []
    current = parents.get(node)
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            scopes.append(current)
        current = parents.get(current)
    return (None, *reversed(scopes))


def _scope_arguments(scope: ast.AST | None) -> set[str]:
    if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        return set()
    arguments = scope.args
    return {
        argument.arg
        for argument in (
            *arguments.posonlyargs,
            *arguments.args,
            *arguments.kwonlyargs,
            *([arguments.vararg] if arguments.vararg is not None else []),
            *([arguments.kwarg] if arguments.kwarg is not None else []),
        )
    }


def _profile_value_is_approved(value: ast.AST | None, approved: set[str]) -> bool:
    """Trace simple, non-forging aliases of an already selected profile value."""

    if value is None:
        return False
    rendered = ast.unparse(value)
    if rendered in approved:
        return True
    if isinstance(value, ast.Constant):
        return value.value in {"", *CONCRETE_PROFILES}
    if isinstance(value, ast.Call):
        call_name = _call_name(value.func)
        if call_name in PROFILE_VALUE_PROVIDERS:
            return True
        if call_name in PROFILE_NORMALIZERS:
            if isinstance(value.func, ast.Attribute):
                return _profile_value_is_approved(value.func.value, approved)
            return bool(value.args) and _profile_value_is_approved(value.args[0], approved)
        return False
    if isinstance(value, ast.BoolOp):
        return all(_profile_value_is_approved(item, approved) for item in value.values)
    if isinstance(value, ast.IfExp):
        return _profile_value_is_approved(value.body, approved) and _profile_value_is_approved(
            value.orelse,
            approved,
        )
    return False


def _approved_profiles_at(
    node: ast.AST,
    *,
    parents: dict[ast.AST, ast.AST],
    assignments_by_scope: dict[ast.AST | None, list[ast.Assign | ast.AnnAssign]],
) -> tuple[str, ...]:
    approved: set[str] = set()
    for scope in _scope_chain(node, parents):
        argument_names = _scope_arguments(scope)
        for name in argument_names:
            for expression in (name, f"{name}.name", f"{name}.profile", f"{name}.profile_key"):
                approved.discard(expression)
            if name.lstrip("_").endswith("profile"):
                approved.add(name)
            approved.update((f"{name}.profile", f"{name}.profile_key"))

        for assignment in assignments_by_scope.get(scope, []):
            if getattr(assignment, "lineno", 0) >= getattr(node, "lineno", 0):
                break
            value = assignment.value
            targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
            ordered_names = tuple(
                name for target in targets for name in _assignment_target_names(target)
            )
            names = set(ordered_names)
            for name in names:
                approved.discard(name)
                approved.discard(f"{name}.name")
                approved.discard(f"{name}.profile")
                approved.discard(f"{name}.profile_key")
            if isinstance(value, ast.Call) and _call_name(value.func) in PROFILE_VALUE_PROVIDERS:
                approved.update(names)
            elif isinstance(value, ast.Call) and _call_name(value.func) in PROFILE_OBJECT_PROVIDERS:
                approved.update(f"{name}.name" for name in names)
            elif isinstance(value, ast.Call) and _call_name(value.func) == "build_profile_context":
                approved.update(f"{name}.profile_key" for name in names)
            elif isinstance(value, ast.Call) and _call_name(value.func) in PROFILE_TUPLE_PROVIDERS:
                approved.update(ordered_names[:1])
            elif _profile_value_is_approved(value, approved):
                approved.update(names)
    return tuple(sorted(approved))


def runtime_string_objects_from_source(source: str) -> tuple[RuntimeStringObject, ...]:
    """Return maximal runtime string objects instead of their AST leaf fragments."""

    tree = _parse_inventory_source(source)
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    assignments_by_scope: dict[ast.AST | None, list[ast.Assign | ast.AnnAssign]] = {}
    for candidate in ast.walk(tree):
        if isinstance(candidate, (ast.Assign, ast.AnnAssign)):
            assignments_by_scope.setdefault(_enclosing_scope(candidate, parents), []).append(candidate)
    for assignments in assignments_by_scope.values():
        assignments.sort(
            key=lambda candidate: (
                getattr(candidate, "lineno", 0),
                getattr(candidate, "col_offset", 0),
            )
        )
    candidates = {
        node for node in ast.walk(tree) if isinstance(node, ast.expr) and _is_string_expression(node)
    }
    maximal: list[ast.expr] = []
    for node in candidates:
        ancestor = parents.get(node)
        while ancestor is not None and not isinstance(ancestor, ast.stmt):
            if ancestor in candidates:
                break
            ancestor = parents.get(ancestor)
        else:
            maximal.append(node)
    return tuple(
        RuntimeStringObject(
            line_number=getattr(node, "lineno", 1),
            rendered=_render_string_expression(node),
            context=_expression_context(node, parents),
            approved_profiles=_approved_profiles_at(
                node,
                parents=parents,
                assignments_by_scope=assignments_by_scope,
            ),
        )
        for node in sorted(
            maximal,
            key=lambda item: (getattr(item, "lineno", 1), getattr(item, "col_offset", 0)),
        )
    )


def _profile_expression_is_explicitly_bound(expression: str, bound: set[str]) -> bool:
    if expression in bound:
        return True
    return expression in {
        "_active_data_profile_name()",
        "resolve_readiness_proof_profile()",
    }


def _is_actionable_proof_object(item: RuntimeStringObject, command: str) -> bool:
    context = {
        re.sub(r"[^a-z0-9]+", "_", token.lower()).strip("_")
        for token in item.context
    }
    proof_context = " ".join(context)
    if any(token in proof_context for token in ("proof_command", "proof_sequence", "st_code")):
        return True
    if context.intersection({"post_guard_proof", "post_run_proof", "proof_after_update"}):
        return True
    has_snapshot = "make readiness-snapshot PROFILE=" in command
    has_comparison = "make reviewed-batch-compare PROFILE=" in command
    return "command" in context and ((has_snapshot and has_comparison) or "-apply" in command)


def _is_write_lane_proof(command: str) -> bool:
    return any(lane in WRITE_PROOF_LANES for lane in SOURCE_LANE_TOKEN.findall(command))


def profile_bound_proof_source_issues(source: str) -> tuple[str, ...]:
    """Report composed proof objects that lose profile provenance or proof boundaries."""

    issues: list[str] = []
    for item in runtime_string_objects_from_source(source):
        command = item.rendered
        bound_profiles = set(item.approved_profiles)
        profile_tokens = SOURCE_PROFILE_TOKEN.findall(command)
        if not profile_tokens:
            continue

        profile_values: set[str] = set()
        resolver_expression_count = 0
        for token in profile_tokens:
            if token in CONCRETE_PROFILES:
                profile_values.add(token)
                continue
            if token.startswith("{") and token.endswith("}"):
                expression = token[1:-1]
                if expression == "resolve_readiness_proof_profile()":
                    resolver_expression_count += 1
                if _profile_expression_is_explicitly_bound(expression, bound_profiles):
                    profile_values.add(expression)
                else:
                    issues.append(
                        f"line {item.line_number}: PROFILE expression {expression} is not explicitly bound "
                        "to the selected profile"
                    )
                continue
            issues.append(f"line {item.line_number}: PROFILE value {token} is not concrete")

        if resolver_expression_count > 1:
            issues.append(
                f"line {item.line_number}: selected profile is resolved more than once in one proof object"
            )
        if len(profile_values) > 1:
            rendered_values = ", ".join(sorted(profile_values))
            issues.append(f"line {item.line_number}: proof object mixes PROFILE values: {rendered_values}")

        snapshot_index = command.find("make readiness-snapshot PROFILE=")
        compare_index = command.find("make reviewed-batch-compare PROFILE=")
        proof_boundary_present = snapshot_index >= 0 or compare_index >= 0
        if proof_boundary_present and _is_actionable_proof_object(item, command):
            if snapshot_index < 0 or compare_index < 0:
                issues.append(f"line {item.line_number}: incomplete proof sequence")
            elif snapshot_index > compare_index:
                issues.append(f"line {item.line_number}: proof sequence compares before its readiness snapshot")
            else:
                validate_index = command.find("-validate")
                preview_index = command.find("-preview")
                apply_index = command.find("-apply")
                if apply_index >= 0 or _is_write_lane_proof(command):
                    if validate_index < 0 or preview_index < 0:
                        issues.append(
                            f"line {item.line_number}: incomplete reviewed write proof sequence"
                        )
                    elif not (
                        snapshot_index
                        < validate_index
                        < preview_index
                        < apply_index
                        < compare_index
                    ):
                        issues.append(
                            f"line {item.line_number}: reviewed write proof sequence is out of order"
                        )
                    lanes = set(SOURCE_LANE_TOKEN.findall(command))
                    required_readiness_tokens = tuple(
                        token
                        for lane in lanes
                        for token in POST_APPLY_READINESS_TOKENS.get(lane, ())
                    )
                    if required_readiness_tokens:
                        readiness_indices = [
                            command.find(token)
                            for token in required_readiness_tokens
                            if command.find(token) >= 0
                        ]
                        if not any(
                            apply_index < readiness_index < compare_index
                            for readiness_index in readiness_indices
                        ):
                            issues.append(
                                f"line {item.line_number}: missing required post-apply readiness rebuild"
                            )

    return tuple(dict.fromkeys(issues))


def _complete_runtime_strings(relative_path: str) -> list[tuple[int, str]]:
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    return [
        (item.line_number, item.rendered)
        for item in runtime_string_objects_from_source(source)
    ]


def assert_structural_proof_sequence(
    command: str,
    *,
    profile: str,
    lane: str,
    requires_reviewed_apply: bool,
) -> None:
    """Validate one rendered proof object, not neighboring source text."""

    steps = [step.strip() for step in command.split("&&")]
    profiles = PROFILE_TOKEN.findall(command)
    assert profiles
    assert set(profiles) == {profile}
    assert profile in CONCRETE_PROFILES
    assert not any("<" in token or ">" in token or "|" in token for token in profiles)

    snapshot_index = next(index for index, step in enumerate(steps) if step == f"make readiness-snapshot PROFILE={profile}")
    compare_index = next(
        index
        for index, step in enumerate(steps)
        if step.startswith(f"make reviewed-batch-compare PROFILE={profile} LANE={lane} ")
    )
    comparison = steps[compare_index]
    assert "BATCH_ID=" in comparison
    assert "REVIEW_DATE=" in comparison
    assert "readiness-preview" not in command

    if requires_reviewed_apply:
        validate_index = next(index for index, step in enumerate(steps) if "-validate" in step)
        preview_index = next(index for index, step in enumerate(steps) if "-preview" in step)
        apply_index = next(index for index, step in enumerate(steps) if "-apply" in step)
        assert snapshot_index < validate_index < preview_index < apply_index < compare_index
    else:
        assert snapshot_index < compare_index


def test_profile_bound_proof_sequence_renders_one_concrete_profile_in_order():
    command = reviewed_batch_proof.profile_bound_readiness_proof_sequence(
        profile="local",
        lane="fundamentals",
        batch_id="RB-LOCAL-001",
        review_date="2026-08-03",
        reviewed_steps=(
            "make imports-validate IMPORT_TICKERS=NVDA",
            "make imports-preview IMPORT_TICKERS=NVDA",
            "make imports-apply IMPORT_TICKERS=NVDA",
        ),
    )

    assert command == (
        "make readiness-snapshot PROFILE=local && "
        "make imports-validate IMPORT_TICKERS=NVDA && "
        "make imports-preview IMPORT_TICKERS=NVDA && "
        "make imports-apply IMPORT_TICKERS=NVDA && "
        "make reviewed-batch-compare PROFILE=local LANE=fundamentals "
        "BATCH_ID=RB-LOCAL-001 REVIEW_DATE=2026-08-03"
    )
    assert_structural_proof_sequence(
        command,
        profile="local",
        lane="fundamentals",
        requires_reviewed_apply=True,
    )


@pytest.mark.parametrize(
    "profile",
    [
        "",
        "DEFAULT",
        "unknown",
        "<default|demo|local>",
        "<profile>",
        "default|demo|local",
        "${PROFILE}",
        "PROFILE=default",
    ],
)
def test_profile_bound_proof_sequence_rejects_missing_unknown_and_placeholder_profiles(profile: str):
    with pytest.raises(ValueError, match="concrete readiness profile"):
        reviewed_batch_proof.profile_bound_readiness_proof_sequence(
            profile=profile,
            lane="prices",
            batch_id="RB-001",
            review_date="2026-08-03",
            reviewed_steps=("make price-validate", "make price-preview", "make price-apply"),
        )


def test_profile_bound_proof_sequence_rejects_missing_comparison_scope():
    for field, values in (
        ("lane", {"lane": ""}),
        ("batch_id", {"batch_id": "<reviewed_batch_id>"}),
        ("review_date", {"review_date": "<yyyy-mm-dd>"}),
    ):
        arguments = {
            "profile": "default",
            "lane": "prices",
            "batch_id": "RB-001",
            "review_date": "2026-08-03",
            "reviewed_steps": ("make price-validate", "make price-preview", "make price-apply"),
            **values,
        }
        with pytest.raises(ValueError, match=field):
            reviewed_batch_proof.profile_bound_readiness_proof_sequence(**arguments)


def test_active_proof_profile_resolver_follows_selected_environment(monkeypatch, tmp_path):
    resolver = getattr(reviewed_batch_proof, "resolve_readiness_proof_profile", None)
    assert resolver is not None

    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    assert resolver(project_root=tmp_path) == "local"
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "<default|demo|local>")
    with pytest.raises(ValueError, match="concrete readiness profile"):
        resolver(project_root=tmp_path)


@pytest.mark.parametrize("profile", ["", " ", "DEFAULT", "unknown", "<profile>"])
def test_proof_profile_resolver_rejects_non_concrete_explicit_values(profile, tmp_path):
    with pytest.raises(ValueError, match="concrete readiness profile"):
        reviewed_batch_proof.resolve_readiness_proof_profile(profile, project_root=tmp_path)


def test_readiness_ops_renders_structural_proof_objects_for_selected_local_profile(tmp_path):
    peer_summary = PeerReadinessSummary(
        total_count=0,
        peer_mapping_ready=0,
        peer_price_ready=0,
        peer_momentum_ready=0,
        peer_fundamentals_ready=0,
        peer_valuation_ready=0,
        peer_valuation_comparison_ready=0,
        missing_mapping=0,
        missing_peer_price=0,
        missing_peer_momentum=0,
        missing_peer_fundamentals=0,
        peer_valuation_blocked=0,
        source_context="test fixture",
    )

    lanes = build_readiness_ops_lanes(
        tmp_path,
        profile="local",
        dcf_input_rows=[],
        share_count_rows=[],
        peer_summary=peer_summary,
    )

    expected = {
        "price_coverage": ("prices", True),
        "fundamentals_dcf": ("fundamentals", True),
        "share_count_proof": ("share_count", True),
        "peer_mapping": ("peers", True),
        "peer_valuation_inputs": ("peers", True),
        "earnings_locked": ("optional_context", True),
        "analyst_estimates_locked": ("optional_context", True),
        "excluded_not_applicable": ("excluded", False),
    }
    for row in lanes:
        lane, requires_apply = expected[row.lane]
        assert_structural_proof_sequence(
            row.proof_command,
            profile="local",
            lane=lane,
            requires_reviewed_apply=requires_apply,
        )


def test_structural_validator_catches_profile_mutation_and_order_mutation():
    valid = reviewed_batch_proof.profile_bound_readiness_proof_sequence(
        profile="demo",
        lane="prices",
        batch_id="RB-DEMO-001",
        review_date="2026-08-03",
        reviewed_steps=("make price-validate", "make price-preview", "make price-apply"),
    )

    with pytest.raises(AssertionError):
        assert_structural_proof_sequence(
            valid.replace("PROFILE=demo LANE=prices", "PROFILE=local LANE=prices"),
            profile="demo",
            lane="prices",
            requires_reviewed_apply=True,
        )
    with pytest.raises(AssertionError):
        assert_structural_proof_sequence(
            valid.replace("make price-preview && make price-apply", "make price-apply && make price-preview"),
            profile="demo",
            lane="prices",
            requires_reviewed_apply=True,
        )


@pytest.mark.parametrize(
    ("source", "expected_issue"),
    [
        (
            """
proof_command = (
    f"make readiness-snapshot PROFILE={wrong()} && "
    "make imports-validate && make imports-preview && make imports-apply && "
    f"make reviewed-batch-compare PROFILE={wrong()} LANE=fundamentals BATCH_ID=RB-1 REVIEW_DATE=2026-08-03"
)
""",
            "wrong()",
        ),
        (
            'proof_command = "make " + "readiness-snapshot PROFILE=" + profile',
            "incomplete proof sequence",
        ),
        (
            """
proof_command = "\n".join(
    [
        "make readiness-snapshot PROFILE=local",
        "make imports-validate",
        "make imports-preview",
    ]
)
""",
            "incomplete proof sequence",
        ),
    ],
)
def test_structural_inventory_catches_composed_and_arbitrary_profile_mutations(source, expected_issue):
    objects = runtime_string_objects_from_source(source)
    issues = profile_bound_proof_source_issues(source)

    assert len(objects) == 1
    assert expected_issue in "\n".join(issues)


def test_structural_inventory_accepts_one_explicitly_bound_profile_per_complete_proof_object():
    source = """
selected_profile = resolve_readiness_proof_profile(profile)
proof_command = (
    f"make readiness-snapshot PROFILE={selected_profile} && "
    "make imports-validate && make imports-preview && make imports-apply && make dcf-readiness && "
    f"make reviewed-batch-compare PROFILE={selected_profile} LANE=fundamentals BATCH_ID=RB-1 REVIEW_DATE=2026-08-03"
)
"""

    assert profile_bound_proof_source_issues(source) == ()


def test_structural_inventory_rejects_forged_selected_profile_alias():
    source = """
selected_profile = wrong()
proof_command = (
    f"make readiness-snapshot PROFILE={selected_profile} && "
    "make imports-validate && make imports-preview && make imports-apply && "
    f"make reviewed-batch-compare PROFILE={selected_profile} LANE=fundamentals BATCH_ID=RB-1 REVIEW_DATE=2026-08-03"
)
"""

    issues = profile_bound_proof_source_issues(source)

    assert "selected_profile is not explicitly bound" in "\n".join(issues)


def test_structural_inventory_validates_actionable_dict_command_order():
    source = """
row = {
    "command": (
        "make readiness-snapshot PROFILE=local && "
        "make imports-validate && make imports-apply && make imports-preview && "
        "make reviewed-batch-compare PROFILE=local LANE=fundamentals BATCH_ID=RB-1 REVIEW_DATE=2026-08-03"
    )
}
"""

    issues = profile_bound_proof_source_issues(source)

    assert "reviewed write proof sequence is out of order" in "\n".join(issues)


@pytest.mark.parametrize(
    ("reviewed_steps", "expected_issue"),
    [
        (
            (
                "make imports-validate",
                "make imports-apply",
                "make imports-preview",
            ),
            "reviewed write proof sequence is out of order",
        ),
        (
            (
                "make imports-preview",
                "make imports-apply",
            ),
            "incomplete reviewed write proof sequence",
        ),
        (
            (
                "make imports-validate",
                "make imports-apply",
            ),
            "incomplete reviewed write proof sequence",
        ),
    ],
)
def test_structural_inventory_rejects_misordered_or_partial_reviewed_write_sequences(
    reviewed_steps,
    expected_issue,
):
    commands = (
        "make readiness-snapshot PROFILE=local",
        *reviewed_steps,
        "make reviewed-batch-compare PROFILE=local LANE=fundamentals "
        "BATCH_ID=RB-1 REVIEW_DATE=2026-08-03",
    )
    source = f"proof_command = {(' && '.join(commands))!r}"

    issues = profile_bound_proof_source_issues(source)

    assert expected_issue in "\n".join(issues)


def test_structural_inventory_allows_read_only_proof_and_standalone_baseline_commands():
    source = """
proof_command = (
    "make readiness-snapshot PROFILE=local && "
    "make reviewed-batch-compare PROFILE=local LANE=excluded BATCH_ID=RB-1 REVIEW_DATE=2026-08-03"
)
inspection_command = "make readiness-snapshot PROFILE=local"
baseline_command = (
    "make reviewed-batch-compare PROFILE=local LANE=excluded BATCH_ID=RB-1 REVIEW_DATE=2026-08-03"
)
"""

    assert profile_bound_proof_source_issues(source) == ()


@pytest.mark.parametrize(
    "lane",
    [
        "prices",
        "price_history",
        "fundamentals",
        "fundamentals_dcf",
        "peers",
        "peer_mapping",
        "peer_valuation_inputs",
        "share_count",
        "shares_outstanding",
        "optional_context",
        "optional_context_locked",
    ],
)
def test_structural_inventory_rejects_write_lane_proof_with_no_reviewed_steps(lane):
    source = f'''\
proof_command = (
    "make readiness-snapshot PROFILE=local && "
    "make reviewed-batch-compare PROFILE=local LANE={lane} BATCH_ID=RB-1 REVIEW_DATE=2026-08-03"
)
'''

    issues = profile_bound_proof_source_issues(source)

    assert "incomplete reviewed write proof sequence" in "\n".join(issues)


@pytest.mark.parametrize(
    "middle_steps",
    [
        "make imports-validate && make imports-preview && make imports-apply && ",
        "make imports-validate && make imports-preview && make dcf-readiness && make imports-apply && ",
    ],
)
def test_structural_inventory_requires_post_apply_fundamentals_readiness(middle_steps):
    source = f'''\
proof_command = (
    "make readiness-snapshot PROFILE=local && "
    "{middle_steps}"
    "make reviewed-batch-compare PROFILE=local LANE=fundamentals BATCH_ID=RB-1 REVIEW_DATE=2026-08-03"
)
'''

    issues = profile_bound_proof_source_issues(source)

    assert "missing required post-apply readiness rebuild" in "\n".join(issues)


def test_task_8_structural_inventory_has_no_composed_profile_or_sequence_gaps():
    offenders: list[str] = []
    for relative_path in TASK_8_RUNTIME_FILES:
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        offenders.extend(
            f"{relative_path}: {issue}"
            for issue in profile_bound_proof_source_issues(source)
        )

    assert offenders == []


def test_dashboard_readiness_ops_cache_keys_concrete_selected_profile(tmp_path):
    dashboard.cached_readiness_ops_lanes.cache_clear()

    default_rows = dashboard.cached_readiness_ops_lanes(str(tmp_path), "default")
    local_rows = dashboard.cached_readiness_ops_lanes(str(tmp_path), "local")

    assert "PROFILE=default" in default_rows[0].proof_command
    assert "PROFILE=local" in local_rows[0].proof_command
    assert default_rows[0].proof_command != local_rows[0].proof_command


def test_dashboard_readiness_ops_frame_uses_actual_selected_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "demo")
    dashboard.cached_readiness_ops_lanes.cache_clear()

    frame = dashboard.data_health_readiness_ops_center_frame(tmp_path)

    assert not frame.empty
    assert frame["Proof Command"].str.contains("PROFILE=demo", regex=False).all()
    assert not frame["Proof Command"].str.contains("PROFILE=default", regex=False).any()


def test_dashboard_recent_progress_calls_bind_actual_selected_profile_structurally():
    tree = ast.parse((ROOT / "src/dashboard.py").read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "readiness_recent_progress_cards"
    ]

    assert len(calls) == 2
    for call in calls:
        profile_keyword = next((keyword for keyword in call.keywords if keyword.arg == "profile"), None)
        assert profile_keyword is not None
        assert ast.unparse(profile_keyword.value) == "_active_data_profile_name()"


def test_task_8_complete_runtime_literals_never_offer_writer_or_placeholder_profile():
    offenders: list[str] = []
    deprecated_writer = re.compile(r"make readiness(?![-_])")
    for relative_path in TASK_8_RUNTIME_FILES:
        for line_number, rendered in _complete_runtime_strings(relative_path):
            if deprecated_writer.search(rendered):
                offenders.append(f"{relative_path}:{line_number}: deprecated writer: {rendered}")
            for profile in PROFILE_TOKEN.findall(rendered):
                if "<" in profile or ">" in profile or "|" in profile:
                    offenders.append(f"{relative_path}:{line_number}: placeholder profile: {rendered}")

    assert offenders == []


def test_task_8_complete_proof_literals_keep_command_fields_in_one_object():
    offenders: list[str] = []
    for relative_path in TASK_8_RUNTIME_FILES:
        for line_number, rendered in _complete_runtime_strings(relative_path):
            if "make readiness-snapshot" not in rendered and "make reviewed-batch-compare" not in rendered:
                continue
            profiles = PROFILE_TOKEN.findall(rendered)
            if not profiles or len(set(profiles)) != 1:
                offenders.append(f"{relative_path}:{line_number}: profile mismatch: {rendered}")
                continue
            if "make reviewed-batch-compare" in rendered:
                comparison = rendered[rendered.index("make reviewed-batch-compare") :]
                missing = [field for field in ("PROFILE=", "LANE=", "BATCH_ID=", "REVIEW_DATE=") if field not in comparison]
                if missing:
                    offenders.append(f"{relative_path}:{line_number}: missing {','.join(missing)}: {rendered}")
            if "make readiness-snapshot" in rendered and "make reviewed-batch-compare" in rendered:
                if rendered.index("make readiness-snapshot") > rendered.index("make reviewed-batch-compare"):
                    offenders.append(f"{relative_path}:{line_number}: compare precedes snapshot: {rendered}")
                if re.search(r"make [\w-]+-apply\b", rendered):
                    ordered = (
                        rendered.index("make readiness-snapshot"),
                        re.search(r"make [\w-]+-validate\b", rendered).start(),
                        re.search(r"make [\w-]+-preview\b", rendered).start(),
                        re.search(r"make [\w-]+-apply\b", rendered).start(),
                        rendered.index("make reviewed-batch-compare"),
                    )
                    if tuple(sorted(ordered)) != ordered:
                        offenders.append(f"{relative_path}:{line_number}: reviewed order is invalid: {rendered}")

    assert offenders == []


def test_task_8_complete_runtime_literals_never_present_preview_as_proof():
    offenders: list[str] = []
    for relative_path in TASK_8_RUNTIME_FILES:
        for line_number, rendered in _complete_runtime_strings(relative_path):
            lowered = rendered.lower()
            if "readiness-preview" in lowered and any(token in lowered for token in ("proof", "post-run", "post-apply", "comparison")):
                offenders.append(f"{relative_path}:{line_number}: {rendered}")

    assert offenders == []
