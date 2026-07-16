from __future__ import annotations

from src.earnings_nowcast_sec_actuals import (
    extract_q1_q3_lineage,
    normalize_sec_duration_facts,
)


CUTOFF = "2026-06-30T23:59:59Z"
RETRIEVED_AT = "2026-06-26T12:00:00Z"


def _fact(
    *,
    val,
    start,
    end,
    filed="2026-06-25",
    fy=2026,
    fp="Q3",
    frame=None,
    accn="0000000000-26-000001",
):
    return {
        "val": val,
        "start": start,
        "end": end,
        "filed": filed,
        "form": "10-Q",
        "accn": accn,
        "fy": fy,
        "fp": fp,
        "frame": frame,
    }


def companyfacts_fixture(*, revenue, eps):
    return {
        "cik": 123456,
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": revenue}},
                "EarningsPerShareDiluted": {"units": {"USD/shares": eps}},
            }
        },
    }


def test_q3_lineage_keeps_aligned_quarter_and_rejects_ytd_and_comparative_period():
    payload = companyfacts_fixture(
        revenue=[
            _fact(val=30, start="2025-08-29", end="2026-05-28"),
            _fact(val=12, start="2026-02-27", end="2026-05-28", frame="CY2026Q2"),
            _fact(val=8, start="2025-02-28", end="2025-05-29", frame="CY2025Q2"),
        ],
        eps=[
            _fact(val=3.0, start="2025-08-29", end="2026-05-28"),
            _fact(val=1.2, start="2026-02-27", end="2026-05-28", frame="CY2026Q2"),
            _fact(val=0.8, start="2025-02-28", end="2025-05-29", frame="CY2025Q2"),
        ],
    )

    facts = normalize_sec_duration_facts(payload)
    result = extract_q1_q3_lineage("SYN1", payload, cutoff=CUTOFF, retrieved_at=RETRIEVED_AT)

    assert len(facts) == 6
    assert sorted(fact.duration_days for fact in facts) == [90, 90, 90, 90, 272, 272]
    assert [(row.fiscal_period, row.revenue_actual, row.eps_actual) for row in result.rows] == [
        ("2026-Q3", 12.0, 1.2)
    ]
    assert {row.state for row in result.audit_rows} >= {
        "accepted_explicit_quarter",
        "cumulative_fact_rejected",
        "comparative_period_relabelled",
    }


def test_later_comparative_uses_original_fiscal_identity_and_unknown_comparative_fails_closed():
    original_q2_revenue = _fact(
        val=8,
        start="2025-02-28",
        end="2025-05-29",
        filed="2025-06-25",
        fy=2025,
        fp="Q2",
        frame="CY2025Q2",
        accn="0000000000-25-000001",
    )
    original_q2_eps = _fact(
        val=0.8,
        start="2025-02-28",
        end="2025-05-29",
        filed="2025-06-25",
        fy=2025,
        fp="Q2",
        frame="CY2025Q2",
        accn="0000000000-25-000001",
    )
    comparative_revenue = _fact(val=9, start="2025-02-28", end="2025-05-29")
    comparative_eps = _fact(val=0.9, start="2025-02-28", end="2025-05-29")
    current_revenue = _fact(val=12, start="2026-02-27", end="2026-05-28", frame="CY2026Q2")
    current_eps = _fact(val=1.2, start="2026-02-27", end="2026-05-28", frame="CY2026Q2")

    result = extract_q1_q3_lineage(
        "SYN1",
        companyfacts_fixture(
            revenue=[original_q2_revenue, comparative_revenue, current_revenue],
            eps=[original_q2_eps, comparative_eps, current_eps],
        ),
        cutoff=CUTOFF,
        retrieved_at=RETRIEVED_AT,
    )

    q2_rows = [row for row in result.rows if row.fiscal_period == "2025-Q2"]
    assert [(row.revenue_actual, row.eps_actual) for row in q2_rows] == [(8.0, 0.8), (9.0, 0.9)]
    assert q2_rows[1].reported_at == "2026-06-25T00:00:00+00:00"
    assert "accepted_revision" in {row.state for row in result.audit_rows}

    no_original = extract_q1_q3_lineage(
        "SYN1",
        companyfacts_fixture(revenue=[comparative_revenue, current_revenue], eps=[comparative_eps, current_eps]),
        cutoff=CUTOFF,
        retrieved_at=RETRIEVED_AT,
    )

    assert [row.fiscal_period for row in no_original.rows] == ["2026-Q3"]
    assert "comparative_period_relabelled" in {row.state for row in no_original.audit_rows}


def test_missing_frame_keeps_uniquely_aligned_quarter():
    result = extract_q1_q3_lineage(
        "SYN1",
        companyfacts_fixture(
            revenue=[_fact(val=12, start="2026-02-27", end="2026-05-28")],
            eps=[_fact(val=1.2, start="2026-02-27", end="2026-05-28")],
        ),
        cutoff=CUTOFF,
        retrieved_at=RETRIEVED_AT,
    )

    assert result.rows[0].revenue_actual == 12.0


def test_conflicting_revenue_concepts_and_frames_withhold_only_revenue():
    revenue = _fact(val=12, start="2026-02-27", end="2026-05-28", frame="CY2026Q2")
    eps = _fact(val=1.2, start="2026-02-27", end="2026-05-28", frame="CY2026Q2")
    ambiguous_payload = companyfacts_fixture(revenue=[revenue], eps=[eps])
    ambiguous_payload["facts"]["us-gaap"]["Revenues"] = {
        "units": {"USD": [_fact(val=13, start="2026-02-27", end="2026-05-28", frame="CY2026Q2")]}
    }
    conflicting_frame_payload = companyfacts_fixture(
        revenue=[
            revenue,
            _fact(val=12, start="2026-02-27", end="2026-05-28", frame="CY2026Q1"),
        ],
        eps=[eps],
    )

    ambiguous_result = extract_q1_q3_lineage(
        "SYN1", ambiguous_payload, cutoff=CUTOFF, retrieved_at=RETRIEVED_AT
    )
    conflicting_frame_result = extract_q1_q3_lineage(
        "SYN1", conflicting_frame_payload, cutoff=CUTOFF, retrieved_at=RETRIEVED_AT
    )

    assert ambiguous_result.rows[0].revenue_actual is None
    assert ambiguous_result.rows[0].eps_actual == 1.2
    assert conflicting_frame_result.rows[0].revenue_actual is None
    assert "ambiguous_concept" in {row.state for row in ambiguous_result.audit_rows}


def test_revenue_only_quarter_is_preserved_as_metric_partial():
    result = extract_q1_q3_lineage(
        "SYN1",
        companyfacts_fixture(revenue=[_fact(val=12, start="2026-02-27", end="2026-05-28")], eps=[]),
        cutoff=CUTOFF,
        retrieved_at=RETRIEVED_AT,
    )

    assert result.rows[0].revenue_actual == 12.0
    assert result.rows[0].eps_actual is None
    assert "metric_partial" in {row.state for row in result.audit_rows}


def test_post_cutoff_quarter_is_withheld_with_audit_state():
    result = extract_q1_q3_lineage(
        "SYN1",
        companyfacts_fixture(
            revenue=[_fact(val=12, start="2026-02-27", end="2026-05-28", filed="2026-07-01")],
            eps=[_fact(val=1.2, start="2026-02-27", end="2026-05-28", filed="2026-07-01")],
        ),
        cutoff=CUTOFF,
        retrieved_at=RETRIEVED_AT,
    )

    assert result.rows == ()
    assert "post_cutoff_rejected" in {row.state for row in result.audit_rows}
