import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tests.point_in_time_universe_fixture import build_valid_package
from tests.test_point_in_time_universe import mutate_identity_membership_case
from tests.test_point_in_time_universe_contracts import (
    _rewrite_csv_and_manifest,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGETS = (
    "point-in-time-universe-status",
    "point-in-time-universe-preview",
)
WRITE_LIKE_OPTIONS = (
    "--output",
    "--apply",
    "--record",
    "--stage",
    "--refresh",
    "--write",
)
WRITE_LIKE_MODES = ("apply", "record", "stage", "refresh", "write")


def _snapshot(root: Path) -> dict[str, tuple[str, bytes]]:
    snapshot: dict[str, tuple[str, bytes]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            snapshot[relative] = ("symlink", os.fsencode(os.readlink(path)))
        elif path.is_dir():
            snapshot[relative] = ("directory", b"")
        elif path.is_file():
            snapshot[relative] = ("file", path.read_bytes())
        else:
            snapshot[relative] = ("other", b"")
    return snapshot


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "src.point_in_time_universe", *arguments],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def _run_make(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "--no-print-directory", *arguments],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def _block_source_rights(manifest: Path, registry: Path) -> None:
    registry.write_text(
        registry.read_text(encoding="utf-8").replace(
            "commercial_use: approved",
            "commercial_use: unverified",
        ),
        encoding="utf-8",
    )
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    raw["source_rights_registry_sha256"] = hashlib.sha256(
        registry.read_bytes()
    ).hexdigest()
    manifest.write_text(json.dumps(raw), encoding="utf-8")


def test_renderers_and_cli_are_deterministic_complete_and_read_only(tmp_path):
    from src.point_in_time_universe import (
        DECISION_ORDER,
        render_preview,
        render_status,
        validate_point_in_time_universe,
    )

    manifest, registry = build_valid_package(tmp_path)
    before = _snapshot(tmp_path)
    packet = validate_point_in_time_universe(manifest, registry, top_n=5)

    status = render_status(packet)
    preview = render_preview(packet, top_n=5)
    assert render_status(packet) == status
    assert render_preview(packet, top_n=5) == preview

    for output in (status, preview):
        assert (
            "Read-only: validates one supplied immutable package; it does not "
            "fetch, write, apply, refresh, or rebuild data."
        ) in output
        assert (
            "Research-only: this does not activate readiness, backtesting, "
            "calibration, or probability and is not investment advice."
        ) in output
        assert "dataset_id: fixture-dataset" in output
        assert "manifest_id: fixture-manifest" in output
        assert "analysis_eligible: true" in output
        assert "raw_count: 6" in output
        assert "normalized_count: 6" in output
        assert "excluded_count: 0" in output
        assert "analysis_eligible_row_count: 8" in output
        assert f"boundary: {packet.boundary}" in output
        for name in DECISION_ORDER:
            decision = packet.decisions[name]
            reasons = ",".join(decision.reason_codes) or "none"
            assert f"{name}: {decision.status}; reasons={reasons}" in output

    assert len(DECISION_ORDER) == 10
    assert "Membership reproduction:" in preview
    assert "Exclusion reason counts:" in preview
    assert "- none" in preview
    for digest in packet.membership_digests:
        assert (
            f"- {digest.universe_id} @ {digest.evaluation_at}: "
            f"members={digest.member_count}; sha256={digest.sha256}"
        ) in preview
    assert "Excluded sample:" in preview

    status_results = [
        _run_cli(
            "status",
            "--manifest",
            str(manifest),
            "--registry",
            str(registry),
            "--top-n",
            "5",
        )
        for _ in range(2)
    ]
    preview_results = [
        _run_cli(
            "preview",
            "--manifest",
            str(manifest),
            "--registry",
            str(registry),
            "--top-n",
            "5",
        )
        for _ in range(2)
    ]

    assert [result.returncode for result in status_results] == [0, 0]
    assert [result.returncode for result in preview_results] == [0, 0]
    assert status_results[0].stdout == status_results[1].stdout == f"{status}\n"
    assert (
        preview_results[0].stdout
        == preview_results[1].stdout
        == f"{preview}\n"
    )
    assert all(not result.stderr for result in status_results + preview_results)
    assert _snapshot(tmp_path) == before


def test_synthetic_package_status_is_local_software_evidence_only(tmp_path):
    from src.point_in_time_universe import (
        render_status,
        validate_point_in_time_universe,
    )

    manifest, registry = build_valid_package(tmp_path)

    output = render_status(
        validate_point_in_time_universe(manifest, registry),
    )

    assert (
        "Synthetic or technically valid packages are local software "
        "evidence only."
    ) in output
    assert (
        "Priority 4 still requires one independently reviewed, permitted "
        "real dataset."
    ) in output
    for prohibited_claim in (
        "Priority 4 complete",
        "real-world validation complete",
        "readiness activated",
        "backtesting activated",
        "calibration complete",
        "probability available",
        "recommendation:",
        "investment advice:",
    ):
        assert prohibited_claim not in output


def test_preview_caps_canonically_sorted_exclusions_without_writing(tmp_path):
    from src.point_in_time_universe import (
        render_preview,
        validate_point_in_time_universe,
    )

    manifest, registry = build_valid_package(tmp_path)
    mutate_identity_membership_case(manifest, "overlapping_identity")
    before = _snapshot(tmp_path)
    packet = validate_point_in_time_universe(
        manifest,
        registry,
        top_n=0,
    )

    one = _run_cli(
        "preview",
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
        "--top-n",
        "1",
    )
    none = _run_cli(
        "preview",
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
        "--top-n",
        "0",
    )

    assert one.returncode == none.returncode == 0
    assert "Membership reproduction:" in one.stdout
    one_exclusions = one.stdout.partition("Excluded sample:\n")[2].splitlines()
    no_exclusions = none.stdout.partition("Excluded sample:\n")[2].splitlines()
    assert one_exclusions == [
        "- membership:2:member-bench-1; reasons=identity_interval_overlap"
    ]
    assert no_exclusions == []
    assert len(packet.excluded) > 1
    assert packet.excluded_count == len(packet.excluded)
    assert (
        "identity_interval_overlap: 4"
        in render_preview(packet, top_n=1)
    )
    for proprietary_value in (
        "AAA",
        "fixture://identity/id-1",
        "fixture://membership/bench-1",
    ):
        assert proprietary_value not in one.stdout
    assert _snapshot(tmp_path) == before


def test_readable_blocked_package_returns_zero_with_blocked_truth(tmp_path):
    manifest, registry = build_valid_package(tmp_path)
    _block_source_rights(manifest, registry)
    before = _snapshot(tmp_path)

    result = _run_cli(
        "status",
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )

    assert result.returncode == 0
    assert "analysis_eligible: false" in result.stdout
    assert (
        "source_rights_eligibility: blocked; "
        "reasons=source_rights_commercial_rights_unverified"
    ) in result.stdout
    assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before


def test_missing_manifest_is_nonzero_without_traceback():
    result = _run_cli("status")

    assert result.returncode == 2
    assert "MANIFEST is required" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "top_n",
    ("-1", "101", "true", "false", "1.5", "not-a-number"),
)
def test_invalid_top_n_is_nonzero_without_traceback(tmp_path, top_n):
    manifest, registry = build_valid_package(tmp_path)
    before = _snapshot(tmp_path)

    result = _run_cli(
        "preview",
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
        "--top-n",
        top_n,
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before


def test_preview_top_n_boundaries_and_packet_independence(tmp_path):
    from src.point_in_time_universe import (
        render_preview,
        validate_point_in_time_universe,
    )

    manifest, registry = build_valid_package(tmp_path)
    before = _snapshot(tmp_path)
    packet_zero = validate_point_in_time_universe(
        manifest,
        registry,
        top_n=0,
    )
    packet_max = validate_point_in_time_universe(
        manifest,
        registry,
        top_n=100,
    )

    assert packet_zero == packet_max
    assert render_preview(packet_zero, top_n=0)
    assert render_preview(packet_max, top_n=100)
    for invalid in (-1, 101, True, 1.5, "1"):
        with pytest.raises(ValueError, match="top_n_invalid"):
            validate_point_in_time_universe(
                manifest,
                registry,
                top_n=invalid,
            )
        with pytest.raises(ValueError, match="top_n_invalid"):
            render_preview(packet_zero, top_n=invalid)
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "resource,error",
    [
        ("manifest", "manifest_size_limit_exceeded"),
        ("contract", "manifest_file_size_limit_exceeded"),
        ("combined", "manifest_total_snapshot_size_limit_exceeded"),
        ("registry", "manifest_registry_size_limit_exceeded"),
        ("rows", "manifest_row_count_limit_exceeded"),
        ("traversal", "manifest_package_entry_limit_exceeded"),
    ],
)
def test_cli_and_make_resource_failures_are_readable_nonwriting(
    tmp_path,
    resource,
    error,
):
    from src.point_in_time_universe_manifest import (
        MAX_CONTRACT_SNAPSHOT_BYTES,
        MAX_MANIFEST_BYTES,
        MAX_PACKAGE_TRAVERSAL_ENTRIES,
        MAX_RIGHTS_REGISTRY_BYTES,
        MAX_TOTAL_CONTRACT_SNAPSHOT_BYTES,
    )

    manifest, registry = build_valid_package(tmp_path)
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    records = {
        item["contract"]: item
        for item in raw["files"]
    }
    if resource == "manifest":
        manifest.write_bytes(
            manifest.read_bytes()
            + b" " * (MAX_MANIFEST_BYTES + 1 - manifest.stat().st_size)
        )
    elif resource == "contract":
        identity = manifest.parent / records["security_identity"]["path"]
        identity.write_bytes(b"\n" * (MAX_CONTRACT_SNAPSHOT_BYTES + 1))
    elif resource == "combined":
        target_size = MAX_TOTAL_CONTRACT_SNAPSHOT_BYTES // 3 + 1
        for contract in ("security_identity", "membership", "events"):
            path = manifest.parent / records[contract]["path"]
            path.write_bytes(
                path.read_bytes()
                + b"\n" * (target_size - path.stat().st_size)
            )
            records[contract]["sha256"] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
        manifest.write_text(json.dumps(raw), encoding="utf-8")
    elif resource == "registry":
        registry.write_bytes(
            registry.read_bytes()
            + b" " * (MAX_RIGHTS_REGISTRY_BYTES + 1 - registry.stat().st_size)
        )
    elif resource == "rows":
        records["security_identity"]["row_count"] = 250_001
        manifest.write_text(json.dumps(raw), encoding="utf-8")
    else:
        current_entries = sum(1 for _ in manifest.parent.iterdir())
        for index in range(
            MAX_PACKAGE_TRAVERSAL_ENTRIES - current_entries + 1
        ):
            (manifest.parent / f"empty-{index:02d}").mkdir()

    before = _snapshot(tmp_path)
    cli = _run_cli(
        "preview",
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )
    make = _run_make(
        "point-in-time-universe-preview",
        f"MANIFEST={manifest}",
        f"REGISTRY={registry}",
    )

    for result in (cli, make):
        assert result.returncode != 0
        assert error in result.stderr
        assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("mode", ("unknown", *WRITE_LIKE_MODES))
def test_unknown_and_write_like_modes_are_rejected_without_traceback(
    tmp_path,
    mode,
):
    manifest, registry = build_valid_package(tmp_path)
    before = _snapshot(tmp_path)

    result = _run_cli(
        mode,
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("option", WRITE_LIKE_OPTIONS)
def test_write_like_options_are_rejected_without_traceback(tmp_path, option):
    manifest, registry = build_valid_package(tmp_path)
    before = _snapshot(tmp_path)

    result = _run_cli(
        "status",
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
        option,
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before


def test_invalid_package_is_nonzero_without_traceback_or_writes(tmp_path):
    manifest, registry = build_valid_package(tmp_path)
    manifest.write_text("{not valid json", encoding="utf-8")
    before = _snapshot(tmp_path)

    result = _run_cli(
        "status",
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )

    assert result.returncode == 2
    assert "manifest_unreadable" in result.stderr
    assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("mode", ("status", "preview"))
def test_oversized_manifest_bound_csv_is_controlled_and_read_only(
    tmp_path,
    mode,
):
    manifest, registry = build_valid_package(tmp_path)
    oversized = "A" * (csv.field_size_limit() + 1)
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(ticker=oversized),
    )
    before = _snapshot(tmp_path)

    result = _run_cli(
        mode,
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )

    assert result.returncode == 2
    assert "field larger than field limit" in result.stderr
    assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("mode", ("status", "preview"))
def test_manifest_referenced_self_loop_symlink_is_controlled_and_read_only(
    tmp_path,
    mode,
):
    manifest, registry = build_valid_package(tmp_path)
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    identity_record = next(
        item
        for item in raw["files"]
        if item["contract"] == "security_identity"
    )
    identity = manifest.parent / identity_record["path"]
    identity.unlink()
    identity.symlink_to(identity.name)
    before = _snapshot(tmp_path)

    result = _run_cli(
        mode,
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )

    assert result.returncode == 2
    assert "symlink" in result.stderr.lower()
    assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before


def test_make_targets_match_cli_and_leave_package_root_byte_identical(tmp_path):
    manifest, registry = build_valid_package(tmp_path)
    before = _snapshot(tmp_path)

    for mode, target in zip(("status", "preview"), TARGETS, strict=True):
        cli = _run_cli(
            mode,
            "--manifest",
            str(manifest),
            "--registry",
            str(registry),
            "--top-n",
            "5",
        )
        make = _run_make(
            target,
            f"MANIFEST={manifest}",
            f"REGISTRY={registry}",
            "TOP_N=5",
        )
        assert cli.returncode == make.returncode == 0
        assert make.stdout == cli.stdout
        assert not make.stderr

    assert _snapshot(tmp_path) == before


def test_all_entry_paths_preserve_supplied_root_symlink_inventory(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    target = tmp_path / "inventory-target.txt"
    target.write_text("immutable supplied-root marker\n", encoding="utf-8")
    link = tmp_path / "inventory-link"
    link.symlink_to(target.name)
    before = _snapshot(tmp_path)

    assert before["inventory-link"] == (
        "symlink",
        os.fsencode(target.name),
    )
    validate_point_in_time_universe(manifest, registry)
    for mode, target_name in zip(
        ("status", "preview"),
        TARGETS,
        strict=True,
    ):
        cli = _run_cli(
            mode,
            "--manifest",
            str(manifest),
            "--registry",
            str(registry),
        )
        make = _run_make(
            target_name,
            f"MANIFEST={manifest}",
            f"REGISTRY={registry}",
        )
        assert cli.returncode == make.returncode == 0

    assert link.is_symlink()
    assert os.readlink(link) == target.name
    assert _snapshot(tmp_path) == before


def test_make_targets_are_phony_listed_in_help_and_require_manifest():
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    phony = {
        target
        for line in makefile.splitlines()
        if line.startswith(".PHONY:")
        for target in line.partition(":")[2].split()
    }
    help_result = _run_make("help")

    assert help_result.returncode == 0
    for target in TARGETS:
        assert target in phony
        assert target in help_result.stdout
        missing = _run_make(target)
        assert missing.returncode != 0
        assert "MANIFEST is required" in missing.stderr
        assert "Traceback" not in missing.stderr


@pytest.mark.parametrize(
    "case,reason",
    [
        (
            "event_history",
            "membership_coverage_semantics_unsupported",
        ),
        (
            "reversed_identity",
            "schema_identity_interval_reversed",
        ),
        (
            "reversed_membership",
            "schema_membership_interval_reversed",
        ),
        (
            "duplicate_evaluation",
            "schema_evaluation_row_id_duplicate",
        ),
    ],
)
def test_remediation_2_blockers_are_traceback_free_and_read_only(
    tmp_path,
    case,
    reason,
):
    manifest, registry = build_valid_package(tmp_path)

    if case == "event_history":
        raw = json.loads(manifest.read_text(encoding="utf-8"))
        raw["coverage_semantics"] = "event_history"
        manifest.write_text(json.dumps(raw), encoding="utf-8")
    elif case == "reversed_identity":
        _rewrite_csv_and_manifest(
            manifest,
            "security_identity",
            lambda rows: rows[0].update(
                valid_from="2020-06-01T00:00:00Z",
                valid_to="2020-05-01T00:00:00Z",
            ),
        )
    elif case == "reversed_membership":
        _rewrite_csv_and_manifest(
            manifest,
            "membership",
            lambda rows: rows[0].update(
                effective_from="2020-06-01T00:00:00Z",
                effective_to="2020-05-01T00:00:00Z",
            ),
        )
    else:
        _rewrite_csv_and_manifest(
            manifest,
            "evaluations",
            lambda rows: rows[1].update(
                evaluation_row_id=rows[0]["evaluation_row_id"],
            ),
        )
    before = _snapshot(tmp_path)

    result = _run_cli(
        "preview",
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )

    assert result.returncode == 0
    assert "analysis_eligible: false" in result.stdout
    assert reason in result.stdout
    assert "Traceback" not in result.stderr
    if case in {"event_history", "duplicate_evaluation"}:
        assert "sha256=" not in result.stdout
    assert _snapshot(tmp_path) == before


def test_distinct_evaluation_ids_share_one_read_only_cutoff_digest(
    tmp_path,
):
    manifest, registry = build_valid_package(tmp_path)

    def add_distinct_same_cutoff(rows):
        rows.append(
            {
                **rows[0],
                "evaluation_row_id": "eval-bench-distinct-2",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        add_distinct_same_cutoff,
    )
    before = _snapshot(tmp_path)

    result = _run_cli(
        "preview",
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )

    assert result.returncode == 0
    assert "analysis_eligible: true" in result.stdout
    assert (
        "reproduction_ready: passed; reasons=none"
        in result.stdout
    )
    assert result.stdout.count(
        "- bench-1 @ 2021-01-01T00:00:00Z:"
    ) == 1
    assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before
