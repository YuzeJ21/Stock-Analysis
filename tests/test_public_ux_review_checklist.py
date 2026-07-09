from src.public_ux_review_checklist import PUBLIC_ROUTES, render_public_ux_review_checklist


def test_public_ux_review_checklist_is_read_only_and_route_complete():
    rendered = render_public_ux_review_checklist()

    assert "Public UX Review Checklist" in rendered
    assert "does not refresh data, import rows, capture screenshots, stage files, commit, or push" in rendered
    assert "product QA, not investment advice, broker integration, data freshness proof, or trade instruction" in rendered
    assert len(PUBLIC_ROUTES) == 5
    for page in ("Home", "Stock Selector", "Single-Stock Report", "Data Health", "Proof History"):
        assert f"| {page} |" in rendered
    assert "http://localhost:8501/?mode=public&page=stock-selector" in rendered
    assert "http://localhost:8501/?mode=public&page=single-stock-report&ticker=NVDA&open=1" in rendered
    assert "http://localhost:8501/?mode=public&page=data-health" in rendered
    assert "http://localhost:8501/?mode=public&page=proof-history" in rendered
    assert "Page question" in rendered
    assert "If it fails" in rendered
    assert "Responsive route checks:" in rendered
    assert "Desktop viewport" in rendered
    assert "Phone viewport" in rendered
    assert "390x844" in rendered
    assert "What is this product and where do I start?" in rendered
    assert "Which stock can I review?" in rendered
    assert "What can I use for this ticker right now?" in rendered
    assert "Why is something blocked and how do I fix it?" in rendered
    assert "What evidence changed a readiness state?" in rendered
    assert "Coverage Summary / What Can I Use?" in rendered
    assert "Evidence-only page, latest proof outcome, raw ledger details collapsed" in rendered


def test_public_ux_review_checklist_keeps_operator_details_and_data_claims_out():
    rendered = render_public_ux_review_checklist()

    assert "one question, one short answer, one primary next action, and one stop rule" in rendered
    assert "Desktop and mobile review rules:" in rendered
    assert "Confirm the visible page question matches the route's job in the table above." in rendered
    assert "If the page fails, fix only the matching failure action before adding new sections or routes." in rendered
    assert "raw tables, command blocks, proof ledgers, provider setup, and operator evidence stay behind Advanced or operator mode" in rendered
    assert "Stop if mobile hides the selector, shows raw readiness tables first, or forces horizontal scrolling." in rendered
    assert "Stop if provider setup, operator commands, raw tables, or proof ledgers appear before the coverage answer." in rendered
    assert "Confirm screenshots remain product evidence only and do not claim data freshness." in rendered
    assert "Review log template:" in rendered
    assert "Issue classification: resolved, intentionally_deferred, environment_limited, skipped, or blocked_with_evidence" in rendered
    assert "blocked, candidate-only, skipped, or excluded lane appears as analysis-ready" in rendered
    assert "broker trading, order routing, auto-trading, direct buy/sell instructions, or investment advice" in rendered
    assert "make project-status-check" in rendered
    assert "make public-check" in rendered
    assert "make diff-hygiene-summary" in rendered
