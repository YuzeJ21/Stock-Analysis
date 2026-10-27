"""Receipt-bound, local-only packet for one exact NVIDIA quarterly filing.

The normal Workbench preview remains an in-memory, no-write path. This module
prints a separate inspection packet; it never applies a financial row.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from src.cohort_field_evidence import DEFAULT_TICKERS, FIELDS, SCHEMA_VERSION as COHORT_SCHEMA
from src.commercial_source_rights import (
    SourceRights,
    load_source_rights_registry,
    review_commercial_field_scope,
)
from src.earnings_nowcast_contract import parse_utc_timestamp
from src.providers.sec_companyfacts import SECUserAgentError, _require_user_agent
from src.sec_quarterly_cash_generation_pilot import (
    CAPEX_CONCEPTS,
    CASH_FROM_OPERATIONS_CONCEPTS,
    OPERATING_INCOME_CONCEPTS,
    REVENUE_CONCEPTS,
    extract_sec_quarterly_cash_generation,
    preview_sec_quarterly_cash_generation,
)
from src.sec_quarterly_cash_generation_preview import (
    SecQuarterlyPreviewFetchError,
    _fetch_bytes,
)


SCHEMA_VERSION = "sec-cash-generation-evidence-v2"
TICKER = "NVDA"
CIK = "0001045810"
FISCAL_PERIOD = "2027-Q1"
PERIOD_START = "2026-01-26"
PERIOD_END = "2026-04-26"
ACCESSION = "0001045810-26-000052"
PRIMARY_DOCUMENT = "nvda-20260426.htm"
SOURCE_ID = "sec_companyfacts"
PINNED_SOURCE_URLS = {
    "companyfacts": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json",
    "submissions": f"https://data.sec.gov/submissions/CIK{CIK}.json",
    "filing": (
        "https://www.sec.gov/Archives/edgar/data/1045810/"
        "000104581026000052/nvda-20260426.htm"
    ),
}
_CONCEPTS = {
    "revenue": REVENUE_CONCEPTS,
    "operating_income": OPERATING_INCOME_CONCEPTS,
    "cash_from_operations": CASH_FROM_OPERATIONS_CONCEPTS,
    "capital_expenditures": CAPEX_CONCEPTS,
}
_COMPARISON_FIELDS = (
    "revenue", "operating_income", "cash_from_operations",
    "capital_expenditures", "free_cash_flow", "fcf_margin",
)
_CAPTURE_FILENAMES = {
    "companyfacts": "companyfacts.json",
    "submissions": "submissions.json",
    "filing": "primary_filing.html",
}


@dataclass(frozen=True)
class CapturedSecSources:
    raw_sources: Mapping[str, bytes]
    observed_at_by_source: Mapping[str, str]


def capture_exact_sec_sources(
    *,
    user_agent: str | None = None,
    fetcher: Callable[[str, str], bytes] | None = None,
    clock: Callable[[], str] | None = None,
) -> CapturedSecSources:
    """Fetch only the three pinned URLs; keep bytes in memory by default."""

    identified_agent = _require_user_agent(user_agent)
    retrieve = fetcher or _fetch_bytes
    now = clock or (lambda: datetime.now(timezone.utc).isoformat())
    raw: dict[str, bytes] = {}
    observed: dict[str, str] = {}
    for name, url in PINNED_SOURCE_URLS.items():
        response = retrieve(url, identified_agent)
        if not isinstance(response, bytes) or not response:
            raise ValueError(f"{name}:source_bytes_missing")
        raw[name] = response
        observed[name] = parse_utc_timestamp(now(), label=f"{name}:observed_at").isoformat()
    return CapturedSecSources(raw_sources=raw, observed_at_by_source=observed)


def load_exact_sec_capture(
    source_dir: Path, *, allowed_root: Path | None = None
) -> CapturedSecSources:
    """Replay ignored local bytes only after verifying pinned URLs and digests."""

    root = Path(__file__).resolve().parent.parent
    local_root = (
        allowed_root if allowed_root is not None else root / "outputs" / "local"
    ).resolve()
    directory = source_dir.resolve()
    if not directory.is_relative_to(local_root):
        raise ValueError("source_dir_must_be_under_ignored_outputs_local")
    manifest_path = directory / "manifest.json"
    if manifest_path.is_symlink():
        raise ValueError("manifest_symlink_invalid")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    receipts = manifest.get("source_receipts") if isinstance(manifest, dict) else None
    if not isinstance(receipts, list) or len(receipts) != len(PINNED_SOURCE_URLS):
        raise ValueError("source_receipt_scope_invalid")
    if any(not isinstance(row, dict) or not isinstance(row.get("name"), str) for row in receipts):
        raise ValueError("source_receipt_scope_invalid")
    by_name = {
        row["name"]: row for row in receipts
    }
    if len(by_name) != len(receipts) or set(by_name) != set(PINNED_SOURCE_URLS):
        raise ValueError("source_receipt_scope_invalid")
    raw: dict[str, bytes] = {}
    observed: dict[str, str] = {}
    for name, url in PINNED_SOURCE_URLS.items():
        receipt = by_name[name]
        if receipt.get("url") != url:
            raise ValueError(f"{name}:receipt_url_mismatch")
        path = directory / _CAPTURE_FILENAMES[name]
        if path.is_symlink():
            raise ValueError(f"{name}:source_symlink_invalid")
        contents = path.read_bytes()
        if hashlib.sha256(contents).hexdigest() != receipt.get("sha256"):
            raise ValueError(f"{name}:receipt_digest_mismatch")
        if len(contents) != receipt.get("byte_length"):
            raise ValueError(f"{name}:receipt_length_mismatch")
        try:
            observed[name] = parse_utc_timestamp(
                receipt["observed_at_utc"], label=f"{name}:observed_at"
            ).isoformat()
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{name}:observation_time_invalid") from exc
        raw[name] = contents
    return CapturedSecSources(raw_sources=raw, observed_at_by_source=observed)


def _matching_fact_values(companyfacts: Mapping[str, Any], concepts: tuple[str, ...]) -> dict[str, set[float]]:
    matched: dict[str, set[float]] = {}
    all_facts = companyfacts.get("facts", {})
    if not isinstance(all_facts, Mapping):
        raise ValueError("companyfacts:payload_shape_invalid")
    facts = all_facts.get("us-gaap", {})
    if not isinstance(facts, Mapping):
        raise ValueError("companyfacts:payload_shape_invalid")
    for concept in concepts:
        fact = facts.get(concept)
        if fact is None:
            continue
        if not isinstance(fact, Mapping):
            raise ValueError("companyfacts:payload_shape_invalid")
        units = fact.get("units", {})
        if not isinstance(units, Mapping):
            raise ValueError("companyfacts:payload_shape_invalid")
        for unit, rows in units.items():
            if not isinstance(rows, list):
                raise ValueError("companyfacts:payload_shape_invalid")
            for row in rows:
                if not isinstance(row, Mapping):
                    raise ValueError("companyfacts:payload_shape_invalid")
                if (
                    row.get("accn") != ACCESSION
                    or row.get("start") != PERIOD_START
                    or row.get("end") != PERIOD_END
                    or row.get("fy") != 2027
                    or row.get("fp") != "Q1"
                    or row.get("form") not in {"10-Q", "10-Q/A"}
                    or row.get("val") is None
                ):
                    continue
                try:
                    value = float(row["val"])
                except (TypeError, ValueError):
                    continue
                if math.isfinite(value):
                    matched.setdefault(str(unit), set()).add(value)
    return matched


def _source_conflicts(companyfacts: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    for field, concepts in _CONCEPTS.items():
        values = _matching_fact_values(companyfacts, concepts)
        if any(unit != "USD" for unit in values):
            blockers.append(f"{field}:unit_conflict")
        if len(values.get("USD", set())) > 1:
            blockers.append(f"{field}:concept_conflict")
    return blockers


def _saved_comparison(saved_cohort: Mapping[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
    empty = {"cohort_snapshot_identity": "", "fields": [], "inspection_only": True}
    if not isinstance(saved_cohort, Mapping):
        return empty, ["saved_cohort:scope_invalid"]
    rows = saved_cohort.get("fields")
    expected = {(ticker, field) for ticker in DEFAULT_TICKERS for field in FIELDS}
    if (
        saved_cohort.get("schema_version") != COHORT_SCHEMA
        or saved_cohort.get("tickers") != list(DEFAULT_TICKERS)
        or saved_cohort.get("inspection_only") is not True
        or not isinstance(rows, list)
        or len(rows) != len(expected)
        or not isinstance(saved_cohort.get("snapshot_identity"), str)
        or re.fullmatch(r"[0-9a-f]{64}", saved_cohort["snapshot_identity"]) is None
        or any(not isinstance(row, Mapping) for row in rows)
        or any(
            not isinstance(row.get("ticker"), str)
            or not isinstance(row.get("field"), str)
            or not isinstance(row.get("withheld_reasons"), list)
            or any(not isinstance(reason, str) for reason in row["withheld_reasons"])
            for row in rows
        )
    ):
        return empty, ["saved_cohort:scope_invalid"]
    by_key = {(row.get("ticker"), row.get("field")): row for row in rows}
    if set(by_key) != expected or len(by_key) != len(rows):
        return empty, ["saved_cohort:scope_invalid"]
    compared = []
    for field in _COMPARISON_FIELDS:
        saved = by_key[(TICKER, field)]
        old_period = str(saved.get("period_end") or "")
        old_ref = str(saved.get("source_ref") or "")
        if old_period != "2026-01-25" or old_ref != "0001045810-26-000021":
            return empty, ["saved_cohort:nvda_reference_mismatch"]
        if saved.get("interpretation_state") != "withheld":
            return empty, ["saved_cohort:unexpected_interpretation"]
        compared.append({
            "field": field,
            "saved_value": str(saved.get("value") or ""),
            "saved_period_end_date": old_period,
            "saved_source_ref": old_ref,
            "saved_interpretation_state": "withheld",
            "saved_withheld_reasons": list(saved.get("withheld_reasons") or []),
            "candidate_period_end_date": PERIOD_END,
            "candidate_accession": ACCESSION,
            "relationship": "different_period_and_accession",
            "numeric_delta": None,
        })
    return {
        "cohort_snapshot_identity": saved_cohort["snapshot_identity"],
        "fields": compared,
        "inspection_only": True,
    }, []


def build_packet_from_bytes(
    *,
    raw_sources: Mapping[str, bytes],
    observed_at_by_source: Mapping[str, str],
    as_of: str,
    rights_registry: Mapping[str, SourceRights],
    saved_cohort: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Validate exact bytes and evidence; return a deterministic no-write packet."""

    blockers: list[str] = []
    receipts = []
    for name, url in PINNED_SOURCE_URLS.items():
        raw = raw_sources.get(name)
        if not isinstance(raw, bytes) or not raw:
            blockers.append(f"{name}:source_bytes_missing")
            continue
        try:
            observed = parse_utc_timestamp(
                observed_at_by_source[name], label=f"{name}:observed_at"
            ).isoformat()
        except (KeyError, ValueError, TypeError):
            observed = ""
            blockers.append(f"{name}:observation_time_invalid")
        receipts.append({
            "name": name, "url": url, "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_length": len(raw), "observed_at_utc": observed,
        })
    comparison, comparison_blockers = _saved_comparison(saved_cohort)
    blockers.extend(comparison_blockers)
    identity = {
        "ticker": TICKER, "cik": CIK, "accession": ACCESSION,
        "primary_document": PRIMARY_DOCUMENT, "fiscal_period": FISCAL_PERIOD,
        "period_start_date": PERIOD_START, "period_end_date": PERIOD_END,
        "duration_basis": "three_months", "filing_date": "", "accepted_at": "",
        "publication_timestamp_basis": "SEC submissions acceptanceDateTime",
    }
    components: list[dict[str, Any]] = []
    registry_record = rights_registry.get(SOURCE_ID)
    rights = {
        "component_registry_source_id": SOURCE_ID,
        "component_redistribution_scope": (
            registry_record.redistribution if registry_record else "unverified"
        ),
        "raw_filing_redistribution": "unreviewed",
        "sec_identity_metadata_scope": "unreviewed",
    }
    if set(raw_sources) != set(PINNED_SOURCE_URLS):
        blockers.append("source_set_mismatch")
    try:
        cutoff = parse_utc_timestamp(as_of, label="as_of").isoformat()
    except ValueError:
        cutoff = ""
        blockers.append("as_of_invalid")
    observation_after_cutoff = bool(cutoff) and any(
        parse_utc_timestamp(row["observed_at_utc"]) > parse_utc_timestamp(cutoff)
        for row in receipts if row["observed_at_utc"]
    )
    if observation_after_cutoff:
        blockers.append("source_observed_after_cutoff")
    if len(receipts) == 3 and cutoff and not any(
        item.endswith("observation_time_invalid") for item in blockers
    ):
        try:
            companyfacts = json.loads(raw_sources["companyfacts"].decode("utf-8"))
            submissions = json.loads(raw_sources["submissions"].decode("utf-8"))
            filing_html = raw_sources["filing"].decode("utf-8")
            if not isinstance(companyfacts, dict) or not isinstance(submissions, dict):
                raise ValueError("payload_shape_invalid")
            if str(submissions.get("cik") or "").zfill(10) != CIK:
                blockers.append("submissions:cik_mismatch")
            if TICKER not in [str(value).upper() for value in submissions.get("tickers", ())]:
                blockers.append("submissions:ticker_mismatch")
            blockers.extend(_source_conflicts(companyfacts))
            extraction = extract_sec_quarterly_cash_generation(
                ticker=TICKER, cik=CIK, fiscal_period=FISCAL_PERIOD,
                period_start_date=PERIOD_START, period_end_date=PERIOD_END,
                accession=ACCESSION, primary_document=PRIMARY_DOCUMENT,
                companyfacts_payload=companyfacts,
                submissions_payload=submissions, filing_html=filing_html,
                retrieved_at=max(row["observed_at_utc"] for row in receipts),
                as_of=cutoff,
            )
            blockers.extend(extraction.blockers)
            identity["filing_date"] = extraction.filing_date
            identity["accepted_at"] = extraction.accepted_at
            if not extraction.blockers:
                for proof in extraction.component_evidence:
                    scope = review_commercial_field_scope(
                        rights_registry, SOURCE_ID, (proof.metric,)
                    )
                    if proof.companyfacts_filed_date != extraction.filing_date:
                        blockers.append(f"{proof.metric}:filing_date_mismatch")
                    if proof.inline_unit != "USD":
                        blockers.append(f"{proof.metric}:inline_unit_mismatch")
                    if not math.isclose(
                        abs(proof.inline_display_value), abs(proof.raw_value), abs_tol=0.5
                    ):
                        blockers.append(f"{proof.metric}:inline_value_mismatch")
                    if not scope.commercial_evidence_ready:
                        blockers.append(f"{proof.metric}:field_scope_unverified")
                    components.append({
                        "field": proof.metric,
                        "concept": proof.concept,
                        "unit": proof.unit,
                        "unit_scale": proof.unit_scale,
                        "raw_value": proof.raw_value,
                        "normalized_value": proof.normalized_value,
                        "period_start_date": proof.period_start_date,
                        "period_end_date": proof.period_end_date,
                        "fiscal_period": proof.fiscal_period,
                        "companyfacts_filed_date": proof.companyfacts_filed_date,
                        "inline_fact_id": proof.inline_fact_id,
                        "inline_unit": proof.inline_unit,
                        "inline_scale": proof.inline_scale,
                        "inline_display_value": proof.inline_display_value,
                        "source_published_at": extraction.accepted_at,
                        "source_ref": proof.source_ref,
                        "explicit_outflow": proof.explicit_outflow,
                        "definition": [proof.unit, proof.unit_scale, "reported", proof.duration_basis],
                        "rights_status": scope.rights_status,
                        "registered_field_scope": scope.commercial_evidence_ready,
                    })
                acceptance = preview_sec_quarterly_cash_generation(
                    extraction=extraction, rights_registry=rights_registry, as_of=cutoff
                )
                blockers.extend(acceptance.blockers)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, KeyError, ValueError) as exc:
            blockers.append(f"source_payload_invalid:{type(exc).__name__}")
    stable_blockers = list(dict.fromkeys(blockers))
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "blocked" if stable_blockers else "accepted_for_review",
        "blockers": stable_blockers,
        "as_of": cutoff,
        "evidence_review_cutoff": cutoff,
        "cutoff_basis": "SEC publication and source observations at or before review cutoff",
        "source_observed_after_cutoff": observation_after_cutoff,
        "source_receipts": receipts,
        "identity": identity,
        "component_rights": rights,
        "components": components,
        "derived_withheld": [
            {"field": field, "reason": "derived_field_not_registered", "value": None}
            for field in ("free_cash_flow", "fcf_margin")
        ],
        "saved_comparison": comparison,
        "inspection_only": True,
        "canonical_writes": False,
        "production_activation": False,
        "readiness_promotions": [],
        "boundary": (
            "Component registry scope does not approve raw filing redistribution, "
            "SEC identity metadata, derived field interpretation, or a canonical import."
        ),
    }


def _save_local_capture(
    capture_dir: Path, captured: CapturedSecSources, packet: Mapping[str, Any]
) -> None:
    root = Path(__file__).resolve().parent.parent
    local_root = (root / "outputs" / "local").resolve()
    destination = capture_dir.resolve()
    if not destination.is_relative_to(local_root):
        raise ValueError("capture_dir_must_be_under_ignored_outputs_local")
    destination.mkdir(parents=True, exist_ok=True)
    files = {
        _CAPTURE_FILENAMES[name]: captured.raw_sources[name]
        for name in PINNED_SOURCE_URLS
    }
    files["manifest.json"] = (
        json.dumps({"source_receipts": packet["source_receipts"]}, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    for filename, contents in files.items():
        target = destination / filename
        if target.is_symlink() or (target.exists() and target.read_bytes() != contents):
            raise ValueError(f"capture_conflict:{filename}")
    for filename, contents in files.items():
        target = destination / filename
        if not target.exists():
            target.write_bytes(contents)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build one local, exact-source SEC evidence packet.")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--saved-cohort", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, help="Replay verified ignored local bytes")
    parser.add_argument("--capture-dir", type=Path)
    parser.add_argument("--sec-user-agent")
    args = parser.parse_args(argv)
    try:
        if args.source_dir is not None and args.capture_dir is not None:
            raise ValueError("source_dir_and_capture_dir_mutually_exclusive")
        captured = (
            load_exact_sec_capture(args.source_dir)
            if args.source_dir is not None
            else capture_exact_sec_sources(user_agent=args.sec_user_agent)
        )
        saved = json.loads(args.saved_cohort.read_text(encoding="utf-8"))
        packet = build_packet_from_bytes(
            raw_sources=captured.raw_sources,
            observed_at_by_source=captured.observed_at_by_source,
            as_of=args.as_of,
            rights_registry=load_source_rights_registry(),
            saved_cohort=saved,
        )
        if args.capture_dir is not None:
            _save_local_capture(args.capture_dir, captured, packet)
    except (SECUserAgentError, SecQuarterlyPreviewFetchError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "schema_version": SCHEMA_VERSION, "status": "blocked",
            "blockers": [str(exc)], "inspection_only": True,
            "canonical_writes": False, "production_activation": False,
            "readiness_promotions": [],
        }, indent=2, sort_keys=True))
        return 2
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0 if packet["status"] == "accepted_for_review" else 2


if __name__ == "__main__":
    raise SystemExit(main())
