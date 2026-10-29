"""Read-only candidate bridge for receipt-verified listing and SEC search aids.

No symbol association from this module is a security identity, domicile,
current listing, point-in-time membership, or analysis eligibility decision.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


WITHHELD_FIELDS = (
    "issuer_identity",
    "security_identity",
    "issuer_domicile",
    "security_type",
    "active_status",
    "point_in_time_membership",
    "financial_coverage",
    "analysis_eligibility",
)
_SYMBOL_FIELDS = ("act_symbol", "cqs_symbol", "nasdaq_symbol")
_REVIEW_PRIORITY = {
    "sec_ticker_conflict": 0,
    "ambiguous_directory_symbol": 1,
    "venue_conflict": 2,
    "venue_unmapped": 3,
    "secondary_symbol_lead": 4,
    "notation_lead": 5,
    "no_directory_counterpart": 6,
}
_SEC_VENUES = {
    "nasdaq": ("nasdaq", ""),
    "nyse": ("other", "N"),
    "new york stock exchange": ("other", "N"),
    "nyse american": ("other", "A"),
    "nyse arca": ("other", "P"),
    "cboe bzx": ("other", "Z"),
    "iex": ("other", "V"),
    "investors exchange": ("other", "V"),
    "texas stock exchange": ("other", "F"),
    "txse": ("other", "F"),
    "nyse texas": ("other", "M"),
}


def _directory_modified_date(report: dict) -> str:
    sources = report.get("sources")
    if not isinstance(sources, list) or len(sources) != 2:
        raise ValueError("directory_receipt_invalid")
    dates: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("directory_receipt_invalid")
        value = source.get("last_modified")
        if not isinstance(value, str):
            raise ValueError("directory_receipt_invalid")
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError) as exc:
            raise ValueError("directory_receipt_invalid") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("directory_receipt_invalid")
        dates.add(parsed.astimezone(timezone.utc).date().isoformat())
    if len(dates) != 1:
        raise ValueError("directory_receipt_time_mismatch")
    return dates.pop()


def _sec_modified_date(report: dict) -> str:
    value = report.get("last_modified_at_utc")
    if not isinstance(value, str):
        raise ValueError("sec_receipt_invalid")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("sec_receipt_invalid") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError("sec_receipt_invalid")
    return parsed.date().isoformat()


def _notation_alternatives(ticker: str) -> set[str]:
    alternatives: set[str] = set()
    if "-" in ticker:
        alternatives.add(ticker.replace("-", "."))
    preferred = re.fullmatch(r"([A-Z0-9]+)-P([A-Z0-9]+)", ticker)
    if preferred:
        alternatives.add(f"{preferred.group(1)}${preferred.group(2)}")
    return alternatives - {ticker}


def _venue_status(sec_exchange: str, directory_row: dict[str, str]) -> str:
    key = " ".join(sec_exchange.split()).casefold()
    expected = _SEC_VENUES.get(key)
    if expected is None:
        return "unmapped"
    actual = (directory_row["source"], directory_row["exchange_code"])
    return "concordant" if actual == expected else "conflict"


def _candidate_row_sets(
    symbol_index: dict[str, set[int]], ticker: str
) -> tuple[set[int], set[int]]:
    exact = set(symbol_index.get(ticker, ()))
    notation = set().union(
        *(symbol_index.get(alias, set()) for alias in _notation_alternatives(ticker))
    )
    return exact, exact | notation


def _classify_same_date(
    directory_rows: list[dict[str, str]],
    sec_rows: list[dict[str, object]],
    *,
    top_n: int,
) -> tuple[dict[str, int], int, list[dict[str, object]]]:
    symbol_index: dict[str, set[int]] = defaultdict(set)
    for index, row in enumerate(directory_rows):
        for field in _SYMBOL_FIELDS:
            symbol = row[field]
            if symbol:
                symbol_index[symbol].add(index)
    sec_by_ticker: dict[str, list[dict[str, object]]] = defaultdict(list)
    tickers_by_cik: dict[int, set[str]] = defaultdict(set)
    for row in sec_rows:
        ticker, cik = row["ticker"], row["cik"]
        sec_by_ticker[ticker].append(row)
        tickers_by_cik[cik].add(ticker)

    counts: Counter[str] = Counter()
    counts["ciks_with_multiple_tickers"] = sum(
        len(tickers) > 1 for tickers in tickers_by_cik.values()
    )
    matched_directory_rows: set[int] = set()
    queue: list[dict[str, object]] = []
    for ticker in sorted(sec_by_ticker):
        associations = sec_by_ticker[ticker]
        exact, candidates = _candidate_row_sets(symbol_index, ticker)
        if len(associations) != 1:
            counts["sec_ticker_conflicts"] += 1
            matched_directory_rows.update(candidates)
            queue.append({
                "ticker": ticker,
                "reason": "sec_ticker_conflict",
                "candidate_ciks": sorted({row["cik"] for row in associations})[:20],
                "association_count": len(associations),
                "candidate_count": len(candidates),
                "candidate_act_symbols": sorted(
                    directory_rows[index]["act_symbol"] for index in candidates
                )[:5],
            })
            continue
        association = associations[0]
        matched_directory_rows.update(candidates)
        lead: dict[str, object] = {
            "ticker": ticker,
            "cik": association["cik"],
            "sec_exchange": association["exchange"],
        }
        if not candidates:
            counts["no_directory_counterpart"] += 1
            queue.append({**lead, "reason": "no_directory_counterpart"})
            continue
        if len(candidates) > 1:
            counts["ambiguous_directory_symbols"] += 1
            queue.append({
                **lead,
                "reason": "ambiguous_directory_symbol",
                "candidate_count": len(candidates),
                "candidate_act_symbols": sorted(
                    directory_rows[index]["act_symbol"] for index in candidates
                )[:5],
            })
            continue
        candidate = directory_rows[next(iter(candidates))]
        lead["candidate_act_symbols"] = [candidate["act_symbol"]]
        if not candidates.intersection(exact):
            counts["notation_leads"] += 1
            queue.append({**lead, "reason": "notation_lead"})
        elif candidate["act_symbol"] != ticker:
            counts["secondary_symbol_leads"] += 1
            queue.append({**lead, "reason": "secondary_symbol_lead"})
        else:
            counts["exact_act_leads"] += 1
            venue = _venue_status(str(association["exchange"]), candidate)
            if venue == "concordant":
                counts["venue_concordant_exact_act"] += 1
            elif venue == "conflict":
                counts["venue_conflicts"] += 1
                queue.append({**lead, "reason": "venue_conflict"})
            else:
                counts["venue_unmapped"] += 1
                queue.append({**lead, "reason": "venue_unmapped"})

    counts["directory_rows_without_sec_lead"] = (
        len(directory_rows) - len(matched_directory_rows)
    )
    names = (
        "exact_act_leads", "secondary_symbol_leads", "notation_leads",
        "ambiguous_directory_symbols", "sec_ticker_conflicts",
        "no_directory_counterpart", "venue_concordant_exact_act",
        "venue_conflicts", "venue_unmapped", "directory_rows_without_sec_lead",
        "ciks_with_multiple_tickers",
    )
    queue.sort(key=lambda row: (_REVIEW_PRIORITY[row["reason"]], row["ticker"]))
    return {name: counts[name] for name in names}, len(queue), queue[:top_n]


def build_issuer_security_bridge(
    directory_report: dict,
    directory_rows: list[dict[str, str]],
    sec_report: dict,
    sec_rows: list[dict[str, object]],
    *,
    top_n: int = 10,
) -> dict[str, object]:
    """Compare verified search aids only when their HTTP-modified dates match."""
    if type(top_n) is not int or not 0 <= top_n <= 20:
        raise ValueError("top_n_invalid")
    if (
        directory_report.get("status") != "validated_receipts"
        or directory_report.get("inspection_only") is not True
        or directory_report.get("import_status") != "held"
        or directory_report.get("rights_status") != "unreviewed"
    ):
        raise ValueError("directory_receipt_invalid")
    if (
        type(directory_report.get("total_non_test_symbols")) is not int
        or directory_report["total_non_test_symbols"] != len(directory_rows)
    ):
        raise ValueError("directory_count_mismatch")
    if (
        sec_report.get("status") != "validated_receipt"
        or sec_report.get("inspection_only") is not True
        or sec_report.get("safe_to_import") is not False
        or sec_report.get("rights_status") != "unreviewed"
    ):
        raise ValueError("sec_receipt_invalid")
    if (
        type(sec_report.get("row_count")) is not int
        or sec_report["row_count"] != len(sec_rows)
    ):
        raise ValueError("sec_count_mismatch")
    if (
        type(sec_report.get("distinct_cik_count")) is not int
        or sec_report["distinct_cik_count"] != len({row["cik"] for row in sec_rows})
    ):
        raise ValueError("sec_cik_count_mismatch")
    directory_date = _directory_modified_date(directory_report)
    sec_date = _sec_modified_date(sec_report)
    same_date = directory_date == sec_date
    report: dict[str, object] = {
        "schema_version": "issuer_security_bridge_v1",
        "status": "same_date_inspection" if same_date else "cutoff_mismatch",
        "inspection_only": True,
        "safe_to_import": False,
        "rights_status": "unreviewed",
        "source_alignment": {
            "basis": "http_last_modified_utc_calendar_date",
            "directory_date": directory_date,
            "sec_date": sec_date,
            "status": "same_date" if same_date else "mismatch",
            "simultaneous_cut_proven": False,
        },
        "inputs": {
            "directory_non_test_symbols": len(directory_rows),
            "directory_excluded_test_issues": directory_report.get("excluded_test_issues", 0),
            "sec_ticker_associations": len(sec_rows),
            "directory_receipts": [
                {"source": item.get("source"), "sha256": item.get("sha256"),
                 "last_modified": item.get("last_modified"),
                 "source_created_at": item.get("source_created_at"),
                 "observed_at_utc": item.get("observed_at_utc")}
                for item in directory_report["sources"]
            ],
            "sec_receipt": {
                "url": sec_report.get("url"),
                "sha256": sec_report.get("sha256"),
                "last_modified_at_utc": sec_report.get("last_modified_at_utc"),
                "observed_at_utc": sec_report.get("observed_at_utc"),
                "manifest_sha256": sec_report.get("manifest_sha256"),
            },
        },
        "comparison_performed": same_date,
        "comparison_counts": None,
        "review_queue_total_count": None,
        "review_queue": [],
        "withheld_fields": list(WITHHELD_FIELDS),
        "boundary": "Ticker and CIK associations are review leads only; no identity, domicile, lifecycle, universe membership, financial coverage, or rights conclusion is granted.",
    }
    if not same_date:
        return report
    counts, total, queue = _classify_same_date(
        directory_rows, sec_rows, top_n=top_n
    )
    report["comparison_counts"] = counts
    report["review_queue_total_count"] = total
    report["review_queue"] = queue
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect receipt-verified listing and SEC search associations"
    )
    parser.add_argument("--directory-snapshot", required=True, type=Path)
    parser.add_argument("--sec-capture", required=True, type=Path)
    parser.add_argument("--top-n", type=int, default=10)
    args = parser.parse_args(argv)

    from src.sec_association_receipt import load_sec_association_receipt
    from src.us_listing_receipt_audit import load_us_listing_rows

    try:
        directory_report, directory_rows = load_us_listing_rows(
            args.directory_snapshot
        )
        sec_report, sec_rows = load_sec_association_receipt(args.sec_capture)
        report = build_issuer_security_bridge(
            directory_report, directory_rows, sec_report, sec_rows,
            top_n=args.top_n,
        )
    except ValueError as exc:
        print(json.dumps({
            "status": "invalid",
            "inspection_only": True,
            "comparison_performed": False,
            "safe_to_import": False,
            "rights_status": "unreviewed",
            "reason": str(exc),
        }, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "same_date_inspection" else 2


if __name__ == "__main__":
    raise SystemExit(main())
