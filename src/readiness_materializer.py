from __future__ import annotations

import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

import pandas as pd

from src.paths import PROJECT_ROOT
from src.readiness_engine import READINESS_REPORT_NAMES, build_ticker_readiness_report
from src.readiness_source_boundary import (
    ReadinessSourceBoundaryError,
    validate_readiness_source_boundary,
)


class ReadinessMaterializationError(RuntimeError):
    """Raised when the fixed local readiness package cannot be safely published."""


@dataclass(frozen=True)
class ReadinessMaterializationResult:
    profile: str
    output_dir: Path
    files: tuple[Path, ...]
    row_counts: Mapping[str, int]


def _publication_checkpoint(_name: str) -> None:
    """Fault-injection seam for crash-consistency tests."""


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def _lstat(path: Path):
    try:
        return path.lstat()
    except FileNotFoundError:
        return None


def _validate_directory_component(path: Path, *, allow_missing: bool) -> bool:
    metadata = _lstat(path)
    if metadata is None:
        if allow_missing:
            return False
        raise ReadinessMaterializationError(f"Required destination directory is missing: {path}")
    if stat.S_ISLNK(metadata.st_mode):
        raise ReadinessMaterializationError(f"Destination path must not be a symbolic link: {path}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise ReadinessMaterializationError(f"Destination component must be a directory: {path}")
    return True


def _validate_absent_recovery_path(path: Path) -> None:
    metadata = _lstat(path)
    if metadata is None:
        return
    if stat.S_ISLNK(metadata.st_mode):
        kind = "symbolic link"
    else:
        kind = "leftover path"
    raise ReadinessMaterializationError(
        f"Refusing materialization because {kind} {path} requires operator recovery; "
        "inspect the fixed staging/backup residue and recover one authoritative snapshot manually."
    )


def _validate_complete_snapshot(destination: Path, expected_names: set[str]) -> bool:
    metadata = _lstat(destination)
    if metadata is None:
        return False
    if stat.S_ISLNK(metadata.st_mode):
        raise ReadinessMaterializationError(f"Destination path must not be a symbolic link: {destination}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise ReadinessMaterializationError(f"Destination snapshot must be a directory: {destination}")

    entries = list(destination.iterdir())
    actual_names = {entry.name for entry in entries}
    unexpected = sorted(actual_names - expected_names)
    missing = sorted(expected_names - actual_names)
    if unexpected:
        raise ReadinessMaterializationError(
            f"Fixed readiness destination contains an unexpected entry that will not be removed: {unexpected[0]}"
        )
    if missing:
        raise ReadinessMaterializationError(
            f"Fixed readiness destination is not a complete 11-file snapshot; missing: {', '.join(missing)}"
        )
    for entry in entries:
        entry_metadata = entry.lstat()
        if stat.S_ISLNK(entry_metadata.st_mode):
            raise ReadinessMaterializationError(f"Destination entry must not be a symbolic link: {entry}")
        if not stat.S_ISREG(entry_metadata.st_mode):
            raise ReadinessMaterializationError(f"Destination entry must be a regular file: {entry}")
    return True


def _validate_destination_boundary(
    resolved_root: Path, profile: str
) -> tuple[Path, Path, Path, Path, bool]:
    outputs = resolved_root / "outputs"
    local = outputs / "local"
    derived = local / "derived"
    destination = derived / profile
    staging = derived / f".{profile}.readiness-staging"
    backup = derived / f".{profile}.readiness-backup"

    for component in (outputs, local, derived):
        _validate_directory_component(component, allow_missing=True)
    resolved_derived = derived.resolve(strict=False)
    if not resolved_derived.is_relative_to(resolved_root):
        raise ReadinessMaterializationError("Resolved derived readiness root escapes the repository root.")

    _validate_absent_recovery_path(staging)
    _validate_absent_recovery_path(backup)
    expected_names = {f"{name}.csv" for name in READINESS_REPORT_NAMES}
    prior_exists = _validate_complete_snapshot(destination, expected_names)
    return resolved_derived, destination, staging, backup, prior_exists


def _create_destination_parents(resolved_root: Path, derived: Path) -> None:
    for path in (resolved_root / "outputs", resolved_root / "outputs/local", derived):
        if _lstat(path) is None:
            path.mkdir()
        _validate_directory_component(path, allow_missing=False)
        if not path.resolve(strict=True).is_relative_to(resolved_root):
            raise ReadinessMaterializationError(f"Created destination component escapes repository root: {path}")


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _serialize_staging(staging: Path, reports: Mapping[str, pd.DataFrame]) -> None:
    staging.mkdir()
    try:
        for name in READINESS_REPORT_NAMES:
            destination = staging / f"{name}.csv"
            with destination.open("x", encoding="utf-8", newline="") as handle:
                reports[name].to_csv(handle, index=False)
                handle.flush()
                os.fsync(handle.fileno())
        _fsync_directory(staging)
    except Exception:
        shutil.rmtree(staging)
        raise


def _restore_after_handled_failure(
    *,
    derived: Path,
    destination: Path,
    staging: Path,
    backup: Path,
    prior_moved: bool,
    published: bool,
) -> None:
    if published and _lstat(destination) is not None:
        os.replace(destination, staging)
        _fsync_directory(derived)
    if prior_moved and _lstat(backup) is not None:
        os.replace(backup, destination)
        _fsync_directory(derived)
    if _lstat(staging) is not None:
        shutil.rmtree(staging)
    _fsync_directory(derived)


def _publish_snapshot(
    *,
    derived: Path,
    destination: Path,
    staging: Path,
    backup: Path,
    prior_exists: bool,
) -> None:
    prior_moved = False
    published = False
    try:
        _fsync_directory(derived)
        _publication_checkpoint("before_backup_rename")
        if prior_exists:
            os.replace(destination, backup)
            prior_moved = True
            _fsync_directory(derived)
        _publication_checkpoint("after_backup_rename")
        _publication_checkpoint("before_publish")
        os.replace(staging, destination)
        published = True
        _fsync_directory(derived)
        _publication_checkpoint("after_publish")
        if prior_moved:
            _publication_checkpoint("during_cleanup")
    except Exception as publication_error:
        try:
            _restore_after_handled_failure(
                derived=derived,
                destination=destination,
                staging=staging,
                backup=backup,
                prior_moved=prior_moved,
                published=published,
            )
        except Exception as restoration_error:
            raise ReadinessMaterializationError(
                "Readiness publication failed and automatic restoration could not complete; "
                "operator recovery is required."
            ) from restoration_error
        raise ReadinessMaterializationError(
            "Readiness publication failed; restored prior snapshot and removed owned staging data."
        ) from publication_error

    if prior_moved:
        try:
            shutil.rmtree(backup)
            _fsync_directory(derived)
        except Exception as cleanup_error:
            raise ReadinessMaterializationError(
                "Readiness snapshot is complete, but backup cleanup failed; operator recovery is required."
            ) from cleanup_error


def materialize_readiness_snapshot(
    base_dir: Path | str | None = None,
    *,
    profile: str,
    confirm_materialize: bool = False,
) -> ReadinessMaterializationResult:
    """Publish one crash-consistent readiness package to the fixed ignored local path."""

    if confirm_materialize is not True:
        raise ReadinessMaterializationError(
            "Readiness materialization requires explicit confirm_materialize=True."
        )

    lexical_root = _lexical_absolute(Path(base_dir) if base_dir is not None else PROJECT_ROOT)
    try:
        selected = validate_readiness_source_boundary(lexical_root, profile)
    except ReadinessSourceBoundaryError as error:
        raise ReadinessMaterializationError(str(error)) from error

    resolved_root = lexical_root.resolve(strict=True)
    resolved_derived, destination, staging, backup, prior_exists = _validate_destination_boundary(
        resolved_root, selected.name
    )

    reports = build_ticker_readiness_report(
        resolved_root,
        data_dir=selected.data_dir,
        output_dir=selected.outputs_dir,
        write_outputs=False,
    )
    if tuple(reports) != READINESS_REPORT_NAMES:
        raise ReadinessMaterializationError(
            "Readiness builder report contract mismatch; refusing to publish an incomplete or expanded package."
        )
    if any(not isinstance(reports[name], pd.DataFrame) for name in READINESS_REPORT_NAMES):
        raise ReadinessMaterializationError("Readiness builder report contract requires 11 pandas DataFrames.")

    _create_destination_parents(resolved_root, resolved_derived)
    try:
        _serialize_staging(staging, reports)
    except Exception as serialization_error:
        raise ReadinessMaterializationError(
            "Readiness staging serialization failed before publication; no snapshot was changed."
        ) from serialization_error
    _publish_snapshot(
        derived=resolved_derived,
        destination=destination,
        staging=staging,
        backup=backup,
        prior_exists=prior_exists,
    )

    files = tuple(sorted(destination / f"{name}.csv" for name in READINESS_REPORT_NAMES))
    row_counts = MappingProxyType({name: int(len(reports[name])) for name in sorted(READINESS_REPORT_NAMES)})
    return ReadinessMaterializationResult(
        profile=selected.name,
        output_dir=destination,
        files=files,
        row_counts=row_counts,
    )
