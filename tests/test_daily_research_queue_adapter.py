from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.commercial_source_rights import build_source_rights_registry
from src.config import AppConfig
from src.daily_research_queue_adapter import (
    build_daily_research_queue,
    build_daily_research_queue_from_files,
)
from src.historical_valuation_regime import ValuationObservation


AS_OF = date(2026, 7, 31)


def tree_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def config() -> AppConfig:
    return AppConfig(
        raw={
            "moving_averages": {"ema": [10, 21], "sma": [50, 200]},
            "returns": {
                "lookbacks": {
                    "one_month": 21,
                    "three_month": 63,
                    "six_month": 126,
                    "twelve_month": 252,
                }
            },
            "volume_rules": {"avg_volume_window": 20},
            "value_rules": {"max_debt_to_equity_for_quality_value": 2.0},
        }
    )


def rights_registry():
    return build_source_rights_registry(
        [
            {
                "source_id": "permitted_fixture",
                "display_name": "Permitted Fixture Source",
                "permitted_use": "test_only",
                "commercial_use": "approved",
                "redistribution": "test_only",
                "storage_limits": "test_only",
                "attribution": "test fixture",
                "rate_limits": "not applicable",
                "authentication": "not applicable",
                "expected_freshness": "daily",
                "supported_fields": [
                    "prices",
                    "valuation_history",
                    "free_cash_flow",
                    "revenue_growth",
                    "debt_to_equity",
                ],
                "fallback_priority": 1,
            }
        ]
    )


def price_rows(
    *,
    ticker: str = "ALFA",
    source: str = "permitted_fixture",
    include_lineage: bool = True,
    final_date: date = date(2026, 7, 30),
) -> pd.DataFrame:
    start = final_date - timedelta(days=219)
    rows: list[dict[str, object]] = []
    for offset in range(220):
        observed = start + timedelta(days=offset)
        close = 100.0 + offset
        row = {
            "date": observed.isoformat(),
            "ticker": ticker,
            "open": close - 1,
            "high": close + 1,
            "low": close - 2,
            "close": close,
            "adj_close": close,
            "volume": 1_000_000,
        }
        if include_lineage:
            row.update(
                {
                    "source": source,
                    "source_ref": f"fixture:{ticker}:{observed.isoformat()}",
                    "retrieved_at": f"{observed.isoformat()}T22:00:00+00:00",
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def prices(**kwargs) -> pd.DataFrame:
    stock = price_rows(**kwargs)
    spy = price_rows(ticker="SPY")
    spy_close = pd.Series(
        [100.0 + offset * 0.2 for offset in range(len(spy))],
        index=spy.index,
    )
    spy["open"] = spy_close - 0.2
    spy["high"] = spy_close + 0.2
    spy["low"] = spy_close - 0.4
    spy["close"] = spy_close
    spy["adj_close"] = spy_close
    return pd.concat([stock, spy], ignore_index=True)


def valuation_rows(ticker: str = "ALFA") -> tuple[ValuationObservation, ...]:
    rows = []
    for index, multiple in enumerate((12, 13, 14, 15, 16, 17, 18, 10)):
        observed = date(2025, 12, 31) + timedelta(days=index * 30)
        rows.append(
            ValuationObservation(
                ticker=ticker,
                metric="price_to_fcf_per_share",
                numerator=float(multiple * 10),
                denominator=10.0,
                numerator_as_of=f"{observed.isoformat()}T20:00:00+00:00",
                denominator_period_end="2025-12-31",
                denominator_available_at="2025-12-31T12:00:00+00:00",
                definition_id="fixture-definition-v1",
                source="permitted_fixture",
                source_ref=f"fixture:valuation:{index}",
                retrieved_at=f"{observed.isoformat()}T21:00:00+00:00",
            )
        )
    return tuple(rows)


def readiness() -> pd.DataFrame:
    return pd.DataFrame(
        [{"ticker": "ALFA", "name": "Alpha Company", "momentum_ready": True}]
    )


def fundamentals(**changes) -> pd.DataFrame:
    row = {
        "ticker": "ALFA",
        "free_cash_flow": 500_000_000.0,
        "revenue_growth": 0.10,
        "debt_to_equity": 0.5,
        "source": "permitted_fixture",
        "source_ref": "fixture:fundamentals:ALFA",
        "retrieved_at": "2026-07-30T22:00:00+00:00",
    }
    row.update(changes)
    return pd.DataFrame([row])


def test_adapter_builds_eligible_row_only_from_complete_permitted_evidence():
    status = build_daily_research_queue(
        readiness=readiness(),
        prices=prices(),
        fundamentals=fundamentals(),
        universe=pd.DataFrame(),
        theme_map=pd.DataFrame(),
        valuation_observations=valuation_rows(),
        config=config(),
        rights_registry=rights_registry(),
        as_of=AS_OF,
    )

    assert status.considered_count == 1
    assert [item.ticker for item in status.result.eligible] == ["ALFA"]
    assert status.result.withheld == ()


def test_adapter_ignores_rows_not_marked_momentum_ready():
    not_ready = readiness().assign(momentum_ready=False)

    status = build_daily_research_queue(
        readiness=not_ready,
        prices=prices(),
        fundamentals=fundamentals(),
        universe=pd.DataFrame(),
        theme_map=pd.DataFrame(),
        valuation_observations=valuation_rows(),
        config=config(),
        rights_registry=rights_registry(),
        as_of=AS_OF,
    )

    assert status.considered_count == 0
    assert status.result.eligible == ()
    assert status.result.withheld == ()


def test_adapter_withholds_missing_price_lineage():
    status = build_daily_research_queue(
        readiness=readiness(),
        prices=prices(include_lineage=False),
        fundamentals=fundamentals(),
        universe=pd.DataFrame(),
        theme_map=pd.DataFrame(),
        valuation_observations=valuation_rows(),
        config=config(),
        rights_registry=rights_registry(),
        as_of=AS_OF,
    )

    assert "price_provenance_ineligible" in status.result.withheld[0].blockers
    assert "price_rights_ineligible" in status.result.withheld[0].blockers


def test_adapter_withholds_stale_price_or_spy_observation():
    stale_prices = prices(final_date=date(2026, 7, 1))

    status = build_daily_research_queue(
        readiness=readiness(),
        prices=stale_prices,
        fundamentals=fundamentals(),
        universe=pd.DataFrame(),
        theme_map=pd.DataFrame(),
        valuation_observations=valuation_rows(),
        config=config(),
        rights_registry=rights_registry(),
        as_of=AS_OF,
    )

    assert "current_market_evidence_ineligible" in status.result.withheld[0].blockers


def test_adapter_withholds_absent_valuation_history_and_unsupported_fundamental_scope():
    restricted_registry = build_source_rights_registry(
        [
            {
                "source_id": "permitted_fixture",
                "display_name": "Incomplete Fixture Source",
                "permitted_use": "test_only",
                "commercial_use": "approved",
                "redistribution": "test_only",
                "storage_limits": "test_only",
                "attribution": "test fixture",
                "rate_limits": "not applicable",
                "authentication": "not applicable",
                "expected_freshness": "daily",
                "supported_fields": ["prices"],
                "fallback_priority": 1,
            }
        ]
    )

    status = build_daily_research_queue(
        readiness=readiness(),
        prices=prices(),
        fundamentals=fundamentals(),
        universe=pd.DataFrame(),
        theme_map=pd.DataFrame(),
        valuation_observations=(),
        config=config(),
        rights_registry=restricted_registry,
        as_of=AS_OF,
    )

    blockers = status.result.withheld[0].blockers
    assert "valuation_not_ready" in blockers
    assert "valuation_commercial_evidence_ineligible" in blockers
    assert "fundamentals_field_scope_ineligible" in blockers


def test_file_adapter_is_read_only_and_fails_closed_without_valuation_ledger(tmp_path):
    data_dir = tmp_path / "data"
    config_dir = tmp_path / "config"
    data_dir.mkdir()
    (data_dir / "reports").mkdir()
    config_dir.mkdir()
    readiness().to_csv(data_dir / "reports" / "ticker_readiness_report.csv", index=False)
    prices().to_csv(data_dir / "prices.csv", index=False)
    fundamentals().to_csv(data_dir / "fundamentals.csv", index=False)
    pd.DataFrame(columns=["ticker", "theme", "sector_etf"]).to_csv(
        data_dir / "universe.csv", index=False
    )
    pd.DataFrame(columns=["theme", "etf"]).to_csv(data_dir / "theme_map.csv", index=False)
    (tmp_path / "config.yaml").write_text(
        """
moving_averages:
  ema: [10, 21]
  sma: [50, 200]
returns:
  lookbacks:
    one_month: 21
    three_month: 63
    six_month: 126
    twelve_month: 252
volume_rules:
  avg_volume_window: 20
value_rules:
  max_debt_to_equity_for_quality_value: 2.0
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (config_dir / "source_rights.yml").write_text(
        """
sources:
  - source_id: permitted_fixture
    display_name: Permitted Fixture Source
    permitted_use: test_only
    commercial_use: approved
    redistribution: test_only
    storage_limits: test_only
    attribution: test fixture
    rate_limits: not applicable
    authentication: not applicable
    expected_freshness: daily
    supported_fields: [prices, valuation_history, free_cash_flow, revenue_growth, debt_to_equity]
    fallback_priority: 1
""".strip()
        + "\n",
        encoding="utf-8",
    )
    before = tree_snapshot(tmp_path)

    status = build_daily_research_queue_from_files(
        project_root=tmp_path,
        data_dir=data_dir,
        as_of=AS_OF,
        rights_registry_path=config_dir / "source_rights.yml",
    )

    assert status.result.eligible == ()
    assert "valuation_not_ready" in status.result.withheld[0].blockers
    assert tree_snapshot(tmp_path) == before
