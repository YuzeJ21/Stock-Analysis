from __future__ import annotations

import subprocess
from pathlib import Path


def _git_changed_paths(root: Path, paths: list[Path]) -> set[str] | None:
    rel_paths = [path.relative_to(root).as_posix() for path in paths if path.exists()]
    if not rel_paths:
        return set()
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--", *rel_paths],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    changed: set[str] = set()
    for line in result.stdout.splitlines():
        path_text = line[3:].strip()
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1].strip()
        if path_text:
            changed.add(path_text)
    return changed


def generated_artifact_stale_warning(
    *,
    root: Path,
    generated_paths: list[Path],
    source_paths: list[Path],
    display_root: Path,
    refresh_command: str = "make readiness or make status",
) -> str:
    existing_generated = [path for path in generated_paths if path.exists()]
    if not existing_generated:
        return ""
    oldest_generated_mtime = min(path.stat().st_mtime for path in existing_generated)
    newer_sources = [path for path in source_paths if path.exists() and path.stat().st_mtime > oldest_generated_mtime]
    if not newer_sources:
        return ""

    changed_paths = _git_changed_paths(root, newer_sources)
    if changed_paths is not None:
        newer_sources = [
            path for path in newer_sources if path.relative_to(root).as_posix() in changed_paths
        ]
        if not newer_sources:
            return ""

    relative_sources = [path.relative_to(display_root).as_posix() for path in newer_sources]
    sample = ", ".join(relative_sources[:4])
    if len(relative_sources) > 4:
        sample = f"{sample}, +{len(relative_sources) - 4} more"
    return (
        "Generated status artifacts may be stale because source CSVs changed after the last generated report "
        f"({sample}). Run {refresh_command} to refresh before relying on exact counts."
    )
