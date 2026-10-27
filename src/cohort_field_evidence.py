"""Read-only, field-by-field gaps for the bounded company research cohort."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

from src.commercial_source_rights import load_source_rights_registry, review_commercial_field_scope


DEFAULT_TICKERS = ("AMD", "AVGO", "COHR", "MU", "NVDA", "QCOM")
FIELDS = (
    "revenue", "operating_income", "cash_from_operations", "capital_expenditures",
    "free_cash_flow", "fcf_margin", "shares_outstanding", "eps", "latest_close",
)
SCHEMA_VERSION = "cohort-field-evidence-v1"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [{str(k): str(v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes() if path.exists() else b"<missing>")
        digest.update(b"\0")
    return digest.hexdigest()


def _age_days(value: str, as_of: date) -> int | None:
    try:
        return (as_of - date.fromisoformat(value[:10])).days
    except (ValueError, TypeError):
        return None


def build_report(
    root: Path | str, *, tickers: tuple[str, ...] = DEFAULT_TICKERS, as_of: str,
) -> dict:
    root = Path(root)
    cutoff = date.fromisoformat(as_of)
    scoped = tuple(dict.fromkeys(str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()))
    if not scoped:
        raise ValueError("ticker_scope_empty")
    data = root / "data"
    fundamentals_path = data / "fundamentals.csv"
    prices_path = data / "prices.csv"
    readiness_path = data / "reports" / "ticker_readiness_report.csv"
    fundamentals = {row.get("ticker", "").upper(): row for row in _read_csv(fundamentals_path)}
    readiness = {row.get("ticker", "").upper(): row for row in _read_csv(readiness_path)}
    latest_price: dict[str, dict[str, str]] = {}
    for row in _read_csv(prices_path):
        ticker = row.get("ticker", "").upper()
        if ticker in scoped and row.get("date", "") > latest_price.get(ticker, {}).get("date", ""):
            latest_price[ticker] = row
    registry_path = root / "config" / "source_rights.yml"
    registry = load_source_rights_registry(registry_path) if registry_path.exists() else {}
    fields = []
    for ticker in scoped:
        fundamental = fundamentals.get(ticker, {})
        price = latest_price.get(ticker, {})
        for field in FIELDS:
            is_price = field == "latest_close"
            row = price if is_price else fundamental
            value = row.get("close", "") if is_price else row.get(field, "")
            source = "" if is_price else fundamental.get("source", "")
            source_ref = "" if is_price else (fundamental.get("source_ref") or fundamental.get("sec_accession") or "")
            period_end = "" if is_price else fundamental.get("as_of_date", "")
            observed_at = price.get("date", "") if is_price else fundamental.get("updated_at", "")
            published_at = "" if is_price else fundamental.get("sec_filed_date", "")
            if is_price:
                rights_status = "source_unidentified"
                registered = False
            elif source:
                scope = review_commercial_field_scope(registry, source, (field,))
                rights_status = scope.rights_status
                registered = scope.commercial_evidence_ready
            else:
                rights_status = "source_unidentified"
                registered = False
            reasons = []
            if not value:
                reasons.append("saved_field_missing")
            else:
                if is_price:
                    reasons.append("price_source_missing")
                else:
                    if not source:
                        reasons.append("source_missing")
                    elif not registered:
                        reasons.append("field_not_registered" if source in registry else "source_rights_unverified")
                    if not source_ref:
                        reasons.append("source_reference_missing")
                    # A row-level accession does not prove the exact concept, unit and duration for each field.
                    if source_ref:
                        reasons.append("field_specific_proof_missing")
                    if not period_end:
                        reasons.append("period_end_missing")
                    if not published_at:
                        reasons.append("publication_date_missing")
                if not observed_at:
                    reasons.append("observation_date_missing")
                days = _age_days(observed_at, cutoff)
                if days is not None and days > (7 if is_price else 90):
                    reasons.append("stale_observation")
                period_age = _age_days(period_end, cutoff)
                if not is_price and period_age is not None and period_age > 90:
                    reasons.append("old_period_end")
            fields.append({
                "ticker": ticker, "field": field, "value": value,
                "source": source, "source_ref": source_ref, "period_end": period_end,
                "source_published_at": published_at, "observation_date": observed_at,
                "observation_date_basis": "price_date" if is_price else "saved_row_updated_at",
                "rights_status": rights_status, "registered_field_scope": registered,
                "withheld_reasons": reasons,
                "interpretation_state": "withheld" if reasons else "inspect_only",
            })
    readiness_summary = {
        ticker: {key: readiness.get(ticker, {}).get(key, "") for key in (
            "price_ready", "fundamentals_ready", "dcf_ready", "peer_ready", "updated_at"
        )} for ticker in scoped
    }
    return {
        "schema_version": SCHEMA_VERSION, "as_of": as_of, "tickers": list(scoped),
        "snapshot_identity": _digest((fundamentals_path, prices_path, readiness_path, registry_path)),
        "fields": fields, "readiness_snapshot": readiness_summary,
        "inspection_only": True, "canonical_writes": False,
        "boundary": "Saved values and row-level source labels are not per-field proof or current readiness.",
    }


def compare_reports(before: dict, after: dict) -> dict:
    if (before.get("schema_version") != SCHEMA_VERSION or after.get("schema_version") != SCHEMA_VERSION
            or before.get("tickers") != after.get("tickers")):
        return {"status": "incompatible_scope", "changes": []}
    compared = ("value", "source", "source_ref", "period_end", "source_published_at",
                "observation_date", "observation_date_basis", "rights_status", "registered_field_scope",
                "withheld_reasons", "interpretation_state")

    def keyed_rows(report: dict) -> dict[tuple[str, str], dict] | None:
        rows = report.get("fields")
        tickers = report.get("tickers")
        if not isinstance(rows, list) or not isinstance(tickers, list):
            return None
        if (not tickers or any(not isinstance(ticker, str) or not ticker for ticker in tickers)
                or len(set(tickers)) != len(tickers)):
            return None
        expected = {(ticker, field) for ticker in tickers for field in FIELDS}
        found: dict[tuple[str, str], dict] = {}
        for row in rows:
            if not isinstance(row, dict) or any(key not in row for key in ("ticker", "field", *compared)):
                return None
            if not isinstance(row["ticker"], str) or not isinstance(row["field"], str):
                return None
            key = (row["ticker"], row["field"])
            if (key in found or key not in expected
                    or not isinstance(row["withheld_reasons"], list)
                    or any(not isinstance(reason, str) for reason in row["withheld_reasons"])):
                return None
            found[key] = row
        return found if found.keys() == expected else None

    prior = keyed_rows(before)
    current = keyed_rows(after)
    if prior is None or current is None:
        return {"status": "incompatible_scope", "changes": []}
    changed = []
    for ticker, field in sorted(prior):
        left, right = prior[ticker, field], current[ticker, field]
        dimensions = [key for key in compared if left[key] != right[key]]
        if dimensions:
            changed.append({"ticker": ticker, "field": field, "prior_value": left.get("value", ""),
                            "current_value": right.get("value", ""),
                            "prior_withheld_reasons": left.get("withheld_reasons", []),
                            "current_withheld_reasons": right.get("withheld_reasons", []),
                            "changed_dimensions": dimensions,
                            "before": {key: left[key] for key in dimensions},
                            "after": {key: right[key] for key in dimensions}})
    same_inputs = bool(before.get("snapshot_identity")) and (
        before.get("snapshot_identity") == after.get("snapshot_identity")
    )
    if same_inputs and changed:
        aging_reasons = {"stale_observation", "old_period_end"}
        aging_only = (
            before.get("as_of") != after.get("as_of")
            and all(
                set(row["changed_dimensions"]) <= {"withheld_reasons", "interpretation_state"}
                and "withheld_reasons" in row["changed_dimensions"]
                and bool(set(row["prior_withheld_reasons"]) ^ set(row["current_withheld_reasons"]))
                and (set(row["prior_withheld_reasons"]) ^ set(row["current_withheld_reasons"])) <= aging_reasons
                for row in changed
            )
        )
        if not aging_only:
            return {"status": "incompatible_scope", "changes": []}
        status = "review_date_reevaluation"
    else:
        status = "changed" if changed else "unchanged"
    return {"status": status, "changes": changed,
            "prior_snapshot_identity": before.get("snapshot_identity", ""),
            "current_snapshot_identity": after.get("snapshot_identity", ""),
            "same_input_digest": same_inputs,
            "input_changes": [] if same_inputs else changed,
            "inspection_only": True}


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only six-company field evidence and gap report.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--as-of", required=True, help="Declared YYYY-MM-DD review date")
    parser.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    parser.add_argument("--compare", type=Path, help="Prior saved report JSON to compare with current inputs")
    args = parser.parse_args()
    report = build_report(args.root, tickers=tuple(args.tickers.split(",")), as_of=args.as_of)
    if args.compare:
        before = json.loads(args.compare.read_text(encoding="utf-8"))
        print(json.dumps(compare_reports(before, report), indent=2, sort_keys=True))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
