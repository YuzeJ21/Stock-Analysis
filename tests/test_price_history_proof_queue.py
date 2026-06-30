from pathlib import Path

import pandas as pd

from src.data_onboarding import build_onboarding_payload
from src.price_history_proof_queue import (
    build_price_history_proof_queue_from_files,
    build_price_history_proof_queue_from_payload,
    render_price_history_proof_queue,
)


def _write_fixture(root: Path) -> None:
    data_dir = root / "data"
    outputs_dir = root / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    (data_dir / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-01,NVDA,100,1000\n"
        "2026-01-02,NVDA,101,1000\n"
        "2026-01-03,NVDA,102,1000\n"
        "2026-01-04,NVDA,103,1000\n"
        "2026-01-05,NVDA,104,1000\n"
        "2026-01-06,NVDA,105,1000\n"
        "2026-01-07,NVDA,106,1000\n"
        "2026-01-08,NVDA,107,1000\n"
        "2026-01-09,NVDA,108,1000\n"
        "2026-01-10,NVDA,109,1000\n"
        "2026-01-11,NVDA,110,1000\n"
        "2026-01-12,NVDA,111,1000\n"
        "2026-01-13,NVDA,112,1000\n"
        "2026-01-14,NVDA,113,1000\n"
        "2026-01-15,NVDA,114,1000\n"
        "2026-01-16,NVDA,115,1000\n"
        "2026-01-17,NVDA,116,1000\n"
        "2026-01-18,NVDA,117,1000\n"
        "2026-01-19,NVDA,118,1000\n"
        "2026-01-20,NVDA,119,1000\n"
        "2026-01-21,NVDA,120,1000\n"
        "2026-01-22,NVDA,121,1000\n"
        "2026-01-01,AMD,50,1000\n",
        encoding="utf-8",
    )
    (data_dir / "fundamentals.csv").write_text(
        "ticker,revenue,fcf_margin,shares_outstanding,eps,free_cash_flow,source,as_of_date\n"
        "NVDA,1000,0.2,10,2,200,fixture,2026-01-01\n",
        encoding="utf-8",
    )
    (data_dir / "peers.csv").write_text(
        "ticker,peer_ticker,peer_group,source,as_of_date\n"
        "NVDA,AMD,semis,fixture,2026-01-01\n",
        encoding="utf-8",
    )
    (data_dir / "earnings.csv").write_text("ticker,next_earnings_date\nNVDA,2026-02-01\n", encoding="utf-8")
    (data_dir / "universe.csv").write_text(
        "ticker,theme,sectoretf,defaultpurpose,marketcapbucket,notes\n"
        "NVDA,AI,SMH,Momentum Leader,Large,fixture\n"
        "AMD,AI,SMH,Momentum Leader,Large,fixture\n",
        encoding="utf-8",
    )
    (data_dir / "holdings.csv").write_text("ticker,primarypurpose\nNVDA,Momentum Leader\n", encoding="utf-8")
    (outputs_dir / "final_watchlist.csv").write_text("Ticker,FinalState\nNVDA,Watch\n", encoding="utf-8")
    (outputs_dir / "momentum_leaders.csv").write_text("Ticker,SetupStatus\nNVDA,Watch\n", encoding="utf-8")


def test_price_history_proof_queue_surfaces_short_history_as_partial(tmp_path: Path):
    _write_fixture(tmp_path)

    rows = build_price_history_proof_queue_from_files(tmp_path, top_n=10)

    amd = next(row for row in rows if row.ticker == "AMD")
    nvda = next(row for row in rows if row.ticker == "NVDA")
    assert amd.state == "partial"
    assert amd.current_history_rows == 1
    assert amd.next_goal == "Unlock Monthly Picks"
    assert amd.rows_needed == 20
    assert amd.next_safe_command == "make focus-price TICKER=AMD"
    assert "DRY_RUN=1" in amd.dry_run_batch_command
    assert "make price-validate -> make price-preview" in amd.validate_preview_apply_gate
    assert "do not infer missing dates or prices" in amd.stop_rule
    assert nvda.next_goal == "Unlock Track Record"


def test_price_history_proof_queue_respects_tickers_and_top_n(tmp_path: Path):
    _write_fixture(tmp_path)

    rows = build_price_history_proof_queue_from_files(tmp_path, top_n=1, tickers=["NVDA", "AMD"])

    assert [row.ticker for row in rows] == ["AMD"]


def test_price_history_proof_queue_renderer_is_research_only_and_read_only(tmp_path: Path):
    _write_fixture(tmp_path)
    payload = build_onboarding_payload(tmp_path)
    rows = build_price_history_proof_queue_from_payload(payload, top_n=2)

    rendered = render_price_history_proof_queue(rows, payload)
    lowered = rendered.lower()

    assert "read-only" in lowered
    assert "research-only" in lowered
    assert "does not refresh prices, apply imports, or write canonical data" in lowered
    assert "do not fabricate missing dates, prices, volume, or adjusted close rows" in lowered
    assert "price coverage can be complete while momentum" in lowered
    assert "make focus-price ticker=amd" in lowered
    assert "price rows are already present for every ticker" in lowered
    assert "not missing-price refresh" in lowered
    assert "review checklist" in lowered
    assert "price target" not in lowered
    assert "undervalued" not in lowered


def test_price_history_proof_queue_empty_scope_explains_no_blockers(tmp_path: Path):
    data_dir = tmp_path / "data"
    outputs_dir = tmp_path / "outputs"
    data_dir.mkdir()
    outputs_dir.mkdir()
    prices = pd.DataFrame(
        [{"date": f"2026-01-{day:02d}", "ticker": "NVDA", "adj_close": 100 + day, "volume": 1000} for day in range(1, 253)]
    )
    prices.to_csv(data_dir / "prices.csv", index=False)
    (data_dir / "fundamentals.csv").write_text("ticker\nNVDA\n", encoding="utf-8")
    (data_dir / "peers.csv").write_text("ticker,peer_ticker\nNVDA,AMD\n", encoding="utf-8")
    (data_dir / "earnings.csv").write_text("ticker,next_earnings_date\nNVDA,2026-02-01\n", encoding="utf-8")
    (data_dir / "universe.csv").write_text("ticker,defaultpurpose\nNVDA,Momentum Leader\n", encoding="utf-8")
    (data_dir / "holdings.csv").write_text("ticker,primarypurpose\nNVDA,Momentum Leader\n", encoding="utf-8")

    payload = build_onboarding_payload(tmp_path)
    rows = build_price_history_proof_queue_from_payload(payload, top_n=10)

    assert rows == []
    assert "No short price-history blockers found" in render_price_history_proof_queue(rows, payload)


def test_price_history_proof_queue_deprioritizes_reviewed_non_actionable_tickers(tmp_path: Path):
    _write_fixture(tmp_path)
    proofs = tmp_path / "data" / "reviewed_batch_proofs.csv"
    proofs.write_text(
        "batch_id,lane,tickers,final_outcome,changed_tickers,notes\n"
        "RB-PRICE-AMD,prices,AMD,still_blocked,none,"
        "\"AMD public provider path already tried; do not retry without a new verified OHLCV source.\"\n",
        encoding="utf-8",
    )

    rows = build_price_history_proof_queue_from_files(tmp_path, top_n=10)

    assert [row.ticker for row in rows[:2]] == ["NVDA", "AMD"]
    amd = next(row for row in rows if row.ticker == "AMD")
    assert "reviewed proof ledger already records" in amd.source_note.lower()
    rendered = render_price_history_proof_queue(rows, build_onboarding_payload(tmp_path))
    assert "Next safest action: make focus-price TICKER=NVDA." in rendered


def test_price_history_proof_queue_renderer_pivots_when_every_row_is_reviewed_non_actionable(tmp_path: Path):
    _write_fixture(tmp_path)
    proofs = tmp_path / "data" / "reviewed_batch_proofs.csv"
    proofs.write_text(
        "batch_id,lane,tickers,final_outcome,changed_tickers,notes\n"
        "RB-PRICE-BOTH,price_coverage,\"AMD,NVDA\",still_blocked,none,"
        "\"AMD and NVDA public provider paths already tried; do not retry without new verified OHLCV source.\"\n",
        encoding="utf-8",
    )

    rows = build_price_history_proof_queue_from_files(tmp_path, top_n=10)
    rendered = render_price_history_proof_queue(rows, build_onboarding_payload(tmp_path))

    assert "Next safest action: No unreviewed executable price-history blockers are shown" in rendered
    assert "do not repeat these source paths unless new provider data" in rendered
    assert "not missing-price refresh" in rendered.lower()
