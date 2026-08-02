from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.calibration_evidence_bundle import (
    CalibrationEvidenceBundleError,
    load_calibration_evidence_bundle,
)


def _envelope() -> dict[str, object]:
    return {
        "schema_version": "calibration-evidence-bundle-v1",
        "bundle_id": "calibration-review-2026-q2",
        "created_at": "2026-08-02T12:00:00Z",
        "cohort": {},
        "observations": [],
        "backtest_report": {},
        "evidence_references": [],
    }


def test_loader_binds_preview_to_the_exact_input_bytes(tmp_path: Path):
    path = tmp_path / "bundle.json"
    raw = json.dumps(_envelope(), indent=2).encode("utf-8")
    path.write_bytes(raw)

    loaded = load_calibration_evidence_bundle(path)

    assert loaded.path == path.resolve()
    assert loaded.bundle_sha256 == hashlib.sha256(raw).hexdigest()
    assert loaded.payload["bundle_id"] == "calibration-review-2026-q2"
    assert path.read_bytes() == raw


def test_loader_digest_changes_when_any_input_byte_changes(tmp_path: Path):
    path = tmp_path / "bundle.json"
    raw = json.dumps(_envelope(), separators=(",", ":")).encode("utf-8")
    path.write_bytes(raw)
    original = load_calibration_evidence_bundle(path)

    path.write_bytes(raw + b"\n")
    changed = load_calibration_evidence_bundle(path)

    assert changed.bundle_sha256 != original.bundle_sha256
    assert changed.raw_bytes == raw + b"\n"


def test_loader_rejects_missing_input(tmp_path: Path):
    with pytest.raises(CalibrationEvidenceBundleError, match="does not exist"):
        load_calibration_evidence_bundle(tmp_path / "missing.json")


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b'{"schema_version":"calibration-evidence-bundle-v1",', "malformed JSON"),
        (b"\xff", "UTF-8"),
        (
            b'{"schema_version":"calibration-evidence-bundle-v1",'
            b'"schema_version":"calibration-evidence-bundle-v1"}',
            "duplicate JSON key",
        ),
    ],
)
def test_loader_rejects_malformed_or_ambiguous_json(
    tmp_path: Path,
    raw: bytes,
    message: str,
):
    path = tmp_path / "bundle.json"
    path.write_bytes(raw)

    with pytest.raises(CalibrationEvidenceBundleError, match=message):
        load_calibration_evidence_bundle(path)


def test_loader_rejects_unknown_or_oversized_input(tmp_path: Path):
    unknown = _envelope() | {"probability_available": True}
    path = tmp_path / "unknown.json"
    path.write_text(json.dumps(unknown), encoding="utf-8")
    with pytest.raises(CalibrationEvidenceBundleError, match="unknown top-level keys"):
        load_calibration_evidence_bundle(path)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * (16 * 1024 * 1024 + 1))
    with pytest.raises(CalibrationEvidenceBundleError, match="16 MiB"):
        load_calibration_evidence_bundle(oversized)
