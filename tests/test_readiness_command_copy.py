import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PERMITTED_LEGACY_READINESS_HELP_LINE = (
    '\t@echo "  make readiness        Deprecated no-write guard; exits 2"'
)
LEGACY_READINESS_COMMAND = re.compile(
    r"(?<![A-Za-z0-9_-])(?:make|\$\(MAKE\))[ \t]+readiness(?![A-Za-z0-9_-])"
)


def _legacy_readiness_occurrences(
    sources: list[tuple[Path, list[str]]] | None = None,
) -> list[str]:
    if sources is None:
        paths = [ROOT / "Makefile", *sorted((ROOT / "src").rglob("*.py"))]
        sources = [
            (path.relative_to(ROOT), path.read_text(encoding="utf-8").splitlines())
            for path in paths
        ]

    occurrences: list[tuple[str, bool]] = []
    for relative_path, lines in sources:
        for line_number, source_text in enumerate(lines, start=1):
            if not LEGACY_READINESS_COMMAND.search(source_text):
                continue
            occurrence = f"{relative_path}:{line_number}: {source_text}"
            if (
                relative_path == Path("Makefile")
                and source_text == PERMITTED_LEGACY_READINESS_HELP_LINE
            ):
                occurrences.append((occurrence, True))
                continue
            occurrences.append((occurrence, False))

    permitted_count = sum(is_permitted for _, is_permitted in occurrences)
    offenders = [
        occurrence
        for occurrence, is_permitted in occurrences
        if permitted_count != 1 or not is_permitted
    ]
    if permitted_count == 0:
        offenders.append(f"Makefile:0: {PERMITTED_LEGACY_READINESS_HELP_LINE}")
    return offenders


def test_legacy_readiness_command_is_limited_to_its_deprecated_guard_help_line():
    assert _legacy_readiness_occurrences() == []


def test_legacy_readiness_scanner_reports_both_command_forms_but_not_hyphenated_targets():
    occurrences = _legacy_readiness_occurrences(
        [
            (Path("Makefile"), [PERMITTED_LEGACY_READINESS_HELP_LINE]),
            (
                Path("src/example.py"),
                [
                    'literal = "make readiness"',
                    'recursive = "$(MAKE) readiness"',
                    'preview = "make readiness-preview"',
                    'snapshot = "$(MAKE) readiness-snapshot"',
                ],
            )
        ]
    )

    assert occurrences == [
        'src/example.py:1: literal = "make readiness"',
        'src/example.py:2: recursive = "$(MAKE) readiness"',
    ]


def test_legacy_readiness_scanner_accepts_shell_spaces_and_tabs_between_command_tokens():
    occurrences = _legacy_readiness_occurrences(
        [
            (Path("Makefile"), [PERMITTED_LEGACY_READINESS_HELP_LINE]),
            (
                Path("src/example.py"),
                [
                    'double_space = "make  readiness"',
                    'tab = "make\treadiness"',
                    'recursive_double_space = "$(MAKE)  readiness"',
                    'recursive_tab = "$(MAKE)\treadiness"',
                    'preview = "make\treadiness-preview"',
                    'snapshot = "$(MAKE)  readiness-snapshot"',
                ],
            )
        ]
    )

    assert occurrences == [
        'src/example.py:1: double_space = "make  readiness"',
        'src/example.py:2: tab = "make\treadiness"',
        'src/example.py:3: recursive_double_space = "$(MAKE)  readiness"',
        'src/example.py:4: recursive_tab = "$(MAKE)\treadiness"',
    ]


def test_legacy_readiness_scanner_rejects_a_missing_exact_help_exception():
    assert _legacy_readiness_occurrences([(Path("Makefile"), [])]) == [
        f"Makefile:0: {PERMITTED_LEGACY_READINESS_HELP_LINE}"
    ]


def test_legacy_readiness_scanner_rejects_duplicate_or_deceptive_help_exceptions():
    occurrences = _legacy_readiness_occurrences(
        [
            (
                Path("Makefile"),
                [
                    PERMITTED_LEGACY_READINESS_HELP_LINE,
                    PERMITTED_LEGACY_READINESS_HELP_LINE,
                    '@echo "make readiness Deprecated no-write guard; exits 2; extra text"',
                    '@echo "$(MAKE) readiness Deprecated no-write guard; exits 2"',
                ],
            )
        ]
    )

    assert occurrences == [
        f"Makefile:1: {PERMITTED_LEGACY_READINESS_HELP_LINE}",
        f"Makefile:2: {PERMITTED_LEGACY_READINESS_HELP_LINE}",
        'Makefile:3: @echo "make readiness Deprecated no-write guard; exits 2; extra text"',
        'Makefile:4: @echo "$(MAKE) readiness Deprecated no-write guard; exits 2"',
    ]
