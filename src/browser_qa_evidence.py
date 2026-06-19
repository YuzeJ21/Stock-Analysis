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


@dataclass(frozen=True)
class BrowserQaRouteCheck:
    name: str
    route: str
    first_view_markers: tuple[str, ...]
    details_boundary: str
    qa_focus: str
    stop_rule: str


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


DEFAULT_BROWSER_QA_ROUTE_CHECKS: tuple[BrowserQaRouteCheck, ...] = (
    BrowserQaRouteCheck(
        name="Public visitor home",
        route="http://localhost:8501/?mode=public",
        first_view_markers=("research-loop-strip", "Public visitor mode", "Review one stock", "Improve data coverage"),
        details_boundary="Operator commands and proof tables stay out of the first public view.",
        qa_focus="Visitor understands readiness-first workflow and research-only boundary in under 30 seconds.",
        stop_rule="Stop if the first view shows raw CSV tables, command-heavy copy, traceback text, or stale generated-thumbnail proof.",
    ),
    BrowserQaRouteCheck(
        name="Single-stock public path",
        route="http://localhost:8501/?mode=public&page=single-stock",
        first_view_markers=("research-loop-strip", "Single-Stock Report", "readiness", "next proof"),
        details_boundary="Detailed report sections stay below the workflow/readiness cue.",
        qa_focus="Reader sees selected ticker state, what can be reviewed, what is blocked, and the next safe proof path.",
        stop_rule="Stop if unavailable DCF, peer, earnings, estimate, or metric outputs are shown as conclusions.",
    ),
    BrowserQaRouteCheck(
        name="Data Health operator fast view",
        route="http://localhost:8501/?mode=operator&page=data-health",
        first_view_markers=("research-loop-strip", "ops-mode-strip", "Executive Snapshot", "Next Data-Readiness Action"),
        details_boundary="Broad queues, proof tables, and generated-artifact lists remain collapsed until review details are opened.",
        qa_focus="Operator can identify the current lane, freshness state, and next safe action without opening raw CSVs.",
        stop_rule="Stop if broad proof queues load before an explicit detail route or if commands are sprayed across the first view.",
    ),
    BrowserQaRouteCheck(
        name="Data Health metrics review",
        route="http://localhost:8501/?mode=operator&page=data-health&lane=metrics&drawer=metrics",
        first_view_markers=("research-loop-strip", "ops-mode-strip", "Operator Queue", "Review details"),
        details_boundary="Metric evidence stays readiness-gated; details appear only after the metrics review route is selected.",
        qa_focus="SPY/QQQ review metrics remain historical review context with ready, partial, blocked, or excluded states.",
        stop_rule="Stop if Sharpe, Sortino, beta, drawdown, trend, multiples, or peer dispersion appear as rankings or instructions.",
    ),
    BrowserQaRouteCheck(
        name="Data Health proof history",
        route="http://localhost:8501/?mode=operator&page=data-health&lane=proof&drawer=proof",
        first_view_markers=("research-loop-strip", "ops-mode-strip", "Proof History", "proof-record"),
        details_boundary="Proof rows, packet details, and ledger fields stay inside review controls.",
        qa_focus="Operator can see latest proof outcome, missing record fields, artifact boundary, and dry-run proof command.",
        stop_rule="Stop if proof history hides missing fields or suggests recording supported outcomes before reviewed evidence exists.",
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


def browser_qa_route_rows(
    route_checks: Iterable[BrowserQaRouteCheck] = DEFAULT_BROWSER_QA_ROUTE_CHECKS,
) -> list[dict[str, object]]:
    return [
        {
            "Route Check": item.name,
            "Route": item.route,
            "First View Markers": ", ".join(item.first_view_markers),
            "Details Boundary": item.details_boundary,
            "QA Focus": item.qa_focus,
            "Stop Rule": item.stop_rule,
        }
        for item in route_checks
    ]


def _markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
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
    route_rows = browser_qa_route_rows()
    verdict = browser_qa_evidence_verdict(rows)
    print("Browser QA Evidence")
    print("Read-only: this command checks committed screenshot assets and route expectations only.")
    print("Research-only: screenshots and route checks are product evidence, not investment advice or trade instructions.")
    print(f"Verdict: {verdict}")
    print()
    print(_markdown_table(rows, ["Asset", "State", "Path", "Route", "Dimensions", "Expected Markers", "Use"]))
    print()
    print("Route QA Checklist")
    print("Manual browser review: use these route checks when a normal local browser can open the Streamlit app.")
    print(_markdown_table(route_rows, ["Route Check", "Route", "First View Markers", "Details Boundary", "QA Focus", "Stop Rule"]))
    print()
    print("Capture boundary:")
    print("- Use real Streamlit screenshots from the routes above; do not use generated thumbnails as product proof.")
    print("- If screenshot capture is environment-limited, keep existing real assets and document the manual capture blocker.")
    print("- Re-run make public-check and make diff-hygiene-summary before committing updated assets.")
    print("- Missing source inputs remain blocked; browser evidence does not unlock fundamentals, peers, earnings, estimates, or metrics.")
    return 1 if args.strict and verdict != "ready" else 0


if __name__ == "__main__":
    raise SystemExit(main())
