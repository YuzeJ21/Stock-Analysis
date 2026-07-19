from src.company_analysis_scope import (
    company_dcf_exclusion_reasons,
    excludes_company_dcf,
    excludes_company_dcf_for_inputs,
)


def test_company_dcf_exclusion_reasons_name_existing_method_families():
    cases = [
        ("etf", {"name": "Broad Market ETF"}, "non_operating_asset_type"),
        ("company", {"name": "Example Acquisition Corp"}, "acquisition_or_spac"),
        ("company", {"name": "Example Fund", "security_type": "Closed End Fund"}, "closed_end_fund"),
        ("company", {"name": "Example Bancshares"}, "bank_or_bancorp"),
        ("company", {"name": "Example Insurance Ltd"}, "financial_insurance_or_mortgage"),
        ("company", {"name": "Example REIT"}, "reit"),
        ("company", {"name": "Example Business Development Company"}, "realty_trust_or_bdc"),
        ("company", {"name": "Example Capital Corporation"}, "capital_corporation"),
    ]

    for asset_type, metadata, expected in cases:
        reasons = company_dcf_exclusion_reasons(asset_type, metadata, {})
        assert expected in reasons
        assert excludes_company_dcf(asset_type, metadata) is True
        assert excludes_company_dcf_for_inputs(asset_type, metadata, {}) is True


def test_company_dcf_exclusion_reasons_preserve_order_and_overlaps():
    reasons = company_dcf_exclusion_reasons(
        "company",
        {"name": "Example Financial Capital Corporation", "security_type": "Closed End Fund"},
        {},
    )

    assert reasons == (
        "closed_end_fund",
        "financial_insurance_or_mortgage",
        "capital_corporation",
    )


def test_company_dcf_exclusion_reasons_include_nonpositive_revenue_model():
    fundamentals = {
        "revenue": 0,
        "free_cash_flow": 10,
        "fcf_margin": None,
        "shares_outstanding": 100,
    }

    assert company_dcf_exclusion_reasons("company", {"name": "Example Biotech"}, fundamentals) == (
        "nonpositive_revenue_margin_model",
    )
    assert excludes_company_dcf("company", {"name": "Example Biotech"}) is False
    assert excludes_company_dcf_for_inputs("company", {"name": "Example Biotech"}, fundamentals) is True


def test_company_dcf_exclusion_reasons_return_empty_for_ordinary_company():
    metadata = {"name": "Example Software Inc", "industry": "Application Software"}
    fundamentals = {"revenue": 100, "free_cash_flow": 10, "fcf_margin": 0.1, "shares_outstanding": 100}

    assert company_dcf_exclusion_reasons("company", metadata, fundamentals) == ()
    assert excludes_company_dcf_for_inputs("company", metadata, fundamentals) is False
