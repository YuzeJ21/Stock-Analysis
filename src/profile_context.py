"""Build one fail-closed data-profile context for UI and status surfaces."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

from src.paths import (
    profile_display_label,
    resolve_data_dir,
    resolve_data_profile,
    resolve_outputs_dir,
    resolve_project_root,
)


READINESS_FILES = (
    Path("reports/ticker_readiness_report.csv"),
    Path("reports/feature_readiness_summary.csv"),
)
SOURCE_DATE_COLUMNS: dict[Path, tuple[str, tuple[str, ...]]] = {
    Path("prices.csv"): ("prices", ("date",)),
    Path("fundamentals.csv"): ("fundamentals", ("as_of_date", "updated_at")),
    Path("peers.csv"): ("peers", ("as_of_date", "review_date")),
    Path("earnings.csv"): ("earnings", ("as_of_date", "reported_at", "retrieved_at")),
    Path("analyst_estimates.csv"): (
        "analyst_estimates",
        ("as_of_date", "retrieved_at", "snapshot_at"),
    ),
}
IDENTITY_FILES = (*READINESS_FILES, *SOURCE_DATE_COLUMNS.keys())
READINESS_PREVIEW_COMMAND = "make readiness-preview TOP_N=20"
READINESS_PREVIEW_NOTE = "In-memory preview only; it does not refresh or persist saved readiness."


def readiness_inspection_route(profile_key: str, profile_label: str, data_dir: Path) -> tuple[str, str]:
    if profile_key == "default":
        return READINESS_PREVIEW_COMMAND, READINESS_PREVIEW_NOTE
    unavailable = (
        f"Unavailable for {profile_label} ({profile_key}): Slice 1 readiness preview inspects only "
        f"Default (default) inputs in data; selected profile inputs are {data_dir.as_posix()}."
    )
    return unavailable, f"{unavailable} {READINESS_PREVIEW_NOTE}"


@dataclass(frozen=True)
class CoverageCounts:
    total: int = 0
    price_ready: int = 0
    fundamentals_ready: int = 0
    dcf_ready: int = 0
    peer_ready: int = 0


@dataclass(frozen=True)
class ProfileContext:
    profile_key: str
    profile_label: str
    data_dir: Path
    outputs_dir: Path
    source_as_of: str
    readiness_built_at: str
    snapshot_identity: str
    snapshot_identity_short: str
    freshness_state: str
    freshness_message: str
    refresh_command: str
    coverage: CoverageCounts
    lane_source_dates: tuple[tuple[str, str], ...]
    snapshot_inputs: tuple[str, ...]
    readiness_evidence_state: str = "unverified"
    readiness_evidence_message: str = "Readiness evidence origin was not evaluated."


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except (OSError, UnicodeError, csv.Error):
        return []


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "y", "ready"}


def _coverage_counts(path: Path) -> CoverageCounts:
    rows = [row for row in _read_csv(path) if str(row.get("ticker") or "").strip()]
    return CoverageCounts(
        total=len(rows),
        price_ready=sum(_truthy(row.get("price_ready")) for row in rows),
        fundamentals_ready=sum(_truthy(row.get("fundamentals_ready")) for row in rows),
        dcf_ready=sum(_truthy(row.get("dcf_ready")) for row in rows),
        peer_ready=sum(_truthy(row.get("peer_ready")) for row in rows),
    )


def _parse_date(value: object) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _parse_datetime(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _latest_date(rows: Iterable[dict[str, str]], columns: tuple[str, ...], *, today: date) -> str:
    values = {
        parsed
        for row in rows
        for column in columns
        for parsed in [_parse_date(row.get(column))]
        if parsed is not None and parsed <= today
    }
    return max(values).isoformat() if values else ""


def _lane_source_dates(data_dir: Path, *, today: date) -> tuple[tuple[str, str], ...]:
    dates: list[tuple[str, str]] = []
    for relative_path, (lane, columns) in SOURCE_DATE_COLUMNS.items():
        value = _latest_date(_read_csv(data_dir / relative_path), columns, today=today)
        if value:
            dates.append((lane, value))
    return tuple(sorted(dates))


def _readiness_built_at(data_dir: Path) -> str:
    timestamps = {
        parsed
        for relative_path in READINESS_FILES
        for row in _read_csv(data_dir / relative_path)
        for column in ("updated_at", "generated_at", "as_of_date")
        for parsed in [_parse_datetime(row.get(column))]
        if parsed is not None
    }
    if timestamps:
        return max(timestamps).isoformat()
    existing = [data_dir / path for path in READINESS_FILES if (data_dir / path).exists()]
    if not existing:
        return ""
    return datetime.fromtimestamp(max(path.stat().st_mtime for path in existing), timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_identity(manifest_path: Path) -> tuple[str, str]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "", ""
    hashes = sorted(
        str(item.get("sha256") or "").strip().lower()
        for item in (payload.get("files") or {}).values()
        if isinstance(item, dict) and str(item.get("sha256") or "").strip()
    )
    identity = (
        hashlib.sha256(json.dumps(hashes, separators=(",", ":")).encode("utf-8")).hexdigest()
        if hashes
        else ""
    )
    snapshot_date = str(payload.get("snapshot_date") or "").strip()
    return identity, snapshot_date


def _local_identity(data_dir: Path) -> tuple[str, tuple[str, ...]]:
    records: list[dict[str, object]] = []
    inputs: list[str] = []
    for relative_path in sorted(IDENTITY_FILES, key=lambda item: item.as_posix()):
        path = data_dir / relative_path
        if path.exists():
            records.append(
                {
                    "path": relative_path.as_posix(),
                    "state": "present",
                    "size": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
            inputs.append(str(path))
        else:
            records.append({"path": relative_path.as_posix(), "state": "missing"})
            inputs.append(f"missing:{path}")
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), tuple(inputs)


def _readiness_evidence(
    project_root: Path,
    data_dir: Path,
    *,
    profile_key: str,
) -> tuple[str, str]:
    """Classify tracked release evidence independently from date freshness."""

    if profile_key != "default" or data_dir != (project_root / "data").resolve():
        return "not_applicable", "Tracked release-evidence comparison applies only to the default data profile."
    try:
        relative_paths = [(data_dir / path).relative_to(project_root).as_posix() for path in READINESS_FILES]
    except ValueError:
        return "unverified", "Readiness artifacts are outside the project root and cannot be compared with HEAD."
    try:
        repository_check = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = str(exc.stderr or "").lower()
        if "not a git repository" in stderr:
            return "not_applicable", "Tracked release-evidence comparison is unavailable outside a Git worktree."
        return "unverified", "Readiness artifacts could not be compared with tracked HEAD evidence."
    except OSError:
        return "unverified", "Readiness artifacts could not be compared with tracked HEAD evidence."
    if repository_check.stdout.strip().lower() != "true":
        return "not_applicable", "Tracked release-evidence comparison is unavailable outside a Git worktree."
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(project_root),
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                "--",
                *relative_paths,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unverified", "Readiness artifacts could not be compared with tracked HEAD evidence."
    if result.stdout.strip():
        return (
            "working_artifact_uncommitted",
            "Readiness artifacts differ from HEAD and are not tracked release evidence.",
        )
    return "tracked", "Readiness artifacts match tracked HEAD evidence."


def _freshness(data_dir: Path, *, profile_key: str, profile_label: str) -> tuple[str, str, str]:
    inspection_action, inspection_note = readiness_inspection_route(profile_key, profile_label, data_dir)
    readiness_paths = [data_dir / path for path in READINESS_FILES]
    readiness_present = [path for path in readiness_paths if path.exists()]
    if not readiness_present:
        return "missing", f"Selected-profile readiness artifacts are missing. {inspection_note}", inspection_action
    if len(readiness_present) != len(readiness_paths):
        return "mixed", f"Only some selected-profile readiness artifacts are available. {inspection_note}", inspection_action

    source_paths = [data_dir / path for path in SOURCE_DATE_COLUMNS if (data_dir / path).exists()]
    if not source_paths:
        return "mixed", f"Readiness exists but selected-profile canonical source files are missing. {inspection_note}", inspection_action
    return "current", "Selected-profile readiness is current for the saved source files.", ""


def build_profile_context(
    project_root: Path | str | None = None,
    *,
    data_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    now: datetime | None = None,
) -> ProfileContext:
    root = resolve_project_root(project_root)
    profile = resolve_data_profile(project_root=root)
    data_path = resolve_data_dir(data_dir, root)
    output_path = resolve_outputs_dir(output_dir, root)
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    lanes = _lane_source_dates(data_path, today=current.date())
    source_as_of = max((value for _, value in lanes), default="")

    if profile.name == "demo" and data_dir is None:
        identity, manifest_date = _manifest_identity(data_path / "manifest.json")
        if manifest_date:
            source_as_of = manifest_date
        snapshot_inputs = (str(data_path / "manifest.json"),)
    else:
        identity, snapshot_inputs = _local_identity(data_path)

    readiness_built_at = _readiness_built_at(data_path)
    freshness_state, freshness_message, refresh_command = _freshness(
        data_path,
        profile_key=profile.name,
        profile_label=profile_display_label(profile.name),
    )
    readiness_evidence_state, readiness_evidence_message = _readiness_evidence(
        root,
        data_path,
        profile_key=profile.name,
    )
    source_date = _parse_date(source_as_of)
    readiness_time = _parse_datetime(readiness_built_at)
    if (
        freshness_state == "current"
        and source_date is not None
        and readiness_time is not None
        and source_date > readiness_time.date()
    ):
        freshness_state = "stale"
        refresh_command, inspection_note = readiness_inspection_route(
            profile.name, profile_display_label(profile.name), data_path
        )
        freshness_message = f"Selected-profile source dates are newer than the saved readiness snapshot. {inspection_note}"
    if profile.name == "demo" and data_dir is None and not identity:
        freshness_state = "mixed" if (data_path / READINESS_FILES[0]).exists() else "missing"
        freshness_message = "The selected demo manifest is missing or invalid."

    return ProfileContext(
        profile_key=profile.name,
        profile_label=profile_display_label(profile.name),
        data_dir=data_path,
        outputs_dir=output_path,
        source_as_of=source_as_of,
        readiness_built_at=readiness_built_at,
        snapshot_identity=identity,
        snapshot_identity_short=identity[:12],
        freshness_state=freshness_state,
        freshness_message=freshness_message,
        refresh_command=refresh_command,
        coverage=_coverage_counts(data_path / READINESS_FILES[0]),
        lane_source_dates=lanes,
        snapshot_inputs=snapshot_inputs,
        readiness_evidence_state=readiness_evidence_state,
        readiness_evidence_message=readiness_evidence_message,
    )


def render_profile_context_text(context: ProfileContext) -> str:
    coverage = context.coverage
    return "\n".join(
        [
            f"Profile: {context.profile_label} ({context.profile_key})",
            f"Sources through: {context.source_as_of or 'unavailable'}",
            f"Readiness built: {context.readiness_built_at or 'unavailable'}",
            f"Snapshot: {context.snapshot_identity_short or 'unavailable'}",
            f"Freshness: {context.freshness_state} - {context.freshness_message}",
            (
                "Readiness evidence: "
                f"{context.readiness_evidence_state} - {context.readiness_evidence_message}"
            ),
            (
                f"Saved readiness coverage: price={coverage.price_ready}/{coverage.total}; "
                f"fundamentals={coverage.fundamentals_ready}/{coverage.total}; "
                f"DCF={coverage.dcf_ready}/{coverage.total}; peers={coverage.peer_ready}/{coverage.total}"
            ),
        ]
    )


def profile_context_payload(context: ProfileContext) -> dict[str, object]:
    payload = asdict(context)
    payload["data_dir"] = str(context.data_dir)
    payload["outputs_dir"] = str(context.outputs_dir)
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print selected data-profile truth without changing data.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--data-dir")
    parser.add_argument("--output-dir")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    context = build_profile_context(
        project_root=args.root,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
    )
    if args.json:
        print(json.dumps(profile_context_payload(context), indent=2, sort_keys=True))
    else:
        print(render_profile_context_text(context))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
