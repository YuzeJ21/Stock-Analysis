from pathlib import Path
import json

from src.browser_qa_evidence import (
    BrowserQaCaptureTarget,
    BrowserQaEvidence,
    BrowserQaResponsiveRouteCheck,
    BrowserQaRouteCheck,
    browser_qa_capture_checklist_rows,
    browser_qa_capture_session_rows,
    browser_qa_capture_target_rows,
    browser_qa_evidence_rows,
    browser_qa_evidence_payload,
    browser_qa_package_verdict,
    browser_qa_evidence_verdict,
    browser_qa_pending_capture_closeout_rows,
    browser_qa_responsive_route_rows,
    browser_qa_reviewed_asset_stage_command,
    browser_qa_route_rows,
    browser_qa_share_recommendation_rows,
    image_size,
    main,
)
from src.browser_qa_evidence import DEFAULT_BROWSER_QA_EVIDENCE, DEFAULT_BROWSER_QA_ROUTE_CHECKS


def _write_png(path: Path, width: int = 1200, height: int = 627) -> None:
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )


def _write_jpeg(path: Path, width: int = 1280, height: int = 720) -> None:
    path.write_bytes(
        b"\xff\xd8"
        b"\xff\xe0\x00\x04\x00\x00"
        b"\xff\xc0\x00\x11\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
        b"\xff\xd9"
    )


def test_image_size_reads_png_and_jpeg_dimensions(tmp_path):
    png = tmp_path / "asset.png"
    jpg = tmp_path / "asset.jpg"
    _write_png(png, width=1200, height=627)
    _write_jpeg(jpg, width=1280, height=720)

    assert image_size(png) == (1200, 627)
    assert image_size(jpg) == (1280, 720)


def test_default_public_browser_qa_contract_uses_current_compact_workflow_markers():
    rendered = " ".join(
        marker
        for item in (*DEFAULT_BROWSER_QA_EVIDENCE[:2], *DEFAULT_BROWSER_QA_ROUTE_CHECKS[:5])
        for marker in (
            item.expected_markers if isinstance(item, BrowserQaEvidence) else item.first_view_markers
        )
    )

    assert "Saved readiness" in rendered
    assert "Data profile" in rendered
    assert "Advanced: research change evidence" in rendered
    assert "Since last review" not in rendered
    assert "Step 1 of 5" in rendered
    assert "Research-only" in rendered
    assert "Earnings Outlook" in rendered
    assert "Research Thesis Journal" in rendered
    assert "Current question" not in rendered
    assert "Primary next step" not in rendered
    assert "research-loop-strip" not in rendered


def test_browser_qa_evidence_rows_keep_routes_assets_and_boundaries_visible(tmp_path):
    asset = tmp_path / "docs" / "assets" / "linkedin-public-dashboard.png"
    asset.parent.mkdir(parents=True)
    _write_png(asset, width=1200, height=627)
    evidence = (
        BrowserQaEvidence(
            name="Public dashboard",
            path=Path("docs/assets/linkedin-public-dashboard.png"),
            route="http://localhost:8501/?mode=public",
            expected_markers=("research-loop-strip", "What can I use now?"),
            min_width=1200,
            min_height=600,
            use="LinkedIn thumbnail.",
        ),
    )

    rows = browser_qa_evidence_rows(tmp_path, evidence)
    rendered = " ".join(str(value) for row in rows for value in row.values()).lower()

    assert rows[0]["State"] == "ready"
    assert rows[0]["Dimensions"].startswith("1200x627")
    assert "localhost:8501/?mode=public" in rendered
    assert "research-loop-strip" in rendered
    assert "what can i use now?" in rendered
    assert "linkedin thumbnail" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_browser_qa_evidence_verdict_blocks_missing_or_small_assets(tmp_path):
    asset = tmp_path / "docs" / "assets" / "small.png"
    asset.parent.mkdir(parents=True)
    _write_png(asset, width=400, height=300)
    evidence = (
        BrowserQaEvidence(
            name="Small asset",
            path=Path("docs/assets/small.png"),
            route="http://localhost:8501/?mode=public",
            expected_markers=("What can I use now?",),
            min_width=1200,
            min_height=600,
            use="Too small for public evidence.",
        ),
        BrowserQaEvidence(
            name="Missing asset",
            path=Path("docs/assets/missing.png"),
            route="http://localhost:8501/?mode=operator&page=data-health",
            expected_markers=("Operator Queue",),
            min_width=1000,
            min_height=600,
            use="Missing evidence.",
        ),
    )

    rows = browser_qa_evidence_rows(tmp_path, evidence)

    assert [row["State"] for row in rows] == ["blocked", "blocked"]
    assert browser_qa_evidence_verdict(rows) == "blocked"


def test_browser_qa_capture_targets_show_manual_pending_without_fabricating_assets(tmp_path):
    target = BrowserQaCaptureTarget(
        name="Single-stock workflow fit screenshot",
        path=Path("docs/assets/single-stock-workflow-fit-real.jpg"),
        route="http://localhost:8501/?mode=public&page=single-stock-report&ticker=NVDA&open=1",
        first_view_markers=("Where This Ticker Fits", "Stop rule"),
        min_width=1000,
        min_height=600,
        use="Workflow proof.",
    )

    rows = browser_qa_capture_target_rows(tmp_path, (target,))
    rendered = " ".join(str(value) for row in rows for value in row.values()).lower()

    assert rows[0]["State"] == "manual_capture_pending"
    assert "normal local browser" in rendered
    assert "do not use generated thumbnails" in rendered
    assert "where this ticker fits" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_browser_qa_capture_targets_become_ready_when_real_asset_exists(tmp_path):
    asset = tmp_path / "docs" / "assets" / "single-stock-workflow-fit-real.jpg"
    asset.parent.mkdir(parents=True)
    _write_jpeg(asset, width=1280, height=720)
    target = BrowserQaCaptureTarget(
        name="Single-stock workflow fit screenshot",
        path=Path("docs/assets/single-stock-workflow-fit-real.jpg"),
        route="http://localhost:8501/?mode=public&page=single-stock-report&ticker=NVDA&open=1",
        first_view_markers=("Where This Ticker Fits", "Stop rule"),
        min_width=1000,
        min_height=600,
        use="Workflow proof.",
    )
    asset_rows = [
        {
            "Asset": "Existing",
            "State": "ready",
            "Path": "docs/assets/public-demo-home-real.jpg",
        }
    ]

    rows = browser_qa_capture_target_rows(tmp_path, (target,))

    assert rows[0]["State"] == "ready"
    assert rows[0]["Dimensions / Capture Note"].startswith("1280x720")
    assert browser_qa_package_verdict(asset_rows, rows) == "ready"


def test_browser_qa_capture_checklist_rows_give_exact_local_capture_steps():
    target = BrowserQaCaptureTarget(
        name="Data Health proof lane screenshot",
        path=Path("docs/assets/operator-data-health-proof-real.jpg"),
        route="http://localhost:8501/?mode=operator&page=data-health&lane=proof",
        first_view_markers=("Proof lane shell", "Review details"),
        min_width=1000,
        min_height=600,
        use="Proof lane evidence.",
    )

    rows = browser_qa_capture_checklist_rows((target,))
    rendered = " ".join(str(value) for row in rows for value in row.values()).lower()

    assert rows[0]["Target"] == "Data Health proof lane screenshot"
    assert rows[0]["Save As"] == "docs/assets/operator-data-health-proof-real.jpg"
    assert rows[0]["Minimum Size"] == "1000x600"
    assert "proof lane shell" in rendered
    assert "do not replace the asset" in rendered
    assert "traceback" in rendered
    assert "raw tables first" in rendered
    assert "missing guardrails" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_browser_qa_pending_capture_closeout_rows_focus_only_missing_real_assets():
    capture_rows = [
        {
            "Capture Target": "Single-stock workflow fit screenshot",
            "State": "manual_capture_pending",
            "Path": "docs/assets/single-stock-workflow-fit-real.jpg",
            "Route": "http://localhost:8501/?mode=public&page=single-stock-report&ticker=NVDA&open=1",
            "First View Markers": "research-loop-strip, Single-Stock Report, Data Health Handoff",
        },
        {
            "Capture Target": "Operator metrics lane screenshot",
            "State": "ready",
            "Path": "docs/assets/operator-data-health-metrics-real.jpg",
            "Route": "http://localhost:8501/?mode=operator&page=data-health&lane=metrics",
            "First View Markers": "Operator Queue",
        },
    ]

    rows = browser_qa_pending_capture_closeout_rows(capture_rows)
    rendered = " ".join(str(value) for row in rows for value in row.values()).lower()

    assert len(rows) == 1
    assert rows[0]["Target"] == "Single-stock workflow fit screenshot"
    assert rows[0]["Open Route"] == "http://localhost:8501/?mode=public&page=single-stock-report&ticker=NVDA&open=1"
    assert rows[0]["Save As"] == "docs/assets/single-stock-workflow-fit-real.jpg"
    assert rows[0]["Verify"] == "make browser-qa-evidence"
    assert rows[0]["Stage If Reviewed"] == "git add -- docs/assets/single-stock-workflow-fit-real.jpg"
    assert "real app screenshot only after visual review" in rendered
    assert "generated thumbnails" in rendered
    assert "research-only guardrails" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_browser_qa_pending_capture_closeout_rows_mark_ready_when_none_pending():
    rows = browser_qa_pending_capture_closeout_rows(
        [
            {
                "Capture Target": "Public home",
                "State": "ready",
                "Path": "docs/assets/public-demo-home-real.jpg",
                "Route": "http://localhost:8501/?mode=public",
                "First View Markers": "First 30 Seconds",
            }
        ]
    )
    rendered = " ".join(str(value) for row in rows for value in row.values()).lower()

    assert rows[0]["Target"] == "All capture targets"
    assert rows[0]["State"] == "ready"
    assert "no screenshot-only staging needed" in rendered
    assert "do not refresh data or unlock blocked inputs" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_browser_qa_capture_session_rows_keep_reviewer_sequence_copy_ready():
    target = BrowserQaCaptureTarget(
        name="Data Health queue drawer routing screenshot",
        path=Path("docs/assets/operator-data-health-queue-routing-real.jpg"),
        route="http://localhost:8501/?mode=operator&page=data-health&lane=fundamentals&drawer=queue",
        first_view_markers=("Operator Queue", "ROUTE MAP", "artifact hygiene"),
        min_width=1000,
        min_height=600,
        use="Queue routing evidence.",
    )

    rows = browser_qa_capture_session_rows((target,))
    rendered = " ".join(str(value) for row in rows for value in row.values()).lower()

    assert [row["Step"] for row in rows] == [
        "1. Start dashboard",
        "2. Capture pending views",
        "3. Confirm first viewport",
        "4. Verify assets",
        "5. Run release gate",
        "6. Commit reviewed evidence only",
    ]
    assert "make dashboard" in rendered
    assert "make browser-qa-evidence" in rendered
    assert "make public-check" in rendered
    assert "make diff-hygiene-summary" in rendered
    assert "make staged-hygiene-check" in rendered
    assert "operator-data-health-queue-routing-real.jpg" in rendered
    assert "reviewed asset command" in rendered
    assert "git add -- docs/assets/operator-data-health-queue-routing-real.jpg" in rendered
    assert "manual_capture_pending" in rendered
    assert "broad generated csv/json/report churn" in rendered
    assert "generated thumbnails" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_browser_qa_reviewed_asset_stage_command_names_only_reviewed_screenshot_assets():
    target = BrowserQaCaptureTarget(
        name="Data Health queue drawer routing screenshot",
        path=Path("docs/assets/operator-data-health-queue-routing-real.jpg"),
        route="http://localhost:8501/?mode=operator&page=data-health&lane=fundamentals&drawer=queue",
        first_view_markers=("Operator Queue", "ROUTE MAP", "artifact hygiene"),
        min_width=1000,
        min_height=600,
        use="Queue routing evidence.",
    )

    command = browser_qa_reviewed_asset_stage_command((target,))

    assert command == "git add -- docs/assets/operator-data-health-queue-routing-real.jpg"
    assert "data/" not in command
    assert "outputs/" not in command
    assert "csv" not in command


def test_browser_qa_package_verdict_keeps_ready_assets_honest_when_capture_targets_pending():
    asset_rows = [
        {
            "Asset": "Public home",
            "State": "ready",
            "Path": "docs/assets/public-demo-home-real.jpg",
        }
    ]
    capture_rows = [
        {
            "Capture Target": "Data Health proof lane screenshot",
            "State": "manual_capture_pending",
            "Path": "docs/assets/operator-data-health-proof-real.jpg",
        }
    ]

    assert browser_qa_package_verdict(asset_rows, capture_rows) == "ready_with_manual_capture_pending"


def test_browser_qa_share_recommendation_prefers_ready_public_image_and_keeps_blockers_visible():
    asset_rows = [
        {
            "Asset": "LinkedIn public dashboard thumbnail",
            "State": "ready",
            "Path": "docs/assets/linkedin-public-dashboard.png",
        }
    ]
    capture_rows = [
        {
            "Capture Target": "Data Health proof lane screenshot",
            "State": "manual_capture_pending",
            "Path": "docs/assets/operator-data-health-proof-real.jpg",
        }
    ]

    rows = browser_qa_share_recommendation_rows(asset_rows, capture_rows)
    rendered = " ".join(str(value) for row in rows for value in row.values()).lower()

    assert rows[0]["Review Item"] == "Current public image"
    assert rows[0]["State"] == "ready"
    assert rows[0]["Recommendation"] == "docs/assets/linkedin-public-dashboard.png"
    assert rows[1]["State"] == "manual_capture_pending"
    assert rows[2]["Review Item"] == "Screenshot copy freshness"
    assert rows[2]["State"] == "route_markers_only"
    assert "exact current copy" in rows[2]["Recommendation"].lower()
    assert "data health proof lane screenshot" in rendered
    assert "use make status-check top_n=5 for current counts" in rendered
    assert "screenshots do not unlock fundamentals" in rendered
    assert "generated thumbnails" in rendered
    assert "normal local browser" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_browser_qa_evidence_payload_is_machine_readable_and_research_safe(tmp_path):
    asset_dir = tmp_path / "docs" / "assets"
    asset_dir.mkdir(parents=True)
    _write_png(asset_dir / "linkedin-public-dashboard.png", width=1200, height=627)
    _write_jpeg(asset_dir / "public-demo-home-real.jpg", width=1200, height=720)
    _write_jpeg(asset_dir / "operator-data-health-metrics-real.jpg", width=1280, height=720)

    payload = browser_qa_evidence_payload(tmp_path)
    rendered = json.dumps(payload).lower()

    assert payload["verdict"] == "ready_with_manual_capture_pending"
    assert len(payload["public_share_recommendation"]) == 4
    assert len(payload["committed_screenshot_assets"]) == 3
    assert len(payload["manual_capture_targets"]) == 3
    assert len(payload["pending_capture_closeout"]) == 3
    assert payload["reviewed_asset_stage_command"] == (
        "git add -- docs/assets/single-stock-workflow-fit-real.jpg "
        "docs/assets/operator-data-health-proof-real.jpg "
        "docs/assets/operator-data-health-queue-routing-real.jpg"
    )
    assert len(payload["local_capture_checklist"]) == 3
    assert len(payload["capture_session_plan"]) == 6
    assert len(payload["route_qa_checklist"]) >= 7
    assert len(payload["responsive_route_qa_checklist"]) == 9
    assert "browser qa evidence is product evidence only" in rendered
    assert "responsive_route_qa_checklist" in rendered
    assert "saved readiness" in rendered
    assert "step 1 of 5" in rendered
    assert "stop rule" in rendered
    assert "no data, no conclusion" in rendered
    assert "data health workspace" in rendered
    assert "phone viewport" in rendered
    assert "390x844" in rendered
    assert "single-stock report" in rendered
    assert "proof history" in rendered
    assert "selected lane answer" in rendered
    assert "single-stock workflow fit screenshot" in rendered
    assert "still withheld" in rendered
    assert "selected ticker" in rendered
    assert "next step" in rendered
    assert "operator-data-health-proof-real.jpg" in rendered
    assert "route map" in rendered
    assert "artifact hygiene" in rendered
    assert "artifact hygiene" in rendered
    assert "commit reviewed evidence only" in rendered
    assert "public_share_recommendation" in rendered
    assert "pending_capture_closeout" in rendered
    assert "linkedin-public-dashboard.png" in rendered
    assert "use make status-check top_n=5 for current counts" in rendered
    assert "make staged-hygiene-check" in rendered
    assert "reviewed_asset_stage_command" in rendered
    assert "do not use generated thumbnails" in rendered
    assert "missing source inputs remain blocked" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_browser_qa_route_rows_keep_workflow_markers_and_stop_rules_visible():
    checks = (
        BrowserQaRouteCheck(
            name="Data Health operator fast view",
            route="http://localhost:8501/?mode=operator&page=data-health",
            first_view_markers=("research-loop-strip", "ops-mode-strip", "Readiness Context"),
            details_boundary="Raw tables stay collapsed.",
            qa_focus="Operator sees next safe action before raw CSVs.",
            stop_rule="Stop if broad proof queues load before explicit detail review.",
        ),
    )

    rows = browser_qa_route_rows(checks)
    rendered = " ".join(str(value) for row in rows for value in row.values()).lower()

    assert rows[0]["Route Check"] == "Data Health operator fast view"
    assert "readiness context" in rendered
    assert "next data-readiness action" not in rendered
    assert "raw tables stay collapsed" in rendered
    assert "stop if broad proof queues load" in rendered
    assert "investment advice" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_browser_qa_responsive_route_rows_cover_public_flow_without_raw_ops():
    rows = browser_qa_responsive_route_rows()
    rendered = " ".join(str(value) for row in rows for value in row.values()).lower()
    pages = [str(row["Page"]) for row in rows]

    assert pages[:5] == ["Home", "Stock Selector", "Single-Stock Report", "Data Health", "Proof History"]
    assert pages[5:] == ["Research Desk", "Discover", "Company Workbench", "Monitor"]
    assert all(row["Desktop Viewport"] == "1280x720" for row in rows)
    assert all(row["Phone Viewport"] == "390x844" for row in rows)
    assert all("Saved readiness" in str(row["First View Must Keep"]) for row in rows)
    assert "lane coverage summary" in rendered
    assert "which stock can i review?" in rendered
    assert "one data health handoff" in rendered
    assert "latest evidence" in rendered
    assert "advanced collapsed" in rendered
    assert "raw tables" in rendered
    assert "horizontal scrolling" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "investment advice" not in rendered


def test_browser_qa_responsive_route_rows_accept_custom_checks():
    rows = browser_qa_responsive_route_rows(
        (
            BrowserQaResponsiveRouteCheck(
                page="Custom",
                route="http://localhost:8501/?mode=public&page=custom",
                desktop_viewport="1200x700",
                phone_viewport="375x812",
                first_view_must_keep="Current question and one next action",
                mobile_risk="Cards stack poorly.",
                stop_rule="Stop if text overlaps.",
            ),
        )
    )

    assert rows == [
        {
            "Page": "Custom",
            "Route": "http://localhost:8501/?mode=public&page=custom",
            "Desktop Viewport": "1200x700",
            "Phone Viewport": "375x812",
            "First View Must Keep": "Current question and one next action",
            "Mobile Risk": "Cards stack poorly.",
            "Stop Rule": "Stop if text overlaps.",
        }
    ]


def test_default_route_checks_cover_workflow_fit_proof_loading_and_queue_routing():
    rows = browser_qa_route_rows()
    rendered = " ".join(str(value) for row in rows for value in row.values()).lower()
    route_names = {str(row["Route Check"]) for row in rows}

    assert "Public Stock Selector" in route_names
    assert "Single-stock workflow fit" in route_names
    assert "Public Data Health coverage answer" in route_names
    assert "Data Health proof lane progressive load" in route_names
    assert "Data Health queue drawer routing" in route_names
    assert {
        "Research Desk",
        "Research Discover",
        "Research Company Workbench",
        "Research Monitor",
    }.issubset(route_names)
    public_rows = [
        row
        for row in rows
        if str(row["Route"]).startswith("http://localhost:8501/?mode=public")
    ]
    assert public_rows
    assert all("Saved readiness" in str(row["First View Markers"]) for row in public_rows)
    stock_selector = next(row for row in rows if row["Route Check"] == "Public Stock Selector")
    assert "Which stock can I review?" in str(stock_selector["First View Markers"])
    assert "Search this review queue" in str(stock_selector["First View Markers"])
    assert "direct review-queue search" in str(stock_selector["Details Boundary"])
    assert "choose a reviewable ticker" in str(stock_selector["QA Focus"])
    single_stock = next(row for row in rows if row["Route Check"] == "Single-stock workflow fit")
    assert "USE NOW" in str(single_stock["First View Markers"])
    assert "STILL WITHHELD" in str(single_stock["First View Markers"])
    public_data_health = next(row for row in rows if row["Route Check"] == "Public Data Health coverage answer")
    assert "What can I use and what stays unavailable?" in str(public_data_health["First View Markers"])
    assert "Lane answer / coverage summary guide" in str(public_data_health["First View Markers"])
    assert "Price / setup" in str(public_data_health["First View Markers"])
    assert "Optional inputs" in str(public_data_health["First View Markers"])
    assert "one coverage answer per lane" in str(public_data_health["Details Boundary"])
    assert "provider setup" in str(public_data_health["Stop Rule"])
    proof_history = next(row for row in rows if row["Route Check"] == "Public proof history evidence view")
    assert "Latest evidence" in str(proof_history["First View Markers"])
    assert "Advanced: proof ledger details" in str(proof_history["First View Markers"])
    assert "latest proof evidence" not in str(proof_history["First View Markers"]).lower()
    fast_view = next(row for row in rows if row["Route Check"] == "Data Health operator fast view")
    assert "READINESS CONTEXT" in str(fast_view["First View Markers"])
    assert "Next Data-Readiness Action" not in str(fast_view["First View Markers"])
    assert "no data, no conclusion" in rendered
    assert "saved readiness" in rendered
    assert "step 1 of 5" in rendered
    assert "primary workflow" not in rendered
    assert "current question" not in rendered
    assert "primary next step" not in rendered
    assert "stop rule" not in rendered
    assert "stock selector" in rendered
    assert "which stock can i review?" in rendered
    assert "still withheld" in rendered
    assert "search this review queue" in rendered
    assert "open data health" in rendered
    assert "lane answer / coverage summary guide" in rendered
    assert "selected lane answer" in rendered
    assert "before advanced proof detail" in rendered
    assert "source gate" in rendered
    assert "before route maps" in rendered
    assert "generated churn" in rendered
    assert "execute commands" in rendered
    assert "investment advice" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_browser_qa_evidence_cli_is_read_only_and_research_safe(tmp_path, capsys):
    asset_dir = tmp_path / "docs" / "assets"
    asset_dir.mkdir(parents=True)
    _write_png(asset_dir / "linkedin-public-dashboard.png", width=1200, height=627)
    _write_jpeg(asset_dir / "public-demo-home-real.jpg", width=1200, height=720)
    _write_jpeg(asset_dir / "operator-data-health-metrics-real.jpg", width=1280, height=720)

    exit_code = main(["--root", str(tmp_path)])
    output = capsys.readouterr().out.lower()

    assert exit_code == 0
    assert "read-only" in output
    assert "ready_with_manual_capture_pending" in output
    assert "public share recommendation" in output
    assert "linkedin-public-dashboard.png" in output
    assert "use make status-check top_n=5 for current counts" in output
    assert "manual capture targets" in output
    assert "pending capture closeout" in output
    assert "stage if reviewed" in output
    assert "local capture checklist" in output
    assert "capture session plan" in output
    assert "commit reviewed evidence only" in output
    assert "save real app screenshots to the listed paths only after visual review" in output
    assert "single-stock workflow fit screenshot" in output
    assert "operator-data-health-proof-real.jpg" in output
    assert "operator-data-health-queue-routing-real.jpg" in output
    assert "real streamlit screenshots" in output
    assert "route qa checklist" in output
    assert "responsive public and personal research workflow qa" in output
    assert "five public pages and four personal-research pages" in output
    assert "manual browser review" in output
    assert "single-stock workflow fit" in output
    assert "data health proof lane progressive load" in output
    assert "data health queue drawer routing" in output
    assert "saved readiness" in output
    assert "step 1 of 5" in output
    assert "stop rule" in output
    assert "no data, no conclusion" in output
    assert "still withheld" in output
    assert "search this review queue" in output
    assert "open data health" in output
    assert "readiness context" in output
    assert "next data-readiness action" not in output
    assert "does not unlock fundamentals" in output
    assert "investment advice" in output
    assert "trade instructions" in output
    assert "buy" not in output
    assert "sell" not in output


def test_browser_qa_evidence_cli_json_mode_prints_payload(tmp_path, capsys):
    asset_dir = tmp_path / "docs" / "assets"
    asset_dir.mkdir(parents=True)
    _write_png(asset_dir / "linkedin-public-dashboard.png", width=1200, height=627)
    _write_jpeg(asset_dir / "public-demo-home-real.jpg", width=1200, height=720)
    _write_jpeg(asset_dir / "operator-data-health-metrics-real.jpg", width=1280, height=720)

    exit_code = main(["--root", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    rendered = json.dumps(payload).lower()

    assert exit_code == 0
    assert payload["verdict"] == "ready_with_manual_capture_pending"
    assert "local_capture_checklist" in payload
    assert "public_share_recommendation" in payload
    assert "pending_capture_closeout" in payload
    assert "capture_session_plan" in payload
    assert "route_qa_checklist" in payload
    assert payload["reviewed_asset_stage_command"].startswith("git add -- docs/assets/")
    assert "saved readiness" in rendered
    assert "step 1 of 5" in rendered
    assert "stop rule" in rendered
    assert "operator-data-health-queue-routing-real.jpg" in rendered
    assert "reviewed_asset_stage_command" in rendered
    assert "linkedin-public-dashboard.png" in rendered
    assert "make staged-hygiene-check" in rendered
    assert "investment advice" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_browser_qa_capture_plan_cli_prints_only_capture_sequence(capsys):
    exit_code = main(["--capture-plan"])
    output = capsys.readouterr().out.lower()

    assert exit_code == 0
    assert "browser qa capture session plan" in output
    assert "read-only" in output
    assert "make dashboard" in output
    assert "make browser-qa-evidence" in output
    assert "make public-check" in output
    assert "make staged-hygiene-check" in output
    assert "commit reviewed evidence only" in output
    assert "committed screenshot assets" not in output
    assert "route qa checklist" not in output
    assert "buy" not in output
    assert "sell" not in output
