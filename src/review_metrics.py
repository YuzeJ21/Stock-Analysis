from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import AppConfig
from src.paths import resolve_data_dir, resolve_project_root
from src.providers.local_market_data import LocalCSVMarketDataProvider
from src.providers.market_data import FinancialSnapshot, MarketDataProvider
from src.reviewed_batch import readiness_freshness_status


READY = "ready"
PARTIAL = "partial"
BLOCKED = "blocked"
EXCLUDED = "excluded"
TRADING_DAYS = 252
DEFAULT_RISK_FREE_RATE = 0.0


@dataclass
class ReviewMetric:
    name: str
    state: str
    value: float | None = None
    unit: str = ""
    benchmark: str | None = None
    required_inputs: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    source_context: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewMetricsSnapshot:
    ticker: str
    benchmark: str
    risk_free_rate: float
    price_metrics: list[ReviewMetric]
    fundamentals_metrics: list[ReviewMetric]
    valuation_metrics: list[ReviewMetric]
    peer_metrics: list[ReviewMetric]
    guardrails: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "benchmark": self.benchmark,
            "risk_free_rate": self.risk_free_rate,
            "price_metrics": [metric.to_dict() for metric in self.price_metrics],
            "fundamentals_metrics": [metric.to_dict() for metric in self.fundamentals_metrics],
            "valuation_metrics": [metric.to_dict() for metric in self.valuation_metrics],
            "peer_metrics": [metric.to_dict() for metric in self.peer_metrics],
            "guardrails": list(self.guardrails),
        }


@dataclass
class MetricReadinessRow:
    ticker: str
    benchmark: str
    overall_state: str
    ready_metrics: int
    partial_metrics: int
    blocked_metrics: int
    top_blocker: str
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean_price_history(history: pd.DataFrame) -> pd.Series:
    if history.empty or "date" not in history.columns or "close" not in history.columns:
        return pd.Series(dtype=float)
    frame = history[["date", "close"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.loc[frame["date"].notna() & frame["close"].notna() & frame["close"].gt(0)]
    if frame.empty:
        return pd.Series(dtype=float)
    return frame.sort_values("date").drop_duplicates("date", keep="last").set_index("date")["close"]


def configured_risk_free_rate(root: Path) -> float:
    try:
        config = AppConfig.load(root / "config.yaml")
    except FileNotFoundError:
        return DEFAULT_RISK_FREE_RATE
    return config.get_pct("risk_rules", "annual_risk_free_rate_pct", DEFAULT_RISK_FREE_RATE)


def _returns(prices: pd.Series) -> pd.Series:
    return prices.pct_change().replace([float("inf"), float("-inf")], pd.NA).dropna()


def _state_for_min_rows(count: int, minimum: int) -> str:
    if count >= minimum:
        return READY
    if count > 1:
        return PARTIAL
    return BLOCKED


def _metric_blocked(
    name: str,
    *,
    required_inputs: list[str],
    missing_inputs: list[str],
    benchmark: str | None = None,
    notes: list[str] | None = None,
) -> ReviewMetric:
    return ReviewMetric(
        name=name,
        state=BLOCKED,
        benchmark=benchmark,
        required_inputs=required_inputs,
        missing_inputs=missing_inputs,
        notes=notes or [],
    )


def _metric_partial(
    name: str,
    *,
    required_inputs: list[str],
    missing_inputs: list[str],
    benchmark: str | None = None,
    notes: list[str] | None = None,
    source_context: str = "",
) -> ReviewMetric:
    return ReviewMetric(
        name=name,
        state=PARTIAL,
        benchmark=benchmark,
        required_inputs=required_inputs,
        missing_inputs=missing_inputs,
        source_context=source_context,
        notes=notes or [],
    )


def _total_return(prices: pd.Series) -> float | None:
    if len(prices) < 2:
        return None
    start = float(prices.iloc[0])
    end = float(prices.iloc[-1])
    if start <= 0:
        return None
    return end / start - 1.0


def benchmark_relative_return(stock_prices: pd.Series, benchmark_prices: pd.Series) -> float | None:
    aligned = pd.concat([stock_prices.rename("stock"), benchmark_prices.rename("benchmark")], axis=1, join="inner").dropna()
    if len(aligned) < 2:
        return None
    stock_return = _total_return(aligned["stock"])
    benchmark_return = _total_return(aligned["benchmark"])
    if stock_return is None or benchmark_return is None:
        return None
    return stock_return - benchmark_return


def max_drawdown(prices: pd.Series) -> float | None:
    if len(prices) < 2:
        return None
    running_high = prices.cummax()
    drawdowns = prices / running_high - 1.0
    return float(drawdowns.min())


def rolling_volatility(prices: pd.Series, *, window: int = 21) -> float | None:
    daily_returns = _returns(prices)
    if len(daily_returns) < window:
        return None
    return float(daily_returns.tail(window).std(ddof=0) * (TRADING_DAYS**0.5))


def beta_vs_benchmark(stock_prices: pd.Series, benchmark_prices: pd.Series, *, min_observations: int = 60) -> float | None:
    aligned = pd.concat(
        [_returns(stock_prices).rename("stock"), _returns(benchmark_prices).rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()
    if len(aligned) < min_observations:
        return None
    benchmark_variance = aligned["benchmark"].var(ddof=0)
    if pd.isna(benchmark_variance) or benchmark_variance == 0:
        return None
    covariance = aligned["stock"].cov(aligned["benchmark"], ddof=0)
    return float(covariance / benchmark_variance)


def sharpe_ratio(prices: pd.Series, *, annual_risk_free_rate: float = 0.0, min_observations: int = 60) -> float | None:
    daily_returns = _returns(prices)
    if len(daily_returns) < min_observations:
        return None
    daily_rf = annual_risk_free_rate / TRADING_DAYS
    excess = daily_returns - daily_rf
    std = excess.std(ddof=0)
    if pd.isna(std) or std == 0:
        return None
    return float(excess.mean() / std * (TRADING_DAYS**0.5))


def sortino_ratio(prices: pd.Series, *, annual_risk_free_rate: float = 0.0, min_observations: int = 60) -> float | None:
    daily_returns = _returns(prices)
    if len(daily_returns) < min_observations:
        return None
    daily_rf = annual_risk_free_rate / TRADING_DAYS
    downside = daily_returns.loc[daily_returns < daily_rf] - daily_rf
    downside_std = downside.std(ddof=0)
    if downside.empty or pd.isna(downside_std) or downside_std == 0:
        return None
    excess = daily_returns - daily_rf
    return float(excess.mean() / downside_std * (TRADING_DAYS**0.5))


def _build_price_metrics(
    ticker: str,
    benchmark: str,
    stock_history: pd.DataFrame,
    benchmark_history: pd.DataFrame,
    *,
    annual_risk_free_rate: float,
) -> list[ReviewMetric]:
    stock_prices = _clean_price_history(stock_history)
    benchmark_prices = _clean_price_history(benchmark_history)
    aligned = pd.concat([stock_prices.rename("stock"), benchmark_prices.rename("benchmark")], axis=1, join="inner").dropna()
    required = ["ticker price history", f"{benchmark} price history", "aligned daily closes"]
    source_context = (
        f"{ticker} rows={len(stock_prices)}; {benchmark} rows={len(benchmark_prices)}; "
        f"aligned rows={len(aligned)}; local daily close history"
    )
    if stock_prices.empty:
        return [
            _metric_blocked(
                "benchmark_relative_return",
                required_inputs=required,
                missing_inputs=["ticker price history"],
                benchmark=benchmark,
            ),
            _metric_blocked("max_drawdown", required_inputs=["ticker price history"], missing_inputs=["ticker price history"]),
            _metric_blocked("rolling_volatility", required_inputs=["ticker price history"], missing_inputs=["ticker price history"]),
            _metric_blocked("beta_vs_benchmark", required_inputs=required, missing_inputs=["ticker price history"], benchmark=benchmark),
            _metric_blocked("sharpe_ratio", required_inputs=["ticker price history", "explicit risk-free-rate assumption"], missing_inputs=["ticker price history"]),
            _metric_blocked("sortino_ratio", required_inputs=["ticker price history", "explicit risk-free-rate assumption"], missing_inputs=["ticker price history"]),
        ]
    if benchmark_prices.empty:
        missing = [f"{benchmark} price history"]
    elif len(aligned) < 60:
        missing = [f"at least 60 aligned ticker/{benchmark} price rows"]
    else:
        missing = []

    metrics: list[ReviewMetric] = []
    relative = benchmark_relative_return(stock_prices, benchmark_prices)
    metrics.append(
        ReviewMetric(
            "benchmark_relative_return",
            READY if relative is not None and len(aligned) >= 60 else _state_for_min_rows(len(aligned), 60),
            relative,
            "percent",
            benchmark,
            required,
            [] if relative is not None and len(aligned) >= 60 else missing,
            source_context,
            ["Historical relative return over the aligned local price window; not a forward-looking recommendation."],
        )
    )

    drawdown = max_drawdown(stock_prices)
    metrics.append(
        ReviewMetric(
            "max_drawdown",
            READY if drawdown is not None and len(stock_prices) >= 60 else _state_for_min_rows(len(stock_prices), 60),
            drawdown,
            "percent",
            None,
            ["ticker price history"],
            [] if drawdown is not None and len(stock_prices) >= 60 else ["at least 60 ticker price rows"],
            source_context,
            ["Historical worst peak-to-trough decline in the local window."],
        )
    )

    vol = rolling_volatility(stock_prices)
    metrics.append(
        ReviewMetric(
            "rolling_volatility",
            READY if vol is not None else _state_for_min_rows(len(_returns(stock_prices)), 21),
            vol,
            "percent",
            None,
            ["ticker daily returns", "21 return observations"],
            [] if vol is not None else ["at least 21 daily return observations"],
            source_context,
            ["Annualized 21-trading-day realized volatility from local closes."],
        )
    )

    beta = beta_vs_benchmark(stock_prices, benchmark_prices)
    metrics.append(
        ReviewMetric(
            "beta_vs_benchmark",
            READY if beta is not None else _state_for_min_rows(len(aligned), 60),
            beta,
            "ratio",
            benchmark,
            required,
            [] if beta is not None else missing or [f"at least 60 aligned ticker/{benchmark} return rows"],
            source_context,
            ["Historical beta from aligned local daily returns; review metric only."],
        )
    )

    sharpe = sharpe_ratio(stock_prices, annual_risk_free_rate=annual_risk_free_rate)
    metrics.append(
        ReviewMetric(
            "sharpe_ratio",
            READY if sharpe is not None else _state_for_min_rows(len(_returns(stock_prices)), 60),
            sharpe,
            "ratio",
            None,
            ["ticker daily returns", "explicit risk-free-rate assumption"],
            [] if sharpe is not None else ["at least 60 daily return observations"],
            source_context,
            [f"Historical review metric only; annual risk-free-rate assumption={annual_risk_free_rate:.2%}."],
        )
    )

    sortino = sortino_ratio(stock_prices, annual_risk_free_rate=annual_risk_free_rate)
    metrics.append(
        ReviewMetric(
            "sortino_ratio",
            READY if sortino is not None else _state_for_min_rows(len(_returns(stock_prices)), 60),
            sortino,
            "ratio",
            None,
            ["ticker daily returns", "downside return observations", "explicit risk-free-rate assumption"],
            [] if sortino is not None else ["at least 60 daily return observations with downside observations"],
            source_context,
            [f"Historical downside-risk review metric only; annual risk-free-rate assumption={annual_risk_free_rate:.2%}."],
        )
    )
    return metrics


def _fundamentals_rows(provider: MarketDataProvider, ticker: str) -> pd.DataFrame:
    if hasattr(provider, "_load_fundamentals"):
        frame = provider._load_fundamentals()  # type: ignore[attr-defined]  # local provider hook
        if not frame.empty and "ticker" in frame.columns:
            rows = frame.loc[frame["ticker"].astype(str).str.upper().str.strip() == ticker.upper()].copy()
            return rows
    return pd.DataFrame()


def _safe_float(value: Any) -> float | None:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(numeric) if pd.notna(numeric) else None


def _first_present_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_to_original = {str(column).lower(): str(column) for column in frame.columns}
    for candidate in candidates:
        column = lower_to_original.get(candidate.lower())
        if column is not None and frame[column].notna().any():
            return column
    return None


def _period_ordered_fundamentals(rows: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    period_column = _first_present_column(
        rows,
        ["period", "fiscal_period", "report_date", "as_of_date", "sec_filed_date", "updated_at"],
    )
    if period_column is None:
        return rows.copy(), None
    ordered = rows.copy()
    ordered["_period_label"] = ordered[period_column].astype(str).str.strip()
    ordered = ordered.loc[ordered["_period_label"].ne("") & ordered["_period_label"].str.lower().ne("nan")].copy()
    if ordered.empty:
        return ordered, period_column
    ordered["_period_date"] = pd.to_datetime(ordered["_period_label"], errors="coerce")
    if ordered["_period_date"].notna().any():
        ordered = ordered.sort_values(["_period_date", "_period_label"])
    else:
        ordered = ordered.sort_values("_period_label")
    return ordered, period_column


def _row_value(row: pd.Series, *columns: str) -> float | None:
    lower_to_original = {str(column).lower(): str(column) for column in row.index}
    for column in columns:
        original = lower_to_original.get(column.lower())
        if original is None:
            continue
        value = _safe_float(row.get(original))
        if value is not None:
            return value
    return None


def _row_fcf_margin(row: pd.Series) -> float | None:
    margin = _row_value(row, "fcf_margin")
    if margin is not None:
        return margin
    revenue = _row_value(row, "revenue")
    free_cash_flow = _row_value(row, "free_cash_flow", "fcf")
    if revenue not in (None, 0) and free_cash_flow is not None:
        return free_cash_flow / revenue
    return None


def _fundamentals_trend_from_rows(rows: pd.DataFrame) -> tuple[dict[str, float | str], list[str], list[str]]:
    ordered, period_column = _period_ordered_fundamentals(rows)
    missing: list[str] = []
    notes: list[str] = []
    values: dict[str, float | str] = {}
    if period_column is None or len(ordered) < 2:
        missing.append("at least two dated trusted fundamentals rows for trend")
        return values, missing, notes

    prior = ordered.iloc[-2]
    latest = ordered.iloc[-1]
    prior_label = str(prior.get("_period_label", "prior"))
    latest_label = str(latest.get("_period_label", "latest"))
    values["prior_period"] = prior_label
    values["latest_period"] = latest_label
    notes.append(f"Trend window uses trusted rows for {prior_label} -> {latest_label}.")

    prior_revenue = _row_value(prior, "revenue")
    latest_revenue = _row_value(latest, "revenue")
    if prior_revenue not in (None, 0) and latest_revenue is not None:
        values["revenue_growth"] = latest_revenue / abs(prior_revenue) - 1.0
        notes.append(f"Row-derived revenue growth={values['revenue_growth']:.2%}.")
    else:
        missing.append("revenue values in two trusted periods")

    prior_margin = _row_fcf_margin(prior)
    latest_margin = _row_fcf_margin(latest)
    if latest_margin is not None:
        values["latest_fcf_margin"] = latest_margin
        notes.append(f"Latest FCF margin={latest_margin:.2%}.")
    if prior_margin is not None and latest_margin is not None:
        values["fcf_margin_change"] = latest_margin - prior_margin
        notes.append(f"FCF margin change={values['fcf_margin_change']:.2%}.")
    else:
        missing.append("FCF margin or free cash flow/revenue in two trusted periods")
    return values, missing, notes


def _build_fundamentals_metrics(ticker: str, financials: FinancialSnapshot, provider: MarketDataProvider) -> list[ReviewMetric]:
    rows = _fundamentals_rows(provider, ticker)
    source_context = (
        f"trusted fundamentals rows={len(rows)}; source={financials.source.provider if financials.source else 'not available'}; "
        f"freshness={financials.source.freshness if financials.source else 'not available'}"
    )
    if rows.empty:
        return [
            _metric_blocked(
                "revenue_growth_and_fcf_margin_trend",
                required_inputs=["trusted fundamentals rows", "revenue growth", "FCF margin", "at least two dated rows for trend"],
                missing_inputs=["trusted fundamentals rows"],
            )
        ]

    trend_values, trend_missing, trend_notes = _fundamentals_trend_from_rows(rows)
    row_revenue_growth = trend_values.get("revenue_growth")
    row_fcf_margin = trend_values.get("latest_fcf_margin")
    has_revenue_growth = financials.revenue_growth is not None or isinstance(row_revenue_growth, float)
    has_fcf_margin = financials.fcf_margin is not None or isinstance(row_fcf_margin, float)
    missing = []
    if not has_revenue_growth:
        missing.append("revenue growth")
    if not has_fcf_margin:
        missing.append("FCF margin")
    missing.extend(item for item in trend_missing if item not in missing)
    state = READY if not missing else PARTIAL if has_revenue_growth or has_fcf_margin else BLOCKED
    metric_value = None
    if has_revenue_growth and has_fcf_margin:
        revenue_growth = financials.revenue_growth if financials.revenue_growth is not None else row_revenue_growth
        fcf_margin = financials.fcf_margin if financials.fcf_margin is not None else row_fcf_margin
        metric_value = float((float(revenue_growth) + float(fcf_margin)) / 2.0)
    notes = ["Current trusted row can be reviewed when present; trend stays partial until multiple trusted periods exist."]
    if state == READY:
        notes = ["Multi-period trend is based on period-labeled trusted fundamentals rows."]
    notes.extend(trend_notes)
    return [
        ReviewMetric(
            "revenue_growth_and_fcf_margin_trend",
            state,
            metric_value,
            "percent",
            None,
            ["trusted fundamentals rows", "revenue growth", "FCF margin", "at least two dated rows for trend"],
            missing,
            source_context,
            notes,
        )
    ]


def _build_valuation_metrics(quote_price: float | None, financials: FinancialSnapshot) -> list[ReviewMetric]:
    required = ["trusted fundamentals", "trusted price or market cap", "shares outstanding when deriving market cap"]
    source_context = f"fundamentals source={financials.source.provider if financials.source else 'not available'}"
    if financials.revenue is None and financials.free_cash_flow is None and financials.market_cap is None:
        return [
            _metric_blocked(
                "valuation_multiples",
                required_inputs=required,
                missing_inputs=["trusted fundamentals"],
            )
        ]
    market_cap = financials.market_cap
    if market_cap is None and quote_price is not None and financials.shares_outstanding is not None:
        market_cap = quote_price * financials.shares_outstanding
    missing = []
    if market_cap is None:
        missing.append("market cap or trusted price plus shares outstanding")
    if financials.revenue is None:
        missing.append("revenue")
    if financials.free_cash_flow is None:
        missing.append("free cash flow")
    values: dict[str, float] = {}
    if market_cap is not None and financials.revenue not in (None, 0):
        values["price_to_sales"] = market_cap / financials.revenue
    if market_cap is not None and financials.free_cash_flow not in (None, 0):
        values["price_to_fcf"] = market_cap / financials.free_cash_flow
    if financials.trailing_pe is not None:
        values["trailing_pe"] = financials.trailing_pe
    elif financials.eps not in (None, 0) and quote_price is not None:
        values["trailing_pe"] = quote_price / financials.eps
    state = READY if values and not missing else PARTIAL if values else BLOCKED
    return [
        ReviewMetric(
            "valuation_multiples",
            state,
            None,
            "mixed",
            None,
            required,
            missing,
            source_context,
            [f"{key}={value:.2f}" for key, value in values.items()]
            or ["Multiples stay blocked until trusted fundamentals plus market-cap or price/share-count context exist."],
        )
    ]


def _peer_multiple_values(peer_inputs: list[dict[str, Any]], field: str) -> list[float]:
    values: list[float] = []
    for item in peer_inputs:
        value = _safe_float(item.get(field))
        if value is not None and value > 0:
            values.append(value)
    return values


def _build_peer_metrics(peer_inputs: list[dict[str, Any]], financials: FinancialSnapshot) -> list[ReviewMetric]:
    required = ["mapped peers", "trusted peer valuation inputs", "standalone valuation multiple"]
    if not peer_inputs:
        return [_metric_blocked("peer_valuation_dispersion", required_inputs=required, missing_inputs=["mapped peers"])]

    standalone: dict[str, float] = {}
    if financials.trailing_pe is not None and financials.trailing_pe > 0:
        standalone["trailing_pe"] = financials.trailing_pe
    if financials.forward_pe is not None and financials.forward_pe > 0:
        standalone["forward_pe"] = financials.forward_pe
    peer_sets = {
        "trailing_pe": _peer_multiple_values(peer_inputs, "trailing_pe"),
        "forward_pe": _peer_multiple_values(peer_inputs, "forward_pe"),
    }
    usable = {field: values for field, values in peer_sets.items() if field in standalone and len(values) >= 2}
    if not usable:
        missing = []
        if not standalone:
            missing.append("standalone valuation multiple")
        missing.append("at least two peers with trusted valuation multiples")
        return [
            _metric_partial(
                "peer_valuation_dispersion",
                required_inputs=required,
                missing_inputs=missing,
                source_context=f"mapped peer rows={len(peer_inputs)}",
                notes=["Peer rows exist, but valuation dispersion stays locked until comparable peer multiples exist."],
            )
        ]

    dispersions = []
    notes = []
    for field, values in usable.items():
        median = float(pd.Series(values).median())
        if median:
            dispersion = standalone[field] / median - 1.0
            dispersions.append(dispersion)
            notes.append(f"{field} dispersion vs peer median={dispersion:.2%}")
    return [
        ReviewMetric(
            "peer_valuation_dispersion",
            READY,
            float(sum(dispersions) / len(dispersions)) if dispersions else None,
            "percent",
            None,
            required,
            [],
            f"mapped peer rows={len(peer_inputs)}; usable multiple sets={len(usable)}",
            notes + ["Historical peer valuation context only; not a conclusion list."],
        )
    ]


def build_review_metrics(
    ticker: str,
    provider: MarketDataProvider,
    *,
    benchmark: str = "SPY",
    annual_risk_free_rate: float = 0.0,
) -> ReviewMetricsSnapshot:
    ticker = ticker.upper().strip()
    benchmark = benchmark.upper().strip()
    financials = provider.get_financials(ticker)
    try:
        quote = provider.get_quote(ticker)
        quote_price = quote.price
    except LookupError:
        quote_price = None
    try:
        stock_history = provider.get_price_history(ticker, period="1y", interval="1d")
    except (KeyError, LookupError):
        stock_history = pd.DataFrame(columns=["date", "close"])
    try:
        benchmark_history = provider.get_price_history(benchmark, period="1y", interval="1d")
    except (KeyError, LookupError):
        benchmark_history = pd.DataFrame(columns=["date", "close"])
    peer_inputs = provider.get_peer_valuation_inputs(ticker)
    return ReviewMetricsSnapshot(
        ticker=ticker,
        benchmark=benchmark,
        risk_free_rate=annual_risk_free_rate,
        price_metrics=_build_price_metrics(
            ticker,
            benchmark,
            stock_history,
            benchmark_history,
            annual_risk_free_rate=annual_risk_free_rate,
        ),
        fundamentals_metrics=_build_fundamentals_metrics(ticker, financials, provider),
        valuation_metrics=_build_valuation_metrics(quote_price, financials),
        peer_metrics=_build_peer_metrics(peer_inputs, financials),
        guardrails=[
            "Research-only review metrics; not investment advice.",
            "No broker integration, auto-trading, order routing, or direct buy/sell instructions.",
            "Missing inputs stay blocked, partial, or excluded instead of being inferred.",
        ],
    )


def _all_metrics(snapshot: ReviewMetricsSnapshot) -> list[ReviewMetric]:
    return [
        *snapshot.price_metrics,
        *snapshot.fundamentals_metrics,
        *snapshot.valuation_metrics,
        *snapshot.peer_metrics,
    ]


def _top_metric_blocker(metrics: list[ReviewMetric]) -> str:
    for metric in metrics:
        if metric.state in {BLOCKED, PARTIAL} and metric.missing_inputs:
            return f"{metric.name}: {', '.join(metric.missing_inputs)}"
    return "none"


def _metric_next_action(row: MetricReadinessRow) -> str:
    blocker = row.top_blocker.lower()
    if "benchmark" in blocker or "aligned" in blocker or "price" in blocker:
        return f"make focus-price TICKER={row.ticker}"
    if "fundamentals" in blocker or "revenue" in blocker or "free cash flow" in blocker:
        return f"make focus-fundamentals TICKER={row.ticker}"
    if "peer" in blocker:
        return f"make focus-peers TICKER={row.ticker}"
    return f"make stock-report-md TICKER={row.ticker}"


def summarize_review_metrics(snapshot: ReviewMetricsSnapshot) -> MetricReadinessRow:
    metrics = _all_metrics(snapshot)
    ready = sum(1 for metric in metrics if metric.state == READY)
    partial = sum(1 for metric in metrics if metric.state == PARTIAL)
    blocked = sum(1 for metric in metrics if metric.state == BLOCKED)
    if blocked:
        state = BLOCKED
    elif partial:
        state = PARTIAL
    else:
        state = READY
    row = MetricReadinessRow(
        ticker=snapshot.ticker,
        benchmark=snapshot.benchmark,
        overall_state=state,
        ready_metrics=ready,
        partial_metrics=partial,
        blocked_metrics=blocked,
        top_blocker=_top_metric_blocker(metrics),
        next_action="",
    )
    row.next_action = _metric_next_action(row)
    return row


def _read_ticker_csv(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        frame = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return []
    columns = {column.lower(): column for column in frame.columns}
    ticker_column = columns.get("ticker")
    if ticker_column is None:
        return []
    values = frame[ticker_column].dropna().astype(str).str.upper().str.strip().tolist()
    return [ticker for ticker in dict.fromkeys(values) if ticker]


def discover_metric_summary_tickers(
    root: Path,
    provider: LocalCSVMarketDataProvider,
    *,
    tickers: list[str] | None = None,
    top_n: int = 10,
) -> list[str]:
    if tickers:
        return list(dict.fromkeys(ticker.upper().strip() for ticker in tickers if ticker.strip()))[:top_n]
    data_dir = provider.data_dir
    for filename in ("universe_active.csv", "holdings.csv", "universe.csv"):
        candidates = _read_ticker_csv(data_dir / filename)
        if candidates:
            return candidates[:top_n]
    return provider.list_local_tickers()[:top_n]


def build_metric_readiness_summary(
    root: Path,
    provider: LocalCSVMarketDataProvider,
    *,
    benchmark: str = "SPY",
    annual_risk_free_rate: float = 0.0,
    tickers: list[str] | None = None,
    top_n: int = 10,
) -> tuple[list[MetricReadinessRow], dict[str, str]]:
    selected = discover_metric_summary_tickers(root, provider, tickers=tickers, top_n=top_n)
    freshness = readiness_freshness_status(root)
    rows = [
        summarize_review_metrics(
            build_review_metrics(
                ticker,
                provider,
                benchmark=benchmark,
                annual_risk_free_rate=annual_risk_free_rate,
            )
        )
        for ticker in selected
    ]
    return rows, {
        "status": freshness.status,
        "message": freshness.message,
        "refresh_command": freshness.refresh_command,
    }


def format_review_metrics_text(snapshot: ReviewMetricsSnapshot) -> str:
    lines = [
        f"Review metrics for {snapshot.ticker} vs {snapshot.benchmark}",
        "Research-only; historical review metrics are not recommendations.",
        f"Risk-free-rate assumption: {snapshot.risk_free_rate:.2%}",
    ]
    for section_name, metrics in (
        ("Price / benchmark risk", snapshot.price_metrics),
        ("Fundamentals trend", snapshot.fundamentals_metrics),
        ("Valuation multiples", snapshot.valuation_metrics),
        ("Peer valuation dispersion", snapshot.peer_metrics),
    ):
        lines.append("")
        lines.append(section_name + ":")
        for metric in metrics:
            value = "not available" if metric.value is None else f"{metric.value:.4f}"
            missing = ", ".join(metric.missing_inputs) if metric.missing_inputs else "none"
            benchmark = f" vs {metric.benchmark}" if metric.benchmark else ""
            lines.append(f"- {metric.name}{benchmark}: {metric.state}; value={value}; missing={missing}")
            if metric.source_context:
                lines.append(f"  source: {metric.source_context}")
            if metric.notes:
                lines.append("  notes: " + " ".join(metric.notes))
    return "\n".join(lines)


def format_metric_readiness_summary_text(rows: list[MetricReadinessRow], freshness: dict[str, str]) -> str:
    lines = [
        "Metric readiness summary",
        "Research-only; this is a readiness queue, not a ranking or recommendation.",
        f"Freshness: {freshness.get('status', 'unknown')} - {freshness.get('message', 'No freshness context available.')}",
    ]
    if freshness.get("status") in {"missing", "stale"}:
        lines.append(f"Refresh before relying on final counts: {freshness.get('refresh_command', 'make readiness')}")
    if not rows:
        lines.append("No tickers were available for metric-readiness review.")
        return "\n".join(lines)
    lines.append("")
    lines.append("Ticker | Benchmark | State | Ready | Partial | Blocked | Top blocker | Next check")
    lines.append("--- | --- | --- | ---: | ---: | ---: | --- | ---")
    for row in rows:
        lines.append(
            " | ".join(
                [
                    row.ticker,
                    row.benchmark,
                    row.overall_state,
                    str(row.ready_metrics),
                    str(row.partial_metrics),
                    str(row.blocked_metrics),
                    row.top_blocker,
                    row.next_action,
                ]
            )
        )
    return "\n".join(lines)


def _split_cli_tickers(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Print readiness-gated benchmark, risk, fundamentals, and peer review metrics.")
    parser.add_argument("--ticker")
    parser.add_argument("--tickers", help="Comma-separated tickers for summary mode.")
    parser.add_argument("--benchmark", default="SPY", choices=["SPY", "QQQ"])
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--risk-free-rate", type=float)
    parser.add_argument("--project-root")
    parser.add_argument("--data-dir")
    parser.add_argument("--summary", action="store_true", help="Print a capped multi-ticker metric-readiness summary.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = resolve_project_root(Path(args.project_root) if args.project_root else None)
    data_dir = resolve_data_dir(Path(args.data_dir) if args.data_dir else None, root)
    provider = LocalCSVMarketDataProvider(base_dir=root, data_dir=data_dir)
    risk_free_rate = args.risk_free_rate if args.risk_free_rate is not None else configured_risk_free_rate(root)
    if args.summary or not args.ticker:
        rows, freshness = build_metric_readiness_summary(
            root,
            provider,
            benchmark=args.benchmark,
            annual_risk_free_rate=risk_free_rate,
            tickers=_split_cli_tickers(args.tickers or args.ticker),
            top_n=args.top_n,
        )
        if args.json:
            print(json.dumps({"freshness": freshness, "rows": [row.to_dict() for row in rows]}, indent=2))
        else:
            print(format_metric_readiness_summary_text(rows, freshness))
        return

    snapshot = build_review_metrics(
        args.ticker,
        provider,
        benchmark=args.benchmark,
        annual_risk_free_rate=risk_free_rate,
    )
    if args.json:
        print(json.dumps(snapshot.to_dict(), indent=2))
    else:
        print(format_review_metrics_text(snapshot))


if __name__ == "__main__":
    main()
