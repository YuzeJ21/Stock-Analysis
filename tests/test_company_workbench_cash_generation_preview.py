from __future__ import annotations

from dataclasses import replace

import pytest

from src.company_workbench_cash_generation_preview import (
    company_workbench_cash_preview_requested,
    compose_company_workbench_cash_generation_preview,
)
from src.earnings_nowcast_contract import QuarterlyActual
from src.quarterly_cash_generation import QuarterlyBusinessObservation
from src.quarterly_cash_generation_adapter import QuarterlyAdapterAcceptance
from src.sec_quarterly_cash_generation_pilot import (
    SecQuarterlyPilotExtraction,
    SecQuarterlyPilotPreview,
)


AS_OF = "2026-07-20T23:59:59-04:00"
ACCEPTED_AT = "2026-05-20T20:35:52+00:00"
RETRIEVED_AT = "2026-07-20T23:00:00+00:00"
SOURCE_URL = (
    "https://www.sec.gov/Archives/edgar/data/1045810/"
    "000104581026000052/nvda-20260426.htm"
)


def _observation(metric: str, value: float) -> QuarterlyBusinessObservation:
    return QuarterlyBusinessObservation(
        ticker="NVDA",
        fiscal_period="2027-Q1",
        period_end_date="2026-04-26",
        metric=metric,
        value=value,
        currency="USD",
        unit_scale=1.0,
        accounting_basis="reported",
        duration_basis="three_months",
        source="sec_companyfacts",
        source_ref=f"{SOURCE_URL}#f-{metric}",
        published_at=ACCEPTED_AT,
        retrieved_at=RETRIEVED_AT,
    )


def _accepted_sec_preview() -> SecQuarterlyPilotPreview:
    observations = (
        _observation("operating_income", 53_536_000_000),
        _observation("cash_from_operations", 50_344_000_000),
        _observation("capital_expenditures", -1_757_000_000),
    )
    revenue = QuarterlyActual(
        ticker="NVDA",
        fiscal_period="2027-Q1",
        period_end_date="2026-04-26",
        reported_at=ACCEPTED_AT,
        revenue_actual=81_615_000_000,
        eps_actual=None,
        source="sec_companyfacts",
        source_ref=f"{SOURCE_URL}#f-revenue",
        retrieved_at=RETRIEVED_AT,
        revenue_currency="USD",
        revenue_unit_scale=1.0,
        revenue_basis="reported",
        split_adjustment_basis="primary_split_basis_unverified",
    )
    extraction = SecQuarterlyPilotExtraction(
        ticker="NVDA",
        cik="0001045810",
        fiscal_period="2027-Q1",
        period_start_date="2026-01-26",
        period_end_date="2026-04-26",
        accession="0001045810-26-000052",
        filing_date="2026-05-20",
        accepted_at=ACCEPTED_AT,
        source_url=SOURCE_URL,
        observations=observations,
        revenue_actuals=(revenue,),
        capex_sign_evidence="explicit_filed_table_outflow",
        blockers=(),
    )
    acceptance = QuarterlyAdapterAcceptance(
        ticker="NVDA",
        source_id="sec_companyfacts",
        status="accepted_for_review",
        blockers=(),
        accepted_observation_count=3,
        reviewed_metrics=(
            "capital_expenditures",
            "cash_from_operations",
            "operating_income",
        ),
        derived_point_count=3,
        explicit_q4_periods=(),
        rights_status="approved",
    )
    return SecQuarterlyPilotPreview(
        extraction=extraction,
        acceptance=acceptance,
        status="accepted_for_review",
        blockers=(),
    )


def test_accepted_sec_packet_composes_complete_non_activation_preview():
    result = compose_company_workbench_cash_generation_preview(
        _accepted_sec_preview(),
        selected_ticker="NVDA",
        as_of=AS_OF,
    )

    assert result.status == "accepted_for_review"
    assert result.operating_margin.value == pytest.approx(
        53_536_000_000 / 81_615_000_000
    )
    assert result.free_cash_flow.value == 48_587_000_000
    assert result.fcf_margin.value == pytest.approx(
        48_587_000_000 / 81_615_000_000
    )
    assert result.production_activation is False
    assert result.readiness_promotions == ()
    assert result.persistence is False
    assert result.accession == "0001045810-26-000052"
    assert result.accepted_at == ACCEPTED_AT
    assert result.cutoff == "2026-07-21T03:59:59+00:00"
    assert result.capex_sign_evidence == "explicit_filed_table_outflow"
    assert result.blockers == ()
    assert result.withheld_metrics == ()
    assert [row.metric for row in result.components] == [
        "revenue",
        "operating_income",
        "cash_from_operations",
        "capital_expenditures",
    ]
    assert [row.value for row in result.components] == [
        81_615_000_000,
        53_536_000_000,
        50_344_000_000,
        -1_757_000_000,
    ]
    assert all(row.source_ref.startswith(SOURCE_URL) for row in result.components)
    assert result.operating_margin.source_refs == (
        f"{SOURCE_URL}#f-operating_income",
        f"{SOURCE_URL}#f-revenue",
    )
    assert result.free_cash_flow.source_refs == (
        f"{SOURCE_URL}#f-cash_from_operations",
        f"{SOURCE_URL}#f-capital_expenditures",
    )


@pytest.mark.parametrize("value", ["1", ["1"], ("1",)])
def test_only_explicit_one_requests_cash_preview(value):
    assert company_workbench_cash_preview_requested(value) is True


@pytest.mark.parametrize(
    "value",
    [None, "", "0", "true", "yes", "1,other", [], ()],
)
def test_all_other_query_values_keep_normal_workbench(value):
    assert company_workbench_cash_preview_requested(value) is False


def _assert_fully_withheld(result, blocker: str) -> None:
    assert result.status == "withheld"
    assert blocker in result.blockers
    assert result.operating_margin.value is None
    assert result.free_cash_flow.value is None
    assert result.fcf_margin.value is None
    assert result.components == ()
    assert result.withheld_metrics == (
        "operating_margin",
        "free_cash_flow",
        "fcf_margin",
    )
    assert result.production_activation is False
    assert result.readiness_promotions == ()
    assert result.persistence is False


def test_blocked_pilot_withholds_every_cash_generation_metric():
    pilot = replace(_accepted_sec_preview(), status="blocked", blockers=("source_blocked",))

    result = compose_company_workbench_cash_generation_preview(
        pilot,
        selected_ticker="NVDA",
        as_of=AS_OF,
    )

    _assert_fully_withheld(result, "pilot_status:blocked")


def _governance_case(name: str):
    pilot = _accepted_sec_preview()
    selected_ticker = "NVDA"
    as_of = AS_OF
    if name == "acceptance_missing":
        pilot = replace(pilot, acceptance=None)
    elif name == "acceptance_blocked":
        pilot = replace(
            pilot,
            acceptance=replace(pilot.acceptance, status="blocked", blockers=("blocked",)),
        )
    elif name == "acceptance_blockers":
        pilot = replace(
            pilot,
            acceptance=replace(pilot.acceptance, blockers=("still_blocked",)),
        )
    elif name == "pilot_blockers":
        pilot = replace(pilot, blockers=("still_blocked",))
    elif name == "rights_unverified":
        pilot = replace(
            pilot,
            acceptance=replace(
                pilot.acceptance,
                rights_status="commercial_rights_unverified",
            ),
        )
    elif name == "reviewed_metrics_missing":
        pilot = replace(
            pilot,
            acceptance=replace(
                pilot.acceptance,
                reviewed_metrics=("cash_from_operations",),
            ),
        )
    elif name == "derived_points_missing":
        pilot = replace(
            pilot,
            acceptance=replace(pilot.acceptance, derived_point_count=2),
        )
    elif name == "production_activation":
        pilot = replace(pilot, production_activation=True)
    elif name == "pilot_promotions":
        pilot = replace(pilot, readiness_promotions=("operating_margin",))
    elif name == "acceptance_activation":
        pilot = replace(
            pilot,
            acceptance=replace(pilot.acceptance, production_activation=True),
        )
    elif name == "acceptance_promotions":
        pilot = replace(
            pilot,
            acceptance=replace(pilot.acceptance, readiness_promotions=("fcf_margin",)),
        )
    elif name == "ticker_mismatch":
        selected_ticker = "OTHER"
    elif name == "extraction_blocked":
        pilot = replace(
            pilot,
            extraction=replace(pilot.extraction, blockers=("fixture_blocker",)),
        )
    elif name == "source_mismatch":
        pilot = replace(
            pilot,
            acceptance=replace(pilot.acceptance, source_id="other_source"),
        )
    elif name == "accepted_count_mismatch":
        pilot = replace(
            pilot,
            acceptance=replace(pilot.acceptance, accepted_observation_count=2),
        )
    elif name == "post_cutoff":
        as_of = "2026-05-20T20:35:51+00:00"
    return pilot, selected_ticker, as_of


@pytest.mark.parametrize(
    ("case", "blocker"),
    [
        ("acceptance_missing", "adapter_acceptance_required"),
        ("acceptance_blocked", "adapter_status:blocked"),
        ("acceptance_blockers", "adapter_blocker:still_blocked"),
        ("pilot_blockers", "pilot_blocker:still_blocked"),
        ("rights_unverified", "source_rights:commercial_rights_unverified"),
        ("reviewed_metrics_missing", "adapter_reviewed_metrics_incomplete"),
        ("derived_points_missing", "adapter_derived_points_incomplete"),
        ("production_activation", "production_activation_forbidden"),
        ("pilot_promotions", "readiness_promotions_forbidden"),
        ("acceptance_activation", "production_activation_forbidden"),
        ("acceptance_promotions", "readiness_promotions_forbidden"),
        ("ticker_mismatch", "ticker_mismatch:NVDA"),
        ("extraction_blocked", "sec_extraction:fixture_blocker"),
        ("source_mismatch", "adapter_source:other_source"),
        ("accepted_count_mismatch", "accepted_observation_count_mismatch"),
        ("post_cutoff", "accepted_after_cutoff"),
    ],
)
def test_governance_or_cutoff_failure_withholds_complete_preview(case, blocker):
    pilot, selected_ticker, as_of = _governance_case(case)

    result = compose_company_workbench_cash_generation_preview(
        pilot,
        selected_ticker=selected_ticker,
        as_of=as_of,
    )

    _assert_fully_withheld(result, blocker)


def _metadata_case(name: str) -> SecQuarterlyPilotPreview:
    pilot = _accepted_sec_preview()
    extraction = pilot.extraction
    if name == "missing_accession":
        extraction = replace(extraction, accession="")
    elif name == "missing_source":
        extraction = replace(extraction, source_url="")
    elif name == "invalid_accepted_at":
        extraction = replace(extraction, accepted_at="not-a-timestamp")
    elif name == "missing_capex_proof":
        extraction = replace(extraction, capex_sign_evidence="")
    elif name == "wrong_capex_proof":
        extraction = replace(extraction, capex_sign_evidence="companyfacts_unsigned")
    return replace(pilot, extraction=extraction)


@pytest.mark.parametrize(
    ("case", "blocker"),
    [
        ("missing_accession", "accession_required"),
        ("missing_source", "source_url_required"),
        ("invalid_accepted_at", "accepted_at_invalid"),
        ("missing_capex_proof", "capex_sign_evidence_required"),
        ("wrong_capex_proof", "capex_sign_evidence_required"),
    ],
)
def test_missing_lineage_or_capex_proof_withholds_complete_preview(case, blocker):
    result = compose_company_workbench_cash_generation_preview(
        _metadata_case(case),
        selected_ticker="NVDA",
        as_of=AS_OF,
    )

    _assert_fully_withheld(result, blocker)


def _evidence_case(name: str) -> SecQuarterlyPilotPreview:
    pilot = _accepted_sec_preview()
    extraction = pilot.extraction
    observations = extraction.observations
    if name == "observations_missing":
        observations = ()
    elif name == "component_missing":
        observations = observations[:-1]
    elif name == "ambiguous_revision":
        observations = (
            *observations,
            replace(
                observations[-1],
                value=-2_000_000_000,
                source_ref=f"{SOURCE_URL}#f-capital_expenditures-conflict",
            ),
        )
    elif name == "incompatible_definition":
        observations = (
            observations[0],
            observations[1],
            replace(observations[2], currency="CAD"),
        )
    elif name == "observation_after_cutoff":
        observations = (
            replace(observations[0], published_at="2026-07-22T00:00:00+00:00"),
            observations[1],
            observations[2],
        )
    elif name == "positive_capex":
        observations = (
            observations[0],
            observations[1],
            replace(observations[2], value=1_757_000_000),
        )
    elif name == "period_mismatch":
        observations = (
            observations[0],
            observations[1],
            replace(
                observations[2],
                fiscal_period="2027-Q2",
                period_end_date="2026-07-26",
            ),
        )
    revenue_actuals = extraction.revenue_actuals
    if name == "revenue_missing":
        revenue_actuals = ()
    elif name == "revenue_after_cutoff":
        revenue_actuals = (
            replace(
                revenue_actuals[0],
                reported_at="2026-07-22T00:00:00+00:00",
                retrieved_at="2026-07-22T00:01:00+00:00",
            ),
        )
    extraction = replace(
        extraction,
        observations=observations,
        revenue_actuals=revenue_actuals,
    )
    acceptance = replace(
        pilot.acceptance,
        accepted_observation_count=len(observations),
    )
    return replace(pilot, extraction=extraction, acceptance=acceptance)


@pytest.mark.parametrize(
    ("case", "blocker"),
    [
        ("observations_missing", "observations_required"),
        ("revenue_missing", "revenue_actual_required"),
        ("component_missing", "complete_cash_generation_preview_required"),
        ("ambiguous_revision", "complete_cash_generation_preview_required"),
        ("incompatible_definition", "complete_cash_generation_preview_required"),
        ("observation_after_cutoff", "observation_after_cutoff:operating_income"),
        ("revenue_after_cutoff", "revenue_after_cutoff"),
        ("positive_capex", "capital_expenditures_outflow_required"),
        ("period_mismatch", "complete_cash_generation_preview_required"),
    ],
)
def test_incomplete_or_incompatible_evidence_never_leaks_partial_values(case, blocker):
    result = compose_company_workbench_cash_generation_preview(
        _evidence_case(case),
        selected_ticker="NVDA",
        as_of=AS_OF,
    )

    _assert_fully_withheld(result, blocker)


@pytest.mark.parametrize(
    ("field", "value", "blocker"),
    [
        ("ticker", "OTHER", "observation_ticker:OTHER"),
        ("source", "other_source", "observation_source:other_source"),
    ],
)
def test_mixed_observation_identity_is_named_and_withheld(field, value, blocker):
    pilot = _accepted_sec_preview()
    observations = (
        replace(pilot.extraction.observations[0], **{field: value}),
        *pilot.extraction.observations[1:],
    )
    pilot = replace(
        pilot,
        extraction=replace(pilot.extraction, observations=observations),
    )

    result = compose_company_workbench_cash_generation_preview(
        pilot,
        selected_ticker="NVDA",
        as_of=AS_OF,
    )

    _assert_fully_withheld(result, blocker)


def test_q4_requires_adapter_recorded_explicit_filed_quarter():
    pilot = _accepted_sec_preview()
    observations = tuple(
        replace(
            row,
            fiscal_period="2027-Q4",
            period_end_date="2027-01-31",
            q4_evidence_state="explicit_filed_quarter",
        )
        for row in pilot.extraction.observations
    )
    revenue = replace(
        pilot.extraction.revenue_actuals[0],
        fiscal_period="2027-Q4",
        period_end_date="2027-01-31",
    )
    extraction = replace(
        pilot.extraction,
        fiscal_period="2027-Q4",
        period_start_date="2026-11-01",
        period_end_date="2027-01-31",
        observations=observations,
        revenue_actuals=(revenue,),
    )
    pilot = replace(
        pilot,
        extraction=extraction,
        acceptance=replace(pilot.acceptance, explicit_q4_periods=()),
    )

    result = compose_company_workbench_cash_generation_preview(
        pilot,
        selected_ticker="NVDA",
        as_of=AS_OF,
    )

    _assert_fully_withheld(result, "explicit_q4_evidence_required")


@pytest.mark.parametrize("as_of", ["", "not-a-timestamp", "2026-07-20T23:59:59"])
def test_invalid_or_naive_cutoff_withholds_instead_of_raising(as_of):
    result = compose_company_workbench_cash_generation_preview(
        _accepted_sec_preview(),
        selected_ticker="NVDA",
        as_of=as_of,
    )

    _assert_fully_withheld(result, "cutoff_invalid")
