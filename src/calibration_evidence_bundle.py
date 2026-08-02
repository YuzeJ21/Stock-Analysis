from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


BUNDLE_SCHEMA_VERSION = "calibration-evidence-bundle-v1"
PREVIEW_SCHEMA_VERSION = "calibration-evidence-bundle-preview-v1"
MAX_BUNDLE_BYTES = 16 * 1024 * 1024
_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "bundle_id",
        "created_at",
        "cohort",
        "observations",
        "backtest_report",
        "evidence_references",
    }
)


class CalibrationEvidenceBundleError(ValueError):
    pass


@dataclass(frozen=True)
class _LoadedCalibrationEvidenceBundle:
    path: Path
    raw_bytes: bytes
    bundle_sha256: str
    payload: Mapping[str, object]


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in pairs:
        if key in output:
            raise CalibrationEvidenceBundleError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def load_calibration_evidence_bundle(
    path: Path | str,
) -> _LoadedCalibrationEvidenceBundle:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise CalibrationEvidenceBundleError(f"bundle does not exist: {resolved}")
    if not resolved.is_file():
        raise CalibrationEvidenceBundleError("bundle path must be a regular file")
    if resolved.stat().st_size > MAX_BUNDLE_BYTES:
        raise CalibrationEvidenceBundleError("bundle exceeds the 16 MiB limit")

    raw = resolved.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CalibrationEvidenceBundleError("bundle must be valid UTF-8") from exc
    try:
        payload = json.loads(text, object_pairs_hook=_unique_object)
    except CalibrationEvidenceBundleError:
        raise
    except json.JSONDecodeError as exc:
        raise CalibrationEvidenceBundleError("bundle contains malformed JSON") from exc

    if not isinstance(payload, dict):
        raise CalibrationEvidenceBundleError("bundle root must be a JSON object")
    keys = set(payload)
    missing = sorted(_TOP_LEVEL_KEYS - keys)
    unknown = sorted(keys - _TOP_LEVEL_KEYS)
    if missing:
        raise CalibrationEvidenceBundleError(
            f"missing top-level keys: {', '.join(missing)}"
        )
    if unknown:
        raise CalibrationEvidenceBundleError(
            f"unknown top-level keys: {', '.join(unknown)}"
        )
    if payload["schema_version"] != BUNDLE_SCHEMA_VERSION:
        raise CalibrationEvidenceBundleError(
            "unsupported calibration evidence bundle schema"
        )

    return _LoadedCalibrationEvidenceBundle(
        path=resolved,
        raw_bytes=raw,
        bundle_sha256=hashlib.sha256(raw).hexdigest(),
        payload=payload,
    )
