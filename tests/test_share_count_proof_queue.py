import pandas as pd

from src.share_count_proof_queue import (
    build_share_count_proof_queue,
    build_share_count_proof_queue_from_files,
    render_share_count_proof_queue,
)


def _sample_universe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "AMD",
                "default_purpose": "Momentum Leader",
                "market_cap_bucket": "Large",
                "in_active_universe": True,
            },
            {
                "ticker": "HOOD",
                "default_purpose": "Core Compounder",
                "market_cap_bucket": "Mid",
                "in_active_universe": False,
            },
            {
                "ticker": "NVDA",
                "default_purpose": "Momentum Leader",
                "market_cap_bucket": "Large",
                "in_active_universe": True,
            },
            {
                "ticker": "QQQ",
                "default_purpose": "ETF / Defensive / Hedge",
                "market_cap_bucket": "ETF",
            },
        ]
    )


def _sample_fundamentals() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"ticker": "AMD", "revenue": 100, "free_cash_flow": 20, "fcf_margin": 0.2},
            {"ticker": "HOOD", "revenue": 80, "free_cash_flow": 12, "fcf_margin": 0.15},
            {"ticker": "NVDA", "revenue": 120, "free_cash_flow": 30, "fcf_margin": 0.25, "shares_outstanding": 10},
            {"ticker": "QQQ", "revenue": 1, "free_cash_flow": 1, "fcf_margin": 1, "shares_outstanding": 1},
        ]
    )


def _sample_prices() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"ticker": "AMD", "date": "2026-01-01", "close": 100},
            {"ticker": "NVDA", "date": "2026-01-01", "close": 200},
            {"ticker": "QQQ", "date": "2026-01-01", "close": 500},
        ]
    )


def test_share_count_queue_keeps_only_company_share_count_blockers():
    rows = build_share_count_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=10,
    )

    assert [row.ticker for row in rows] == ["AMD", "HOOD"]
    assert rows[0].dcf_input_status.startswith("share-count-only")
    assert rows[0].scope == "active universe"
    assert "make sec-stage TICKERS=AMD" == rows[0].sec_stage_command
    assert "do not infer share count" in rows[0].stop_rule
    assert "QQQ" not in {row.ticker for row in rows}
    assert "NVDA" not in {row.ticker for row in rows}


def test_share_count_queue_marks_other_missing_dcf_inputs():
    rows = build_share_count_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=10,
        tickers=["HOOD"],
    )

    assert len(rows) == 1
    assert rows[0].ticker == "HOOD"
    assert rows[0].dcf_input_status == "shares plus missing price"
    assert "remaining missing fields: shares_outstanding, price" in rows[0].source_note


def test_share_count_queue_respects_top_n_cap():
    rows = build_share_count_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=1,
    )

    assert [row.ticker for row in rows] == ["AMD"]


def test_share_count_queue_renderer_is_research_only_and_copy_only():
    rows = build_share_count_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=1,
    )

    output = render_share_count_proof_queue(rows)
    lowered = output.lower()

    assert "research-only" in lowered
    assert "does not refresh data, apply imports, or create valuation conclusions" in lowered
    assert "do not infer share count" in lowered
    assert "make sec-stage tickers=amd" in lowered
    assert "review checklist" in lowered
    assert "price target" not in lowered
    assert "undervalued" not in lowered
    assert "recommendation" not in lowered


def test_share_count_queue_from_files_respects_session_preflight_when_sec_unavailable(tmp_path):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    (data_dir / "universe.csv").write_text(
        "ticker,in_active_universe,asset_type\nAMD,true,company\n",
        encoding="utf-8",
    )
    (data_dir / "fundamentals.csv").write_text(
        "ticker,revenue,free_cash_flow,fcf_margin\nAMD,100,20,0.2\n",
        encoding="utf-8",
    )
    (data_dir / "prices.csv").write_text(
        "ticker,date,close\nAMD,2026-01-01,100\n",
        encoding="utf-8",
    )
    (outputs_dir / "session_source_preflight.json").write_text(
        """{
  "sources": {
    "sec": {"status": "unavailable", "reason_code": "network_error"},
    "yfinance_stage": {"status": "unavailable", "reason_code": "probe_failed"},
    "fmp": {"status": "unavailable", "reason_code": "provider_key_missing"},
    "alpha_vantage": {"status": "unavailable", "reason_code": "provider_key_missing"},
    "local_fundamentals": {"status": "available", "fundamentals_fixable_ticker_count": 1}
  }
}
""",
        encoding="utf-8",
    )

    rows = build_share_count_proof_queue_from_files(tmp_path, top_n=1)
    rendered = render_share_count_proof_queue(rows).lower()

    assert rows[0].sec_stage_command == "make focus-fundamentals TICKER=AMD"
    assert "session preflight marks sec unavailable" in rows[0].source_note.lower()
    assert "make sec-stage" not in rendered
    assert "do not retry sec" in rendered


def test_share_count_queue_empty_scope_explains_no_blockers():
    rows = build_share_count_proof_queue(
        universe=_sample_universe(),
        fundamentals=_sample_fundamentals(),
        prices=_sample_prices(),
        top_n=10,
        tickers=["NVDA"],
    )

    assert rows == []
    assert "No shares-outstanding DCF blockers found" in render_share_count_proof_queue(rows)


def test_share_count_queue_deprioritizes_reviewed_non_actionable_tickers(tmp_path):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    (data_dir / "universe.csv").write_text(
        "ticker,in_active_universe,asset_type\nAMD,true,company\nHOOD,true,company\n",
        encoding="utf-8",
    )
    (data_dir / "fundamentals.csv").write_text(
        "ticker,revenue,free_cash_flow,fcf_margin\nAMD,100,20,0.2\nHOOD,80,12,0.15\n",
        encoding="utf-8",
    )
    (data_dir / "prices.csv").write_text(
        "ticker,date,close\nAMD,2026-01-01,100\nHOOD,2026-01-01,50\n",
        encoding="utf-8",
    )
    (data_dir / "reviewed_batch_proofs.csv").write_text(
        "batch_id,lane,tickers,final_outcome,changed_tickers,notes\n"
        "RB-SHARE-AMD,share_count,AMD,still_blocked,none,"
        "\"AMD share-count source path already reviewed; explicit share-count fact missing.\"\n",
        encoding="utf-8",
    )

    rows = build_share_count_proof_queue_from_files(tmp_path, top_n=10)

    assert [row.ticker for row in rows] == ["HOOD", "AMD"]
    amd = next(row for row in rows if row.ticker == "AMD")
    assert "reviewed proof ledger already records" in amd.source_note.lower()
    assert amd.manual_source_path == "no executable source path until new evidence"
    assert amd.validation_sequence == "no validate/preview/apply path until new source-backed rows exist"
    assert amd.proof_after_update == "make project-status"
    rendered = render_share_count_proof_queue(rows)
    assert "Next safest action: make sec-stage TICKERS=HOOD" in rendered


def test_share_count_queue_renderer_pivots_when_every_row_is_reviewed_non_actionable(tmp_path):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    (data_dir / "universe.csv").write_text(
        "ticker,in_active_universe,asset_type\nAMD,true,company\nHOOD,true,company\n",
        encoding="utf-8",
    )
    (data_dir / "fundamentals.csv").write_text(
        "ticker,revenue,free_cash_flow,fcf_margin\nAMD,100,20,0.2\nHOOD,80,12,0.15\n",
        encoding="utf-8",
    )
    (data_dir / "prices.csv").write_text(
        "ticker,date,close\nAMD,2026-01-01,100\nHOOD,2026-01-01,50\n",
        encoding="utf-8",
    )
    (data_dir / "reviewed_batch_proofs.csv").write_text(
        "batch_id,lane,tickers,final_outcome,changed_tickers,notes\n"
        "RB-SHARE-BOTH,share_count,\"AMD,HOOD\",still_blocked,none,"
        "\"AMD and HOOD share-count source paths already reviewed.\"\n",
        encoding="utf-8",
    )

    rows = build_share_count_proof_queue_from_files(tmp_path, top_n=10)
    rendered = render_share_count_proof_queue(rows)

    assert "Next safest action: No unreviewed executable share-count blockers are shown" in rendered
    assert "do not repeat these source paths unless new SEC facts" in rendered
    assert "Do not repeat reviewed share-count source paths" in rendered
    assert "no executable source path until new evidence" in rendered
