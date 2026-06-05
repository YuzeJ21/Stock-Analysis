"""Check public-facing text for unsupported advice or execution language."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


PUBLIC_ROOT_FILES = (
    "README.md",
    "ROADMAP.md",
    "PRODUCT_SPEC.md",
    "READINESS_MODEL.md",
    "DECISION_OUTPUT_MODEL.md",
)
PUBLIC_GLOBS = (
    "docs/*.md",
    "docs/assets/*.svg",
    "outputs/stock_reports/*.md",
)
PUBLIC_SOURCE_FILES = (
    "src/dashboard.py",
    "src/stock_report.py",
)

SAFE_CONTEXT_PATTERNS = (
    re.compile(
        r"\bdoes not [^.]*\b(?:place|connect|route|auto-trade|recommend|provide)[^.]*",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bis intentionally research-only and does not [^.]*",
        re.IGNORECASE,
    ),
    re.compile(r"\bnot investment advice\b", re.IGNORECASE),
    re.compile(r"\bresearch-only\b", re.IGNORECASE),
    re.compile(r"\bnot a trading system\b", re.IGNORECASE),
    re.compile(r"\bnot a trading bot\b", re.IGNORECASE),
    re.compile(r"\bdoes not place orders?\b", re.IGNORECASE),
    re.compile(r"\bdoes not connect to (?:a\s+)?brokers?\b", re.IGNORECASE),
    re.compile(r"\bdoes not provide allocation instructions\b", re.IGNORECASE),
    re.compile(r"\bdoes not provide .*direct recommendations\b", re.IGNORECASE),
    re.compile(r"\bno broker integration\b", re.IGNORECASE),
    re.compile(r"\bno order routing\b", re.IGNORECASE),
    re.compile(r"\bno auto-trading\b", re.IGNORECASE),
    re.compile(r"\bno direct buy/sell instructions\b", re.IGNORECASE),
    re.compile(r"\bno options recommendations\b", re.IGNORECASE),
    re.compile(r"\bwithout.*direct recommendation", re.IGNORECASE),
    re.compile(r"\bmust not produce unsupported buy/sell", re.IGNORECASE),
    re.compile(r"\bdo not produce unsupported buy/sell", re.IGNORECASE),
    re.compile(r"\bremove execution and direct recommendation wording\b", re.IGNORECASE),
)

FORBIDDEN_PATTERNS = {
    "direct_buy_call": re.compile(
        r"\b(?:buy|purchase)\s+(?:now|today|immediately|this\s+(?:stock|ticker|name)|shares?)\b",
        re.IGNORECASE,
    ),
    "direct_sell_call": re.compile(
        r"\b(?:sell|short)\s+(?:now|today|immediately|this\s+(?:stock|ticker|name)|shares?)\b",
        re.IGNORECASE,
    ),
    "direct_recommendation": re.compile(
        r"\b(?:we\s+)?recommend(?:s|ed|ing)?\s+(?:that\s+you\s+)?(?:buy|sell|short|hold)\b",
        re.IGNORECASE,
    ),
    "order_execution": re.compile(
        r"\b(?:place|execute|route|submit)\s+(?:an?\s+)?(?:orders?|trades?)\b",
        re.IGNORECASE,
    ),
    "broker_connection_enabled": re.compile(
        r"\b(?:connects?|integrates?|links?)\s+(?:to|with)\s+(?:a\s+)?brokers?\b",
        re.IGNORECASE,
    ),
    "auto_trading_enabled": re.compile(
        r"\bauto[- ]?trading\s+(?:enabled|engine|feature|mode|system|workflow)\b",
        re.IGNORECASE,
    ),
    "options_advice": re.compile(
        r"\b(?:recommend(?:s|ed|ing)?|advise(?:s|d)?|suggest(?:s|ed|ing)?)\s+"
        r"(?:an?\s+)?options?\s+(?:trade|strategy|position)\b",
        re.IGNORECASE,
    ),
}

INTERNAL_LEAK_PATTERNS = {
    "old_github_owner": re.compile(r"\bdavidjiang8888/Stock-Analysis\b", re.IGNORECASE),
    "codex_internal": re.compile(r"\b(?:Codex|\.codex|codex_internal_context)\b", re.IGNORECASE),
    "assistant_skill_leak": re.compile(
        r"\b(?:assistant\s+skills?|plugins?\s+can\s+help|Public\s+Equity\s+Investing|Investment\s+Banking)\b",
        re.IGNORECASE,
    ),
    "internal_pr_note": re.compile(r"\b(?:draft\s+PR|PR\s+#\d+|pull/\d+|internal\s+thread)\b", re.IGNORECASE),
}


@dataclass(frozen=True)
class WordingMatch:
    path: str
    line_number: int
    rule: str
    text: str


def public_paths(repo_root: Path) -> list[Path]:
    paths = [repo_root / path for path in PUBLIC_ROOT_FILES]
    for pattern in PUBLIC_GLOBS:
        paths.extend(sorted(repo_root.glob(pattern)))
    paths.extend(repo_root / path for path in PUBLIC_SOURCE_FILES)
    return [path for path in paths if path.exists() and path.is_file()]


def strip_safe_contexts(line: str) -> str:
    cleaned = line
    for pattern in SAFE_CONTEXT_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    return cleaned


def find_forbidden_matches(text: str, *, path: str) -> list[WordingMatch]:
    matches: list[WordingMatch] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        cleaned = strip_safe_contexts(line)
        for rule, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(cleaned):
                matches.append(WordingMatch(path=path, line_number=line_number, rule=rule, text=line.strip()))
        for rule, pattern in INTERNAL_LEAK_PATTERNS.items():
            if pattern.search(line):
                matches.append(WordingMatch(path=path, line_number=line_number, rule=rule, text=line.strip()))
    return matches


def scan_public_files(repo_root: Path) -> tuple[int, list[WordingMatch]]:
    matches: list[WordingMatch] = []
    paths = public_paths(repo_root)
    for path in paths:
        relative_path = path.relative_to(repo_root).as_posix()
        text = path.read_text(encoding="utf-8")
        matches.extend(find_forbidden_matches(text, path=relative_path))
    return len(paths), matches


def build_report(scanned_count: int, matches: list[WordingMatch]) -> str:
    lines = [
        "Public Wording Check",
        "Read-only: this command scans public text and does not rewrite files.",
        "Guardrail-safe phrases such as no broker integration, no order routing,",
        "not investment advice, and no direct buy/sell instructions are allowed.",
        "It also flags internal development-tool, stale-repo, PR, and thread references.",
        "",
    ]
    if not matches:
        lines.extend(
            [
                "Public wording check passed.",
                f"Scanned public files: {scanned_count}",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "Public wording check failed.",
            "Review these lines before sharing or staging public-facing changes:",
        ]
    )
    for match in matches:
        lines.append(f"- {match.path}:{match.line_number} [{match.rule}] {match.text}")
    return "\n".join(lines)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    scanned_count, matches = scan_public_files(repo_root)
    print(build_report(scanned_count, matches))
    return 1 if matches else 0


if __name__ == "__main__":
    raise SystemExit(main())
