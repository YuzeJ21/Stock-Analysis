from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.peer_evidence_quality import assess_peer_evidence, is_valuation_anchor_eligible
from src.providers.local_data_catalog import LocalDataCatalog
from src.providers.market_data import (
    AnalystEstimateSummary,
    EarningsSummary,
    FinancialSnapshot,
    MarketDataProvider,
    OptionsChainSummary,
    QuoteSnapshot,
    make_source_metadata,
)

ALLOWED_CANDIDATE_STATES = {"candidate", "fallback_context", "research_only"}


def _peer_evidence_value(value: object) -> object:
    """Keep peer evidence JSON-safe without changing its meaning."""

    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except (AttributeError, ValueError):
            pass
    return value


class LocalCSVMarketDataProvider(MarketDataProvider):
    """Research provider backed by local project CSVs.

    This keeps the new stock-report workflow aligned with the existing
    deterministic CSV-first pipeline.
    """

    def __init__(self, base_dir: Path | None = None, data_dir: Path | None = None, outputs_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.data_dir = data_dir or (self.base_dir / "data")
        self.outputs_dir = outputs_dir or (self.base_dir / "outputs")
        self.catalog = LocalDataCatalog(self.base_dir, data_dir=self.data_dir, outputs_dir=self.outputs_dir)
        self.prices_path = self.data_dir / "prices.csv"
        self.fundamentals_path = self.data_dir / "fundamentals.csv"
        self._prepared_prices: pd.DataFrame | None = None
        self._price_rows_by_ticker: dict[str, pd.DataFrame] = {}
        self._dataset_rows_by_ticker: dict[str, dict[str, pd.Series]] = {}
        self._peer_rows_by_ticker: dict[str, tuple[pd.DataFrame, list[str]]] = {}
        self._peer_candidate_rows_by_ticker: dict[str, tuple[pd.DataFrame, list[str]]] = {}

    def _source(self, file_path: Path, freshness: str, notes: list[str]) -> object:
        retrieved_at = (
            pd.Timestamp(file_path.stat().st_mtime, unit="s", tz="UTC").isoformat()
            if file_path.exists()
            else pd.Timestamp.now(tz="UTC").isoformat()
        )
        return make_source_metadata(
            provider=f"local:{file_path.name}",
            freshness=freshness,
            official=False,
            notes=notes,
            retrieved_at=retrieved_at,
        )

    def _unavailable_source(self, provider_label: str, notes: list[str]) -> object:
        return make_source_metadata(
            provider=provider_label,
            freshness="not available in local CSVs",
            official=False,
            notes=notes,
        )

    def _row_source(
        self,
        dataset_name: str,
        row: pd.Series,
        default_notes: list[str],
    ):
        metadata = self.catalog.dataset_metadata(dataset_name)
        notes = list(default_notes)
        if "source" in row and pd.notna(row["source"]):
            notes.append(f"Dataset row source: {row['source']}")
        freshness = metadata.source["freshness"]
        if "as_of_date" in row and pd.notna(row["as_of_date"]):
            freshness = f"dataset row as of {pd.Timestamp(row['as_of_date']).date().isoformat()}"
        return make_source_metadata(
            provider=metadata.source["provider"],
            freshness=freshness,
            official=False,
            notes=notes,
            retrieved_at=metadata.source["retrieved_at"],
        )

    def _load_prices(self) -> pd.DataFrame:
        return self._prepared_prices_frame().copy()

    def _prepared_prices_frame(self) -> pd.DataFrame:
        if self._prepared_prices is not None:
            return self._prepared_prices
        prices = self.catalog.load_dataframe("prices")
        if prices is None:
            raise FileNotFoundError(f"Local prices file is missing: {self.prices_path}")
        prices = prices.copy()
        required_columns = {"date", "ticker"}
        missing_columns = sorted(required_columns - set(prices.columns))
        if missing_columns:
            raise ValueError(f"Local prices file is missing required columns: {', '.join(missing_columns)}")
        if "adj_close" in prices.columns and "close" not in prices.columns:
            prices["close"] = prices["adj_close"]
        if "close" not in prices.columns:
            raise ValueError("Local prices file must include either `close` or `adj_close`.")
        for optional_column in ("open", "high", "low"):
            if optional_column not in prices.columns:
                prices[optional_column] = pd.NA
        for column in ("open", "high", "low", "close", "adj_close", "volume"):
            if column in prices.columns:
                prices[column] = pd.to_numeric(prices[column], errors="coerce")
        prices = prices.loc[prices["date"].notna()].copy()
        if "ticker" in prices.columns:
            prices["ticker"] = prices["ticker"].astype(str).str.upper().str.strip()
        self._prepared_prices = prices
        return prices

    def _price_rows_for_ticker(self, ticker: str) -> pd.DataFrame:
        ticker = ticker.upper().strip()
        if ticker not in self._price_rows_by_ticker:
            prices = self._prepared_prices_frame()
            self._price_rows_by_ticker[ticker] = prices.loc[prices["ticker"] == ticker].sort_values("date").copy()
        return self._price_rows_by_ticker[ticker].copy()

    def _load_fundamentals(self) -> pd.DataFrame:
        return self._dataset_frame("fundamentals")

    def _load_optional_dataset(self, dataset_name: str) -> pd.DataFrame:
        return self._dataset_frame(dataset_name)

    def _dataset_frame(self, dataset_name: str) -> pd.DataFrame:
        frame = self.catalog.load_dataframe(dataset_name)
        return frame.copy() if frame is not None else pd.DataFrame()

    def _select_ticker_row(self, frame: pd.DataFrame, ticker: str) -> pd.Series:
        if frame.empty or "ticker" not in frame.columns:
            return pd.Series(dtype=object)
        ticker = ticker.upper().strip()
        tickers = frame["ticker"].astype(str).str.upper().str.strip()
        matches = frame.loc[tickers == ticker]
        return matches.iloc[-1] if not matches.empty else pd.Series(dtype=object)

    def _select_ticker_row_from_dataset(self, dataset_name: str, ticker: str) -> pd.Series:
        ticker = ticker.upper().strip()
        if not ticker:
            return pd.Series(dtype=object)
        if dataset_name not in self._dataset_rows_by_ticker:
            frame = self._dataset_frame(dataset_name)
            lookup: dict[str, pd.Series] = {}
            if not frame.empty and "ticker" in frame.columns:
                tickers = frame["ticker"].astype(str).str.upper().str.strip()
                for index, ticker_key in tickers.items():
                    if ticker_key:
                        lookup[ticker_key] = frame.loc[index]
            self._dataset_rows_by_ticker[dataset_name] = lookup
        row = self._dataset_rows_by_ticker[dataset_name].get(ticker)
        return row.copy() if row is not None else pd.Series(dtype=object)

    def _float_value(self, row: pd.Series, *columns: str) -> float | None:
        for column in columns:
            if column in row and pd.notna(row[column]):
                return float(row[column])
        return None

    def _string_value(self, row: pd.Series, *columns: str) -> str | None:
        for column in columns:
            if column in row and pd.notna(row[column]):
                value = row[column]
                if isinstance(value, pd.Timestamp):
                    return value.date().isoformat() if value.time().isoformat() == "00:00:00" else value.isoformat()
                return str(value)
        return None

    def list_local_tickers(self) -> list[str]:
        return self.catalog.list_tickers(
            ["prices", "fundamentals", "earnings", "analyst_estimates", "peers", "peer_candidates", "universe", "holdings"]
        )

    def get_local_data_validation(self) -> list[dict[str, Any]]:
        return [entry.to_dict() for entry in self.catalog.discover()]

    def get_ticker_dataset_coverage(self, ticker: str) -> list[dict[str, Any]]:
        coverage = self.catalog.describe_ticker(
            ticker,
            [
                "prices",
                "fundamentals",
                "earnings",
                "analyst_estimates",
                "peers",
                "peer_candidates",
                "purpose_classification",
                "momentum_leaders",
                "portfolio_review",
                "undervalued_candidates",
                "final_watchlist",
            ],
        )
        return [row.to_dict() for row in coverage]

    def _mapping_rows_for_ticker(
        self,
        dataset_name: str,
        ticker: str,
        cache: dict[str, tuple[pd.DataFrame, list[str]]],
        *,
        warning_label: str,
    ) -> tuple[pd.DataFrame, list[str]]:
        ticker = ticker.upper().strip()
        if ticker in cache:
            selected, warnings = cache[ticker]
            return selected.copy(), list(warnings)
        peers = self._load_optional_dataset(dataset_name)
        if peers.empty or "ticker" not in peers.columns or "peer_ticker" not in peers.columns:
            return pd.DataFrame(), []
        tickers = peers["ticker"].astype(str).str.upper().str.strip()
        selected = peers.loc[tickers == ticker].copy()
        if selected.empty:
            cache[ticker] = (selected, [])
            return selected, []

        warnings: list[str] = []
        selected["peer_ticker"] = selected["peer_ticker"].astype(str).str.upper().str.strip()
        self_rows = selected.loc[selected["peer_ticker"] == ticker]
        if not self_rows.empty:
            warnings.append(f"Ignored {len(self_rows)} self-{warning_label} row(s) for {ticker}.")
            selected = selected.loc[selected["peer_ticker"] != ticker].copy()

        duplicate_mask = selected.duplicated(subset=["ticker", "peer_ticker"], keep="last")
        duplicate_count = int(duplicate_mask.sum())
        if duplicate_count:
            warnings.append(f"Ignored {duplicate_count} duplicate {warning_label} row(s) for {ticker}.")
            selected = selected.loc[~duplicate_mask].copy()

        selected = selected.sort_values(["ticker", "peer_ticker"]).reset_index(drop=True)
        cache[ticker] = (selected, warnings)
        return selected.copy(), list(warnings)

    def _peer_rows_for_ticker(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        return self._mapping_rows_for_ticker(
            "peers",
            ticker,
            self._peer_rows_by_ticker,
            warning_label="peer mapping row",
        )

    def _peer_candidate_rows_for_ticker(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        rows, warnings = self._mapping_rows_for_ticker(
            "peer_candidates",
            ticker,
            self._peer_candidate_rows_by_ticker,
            warning_label="peer-candidate row",
        )
        if rows.empty:
            return rows, warnings
        candidate_states = (
            rows.get("candidate_state", pd.Series(dtype=object))
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )
        rows = rows.assign(candidate_state=candidate_states)
        return rows, warnings

    def get_peer_tickers(self, ticker: str) -> list[str]:
        peer_rows, _warnings = self._peer_rows_for_ticker(ticker)
        if peer_rows.empty or "peer_ticker" not in peer_rows.columns:
            return []
        return sorted(peer_rows["peer_ticker"].dropna().astype(str).str.upper().str.strip().unique().tolist())

    def get_peer_summary(self, ticker: str) -> dict[str, Any]:
        ticker = ticker.upper()
        peer_rows, warnings = self._peer_rows_for_ticker(ticker)
        candidate_rows, candidate_warnings = self._peer_candidate_rows_for_ticker(ticker)
        metadata = self.catalog.dataset_metadata("peers")
        candidate_metadata = self.catalog.dataset_metadata("peer_candidates")
        peer_tickers = peer_rows["peer_ticker"].dropna().astype(str).str.upper().str.strip().tolist() if not peer_rows.empty else []
        peer_groups = sorted({str(value) for value in peer_rows.get("peer_group", pd.Series(dtype=object)).dropna().astype(str)} )
        candidate_tickers = (
            candidate_rows["peer_ticker"].dropna().astype(str).str.upper().str.strip().tolist()
            if not candidate_rows.empty
            else []
        )
        candidate_groups = sorted(
            {
                str(value)
                for value in candidate_rows.get("peer_group", pd.Series(dtype=object)).dropna().astype(str)
            }
        )
        candidate_states = sorted(
            {
                str(value).strip().lower()
                for value in candidate_rows.get("candidate_state", pd.Series(dtype=object)).dropna().astype(str)
                if str(value).strip()
            }
        )
        valid_candidate_states = sorted(state for state in candidate_states if state in ALLOWED_CANDIDATE_STATES)
        invalid_candidate_states = sorted(state for state in candidate_states if state not in ALLOWED_CANDIDATE_STATES)
        trusted_relationships: list[dict[str, Any]] = []
        for _, relationship in peer_rows.iterrows():
            peer_ticker = str(relationship.get("peer_ticker") or "").strip().upper()
            peer_result = self.get_earnings(peer_ticker).to_dict() if peer_ticker else {}
            evidence_quality = assess_peer_evidence(relationship.to_dict())
            trusted_relationships.append(
                {
                    key: _peer_evidence_value(relationship.get(key))
                    for key in (
                        "ticker",
                        "peer_ticker",
                        "peer_group",
                        "sector",
                        "industry",
                        "peer_role",
                        "relationship_rationale",
                        "comparability_basis",
                        "valuation_anchor_eligible",
                        "source",
                        "as_of_date",
                    )
                    if key in relationship.index and pd.notna(relationship.get(key))
                }
                | {
                    "peer_result": peer_result,
                    "peer_role": evidence_quality.peer_role,
                    "relationship_evidence_state": evidence_quality.relationship_state,
                    "role_state": evidence_quality.role_state,
                    "comparability_state": evidence_quality.comparability_state,
                    "valuation_anchor_state": evidence_quality.valuation_anchor_state,
                    "evidence_quality_blockers": list(evidence_quality.blockers),
                }
            )
        candidate_relationships = [
            {
                key: _peer_evidence_value(relationship.get(key))
                for key in (
                    "ticker",
                    "peer_ticker",
                    "candidate_state",
                    "peer_group",
                    "sector",
                    "industry",
                    "relationship_rationale",
                    "source",
                    "as_of_date",
                )
                if key in relationship.index and pd.notna(relationship.get(key))
            }
            for _, relationship in candidate_rows.iterrows()
        ]
        peers_with_fundamentals: list[str] = []
        peers_with_quote_or_market_cap: list[str] = []
        for peer_ticker in peer_tickers:
            financials = self.get_financials(peer_ticker)
            has_fundamentals = any(
                value is not None
                for value in (
                    financials.revenue,
                    financials.eps,
                    financials.free_cash_flow,
                    financials.ebitda,
                    financials.trailing_pe,
                    financials.market_cap,
                )
            )
            if has_fundamentals:
                peers_with_fundamentals.append(peer_ticker)
            try:
                quote = self.get_quote(peer_ticker)
            except LookupError:
                quote = None
            if quote is not None or financials.market_cap is not None:
                peers_with_quote_or_market_cap.append(peer_ticker)

        return {
            "peer_dataset_present": metadata.validation_status != "missing_file",
            "peer_dataset_status": metadata.validation_status,
            "peer_group": peer_groups[0] if len(peer_groups) == 1 else None,
            "peer_groups": peer_groups,
            "peer_tickers": peer_tickers,
            "peer_count": len(peer_tickers),
            "peers_with_fundamentals": peers_with_fundamentals,
            "peers_with_quote_or_market_cap": peers_with_quote_or_market_cap,
            "peer_fundamentals_available": len(peers_with_fundamentals),
            "peer_market_context_available": len(peers_with_quote_or_market_cap),
            "warnings": warnings,
            "source_metadata": metadata.source,
            "candidate_dataset_present": candidate_metadata.validation_status != "missing_file",
            "candidate_dataset_status": candidate_metadata.validation_status,
            "candidate_peer_group": candidate_groups[0] if len(candidate_groups) == 1 else None,
            "candidate_peer_groups": candidate_groups,
            "candidate_peer_tickers": candidate_tickers,
            "candidate_peer_count": len(candidate_tickers),
            "candidate_states": valid_candidate_states,
            "invalid_candidate_states": invalid_candidate_states,
            "candidate_mapping_status": (
                "candidate_available"
                if len(candidate_tickers) >= 2 and valid_candidate_states
                else "candidate_unlabeled"
                if len(candidate_tickers) >= 1 and not valid_candidate_states
                else "candidate_insufficient"
                if len(candidate_tickers) == 1
                else "candidate_missing"
            ),
            "candidate_warnings": candidate_warnings,
            "candidate_source_metadata": candidate_metadata.source,
            "trusted_relationships": trusted_relationships,
            "candidate_relationships": candidate_relationships,
        }

    def get_peer_valuation_inputs(self, ticker: str) -> list[dict[str, Any]]:
        peer_inputs: list[dict[str, Any]] = []
        peer_rows, warnings = self._peer_rows_for_ticker(ticker)
        if peer_rows.empty or "peer_ticker" not in peer_rows.columns:
            return peer_inputs
        for peer_ticker in peer_rows["peer_ticker"].dropna().astype(str).str.upper().str.strip().tolist():
            peer_row = peer_rows.loc[peer_rows["peer_ticker"] == peer_ticker].iloc[-1]
            if not is_valuation_anchor_eligible(peer_row.to_dict()):
                continue
            financials = self.get_financials(peer_ticker)
            try:
                quote = self.get_quote(peer_ticker)
            except LookupError:
                quote = None
            peer_inputs.append(
                {
                    "ticker": peer_ticker,
                    "current_price": quote.price if quote is not None else None,
                    "revenue": financials.revenue,
                    "eps": financials.eps,
                    "free_cash_flow": financials.free_cash_flow,
                    "ebitda": financials.ebitda,
                    "shares_outstanding": financials.shares_outstanding,
                    "cash": financials.cash,
                    "debt": financials.debt,
                    "market_cap": financials.market_cap,
                    "trailing_pe": financials.trailing_pe,
                    "forward_pe": financials.forward_pe,
                    "price_to_book": financials.price_to_book,
                    "peer_group": self._string_value(peer_row, "peer_group"),
                    "sector": self._string_value(peer_row, "sector"),
                    "industry": self._string_value(peer_row, "industry"),
                    "peer_role": self._string_value(peer_row, "peer_role"),
                    "relationship_rationale": self._string_value(peer_row, "relationship_rationale"),
                    "comparability_basis": self._string_value(peer_row, "comparability_basis"),
                    "valuation_anchor_eligible": self._string_value(peer_row, "valuation_anchor_eligible"),
                    "mapping_source": self._string_value(peer_row, "source"),
                    "mapping_as_of_date": self._string_value(peer_row, "as_of_date"),
                    "source_metadata": [
                        financials.source.to_dict() if financials.source is not None else None,
                        quote.source.to_dict() if quote is not None else None,
                    ],
                }
            )
        if warnings and peer_inputs:
            peer_inputs[0]["peer_mapping_warnings"] = warnings
        return peer_inputs

    def get_screener_context(self, ticker: str) -> dict[str, dict[str, Any]]:
        ticker = ticker.upper()
        context: dict[str, dict[str, Any]] = {}
        for dataset_name in (
            "purpose_classification",
            "momentum_leaders",
            "portfolio_review",
            "undervalued_candidates",
            "final_watchlist",
        ):
            frame = self.catalog.load_dataframe(dataset_name)
            if frame is None or "ticker" not in frame.columns:
                continue
            matches = frame.loc[frame["ticker"] == ticker]
            if matches.empty:
                continue
            row = matches.iloc[-1]
            context[dataset_name] = {
                column: (None if pd.isna(value) else value.item() if hasattr(value, "item") else value)
                for column, value in row.to_dict().items()
            }
        return context

    def get_quote(self, ticker: str) -> QuoteSnapshot:
        ticker = ticker.upper()
        frame = self._price_rows_for_ticker(ticker)
        if frame.empty:
            raise LookupError(f"No local price rows were found for {ticker}.")

        latest = frame.iloc[-1]
        previous = frame.iloc[-2] if len(frame) > 1 else None
        source = self._source(
            self.prices_path,
            freshness=f"daily CSV through {latest['date'].date().isoformat()}",
            notes=["Saved local research data."],
        )
        return QuoteSnapshot(
            ticker=ticker,
            price=float(latest["close"]) if pd.notna(latest["close"]) else None,
            previous_close=float(previous["close"]) if previous is not None and pd.notna(previous["close"]) else None,
            open=float(latest["open"]) if pd.notna(latest["open"]) else None,
            day_high=float(latest["high"]) if pd.notna(latest["high"]) else None,
            day_low=float(latest["low"]) if pd.notna(latest["low"]) else None,
            volume=float(latest["volume"]) if pd.notna(latest["volume"]) else None,
            currency=self._string_value(latest, "currency"),
            market_time=latest["date"].isoformat() if pd.notna(latest["date"]) else None,
            source=source,
        )

    def get_price_history(self, ticker: str, period: str, interval: str) -> pd.DataFrame:
        if interval != "1d":
            raise ValueError("Local CSV market-data provider only supports 1d interval.")

        ticker = ticker.upper()
        frame = self._price_rows_for_ticker(ticker)
        if frame.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

        period_map = {
            "1mo": 31,
            "3mo": 93,
            "1y": 366,
        }
        if period in period_map:
            cutoff = frame["date"].max() - pd.Timedelta(days=period_map[period])
            frame = frame.loc[frame["date"] >= cutoff].copy()

        return frame[[column for column in ["date", "open", "high", "low", "close", "volume"] if column in frame.columns]].copy()

    def get_financials(self, ticker: str) -> FinancialSnapshot:
        ticker = ticker.upper()
        row = self._select_ticker_row_from_dataset("fundamentals", ticker)
        metadata = self.catalog.dataset_metadata("fundamentals")
        source = self._row_source("fundamentals", row, ["Local fundamentals data."]) if not row.empty else (
            self._unavailable_source(
                "local:fundamentals.csv",
                ["No local fundamentals row was found for this ticker."],
            )
            if metadata.validation_status != "missing_file"
            else self._unavailable_source(
                "local:fundamentals.csv",
                ["No trusted fundamentals CSV has been added yet."],
            )
        )
        return FinancialSnapshot(
            ticker=ticker,
            revenue=self._float_value(row, "revenue"),
            revenue_growth=self._float_value(row, "revenue_growth"),
            eps=self._float_value(row, "eps"),
            gross_margin=self._float_value(row, "gross_margin"),
            operating_margin=self._float_value(row, "operating_margin"),
            profit_margin=self._float_value(row, "profit_margin"),
            free_cash_flow=self._float_value(row, "free_cash_flow", "fcf"),
            fcf_margin=self._float_value(row, "fcf_margin"),
            ebitda=self._float_value(row, "ebitda"),
            market_cap=self._float_value(row, "market_cap"),
            enterprise_value=self._float_value(row, "enterprise_value"),
            trailing_pe=self._float_value(row, "pe_ratio", "trailing_pe"),
            forward_pe=self._float_value(row, "forward_pe"),
            price_to_book=self._float_value(row, "price_to_book"),
            shares_outstanding=self._float_value(row, "shares_outstanding"),
            cash=self._float_value(row, "cash"),
            debt=self._float_value(row, "debt", "total_debt"),
            net_debt=self._float_value(row, "net_debt"),
            debt_to_equity=self._float_value(row, "debt_to_equity"),
            currency=self._string_value(row, "currency"),
            as_of_date=self._string_value(row, "as_of_date", "date"),
            reporting_period=self._string_value(row, "period", "fiscal_period"),
            source=source,
        )

    def get_earnings(self, ticker: str) -> EarningsSummary:
        ticker = ticker.upper()
        row = self._select_ticker_row_from_dataset("earnings", ticker)
        metadata = self.catalog.dataset_metadata("earnings")
        if metadata.validation_status == "missing_file":
            return EarningsSummary(
                ticker=ticker,
                notes=["No trusted earnings CSV has been added yet."],
                source=self._unavailable_source(
                    "local:earnings.csv",
                    ["Earnings fields stay locked until trusted rows are imported."],
                ),
            )
        return EarningsSummary(
            ticker=ticker,
            next_earnings_date=self._string_value(row, "next_earnings_date", "earnings_date"),
            last_earnings_date=self._string_value(row, "last_earnings_date", "report_date"),
            fiscal_period=self._string_value(row, "fiscal_period"),
            eps_estimate=self._float_value(row, "eps_estimate"),
            eps_actual=self._float_value(row, "eps_actual"),
            revenue_estimate=self._float_value(row, "revenue_estimate"),
            revenue_actual=self._float_value(row, "revenue_actual"),
            surprise_pct=self._float_value(row, "surprise_pct"),
            notes=[] if not row.empty else [f"No local earnings row was found for {ticker}."],
            source=self._row_source("earnings", row, ["Local earnings data."]) if not row.empty else make_source_metadata(**metadata.source),
        )

    def get_analyst_estimates(self, ticker: str) -> AnalystEstimateSummary:
        ticker = ticker.upper()
        row = self._select_ticker_row_from_dataset("analyst_estimates", ticker)
        metadata = self.catalog.dataset_metadata("analyst_estimates")
        if metadata.validation_status == "missing_file":
            return AnalystEstimateSummary(
                ticker=ticker,
                notes=["No trusted analyst-estimate CSV has been added yet."],
                source=self._unavailable_source(
                    "local:analyst_estimates.csv",
                    ["Analyst-estimate fields stay locked until trusted rows are imported."],
                ),
            )
        return AnalystEstimateSummary(
            ticker=ticker,
            current_quarter_eps=self._float_value(row, "current_quarter_eps", "eps_estimate"),
            next_quarter_eps=self._float_value(row, "next_quarter_eps"),
            current_year_eps=self._float_value(row, "current_year_eps"),
            next_year_eps=self._float_value(row, "next_year_eps"),
            current_quarter_revenue=self._float_value(row, "current_quarter_revenue", "revenue_estimate"),
            next_quarter_revenue=self._float_value(row, "next_quarter_revenue"),
            current_year_revenue=self._float_value(row, "current_year_revenue"),
            next_year_revenue=self._float_value(row, "next_year_revenue"),
            recommendation=self._string_value(row, "recommendation", "rating_consensus"),
            target_mean_price=self._float_value(row, "target_mean_price", "price_target_mean"),
            target_high_price=self._float_value(row, "target_high_price", "price_target_high"),
            target_low_price=self._float_value(row, "target_low_price", "price_target_low"),
            revision_trend=self._string_value(row, "revision_trend"),
            notes=[] if not row.empty else [f"No local analyst-estimate row was found for {ticker}."],
            source=self._row_source("analyst_estimates", row, ["Local analyst estimate data."]) if not row.empty else make_source_metadata(**metadata.source),
        )

    def get_options_chain(self, ticker: str, expiry: str) -> OptionsChainSummary:
        return OptionsChainSummary(
            ticker=ticker.upper(),
            expiry=expiry,
            calls_count=0,
            puts_count=0,
            notes=["Options-chain data is not part of this research-only workflow."],
            source=self._unavailable_source(
                "local:options_chain.csv",
                ["Options-chain analysis is intentionally unavailable in the local research workflow."],
            ),
        )
