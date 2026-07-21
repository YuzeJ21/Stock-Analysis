import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _make(*arguments: str, dry_run: bool = False) -> subprocess.CompletedProcess[str]:
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
    )


def test_prospective_field_proof_targets_are_phony_and_default_ledger_is_explicit():
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

    for target in (
        "prospective-field-proof-status",
        "prospective-field-proof-preview",
        "prospective-field-proof-record",
    ):
        assert target in makefile.split(".PHONY:", 1)[1]

    result = _make("prospective-field-proof-status", "JSON=1", dry_run=True)

    assert result.returncode == 0
    assert (
        'python3 -m src.prospective_field_proof status '
        '--ledger "data/prospective_field_proofs.csv" --json'
    ) in result.stdout
    assert not (PROJECT_ROOT / "data" / "prospective_field_proofs.csv").exists()


def test_prospective_field_proof_make_targets_forward_exact_paths_cutoff_and_receipt():
    input_path = "review inputs/proposed.csv"
    ledger_path = "review ledgers/proofs.csv"
    cutoff = "2026-07-20T00:00:00Z"
    receipt = "b" * 64

    preview = _make(
        "prospective-field-proof-preview",
        f"INPUT={input_path}",
        f"LEDGER={ledger_path}",
        f"AS_OF={cutoff}",
        "JSON=1",
        dry_run=True,
    )
    record = _make(
        "prospective-field-proof-record",
        f"INPUT={input_path}",
        f"LEDGER={ledger_path}",
        f"AS_OF={cutoff}",
        f"PREVIEW_RECEIPT={receipt}",
        "CONFIRM_REVIEWED=1",
        "JSON=1",
        dry_run=True,
    )

    assert preview.returncode == record.returncode == 0
    assert (
        'python3 -m src.prospective_field_proof preview '
        f'--input "{input_path}" --ledger "{ledger_path}" '
        f'--as-of "{cutoff}" --json'
    ) in preview.stdout
    assert (
        'python3 -m src.prospective_field_proof record '
        f'--input "{input_path}" --ledger "{ledger_path}" '
        f'--as-of "{cutoff}" --preview-receipt "{receipt}" '
        '--confirm-reviewed --json'
    ) in record.stdout


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
