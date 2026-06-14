from __future__ import annotations

import pandas as pd

from src.providers.market_data import (
    AnalystEstimateSummary,
    EarningsSummary,
    FinancialSnapshot,
    OptionsChainSummary,
    QuoteSnapshot,
    make_source_metadata,
)
from src.review_metrics import (
    BLOCKED,
    PARTIAL,
    READY,
    MetricReadinessBoardRow,
    beta_vs_benchmark,
    build_metric_readiness_board,
    build_metric_readiness_summary,
    build_review_metrics,
    configured_risk_free_rate,
    format_metric_readiness_board_text,
    format_metric_readiness_summary_text,
    format_review_metrics_text,
    max_drawdown,
    metric_readiness_board_next_safe_action,
    metric_readiness_board_status,
    rolling_volatility,
    sharpe_ratio,
    sortino_ratio,
)


class FakeMetricsProvider:
    def __init__(
        self,
        *,
        prices: dict[str, pd.DataFrame],
        financials: FinancialSnapshot | None = None,
        fundamentals_rows: pd.DataFrame | None = None,
        peer_inputs: list[dict[str, object]] | None = None,
    ) -> None:
        self.prices = {ticker.upper(): frame for ticker, frame in prices.items()}
        self.financials = financials or FinancialSnapshot(
            ticker="AAA",
            revenue=100.0,
            revenue_growth=0.2,
            free_cash_flow=20.0,
            fcf_margin=0.2,
            shares_outstanding=10.0,
            trailing_pe=20.0,
            source=make_source_metadata("local:fundamentals.csv", "test rows", False),
        )
        self.fundamentals_rows = fundamentals_rows if fundamentals_rows is not None else pd.DataFrame()
        self.peer_inputs = peer_inputs or []

    def get_quote(self, ticker: str) -> QuoteSnapshot:
        frame = self.get_price_history(ticker, "1y", "1d")
        if frame.empty:
            raise LookupError(ticker)
        row = frame.iloc[-1]
        return QuoteSnapshot(
            ticker=ticker.upper(),
            price=float(row["close"]),
            previous_close=None,
            open=None,
            day_high=None,
            day_low=None,
            volume=None,
            currency=None,
            market_time=str(row["date"]),
            source=make_source_metadata("local:prices.csv", "test rows", False),
        )

    def get_price_history(self, ticker: str, period: str, interval: str) -> pd.DataFrame:
        return self.prices.get(ticker.upper(), pd.DataFrame(columns=["date", "close"])).copy()

    def get_financials(self, ticker: str) -> FinancialSnapshot:
        return self.financials

    def get_earnings(self, ticker: str) -> EarningsSummary:
        return EarningsSummary(ticker=ticker.upper())

    def get_analyst_estimates(self, ticker: str) -> AnalystEstimateSummary:
        return AnalystEstimateSummary(ticker=ticker.upper())

    def get_options_chain(self, ticker: str, expiry: str) -> OptionsChainSummary:
        return OptionsChainSummary(ticker=ticker.upper(), expiry=expiry, calls_count=0, puts_count=0)

    def get_peer_valuation_inputs(self, ticker: str) -> list[dict[str, object]]:
        return self.peer_inputs

    def _load_fundamentals(self) -> pd.DataFrame:
        return self.fundamentals_rows.copy()


def _price_frame(ticker: str, count: int, *, start: float = 100.0, step: float = 1.0) -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=count, freq="D")
    closes = [start + index * step for index in range(count)]
    return pd.DataFrame({"date": dates, "ticker": ticker, "close": closes})


def test_price_metric_calculations_are_available_with_enough_history():
    stock = _price_frame("AAA", 80, start=100, step=1.0).set_index("date")["close"]
    benchmark = _price_frame("SPY", 80, start=100, step=0.5).set_index("date")["close"]

    assert max_drawdown(stock) == 0.0
    assert rolling_volatility(stock, window=21) is not None
    assert beta_vs_benchmark(stock, benchmark) is not None
    assert sharpe_ratio(stock) is not None
    assert sortino_ratio(stock) is None


def test_review_metrics_block_benchmark_beta_when_aligned_history_is_short():
    provider = FakeMetricsProvider(
        prices={
            "AAA": _price_frame("AAA", 90),
            "SPY": _price_frame("SPY", 25),
        },
        fundamentals_rows=pd.DataFrame([{"ticker": "AAA", "revenue_growth": 0.2, "fcf_margin": 0.2}]),
    )

    snapshot = build_review_metrics("AAA", provider, benchmark="SPY")
    by_name = {metric.name: metric for metric in snapshot.price_metrics}

    assert by_name["max_drawdown"].state == READY
    assert by_name["rolling_volatility"].state == READY
    assert by_name["benchmark_relative_return"].state == PARTIAL
    assert by_name["benchmark_relative_return"].value is None
    assert by_name["beta_vs_benchmark"].state == PARTIAL
    assert by_name["beta_vs_benchmark"].value is None
    assert "at least 60 aligned ticker/SPY price rows" in by_name["beta_vs_benchmark"].missing_inputs


def test_partial_price_metrics_withhold_values_until_row_gate_is_ready():
    provider = FakeMetricsProvider(
        prices={
            "AAA": _price_frame("AAA", 25),
            "SPY": _price_frame("SPY", 25),
        },
        fundamentals_rows=pd.DataFrame([{"ticker": "AAA", "revenue_growth": 0.2, "fcf_margin": 0.2}]),
    )

    snapshot = build_review_metrics("AAA", provider, benchmark="SPY")
    by_name = {metric.name: metric for metric in snapshot.price_metrics}

    assert by_name["benchmark_relative_return"].state == PARTIAL
    assert by_name["benchmark_relative_return"].value is None
    assert by_name["max_drawdown"].state == PARTIAL
    assert by_name["max_drawdown"].value is None
    assert by_name["rolling_volatility"].state == READY
    assert by_name["rolling_volatility"].value is not None


def test_fundamentals_trend_stays_partial_with_only_one_trusted_period():
    provider = FakeMetricsProvider(
        prices={"AAA": _price_frame("AAA", 90), "SPY": _price_frame("SPY", 90)},
        fundamentals_rows=pd.DataFrame([{"ticker": "AAA", "revenue_growth": 0.2, "fcf_margin": 0.2}]),
    )

    snapshot = build_review_metrics("AAA", provider, benchmark="SPY")
    metric = snapshot.fundamentals_metrics[0]

    assert metric.state == PARTIAL
    assert metric.value is None
    assert "at least two dated trusted fundamentals rows for trend" in metric.missing_inputs


def test_fundamentals_trend_becomes_ready_with_two_dated_trusted_periods():
    provider = FakeMetricsProvider(
        prices={"AAA": _price_frame("AAA", 90), "SPY": _price_frame("SPY", 90)},
        financials=FinancialSnapshot(
            ticker="AAA",
            revenue=125.0,
            free_cash_flow=25.0,
            shares_outstanding=10.0,
            source=make_source_metadata("local:fundamentals.csv", "test rows", False),
        ),
        fundamentals_rows=pd.DataFrame(
            [
                {"ticker": "AAA", "period": "2024", "revenue": 100.0, "free_cash_flow": 15.0},
                {"ticker": "AAA", "period": "2025", "revenue": 125.0, "free_cash_flow": 25.0},
            ]
        ),
    )

    snapshot = build_review_metrics("AAA", provider, benchmark="SPY")
    metric = snapshot.fundamentals_metrics[0]

    assert metric.state == READY
    assert metric.missing_inputs == []
    assert metric.value == 0.225
    assert any("2024 -> 2025" in note for note in metric.notes)
    assert any("Row-derived revenue growth=25.00%" in note for note in metric.notes)
    assert any("FCF margin change=5.00%" in note for note in metric.notes)


def test_valuation_multiples_require_trusted_market_context():
    financials = FinancialSnapshot(
        ticker="AAA",
        revenue=100.0,
        free_cash_flow=20.0,
        source=make_source_metadata("local:fundamentals.csv", "test rows", False),
    )
    provider = FakeMetricsProvider(
        prices={},
        financials=financials,
        fundamentals_rows=pd.DataFrame([{"ticker": "AAA", "revenue": 100.0, "free_cash_flow": 20.0}]),
    )

    snapshot = build_review_metrics("AAA", provider, benchmark="SPY")
    metric = snapshot.valuation_metrics[0]

    assert metric.state == BLOCKED
    assert "market cap or trusted price plus shares outstanding" in metric.missing_inputs


def test_peer_dispersion_requires_peer_valuation_inputs():
    provider = FakeMetricsProvider(
        prices={"AAA": _price_frame("AAA", 90), "SPY": _price_frame("SPY", 90)},
        fundamentals_rows=pd.DataFrame([{"ticker": "AAA", "revenue_growth": 0.2, "fcf_margin": 0.2}]),
        peer_inputs=[{"ticker": "BBB", "trailing_pe": 15.0}, {"ticker": "CCC", "trailing_pe": 25.0}],
    )

    snapshot = build_review_metrics("AAA", provider, benchmark="SPY")
    metric = snapshot.peer_metrics[0]

    assert metric.state == READY
    assert metric.value == 0.0


def test_etf_proxy_excludes_operating_company_metrics(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "universe_master.csv").write_text(
        "ticker,asset_type\nQQQ,etf\n",
        encoding="utf-8",
    )
    provider = FakeMetricsProvider(
        prices={"QQQ": _price_frame("QQQ", 90), "SPY": _price_frame("SPY", 90)},
        fundamentals_rows=pd.DataFrame(
            [
                {"ticker": "QQQ", "period": "2024", "revenue": 100.0, "free_cash_flow": 20.0},
                {"ticker": "QQQ", "period": "2025", "revenue": 110.0, "free_cash_flow": 22.0},
            ]
        ),
        peer_inputs=[{"ticker": "SPY", "trailing_pe": 20.0}, {"ticker": "SMH", "trailing_pe": 25.0}],
    )
    provider.data_dir = data_dir

    snapshot = build_review_metrics("QQQ", provider, benchmark="SPY")
    row = build_metric_readiness_summary(
        tmp_path,
        provider,  # type: ignore[arg-type]
        benchmark="SPY",
        tickers=["QQQ"],
        top_n=1,
    )[0][0]

    assert any(metric.state == READY for metric in snapshot.price_metrics)
    assert snapshot.fundamentals_metrics[0].state == "excluded"
    assert snapshot.valuation_metrics[0].state == "excluded"
    assert snapshot.peer_metrics[0].state == "excluded"
    assert snapshot.fundamentals_metrics[0].missing_inputs == []
    assert "operating-company fundamentals" in snapshot.fundamentals_metrics[0].required_inputs
    assert any("excluded rather than treated as failed data coverage" in note for note in snapshot.peer_metrics[0].notes)
    assert row.excluded_metrics == 3


def test_cli_text_preserves_research_only_review_wording():
    provider = FakeMetricsProvider(
        prices={"AAA": _price_frame("AAA", 90), "SPY": _price_frame("SPY", 90)},
        fundamentals_rows=pd.DataFrame([{"ticker": "AAA", "revenue_growth": 0.2, "fcf_margin": 0.2}]),
    )

    rendered = format_review_metrics_text(build_review_metrics("AAA", provider, benchmark="SPY")).lower()

    assert "research-only" in rendered
    assert "historical review metrics are not recommendations" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_metric_readiness_summary_uses_selected_tickers_and_freshness_context(tmp_path):
    data_dir = tmp_path / "data"
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True)
    (data_dir / "prices.csv").write_text("date,ticker,close\n2025-01-01,AAA,100\n", encoding="utf-8")
    (data_dir / "fundamentals.csv").write_text("ticker,revenue\nAAA,100\n", encoding="utf-8")
    (data_dir / "peers.csv").write_text("ticker,peer_ticker\n", encoding="utf-8")
    (data_dir / "earnings.csv").write_text("ticker\n", encoding="utf-8")
    (data_dir / "analyst_estimates.csv").write_text("ticker\n", encoding="utf-8")
    (reports_dir / "ticker_readiness_report.csv").write_text("ticker\nAAA\n", encoding="utf-8")
    (reports_dir / "feature_readiness_summary.csv").write_text("feature\nreview_metrics\n", encoding="utf-8")
    provider = FakeMetricsProvider(
        prices={"AAA": _price_frame("AAA", 90), "SPY": _price_frame("SPY", 25)},
        fundamentals_rows=pd.DataFrame([{"ticker": "AAA", "revenue_growth": 0.2, "fcf_margin": 0.2}]),
    )
    provider.data_dir = data_dir

    rows, freshness = build_metric_readiness_summary(
        tmp_path,
        provider,  # type: ignore[arg-type]
        benchmark="SPY",
        tickers=["AAA"],
        top_n=10,
    )
    rendered = format_metric_readiness_summary_text(rows, freshness).lower()

    assert freshness["status"] in {"current", "stale"}
    assert rows[0].ticker == "AAA"
    assert rows[0].partial_metrics >= 1
    assert rows[0].excluded_metrics == 0
    assert "metric readiness summary" in rendered
    assert "freshness:" in rendered
    assert "aaa | spy" in rendered
    assert "excluded" in rendered
    assert "ranking or recommendation" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_metric_readiness_board_combines_spy_and_qqq_without_recommendations(tmp_path):
    data_dir = tmp_path / "data"
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True)
    (data_dir / "prices.csv").write_text("date,ticker,close\n2025-01-01,AAA,100\n", encoding="utf-8")
    (data_dir / "fundamentals.csv").write_text("ticker,revenue\nAAA,100\n", encoding="utf-8")
    (data_dir / "peers.csv").write_text("ticker,peer_ticker\n", encoding="utf-8")
    (data_dir / "earnings.csv").write_text("ticker\n", encoding="utf-8")
    (data_dir / "analyst_estimates.csv").write_text("ticker\n", encoding="utf-8")
    (reports_dir / "ticker_readiness_report.csv").write_text("ticker\nAAA\n", encoding="utf-8")
    (reports_dir / "feature_readiness_summary.csv").write_text("feature\nreview_metrics\n", encoding="utf-8")
    provider = FakeMetricsProvider(
        prices={
            "AAA": _price_frame("AAA", 90),
            "SPY": _price_frame("SPY", 25),
            "QQQ": _price_frame("QQQ", 25),
        },
        fundamentals_rows=pd.DataFrame([{"ticker": "AAA", "revenue_growth": 0.2, "fcf_margin": 0.2}]),
    )
    provider.data_dir = data_dir

    rows = build_metric_readiness_board(
        tmp_path,
        provider,  # type: ignore[arg-type]
        benchmarks=["SPY", "QQQ"],
        tickers=["AAA"],
        top_n=10,
    )
    rendered = format_metric_readiness_board_text(rows).lower()

    assert [row.benchmark for row in rows] == ["SPY", "QQQ"]
    assert all(row.blocker_family == "benchmark / risk" for row in rows)
    assert "metric readiness board" in rendered
    assert "spy/qqq review-metric readiness" in rendered
    assert "partial and blocked metric rows withhold numeric values" in rendered
    assert "board status:" in rendered
    assert "next safe action:" in rendered
    assert "blocker families: benchmark / risk: 2" in rendered
    assert "aaa | spy" in rendered
    assert "aaa | qqq" in rendered
    assert "ranking or recommendation" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_metric_readiness_board_blocks_stale_rows_before_current_proof():
    rows = [
        MetricReadinessBoardRow(
            ticker="AAA",
            benchmark="SPY",
            overall_state="partial",
            ready_metrics=5,
            partial_metrics=4,
            blocked_metrics=0,
            excluded_metrics=0,
            top_blocker="benchmark_relative_return: at least 60 aligned ticker/SPY price rows",
            blocker_family="benchmark / risk",
            next_action="make focus-price TICKER=AAA",
            freshness="stale",
            freshness_message="source CSV changed after report",
            refresh_command="make readiness",
        )
    ]

    rendered = format_metric_readiness_board_text(rows).lower()

    assert metric_readiness_board_status(rows) == "blocked_by_freshness"
    assert metric_readiness_board_next_safe_action(rows) == "make readiness"
    assert "board status: blocked_by_freshness" in rendered
    assert "next safe action: make readiness" in rendered
    assert "blocked preflight" in rendered
    assert "current coverage proof" in rendered
    assert "ranking or recommendation" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_metric_readiness_board_ready_state_uses_first_safe_next_check():
    rows = [
        MetricReadinessBoardRow(
            ticker="AAA",
            benchmark="QQQ",
            overall_state="partial",
            ready_metrics=5,
            partial_metrics=4,
            blocked_metrics=0,
            excluded_metrics=0,
            top_blocker="benchmark_relative_return: at least 60 aligned ticker/QQQ price rows",
            blocker_family="benchmark / risk",
            next_action="make focus-price TICKER=AAA",
            freshness="current",
            freshness_message="ready",
            refresh_command="make readiness",
        )
    ]

    rendered = format_metric_readiness_board_text(rows).lower()

    assert metric_readiness_board_status(rows) == "ready_for_review"
    assert metric_readiness_board_next_safe_action(rows) == "make focus-price TICKER=AAA"
    assert "board status: ready_for_review" in rendered
    assert "next safe action: make focus-price ticker=aaa" in rendered
    assert "blocked preflight" not in rendered


def test_metric_readiness_board_no_rows_stays_copy_only_and_non_recommending():
    rendered = format_metric_readiness_board_text([]).lower()

    assert metric_readiness_board_status([]) == "blocked_no_rows"
    assert metric_readiness_board_next_safe_action([]) == "make metric-readiness-board TOP_N=10 BENCHMARKS=SPY,QQQ"
    assert "board status: blocked_no_rows" in rendered
    assert "next safe action: make metric-readiness-board top_n=10 benchmarks=spy,qqq" in rendered
    assert "no tickers were available" in rendered
    assert "recommendation" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_metric_readiness_board_csv_export_writes_reviewed_shape(tmp_path):
    from src.review_metrics import write_metric_readiness_board_csv

    data_dir = tmp_path / "data"
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True)
    (data_dir / "prices.csv").write_text("date,ticker,close\n2025-01-01,AAA,100\n", encoding="utf-8")
    (data_dir / "fundamentals.csv").write_text("ticker,revenue\nAAA,100\n", encoding="utf-8")
    (data_dir / "peers.csv").write_text("ticker,peer_ticker\n", encoding="utf-8")
    (data_dir / "earnings.csv").write_text("ticker\n", encoding="utf-8")
    (data_dir / "analyst_estimates.csv").write_text("ticker\n", encoding="utf-8")
    (reports_dir / "ticker_readiness_report.csv").write_text("ticker\nAAA\n", encoding="utf-8")
    (reports_dir / "feature_readiness_summary.csv").write_text("feature\nreview_metrics\n", encoding="utf-8")
    provider = FakeMetricsProvider(
        prices={"AAA": _price_frame("AAA", 90), "SPY": _price_frame("SPY", 25)},
        fundamentals_rows=pd.DataFrame([{"ticker": "AAA", "revenue_growth": 0.2, "fcf_margin": 0.2}]),
    )
    provider.data_dir = data_dir
    rows = build_metric_readiness_board(
        tmp_path,
        provider,  # type: ignore[arg-type]
        benchmarks=["SPY"],
        tickers=["AAA"],
        top_n=10,
    )
    output = tmp_path / "outputs" / "metric_readiness_board.csv"

    write_metric_readiness_board_csv(rows, output)
    exported = pd.read_csv(output)

    assert output.exists()
    assert exported.loc[0, "ticker"] == "AAA"
    assert exported.loc[0, "benchmark"] == "SPY"
    assert exported.loc[0, "blocker_family"] == "benchmark / risk"
    assert "top_blocker" in exported.columns
    assert "next_action" in exported.columns


def test_configured_risk_free_rate_reads_project_config(tmp_path):
    (tmp_path / "config.yaml").write_text(
        "risk_rules:\n  annual_risk_free_rate_pct: 4\n",
        encoding="utf-8",
    )

    assert configured_risk_free_rate(tmp_path) == 0.04
