from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from src.paths import resolve_data_profile, resolve_project_root


DATA_SUBDIRECTORIES = ("imports", "reports", "outputs")
EXCLUDED_DATA_DIRECTORIES = {"backups", "cache", "demo", "raw", "rejected", "staged", "templates", "local"}
EXCLUDED_OUTPUT_DIRECTORIES = {"browser_audits", "demo", "local", "staging", "stock_reports"}


def _copy_file(source: Path, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return 1


def _copy_tree(source: Path, destination: Path) -> int:
    if not source.exists():
        return 0
    count = 0
    for path in sorted(source.rglob("*")):
        if path.is_file():
            count += _copy_file(path, destination / path.relative_to(source))
    return count


def seed_local_profile(base_dir: Path | str | None = None, *, overwrite: bool = False) -> dict[str, Any]:
    """Seed the ignored local profile from canonical data without copying caches or evidence churn."""

    root = resolve_project_root(base_dir)
    profile = resolve_data_profile("local", root)
    if profile.data_dir.exists() and any(profile.data_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"Local profile already exists at {profile.data_dir}; pass overwrite=True to replace it.")
    if profile.data_dir.exists():
        shutil.rmtree(profile.data_dir)
    if profile.outputs_dir.exists():
        shutil.rmtree(profile.outputs_dir)
    profile.data_dir.mkdir(parents=True)
    profile.outputs_dir.mkdir(parents=True)

    source_data = root / "data"
    source_outputs = root / "outputs"
    files_copied = 0
    for path in sorted(source_data.iterdir()):
        if path.is_file():
            files_copied += _copy_file(path, profile.data_dir / path.name)
        elif path.is_dir() and path.name in DATA_SUBDIRECTORIES:
            files_copied += _copy_tree(path, profile.data_dir / path.name)

    for path in sorted(source_outputs.iterdir()):
        if path.is_file():
            files_copied += _copy_file(path, profile.outputs_dir / path.name)

    marker = {
        "profile": "local",
        "source_data_dir": str(source_data),
        "source_outputs_dir": str(source_outputs),
        "files_copied": files_copied,
        "excluded_data_directories": sorted(EXCLUDED_DATA_DIRECTORIES),
        "excluded_output_directories": sorted(EXCLUDED_OUTPUT_DIRECTORIES),
    }
    (profile.data_dir / ".profile_seed.json").write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "seeded", **marker, "data_dir": str(profile.data_dir), "outputs_dir": str(profile.outputs_dir)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the ignored local data profile from canonical local files.")
    parser.add_argument("--root", help="Project root. Defaults to this repository.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing local profile.")
    args = parser.parse_args()
    print(json.dumps(seed_local_profile(args.root, overwrite=args.overwrite), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
