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
