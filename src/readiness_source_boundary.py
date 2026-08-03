from __future__ import annotations

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

READINESS_SOURCE_FILE_NAMES: tuple[str, ...] = (
    "universe.csv",
    "universe_master.csv",
    "universe_active.csv",
    "holdings.csv",
    "prices.csv",
    "fundamentals.csv",
    "earnings.csv",
    "analyst_estimates.csv",
    "peers.csv",
    "peer_candidates.csv",
)

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
