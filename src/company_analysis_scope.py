from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

try:
    import pandas as pd
except ImportError:  # pragma: no cover - pandas is present in normal project runs.
    pd = None  # type: ignore[assignment]


COMPANY_DCF_EXCLUDED_ASSET_TYPES = {"etf", "index_proxy", "fund"}
COMPANY_DCF_EXCLUDED_TEXT_PATTERNS = (
    re.compile(
        r"\b(\w*acquisitions?\b.{0,36}\b(co|corp|corporation|company|inc|limited|ltd)|spac|blank check)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bclosed[- ]end fund\b", re.IGNORECASE),
    re.compile(
        r"\b\w*bank\w*|\b(banc\w*|bankshares|bankholding|bank holding)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(financial\b|finance\b|insurance|reinsurance|mortgage)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(real estate investment trust|reit)\b", re.IGNORECASE),
    re.compile(r"\b(realty trust|business development company)\b", re.IGNORECASE),
    re.compile(r"\b(capital corp|capital corporation)\b", re.IGNORECASE),
)


def _metadata_value(metadata: Mapping[str, Any] | Any, column: str) -> str:
    if metadata is None:
        return ""
    if isinstance(metadata, Mapping):
        value = metadata.get(column)
    else:
        value = getattr(metadata, "get", lambda key, default=None: default)(column)
    if value is None:
        return ""
    if pd is not None:
        try:
            if pd.isna(value):
                return ""
        except (TypeError, ValueError):
            pass
    return str(value)


def _numeric_value(values: Mapping[str, Any] | Any, column: str) -> float | None:
    if values is None:
        return None
    if isinstance(values, Mapping):
        value = values.get(column)
    else:
        value = getattr(values, "get", lambda key, default=None: default)(column)
    if value is None:
        return None
    if pd is not None:
        try:
            value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            if pd.notna(value):
                return float(value)
            return None
        except (TypeError, ValueError):
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def excludes_company_dcf(asset_type: object, metadata: Mapping[str, Any] | Any) -> bool:
    normalized_asset_type = str(asset_type or "").strip().lower()
    if normalized_asset_type in COMPANY_DCF_EXCLUDED_ASSET_TYPES:
        return True
    text = " ".join(_metadata_value(metadata, column) for column in ("name", "security_type", "industry"))
    return any(pattern.search(text) for pattern in COMPANY_DCF_EXCLUDED_TEXT_PATTERNS)


def excludes_revenue_margin_dcf(fundamentals: Mapping[str, Any] | Any) -> bool:
    revenue = _numeric_value(fundamentals, "revenue")
    if revenue is None or revenue > 0:
        return False
    fcf_margin = _numeric_value(fundamentals, "fcf_margin")
    free_cash_flow = _numeric_value(fundamentals, "free_cash_flow")
    if free_cash_flow is None:
        free_cash_flow = _numeric_value(fundamentals, "fcf")
    shares = _numeric_value(fundamentals, "shares_outstanding")
    return fcf_margin is None and free_cash_flow is not None and shares is not None


def excludes_company_dcf_for_inputs(
    asset_type: object,
    metadata: Mapping[str, Any] | Any,
    fundamentals: Mapping[str, Any] | Any,
) -> bool:
    return excludes_company_dcf(asset_type, metadata) or excludes_revenue_margin_dcf(fundamentals)
