from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_valid_package(root: Path) -> tuple[Path, Path]:
    package = root / "package"
    package.mkdir()
    identity = [{
        "identity_row_id": "id-1", "security_id": "sec-1", "issuer_id": "issuer-1",
        "ticker": "AAA", "exchange": "XNYS", "security_type": "common_stock",
        "currency": "USD", "valid_from": "2020-01-01T00:00:00Z", "valid_to": "",
        "source_id": "fixture_source", "source_ref": "fixture://identity/id-1",
        "source_published_at": "2020-01-01T00:00:00Z",
        "retrieved_at": "2020-01-02T00:00:00Z",
        "supersedes_identity_row_id": "",
    }]
    membership = [
        {
            "membership_row_id": f"member-{universe}", "universe_id": universe,
            "universe_kind": kind, "security_id": "sec-1",
            "membership_state": "included", "effective_from": "2020-01-01T00:00:00Z",
            "effective_to": "", "observation_at": "2020-01-01T00:00:00Z",
            "source_id": "fixture_source", "source_ref": f"fixture://membership/{universe}",
            "source_published_at": "2020-01-01T00:00:00Z",
            "retrieved_at": "2020-01-02T00:00:00Z",
            "supersedes_membership_row_id": "",
        }
        for universe, kind in (("bench-1", "benchmark"), ("research-1", "research_universe"))
    ]
    events = [{
        "event_row_id": "event-1", "security_id": "sec-1", "event_type": "listing",
        "effective_at": "2020-01-01T00:00:00Z", "successor_security_id": "",
        "ratio_numerator": "", "ratio_denominator": "", "listing_state_after": "active",
        "source_id": "fixture_source", "source_ref": "fixture://event/event-1",
        "source_published_at": "2020-01-01T00:00:00Z",
        "retrieved_at": "2020-01-02T00:00:00Z", "supersedes_event_row_id": "",
    }]
    evaluations = [
        {
            "evaluation_row_id": f"eval-{universe}", "universe_id": universe,
            "evaluation_at": "2021-01-01T00:00:00Z",
            "available_at": "2021-01-01T00:00:00Z", "partition": "train",
            "source_ref": f"fixture://evaluation/{universe}",
        }
        for universe in ("bench-1", "research-1")
    ]
    payloads = {
        "identity.csv": identity,
        "membership.csv": membership,
        "events.csv": events,
        "evaluations.csv": evaluations,
    }
    files = []
    contract_by_name = {
        "identity.csv": "security_identity",
        "membership.csv": "membership",
        "events.csv": "events",
        "evaluations.csv": "evaluations",
    }
    for name, rows in payloads.items():
        path = package / name
        _write_csv(path, rows)
        files.append({
            "path": name, "contract": contract_by_name[name],
            "sha256": _sha256(path), "row_count": len(rows),
        })
    registry = root / "source_rights.yml"
    registry.write_text(
        "sources:\n"
        "  - source_id: fixture_source\n"
        "    display_name: Test-only source\n"
        "    permitted_use: test_only\n"
        "    commercial_use: approved\n"
        "    redistribution: test_only\n"
        "    storage_limits: pytest temporary directory only\n"
        "    attribution: synthetic fixture\n"
        "    rate_limits: not_applicable\n"
        "    authentication: none\n"
        "    expected_freshness: point in time\n"
        "    supported_fields: [security_identity, universe_membership, corporate_actions, delistings]\n"
        "    fallback_priority: 1\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "point_in_time_universe_v1",
        "dataset_id": "fixture-dataset", "manifest_id": "fixture-manifest",
        "manifest_created_at": "2030-01-01T00:00:00Z",
        "observation_cutoff_at": "2021-01-01T00:00:00Z",
        "coverage_semantics": "complete_snapshot",
        "declared_universes": [
            {"universe_id": "bench-1", "universe_kind": "benchmark"},
            {"universe_id": "research-1", "universe_kind": "research_universe"},
        ],
        "allowed_source_ids": ["fixture_source"],
        "source_rights_registry_sha256": _sha256(registry),
        "files": files,
        "evaluation_policy": {
            "kind": "train_validation_test",
            "train_end_at": "2021-01-01T00:00:00Z",
            "validation_start_at": "2021-01-02T00:00:00Z",
            "validation_end_at": "2021-01-03T00:00:00Z",
            "test_start_at": "2021-01-04T00:00:00Z",
        },
        "corporate_action_policy": {
            "listing": "required", "ticker_change": "not_applicable",
            "exchange_change": "not_applicable", "split": "not_applicable",
            "reverse_split": "not_applicable", "merger": "not_applicable",
            "acquisition": "not_applicable", "spinoff": "not_applicable",
            "delisting": "not_applicable", "suspension": "not_applicable",
            "reactivation": "not_applicable",
        },
        "delisting_policy": {
            "retain_historical_members": True,
            "missing_evidence": "blocked",
        },
        "survivorship_policy": {
            "filter_by_current_listing_state": False,
        },
        "reproduction_contract": "membership_count_and_sha256_at_cutoff_v1",
    }
    manifest_path = package / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return manifest_path, registry
