"""Financial interpretation must use source-aligned approved direct observations."""

from copy import deepcopy

import pytest


def _view():
    source = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000001234.json"
    view = {
        "status": "inspection_only", "safe_to_apply": False,
        "ticker": "FICT", "sec_cik": "0000001234", "source_url": source,
        "accession": "0000001234-26-000001", "period_end": "2025-12-31",
        "filing_date": "2026-03-01", "retrieved_at_utc": "2026-10-30T12:00:00Z",
        "annual_form": "10-K", "withheld_fields": [],
    }
    view["approved_direct_fields"] = [
        {
            "field": field, "value": value, "unit": "USD", "taxonomy": "us-gaap",
            "concept": concept, "period_start": "2025-01-01", "period_end": view["period_end"],
            "accession": view["accession"], "source_ref": source,
            "observed_at_utc": view["retrieved_at_utc"],
            "rights_status": "approved_field_scope_raw_redistribution_held",
        }
        for field, concept, value in (
            ("revenue", "Revenues", 1000),
            ("operating_income", "OperatingIncomeLoss", 100),
            ("cash_from_operations", "NetCashProvidedByUsedInOperatingActivities", 200),
            ("capital_expenditures", "PaymentsToAcquirePropertyPlantAndEquipment", 50),
        )
    ]
    return view


def test_generic_online_analysis_uses_only_matching_direct_facts():
    from src.online_company_analysis import build_online_company_analysis, online_company_analysis_html

    result = build_online_company_analysis(_view())
    assert result["status"] == "inspection_only"
    assert [x["key"] for x in result["findings"]] == [
        "revenue_anchor", "operating_result", "operating_cash", "cash_spend_relation"
    ]
    rendered = online_company_analysis_html(result)
    assert "Operating profit reported" in rendered
    assert "Operating activities generated cash" in rendered
    assert "exceeds reported PP&amp;E spending" in rendered
    assert "not issuer-defined free cash flow" in rendered
    assert all(x["status"] == "withheld" for x in result["lanes"] if x["key"] in {"valuation", "peers", "forecasts", "growth", "prices"})
    assert result["derived_numeric_values"] == {}


def test_loss_and_negative_cash_flow_are_reported_without_zero_filling():
    from src.online_company_analysis import build_online_company_analysis

    view = _view()
    view["approved_direct_fields"][1]["value"] = -100
    view["approved_direct_fields"][2]["value"] = -200
    result = build_online_company_analysis(view)
    titles = " ".join(x["title"] for x in result["findings"])
    assert "Operating loss reported" in titles
    assert "Operating activities used cash" in titles
    assert "Operating cash outflow alongside PP&E spending" in titles
    cash = next(x for x in result["findings"] if x["key"] == "operating_cash")
    assert "used cash" in cash["detail"]
    assert "cash inflow" not in cash["detail"]


def test_reported_zero_is_distinct_from_a_missing_fact():
    from src.online_company_analysis import build_online_company_analysis

    view = _view()
    for row in view["approved_direct_fields"][1:]: row["value"] = 0
    result = build_online_company_analysis(view)
    titles = {x["title"] for x in result["findings"]}
    assert "Operating result was zero" in titles
    assert "Operating cash flow was zero" in titles
    assert "Operating cash flow equals reported PP&E spending" in titles
    cash = next(x for x in result["findings"] if x["key"] == "operating_cash")
    assert "no net operating cash flow" in cash["detail"]


@pytest.mark.parametrize("change", [
    {"period_start": "2025-04-01"}, {"period_end": "2024-12-31"},
    {"unit": "EUR"}, {"source_ref": "https://example.invalid/facts"},
    {"accession": "0000001234-26-000002"}, {"concept": "NetIncomeLoss"},
    {"rights_status": "unreviewed"}, {"value": float("nan")},
    {"observed_at_utc": "2026-10-29T12:00:00Z"},
    {"concept": []}, {"field": []}, {"taxonomy": {}},
])
def test_unaligned_operating_fact_cannot_create_an_analysis_finding(change):
    from src.online_company_analysis import build_online_company_analysis

    view = _view()
    view["approved_direct_fields"][1].update(change)
    result = build_online_company_analysis(view)
    assert "operating_result" not in {x["key"] for x in result["findings"]}
    assert next(x for x in result["lanes"] if x["key"] == "operating")["status"] == "withheld"


def test_invalid_revenue_anchor_withholds_the_entire_analysis():
    from src.online_company_analysis import build_online_company_analysis

    view = _view()
    view["approved_direct_fields"][0]["rights_status"] = "unreviewed"
    assert build_online_company_analysis(view)["findings"] == []


def test_duplicate_component_and_negative_capex_withhold_cash_comparison():
    from src.online_company_analysis import build_online_company_analysis

    view = _view()
    view["approved_direct_fields"].append(deepcopy(view["approved_direct_fields"][2]))
    result = build_online_company_analysis(view)
    assert not {"operating_cash", "cash_spend_relation"} & {x["key"] for x in result["findings"]}
    view = _view()
    view["approved_direct_fields"][3]["value"] = -50
    assert "cash_spend_relation" not in {x["key"] for x in build_online_company_analysis(view)["findings"]}


@pytest.mark.parametrize("index, concept", [
    (2, "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"),
    (3, "PaymentsToAcquireProductiveAssets"),
])
def test_different_component_definitions_do_not_form_a_cash_spend_comparison(index, concept):
    from src.online_company_analysis import build_online_company_analysis

    view = _view(); view["approved_direct_fields"][index]["concept"] = concept
    result = build_online_company_analysis(view)
    assert "operating_cash" in {x["key"] for x in result["findings"]}
    assert "cash_spend_relation" not in {x["key"] for x in result["findings"]}
    assert next(x for x in result["lanes"] if x["key"] == "investment")["status"] == "withheld"


@pytest.mark.parametrize("value", [200, -200, 0])
def test_continuing_operations_cash_keeps_its_scope_in_the_narrative(value):
    from src.online_company_analysis import build_online_company_analysis

    view = _view()
    view["approved_direct_fields"][2].update({
        "concept": "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations", "value": value,
    })
    result = build_online_company_analysis(view)
    cash = next(x for x in result["findings"] if x["key"] == "operating_cash")
    assert "Continuing" in cash["title"]
    assert "continuing" in cash["detail"].lower()
    assert cash["source_fields"] == ["cash_from_operations"]


@pytest.mark.parametrize("change", [
    {"status": "not_requested"}, {"safe_to_apply": True},
    {"sec_cik": "0000009999"}, {"filing_date": "2024-01-01"},
    {"retrieved_at_utc": "2025-01-01T00:00:00Z"}, {"annual_form": "10-Q"},
    {"annual_form": {}},
    {"ticker": "<script>alert(1)</script>"},
])
def test_invalid_or_unrequested_source_context_has_no_financial_interpretation(change):
    from src.online_company_analysis import build_online_company_analysis, online_company_analysis_html

    view = _view(); view.update(change)
    result = build_online_company_analysis(view)
    assert result["findings"] == []
    assert "<script>" not in online_company_analysis_html(result)


def test_workbench_shows_online_interpretation_before_raw_field_evidence(monkeypatch):
    from types import SimpleNamespace
    from src import dashboard

    class Container:
        def __enter__(self): return self
        def __exit__(self, *_args): return False

    output = []
    monkeypatch.setattr(dashboard, "st", SimpleNamespace(
        container=lambda **kw: Container(), button=lambda *a, **kw: True,
        empty=lambda: SimpleNamespace(markdown=lambda value, **kw: output.append(value)),
        session_state={},
    ))
    monkeypatch.setattr(dashboard, "get_company_sec_annual_preview", lambda *a, **kw: _view())
    dashboard.render_company_sec_annual_check("FICT", expected_cik="0000001234")
    rendered = " ".join(output)
    assert "Operating profit reported" in rendered
    assert rendered.index("Online financial review") < rendered.index("SEC annual facts FICT")
