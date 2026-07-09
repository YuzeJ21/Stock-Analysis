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


def test_public_ux_review_checklist_keeps_operator_details_and_data_claims_out():
    rendered = render_public_ux_review_checklist()

    assert "one question, one short answer, one primary next action, and one stop rule" in rendered
    assert "raw tables, command blocks, proof ledgers, provider setup, and operator evidence stay behind Advanced or operator mode" in rendered
    assert "Confirm screenshots remain product evidence only and do not claim data freshness." in rendered
    assert "blocked, candidate-only, skipped, or excluded lane appears as analysis-ready" in rendered
    assert "broker trading, order routing, auto-trading, direct buy/sell instructions, or investment advice" in rendered
    assert "make public-check" in rendered
    assert "make diff-hygiene-summary" in rendered
