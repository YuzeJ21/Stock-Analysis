from pathlib import Path


PUBLIC_V1_ROUTE = (
    "Home readiness snapshot -> Stock Selector -> Single-Stock Report -> "
    "Data Health lane answer -> Proof History evidence"
)


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_readme_product_tour_matches_v1_public_route_model():
    readme = _read("README.md")

    assert "Start with the five public paths" in readme
    assert "| Start at Home |" in readme
    assert "| Explore ready names |" in readme
    assert "| Review one stock |" in readme
    assert "| Check data coverage |" in readme
    assert "| Inspect proof |" in readme
    assert "| Explore ready names | You want to filter readiness-backed candidates" in readme
    assert "| Inspect proof | You want to see the proof ledger" in readme
    assert "| Inspect proof |" in readme and "| `Proof History` |" in readme
    assert PUBLIC_V1_ROUTE in readme
    assert "Data Health source-proof lane" not in readme
    assert "Proof History is the public proof-inspection surface" not in readme
    assert "Operator context" in readme
    assert "Home readiness snapshot -> Single-Stock Report -> Data Health source-proof lane -> proof history" not in readme
    assert "Start with the three paths" not in readme


def test_readme_and_roadmap_name_pilot_operator_runbook():
    readme = _read("README.md")
    roadmap = _read("ROADMAP.md")

    assert "Pilot Operator Runbook" in readme
    assert "navigation-only queue route map" in readme
    assert "share gate -> source gate -> provider setup -> reviewed one-provider smoke -> validate/preview -> packet and hygiene" in readme
    assert "does not refresh data, apply imports, or promote metadata into fundamentals proof" in readme

    assert "Pilot Operator Runbook V1" in roadmap
    assert "share gate, source gate, provider setup, reviewed one-provider smoke, validate/preview, packet, and hygiene" in roadmap
    assert "without reopening broad proof loops" in roadmap


def test_readme_surfaces_compact_pilot_share_status_before_local_hygiene():
    readme = _read("README.md")

    assert "## Pilot Share Status" in readme
    assert "Share as portfolio/demo evidence only; do not describe the repository as open source until a root `LICENSE` exists." in readme
    assert "Generated CSV/JSON/report churn stays local unless an exact artifact is reviewed as evidence." in readme
    assert "`make project-status` -> `make provider-setup-checklist` -> one reviewed ticker smoke command" in readme
    assert "No broad coverage batch should run from setup alone." in readme
    assert readme.index("## Pilot Share Status") < readme.index("## Local Data Hygiene")


def test_public_docs_share_same_coverage_gate_rule():
    readme = _read("README.md")
    checklist = _read("docs/PUBLIC_RELEASE_CHECKLIST.md")
    runbook = _read("docs/PILOT_RUNBOOK.md")

    for doc in (readme, checklist, runbook):
        assert "No broad coverage batch should run from setup alone" in doc
        assert "Provider setup only makes a source executable" in doc
        assert "readiness changes still require validate, preview, rejected-row review" in doc
        assert "Do not retry exhausted proof queues until new source-backed rows, keyed provider data, reviewed manual rows, or changed blockers exist" in doc


def test_public_walkthrough_uses_stock_selector_before_single_stock_report():
    walkthrough = _read("docs/PUBLIC_DEMO_WALKTHROUGH.md")

    assert PUBLIC_V1_ROUTE in walkthrough
    assert "Open Stock Selector" in walkthrough
    assert "Check Proof History" in walkthrough
    assert "Data Health source-proof lane" not in walkthrough
    assert "Home readiness snapshot -> Single-Stock Report -> Data Health source-proof lane -> proof history" not in walkthrough


def test_public_release_checklist_names_v1_routes_and_primary_surfaces():
    checklist = _read("docs/PUBLIC_RELEASE_CHECKLIST.md")

    for route in (
        "?mode=public&page=home",
        "?mode=public&page=stock-selector",
        "?mode=public&page=single-stock-report&ticker=NVDA&open=1",
        "?mode=public&page=data-health",
        "?mode=public&page=proof-history",
    ):
        assert route in checklist

    assert "Stock Selector is the primary public stock-selection surface" in checklist
    assert "Proof History evidence is the public proof-inspection surface" in checklist
    assert "Data Health lane answer" in checklist
    assert "Operator context" in checklist
    assert "`make public-check` now includes `make license-status`" in checklist
    assert "license/reuse boundary is checked in the same share gate" in checklist


def test_dashboard_qa_tracks_v1_replacement_browser_checks():
    qa = _read("docs/DASHBOARD_QA.md")

    assert "V1 Public UI Replacement QA" in qa
    assert "stock-selector" in qa
    assert "single-stock-report&ticker=NVDA&open=1" in qa
    assert "proof-history" in qa
    assert "no visible first-viewport raw dataframe" in qa


def test_public_demo_and_linkedin_copy_use_v1_route_sequence():
    makefile = _read("Makefile")
    brief = _read("docs/LINKEDIN_PROJECT_BRIEF.md")

    assert PUBLIC_V1_ROUTE in makefile
    assert PUBLIC_V1_ROUTE in brief
    assert "readiness-backed selection comes first" in makefile
    assert "Review one stock, Improve data coverage, and Inspect proof" not in makefile
    assert "Check data coverage:     make readiness-ops-center" in makefile
