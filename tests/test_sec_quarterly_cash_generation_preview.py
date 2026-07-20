from pathlib import Path

import pytest

from src.earnings_nowcast_contract import QuarterlyActual
from src.providers.sec_companyfacts import SECUserAgentError
from src.quarterly_cash_generation import QuarterlyBusinessObservation
from src.quarterly_cash_generation_adapter import QuarterlyAdapterAcceptance
from src.sec_quarterly_cash_generation_pilot import (
    SecQuarterlyPilotExtraction,
    SecQuarterlyPilotPreview,
)
from src.sec_quarterly_cash_generation_preview import (
    fetch_sec_quarterly_pilot_payloads,
    main,
    render_sec_quarterly_pilot_preview,
)


def _recording_fetcher(seen: list[str]):
    def fetch(url: str, _user_agent: str) -> bytes:
        seen.append(url)
        if "companyfacts" in url:
            return b'{"cik": 1045810, "facts": {}}'
        if "submissions" in url:
            return b'{"cik": "0001045810", "filings": {}}'
        return b"<html><body>filing</body></html>"

    return fetch


def _observation(metric: str, value: float, fact_id: str) -> QuarterlyBusinessObservation:
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
        source_ref=(
            "https://www.sec.gov/Archives/edgar/data/1045810/"
            f"000104581026000052/nvda-20260426.htm#{fact_id}"
        ),
        published_at="2026-05-20T20:35:52+00:00",
        retrieved_at="2026-07-20T15:00:00+00:00",
    )


def _accepted_preview() -> SecQuarterlyPilotPreview:
    observations = (
        _observation("operating_income", 53_536_000_000.0, "f-operating"),
        _observation("cash_from_operations", 50_344_000_000.0, "f-cfo"),
        _observation("capital_expenditures", -1_757_000_000.0, "f-capex"),
    )
    revenue = QuarterlyActual(
        ticker="NVDA",
        fiscal_period="2027-Q1",
        period_end_date="2026-04-26",
        reported_at="2026-05-20T20:35:52+00:00",
        revenue_actual=81_615_000_000.0,
        eps_actual=None,
        source="sec_companyfacts",
        source_ref=(
            "https://www.sec.gov/Archives/edgar/data/1045810/"
            "000104581026000052/nvda-20260426.htm#f-revenue"
        ),
        retrieved_at="2026-07-20T15:00:00+00:00",
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
        accepted_at="2026-05-20T20:35:52+00:00",
        source_url=(
            "https://www.sec.gov/Archives/edgar/data/1045810/"
            "000104581026000052/nvda-20260426.htm"
        ),
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


def test_client_fetches_only_three_exact_sec_endpoints_without_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    seen: list[str] = []

    payloads = fetch_sec_quarterly_pilot_payloads(
        cik="0001045810",
        accession="0001045810-26-000052",
        primary_document="nvda-20260426.htm",
        user_agent="Research Test test@example.com",
        fetcher=_recording_fetcher(seen),
    )

    assert seen == [
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
        "https://data.sec.gov/submissions/CIK0001045810.json",
        (
            "https://www.sec.gov/Archives/edgar/data/1045810/"
            "000104581026000052/nvda-20260426.htm"
        ),
    ]
    assert not list(tmp_path.iterdir())
    assert set(payloads) == {"companyfacts", "submissions", "filing_html"}


def test_client_requires_identified_sec_user_agent(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)

    with pytest.raises(SECUserAgentError):
        fetch_sec_quarterly_pilot_payloads(
            cik="0001045810",
            accession="0001045810-26-000052",
            primary_document="nvda-20260426.htm",
        )


def test_renderer_is_human_readable_and_keeps_non_activation_visible():
    text = render_sec_quarterly_pilot_preview(_accepted_preview())

    assert "status: accepted_for_review" in text
    assert "NVIDIA Q1 FY2027" in text
    assert "capital expenditures: -1757000000.0 USD" in text
    assert "capex sign evidence: explicit_filed_table_outflow" in text
    assert "production activation: false" in text
    assert "readiness promotions: none" in text
    assert "generated artifacts: none" in text
    assert not text.lstrip().startswith("{")


def test_preview_module_and_make_target_expose_no_write_or_apply_surface():
    source = Path("src/sec_quarterly_cash_generation_preview.py").read_text(
        encoding="utf-8"
    )
    makefile = Path("Makefile").read_text(encoding="utf-8")

    for forbidden in (
        "write_text",
        "Path(",
        "--output",
        "make readiness",
        "imports-apply",
        "data/cache",
        "yfinance",
        "fallback",
    ):
        assert forbidden not in source
    target = makefile.split("sec-quarterly-cash-preview:", 1)[1].split("\n\n", 1)[0]
    assert "--as-of" in target
    assert "--output" not in target
    assert "readiness" not in target


def test_cli_renders_accepted_preview_and_passes_exact_primary_document(
    monkeypatch, capsys
):
    captured: dict[str, object] = {}

    def fake_fetch(**kwargs):
        captured.update(kwargs)
        return {"companyfacts": {}, "submissions": {}, "filing_html": "<html/>"}

    monkeypatch.setattr(
        "src.sec_quarterly_cash_generation_preview.fetch_sec_quarterly_pilot_payloads",
        fake_fetch,
    )
    monkeypatch.setattr(
        "src.sec_quarterly_cash_generation_preview.extract_sec_quarterly_cash_generation",
        lambda **kwargs: (captured.update({"extraction": kwargs}) or _accepted_preview().extraction),
    )
    monkeypatch.setattr(
        "src.sec_quarterly_cash_generation_preview.preview_sec_quarterly_cash_generation",
        lambda **_kwargs: _accepted_preview(),
    )

    exit_code = main(
        [
            "--ticker",
            "NVDA",
            "--cik",
            "0001045810",
            "--fiscal-period",
            "2027-Q1",
            "--period-start",
            "2026-01-26",
            "--period-end",
            "2026-04-26",
            "--accession",
            "0001045810-26-000052",
            "--primary-document",
            "nvda-20260426.htm",
            "--as-of",
            "2026-07-20T23:59:59-04:00",
            "--sec-user-agent",
            "Research Test test@example.com",
        ]
    )

    assert exit_code == 0
    assert captured["primary_document"] == "nvda-20260426.htm"
    assert captured["extraction"]["primary_document"] == "nvda-20260426.htm"
    assert "status: accepted_for_review" in capsys.readouterr().out
