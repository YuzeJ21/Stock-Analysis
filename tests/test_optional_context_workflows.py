from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

from src.manual_optional_context_import import import_staged_optional_context
from src.optional_context_readiness import (
    NOT_AVAILABLE_REASON,
    build_analyst_estimates_readiness_frame,
    build_earnings_readiness_frame,
    build_optional_context_readiness_frames,
    build_optional_context_readiness_reports,
    format_optional_context_summary,
    main,
)


def _write_universe(root: Path) -> None:
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "universe.csv").write_text(
        "ticker,theme,defaultpurpose,marketcapbucket,notes\n"
        "NVDA,AI,Momentum Leader,Large,\n"
        "TSLA,EV,Core Compounder,Large,\n",
        encoding="utf-8",
    )


def test_import_earnings_accepts_valid_staged_csv(tmp_path: Path):
    _write_universe(tmp_path)
    staged = tmp_path / "data" / "staged" / "earnings"
    staged.mkdir(parents=True)
    (staged / "earnings_manual.csv").write_text(
        "ticker,fiscal_period,report_date,eps_actual,eps_estimate,revenue_actual,revenue_estimate,source,updated_at\n"
        "NVDA,Q1-2026,2026-05-20,1.05,1.00,26000,25500,company_release,2026-05-21\n",
        encoding="utf-8",
    )

    result = import_staged_optional_context("earnings", tmp_path)

    output = pd.read_csv(tmp_path / "data" / "imports" / "earnings.csv")
    rejected = pd.read_csv(tmp_path / "data" / "earnings_import_rejected.csv")
    assert result.status == "imported"
    assert result.rows_valid == 1
    assert rejected.empty
    assert output.loc[0, "ticker"] == "NVDA"
    assert output.loc[0, "last_earnings_date"] == "2026-05-20"


def test_import_analyst_estimates_rejects_invalid_rows(tmp_path: Path):
    _write_universe(tmp_path)
    staged = tmp_path / "data" / "staged" / "analyst_estimates"
    staged.mkdir(parents=True)
    (staged / "estimates_manual.csv").write_text(
        "ticker,period,eps_estimate,revenue_estimate,price_target_mean,source,updated_at\n"
        "NVDA,Q2-2026,abc,30000,150,trusted,2026-05-22\n"
        "MSFT,Q2-2026,2.10,62000,500,trusted,2026-05-22\n"
        "TSLA,Q2-2026,0.60,28000,300,,2026-05-22\n",
        encoding="utf-8",
    )

    result = import_staged_optional_context("analyst_estimates", tmp_path)

    rejected = pd.read_csv(tmp_path / "data" / "analyst_estimates_import_rejected.csv")
    assert result.status == "no_valid_rows"
    assert result.rows_rejected == 3
    assert not (tmp_path / "data" / "imports" / "analyst_estimates.csv").exists()
    assert set(rejected["rejection_reason"]) == {"eps_estimate_not_numeric", "ticker_not_in_universe", "missing_source"}


def test_earnings_readiness_requires_trusted_local_rows():
    universe = pd.DataFrame({"ticker": ["NVDA", "TSLA"]})
    earnings = pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "fiscal_period": "Q1-2026",
                "report_date": "2026-05-20",
                "eps_actual": 1.05,
                "source": "company_release",
            }
        ]
    )

    frame = build_earnings_readiness_frame(universe, earnings, updated_at="2026-05-24T00:00:00Z")
    lookup = frame.set_index("ticker")

    assert bool(lookup.loc["NVDA", "has_trusted_earnings"])
    assert not bool(lookup.loc["TSLA", "has_trusted_earnings"])
    assert lookup.loc["TSLA", "reason_not_ready"] == NOT_AVAILABLE_REASON


def test_analyst_estimates_readiness_requires_decision_useful_fields():
    universe = pd.DataFrame({"ticker": ["NVDA", "TSLA"]})
    estimates = pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "period": "Q2-2026",
                "eps_estimate": 1.20,
                "revenue_estimate": 27000,
                "price_target_mean": 150,
                "source": "trusted_manual",
            },
            {"ticker": "TSLA", "period": "Q2-2026", "source": "trusted_manual"},
        ]
    )

    frame = build_analyst_estimates_readiness_frame(universe, estimates, updated_at="2026-05-24T00:00:00Z")
    lookup = frame.set_index("ticker")

    assert bool(lookup.loc["NVDA", "has_trusted_analyst_estimates"])
    assert not bool(lookup.loc["TSLA", "has_trusted_analyst_estimates"])
    assert "eps_estimate" in lookup.loc["TSLA", "missing_fields"]


def test_optional_context_readiness_reports_write_data_files(tmp_path: Path):
    _write_universe(tmp_path)

    reports = build_optional_context_readiness_reports(tmp_path)

    assert (tmp_path / "data" / "earnings_readiness.csv").exists()
    assert (tmp_path / "data" / "analyst_estimates_readiness.csv").exists()
    assert len(reports["earnings_readiness"]) == 2
    assert reports["earnings_readiness"]["reason_not_ready"].eq(NOT_AVAILABLE_REASON).all()


def test_optional_context_summary_is_read_only(tmp_path: Path):
    _write_universe(tmp_path)

    reports = build_optional_context_readiness_frames(tmp_path)
    rendered = format_optional_context_summary(tmp_path, tmp_path / "data", reports, top_n=1).lower()

    assert "read-only: no earnings or analyst-estimate readiness csvs were written" in rendered
    assert "earnings_readiness: 0/2 ready; locked=2" in rendered
    assert "analyst_estimates_readiness: 0/2 ready; locked=2" in rendered
    assert "top locked earnings_readiness rows" in rendered
    assert "validate/preview/apply gates" in rendered
    assert not (tmp_path / "data" / "earnings_readiness.csv").exists()
    assert not (tmp_path / "data" / "analyst_estimates_readiness.csv").exists()


def test_optional_context_readiness_cli_prints_unlock_paths(tmp_path: Path, capsys):
    _write_universe(tmp_path)

    argv_before = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path)]
    try:
        main()
        output = capsys.readouterr().out.lower()
    finally:
        sys.argv = argv_before

    assert "optional context readiness:" in output
    assert "earnings_readiness: 0/2 ready" in output
    assert "analyst_estimates_readiness: 0/2 ready" in output
    assert "zero ready rows means the lane is intentionally locked until trusted local csv rows exist" in output
    assert "what stays withheld: earnings timing, surprise context, consensus estimates, revision context, and price-target context" in output
    assert "data/staged/earnings/" in output
    assert "data/staged/analyst_estimates/" in output
    assert "data/imports/earnings.csv" in output
    assert "data/imports/analyst_estimates.csv" in output
    assert "make import-earnings or make import-analyst-estimates" in output
    assert "make imports-validate -> make imports-preview -> make imports-apply -> make optional-context-readiness" in output
    assert "data/earnings_import_rejected.csv" in output
    assert "data/analyst_estimates_import_rejected.csv" in output
    assert "do not infer earnings or estimate context from price, dcf, peer, or sector data" in output


def test_dashboard_optional_context_empty_state_is_safe():
    from src.dashboard import optional_context_available, optional_context_empty_state_message

    assert optional_context_available({"ticker": "NVDA", "eps_actual": None}, ["eps_actual"]) is False
    assert "Not available: missing trusted local earnings input" in optional_context_empty_state_message("earnings")
    assert "Not available: missing trusted local analyst-estimate input" in optional_context_empty_state_message(
        "analyst_estimates"
    )
