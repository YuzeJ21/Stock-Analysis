from __future__ import annotations

import csv
import json
import time
from dataclasses import replace
from pathlib import Path

import pytest

import src.earnings_nowcast_sec_actuals as sec_actuals
from src.earnings_nowcast_contract import ConsensusSnapshot, QuarterlyActual
from src.earnings_nowcast_readiness import assess_nowcast_readiness
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
  <tr><th>Period ended</th><th>January 26, 2025</th></tr>
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
    assert result.rows[0].period_end_date == "2025-01-26"
    assert result.rows[0].split_adjustment_basis == "split_adjusted_2024_06_07"


def test_extract_explicit_q4_actual_reads_the_column_labeled_q4():
    result = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        """
        <p>Fourth Quarter Fiscal 2025 Summary</p>
        <table>
          <tr><th></th><th>Fiscal 2025</th><th>Q4 FY25</th></tr>
          <tr><th>Period ended</th><th>January 28, 2024</th><th>January 26, 2025</th></tr>
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
          <tr><th>Period ended</th><th>January 26, 2025</th></tr>
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
          <tr><th>Period ended</th><th>January 26, 2025</th></tr>
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
          <tr><th>Period ended</th><th>January 26, 2025</th></tr>
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


def test_extract_explicit_q4_actual_requires_source_backed_period_end():
    result = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        """
        <p>Fourth Quarter Fiscal 2025 Summary</p>
        <table><tr><th></th><th>Q4 FY25</th></tr>
        <tr><td>Revenue</td><td>$39,331 million</td></tr>
        <tr><td>GAAP diluted earnings per share</td><td>$0.89</td></tr></table>
        """,
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert result.rows == ()
    assert "period_end_missing" in {row.state for row in result.audit_rows}


def test_extract_explicit_q4_actual_does_not_borrow_period_end_from_non_result_table():
    result = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        """
        <p>Fourth Quarter Fiscal 2025 Summary</p>
        <table>
          <tr><th></th><th>Q4 FY25</th></tr>
          <tr><td>Revenue</td><td>$39,331 million</td></tr>
          <tr><td>GAAP diluted earnings per share</td><td>$0.89</td></tr>
        </table>
        <table>
          <tr><th></th><th>Q4 FY25</th></tr>
          <tr><th>Period ended</th><th>January 26, 2025</th></tr>
          <tr><td>Cash and cash equivalents</td><td>$8,000 million</td></tr>
        </table>
        """,
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert result.rows == ()
    assert "period_end_missing" in {row.state for row in result.audit_rows}


def test_extract_explicit_q4_actual_does_not_borrow_period_end_across_metric_tables():
    result = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        """
        <p>Fourth Quarter Fiscal 2025 Summary</p>
        <table>
          <tr><th>Dollars in millions</th><th>Q4 FY25</th></tr>
          <tr><td>Revenue</td><td>$39,331</td></tr>
        </table>
        <table>
          <tr><th></th><th>Q4 FY25</th></tr>
          <tr><th>Period ended</th><th>January 26, 2025</th></tr>
          <tr><td>GAAP diluted earnings per share</td><td>$0.89</td></tr>
        </table>
        """,
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert len(result.rows) == 1
    assert result.rows[0].revenue_actual is None
    assert result.rows[0].eps_actual == 0.89
    assert result.rows[0].period_end_date == "2025-01-26"
    assert "period_end_missing" in {row.state for row in result.audit_rows}


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
        "Q4 amounts were derived by subtracting nine-month results from full-year results.",
        "Q4 amounts were computed from annual results less the first three quarters.",
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
    period_end_date="2025-06-30",
):
    return QuarterlyActual(
        ticker="SYN1",
        fiscal_period=fiscal_period,
        period_end_date=period_end_date,
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


def test_revision_linking_preserves_a_b_a_chain_and_latest_return_to_a():
    original = actual(
        "2025-Q2",
        revenue=100,
        eps=1.0,
        source_ref="sec://a-original",
        reported_at="2025-08-01T00:00:00Z",
    )
    revised = actual(
        "2025-Q2",
        revenue=110,
        eps=1.1,
        source_ref="sec://b-revised",
        reported_at="2025-11-01T00:00:00Z",
    )
    restored = actual(
        "2025-Q2",
        revenue=100,
        eps=1.0,
        source_ref="sec://a-restored",
        reported_at="2026-02-01T00:00:00Z",
    )

    linked = link_quarter_revisions([restored, original, revised])

    assert [row.source_ref for row in linked] == [
        "sec://a-original",
        "sec://b-revised",
        "sec://a-restored",
    ]
    assert linked[1].supersedes_source_ref == "sec://a-original"
    assert linked[2].supersedes_source_ref == "sec://b-revised"


def test_revision_linking_does_not_cross_period_end_collisions():
    original = actual(
        "2025-Q2",
        revenue=100,
        eps=1.0,
        source_ref="sec://first-period-end",
        reported_at="2025-08-01T00:00:00Z",
        period_end_date="2025-06-29",
    )
    colliding_identity = actual(
        "2025-Q2",
        revenue=110,
        eps=1.1,
        source_ref="sec://second-period-end",
        reported_at="2025-11-01T00:00:00Z",
        period_end_date="2025-06-30",
    )

    linked = link_quarter_revisions([original, colliding_identity])

    assert len(linked) == 2
    assert linked[1].supersedes_source_ref is None


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


def test_sec_actuals_cli_json_uses_injected_cached_fixture_stage(tmp_path, capsys):
    def cached_fixture_stage(tickers, **kwargs):
        assert tickers == ["SYN1"]
        assert kwargs["output_dir"] == tmp_path / "stage"
        assert kwargs["cutoff"] == CUTOFF
        assert kwargs["allow_network"] is False
        assert kwargs["refresh"] is False
        return write_sec_actuals_stage(tmp_path / "stage", {"SYN1": extraction_result()})

    sec_actuals.main(
        [
            "--tickers",
            "SYN1",
            "--output-dir",
            str(tmp_path / "stage"),
            "--cutoff",
            CUTOFF,
            "--no-network",
            "--json",
        ],
        stage_runner=cached_fixture_stage,
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["automatic_apply"] is False
    assert payload["tickers"]["SYN1"]["accepted_rows"]
    assert payload["tickers"]["SYN1"]["rejected_rows"]
    assert payload["tickers"]["SYN1"]["metrics"]["revenue"]["missing_q4"] is True
    assert payload["tickers"]["SYN1"]["metrics"]["eps"]["missing_q4"] is True
    assert payload["tickers"]["SYN1"]["source_refs"]


def test_sec_actuals_cli_fails_closed_when_stage_exceeds_max_runtime(tmp_path, capsys):
    def slow_stage(_tickers, **_kwargs):
        time.sleep(0.05)
        return write_sec_actuals_stage(tmp_path / "stage", {"SYN1": extraction_result()})

    with pytest.raises(SystemExit) as exc:
        sec_actuals.main(
            [
                "--tickers",
                "SYN1",
                "--output-dir",
                str(tmp_path / "stage"),
                "--cutoff",
                CUTOFF,
                "--no-network",
                "--max-runtime-seconds",
                "0.01",
            ],
            stage_runner=slow_stage,
        )

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "environment_limited" in captured.err
    assert "exceeded max runtime" in captured.err


@pytest.mark.parametrize(
    "output_dir",
    (
        Path(sec_actuals.__file__).resolve().parents[1] / "data" / "earnings_nowcast",
        Path(sec_actuals.__file__).resolve().parents[1] / "data" / "imports" / "earnings_nowcast",
    ),
)
def test_sec_actuals_cli_rejects_canonical_output_directories(output_dir, capsys):
    stage_called = False

    def forbidden_stage(*_args, **_kwargs):
        nonlocal stage_called
        stage_called = True
        raise AssertionError("canonical output must be rejected before staging")

    with pytest.raises(SystemExit) as exc:
        sec_actuals.main(
            [
                "--tickers",
                "SYN1",
                "--output-dir",
                str(output_dir),
                "--cutoff",
                CUTOFF,
                "--no-network",
            ],
            stage_runner=forbidden_stage,
        )

    assert exc.value.code == 2
    assert stage_called is False
    assert "generated temporary/review directory" in capsys.readouterr().err


def test_stage_rejects_existing_non_generated_evidence_directory(tmp_path):
    existing_evidence = tmp_path / "existing-evidence"
    existing_evidence.mkdir()
    sentinel = existing_evidence / "quarterly_actuals.csv"
    sentinel.write_text("trusted,evidence\n", encoding="utf-8")

    with pytest.raises(ValueError, match="existing non-generated evidence directory"):
        write_sec_actuals_stage(existing_evidence, {"SYN1": extraction_result()})

    assert sentinel.read_text(encoding="utf-8") == "trusted,evidence\n"


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


def test_stage_summary_reports_q4_and_continuity_by_metric(tmp_path):
    result = write_sec_actuals_stage(
        tmp_path / "stage",
        {
            "SYN1": ExtractionResult(
                rows=(
                    actual(
                        "2025-Q3",
                        revenue=100,
                        eps=None,
                        source_ref="sec://revenue-q3",
                        reported_at="2025-11-01T00:00:00Z",
                        period_end_date="2025-09-30",
                    ),
                    actual(
                        "2025-Q4",
                        revenue=110,
                        eps=None,
                        source_ref="sec://revenue-q4",
                        reported_at="2026-02-01T00:00:00Z",
                        period_end_date="2025-12-31",
                    ),
                    actual(
                        "2025-Q3",
                        revenue=None,
                        eps=1.0,
                        source_ref="sec://eps-q3",
                        reported_at="2025-11-01T00:00:00Z",
                        period_end_date="2025-09-30",
                    ),
                    actual(
                        "2026-Q1",
                        revenue=None,
                        eps=1.1,
                        source_ref="sec://eps-q1",
                        reported_at="2026-05-01T00:00:00Z",
                        period_end_date="2026-03-31",
                    ),
                ),
                audit_rows=(),
            )
        },
    )

    summary = sec_actuals.build_sec_actuals_stage_summary(result)["tickers"]["SYN1"]

    assert summary["metrics"]["revenue"]["missing_q4"] is False
    assert summary["metrics"]["revenue"]["continuity_gaps"] == []
    assert len(summary["metrics"]["revenue"]["accepted_rows"]) == 2
    assert summary["metrics"]["eps"]["missing_q4"] is True
    assert summary["metrics"]["eps"]["continuity_gaps"] == [
        {
            "after_fiscal_period": "2025-Q3",
            "before_fiscal_period": "2026-Q1",
            "missing_fiscal_periods": ["2025-Q4"],
        }
    ]
    assert len(summary["metrics"]["eps"]["accepted_rows"]) == 2

    inverse_result = write_sec_actuals_stage(
        tmp_path / "inverse-stage",
        {
            "SYN1": ExtractionResult(
                rows=(
                    actual(
                        "2025-Q3",
                        revenue=100,
                        eps=None,
                        source_ref="sec://inverse-revenue-q3",
                        reported_at="2025-11-01T00:00:00Z",
                        period_end_date="2025-09-30",
                    ),
                    actual(
                        "2026-Q1",
                        revenue=110,
                        eps=None,
                        source_ref="sec://inverse-revenue-q1",
                        reported_at="2026-05-01T00:00:00Z",
                        period_end_date="2026-03-31",
                    ),
                    actual(
                        "2025-Q3",
                        revenue=None,
                        eps=1.0,
                        source_ref="sec://inverse-eps-q3",
                        reported_at="2025-11-01T00:00:00Z",
                        period_end_date="2025-09-30",
                    ),
                    actual(
                        "2025-Q4",
                        revenue=None,
                        eps=1.1,
                        source_ref="sec://inverse-eps-q4",
                        reported_at="2026-02-01T00:00:00Z",
                        period_end_date="2025-12-31",
                    ),
                ),
                audit_rows=(),
            )
        },
    )

    inverse_summary = sec_actuals.build_sec_actuals_stage_summary(inverse_result)["tickers"]["SYN1"]

    assert inverse_summary["metrics"]["revenue"]["missing_q4"] is True
    assert inverse_summary["metrics"]["revenue"]["continuity_gaps"] == [
        {
            "after_fiscal_period": "2025-Q3",
            "before_fiscal_period": "2026-Q1",
            "missing_fiscal_periods": ["2025-Q4"],
        }
    ]
    assert inverse_summary["metrics"]["eps"]["missing_q4"] is False
    assert inverse_summary["metrics"]["eps"]["continuity_gaps"] == []


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


def test_stage_rejects_direct_rows_with_one_identity_and_multiple_period_ends(tmp_path):
    result = write_sec_actuals_stage(
        tmp_path / "stage",
        {
            "SYN1": ExtractionResult(
                rows=(
                    actual(
                        "2025-Q2",
                        revenue=100,
                        eps=1.0,
                        source_ref="sec://first-period-end",
                        reported_at="2025-08-01T00:00:00Z",
                        period_end_date="2025-06-29",
                    ),
                    actual(
                        "2025-Q2",
                        revenue=110,
                        eps=1.1,
                        source_ref="sec://second-period-end",
                        reported_at="2025-11-01T00:00:00Z",
                        period_end_date="2025-06-30",
                    ),
                ),
                audit_rows=(),
            )
        },
    )

    rows = list(csv.DictReader(Path(result.quarterly_actuals_path).open(encoding="utf-8")))
    rejected_rows = list(csv.DictReader(Path(result.rejected_path).open(encoding="utf-8")))
    assert rows == []
    assert result.rejected_row_count == 2
    assert {row["state"] for row in rejected_rows} == {"fiscal_period_conflict"}


def test_stage_rejects_direct_rows_with_one_period_end_and_multiple_identities(tmp_path):
    result = write_sec_actuals_stage(
        tmp_path / "stage",
        {
            "SYN1": ExtractionResult(
                rows=(
                    actual(
                        "2025-Q3",
                        revenue=100,
                        eps=1.0,
                        source_ref="sec://q3-collision",
                        reported_at="2025-11-01T00:00:00Z",
                        period_end_date="2025-09-30",
                    ),
                    actual(
                        "2025-Q4",
                        revenue=110,
                        eps=1.1,
                        source_ref="sec://q4-collision",
                        reported_at="2026-02-01T00:00:00Z",
                        period_end_date="2025-09-30",
                    ),
                ),
                audit_rows=(),
            )
        },
    )

    rows = list(csv.DictReader(Path(result.quarterly_actuals_path).open(encoding="utf-8")))
    rejected_rows = list(csv.DictReader(Path(result.rejected_path).open(encoding="utf-8")))
    assert rows == []
    assert result.rejected_row_count == 2
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


def test_stage_records_unavailable_q4_source_when_submissions_have_no_eligible_candidate(tmp_path):
    submissions = {
        "cik": "123456",
        "filings": {
            "recent": {
                "form": ["10-K", "10-Q"],
                "filingDate": ["2026-02-25", "2026-05-25"],
                "reportDate": ["2026-01-25", "2026-04-25"],
                "accessionNumber": ["0000123456-26-000001", "0000123456-26-000002"],
            }
        },
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
        filing_index_loader=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("no eligible Q4 candidate must not fetch a filing index")
        ),
    )

    rejected_rows = list(csv.DictReader(Path(result.rejected_path).open(encoding="utf-8")))
    assert result.accepted_row_count == 0
    assert {(row["state"], row["detail"]) for row in rejected_rows} == {
        (
            "q4_source_unavailable",
            "no eligible 8-K or 8-K/A Q4 candidate filing was found",
        ),
    }


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
    release_html = (
        Q4_RELEASE_HTML.replace("Fiscal 2025", "Fiscal 2026")
        .replace("FY25", "FY26")
        .replace("January 26, 2025", "January 25, 2026")
    )

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
    assert rows[0]["period_end_date"] == "2026-01-25"
    assert rows[0]["source_ref"].endswith("/earnings-release.htm")


def test_stage_does_not_use_submission_report_date_as_q4_period_end(tmp_path):
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
    release_without_period_end = """
    <p>Fourth Quarter Fiscal 2026 Summary</p>
    <table><tr><th></th><th>Q4 FY26</th></tr>
    <tr><td>Revenue</td><td>$40 billion</td></tr>
    <tr><td>GAAP diluted earnings per share</td><td>$0.89</td></tr></table>
    """

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
        exhibit_document_loader=lambda *_args, **_kwargs: release_without_period_end,
    )

    rows = list(csv.DictReader(Path(result.quarterly_actuals_path).open(encoding="utf-8")))
    rejected_rows = list(csv.DictReader(Path(result.rejected_path).open(encoding="utf-8")))
    assert rows == []
    assert {row["state"] for row in rejected_rows} == {"period_end_missing"}


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
            <tr><th>Period ended</th><th>January 25, 2026</th></tr>
            <tr><td>Revenue</td><td>$40 billion</td></tr></table>
        """,
        "eps.htm": """
            <p>Fourth Quarter Fiscal 2026 Summary</p>
            <table><tr><th></th><th>Q4 FY26</th></tr>
            <tr><th>Period ended</th><th>January 25, 2026</th></tr>
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
    assert q2_rows[1].reported_at == "2026-06-25T23:59:59+00:00"
    assert "accepted_revision" in {row.state for row in result.audit_rows}

    no_original = extract_q1_q3_lineage(
        "SYN1",
        companyfacts_fixture(revenue=[comparative_revenue, current_revenue], eps=[comparative_eps, current_eps]),
        cutoff=CUTOFF,
        retrieved_at=RETRIEVED_AT,
    )

    assert [row.fiscal_period for row in no_original.rows] == ["2026-Q3"]
    assert "comparative_period_relabelled" in {row.state for row in no_original.audit_rows}


def test_companyfacts_date_only_filing_is_available_at_end_of_day():
    payload = companyfacts_fixture(
        revenue=[
            _fact(
                val=12,
                start="2026-01-20",
                end="2026-04-19",
                filed="2026-04-20",
                fy=2026,
                fp="Q1",
            )
        ],
        eps=[
            _fact(
                val=1.2,
                start="2026-01-20",
                end="2026-04-19",
                filed="2026-04-20",
                fy=2026,
                fp="Q1",
            )
        ],
    )

    early = extract_q1_q3_lineage(
        "SYN1",
        payload,
        cutoff="2026-04-20T00:00:01Z",
        retrieved_at=RETRIEVED_AT,
    )
    end_of_day = extract_q1_q3_lineage(
        "SYN1",
        payload,
        cutoff="2026-04-20T23:59:59Z",
        retrieved_at=RETRIEVED_AT,
    )

    assert early.rows == ()
    assert "post_cutoff_rejected" in {row.state for row in early.audit_rows}
    assert len(end_of_day.rows) == 1
    assert end_of_day.rows[0].reported_at == "2026-04-20T23:59:59+00:00"


def test_one_fiscal_identity_mapping_to_multiple_period_ends_fails_closed():
    payload = companyfacts_fixture(
        revenue=[
            _fact(
                val=12,
                start="2026-02-27",
                end="2026-05-28",
                fy=2026,
                fp="Q2",
                accn="0000000000-26-000001",
            ),
            _fact(
                val=13,
                start="2026-02-28",
                end="2026-05-29",
                fy=2026,
                fp="Q2",
                accn="0000000000-26-000002",
            ),
        ],
        eps=[
            _fact(
                val=1.2,
                start="2026-02-27",
                end="2026-05-28",
                fy=2026,
                fp="Q2",
                accn="0000000000-26-000001",
            ),
            _fact(
                val=1.3,
                start="2026-02-28",
                end="2026-05-29",
                fy=2026,
                fp="Q2",
                accn="0000000000-26-000002",
            ),
        ],
    )

    result = extract_q1_q3_lineage("SYN1", payload, cutoff=CUTOFF, retrieved_at=RETRIEVED_AT)

    assert result.rows == ()
    conflicts = [row for row in result.audit_rows if row.state == "fiscal_period_conflict"]
    assert len(conflicts) == 4
    assert {row.end for row in conflicts} == {"2026-05-28", "2026-05-29"}


def test_companyfacts_eps_split_basis_is_unverified_for_split_restatement():
    original_eps = _fact(
        val=0.80,
        start="2025-02-28",
        end="2025-05-29",
        filed="2025-06-25",
        fy=2025,
        fp="Q2",
        accn="0000000000-25-000001",
    )
    comparative_eps = _fact(
        val=0.08,
        start="2025-02-28",
        end="2025-05-29",
        filed="2026-06-25",
        fy=2026,
        fp="Q3",
        accn="0000000000-26-000001",
    )
    result = extract_q1_q3_lineage(
        "SYN1",
        companyfacts_fixture(
            revenue=[
                _fact(
                    val=8,
                    start="2025-02-28",
                    end="2025-05-29",
                    filed="2025-06-25",
                    fy=2025,
                    fp="Q2",
                    accn="0000000000-25-000001",
                ),
                _fact(val=12, start="2026-02-27", end="2026-05-28"),
            ],
            eps=[
                original_eps,
                comparative_eps,
                _fact(val=1.2, start="2026-02-27", end="2026-05-28"),
            ],
        ),
        cutoff=CUTOFF,
        retrieved_at=RETRIEVED_AT,
    )

    eps_rows = [row for row in result.rows if row.eps_actual is not None]
    assert {row.split_adjustment_basis for row in eps_rows} == {
        "companyfacts_split_basis_unverified"
    }
    assert "split_basis_unverified" in {row.state for row in result.audit_rows}


def test_explicit_filed_q4_keeps_revenue_ready_while_companyfacts_eps_is_withheld():
    companyfacts = extract_q1_q3_lineage(
        "SYN1",
        companyfacts_fixture(
            revenue=[_fact(val=36_000_000_000, start="2026-02-27", end="2026-05-28")],
            eps=[_fact(val=0.8, start="2026-02-27", end="2026-05-28")],
        ),
        cutoff=CUTOFF,
        retrieved_at=RETRIEVED_AT,
    )
    filed_q4 = extract_explicit_q4_actual(
        "SYN1",
        Q4_EXHIBIT,
        Q4_RELEASE_HTML,
        fiscal_period="2025-Q4",
        filed_at="2026-02-25T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
    )

    companyfacts_seed = companyfacts.rows[0]
    q4_seed = filed_q4.rows[0]
    history = [
        replace(
            q4_seed,
            fiscal_period="2024-Q4",
            period_end_date="2024-12-31",
            reported_at="2025-02-20T00:00:00Z",
            retrieved_at="2025-02-21T00:00:00Z",
            revenue_actual=30_000_000_000,
            eps_actual=0.70,
            source_ref=f"{q4_seed.source_ref}#2024-Q4",
        ),
        replace(
            companyfacts_seed,
            fiscal_period="2025-Q1",
            period_end_date="2025-03-31",
            reported_at="2025-05-20T00:00:00Z",
            retrieved_at="2025-05-21T00:00:00Z",
            revenue_actual=32_000_000_000,
            eps_actual=0.72,
            source_ref=f"{companyfacts_seed.source_ref}#2025-Q1",
        ),
        replace(
            companyfacts_seed,
            fiscal_period="2025-Q2",
            period_end_date="2025-06-30",
            reported_at="2025-08-20T00:00:00Z",
            retrieved_at="2025-08-21T00:00:00Z",
            revenue_actual=34_000_000_000,
            eps_actual=0.76,
            source_ref=f"{companyfacts_seed.source_ref}#2025-Q2",
        ),
        replace(
            companyfacts_seed,
            fiscal_period="2025-Q3",
            period_end_date="2025-09-30",
            reported_at="2025-11-20T00:00:00Z",
            retrieved_at="2025-11-21T00:00:00Z",
            revenue_actual=36_000_000_000,
            eps_actual=0.80,
            source_ref=f"{companyfacts_seed.source_ref}#2025-Q3",
        ),
        replace(
            q4_seed,
            fiscal_period="2025-Q4",
            period_end_date="2025-12-31",
            reported_at="2026-02-20T00:00:00Z",
            retrieved_at="2026-02-21T00:00:00Z",
            revenue_actual=39_331_000_000,
            source_ref=f"{q4_seed.source_ref}#2025-Q4",
        ),
    ]
    consensus = ConsensusSnapshot(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        snapshot_at="2026-02-25T00:00:00Z",
        retrieved_at="2026-02-25T01:00:00Z",
        revenue_consensus=41_000_000_000,
        eps_consensus=0.90,
        source="synthetic_test_fixture",
        source_ref="fixture:consensus:2026-Q1",
        revenue_basis=history[0].revenue_basis,
        eps_basis=history[-1].eps_basis,
        eps_share_basis=history[-1].eps_share_basis,
        eps_operations_basis=history[-1].eps_operations_basis,
        split_adjustment_basis=history[-1].split_adjustment_basis,
    )

    readiness = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp="2026-03-01T00:00:00Z",
        actuals=history,
        consensus=[consensus],
    )

    assert readiness.revenue_ready is True
    assert readiness.eps_ready is False
    assert "incompatible_eps_definition" in readiness.missing_evidence
    assert history[-1].split_adjustment_basis == "split_adjusted_2024_06_07"
    assert {
        row.split_adjustment_basis for row in history[1:4]
    } == {"companyfacts_split_basis_unverified"}


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
