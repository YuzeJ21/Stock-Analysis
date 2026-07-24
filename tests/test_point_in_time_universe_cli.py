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
        assert f"boundary: {packet.boundary}" in output
        for name in DECISION_ORDER:
            decision = packet.decisions[name]
            reasons = ",".join(decision.reason_codes) or "none"
            assert f"{name}: {decision.status}; reasons={reasons}" in output

    assert len(DECISION_ORDER) == 10
    assert "Membership reproduction:" in preview
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


def test_preview_caps_canonically_sorted_exclusions_without_writing(tmp_path):
    manifest, registry = build_valid_package(tmp_path)
    mutate_identity_membership_case(manifest, "overlapping_identity")
    before = _snapshot(tmp_path)

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


@pytest.mark.parametrize("top_n", ("-1", "true", "false", "1.5", "not-a-number"))
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
