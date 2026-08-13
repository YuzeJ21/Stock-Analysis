from dataclasses import FrozenInstanceError

import pytest

from src.quant_interpretation_eligibility import (
    QuantEvidenceAssessment,
    evaluate_quant_interpretation,
)


@pytest.mark.parametrize(
    ("overrides", "state", "commercial", "reasons"),
    [
        ({}, "current_context_eligible", True, ()),
        (
            {"observation_state": "stale_review_only"},
            "historical_review_only",
            False,
            ("observation_stale",),
        ),
        (
            {"provenance_state": "unverified"},
            "historical_review_only",
            False,
            ("provenance_unverified",),
        ),
        (
            {"rights_state": "unverified"},
            "historical_review_only",
            False,
            ("rights_unverified",),
        ),
        (
            {"calculation_state": "partial"},
            "historical_review_only",
            False,
            ("calculation_partial",),
        ),
        (
            {"observation_state": "unavailable"},
            "withheld",
            False,
            ("observation_unavailable",),
        ),
        (
            {"provenance_state": "invalid"},
            "withheld",
            False,
            ("provenance_invalid",),
        ),
        (
            {"rights_state": "restricted"},
            "withheld",
            False,
            ("rights_restricted",),
        ),
    ],
)
def test_interpretation_table(overrides, state, commercial, reasons):
    values = {
        "family": "valuation",
        "scope": "NVDA:dcf",
        "calculation_state": "available",
        "observation_state": "current",
        "observation_through_date": "2026-07-27",
        "provenance_state": "verified",
        "rights_state": "permitted",
        "field_scope_state": "permitted",
        "evidence_notes": (),
    }
    result = evaluate_quant_interpretation(
        QuantEvidenceAssessment(**(values | overrides))
    )
    assert (result.interpretation_state, result.commercial_eligible) == (
        state,
        commercial,
    )
    assert result.reasons == reasons


def test_rejects_unknown_or_empty_contract_tokens():
    values = {
        "family": "valuation",
        "scope": "NVDA:dcf",
        "calculation_state": "available",
        "observation_state": "current",
        "observation_through_date": "2026-07-27",
        "provenance_state": "verified",
        "rights_state": "permitted",
        "field_scope_state": "permitted",
        "evidence_notes": (),
    }
    for overrides in (
        {"family": "unknown"},
        {"family": ""},
        {"scope": ""},
        {"calculation_state": "unknown"},
        {"observation_state": "unknown"},
        {"provenance_state": "unknown"},
        {"rights_state": "unknown"},
        {"field_scope_state": "unknown"},
    ):
        with pytest.raises(ValueError):
            evaluate_quant_interpretation(
                QuantEvidenceAssessment(**(values | overrides))
            )


@pytest.mark.parametrize("observation_through_date", ["malformed", "2027-01-01"])
def test_unavailable_observation_with_rejected_date_is_withheld(
    observation_through_date,
):
    result = evaluate_quant_interpretation(
        QuantEvidenceAssessment(
            family="indicator",
            scope="NVDA:rsi",
            calculation_state="available",
            observation_state="unavailable",
            observation_through_date=observation_through_date,
            provenance_state="verified",
            rights_state="permitted",
            field_scope_state="permitted",
            evidence_notes=(),
        )
    )
    assert result.interpretation_state == "withheld"
    assert result.reasons == ("observation_unavailable",)


@pytest.mark.parametrize("observation_through_date", ["", "malformed", "9999-01-01"])
def test_current_observation_with_rejected_date_is_withheld(
    observation_through_date,
):
    result = evaluate_quant_interpretation(
        QuantEvidenceAssessment(
            family="indicator",
            scope="NVDA:rsi",
            calculation_state="available",
            observation_state="current",
            observation_through_date=observation_through_date,
            provenance_state="verified",
            rights_state="permitted",
            field_scope_state="permitted",
            evidence_notes=(),
        )
    )
    assert result.interpretation_state == "withheld"
    assert result.commercial_eligible is False
    assert result.reasons == ("observation_unavailable",)


def test_preserves_two_independent_blockers_in_fixed_order():
    result = evaluate_quant_interpretation(
        QuantEvidenceAssessment(
            family="review_metric",
            scope="NVDA:max_drawdown",
            calculation_state="available",
            observation_state="stale_review_only",
            observation_through_date="2026-05-22",
            provenance_state="verified",
            rights_state="unverified",
            field_scope_state="permitted",
            evidence_notes=(),
        )
    )
    assert result.interpretation_state == "historical_review_only"
    assert result.reasons == ("observation_stale", "rights_unverified")


def test_not_applicable_rights_or_scope_cannot_be_commercially_eligible():
    result = evaluate_quant_interpretation(
        QuantEvidenceAssessment(
            family="valuation",
            scope="NVDA:dcf",
            calculation_state="available",
            observation_state="current",
            observation_through_date="2026-07-27",
            provenance_state="verified",
            rights_state="not_applicable",
            field_scope_state="not_applicable",
            evidence_notes=(),
        )
    )
    assert result.interpretation_state == "current_context_eligible"
    assert result.commercial_eligible is False


def test_returns_new_frozen_decision_without_mutating_assessment_tuple():
    notes = ("source: synthetic fixture",)
    assessment = QuantEvidenceAssessment(
        family="valuation",
        scope="NVDA:dcf",
        calculation_state="available",
        observation_state="current",
        observation_through_date="2026-07-27",
        provenance_state="verified",
        rights_state="permitted",
        field_scope_state="permitted",
        evidence_notes=notes,
    )
    result = evaluate_quant_interpretation(assessment)

    assert assessment.evidence_notes is notes
    assert result is not assessment
    with pytest.raises(FrozenInstanceError):
        assessment.scope = "AMD:dcf"
    with pytest.raises(FrozenInstanceError):
        result.summary = "changed"
