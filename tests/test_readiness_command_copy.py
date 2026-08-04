import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY_READINESS_COMMAND = re.compile(r"(?<![A-Za-z0-9_-])make readiness(?![A-Za-z0-9_-])")


def _legacy_readiness_occurrences() -> list[str]:
    occurrences: list[str] = []
    paths = [ROOT / "Makefile", *sorted((ROOT / "src").rglob("*.py"))]
    for path in paths:
        relative_path = path.relative_to(ROOT)
        for line_number, source_text in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not LEGACY_READINESS_COMMAND.search(source_text):
                continue
            if (
                relative_path == Path("Makefile")
                and "Deprecated no-write guard; exits 2" in source_text
            ):
                continue
            occurrences.append(f"{relative_path}:{line_number}: {source_text}")
    return occurrences


def test_legacy_readiness_command_is_limited_to_its_deprecated_guard_help_line():
    assert _legacy_readiness_occurrences() == []
