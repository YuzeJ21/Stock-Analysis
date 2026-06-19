from pathlib import Path
import json

from src.browser_qa_evidence import (
    BrowserQaCaptureTarget,
    BrowserQaEvidence,
    BrowserQaRouteCheck,
    browser_qa_capture_checklist_rows,
    browser_qa_capture_session_rows,
    browser_qa_capture_target_rows,
    browser_qa_evidence_rows,
    browser_qa_evidence_payload,
    browser_qa_package_verdict,
    browser_qa_evidence_verdict,
    browser_qa_route_rows,
    browser_qa_share_recommendation_rows,
    image_size,
    main,
)


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


def test_browser_qa_evidence_rows_keep_routes_assets_and_boundaries_visible(tmp_path):
    asset = tmp_path / "docs" / "assets" / "linkedin-public-dashboard.png"
    asset.parent.mkdir(parents=True)
    _write_png(asset, width=1200, height=627)
    evidence = (
        BrowserQaEvidence(
            name="Public dashboard",
            path=Path("docs/assets/linkedin-public-dashboard.png"),
            route="http://localhost:8501/?mode=public",
            expected_markers=("research-loop-strip", "Public visitor mode"),
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
            expected_markers=("Public visitor mode",),
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
        route="http://localhost:8501/?mode=public&page=single-stock",
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
        route="http://localhost:8501/?mode=public&page=single-stock",
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


def test_browser_qa_capture_session_rows_keep_reviewer_sequence_copy_ready():
    target = BrowserQaCaptureTarget(
        name="Data Health queue drawer routing screenshot",
        path=Path("docs/assets/operator-data-health-queue-routing-real.jpg"),
        route="http://localhost:8501/?mode=operator&page=data-health&lane=fundamentals&drawer=queue",
        first_view_markers=("Operator Queue", "ROUTE 1", "proof record"),
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
    assert "manual_capture_pending" in rendered
    assert "broad generated csv/json/report churn" in rendered
    assert "generated thumbnails" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


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
    assert "data health proof lane screenshot" in rendered
    assert "use make status-check top_n=5 for current counts" in rendered
    assert "screenshots do not unlock fundamentals" in rendered
    assert "generated thumbnails" in rendered
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
    assert len(payload["public_share_recommendation"]) == 3
    assert len(payload["committed_screenshot_assets"]) == 3
    assert len(payload["manual_capture_targets"]) == 3
    assert len(payload["local_capture_checklist"]) == 3
    assert len(payload["capture_session_plan"]) == 6
    assert len(payload["route_qa_checklist"]) >= 7
    assert "browser qa evidence is product evidence only" in rendered
    assert "first 30 seconds" in rendered
    assert "single-stock workflow fit screenshot" in rendered
    assert "current step" in rendered
    assert "next safe action" in rendered
    assert "operator-data-health-proof-real.jpg" in rendered
    assert "route 1" in rendered
    assert "proof record" in rendered
    assert "commit reviewed evidence only" in rendered
    assert "public_share_recommendation" in rendered
    assert "linkedin-public-dashboard.png" in rendered
    assert "use make status-check top_n=5 for current counts" in rendered
    assert "make staged-hygiene-check" in rendered
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
            first_view_markers=("research-loop-strip", "ops-mode-strip", "Next Data-Readiness Action"),
            details_boundary="Raw tables stay collapsed.",
            qa_focus="Operator sees next safe action before raw CSVs.",
            stop_rule="Stop if broad proof queues load before explicit detail review.",
        ),
    )

    rows = browser_qa_route_rows(checks)
    rendered = " ".join(str(value) for row in rows for value in row.values()).lower()

    assert rows[0]["Route Check"] == "Data Health operator fast view"
    assert "next data-readiness action" in rendered
    assert "raw tables stay collapsed" in rendered
    assert "stop if broad proof queues load" in rendered
    assert "investment advice" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_default_route_checks_cover_workflow_fit_proof_loading_and_queue_routing():
    rows = browser_qa_route_rows()
    rendered = " ".join(str(value) for row in rows for value in row.values()).lower()
    route_names = {str(row["Route Check"]) for row in rows}

    assert "Single-stock workflow fit" in route_names
    assert "Data Health proof lane progressive load" in route_names
    assert "Data Health queue drawer routing" in route_names
    assert "first 30 seconds" in rendered
    assert "current step" in rendered
    assert "next safe action" in rendered
    assert "proof lane shell" in rendered
    assert "intentionally deferred" in rendered
    assert "navigation-only" in rendered
    assert "route cards appear before detailed action tables" in rendered
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
    assert "local capture checklist" in output
    assert "capture session plan" in output
    assert "commit reviewed evidence only" in output
    assert "save real app screenshots to the listed paths only after visual review" in output
    assert "single-stock workflow fit screenshot" in output
    assert "operator-data-health-proof-real.jpg" in output
    assert "operator-data-health-queue-routing-real.jpg" in output
    assert "real streamlit screenshots" in output
    assert "route qa checklist" in output
    assert "manual browser review" in output
    assert "single-stock workflow fit" in output
    assert "data health proof lane progressive load" in output
    assert "data health queue drawer routing" in output
    assert "first 30 seconds" in output
    assert "next safe action" in output
    assert "next data-readiness action" in output
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
    assert "capture_session_plan" in payload
    assert "route_qa_checklist" in payload
    assert "operator-data-health-queue-routing-real.jpg" in rendered
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
