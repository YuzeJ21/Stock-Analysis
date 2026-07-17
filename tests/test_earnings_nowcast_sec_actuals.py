from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.earnings_nowcast_contract import QuarterlyActual
from src.earnings_nowcast_sec_actuals import (
    ExtractionAuditRow,
    ExtractionResult,
    extract_explicit_q4_actual,
    extract_q1_q3_lineage,
    link_quarter_revisions,
    normalize_sec_duration_facts,
    stage_sec_quarterly_actuals,
    write_sec_actuals_stage,
)
from src.providers.sec_submissions import FiledExhibit


CUTOFF = "2026-06-30T23:59:59Z"
RETRIEVED_AT = "2026-06-26T12:00:00Z"


Q4_EXHIBIT = FiledExhibit(
    document_type="EX-99.1",
    document_name="earnings-release.htm",
    source_ref="https://www.sec.gov/Archives/edgar/data/123456/000012345626000001/earnings-release.htm",
)


Q4_RELEASE_HTML = """
<p>Fourth Quarter Fiscal 2025 Summary</p>
<table>
  <tr><th></th><th>Q4 FY25</th></tr>
  <tr><td>Revenue</td><td>$39,331 million</td></tr>
  <tr><td>GAAP diluted earnings per share</td><td>$0.89</td></tr>
</table>
<p>All per-share amounts are retrospectively adjusted for the ten-for-one split effective June 7, 2024.</p>
"""


def test_extract_explicit_q4_actual_reads_filed_result_table():
    result = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        Q4_RELEASE_HTML,
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert len(result.rows) == 1
    assert result.rows[0].fiscal_period == "2025-Q4"
    assert result.rows[0].revenue_actual == 39_331_000_000
    assert result.rows[0].eps_actual == 0.89
    assert result.rows[0].split_adjustment_basis == "split_adjusted_2024_06_07"


def test_extract_explicit_q4_actual_reads_the_column_labeled_q4():
    result = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        """
        <p>Fourth Quarter Fiscal 2025 Summary</p>
        <table>
          <tr><th></th><th>Fiscal 2025</th><th>Q4 FY25</th></tr>
          <tr><td>Revenue</td><td>$160 billion</td><td>$39,331 million</td></tr>
          <tr><td>GAAP diluted earnings per share</td><td>$3.00</td><td>$0.89</td></tr>
        </table>
        """,
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert result.rows[0].revenue_actual == 39_331_000_000
    assert result.rows[0].eps_actual == 0.89


def test_extract_explicit_q4_actual_uses_explicit_table_level_revenue_scale():
    result = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        """
        <p>Fourth Quarter Fiscal 2025 Summary</p>
        <table>
          <tr><th>Dollars in millions</th><th>Q4 FY25</th></tr>
          <tr><td>Revenue</td><td>$39,331</td></tr>
          <tr><td>GAAP diluted earnings per share</td><td>$0.89</td></tr>
        </table>
        """,
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert result.rows[0].revenue_actual == 39_331_000_000


def test_extract_explicit_q4_actual_uses_caption_table_level_revenue_scale():
    result = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        """
        <p>Fourth Quarter Fiscal 2025 Summary</p>
        <table>
          <caption>Dollars in millions</caption>
          <tr><th></th><th>Q4 FY25</th></tr>
          <tr><td>Revenue</td><td>$39,331</td></tr>
          <tr><td>GAAP diluted earnings per share</td><td>$0.89</td></tr>
        </table>
        """,
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert result.rows[0].revenue_actual == 39_331_000_000


def test_extract_explicit_q4_actual_rejects_revenue_without_an_unambiguous_scale():
    result = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        """
        <p>Fourth Quarter Fiscal 2025 Summary</p>
        <table>
          <tr><th></th><th>Q4 FY25</th></tr>
          <tr><td>Revenue</td><td>$39,331</td></tr>
          <tr><td>GAAP diluted earnings per share</td><td>$0.89</td></tr>
        </table>
        """,
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert result.rows[0].revenue_actual is None
    assert result.rows[0].eps_actual == 0.89
    assert "revenue_scale_missing" in {row.state for row in result.audit_rows}


def test_extract_explicit_q4_actual_rejects_annual_only_table():
    result = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        """
        <table><tr><th></th><th>Fiscal 2025</th></tr>
        <tr><td>Revenue</td><td>$100 billion</td></tr>
        <tr><td>GAAP diluted earnings per share</td><td>$2.00</td></tr></table>
        """,
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert result.rows == ()
    assert "quarter_header_missing" in {row.state for row in result.audit_rows}


def test_extract_explicit_q4_actual_rejects_guidance_and_non_gaap_metrics():
    result = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        """
        <p>Q4 FY25 outlook</p><table><tr><th></th><th>Q4 FY25</th></tr>
        <tr><td>Revenue expected</td><td>approximately $40 billion</td></tr>
        <tr><td>Non-GAAP diluted earnings per share</td><td>$0.90</td></tr></table>
        """,
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert result.rows == ()
    assert {row.state for row in result.audit_rows} >= {"guidance_or_outlook_rejected", "gaap_eps_missing"}


def test_extract_explicit_q4_actual_rejects_derived_and_ambiguous_q4_headers():
    result = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        """
        <table><tr><th></th><th>Q4 / Fiscal 2025</th></tr>
        <tr><td>Revenue (annual less nine months)</td><td>$40 billion</td></tr>
        <tr><td>GAAP diluted earnings per share</td><td>$0.89</td></tr></table>
        """,
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert result.rows == ()
    assert {row.state for row in result.audit_rows} >= {"ambiguous_period_header", "derived_q4_rejected"}


def test_extract_explicit_q4_actual_rejects_nearby_annual_less_nine_month_derivation_note():
    result = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        """
        <p>Fourth Quarter Fiscal 2025 Summary</p>
        <table><tr><th></th><th>Q4 FY25</th></tr>
        <tr><td>Revenue</td><td>$40 billion</td></tr>
        <tr><td>GAAP diluted earnings per share</td><td>$0.89</td></tr></table>
        <p>Q4 amounts were calculated from annual less nine-month results.</p>
        """,
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert result.rows == ()
    assert "derived_q4_rejected" in {row.state for row in result.audit_rows}


@pytest.mark.parametrize(
    "derivation_note",
    (
        "Q4 amounts were calculated from annual less nine months results.",
        "Q4 amounts were calculated from full year minus 9 months results.",
    ),
)
def test_extract_explicit_q4_actual_rejects_plural_and_numeric_annual_minus_nine_month_derivation(
    derivation_note,
):
    result = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        f"""
        <p>Fourth Quarter Fiscal 2025 Summary</p>
        <table><tr><th></th><th>Q4 FY25</th></tr>
        <tr><td>Revenue</td><td>$40 billion</td></tr>
        <tr><td>GAAP diluted earnings per share</td><td>$0.89</td></tr></table>
        <p>{derivation_note}</p>
        """,
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert result.rows == ()
    assert "derived_q4_rejected" in {row.state for row in result.audit_rows}


def test_extract_explicit_q4_actual_rejects_post_cutoff_but_keeps_as_reported_split_basis():
    post_cutoff = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        Q4_RELEASE_HTML,
        fiscal_period="2025-Q4",
        filed_at="2026-07-01T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
        cutoff=CUTOFF,
    )
    as_reported = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        Q4_RELEASE_HTML.replace(
            "All per-share amounts are retrospectively adjusted for the ten-for-one split effective June 7, 2024.",
            "",
        ),
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert post_cutoff.rows == ()
    assert "post_cutoff_rejected" in {row.state for row in post_cutoff.audit_rows}
    assert as_reported.rows[0].split_adjustment_basis == "as_reported"


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


def actual(
    fiscal_period,
    *,
    revenue,
    eps,
    source_ref,
    reported_at,
    source="sec_companyfacts",
):
    return QuarterlyActual(
        ticker="SYN1",
        fiscal_period=fiscal_period,
        period_end_date="2025-06-30",
        reported_at=reported_at,
        revenue_actual=revenue,
        eps_actual=eps,
        source=source,
        source_ref=source_ref,
        retrieved_at=RETRIEVED_AT,
    )


def extraction_result():
    return ExtractionResult(
        rows=(
            actual(
                "2025-Q2",
                revenue=100,
                eps=1.0,
                source_ref="sec://original",
                reported_at="2025-08-01T00:00:00Z",
            ),
        ),
        audit_rows=(
            ExtractionAuditRow(
                ticker="SYN1",
                state="cumulative_fact_rejected",
                metric="revenue",
                fiscal_period="2025-Q2",
                source_ref="sec://original",
                detail="duration is cumulative",
                concept="Revenues",
                start="2025-01-01",
                end="2025-06-30",
                frame="CY2025",
                accession="0000000000-25-000001",
            ),
        ),
    )


def test_later_changed_presentation_is_append_only_revision():
    original = actual(
        "2025-Q2",
        revenue=100,
        eps=1.0,
        source_ref="sec://original",
        reported_at="2025-08-01T00:00:00Z",
    )
    revised = actual(
        "2025-Q2",
        revenue=100,
        eps=0.1,
        source_ref="sec://split-adjusted",
        reported_at="2025-11-01T00:00:00Z",
    )

    linked = link_quarter_revisions([original, revised])

    assert len(linked) == 2
    assert linked[1].supersedes_source_ref == original.source_ref
    assert linked[0].eps_actual == 1.0


def test_later_unchanged_presentation_is_deduplicated():
    original = actual(
        "2025-Q2",
        revenue=100,
        eps=1.0,
        source_ref="sec://original",
        reported_at="2025-08-01T00:00:00Z",
    )
    later_same = actual(
        "2025-Q2",
        revenue=100,
        eps=1.0,
        source_ref="sec://later-presentation",
        reported_at="2025-11-01T00:00:00Z",
    )

    linked = link_quarter_revisions([later_same, original])

    assert linked == (original,)


def test_unrelated_conflicting_source_is_not_marked_as_revision():
    sec_original = actual(
        "2025-Q2",
        revenue=100,
        eps=1.0,
        source_ref="sec://original",
        reported_at="2025-08-01T00:00:00Z",
    )
    unrelated = actual(
        "2025-Q2",
        revenue=100,
        eps=0.1,
        source_ref="other://conflict",
        reported_at="2025-11-01T00:00:00Z",
        source="other_source",
    )

    linked = link_quarter_revisions([sec_original, unrelated])

    assert len(linked) == 2
    assert linked[1].supersedes_source_ref is None


def test_stage_writes_only_explicit_output_directory(tmp_path):
    result = write_sec_actuals_stage(tmp_path / "stage", {"SYN1": extraction_result()})

    stage_dir = tmp_path / "stage"
    assert Path(result.quarterly_actuals_path).parent == stage_dir
    assert (stage_dir / "quarterly_actuals.csv").exists()
    assert (stage_dir / "consensus_snapshots.csv").read_text(encoding="utf-8").count("\n") == 1
    assert (stage_dir / "signals.csv").read_text(encoding="utf-8").count("\n") == 1
    assert result.automatic_apply is False
    assert not (tmp_path / "data").exists()

    audit = json.loads((stage_dir / "sec_actuals_audit.json").read_text(encoding="utf-8"))
    assert audit["audit_rows"][0]["concept"] == "Revenues"
    assert audit["audit_rows"][0]["start"] == "2025-01-01"
    assert audit["audit_rows"][0]["end"] == "2025-06-30"
    assert audit["audit_rows"][0]["frame"] == "CY2025"
    assert audit["audit_rows"][0]["accession"] == "0000000000-25-000001"

    with (stage_dir / "sec_actuals_rejected.csv").open(newline="", encoding="utf-8") as handle:
        rejected = list(csv.DictReader(handle))
    assert rejected[0]["reason_code"] == "cumulative_fact_rejected"
    assert rejected[0]["state"] == "cumulative_fact_rejected"


def test_stage_keeps_revenue_only_metric_partial_out_of_rejected_rows(tmp_path):
    extraction = extract_q1_q3_lineage(
        "SYN1",
        companyfacts_fixture(revenue=[_fact(val=12, start="2026-02-27", end="2026-05-28")], eps=[]),
        cutoff=CUTOFF,
        retrieved_at=RETRIEVED_AT,
    )

    result = write_sec_actuals_stage(tmp_path / "stage", {"SYN1": extraction})

    with Path(result.quarterly_actuals_path).open(newline="", encoding="utf-8") as handle:
        staged_rows = list(csv.DictReader(handle))
    with Path(result.rejected_path).open(newline="", encoding="utf-8") as handle:
        rejected_rows = list(csv.DictReader(handle))

    assert len(staged_rows) == 1
    assert staged_rows[0]["revenue_actual"] == "12.0"
    assert staged_rows[0]["eps_actual"] == ""
    assert result.rejected_row_count == 0
    assert rejected_rows == []


def test_stage_writes_fiscal_period_conflicts_to_rejected_rows(tmp_path):
    result = write_sec_actuals_stage(
        tmp_path / "stage",
        {
            "SYN1": extract_q1_q3_lineage(
                "SYN1",
                companyfacts_fixture(
                    revenue=[
                        _fact(val=12, start="2026-02-27", end="2026-05-28", fp="Q2"),
                        _fact(val=12, start="2026-02-27", end="2026-05-28", fp="Q3"),
                    ],
                    eps=[
                        _fact(val=1.2, start="2026-02-27", end="2026-05-28", fp="Q2"),
                        _fact(val=1.2, start="2026-02-27", end="2026-05-28", fp="Q3"),
                    ],
                ),
                cutoff=CUTOFF,
                retrieved_at=RETRIEVED_AT,
            )
        },
    )

    with Path(result.rejected_path).open(newline="", encoding="utf-8") as handle:
        rejected_rows = list(csv.DictReader(handle))

    assert result.rejected_row_count == 4
    assert {row["state"] for row in rejected_rows} == {"fiscal_period_conflict"}


def test_stage_orchestrator_writes_unresolved_and_fetch_failures_to_rejected_rows(tmp_path):
    result = stage_sec_quarterly_actuals(
        ["missing", "broken"],
        output_dir=tmp_path / "stage",
        cutoff=CUTOFF,
        user_agent="Test test@example.com",
        retrieved_at=RETRIEVED_AT,
        ticker_map={"BROKEN": {"ticker": "BROKEN", "cik": "0000123456"}},
        companyfacts_loader=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fixture failure")),
    )

    with Path(result.rejected_path).open(newline="", encoding="utf-8") as handle:
        rejected_rows = list(csv.DictReader(handle))

    assert result.rejected_row_count == 2
    assert {(row["ticker"], row["state"]) for row in rejected_rows} == {
        ("BROKEN", "companyfacts_fetch_failed"),
        ("MISSING", "ticker_unresolved"),
    }


def test_stage_uses_injected_ticker_map_and_companyfacts_fetcher(tmp_path):
    result = stage_sec_quarterly_actuals(
        ["syn1", "missing"],
        output_dir=tmp_path / "stage",
        cutoff=CUTOFF,
        user_agent="Test test@example.com",
        retrieved_at=RETRIEVED_AT,
        ticker_map={"SYN1": {"ticker": "SYN1", "cik": "0000123456"}},
        companyfacts_fetcher=lambda *_: companyfacts_fixture(
            revenue=[_fact(val=12, start="2026-02-27", end="2026-05-28")],
            eps=[_fact(val=1.2, start="2026-02-27", end="2026-05-28")],
        ),
        submissions_loader=lambda *_args, **_kwargs: {"filings": {"recent": {}}},
    )

    assert result.requested_tickers == ("MISSING", "SYN1")
    assert result.accepted_tickers == ("SYN1",)
    assert result.withheld_tickers == ("MISSING",)
    assert result.accepted_row_count == 1
    assert result.automatic_apply is False


def test_stage_combines_explicit_q4_exhibit_using_injected_document_loaders(tmp_path):
    submissions = {
        "cik": "123456",
        "filings": {
            "recent": {
                "form": ["8-K"],
                "filingDate": ["2026-02-25"],
                "reportDate": ["2026-01-25"],
                "accessionNumber": ["0000123456-26-000001"],
            }
        },
    }
    index_html = """
    <table><tr><td><a href="earnings-release.htm">earnings-release.htm</a></td>
    <td>Earnings release</td><td>EX-99.1</td></tr></table>
    """
    release_html = Q4_RELEASE_HTML.replace("Fiscal 2025", "Fiscal 2026").replace("FY25", "FY26")

    result = stage_sec_quarterly_actuals(
        ["syn1"],
        output_dir=tmp_path / "stage",
        cutoff=CUTOFF,
        user_agent="Test test@example.com",
        retrieved_at=RETRIEVED_AT,
        ticker_map={"SYN1": {"ticker": "SYN1", "cik": "0000123456"}},
        companyfacts_loader=lambda *_args, **_kwargs: companyfacts_fixture(revenue=[], eps=[]),
        submissions_loader=lambda *_args, **_kwargs: submissions,
        filing_index_loader=lambda *_args, **_kwargs: index_html,
        exhibit_document_loader=lambda *_args, **_kwargs: release_html,
    )

    rows = list(csv.DictReader(Path(result.quarterly_actuals_path).open(encoding="utf-8")))
    assert [(row["fiscal_period"], row["source"]) for row in rows] == [("2026-Q4", "sec_filed_exhibit")]
    assert rows[0]["source_ref"].endswith("/earnings-release.htm")


def test_stage_withholds_independent_q4_metrics_from_separate_exhibits(tmp_path):
    submissions = {
        "cik": "123456",
        "filings": {
            "recent": {
                "form": ["8-K"],
                "filingDate": ["2026-02-25"],
                "reportDate": ["2026-01-25"],
                "accessionNumber": ["0000123456-26-000001"],
            }
        },
    }
    index_html = """
    <table>
      <tr><td><a href="revenue.htm">revenue.htm</a></td><td>EX-99.1</td></tr>
      <tr><td><a href="eps.htm">eps.htm</a></td><td>EX-99.2</td></tr>
    </table>
    """
    documents = {
        "revenue.htm": """
            <p>Fourth Quarter Fiscal 2026 Summary</p>
            <table><tr><th></th><th>Q4 FY26</th></tr>
            <tr><td>Revenue</td><td>$40 billion</td></tr></table>
        """,
        "eps.htm": """
            <p>Fourth Quarter Fiscal 2026 Summary</p>
            <table><tr><th></th><th>Q4 FY26</th></tr>
            <tr><td>GAAP diluted earnings per share</td><td>$0.89</td></tr></table>
        """,
    }

    result = stage_sec_quarterly_actuals(
        ["syn1"],
        output_dir=tmp_path / "stage",
        cutoff=CUTOFF,
        user_agent="Test test@example.com",
        retrieved_at=RETRIEVED_AT,
        ticker_map={"SYN1": {"ticker": "SYN1", "cik": "0000123456"}},
        companyfacts_loader=lambda *_args, **_kwargs: companyfacts_fixture(revenue=[], eps=[]),
        submissions_loader=lambda *_args, **_kwargs: submissions,
        filing_index_loader=lambda *_args, **_kwargs: index_html,
        exhibit_document_loader=lambda _cik, _accession, document_name, *_args, **_kwargs: documents[document_name],
    )

    rows = list(csv.DictReader(Path(result.quarterly_actuals_path).open(encoding="utf-8")))
    rejected_rows = list(csv.DictReader(Path(result.rejected_path).open(encoding="utf-8")))

    assert rows == []
    assert {(row["state"], row["fiscal_period"]) for row in rejected_rows} >= {
        ("ambiguous_concept", "2026-Q4"),
    }


def test_stage_rejects_same_day_date_only_filing_before_end_of_day_cutoff(tmp_path):
    submissions = {
        "cik": "123456",
        "filings": {
            "recent": {
                "form": ["8-K"],
                "filingDate": ["2026-02-25"],
                "reportDate": ["2026-01-25"],
                "accessionNumber": ["0000123456-26-000001"],
            }
        },
    }

    result = stage_sec_quarterly_actuals(
        ["syn1"],
        output_dir=tmp_path / "stage",
        cutoff="2026-02-25T12:00:00Z",
        user_agent="Test test@example.com",
        retrieved_at=RETRIEVED_AT,
        ticker_map={"SYN1": {"ticker": "SYN1", "cik": "0000123456"}},
        companyfacts_loader=lambda *_args, **_kwargs: companyfacts_fixture(revenue=[], eps=[]),
        submissions_loader=lambda *_args, **_kwargs: submissions,
        filing_index_loader=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("same-day filing must fail closed before exhibit lookup")),
    )

    rows = list(csv.DictReader(Path(result.quarterly_actuals_path).open(encoding="utf-8")))
    rejected_rows = list(csv.DictReader(Path(result.rejected_path).open(encoding="utf-8")))
    assert rows == []
    assert {(row["state"], row["accession"]) for row in rejected_rows} == {("post_cutoff_rejected", "0000123456-26-000001")}


def test_normalization_rejects_non_json_numeric_scalars_and_non_integral_fiscal_years():
    payload = companyfacts_fixture(
        revenue=[
            _fact(val=12, start="2026-02-27", end="2026-05-28", frame="CY2026Q2"),
            _fact(val=True, start="2026-02-27", end="2026-05-28"),
            _fact(val="12", start="2026-02-27", end="2026-05-28"),
            _fact(val=12, start="2026-02-27", end="2026-05-28", fy=2026.9),
            _fact(val=12, start="2026-02-27", end="2026-05-28", fy=True),
            _fact(val=12, start="2026-02-27", end="2026-05-28", fy="2026"),
        ],
        eps=[],
    )

    facts = normalize_sec_duration_facts(payload)

    assert [(fact.value, fact.fiscal_year) for fact in facts] == [(12.0, 2026)]


def test_normalization_rejects_oversized_integer_scalars():
    oversized_integer = 10**400
    payload = companyfacts_fixture(
        revenue=[
            _fact(val=12, start="2026-02-27", end="2026-05-28", frame="CY2026Q2"),
            _fact(val=oversized_integer, start="2026-02-27", end="2026-05-28"),
            _fact(val=12, start="2026-02-27", end="2026-05-28", fy=oversized_integer),
        ],
        eps=[],
    )

    facts = normalize_sec_duration_facts(payload)

    assert [(fact.value, fact.fiscal_year) for fact in facts] == [(12.0, 2026)]


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
