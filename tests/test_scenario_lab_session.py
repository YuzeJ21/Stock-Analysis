from __future__ import annotations

from dataclasses import replace
import math

import pytest
from streamlit.testing.v1 import AppTest

from src.scenario_lab import ScenarioParameters, run_scenario_lab
from src.valuation import ValuationInput


def _report_payload(*, ticker: str = "SYN1", include_baseline: bool = True) -> dict[str, object]:
    financials = {
        "revenue": 1_000.0,
        "revenue_growth": 0.10,
        "free_cash_flow": 200.0,
        "fcf_margin": 0.20,
        "operating_margin": 0.25,
        "shares_outstanding": 10.0,
        "cash": 100.0,
        "debt": 50.0,
    }
    if not include_baseline:
        financials["revenue_growth"] = None
        financials["fcf_margin"] = None
        financials["free_cash_flow"] = None
    return {
        "ticker": ticker,
        "price_snapshot": {"price": 100.0},
        "financial_summary": financials,
        "valuation_readiness": {"dcf_ready": True},
        "valuation_snapshot": {
            "source_metadata": [
                {
                    "source": "synthetic_fixture",
                    "source_ref": "fixture:SYN1",
                    "as_of_date": "2026-06-30",
                }
            ]
        },
    }


def _source_defaults() -> ScenarioParameters:
    from src.scenario_lab_session import scenario_lab_input_from_report
    from src.scenario_lab import default_scenario_parameters

    return default_scenario_parameters(scenario_lab_input_from_report(_report_payload()))


def test_widget_keys_are_stable_and_scoped_by_profile_and_ticker():
    from src.scenario_lab_session import scenario_lab_widget_keys

    first = scenario_lab_widget_keys("private-alpha", "nvda")
    repeat = scenario_lab_widget_keys("private-alpha", "NVDA")
    other_profile = scenario_lab_widget_keys("private-beta", "NVDA")
    other_ticker = scenario_lab_widget_keys("private-alpha", "AMD")

    assert first == repeat
    assert tuple(first) == (
        "revenue_growth",
        "fcf_margin",
        "wacc",
        "terminal_growth",
        "forecast_years",
    )
    assert len(set(first.values())) == 5
    assert set(first.values()).isdisjoint(other_profile.values())
    assert set(first.values()).isdisjoint(other_ticker.values())
    assert all("private-alpha" in value and "NVDA" in value for value in first.values())


def test_missing_widget_state_uses_current_source_backed_defaults():
    from src.scenario_lab_session import scenario_lab_parameters_from_state

    parameters = scenario_lab_parameters_from_state(
        _report_payload(),
        {},
        profile_key="private-alpha",
    )

    assert parameters == _source_defaults()


def test_valid_current_state_calls_authoritative_runner_exactly_once(monkeypatch):
    import src.scenario_lab_session as session_module

    report = _report_payload()
    keys = session_module.scenario_lab_widget_keys("private-alpha", "SYN1")
    state = {
        keys["revenue_growth"]: 0.12,
        keys["fcf_margin"]: 0.22,
        keys["wacc"]: 0.095,
        keys["terminal_growth"]: 0.025,
        keys["forecast_years"]: 6,
    }
    calls: list[tuple[ValuationInput, ScenarioParameters, dict[str, object]]] = []
    real_runner = session_module.run_scenario_lab

    def spy(valuation_input, parameters, **kwargs):
        calls.append((valuation_input, parameters, kwargs))
        return real_runner(valuation_input, parameters, **kwargs)

    monkeypatch.setattr(session_module, "run_scenario_lab", spy)

    session = session_module.run_scenario_lab_from_state(
        report,
        state,
        profile_key="private-alpha",
        dcf_ready=True,
        asset_type="company",
    )

    assert session.state == "calculated"
    assert session.result is not None
    assert session.result.status == "calculated"
    assert session.parameters == ScenarioParameters(0.12, 0.22, 0.095, 0.025, 6)
    assert len(calls) == 1
    assert calls[0][0].ticker == "SYN1"
    assert calls[0][1] == session.parameters
    assert calls[0][2] == {
        "profile_key": "private-alpha",
        "dcf_ready": True,
        "asset_type": "company",
    }


def test_missing_source_baseline_returns_blocked_session_without_calling_runner(monkeypatch):
    import src.scenario_lab_session as session_module

    monkeypatch.setattr(
        session_module,
        "run_scenario_lab",
        lambda *args, **kwargs: pytest.fail("calculation must remain closed without a source baseline"),
    )

    session = session_module.run_scenario_lab_from_state(
        _report_payload(include_baseline=False),
        {},
        profile_key="private-alpha",
        dcf_ready=False,
        asset_type="company",
    )

    assert session.state == "blocked"
    assert session.result is None
    assert session.parameters == ScenarioParameters(0.08, 0.15, 0.09, 0.03, 5)
    assert "source-backed" in session.blocker.lower()
    assert "baseline" in session.blocker.lower()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("revenue_growth", "not-a-number"),
        ("revenue_growth", math.nan),
        ("fcf_margin", 0.46),
        ("wacc", 0.049),
        ("terminal_growth", 0.051),
        ("forecast_years", 11),
        ("forecast_years", 5.5),
        ("forecast_years", True),
    ],
)
def test_malformed_or_out_of_range_state_is_withheld_without_calculation(
    monkeypatch,
    field,
    value,
):
    import src.scenario_lab_session as session_module

    keys = session_module.scenario_lab_widget_keys("private-alpha", "SYN1")
    state = {keys[field]: value}
    monkeypatch.setattr(
        session_module,
        "run_scenario_lab",
        lambda *args, **kwargs: pytest.fail("invalid session state must not calculate"),
    )

    session = session_module.run_scenario_lab_from_state(
        _report_payload(),
        state,
        profile_key="private-alpha",
        dcf_ready=True,
        asset_type="company",
    )

    assert session.state == "withheld"
    assert session.result is None
    assert session.parameters == _source_defaults()
    assert "invalid" in session.blocker.lower()
    assert field.replace("_", " ") in session.blocker.lower()


def test_terminal_growth_at_or_above_wacc_is_withheld_without_calculation(monkeypatch):
    import src.scenario_lab_session as session_module

    keys = session_module.scenario_lab_widget_keys("private-alpha", "SYN1")
    state = {
        keys["wacc"]: 0.05,
        keys["terminal_growth"]: 0.05,
    }
    monkeypatch.setattr(
        session_module,
        "run_scenario_lab",
        lambda *args, **kwargs: pytest.fail("cross-field invalid state must not calculate"),
    )

    session = session_module.run_scenario_lab_from_state(
        _report_payload(),
        state,
        profile_key="private-alpha",
        dcf_ready=True,
        asset_type="company",
    )

    assert session.state == "withheld"
    assert session.result is None
    assert session.parameters == _source_defaults()
    assert "terminal growth" in session.blocker.lower()
    assert "wacc" in session.blocker.lower()


def test_other_profile_and_ticker_state_cannot_modify_current_session():
    from src.scenario_lab_session import (
        run_scenario_lab_from_state,
        scenario_lab_widget_keys,
    )

    current_defaults = _source_defaults()
    foreign_profile = scenario_lab_widget_keys("other-profile", "SYN1")
    foreign_ticker = scenario_lab_widget_keys("private-alpha", "AMD")
    state = {
        foreign_profile["wacc"]: 0.20,
        foreign_ticker["revenue_growth"]: 0.40,
    }

    session = run_scenario_lab_from_state(
        _report_payload(),
        state,
        profile_key="private-alpha",
        dcf_ready=True,
        asset_type="company",
    )

    assert session.parameters == current_defaults
    assert session.result is not None
    assert session.result.profile_key == "private-alpha"
    assert session.result.ticker == "SYN1"
    assert session.result.input_identity


def test_empty_ticker_never_becomes_an_accepted_modified_base_identity():
    from src.company_workbench_html import _accepted_scenario

    result = run_scenario_lab(
        ValuationInput(
            ticker="",
            revenue=1_000.0,
            revenue_growth=0.10,
            free_cash_flow=200.0,
            fcf_margin=0.20,
            shares_outstanding=10.0,
            cash=100.0,
            debt=50.0,
            source_metadata=[{"source": "fixture", "source_ref": "fixture:SYN1"}],
        ),
        ScenarioParameters(0.12, 0.20, 0.09, 0.03, 5),
        profile_key="private-alpha",
        dcf_ready=True,
        asset_type="company",
    )

    assert result.input_identity
    assert not _accepted_scenario(result, "", "private-alpha")
    assert not _accepted_scenario(replace(result, ticker="SYN1"), "SYN1", "other-profile")


def test_dashboard_resets_malformed_and_above_maximum_widget_state_without_raising():
    app = AppTest.from_string(
        """
import streamlit as st
from src.dashboard import render_scenario_lab
from src.scenario_lab_session import run_scenario_lab_from_state, scenario_lab_widget_keys

report = {
    "ticker": "SYN1",
    "price_snapshot": {"price": 100.0},
    "financial_summary": {
        "revenue": 1000.0,
        "revenue_growth": 0.10,
        "free_cash_flow": 200.0,
        "fcf_margin": 0.20,
        "shares_outstanding": 10.0,
        "cash": 100.0,
        "debt": 50.0,
    },
    "valuation_readiness": {"dcf_ready": True},
    "valuation_snapshot": {
        "source_metadata": [{"source": "fixture", "source_ref": "fixture:SYN1"}]
    },
}
keys = scenario_lab_widget_keys("private-alpha", "SYN1")
if not st.session_state.get("scenario-test-seeded"):
    st.session_state[keys["revenue_growth"]] = "malformed"
    st.session_state[keys["forecast_years"]] = 99
    st.session_state["scenario-test-seeded"] = True
session = run_scenario_lab_from_state(
    report,
    st.session_state,
    profile_key="private-alpha",
    dcf_ready=True,
    asset_type="company",
)
render_scenario_lab(session)
"""
    ).run(timeout=20)

    assert not app.exception
    assert any("invalid" in warning.value.lower() for warning in app.warning)
    slider_values = {slider.label: slider.value for slider in app.slider}
    assert slider_values == {
        "Revenue growth": 0.10,
        "FCF margin": 0.20,
        "Forecast years": 5,
        "WACC": 0.09,
        "Terminal growth": 0.03,
    }
