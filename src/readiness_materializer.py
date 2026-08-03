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


class _PublicationRaceError(ReadinessMaterializationError):
    """Raised when a validated publication path changes before mutation."""


_PathIdentity = tuple[int, int]


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


def _path_identity(path: Path) -> _PathIdentity | None:
    metadata = _lstat(path)
    if metadata is None:
        return None
    return (metadata.st_dev, metadata.st_ino)


def _require_identity(path: Path, expected: _PathIdentity, *, label: str) -> None:
    metadata = _lstat(path)
    if (
        metadata is None
        or stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
        or (metadata.st_dev, metadata.st_ino) != expected
    ):
        raise _PublicationRaceError(
            f"{label} changed after validation; preserve all fixed-path residue for operator recovery."
        )


def _require_absent(path: Path, *, label: str) -> None:
    if _lstat(path) is not None:
        raise _PublicationRaceError(
            f"{label} appeared after validation; preserve it for operator recovery."
        )


def _require_complete_snapshot(path: Path, expected_names: set[str], *, label: str) -> None:
    try:
        complete = _validate_complete_snapshot(path, expected_names)
    except ReadinessMaterializationError as error:
        raise _PublicationRaceError(
            f"{label} changed after validation; preserve it for operator recovery."
        ) from error
    if not complete:
        raise _PublicationRaceError(
            f"{label} disappeared after validation; operator recovery is required."
        )


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


def _serialize_staging(staging: Path, reports: Mapping[str, pd.DataFrame]) -> _PathIdentity:
    staging_identity: _PathIdentity | None = None
    directory_descriptor: int | None = None
    try:
        staging.mkdir()
        staging_identity = _path_identity(staging)
        if staging_identity is None:
            raise _PublicationRaceError("Created staging directory became unavailable; operator recovery is required.")
        _publication_checkpoint("after_staging_create")
        _require_identity(staging, staging_identity, label="Readiness staging directory")
        directory_descriptor = os.open(
            staging,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        descriptor_metadata = os.fstat(directory_descriptor)
        if (descriptor_metadata.st_dev, descriptor_metadata.st_ino) != staging_identity:
            raise _PublicationRaceError(
                "Readiness staging directory changed while opening it; operator recovery is required."
            )
        for name in READINESS_REPORT_NAMES:
            _require_identity(staging, staging_identity, label="Readiness staging directory")
            file_descriptor = os.open(
                f"{name}.csv",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o666,
                dir_fd=directory_descriptor,
            )
            with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
                reports[name].to_csv(handle, index=False)
                handle.flush()
                os.fsync(handle.fileno())
        os.fsync(directory_descriptor)
        _require_identity(staging, staging_identity, label="Readiness staging directory")
        return staging_identity
    except Exception as serialization_error:
        _publication_checkpoint("before_staging_cleanup")
        if staging_identity is not None:
            if _path_identity(staging) == staging_identity:
                shutil.rmtree(staging)
            else:
                raise _PublicationRaceError(
                    "Readiness staging changed before cleanup; replacement paths require operator recovery."
                ) from serialization_error
        raise
    finally:
        if directory_descriptor is not None:
            os.close(directory_descriptor)


def _validate_publication_state(
    *,
    destination: Path,
    staging: Path,
    backup: Path,
    prior_exists: bool,
    prior_moved: bool,
    staging_identity: _PathIdentity,
    prior_identity: _PathIdentity | None,
) -> None:
    expected_names = {f"{name}.csv" for name in READINESS_REPORT_NAMES}
    _require_identity(staging, staging_identity, label="Readiness staging directory")
    _require_complete_snapshot(staging, expected_names, label="Readiness staging directory")
    if prior_moved:
        if prior_identity is None:
            raise _PublicationRaceError("Readiness backup identity is unavailable; operator recovery is required.")
        _require_identity(backup, prior_identity, label="Readiness backup directory")
        _require_complete_snapshot(backup, expected_names, label="Readiness backup directory")
        _require_absent(destination, label="Canonical readiness destination")
        return
    _require_absent(backup, label="Readiness backup directory")
    if prior_exists:
        if prior_identity is None:
            raise _PublicationRaceError("Prior readiness identity is unavailable; operator recovery is required.")
        _require_identity(destination, prior_identity, label="Canonical readiness destination")
        _require_complete_snapshot(destination, expected_names, label="Canonical readiness destination")
    else:
        _require_absent(destination, label="Canonical readiness destination")


def _restore_after_handled_failure(
    *,
    derived: Path,
    destination: Path,
    staging: Path,
    backup: Path,
    prior_moved: bool,
    published: bool,
    staging_identity: _PathIdentity,
    prior_identity: _PathIdentity | None,
) -> None:
    if published and _lstat(destination) is not None:
        _require_identity(destination, staging_identity, label="Published readiness destination")
        _require_complete_snapshot(
            destination,
            {f"{name}.csv" for name in READINESS_REPORT_NAMES},
            label="Published readiness destination",
        )
        _require_absent(staging, label="Readiness staging directory")
        os.replace(destination, staging)
        _fsync_directory(derived)
    if prior_moved and _lstat(backup) is not None:
        if prior_identity is None:
            raise _PublicationRaceError("Prior readiness identity is unavailable; operator recovery is required.")
        _require_identity(backup, prior_identity, label="Readiness backup directory")
        _require_complete_snapshot(
            backup,
            {f"{name}.csv" for name in READINESS_REPORT_NAMES},
            label="Readiness backup directory",
        )
        _require_absent(destination, label="Canonical readiness destination")
        os.replace(backup, destination)
        _fsync_directory(derived)
    if _lstat(staging) is not None:
        _require_identity(staging, staging_identity, label="Readiness staging directory")
        shutil.rmtree(staging)
    _fsync_directory(derived)


def _publish_snapshot(
    *,
    derived: Path,
    destination: Path,
    staging: Path,
    backup: Path,
    prior_exists: bool,
    staging_identity: _PathIdentity,
    prior_identity: _PathIdentity | None,
) -> None:
    prior_moved = False
    published = False
    try:
        _fsync_directory(derived)
        _publication_checkpoint("before_backup_rename")
        _validate_publication_state(
            destination=destination,
            staging=staging,
            backup=backup,
            prior_exists=prior_exists,
            prior_moved=False,
            staging_identity=staging_identity,
            prior_identity=prior_identity,
        )
        if prior_exists:
            os.replace(destination, backup)
            prior_moved = True
            _fsync_directory(derived)
        _publication_checkpoint("after_backup_rename")
        _validate_publication_state(
            destination=destination,
            staging=staging,
            backup=backup,
            prior_exists=prior_exists,
            prior_moved=prior_moved,
            staging_identity=staging_identity,
            prior_identity=prior_identity,
        )
        _publication_checkpoint("before_publish")
        _validate_publication_state(
            destination=destination,
            staging=staging,
            backup=backup,
            prior_exists=prior_exists,
            prior_moved=prior_moved,
            staging_identity=staging_identity,
            prior_identity=prior_identity,
        )
        os.replace(staging, destination)
        published = True
        _require_identity(destination, staging_identity, label="Published readiness destination")
        _fsync_directory(derived)
        _publication_checkpoint("after_publish")
        _require_identity(destination, staging_identity, label="Published readiness destination")
        _require_complete_snapshot(
            destination,
            {f"{name}.csv" for name in READINESS_REPORT_NAMES},
            label="Published readiness destination",
        )
        if prior_moved:
            _publication_checkpoint("during_cleanup")
            if prior_identity is None:
                raise _PublicationRaceError("Prior readiness identity is unavailable; operator recovery is required.")
            _require_identity(backup, prior_identity, label="Readiness backup directory")
            _require_complete_snapshot(
                backup,
                {f"{name}.csv" for name in READINESS_REPORT_NAMES},
                label="Readiness backup directory",
            )
    except Exception as publication_error:
        try:
            _restore_after_handled_failure(
                derived=derived,
                destination=destination,
                staging=staging,
                backup=backup,
                prior_moved=prior_moved,
                published=published,
                staging_identity=staging_identity,
                prior_identity=prior_identity,
            )
        except Exception as restoration_error:
            raise ReadinessMaterializationError(
                "Readiness publication failed and automatic restoration could not complete; "
                "operator recovery is required."
            ) from restoration_error
        if isinstance(publication_error, _PublicationRaceError):
            raise ReadinessMaterializationError(
                "Readiness publication paths changed after validation; raced-in entries were preserved for "
                "operator recovery."
            ) from publication_error
        raise ReadinessMaterializationError(
            "Readiness publication failed; restored prior snapshot and removed owned staging data."
        ) from publication_error

    if prior_moved:
        try:
            _publication_checkpoint("before_backup_cleanup")
            if prior_identity is None:
                raise _PublicationRaceError("Prior readiness identity is unavailable; operator recovery is required.")
            _require_identity(backup, prior_identity, label="Readiness backup directory")
            _require_complete_snapshot(
                backup,
                {f"{name}.csv" for name in READINESS_REPORT_NAMES},
                label="Readiness backup directory",
            )
            shutil.rmtree(backup)
            _fsync_directory(derived)
        except Exception as cleanup_error:
            expected_names = {f"{name}.csv" for name in READINESS_REPORT_NAMES}
            if _lstat(backup) is None:
                _fsync_directory(derived)
                return
            try:
                backup_complete = _validate_complete_snapshot(backup, expected_names)
            except ReadinessMaterializationError:
                _validate_complete_snapshot(destination, expected_names)
                _fsync_directory(backup)
                _fsync_directory(derived)
                raise ReadinessMaterializationError(
                    "Readiness backup cleanup partially failed; the complete new canonical snapshot and "
                    "explicit incomplete backup residue were preserved for operator recovery."
                ) from cleanup_error
            if backup_complete:
                try:
                    _restore_after_handled_failure(
                        derived=derived,
                        destination=destination,
                        staging=staging,
                        backup=backup,
                        prior_moved=True,
                        published=True,
                        staging_identity=staging_identity,
                        prior_identity=prior_identity,
                    )
                except Exception as restoration_error:
                    raise ReadinessMaterializationError(
                        "Readiness backup cleanup failed and automatic restoration could not complete; "
                        "operator recovery is required."
                    ) from restoration_error
                raise ReadinessMaterializationError(
                    "Readiness backup cleanup failed; restored prior snapshot and removed the complete new staging set."
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
    resolved_derived, destination, staging, backup, _prior_exists = _validate_destination_boundary(
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

    resolved_derived, destination, staging, backup, prior_exists = _validate_destination_boundary(
        resolved_root, selected.name
    )
    _create_destination_parents(resolved_root, resolved_derived)
    resolved_derived, destination, staging, backup, prior_exists = _validate_destination_boundary(
        resolved_root, selected.name
    )
    prior_identity = _path_identity(destination) if prior_exists else None
    try:
        staging_identity = _serialize_staging(staging, reports)
    except _PublicationRaceError as serialization_error:
        raise ReadinessMaterializationError(
            "Readiness staging identity changed; replacement paths were preserved for operator recovery."
        ) from serialization_error
    except FileExistsError as serialization_error:
        raise ReadinessMaterializationError(
            "Readiness staging appeared before creation; preserve it for operator recovery."
        ) from serialization_error
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
        staging_identity=staging_identity,
        prior_identity=prior_identity,
    )

    files = tuple(sorted(destination / f"{name}.csv" for name in READINESS_REPORT_NAMES))
    row_counts = MappingProxyType({name: int(len(reports[name])) for name in sorted(READINESS_REPORT_NAMES)})
    return ReadinessMaterializationResult(
        profile=selected.name,
        output_dir=destination,
        files=files,
        row_counts=row_counts,
    )
