from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PROFILE_ENV = "STOCK_RESEARCH_DATA_PROFILE"


@dataclass(frozen=True)
class DataProfile:
    """Named data and output roots for an isolated product profile."""

    name: str
    data_dir: Path
    outputs_dir: Path


_DATA_PROFILE_PATHS: dict[str, tuple[str, str]] = {
    "default": ("data", "outputs"),
    "demo": ("data/demo", "outputs/demo"),
    "local": ("data/local", "outputs/local"),
}

PROFILE_LABELS: dict[str, str] = {
    "default": "Default",
    "demo": "Demo",
    "local": "Local Research",
}


def profile_display_label(name: str) -> str:
    """Return the stable user-facing label for a known data profile."""

    normalized = str(name or "default").strip().lower()
    if normalized not in PROFILE_LABELS:
        available = ", ".join(sorted(PROFILE_LABELS))
        raise ValueError(f"Unknown data profile '{normalized}'. Choose one of: {available}.")
    return PROFILE_LABELS[normalized]


def resolve_project_root(project_root: Path | str | None = None) -> Path:
    """Return the repository root used for config and default data paths."""
    if project_root is None:
        return PROJECT_ROOT
    return Path(project_root).expanduser().resolve()


def resolve_data_profile(name: str | None = None, project_root: Path | str | None = None) -> DataProfile:
    """Resolve the requested data profile without creating or changing files."""

    root = resolve_project_root(project_root)
    profile_name = (name or os.getenv(DATA_PROFILE_ENV) or "default").strip().lower()
    if profile_name not in _DATA_PROFILE_PATHS:
        available = ", ".join(sorted(_DATA_PROFILE_PATHS))
        raise ValueError(f"Unknown data profile '{profile_name}'. Choose one of: {available}.")
    data_path, outputs_path = _DATA_PROFILE_PATHS[profile_name]
    return DataProfile(
        name=profile_name,
        data_dir=(root / data_path).resolve(),
        outputs_dir=(root / outputs_path).resolve(),
    )


def resolve_data_dir(data_dir: Path | str | None = None, project_root: Path | str | None = None) -> Path:
    root = resolve_project_root(project_root)
    if data_dir is None:
        return resolve_data_profile(project_root=root).data_dir
    path = Path(data_dir).expanduser()
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def resolve_outputs_dir(output_dir: Path | str | None = None, project_root: Path | str | None = None) -> Path:
    root = resolve_project_root(project_root)
    if output_dir is None:
        return resolve_data_profile(project_root=root).outputs_dir
    path = Path(output_dir).expanduser()
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def path_context(
    project_root: Path | str | None = None,
    data_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
) -> dict[str, str]:
    root = resolve_project_root(project_root)
    return {
        "project_root": str(root),
        "data_dir": str(resolve_data_dir(data_dir, root)),
        "outputs_dir": str(resolve_outputs_dir(output_dir, root)),
    }


def format_path_context(
    project_root: Path | str | None = None,
    data_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
) -> str:
    context = path_context(project_root=project_root, data_dir=data_dir, output_dir=output_dir)
    return (
        f"Project root: {context['project_root']}\n"
        f"Data dir: {context['data_dir']}\n"
        f"Outputs dir: {context['outputs_dir']}"
    )
