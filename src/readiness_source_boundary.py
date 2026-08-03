from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

from src.paths import DataProfile, PROJECT_ROOT


class ReadinessSourceBoundaryError(ValueError):
    """Raised before a readiness source path can be resolved or read unsafely."""


_PROFILE_PATHS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "default": (("data",), ("outputs",)),
    "demo": (("data", "demo"), ("outputs", "demo")),
    "local": (("data", "local"), ("outputs", "local")),
}

READINESS_SOURCE_FILENAMES: tuple[str, ...] = (
    "config/readiness.yml",
    "universe_master.csv",
    "universe_active.csv",
    "universe.csv",
    "holdings.csv",
    "prices.csv",
    "fundamentals.csv",
    "peers.csv",
    "peer_candidates.csv",
    "earnings.csv",
    "analyst_estimates.csv",
)

READINESS_SOURCE_FILE_NAMES: tuple[str, ...] = READINESS_SOURCE_FILENAMES[1:]

_STAGED_SOURCE_DIRS: tuple[tuple[str, ...], ...] = (
    ("staged",),
    ("staged", "prices"),
    ("staged", "fundamentals"),
    ("staged", "earnings"),
    ("staged", "analyst_estimates"),
)


def _lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def _lstat(path: Path):
    try:
        return path.lstat()
    except FileNotFoundError:
        return None


def _validate_directory(path: Path, *, required: bool) -> bool:
    metadata = _lstat(path)
    if metadata is None:
        if required:
            raise ReadinessSourceBoundaryError(f"Readiness source directory is missing: {path}")
        return False
    if stat.S_ISLNK(metadata.st_mode):
        raise ReadinessSourceBoundaryError(f"Readiness source path must not be a symbolic link: {path}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise ReadinessSourceBoundaryError(f"Readiness source path must be a directory: {path}")
    return True


def _validate_optional_regular_file(path: Path) -> None:
    metadata = _lstat(path)
    if metadata is None:
        return
    if stat.S_ISLNK(metadata.st_mode):
        raise ReadinessSourceBoundaryError(f"Readiness source path must not be a symbolic link: {path}")
    if not stat.S_ISREG(metadata.st_mode):
        raise ReadinessSourceBoundaryError(f"Readiness source path must be a regular file: {path}")


def validate_readiness_source_boundary(project_root: Path, profile_name: str) -> DataProfile:
    """Validate lexical named readiness sources before returning resolved paths."""

    if not isinstance(profile_name, str) or profile_name not in _PROFILE_PATHS:
        raise ReadinessSourceBoundaryError(
            f"Unknown readiness profile {profile_name!r}; choose exactly one of: default, demo, local."
        )

    lexical_root = _lexical_absolute(Path(project_root) if project_root is not None else PROJECT_ROOT)
    _validate_directory(lexical_root, required=True)
    data_components, output_components = _PROFILE_PATHS[profile_name]

    current = lexical_root
    for component in data_components:
        current = current / component
        _validate_directory(current, required=True)
    lexical_data_dir = current

    for name in READINESS_SOURCE_FILE_NAMES:
        _validate_optional_regular_file(lexical_data_dir / name)

    for relative_parts in _STAGED_SOURCE_DIRS:
        staged_path = lexical_data_dir.joinpath(*relative_parts)
        if not _validate_directory(staged_path, required=False):
            continue
        if relative_parts != ("staged",):
            for candidate in staged_path.glob("*.csv"):
                _validate_optional_regular_file(candidate)

    config_dir = lexical_root / "config"
    if _validate_directory(config_dir, required=False):
        _validate_optional_regular_file(config_dir / "readiness.yml")

    resolved_root = lexical_root.resolve(strict=True)
    resolved_data_dir = lexical_data_dir.resolve(strict=True)
    if not resolved_data_dir.is_relative_to(resolved_root):
        raise ReadinessSourceBoundaryError("Resolved readiness source directory escapes the repository root.")
    resolved_outputs_dir = resolved_root.joinpath(*output_components).resolve(strict=False)
    return DataProfile(
        name=profile_name,
        data_dir=resolved_data_dir,
        outputs_dir=resolved_outputs_dir,
    )


def _update_identity_field(digest, label: bytes, payload: bytes) -> None:
    digest.update(len(label).to_bytes(8, "big"))
    digest.update(label)
    digest.update(len(payload).to_bytes(8, "big"))
    digest.update(payload)


def _read_exact_regular_file(path: Path) -> bytes | None:
    metadata = _lstat(path)
    if metadata is None:
        return None
    if stat.S_ISLNK(metadata.st_mode):
        raise ReadinessSourceBoundaryError(f"Readiness source path must not be a symbolic link: {path}")
    if not stat.S_ISREG(metadata.st_mode):
        raise ReadinessSourceBoundaryError(f"Readiness source path must be a regular file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ReadinessSourceBoundaryError(
            f"Readiness source changed before it could be read safely: {path}"
        ) from error
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            metadata.st_dev,
            metadata.st_ino,
        ):
            raise ReadinessSourceBoundaryError(
                f"Readiness source changed before it could be read safely: {path}"
            )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(descriptor)


def readiness_input_identity(project_root: Path, profile_name: str) -> str:
    """Hash the selected profile and only its exact named readiness inputs.

    Adding, removing, reordering, or changing any input that can affect readiness
    comparison fields requires a deliberate readiness method-version review.
    """

    lexical_root = _lexical_absolute(Path(project_root) if project_root is not None else PROJECT_ROOT)
    selected = validate_readiness_source_boundary(lexical_root, profile_name)
    inputs: list[tuple[str, Path]] = []
    for name in READINESS_SOURCE_FILENAMES:
        if name == "config/readiness.yml":
            path = lexical_root / "config/readiness.yml"
        else:
            path = selected.data_dir / name
        relative = path.relative_to(lexical_root).as_posix()
        inputs.append((relative, path))

    digest = hashlib.sha256()
    _update_identity_field(digest, b"profile", selected.name.encode("utf-8"))
    for relative, path in sorted(inputs, key=lambda item: item[0]):
        payload = _read_exact_regular_file(path)
        _update_identity_field(digest, b"path", relative.encode("utf-8"))
        if payload is None:
            _update_identity_field(digest, b"state", b"absent")
        else:
            _update_identity_field(digest, b"state", b"present")
            _update_identity_field(digest, b"bytes", payload)
    return digest.hexdigest()
