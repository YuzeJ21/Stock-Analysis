"""Responsive source-labelled annual and daily-price inspection views."""

import re
from html import escape
from urllib.parse import quote

from src.company_sec_online_preview import _iso_date, _finite_direct_number, _utc_timestamp
from src.online_history_contract import validated_annual_history

STYLE = """<style>
.online-history,.online-price-inspection{margin:16px 0;padding:16px;border:1px solid #d9e0dc;border-radius:8px;min-width:0;overflow-wrap:anywhere;box-sizing:border-box}
.online-history-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,20rem),1fr));gap:12px}
.online-history-grid article{padding:12px;border:1px solid #d9e0dc;border-radius:8px;background:#fff;min-width:0;box-sizing:border-box}
.online-history h4{margin:0 0 8px}.online-history dl{margin:8px 0}.online-history dl div{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 16px}.online-history dd{margin:0;font-weight:650}
.online-history small,.online-price-inspection small{color:#52615c}.online-research-chart{width:100%;min-width:0;margin:12px 0}.online-research-chart svg{display:block;width:100%;height:auto;max-height:220px}.online-research-chart figcaption{display:flex;flex-wrap:wrap;justify-content:space-between;gap:6px;font-size:.8rem}
</style>""".replace("\n", "")


def _amount(value):
    if not _finite_direct_number(value): return "Withheld"
    return format(int(value), ",") if float(value).is_integer() else format(value, ",.2f")


def _line(points, title):
    if not points or len(points) > 800: return ""
    valid = [(day, value) for day, value in points if value is not None]
    if not valid or any(_iso_date(day) is None or not _finite_direct_number(value) for day, value in valid): return ""
    low, high = min(v for _, v in valid), max(v for _, v in valid)
    start, end = min(_iso_date(d).toordinal() for d, _ in valid), max(_iso_date(d).toordinal() for d, _ in valid)
    segments = []; current = []
    for day, value in points:
        if value is None:
            if current: segments.append(current)
            current = []; continue
        x = 12 + (_iso_date(day).toordinal() - start) / max(end - start, 1) * 616
        y = 160 - (value - low) / (high - low if high != low else 1) * 140
        current.append((x, y))
    if current: segments.append(current)
    drawing = "".join(
        '<polyline fill="none" stroke="#0f766e" stroke-width="2.5" points="' + " ".join(f"{x:.2f},{y:.2f}" for x, y in segment) + '"/>'
        + "".join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2" fill="#0f766e"/>' for x, y in segment)
        for segment in segments
    )
    return (
        '<figure class="online-research-chart">'
        f'<svg viewBox="0 0 640 180" role="img" aria-label="{escape(title, quote=True)}"><title>{escape(title)}</title>'
        '<path d="M12 166 H628" stroke="#d9e0dc"/>' + drawing + '</svg>'
        f'<figcaption><span>{escape(valid[0][0])} → {escape(valid[-1][0])}</span>'
        f'<span>Reported range: {_amount(low)} to {_amount(high)}</span></figcaption></figure>'
    )


def annual_history_html(view):
    if view.get("status") != "inspection_only": return ""
    history = validated_annual_history(view)
    if history is None:
        return '<section class="online-history"><h3>Historical annual financials</h3><p>Compatible historical evidence is unavailable. Refresh the SEC action to inspect the current source; no prior value is inferred.</p></section>'
    points = []; cards = []; comparisons = history["comparisons"]
    for index, row in enumerate(history["periods"]):
        if index and comparisons[index-1]["status"] != "comparable": points.append((row["period_end"], None))
        points.append((row["period_end"], row["revenue"]))
        fields = {f["field"]: f["value"] for f in row["fields"]}
        continuing = any(f.get("concept") == "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations" for f in row["fields"])
        cash_label = "Operating cash flow · continuing operations" if continuing else "Operating cash flow"
        values = "".join(f'<div><dt>{label}</dt><dd>{_amount(fields.get(name))}</dd></div>' for name, label in (
            ("revenue", "Revenue"), ("operating_income", "Operating income"),
            ("cash_from_operations", cash_label), ("capital_expenditures", "Capital spending"),
        ))
        context = (
            f'Filed {escape(row["filed"])} · accession {escape(row["accession"])} · {escape(row["form"])}'
            if row["status"] == "available" else 'Withheld · ' + escape(str(row["reason"]).replace('_', ' '))
        )
        definitions = "; ".join(f'{f["field"]}: {f.get("taxonomy", "")}:{f.get("concept", "")}' for f in row["fields"] if f["field"] in {"revenue", "operating_income", "cash_from_operations", "capital_expenditures"})
        cards.append(
            f'<article><h4>Year ended {escape(row["period_end"])}</h4><small>{escape(row["period_start"] or "Unresolved start")} to {escape(row["period_end"])} · USD</small>'
            f'<dl>{values}</dl><details><summary>Period evidence</summary><p>{context}</p><small>{escape(definitions)}</small></details></article>'
        )
    directions = "".join(
        f'<li>{escape(x["from_period"])} → {escape(x["to_period"])}: '
        + (f'Revenue {escape(x["direction"])}' if x["status"] == "comparable" else 'Comparison withheld · annual period or source gap') + '</li>'
        for x in comparisons
    )
    return (
        STYLE + '<section class="online-history" aria-label="Historical annual financials"><h3>Historical annual financials</h3>'
        '<p>Latest reported values as observed now, including later revisions; this is not point-in-time history.</p>'
        + _line(points, "Reported annual revenue in USD; source or period gaps break the line")
        + '<ul>' + directions + '</ul><p>Percentage growth remains withheld until its derived field scope is reviewed.</p>'
        + '<div class="online-history-grid">' + "".join(cards) + '</div>'
        + f'<p><a href="{escape(history["source_url"], quote=True)}" target="_blank" rel="noopener noreferrer">SEC Companyfacts history source</a> · observed {escape(history["observed_at"])} · {escape(history["taxonomy"])}:{escape(history["concept"])} · USD. Direct-field scope inspected; raw redistribution held.</p></section>'
    )


def online_price_history_html(result):
    if result.get("status") == "not_requested":
        return '<p>Inspect one year of dated daily prices for this ticker on request.</p>'
    if result.get("status") != "inspection_only":
        reasons = {
            "commercial_rights_unreviewed": "Commercial source rights have not been reviewed. Personal price inspection is unavailable in commercial mode.",
            "personal_research_mode_required": "This action is available only in Personal Research.",
            "unsupported_price_currency": "The provider returned an unsupported currency.",
            "price_symbol_or_security_type_mismatch": "The provider symbol or security type did not match.",
            "price_source_unavailable": "The online price source is unavailable. Retry explicitly later.",
        }
        message = reasons.get(result.get("reason"), 'Price evidence failed validation; no price was accepted.')
        return f'<section class="online-price-inspection"><h3>Daily price history · personal research</h3><p>{escape(message)}</p></section>'
    ticker, symbol, bars = result.get("ticker"), result.get("provider_symbol"), result.get("bars")
    if (
        not isinstance(ticker, str) or re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,19}", ticker) is None
        or symbol != ticker.replace('.', '-') or not isinstance(bars, list) or not 1 <= len(bars) <= 400
        or result.get("currency") != "USD" or result.get("source_id") != "yahoo_chart"
        or result.get("rights_status") != "exact_source_unregistered_personal_inspection_only"
        or result.get("commercial_eligible") is not False or _utc_timestamp(result.get("observed_at")) is None
        or not str(result.get("source_url", "")).startswith(f'https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe="")}?')
        or any(not isinstance(r, dict) or _iso_date(r.get("date")) is None or not _finite_direct_number(r.get("close")) or r["close"] <= 0 for r in bars)
    ):
        return '<section class="online-price-inspection"><p>Price evidence is unavailable.</p></section>'
    if result.get("last_price_date") != bars[-1]["date"] or any(a["date"] >= b["date"] for a, b in zip(bars, bars[1:])):
        return '<section class="online-price-inspection"><p>Price chronology is unavailable.</p></section>'
    split_dates = ", ".join(str(x.get("date", "unknown")) for x in result.get("splits", [])) or "none reported in this response"
    return (
        STYLE + '<section class="online-price-inspection" aria-label="Daily price history"><h3>Daily price history · personal research</h3>'
        f'<p><strong>USD {_amount(bars[-1]["close"])}</strong> · provider daily close dated {escape(bars[-1]["date"])} · {len(bars)} completed daily bars.</p>'
        f'<p>{escape(str(result.get("observation_state", "unavailable")).replace("_", " "))}. The observation day is excluded to avoid an incomplete daily bar. This is a dated observation, not a real-time quote.</p>'
        + _line([(r["date"], r["close"]) for r in bars], "Yahoo provider daily closing prices in USD")
        + '<p>Adjustment basis is unverified. Splits and dividends can affect comparisons; no total-return calculation is shown. The issuer link to SEC has not been reconciled. Commercial use and redistribution remain held for this exact unregistered source.</p>'
        + f'<details><summary>Price source evidence</summary><p>Source: yahoo_chart · requested {escape(ticker)} · provider symbol {escape(symbol)} · observed {escape(result["observed_at"])} · timezone {escape(str(result.get("exchange_timezone", "unknown")))}.</p>'
        f'<p>Split event dates: {escape(split_dates)}. Missing source bars: {escape(str(result.get("missing_bar_count", 0)))}.</p>'
        f'<p><a href="{escape(result["source_url"], quote=True)}" target="_blank" rel="noopener noreferrer">Yahoo chart source</a> · payload SHA-256 {escape(str(result.get("payload_sha256", "unavailable")))}</p></details></section>'
    )
