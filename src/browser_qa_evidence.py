from __future__ import annotations

import argparse
import json
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
        expected_markers=("research-loop-strip", "What can I use now?", "First 30 Seconds", "Primary Workflow"),
        min_width=1200,
        min_height=600,
        use="LinkedIn Featured and GitHub preview image.",
    ),
    BrowserQaEvidence(
        name="Public visitor home screenshot",
        path=Path("docs/assets/public-demo-home-real.jpg"),
        route="http://localhost:8501/?mode=public",
        expected_markers=("First 30 Seconds", "Primary Workflow", "Stock Selector", "Single-Stock Report"),
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
        route="http://localhost:8501/?mode=public&page=single-stock-report&ticker=NVDA&open=1",
        first_view_markers=(
            "research-loop-strip",
            "One-Stock Review",
            "Review Status",
            "SELECTED TICKER",
            "NEXT STEP",
        ),
        min_width=1000,
        min_height=600,
        use="GitHub/LinkedIn proof that one-stock review shows current state, review scope, blocked inputs, and Data Health handoff.",
    ),
    BrowserQaCaptureTarget(
        name="Data Health proof lane screenshot",
        path=Path("docs/assets/operator-data-health-proof-real.jpg"),
        route="http://localhost:8501/?mode=operator&page=data-health&lane=proof",
        first_view_markers=("research-loop-strip", "ops-mode-strip", "Selected Lane Answer", "Proof History"),
        min_width=1000,
        min_height=600,
        use="Operator proof that Data Health answers the selected lane before advanced evidence details.",
    ),
    BrowserQaCaptureTarget(
        name="Data Health queue drawer routing screenshot",
        path=Path("docs/assets/operator-data-health-queue-routing-real.jpg"),
        route="http://localhost:8501/?mode=operator&page=data-health&lane=fundamentals&drawer=queue",
        first_view_markers=(
            "research-loop-strip",
            "ops-mode-strip",
            "Selected Lane Answer",
            "Fundamentals / DCF",
            "Source Gate",
        ),
        min_width=1000,
        min_height=600,
        use="Operator proof that source-gate guidance appears before advanced route-map, proof drawer, and artifact hygiene details.",
    ),
)


DEFAULT_BROWSER_QA_ROUTE_CHECKS: tuple[BrowserQaRouteCheck, ...] = (
    BrowserQaRouteCheck(
        name="Public visitor home",
        route="http://localhost:8501/?mode=public",
        first_view_markers=("research-loop-strip", "What can I use now?", "First 30 Seconds", "Primary Workflow"),
        details_boundary="Operator commands and proof tables stay out of the first public view.",
        qa_focus="Visitor understands readiness-first workflow and research-only boundary in under 30 seconds.",
        stop_rule="Stop if the first view shows raw CSV tables, command-heavy copy, traceback text, or stale generated-thumbnail proof.",
    ),
    BrowserQaRouteCheck(
        name="Single-stock workflow fit",
        route="http://localhost:8501/?mode=public&page=single-stock-report&ticker=NVDA&open=1",
        first_view_markers=(
            "research-loop-strip",
            "One-Stock Review",
            "Review Status",
            "SELECTED TICKER",
            "NEXT STEP",
        ),
        details_boundary="Detailed report sections stay below the selected-ticker contract, usable-now answer, blocked-input answer, and one next step.",
        qa_focus="Reader sees selected ticker state, what can be reviewed, what is blocked or excluded, and where Data Health fits next.",
        stop_rule="Stop if unavailable DCF, peer, earnings, estimate, or metric outputs are shown as conclusions.",
    ),
    BrowserQaRouteCheck(
        name="Public proof history evidence view",
        route="http://localhost:8501/?mode=public&page=proof-history",
        first_view_markers=("research-loop-strip", "Evidence-only page", "LATEST LANE PROOF", "Advanced: proof ledger details"),
        details_boundary="Proof History starts with evidence cards; raw ledger rows stay collapsed under advanced proof details.",
        qa_focus="Visitor can verify what changed a readiness state without treating Proof History as another command center.",
        stop_rule="Stop if Proof History shows command blocks, raw ledger rows, or data-refresh language before the evidence answer.",
    ),
    BrowserQaRouteCheck(
        name="Data Health operator fast view",
        route="http://localhost:8501/?mode=operator&page=data-health",
        first_view_markers=("research-loop-strip", "ops-mode-strip", "Executive Snapshot", "READINESS CONTEXT"),
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
        first_view_markers=("research-loop-strip", "ops-mode-strip", "Selected Lane Answer", "Proof History"),
        details_boundary="The selected lane answer loads before ledger rows, packet details, and command builders are opened.",
        qa_focus="Operator sees the proof-history answer before advanced proof detail.",
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
        first_view_markers=("research-loop-strip", "ops-mode-strip", "Selected Lane Answer", "Fundamentals / DCF", "Source Gate"),
        details_boundary="The lane answer and source gate appear before route maps, per-lane drawers, and detailed action tables.",
        qa_focus="Operator can see why a fundamentals lane is blocked before opening advanced route-map evidence.",
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


def browser_qa_pending_capture_closeout_rows(capture_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return one compact closeout row per pending real-app screenshot capture."""

    pending_rows = [row for row in capture_rows if row.get("State") == "manual_capture_pending"]
    if not pending_rows:
        return [
            {
                "Target": "All capture targets",
                "State": "ready",
                "Open Route": "-",
                "Confirm First View": "All listed real-app screenshots exist and meet minimum dimensions.",
                "Save As": "-",
                "Verify": "make browser-qa-evidence",
                "Stage If Reviewed": "No screenshot-only staging needed.",
                "Boundary": "Screenshots remain product evidence only; they do not refresh data or unlock blocked inputs.",
            }
        ]
    rows: list[dict[str, object]] = []
    for row in pending_rows:
        path = str(row.get("Path") or "")
        rows.append(
            {
                "Target": row.get("Capture Target", "Pending screenshot"),
                "State": row.get("State", "manual_capture_pending"),
                "Open Route": row.get("Route", ""),
                "Confirm First View": row.get("First View Markers", "workflow strip, next action, stop rule"),
                "Save As": path,
                "Verify": "make browser-qa-evidence",
                "Stage If Reviewed": f"git add -- {path}" if path else "Stage only the reviewed screenshot asset.",
                "Boundary": (
                    "Use a real app screenshot only after visual review; do not use generated thumbnails, "
                    "traceback views, raw-table-first views, or screenshots missing research-only guardrails."
                ),
            }
        )
    return rows


def browser_qa_reviewed_asset_stage_command(
    targets: Iterable[BrowserQaCaptureTarget] = DEFAULT_BROWSER_QA_CAPTURE_TARGETS,
) -> str:
    target_list = list(targets)
    return "git add -- " + " ".join(item.path.as_posix() for item in target_list)


def browser_qa_capture_session_rows(
    targets: Iterable[BrowserQaCaptureTarget] = DEFAULT_BROWSER_QA_CAPTURE_TARGETS,
) -> list[dict[str, object]]:
    target_list = list(targets)
    target_paths = ", ".join(item.path.as_posix() for item in target_list)
    target_stage_command = browser_qa_reviewed_asset_stage_command(target_list)
    target_routes = ", ".join(item.route for item in target_list)
    return [
        {
            "Step": "1. Start dashboard",
            "Action": "Run `make dashboard` in a normal local terminal.",
            "Proof": "The browser can open http://localhost:8501 without a connection error.",
            "Stop Rule": "Stop if Streamlit shows a traceback or cannot bind a local port.",
        },
        {
            "Step": "2. Capture pending views",
            "Action": f"Open the pending routes and save real screenshots: {target_routes}.",
            "Proof": f"Reviewed image files exist at: {target_paths}.",
            "Stop Rule": "Do not use generated thumbnails or cropped GitHub cards as product evidence.",
        },
        {
            "Step": "3. Confirm first viewport",
            "Action": "Check the required first-view markers before replacing any asset.",
            "Proof": "Each screenshot shows its workflow strip, next action, and stop rule or review-detail boundary.",
            "Stop Rule": "Stop if the first viewport shows raw tables, command-heavy public copy, or missing guardrails.",
        },
        {
            "Step": "4. Verify assets",
            "Action": "Run `make browser-qa-evidence`.",
            "Proof": "Verdict is `ready`; `manual_capture_pending` is gone for the captured targets.",
            "Stop Rule": "Stop if any screenshot is missing, too small, or mismatched to its route.",
        },
        {
            "Step": "5. Run release gate",
            "Action": "Run `make public-check` and `make diff-hygiene-summary`.",
            "Proof": "Public wording, tests, dashboard smoke, browser evidence, and churn classification pass.",
            "Stop Rule": "Stop if public wording weakens research-only boundaries or generated churn is mixed into the release set.",
        },
        {
            "Step": "6. Commit reviewed evidence only",
            "Action": (
                f"Stage only intentional product/docs/test files and reviewed assets: {target_paths}. "
                f"Reviewed asset command: `{target_stage_command}`."
            ),
            "Proof": "`make staged-hygiene-check` reports no broad generated CSV/JSON/report churn.",
            "Stop Rule": "Do not stage broad data/reports/outputs CSV churn unless it is explicitly selected evidence.",
        },
    ]


def browser_qa_package_verdict(asset_rows: list[dict[str, object]], capture_rows: list[dict[str, object]]) -> str:
    if browser_qa_evidence_verdict(asset_rows) != "ready":
        return "blocked"
    if any(row["State"] == "manual_capture_pending" for row in capture_rows):
        return "ready_with_manual_capture_pending"
    return "ready"


def browser_qa_share_recommendation_rows(
    asset_rows: list[dict[str, object]],
    capture_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    ready_assets = [row for row in asset_rows if row["State"] == "ready"]
    pending_targets = [row for row in capture_rows if row["State"] == "manual_capture_pending"]
    linkedin_asset = next(
        (row for row in ready_assets if "LinkedIn" in str(row["Asset"])),
        ready_assets[0] if ready_assets else None,
    )
    recommendation = (
        str(linkedin_asset["Path"])
        if linkedin_asset
        else "blocked until a real public dashboard screenshot is committed"
    )
    pending_names = ", ".join(str(row["Capture Target"]) for row in pending_targets) if pending_targets else "none"
    pending_action = (
        "Use the committed public dashboard image for GitHub/LinkedIn now; capture pending operator/workflow views later."
        if linkedin_asset and pending_targets
        else "All listed screenshot evidence is ready for public-review packaging."
        if linkedin_asset
        else "Capture a real public dashboard screenshot before public sharing."
    )
    return [
        {
            "Review Item": "Current public image",
            "State": "ready" if linkedin_asset else "blocked",
            "Recommendation": recommendation,
            "Boundary": "Use real app screenshots only; do not use generated thumbnails as product proof.",
        },
        {
            "Review Item": "Pending workflow captures",
            "State": "manual_capture_pending" if pending_targets else "ready",
            "Recommendation": pending_names,
            "Boundary": pending_action,
        },
        {
            "Review Item": "Screenshot copy freshness",
            "State": "route_markers_only",
            "Recommendation": (
                "Committed screenshots prove route markers, dimensions, and share packaging; "
                "recapture in a normal local browser when exact current copy matters."
            ),
            "Boundary": "Do not treat screenshot text as the current data snapshot or latest UI-copy proof after product-code changes.",
        },
        {
            "Review Item": "Data readiness claim",
            "State": "blocked_inputs_remain_blocked",
            "Recommendation": "Use make status-check TOP_N=5 for current counts; do not treat screenshots as data freshness proof.",
            "Boundary": "Screenshots do not unlock fundamentals, peers, earnings, estimates, valuation inputs, or metrics.",
        },
    ]


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


def browser_qa_evidence_payload(root: Path) -> dict[str, object]:
    asset_rows = browser_qa_evidence_rows(root)
    capture_rows = browser_qa_capture_target_rows(root)
    capture_checklist_rows = browser_qa_capture_checklist_rows()
    capture_session_rows = browser_qa_capture_session_rows()
    route_rows = browser_qa_route_rows()
    share_recommendation_rows = browser_qa_share_recommendation_rows(asset_rows, capture_rows)
    pending_capture_closeout_rows = browser_qa_pending_capture_closeout_rows(capture_rows)
    return {
        "verdict": browser_qa_package_verdict(asset_rows, capture_rows),
        "research_only_boundary": (
            "Browser QA evidence is product evidence only; it does not refresh data, apply imports, "
            "record proof, unlock blocked inputs, or provide investment advice."
        ),
        "public_share_recommendation": share_recommendation_rows,
        "committed_screenshot_assets": asset_rows,
        "manual_capture_targets": capture_rows,
        "pending_capture_closeout": pending_capture_closeout_rows,
        "reviewed_asset_stage_command": browser_qa_reviewed_asset_stage_command(),
        "local_capture_checklist": capture_checklist_rows,
        "capture_session_plan": capture_session_rows,
        "route_qa_checklist": route_rows,
        "capture_boundary": [
            "Use real Streamlit screenshots from the listed routes; do not use generated thumbnails as product proof.",
            "Keep existing real assets if local browser or socket capture is environment-limited.",
            "Re-run make public-check and make diff-hygiene-summary before committing updated assets.",
            "Missing source inputs remain blocked; browser evidence does not unlock fundamentals, peers, earnings, estimates, or metrics.",
        ],
    }


def _markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    lines = [" | ".join(columns), " | ".join("---" for _ in columns)]
    for row in rows:
        lines.append(" | ".join(str(row.get(column, "")).replace("\n", " ") for column in columns))
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Print read-only browser QA evidence asset status.")
    parser.add_argument("--root", default=".", help="Repository root. Defaults to the current directory.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable browser QA evidence and capture instructions.")
    parser.add_argument("--capture-plan", action="store_true", help="Print only the copy-ready browser screenshot capture session plan.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any expected evidence asset is blocked.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    payload = browser_qa_evidence_payload(root)
    rows = list(payload["committed_screenshot_assets"])
    capture_rows = list(payload["manual_capture_targets"])
    share_recommendation_rows = list(payload["public_share_recommendation"])
    capture_checklist_rows = list(payload["local_capture_checklist"])
    pending_capture_closeout_rows = list(payload["pending_capture_closeout"])
    capture_session_rows = list(payload["capture_session_plan"])
    route_rows = list(payload["route_qa_checklist"])
    verdict = browser_qa_package_verdict(rows, capture_rows)
    if args.capture_plan:
        print("Browser QA Capture Session Plan")
        print("Read-only: this plan does not capture screenshots, refresh data, apply imports, stage files, commit, or push.")
        print("Use it in a normal local browser session after `make dashboard` is running.")
        print(_markdown_table(capture_session_rows, ["Step", "Action", "Proof", "Stop Rule"]))
        return 0
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if args.strict and browser_qa_evidence_verdict(rows) != "ready" else 0
    print("Browser QA Evidence")
    print("Read-only: this command checks committed screenshot assets and route expectations only.")
    print("Research-only: screenshots and route checks are product evidence, not investment advice or trade instructions.")
    print(f"Verdict: {verdict}")
    print()
    print("Public Share Recommendation")
    print(_markdown_table(share_recommendation_rows, ["Review Item", "State", "Recommendation", "Boundary"]))
    print()
    print("Committed Screenshot Assets")
    print(_markdown_table(rows, ["Asset", "State", "Path", "Route", "Dimensions", "Expected Markers", "Use"]))
    print()
    print("Manual Capture Targets")
    print("These are real-app screenshot targets that should be captured in a normal local browser when socket/screenshot access is available.")
    print(_markdown_table(capture_rows, ["Capture Target", "State", "Path", "Route", "Dimensions / Capture Note", "First View Markers", "Use"]))
    print()
    print("Pending Capture Closeout")
    print("Use this compact list to finish only the missing real-app screenshots; keep generated thumbnails out.")
    print(_markdown_table(pending_capture_closeout_rows, ["Target", "State", "Open Route", "Confirm First View", "Save As", "Verify", "Stage If Reviewed", "Boundary"]))
    print()
    print("Local Capture Checklist")
    print("Use this after `make dashboard` in a normal local terminal; save real app screenshots to the listed paths only after visual review.")
    print(_markdown_table(capture_checklist_rows, ["Target", "Open Route", "Save As", "Minimum Size", "First View Must Show", "Stop Rule"]))
    print()
    print("Capture Session Plan")
    print("Follow this sequence when replacing or adding real product screenshots.")
    print(_markdown_table(capture_session_rows, ["Step", "Action", "Proof", "Stop Rule"]))
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
