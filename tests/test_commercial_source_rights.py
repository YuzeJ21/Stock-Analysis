from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest


MODULE_NAME = "src.commercial_source_rights"
REQUIRED_FIELDS = {
    "source_id",
    "display_name",
    "permitted_use",
    "commercial_use",
    "redistribution",
    "storage_limits",
    "attribution",
    "rate_limits",
    "authentication",
    "expected_freshness",
    "supported_fields",
    "fallback_priority",
}


def _module():
    assert importlib.util.find_spec(MODULE_NAME) is not None, "commercial source-rights registry is not implemented"
    return importlib.import_module(MODULE_NAME)


def _registry():
    module = _module()
    config_path = Path("config/source_rights.yml")
    return module.load_source_rights_registry(config_path)


def test_checked_in_records_are_complete_and_immutable():
    registry = _registry()

    assert set(registry) == {"sec_companyfacts", "yfinance"}
    for record in registry.values():
        assert REQUIRED_FIELDS <= set(record.__dataclass_fields__)
        assert isinstance(record.supported_fields, tuple)
        with pytest.raises(FrozenInstanceError):
            record.commercial_use = "unverified"
    with pytest.raises(TypeError):
        registry["new_source"] = registry["sec_companyfacts"]


def test_rejects_records_missing_required_rights_fields():
    module = _module()

    with pytest.raises(ValueError, match="missing required fields: attribution"):
        module.build_source_rights_registry(
            [
                {
                    "source_id": "incomplete",
                    "display_name": "Incomplete Source",
                    "permitted_use": "research",
                    "commercial_use": "approved",
                    "redistribution": "none",
                    "storage_limits": "none",
                    "rate_limits": "none",
                    "authentication": "none",
                    "expected_freshness": "daily",
                    "supported_fields": ["price"],
                    "fallback_priority": 1,
                }
            ]
        )


def test_unknown_source_is_refused_in_commercial_mode():
    module = _module()

    decision = module.commercial_eligibility(_registry(), "unknown_source")

    assert decision.allowed is False
    assert decision.status == "unknown_source"


def test_unverified_commercial_rights_are_refused():
    module = _module()

    decision = module.commercial_eligibility(_registry(), "yfinance")

    assert decision.allowed is False
    assert decision.status == "commercial_rights_unverified"


def test_explicitly_approved_source_is_accepted():
    module = _module()

    decision = module.commercial_eligibility(_registry(), "sec_companyfacts")

    assert decision.allowed is True
    assert decision.status == "approved"


def test_commercial_source_rights_cli_reports_unverified_yfinance():
    result = subprocess.run(
        [sys.executable, "-m", MODULE_NAME, "--source", "yfinance"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "source_id: yfinance" in result.stdout
    assert "commercial_mode_allowed: false" in result.stdout
    assert "status: commercial_rights_unverified" in result.stdout


def test_make_commercial_source_rights_target_runs_the_cli():
    result = subprocess.run(
        ["make", "--no-print-directory", "commercial-source-rights", "SOURCE=yfinance"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "source_id: yfinance" in result.stdout
    assert "status: commercial_rights_unverified" in result.stdout


def test_yfinance_provider_remains_available_in_default_research_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("COMMERCIAL_RESEARCH_MODE", raising=False)
    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=lambda _ticker: object()))
    from src.providers.yfinance_provider import YFinanceProvider

    assert isinstance(YFinanceProvider(), YFinanceProvider)


def test_yfinance_staging_fails_closed_in_explicit_commercial_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_RESEARCH_MODE", "1")
    ticker_calls: list[str] = []
    monkeypatch.setitem(
        sys.modules,
        "yfinance",
        SimpleNamespace(Ticker=lambda ticker: ticker_calls.append(ticker)),
    )
    from src.providers.yfinance_provider import build_yfinance_fundamentals_rows

    with pytest.raises(RuntimeError, match="commercial rights are not explicitly approved"):
        build_yfinance_fundamentals_rows(["NVDA"])

    assert ticker_calls == []
