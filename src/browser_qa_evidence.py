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


@dataclass(frozen=True)
class BrowserQaCaptureTarget:
    name: str
    path: Path
    route: str
    first_view_markers: tuple[str, ...]
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


DEFAULT_BROWSER_QA_CAPTURE_TARGETS: tuple[BrowserQaCaptureTarget, ...] = (
    BrowserQaCaptureTarget(
        name="Single-stock workflow fit screenshot",
        path=Path("docs/assets/single-stock-workflow-fit-real.jpg"),
        route="http://localhost:8501/?mode=public&page=single-stock",
        first_view_markers=("research-loop-strip", "Single-Stock Report", "Where This Ticker Fits", "Stop rule"),
        min_width=1000,
        min_height=600,
        use="GitHub/LinkedIn proof that one-stock review shows current state, review scope, blocked inputs, and Data Health handoff.",
    ),
    BrowserQaCaptureTarget(
        name="Data Health proof lane screenshot",
        path=Path("docs/assets/operator-data-health-proof-real.jpg"),
        route="http://localhost:8501/?mode=operator&page=data-health&lane=proof",
        first_view_markers=("research-loop-strip", "ops-mode-strip", "Proof lane shell", "Review details"),
        min_width=1000,
        min_height=600,
        use="Operator proof that proof details are progressively loaded and not shown as raw tables first.",
    ),
    BrowserQaCaptureTarget(
        name="Data Health queue drawer routing screenshot",
        path=Path("docs/assets/operator-data-health-queue-routing-real.jpg"),
        route="http://localhost:8501/?mode=operator&page=data-health&lane=fundamentals&drawer=queue",
        first_view_markers=("research-loop-strip", "ops-mode-strip", "Operator Queue", "source-proof"),
        min_width=1000,
        min_height=600,
        use="Operator proof that queue lane routing leads to source proof and proof-record context without executing commands.",
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
        name="Single-stock workflow fit",
        route="http://localhost:8501/?mode=public&page=single-stock",
        first_view_markers=("research-loop-strip", "Single-Stock Report", "Workflow Fit", "Stop rule"),
        details_boundary="Detailed report sections stay below the ticker state, reviewable-now, blocked, and Data Health handoff cues.",
        qa_focus="Reader sees selected ticker state, what can be reviewed now, what is blocked or excluded, and where Data Health fits next.",
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
        name="Data Health proof lane progressive load",
        route="http://localhost:8501/?mode=operator&page=data-health&lane=proof",
        first_view_markers=("research-loop-strip", "ops-mode-strip", "Proof lane shell", "Review details"),
        details_boundary="The proof lane shell loads before ledger rows, packet details, and command builders are opened.",
        qa_focus="Operator sees that proof detail is intentionally deferred, not missing or broken.",
        stop_rule="Stop if the proof lane first view looks empty, shows a traceback, or expands raw ledger rows by default.",
    ),
    BrowserQaRouteCheck(
        name="Data Health proof history detail",
        route="http://localhost:8501/?mode=operator&page=data-health&lane=proof&drawer=proof",
        first_view_markers=("research-loop-strip", "ops-mode-strip", "Proof History", "proof-record"),
        details_boundary="Proof rows, packet details, and ledger fields stay inside review controls.",
        qa_focus="Operator can see latest proof outcome, missing record fields, artifact boundary, and dry-run proof command.",
        stop_rule="Stop if proof history hides missing fields or suggests recording supported outcomes before reviewed evidence exists.",
    ),
    BrowserQaRouteCheck(
        name="Data Health queue drawer routing",
        route="http://localhost:8501/?mode=operator&page=data-health&lane=fundamentals&drawer=queue",
        first_view_markers=("research-loop-strip", "ops-mode-strip", "Operator Queue", "source-proof"),
        details_boundary="Queue lane links are navigation-only; source proof, packet, comparison, proof record, and artifact hygiene stay collapsed.",
        qa_focus="Operator can move from readiness queue to source proof and proof record without hunting across disconnected sections.",
        stop_rule="Stop if route links execute commands, expose raw tables first, or imply generated churn belongs in the default staging set.",
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


def browser_qa_capture_target_rows(
    root: Path,
    targets: Iterable[BrowserQaCaptureTarget] = DEFAULT_BROWSER_QA_CAPTURE_TARGETS,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in targets:
        absolute_path = root / item.path
        exists = absolute_path.exists()
        size = image_size(absolute_path) if exists else None
        width, height = size if size else (0, 0)
        status = "ready" if exists and width >= item.min_width and height >= item.min_height else "manual_capture_pending"
        detail = (
            f"{width}x{height}; expected at least {item.min_width}x{item.min_height}"
            if exists and size
            else "capture with a normal local browser; do not use generated thumbnails"
        )
        rows.append(
            {
                "Capture Target": item.name,
                "State": status,
                "Path": item.path.as_posix(),
                "Route": item.route,
                "Dimensions / Capture Note": detail,
                "First View Markers": ", ".join(item.first_view_markers),
                "Use": item.use,
            }
        )
    return rows


def browser_qa_capture_checklist_rows(
    targets: Iterable[BrowserQaCaptureTarget] = DEFAULT_BROWSER_QA_CAPTURE_TARGETS,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in targets:
        rows.append(
            {
                "Target": item.name,
                "Open Route": item.route,
                "Save As": item.path.as_posix(),
                "Minimum Size": f"{item.min_width}x{item.min_height}",
                "First View Must Show": ", ".join(item.first_view_markers),
                "Stop Rule": "Do not replace the asset if the route shows a traceback, raw tables first, command-heavy public copy, or missing guardrails.",
            }
        )
    return rows


def browser_qa_package_verdict(asset_rows: list[dict[str, object]], capture_rows: list[dict[str, object]]) -> str:
    if browser_qa_evidence_verdict(asset_rows) != "ready":
        return "blocked"
    if any(row["State"] == "manual_capture_pending" for row in capture_rows):
        return "ready_with_manual_capture_pending"
    return "ready"


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
    capture_rows = browser_qa_capture_target_rows(root)
    capture_checklist_rows = browser_qa_capture_checklist_rows()
    route_rows = browser_qa_route_rows()
    verdict = browser_qa_package_verdict(rows, capture_rows)
    print("Browser QA Evidence")
    print("Read-only: this command checks committed screenshot assets and route expectations only.")
    print("Research-only: screenshots and route checks are product evidence, not investment advice or trade instructions.")
    print(f"Verdict: {verdict}")
    print()
    print("Committed Screenshot Assets")
    print(_markdown_table(rows, ["Asset", "State", "Path", "Route", "Dimensions", "Expected Markers", "Use"]))
    print()
    print("Manual Capture Targets")
    print("These are real-app screenshot targets that should be captured in a normal local browser when socket/screenshot access is available.")
    print(_markdown_table(capture_rows, ["Capture Target", "State", "Path", "Route", "Dimensions / Capture Note", "First View Markers", "Use"]))
    print()
    print("Local Capture Checklist")
    print("Use this after `make dashboard` in a normal local terminal; save real app screenshots to the listed paths only after visual review.")
    print(_markdown_table(capture_checklist_rows, ["Target", "Open Route", "Save As", "Minimum Size", "First View Must Show", "Stop Rule"]))
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
    return 1 if args.strict and browser_qa_evidence_verdict(rows) != "ready" else 0


if __name__ == "__main__":
    raise SystemExit(main())
