from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


PROVIDER_ENV_FILES = (".env", "config/provider_keys.env", ".env.local")
_ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_loaded_roots: set[Path] = set()


def reset_provider_environment_cache() -> None:
    _loaded_roots.clear()


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export "):].strip()
    if "=" not in stripped:
        return None
    key, raw_value = stripped.split("=", 1)
    key = key.strip()
    if not _ENV_KEY_PATTERN.match(key):
        return None

    value = raw_value.strip()
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        value = value[1:-1]
    else:
        value = value.split(" #", 1)[0].strip()
    return key, value


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for line in lines:
        parsed = _parse_env_line(line)
        if parsed is None:
            continue
        key, value = parsed
        values[key] = value
    return values


def load_provider_environment(project_root: str | Path | None = None, *, force: bool = False) -> dict[str, Any]:
    root = Path(project_root or os.getcwd()).resolve()
    if root in _loaded_roots and not force:
        return {
            "root": str(root),
            "loaded_files": [],
            "loaded_keys": [],
            "protected_keys": [],
            "already_loaded": True,
        }

    original_keys = set(os.environ)
    loaded_files: list[str] = []
    loaded_keys: set[str] = set()
    protected_keys: set[str] = set()

    for relative_path in PROVIDER_ENV_FILES:
        path = root / relative_path
        if not path.exists():
            continue
        values = _read_env_file(path)
        if not values:
            continue
        loaded_files.append(str(path))
        for key, value in values.items():
            if key in original_keys:
                protected_keys.add(key)
                continue
            os.environ[key] = value
            loaded_keys.add(key)

    _loaded_roots.add(root)
    return {
        "root": str(root),
        "loaded_files": loaded_files,
        "loaded_keys": sorted(loaded_keys),
        "protected_keys": sorted(protected_keys),
        "already_loaded": False,
    }
