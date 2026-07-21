import json
import os
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _make(
    *arguments: str,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = ["make", "--no-print-directory"]
    if dry_run:
        command.append("--just-print")
    command.extend(arguments)
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def _phony_targets(makefile: str) -> set[str]:
    targets: set[str] = set()
    for line in makefile.splitlines():
        if line.startswith(".PHONY:"):
            targets.update(line.partition(":")[2].split())
    return targets


def _argv_capture_environment(tmp_path: Path) -> dict[str, str]:
    shim = tmp_path / "python3"
    shim.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$@\"\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}


def test_prospective_field_proof_targets_are_phony_and_default_ledger_is_explicit():
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    phony_targets = _phony_targets(makefile)

    for target in (
        "prospective-field-proof-status",
        "prospective-field-proof-preview",
        "prospective-field-proof-record",
    ):
        assert target in phony_targets


def test_default_status_target_runs_live_without_creating_or_changing_scoped_files():
    ledger = PROJECT_ROOT / "data" / "prospective_field_proofs.csv"
    scoped_files = (
        PROJECT_ROOT / "data" / "earnings_readiness.csv",
        PROJECT_ROOT / "data" / "universe_master.csv",
        PROJECT_ROOT / "data" / "reviewed_data_proof.csv",
        PROJECT_ROOT / "outputs" / "feature_readiness_summary.csv",
    )
    assert not ledger.exists()
    before = {path: path.read_bytes() for path in scoped_files if path.is_file()}

    result = _make("prospective-field-proof-status", "JSON=1")
    payload = json.loads(result.stdout)
    after = {path: path.read_bytes() for path in scoped_files if path.is_file()}

    assert result.returncode == 0
    assert payload["ledger"] == "data/prospective_field_proofs.csv"
    assert payload["state"] == "absent"
    assert payload["write_performed"] is False
    assert not ledger.exists()
    assert after == before


def test_prospective_field_proof_make_targets_forward_adversarial_values_literally(
    tmp_path: Path,
):
    marker = tmp_path / "make-injection-marker"
    command_substitution = f"$(touch {marker})"
    backtick_substitution = f"`touch {marker}`"
    input_path = (
        "review inputs/quote'\"-"
        f"{backtick_substitution}-{command_substitution}-back\\slash.csv"
    )
    ledger_path = (
        "review ledgers/quote'\"-"
        f"{backtick_substitution}-{command_substitution}-back\\slash.csv"
    )
    cutoff = (
        "2026-07-20T00:00:00Z quote'\"-"
        f"{backtick_substitution}-{command_substitution}-back\\slash"
    )
    receipt = (
        "receipt quote'\"-"
        f"{backtick_substitution}-{command_substitution}-back\\slash"
    )
    capture_env = _argv_capture_environment(tmp_path)

    preview = _make(
        "prospective-field-proof-preview",
        f"INPUT={input_path}",
        f"LEDGER={ledger_path}",
        f"AS_OF={cutoff}",
        "JSON=1",
        env=capture_env,
    )
    record = _make(
        "prospective-field-proof-record",
        f"INPUT={input_path}",
        f"LEDGER={ledger_path}",
        f"AS_OF={cutoff}",
        f"PREVIEW_RECEIPT={receipt}",
        "CONFIRM_REVIEWED=1",
        "JSON=1",
        env=capture_env,
    )
    marker_created = marker.exists()
    marker.unlink(missing_ok=True)

    assert preview.returncode == record.returncode == 0
    assert preview.stdout.splitlines() == [
        "-m",
        "src.prospective_field_proof",
        "preview",
        "--input",
        input_path,
        "--ledger",
        ledger_path,
        "--as-of",
        cutoff,
        "--json",
    ]
    assert record.stdout.splitlines() == [
        "-m",
        "src.prospective_field_proof",
        "record",
        "--input",
        input_path,
        "--ledger",
        ledger_path,
        "--as-of",
        cutoff,
        "--preview-receipt",
        receipt,
        "--confirm-reviewed",
        "--json",
    ]
    assert marker_created is False


@pytest.mark.parametrize(
    ("variable", "message"),
    [
        ("INPUT", "INPUT is required for the exact reviewed field proof batch"),
        ("AS_OF", "AS_OF is required and must match the reviewed preview cutoff"),
        (
            "PREVIEW_RECEIPT",
            "PREVIEW_RECEIPT is required from the exact reviewed preview",
        ),
    ],
)
def test_record_make_target_rejects_blank_values_before_python(
    variable: str, message: str
):
    values = {
        "INPUT": "review/proposed.csv",
        "AS_OF": "2026-07-20T00:00:00Z",
        "PREVIEW_RECEIPT": "c" * 64,
    }
    values[variable] = "   "

    result = _make(
        "prospective-field-proof-record",
        *(f"{name}={value}" for name, value in values.items()),
        "CONFIRM_REVIEWED=1",
    )

    assert result.returncode != 0
    assert message in result.stderr
    assert "src.prospective_field_proof" not in result.stdout + result.stderr


def test_record_make_target_requires_explicit_review_confirmation_before_python():
    result = _make(
        "prospective-field-proof-record",
        "INPUT=review/proposed.csv",
        "AS_OF=2026-07-20T00:00:00Z",
        f"PREVIEW_RECEIPT={'d' * 64}",
    )

    assert result.returncode != 0
    assert "CONFIRM_REVIEWED=1 is required after reviewing the exact preview" in result.stderr
    assert "src.prospective_field_proof" not in result.stdout + result.stderr
