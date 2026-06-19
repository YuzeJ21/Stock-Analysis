from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class BrowserQaEvidence:
    name: str
    path: Path
    route: str
    expected_markers: tuple[str, ...]
    min_width: int
    min_height: int
    use: str


DEFAULT_BROWSER_QA_EVIDENCE: tuple[BrowserQaEvidence, ...] = (
    BrowserQaEvidence(
        name="LinkedIn public dashboard thumbnail",
        path=Path("docs/assets/linkedin-public-dashboard.png"),
        route="http://localhost:8501/?mode=public",
        expected_markers=("research-loop-strip", "Public visitor mode", "Data readiness first"),
        min_width=1200,
        min_height=600,
        use="LinkedIn Featured and GitHub preview image.",
    ),
    BrowserQaEvidence(
        name="Public visitor home screenshot",
        path=Path("docs/assets/public-demo-home-real.jpg"),
        route="http://localhost:8501/?mode=public",
        expected_markers=("Research paths", "Review one stock", "Improve data coverage", "Inspect proof"),
        min_width=1000,
        min_height=600,
        use="README first-screen product preview.",
    ),
    BrowserQaEvidence(
        name="Operator metrics lane screenshot",
        path=Path("docs/assets/operator-data-health-metrics-real.jpg"),
        route="http://localhost:8501/?mode=operator&page=data-health&lane=metrics&drawer=metrics",
        expected_markers=("research-loop-strip", "ops-mode-strip", "Operator Queue", "Review details"),
        min_width=1000,
        min_height=600,
        use="Operator-mode proof that Data Health stays readiness-gated and copy-only.",
    ),
)


def _png_size(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 24:
        return None
    return struct.unpack(">II", data[16:24])


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"\xff\xd8"):
        return None
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            return None
        segment_length = struct.unpack(">H", data[index:index + 2])[0]
        if segment_length < 2 or index + segment_length > len(data):
            return None
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            height, width = struct.unpack(">HH", data[index + 3:index + 7])
            return width, height
        index += segment_length
    return None


def image_size(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()
    return _png_size(data) or _jpeg_size(data)


def browser_qa_evidence_rows(
    root: Path,
    evidence: Iterable[BrowserQaEvidence] = DEFAULT_BROWSER_QA_EVIDENCE,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in evidence:
        absolute_path = root / item.path
        exists = absolute_path.exists()
        size = image_size(absolute_path) if exists else None
        width, height = size if size else (0, 0)
        status = "ready" if exists and width >= item.min_width and height >= item.min_height else "blocked"
        detail = (
            f"{width}x{height}; expected at least {item.min_width}x{item.min_height}"
            if exists and size
            else "missing or unsupported image"
        )
        rows.append(
            {
                "Asset": item.name,
                "State": status,
                "Path": item.path.as_posix(),
                "Route": item.route,
                "Dimensions": detail,
                "Expected Markers": ", ".join(item.expected_markers),
                "Use": item.use,
            }
        )
    return rows


def browser_qa_evidence_verdict(rows: list[dict[str, object]]) -> str:
    return "ready" if rows and all(row["State"] == "ready" for row in rows) else "blocked"


def _markdown_table(rows: list[dict[str, object]]) -> str:
    columns = ["Asset", "State", "Path", "Route", "Dimensions", "Expected Markers", "Use"]
    lines = [" | ".join(columns), " | ".join("---" for _ in columns)]
    for row in rows:
        lines.append(" | ".join(str(row.get(column, "")).replace("\n", " ") for column in columns))
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print read-only browser QA evidence asset status.")
    parser.add_argument("--root", default=".", help="Repository root. Defaults to the current directory.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any expected evidence asset is blocked.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    rows = browser_qa_evidence_rows(root)
    verdict = browser_qa_evidence_verdict(rows)
    print("Browser QA Evidence")
    print("Read-only: this command checks committed screenshot assets and route expectations only.")
    print("Research-only: screenshots and route checks are product evidence, not investment advice or trade instructions.")
    print(f"Verdict: {verdict}")
    print()
    print(_markdown_table(rows))
    print()
    print("Capture boundary:")
    print("- Use real Streamlit screenshots from the routes above; do not use generated thumbnails as product proof.")
    print("- If screenshot capture is environment-limited, keep existing real assets and document the manual capture blocker.")
    print("- Re-run make public-check and make diff-hygiene-summary before committing updated assets.")
    print("- Missing source inputs remain blocked; browser evidence does not unlock fundamentals, peers, earnings, estimates, or metrics.")
    return 1 if args.strict and verdict != "ready" else 0


if __name__ == "__main__":
    raise SystemExit(main())
