import csv
import hashlib
import json
from types import SimpleNamespace

import pytest

from tests.point_in_time_universe_fixture import build_valid_package
from tests.test_point_in_time_universe_contracts import _rewrite_csv_and_manifest


EXPECTED_REASON_PREFIXES = {
    "manifest_",
    "schema_",
    "lineage_",
    "identity_",
    "membership_",
    "corporate_action_",
    "delisting_",
    "source_rights_",
    "cutoff_",
    "leakage_",
    "partition_",
    "reproduction_",
}

EXPECTED_EXCLUSION_CODES = {
    "schema_columns_invalid",
    "schema_required_field_missing",
    "schema_whitespace_invalid",
    "schema_timestamp_invalid",
    "schema_enum_invalid",
    "schema_ratio_invalid",
    "schema_ratio_pair_required",
    "schema_delisting_listing_state_invalid",
    "schema_identity_interval_reversed",
    "schema_membership_interval_reversed",
    "schema_event_row_id_duplicate",
    "schema_evaluation_row_id_duplicate",
    "lineage_duplicate_id",
    "lineage_missing_parent",
    "lineage_cross_scope_parent",
    "lineage_order_reversed",
    "lineage_multiple_roots",
    "lineage_fork",
    "lineage_cycle",
    "identity_interval_overlap",
    "identity_missing",
    "membership_interval_inactive",
    "corporate_action_policy_unsupported",
    "corporate_action_successor_required",
    "delisting_transition_invalid",
    "cutoff_evaluation_after_manifest",
    "cutoff_evaluation_unavailable",
    "cutoff_post_evaluation_evidence",
    "cutoff_required_scope_unavailable",
    "cutoff_later_revision_invisible",
    "cutoff_unrelated_scope_invisible",
    "leakage_evaluation_after_manifest_cutoff",
    "leakage_evaluation_available_late",
    "leakage_post_cutoff_evidence",
    "partition_assignment_invalid",
    "partition_minimum_history_unmet",
    "partition_boundary_unassigned",
    "reproduction_evaluation_after_manifest_cutoff",
}

EXPECTED_EXCLUSION_PREFIXES = {
    "schema_",
    "lineage_",
    "identity_",
    "membership_",
    "corporate_action_",
    "delisting_",
    "cutoff_",
    "leakage_",
    "partition_",
    "reproduction_",
}

EXCLUSION_MUTATION_CASES = (
    "schema_columns",
    "schema_required",
    "schema_whitespace",
    "schema_timestamp",
    "schema_enum",
    "schema_ratio",
    "schema_ratio_pair",
    "schema_delisting_state",
    "schema_identity_interval",
    "schema_membership_interval",
    "schema_event_duplicate",
    "schema_evaluation_duplicate",
    "lineage_duplicate",
    "lineage_missing_parent",
    "lineage_cross_scope",
    "lineage_order_reversed",
    "lineage_multiple_roots",
    "lineage_fork",
    "lineage_cycle",
    "identity_interval_overlap",
    "identity_missing",
    "membership_interval_inactive",
    "corporate_action_unsupported",
    "corporate_action_successor",
    "delisting_transition",
    "cutoff_after_manifest",
    "cutoff_evaluation_unavailable",
    "cutoff_required_scope",
    "cutoff_later_revision",
    "cutoff_unrelated_scope",
    "partition_assignment",
    "partition_minimum_history",
    "partition_boundary",
)


def _sha256_members(*security_ids):
    return hashlib.sha256("\n".join(sorted(security_ids)).encode("utf-8")).hexdigest()


def _decision(packet, area):
    return packet.decisions[area]


def _digest_by_universe(packet):
    return {digest.universe_id: digest for digest in packet.membership_digests}


def _rewrite_manifest(manifest, mutate):
    raw = json.loads(manifest.read_text())
    mutate(raw)
    manifest.write_text(json.dumps(raw), encoding="utf-8")


def _refresh_registry_digest(manifest, registry):
    _rewrite_manifest(
        manifest,
        lambda raw: raw.update(
            source_rights_registry_sha256=hashlib.sha256(
                registry.read_bytes()
            ).hexdigest()
        ),
    )


def _replace_contract_rows(manifest, contract, rows):
    raw = json.loads(manifest.read_text())
    entry = next(item for item in raw["files"] if item["contract"] == contract)
    path = manifest.parent / entry["path"]
    with path.open(encoding="utf-8", newline="") as handle:
        fieldnames = next(csv.reader(handle))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    entry["row_count"] = len(rows)
    manifest.write_text(json.dumps(raw), encoding="utf-8")


def _read_contract_rows(manifest, contract):
    raw = json.loads(manifest.read_text())
    entry = next(item for item in raw["files"] if item["contract"] == contract)
    path = manifest.parent / entry["path"]
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _refresh_contract_digest(manifest, contract):
    raw = json.loads(manifest.read_text())
    entry = next(
        item for item in raw["files"] if item["contract"] == contract
    )
    path = manifest.parent / entry["path"]
    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    entry["row_count"] = len(path.read_text(encoding="utf-8").splitlines()) - 1
    manifest.write_text(json.dumps(raw), encoding="utf-8")


def _mutate_identity_lineage_exclusion(manifest, case):
    def mutate(rows):
        base = rows[0]
        if case == "lineage_duplicate":
            rows.append(
                {
                    **base,
                    "source_ref": "fixture://identity/duplicate",
                }
            )
        elif case == "lineage_missing_parent":
            base["supersedes_identity_row_id"] = "missing"
        elif case == "lineage_cross_scope":
            rows.append(
                {
                    **base,
                    "identity_row_id": "id-cross-scope",
                    "security_id": "sec-2",
                    "issuer_id": "issuer-2",
                    "source_ref": "fixture://identity/cross-scope",
                    "source_published_at": "2020-02-01T00:00:00Z",
                    "retrieved_at": "2020-02-02T00:00:00Z",
                    "supersedes_identity_row_id": "id-1",
                }
            )
        elif case == "lineage_order_reversed":
            rows.append(
                {
                    **base,
                    "identity_row_id": "id-reversed",
                    "source_ref": "fixture://identity/reversed",
                    "source_published_at": "2020-01-01T00:00:00Z",
                    "retrieved_at": "2020-01-01T00:00:00Z",
                    "supersedes_identity_row_id": "id-1",
                }
            )
        elif case == "lineage_multiple_roots":
            rows.append(
                {
                    **base,
                    "identity_row_id": "id-second-root",
                    "source_ref": "fixture://identity/second-root",
                }
            )
        elif case == "lineage_fork":
            for suffix, month in (("a", "02"), ("b", "03")):
                rows.append(
                    {
                        **base,
                        "identity_row_id": f"id-child-{suffix}",
                        "source_ref": f"fixture://identity/child-{suffix}",
                        "source_published_at": (
                            f"2020-{month}-01T00:00:00Z"
                        ),
                        "retrieved_at": f"2020-{month}-02T00:00:00Z",
                        "supersedes_identity_row_id": "id-1",
                    }
                )
        elif case == "lineage_cycle":
            base["supersedes_identity_row_id"] = "id-cycle"
            rows.append(
                {
                    **base,
                    "identity_row_id": "id-cycle",
                    "source_ref": "fixture://identity/cycle",
                    "source_published_at": "2020-02-01T00:00:00Z",
                    "retrieved_at": "2020-02-02T00:00:00Z",
                    "supersedes_identity_row_id": "id-1",
                }
            )

    _rewrite_csv_and_manifest(manifest, "security_identity", mutate)


def _mutate_exclusion_case(manifest, case):
    if case == "schema_columns":
        identity = manifest.parent / "identity.csv"
        identity.write_text(
            identity.read_text(encoding="utf-8").replace(
                "issuer_id,",
                "",
                1,
            ),
            encoding="utf-8",
        )
        _refresh_contract_digest(manifest, "security_identity")
    elif case == "schema_required":
        _rewrite_csv_and_manifest(
            manifest,
            "security_identity",
            lambda rows: rows[0].update(ticker=""),
        )
    elif case == "schema_whitespace":
        _rewrite_csv_and_manifest(
            manifest,
            "security_identity",
            lambda rows: rows[0].update(security_id=" sec-1 "),
        )
    elif case == "schema_timestamp":
        _rewrite_csv_and_manifest(
            manifest,
            "security_identity",
            lambda rows: rows[0].update(valid_from="not-a-timestamp"),
        )
    elif case == "schema_enum":
        _rewrite_csv_and_manifest(
            manifest,
            "membership",
            lambda rows: rows[0].update(membership_state="maybe"),
        )
    elif case == "schema_ratio":
        _rewrite_csv_and_manifest(
            manifest,
            "events",
            lambda rows: rows[0].update(
                ratio_numerator="nan",
                ratio_denominator="1",
            ),
        )
    elif case == "schema_ratio_pair":
        _rewrite_csv_and_manifest(
            manifest,
            "events",
            lambda rows: rows[0].update(
                event_type="split",
                ratio_numerator="",
                ratio_denominator="",
            ),
        )
    elif case == "schema_delisting_state":
        _rewrite_csv_and_manifest(
            manifest,
            "events",
            lambda rows: rows[0].update(
                event_type="delisting",
                listing_state_after="active",
            ),
        )
    elif case == "schema_identity_interval":
        _rewrite_csv_and_manifest(
            manifest,
            "security_identity",
            lambda rows: rows[0].update(
                valid_from="2020-06-01T00:00:00Z",
                valid_to="2020-05-01T00:00:00Z",
            ),
        )
    elif case == "schema_membership_interval":
        _rewrite_csv_and_manifest(
            manifest,
            "membership",
            lambda rows: rows[0].update(
                effective_from="2020-06-01T00:00:00Z",
                effective_to="2020-05-01T00:00:00Z",
            ),
        )
    elif case == "schema_event_duplicate":
        _rewrite_csv_and_manifest(
            manifest,
            "events",
            lambda rows: rows.append(
                {
                    **rows[0],
                    "source_ref": "fixture://event/duplicate",
                }
            ),
        )
    elif case == "schema_evaluation_duplicate":
        _rewrite_csv_and_manifest(
            manifest,
            "evaluations",
            lambda rows: rows[1].update(
                evaluation_row_id=rows[0]["evaluation_row_id"],
            ),
        )
    elif case.startswith("lineage_"):
        _mutate_identity_lineage_exclusion(manifest, case)
    elif case == "identity_interval_overlap":
        mutate_identity_membership_case(manifest, "overlapping_identity")
    elif case == "identity_missing":
        mutate_identity_membership_case(manifest, "missing_identity")
    elif case == "membership_interval_inactive":
        mutate_identity_membership_case(
            manifest,
            "membership_outside_interval",
        )
    elif case == "corporate_action_unsupported":
        _rewrite_manifest(
            manifest,
            lambda raw: raw["corporate_action_policy"].update(
                listing="unsupported",
            ),
        )
    elif case == "corporate_action_successor":
        _rewrite_csv_and_manifest(
            manifest,
            "events",
            lambda rows: rows[0].update(
                event_type="merger",
                successor_security_id="",
            ),
        )
    elif case == "delisting_transition":
        _rewrite_csv_and_manifest(
            manifest,
            "events",
            lambda rows: rows[0].update(
                event_type="suspension",
                listing_state_after="active",
            ),
        )
    elif case == "cutoff_after_manifest":
        def add_evaluation(rows):
            rows.append(
                {
                    **rows[-1],
                    "evaluation_row_id": "eval-after-manifest",
                    "evaluation_at": "2022-01-01T00:00:00Z",
                    "available_at": "2022-01-01T00:00:00Z",
                    "source_ref": "fixture://evaluation/after-manifest",
                }
            )

        _rewrite_csv_and_manifest(manifest, "evaluations", add_evaluation)
    elif case == "cutoff_evaluation_unavailable":
        _rewrite_csv_and_manifest(
            manifest,
            "evaluations",
            lambda rows: rows[0].update(
                available_at="2022-01-01T00:00:00Z",
            ),
        )
    elif case == "cutoff_required_scope":
        _rewrite_csv_and_manifest(
            manifest,
            "membership",
            lambda rows: rows[0].update(
                retrieved_at="2022-01-01T00:00:00Z",
            ),
        )
    elif case == "cutoff_later_revision":
        def add_revision(rows):
            rows.append(
                {
                    **rows[0],
                    "membership_row_id": "member-later",
                    "source_ref": "fixture://membership/later",
                    "source_published_at": "2022-01-01T00:00:00Z",
                    "retrieved_at": "2022-01-02T00:00:00Z",
                    "supersedes_membership_row_id": rows[0][
                        "membership_row_id"
                    ],
                }
            )

        _rewrite_csv_and_manifest(manifest, "membership", add_revision)
    elif case == "cutoff_unrelated_scope":
        def add_unrelated(rows):
            rows.append(
                {
                    **rows[0],
                    "identity_row_id": "id-unrelated",
                    "security_id": "sec-unrelated",
                    "issuer_id": "issuer-unrelated",
                    "ticker": "ZZZ",
                    "source_ref": "fixture://identity/unrelated",
                    "source_published_at": "2022-01-01T00:00:00Z",
                    "retrieved_at": "2022-01-02T00:00:00Z",
                    "supersedes_identity_row_id": "",
                }
            )

        _rewrite_csv_and_manifest(
            manifest,
            "security_identity",
            add_unrelated,
        )
    elif case == "partition_assignment":
        _rewrite_csv_and_manifest(
            manifest,
            "evaluations",
            lambda rows: [
                row.update(partition="test")
                for row in rows
            ],
        )
    elif case == "partition_minimum_history":
        _rewrite_manifest(
            manifest,
            lambda raw: raw.update(
                evaluation_policy={
                    "kind": "walk_forward",
                    "minimum_history_count": 2,
                }
            ),
        )
    elif case == "partition_boundary":
        _rewrite_manifest(
            manifest,
            lambda raw: raw.update(
                evaluation_policy={
                    "kind": "train_validation_test",
                    "train_end_at": "2020-06-01T00:00:00Z",
                    "validation_start_at": "2020-08-01T00:00:00Z",
                    "validation_end_at": "2020-09-01T00:00:00Z",
                    "test_start_at": "2020-10-01T00:00:00Z",
                }
            ),
        )
        _rewrite_csv_and_manifest(
            manifest,
            "evaluations",
            lambda rows: [
                row.update(
                    evaluation_at="2020-07-01T00:00:00Z",
                    available_at="2020-07-01T00:00:00Z",
                    partition="train",
                )
                for row in rows
            ],
        )


def mutate_package_for_empty_case(manifest, mutation):
    memberships = _read_contract_rows(manifest, "membership")
    evaluations = _read_contract_rows(manifest, "evaluations")
    raw = json.loads(manifest.read_text())
    if mutation == "no_evaluations":
        _replace_contract_rows(manifest, "evaluations", [])
        return
    if mutation == "benchmark_only":
        memberships = [
            row
            for row in memberships
            if row["universe_kind"] == "benchmark"
        ]
        evaluations = [
            row
            for row in evaluations
            if row["universe_id"] == "bench-1"
        ]
        raw["declared_universes"] = [
            item
            for item in raw["declared_universes"]
            if item["universe_kind"] == "benchmark"
        ]
    elif mutation == "research_only":
        memberships = [
            row
            for row in memberships
            if row["universe_kind"] == "research_universe"
        ]
        evaluations = [
            row
            for row in evaluations
            if row["universe_id"] == "research-1"
        ]
        raw["declared_universes"] = [
            item
            for item in raw["declared_universes"]
            if item["universe_kind"] == "research_universe"
        ]
    elif mutation == "all_excluded":
        for row in memberships:
            row["membership_state"] = "excluded"
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    _replace_contract_rows(manifest, "membership", memberships)
    _replace_contract_rows(manifest, "evaluations", evaluations)


def _append_registry_source(
    registry,
    source_id,
    supported_fields,
    *,
    commercial_use="approved",
):
    fields = ", ".join(supported_fields)
    registry.write_text(
        registry.read_text()
        + (
            f"  - source_id: {source_id}\n"
            f"    display_name: {source_id}\n"
            "    permitted_use: test_only\n"
            f"    commercial_use: {commercial_use}\n"
            "    redistribution: test_only\n"
            "    storage_limits: pytest temporary directory only\n"
            "    attribution: synthetic fixture\n"
            "    rate_limits: not_applicable\n"
            "    authentication: none\n"
            "    expected_freshness: point in time\n"
            f"    supported_fields: [{fields}]\n"
            "    fallback_priority: 2\n"
        ),
        encoding="utf-8",
    )


def test_ticker_change_preserves_security_identity_without_current_ticker_fallback(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def mutate(rows):
        prior = dict(rows[0])
        rows[0]["valid_to"] = "2020-06-01T00:00:00Z"
        rows.append(
            {
                **prior,
                "identity_row_id": "id-2",
                "ticker": "BBB",
                "valid_from": "2020-06-01T00:00:00Z",
                "valid_to": "",
                "source_ref": "fixture://identity/id-2",
                "source_published_at": "2020-06-01T00:00:00Z",
                "retrieved_at": "2020-06-02T00:00:00Z",
                "supersedes_identity_row_id": "id-1",
            }
        )

    _rewrite_csv_and_manifest(manifest, "security_identity", mutate)

    packet = validate_point_in_time_universe(manifest, registry)

    assert packet.decisions["identity_coverage"].status == "passed"
    assert packet.display_tickers == {"sec-1": "BBB"}


def test_same_ticker_for_two_security_ids_does_not_merge_membership(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def mutate(rows):
        rows.append(
            {
                **rows[0],
                "identity_row_id": "id-2",
                "security_id": "sec-2",
                "issuer_id": "issuer-2",
                "source_ref": "fixture://identity/id-2",
            }
        )

    _rewrite_csv_and_manifest(manifest, "security_identity", mutate)

    packet = validate_point_in_time_universe(manifest, registry)

    assert all(digest.member_count == 1 for digest in packet.membership_digests)
    assert packet.display_tickers == {"sec-1": "AAA"}


@pytest.mark.parametrize(
    "case,reason",
    [
        ("overlapping_identity", "identity_interval_overlap"),
        ("missing_identity", "identity_missing"),
        ("membership_outside_interval", "membership_interval_inactive"),
        ("undeclared_universe", "membership_universe_undeclared"),
        ("kind_mismatch", "membership_universe_kind_mismatch"),
    ],
)
def test_identity_and_membership_fail_closed(tmp_path, case, reason):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    mutate_identity_membership_case(manifest, case)

    packet = validate_point_in_time_universe(manifest, registry)

    assert reason in {
        code
        for decision in packet.decisions.values()
        for code in decision.reason_codes
    }
    assert packet.analysis_eligible is False


def mutate_identity_membership_case(manifest, case):
    if case == "overlapping_identity":

        def mutate(rows):
            rows.append(
                {
                    **rows[0],
                    "identity_row_id": "id-overlap",
                    "source_ref": "fixture://identity/id-overlap",
                    "source_published_at": "2020-02-01T00:00:00Z",
                    "retrieved_at": "2020-02-02T00:00:00Z",
                    "supersedes_identity_row_id": "id-1",
                }
            )

        _rewrite_csv_and_manifest(manifest, "security_identity", mutate)
    elif case == "missing_identity":
        _rewrite_csv_and_manifest(
            manifest,
            "membership",
            lambda rows: rows[0].update(security_id="sec-missing"),
        )
    elif case == "membership_outside_interval":
        _rewrite_csv_and_manifest(
            manifest,
            "membership",
            lambda rows: rows[0].update(effective_to="2020-06-01T00:00:00Z"),
        )
    elif case == "undeclared_universe":
        _rewrite_csv_and_manifest(
            manifest,
            "membership",
            lambda rows: rows[0].update(universe_id="unknown"),
        )
    elif case == "kind_mismatch":
        _rewrite_csv_and_manifest(
            manifest,
            "membership",
            lambda rows: rows[0].update(universe_kind="research_universe"),
        )


@pytest.mark.parametrize(
    "case,expected_reason",
    [
        ("membership_security_drift", "lineage_cross_scope_parent"),
        ("membership_duplicate_across_scopes", "lineage_duplicate_id"),
        ("membership_fork_across_scopes", "lineage_fork"),
        ("identity_security_drift", "lineage_cross_scope_parent"),
        ("identity_issuer_drift", "lineage_cross_scope_parent"),
        ("identity_duplicate_across_scopes", "lineage_duplicate_id"),
        ("identity_fork_across_scopes", "lineage_fork"),
        ("corrupt_non_member_identity", "lineage_missing_parent"),
    ],
)
def test_integrated_lineage_validation_precedes_scope_grouping(
    tmp_path,
    case,
    expected_reason,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    mutate_integrated_lineage_case(manifest, case)

    packet = validate_point_in_time_universe(manifest, registry)

    area = (
        "membership_coverage"
        if case.startswith("membership_")
        else "identity_coverage"
    )
    assert expected_reason in _decision(packet, area).reason_codes
    assert _decision(packet, area).status == "blocked"
    assert packet.analysis_eligible is False


def mutate_integrated_lineage_case(manifest, case):
    if case.startswith("membership_"):

        def mutate(rows):
            if case == "membership_security_drift":
                rows.append(
                    {
                        **rows[0],
                        "membership_row_id": "member-drift",
                        "security_id": "sec-2",
                        "source_ref": "fixture://membership/member-drift",
                        "source_published_at": "2020-02-01T00:00:00Z",
                        "retrieved_at": "2020-02-02T00:00:00Z",
                        "supersedes_membership_row_id": rows[0][
                            "membership_row_id"
                        ],
                    }
                )
            elif case == "membership_duplicate_across_scopes":
                rows[1]["membership_row_id"] = rows[0][
                    "membership_row_id"
                ]
            elif case == "membership_fork_across_scopes":
                rows.extend(
                    [
                        {
                            **rows[0],
                            "membership_row_id": "member-child-1",
                            "source_ref": (
                                "fixture://membership/member-child-1"
                            ),
                            "source_published_at": (
                                "2020-02-01T00:00:00Z"
                            ),
                            "retrieved_at": "2020-02-02T00:00:00Z",
                            "supersedes_membership_row_id": rows[0][
                                "membership_row_id"
                            ],
                        },
                        {
                            **rows[0],
                            "membership_row_id": "member-child-2",
                            "security_id": "sec-2",
                            "source_ref": (
                                "fixture://membership/member-child-2"
                            ),
                            "source_published_at": (
                                "2020-03-01T00:00:00Z"
                            ),
                            "retrieved_at": "2020-03-02T00:00:00Z",
                            "supersedes_membership_row_id": rows[0][
                                "membership_row_id"
                            ],
                        },
                    ]
                )

        _rewrite_csv_and_manifest(manifest, "membership", mutate)
        return

    def mutate(rows):
        if case == "identity_security_drift":
            rows.append(
                {
                    **rows[0],
                    "identity_row_id": "id-security-drift",
                    "security_id": "sec-2",
                    "source_ref": "fixture://identity/id-security-drift",
                    "source_published_at": "2020-02-01T00:00:00Z",
                    "retrieved_at": "2020-02-02T00:00:00Z",
                    "supersedes_identity_row_id": "id-1",
                }
            )
        elif case == "identity_issuer_drift":
            rows.append(
                {
                    **rows[0],
                    "identity_row_id": "id-issuer-drift",
                    "issuer_id": "issuer-2",
                    "source_ref": "fixture://identity/id-issuer-drift",
                    "source_published_at": "2020-02-01T00:00:00Z",
                    "retrieved_at": "2020-02-02T00:00:00Z",
                    "supersedes_identity_row_id": "id-1",
                }
            )
        elif case == "identity_duplicate_across_scopes":
            rows.append(
                {
                    **rows[0],
                    "security_id": "sec-2",
                    "issuer_id": "issuer-2",
                    "source_ref": "fixture://identity/id-duplicate",
                }
            )
        elif case == "identity_fork_across_scopes":
            rows.extend(
                [
                    {
                        **rows[0],
                        "identity_row_id": "id-child-1",
                        "source_ref": "fixture://identity/id-child-1",
                        "source_published_at": "2020-02-01T00:00:00Z",
                        "retrieved_at": "2020-02-02T00:00:00Z",
                        "supersedes_identity_row_id": "id-1",
                    },
                    {
                        **rows[0],
                        "identity_row_id": "id-child-2",
                        "security_id": "sec-2",
                        "issuer_id": "issuer-2",
                        "source_ref": "fixture://identity/id-child-2",
                        "source_published_at": "2020-03-01T00:00:00Z",
                        "retrieved_at": "2020-03-02T00:00:00Z",
                        "supersedes_identity_row_id": "id-1",
                    },
                ]
            )
        elif case == "corrupt_non_member_identity":
            rows.append(
                {
                    **rows[0],
                    "identity_row_id": "id-orphan",
                    "security_id": "sec-2",
                    "issuer_id": "issuer-2",
                    "source_ref": "fixture://identity/id-orphan",
                    "supersedes_identity_row_id": "missing",
                }
            )

    _rewrite_csv_and_manifest(manifest, "security_identity", mutate)


@pytest.mark.parametrize(
    "case,identity_reason",
    [
        ("overlapping_identity", "identity_interval_overlap"),
        ("missing_identity", "identity_missing"),
    ],
)
def test_identity_failure_does_not_change_membership_decision_or_digest(
    tmp_path,
    case,
    identity_reason,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    mutate_identity_membership_case(manifest, case)

    packet = validate_point_in_time_universe(manifest, registry)
    digests = _digest_by_universe(packet)

    assert _decision(packet, "identity_coverage").status == "blocked"
    assert identity_reason in _decision(
        packet,
        "identity_coverage",
    ).reason_codes
    assert _decision(packet, "membership_coverage").status == "passed"
    assert _decision(packet, "membership_coverage").reason_codes == ()
    assert digests["bench-1"].member_count == 1
    assert digests["bench-1"].sha256 == _sha256_members(
        "sec-missing" if case == "missing_identity" else "sec-1"
    )
    assert digests["research-1"].member_count == 1
    assert digests["research-1"].sha256 == _sha256_members("sec-1")


def test_invalid_global_membership_lineage_has_no_valid_digest_leaves(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    mutate_integrated_lineage_case(manifest, "membership_security_drift")

    packet = validate_point_in_time_universe(manifest, registry)

    assert "lineage_cross_scope_parent" in _decision(
        packet,
        "membership_coverage",
    ).reason_codes
    assert all(
        digest.member_count == 0
        and digest.sha256 == hashlib.sha256(b"").hexdigest()
        for digest in packet.membership_digests
    )


def test_overlapping_non_member_identity_blocks_identity_coverage(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_overlapping_non_member(rows):
        root = {
            **rows[0],
            "identity_row_id": "id-non-member-root",
            "security_id": "sec-2",
            "issuer_id": "issuer-2",
            "source_ref": "fixture://identity/id-non-member-root",
        }
        rows.extend(
            [
                root,
                {
                    **root,
                    "identity_row_id": "id-non-member-child",
                    "source_ref": "fixture://identity/id-non-member-child",
                    "source_published_at": "2020-02-01T00:00:00Z",
                    "retrieved_at": "2020-02-02T00:00:00Z",
                    "supersedes_identity_row_id": "id-non-member-root",
                },
            ]
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        add_overlapping_non_member,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert "identity_interval_overlap" in _decision(
        packet,
        "identity_coverage",
    ).reason_codes
    assert _decision(packet, "membership_coverage").status == "passed"


def test_same_ticker_membership_keeps_both_stable_security_ids(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_identity(rows):
        rows.append(
            {
                **rows[0],
                "identity_row_id": "id-2",
                "security_id": "sec-2",
                "issuer_id": "issuer-2",
                "source_ref": "fixture://identity/id-2",
            }
        )

    def add_memberships(rows):
        additions = []
        for row in rows:
            additions.append(
                {
                    **row,
                    "membership_row_id": f"{row['membership_row_id']}-sec-2",
                    "security_id": "sec-2",
                    "source_ref": (
                        f"fixture://membership/{row['universe_id']}/sec-2"
                    ),
                }
            )
        rows.extend(additions)

    _rewrite_csv_and_manifest(manifest, "security_identity", add_identity)
    _rewrite_csv_and_manifest(manifest, "membership", add_memberships)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "membership_coverage").status == "passed"
    assert packet.display_tickers == {"sec-1": "AAA", "sec-2": "AAA"}
    for digest in packet.membership_digests:
        assert digest.member_count == 2
        assert digest.sha256 == _sha256_members("sec-1", "sec-2")


def test_excluded_membership_revision_has_exact_empty_digest(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def exclude_benchmark(rows):
        prior = next(row for row in rows if row["universe_id"] == "bench-1")
        prior["effective_to"] = "2020-06-01T00:00:00Z"
        rows.append(
            {
                **prior,
                "membership_row_id": "member-bench-excluded",
                "membership_state": "excluded",
                "effective_from": "2020-06-01T00:00:00Z",
                "effective_to": "",
                "source_ref": "fixture://membership/bench-1/excluded",
                "source_published_at": "2020-06-01T00:00:00Z",
                "retrieved_at": "2020-06-02T00:00:00Z",
                "supersedes_membership_row_id": prior["membership_row_id"],
            }
        )

    _rewrite_csv_and_manifest(manifest, "membership", exclude_benchmark)

    packet = validate_point_in_time_universe(manifest, registry)
    digests = _digest_by_universe(packet)

    assert digests["bench-1"].member_count == 0
    assert digests["bench-1"].sha256 == hashlib.sha256(b"").hexdigest()
    assert digests["research-1"].member_count == 1
    assert digests["research-1"].sha256 == _sha256_members("sec-1")
    assert "membership_no_eligible_members" in _decision(
        packet,
        "membership_coverage",
    ).reason_codes


def test_each_declared_universe_requires_an_eligible_evaluation(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        lambda rows: rows.__setitem__(
            slice(None),
            [row for row in rows if row["universe_id"] == "bench-1"],
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "membership_coverage").status == "blocked"
    assert "membership_no_evaluation" in _decision(
        packet,
        "membership_coverage",
    ).reason_codes


def test_reversed_evaluation_rows_have_canonical_digests_and_latest_ticker(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifests = []
    for name, reverse in (("forward", False), ("reversed", True)):
        root = tmp_path / name
        root.mkdir()
        manifest, registry = build_valid_package(root)

        def change_ticker(rows):
            prior = dict(rows[0])
            rows[0]["valid_to"] = "2020-06-01T00:00:00Z"
            rows.append(
                {
                    **prior,
                    "identity_row_id": "id-2",
                    "ticker": "BBB",
                    "valid_from": "2020-06-01T00:00:00Z",
                    "valid_to": "",
                    "source_ref": "fixture://identity/id-2",
                    "source_published_at": "2020-06-01T00:00:00Z",
                    "retrieved_at": "2020-06-02T00:00:00Z",
                    "supersedes_identity_row_id": "id-1",
                }
            )

        def change_evaluations(rows):
            research = next(
                row for row in rows if row["universe_id"] == "research-1"
            )
            research["evaluation_at"] = "2020-03-01T00:00:00Z"
            research["available_at"] = "2020-03-01T00:00:00Z"
            if reverse:
                rows.reverse()

        _rewrite_csv_and_manifest(
            manifest,
            "security_identity",
            change_ticker,
        )
        _rewrite_csv_and_manifest(
            manifest,
            "evaluations",
            change_evaluations,
        )
        manifests.append((manifest, registry))

    packets = [
        validate_point_in_time_universe(manifest, registry)
        for manifest, registry in manifests
    ]

    assert packets[0].membership_digests == packets[1].membership_digests
    assert tuple(
        digest.universe_id for digest in packets[0].membership_digests
    ) == ("research-1", "bench-1")
    assert packets[0].display_tickers == {"sec-1": "BBB"}
    assert packets[1].display_tickers == {"sec-1": "BBB"}


def test_latest_identity_failure_does_not_fall_back_to_older_ticker(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_later_overlap(rows):
        rows.append(
            {
                **rows[0],
                "identity_row_id": "id-overlap",
                "ticker": "BBB",
                "source_ref": "fixture://identity/id-overlap",
                "source_published_at": "2020-06-01T00:00:00Z",
                "retrieved_at": "2020-06-02T00:00:00Z",
                "supersedes_identity_row_id": "id-1",
            }
        )

    def add_earlier_evaluation(rows):
        research = next(
            row for row in rows if row["universe_id"] == "research-1"
        )
        research["evaluation_at"] = "2020-03-01T00:00:00Z"
        research["available_at"] = "2020-03-01T00:00:00Z"

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        add_later_overlap,
    )
    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        add_earlier_evaluation,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert "identity_interval_overlap" in _decision(
        packet,
        "identity_coverage",
    ).reason_codes
    assert _decision(packet, "membership_coverage").status == "passed"
    assert packet.display_tickers == {}


@pytest.mark.parametrize("top_n", [True, False, -1, 1.5, "1", None])
def test_top_n_rejects_bool_non_integer_and_negative_values(tmp_path, top_n):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    with pytest.raises(ValueError, match="^top_n_invalid$"):
        validate_point_in_time_universe(
            manifest,
            registry,
            top_n=top_n,
        )


def test_top_n_zero_returns_no_excluded_rows(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    mutate_identity_membership_case(manifest, "overlapping_identity")

    packet = validate_point_in_time_universe(
        manifest,
        registry,
        top_n=0,
    )

    assert packet.excluded == ()


def test_excluded_rows_are_canonically_sorted_before_positive_cap(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(ticker=""),
    )

    packet = validate_point_in_time_universe(
        manifest,
        registry,
        top_n=1,
    )

    assert len(packet.excluded) == 1
    assert packet.excluded[0].contract == "membership"
    assert packet.excluded[0].row_id == "member-bench-1"


def test_split_requires_positive_explicit_ratio_and_does_not_rewrite_membership(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def mutate(rows):
        rows[0].update(
            event_type="split",
            ratio_numerator="2",
            ratio_denominator="1",
        )

    _rewrite_csv_and_manifest(manifest, "events", mutate)
    raw = json.loads(manifest.read_text())
    raw["corporate_action_policy"]["listing"] = "not_applicable"
    raw["corporate_action_policy"]["split"] = "required"
    manifest.write_text(json.dumps(raw), encoding="utf-8")

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").area == (
        "corporate_action_coverage"
    )
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").reason_codes == ()
    assert _decision(packet, "delisting_coverage").status == "not_applicable"
    assert packet.membership_digests[0].member_count == 1


def test_reverse_split_has_independent_action_coverage(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        lambda rows: rows[0].update(
            event_type="reverse_split",
            ratio_numerator="1",
            ratio_denominator="10",
        ),
    )

    def require_reverse_split(raw):
        raw["corporate_action_policy"]["listing"] = "not_applicable"
        raw["corporate_action_policy"]["reverse_split"] = "required"

    _rewrite_manifest(manifest, require_reverse_split)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").reason_codes == ()
    assert _decision(packet, "delisting_coverage").status == "not_applicable"
    assert all(digest.member_count == 1 for digest in packet.membership_digests)


def test_delisted_historical_member_is_retained_and_not_filtered_by_current_state(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def mutate(rows):
        rows.append(
            {
                **rows[0],
                "event_row_id": "event-2",
                "event_type": "delisting",
                "effective_at": "2020-06-01T00:00:00Z",
                "listing_state_after": "delisted",
                "source_ref": "fixture://event/event-2",
                "source_published_at": "2020-06-01T00:00:00Z",
                "retrieved_at": "2020-06-02T00:00:00Z",
                "supersedes_event_row_id": "",
            }
        )

    _rewrite_csv_and_manifest(manifest, "events", mutate)
    raw = json.loads(manifest.read_text())
    raw["corporate_action_policy"]["delisting"] = "required"
    manifest.write_text(json.dumps(raw), encoding="utf-8")

    packet = validate_point_in_time_universe(manifest, registry)

    assert all(d.member_count == 1 for d in packet.membership_digests)
    assert packet.decisions["delisting_coverage"].status == "passed"


@pytest.mark.parametrize(
    "event_type,updates,reason,decision_area,sibling_area,sibling_status",
    [
        (
            "merger",
            {"successor_security_id": ""},
            "corporate_action_successor_required",
            "corporate_action_coverage",
            "delisting_coverage",
            "not_applicable",
        ),
        (
            "acquisition",
            {"successor_security_id": ""},
            "corporate_action_successor_required",
            "corporate_action_coverage",
            "delisting_coverage",
            "not_applicable",
        ),
        (
            "spinoff",
            {"successor_security_id": ""},
            "corporate_action_successor_required",
            "corporate_action_coverage",
            "delisting_coverage",
            "not_applicable",
        ),
        (
            "delisting",
            {"listing_state_after": "active"},
            "delisting_state_invalid",
            "delisting_coverage",
            "corporate_action_coverage",
            "passed",
        ),
        (
            "suspension",
            {"listing_state_after": "active"},
            "delisting_transition_invalid",
            "delisting_coverage",
            "corporate_action_coverage",
            "passed",
        ),
        (
            "reactivation",
            {"listing_state_after": "active"},
            "delisting_transition_invalid",
            "delisting_coverage",
            "corporate_action_coverage",
            "passed",
        ),
    ],
)
def test_invalid_action_or_listing_transition_is_blocked(
    tmp_path,
    event_type,
    updates,
    reason,
    decision_area,
    sibling_area,
    sibling_status,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def mutate(rows):
        rows[0].update(event_type=event_type, **updates)

    _rewrite_csv_and_manifest(manifest, "events", mutate)
    raw = json.loads(manifest.read_text())
    raw["corporate_action_policy"]["listing"] = "not_applicable"
    raw["corporate_action_policy"][event_type] = "required"
    manifest.write_text(json.dumps(raw), encoding="utf-8")

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, decision_area).status == "blocked"
    assert reason in _decision(packet, decision_area).reason_codes
    assert _decision(packet, sibling_area).status == sibling_status
    assert reason not in _decision(packet, sibling_area).reason_codes


def test_present_event_marked_unsupported_is_blocked(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    raw = json.loads(manifest.read_text())
    raw["corporate_action_policy"]["listing"] = "unsupported"
    manifest.write_text(json.dumps(raw), encoding="utf-8")

    packet = validate_point_in_time_universe(manifest, registry)

    assert (
        "corporate_action_policy_unsupported"
        in packet.decisions["corporate_action_coverage"].reason_codes
    )
    assert _decision(packet, "delisting_coverage").status == "not_applicable"
    assert _decision(packet, "delisting_coverage").reason_codes == ()


@pytest.mark.parametrize("event_type", ["suspension", "reactivation"])
def test_missing_required_listing_transition_blocks_only_delisting_coverage(
    tmp_path,
    event_type,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            {event_type: "required"}
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").reason_codes == ()
    assert _decision(packet, "delisting_coverage").status == "blocked"
    assert _decision(packet, "delisting_coverage").reason_codes == (
        "delisting_evidence_missing",
    )


def test_suspension_transition_is_delisting_coverage(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_suspension(rows):
        rows.append(
            {
                **rows[0],
                "event_row_id": "event-suspension",
                "event_type": "suspension",
                "effective_at": "2020-02-01T00:00:00Z",
                "listing_state_after": "suspended",
                "source_ref": "fixture://event/event-suspension",
                "source_published_at": "2020-02-01T00:00:00Z",
                "retrieved_at": "2020-02-02T00:00:00Z",
            }
        )

    _rewrite_csv_and_manifest(manifest, "events", add_suspension)
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            {"suspension": "required"}
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "delisting_coverage").status == "passed"
    assert _decision(packet, "delisting_coverage").reason_codes == ()
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").reason_codes == ()


def test_ordered_suspension_reactivation_pair_passes(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_transitions(rows):
        base = rows[0]
        rows.extend(
            [
                {
                    **base,
                    "event_row_id": "event-suspension",
                    "event_type": "suspension",
                    "effective_at": "2020-02-01T00:00:00Z",
                    "listing_state_after": "suspended",
                    "source_ref": "fixture://event/event-suspension",
                    "source_published_at": "2020-02-01T00:00:00Z",
                    "retrieved_at": "2020-02-02T00:00:00Z",
                },
                {
                    **base,
                    "event_row_id": "event-reactivation",
                    "event_type": "reactivation",
                    "effective_at": "2020-03-01T00:00:00Z",
                    "listing_state_after": "active",
                    "source_ref": "fixture://event/event-reactivation",
                    "source_published_at": "2020-03-01T00:00:00Z",
                    "retrieved_at": "2020-03-02T00:00:00Z",
                },
            ]
        )

    _rewrite_csv_and_manifest(manifest, "events", add_transitions)
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            {"suspension": "required", "reactivation": "required"}
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "delisting_coverage").status == "passed"
    assert _decision(packet, "delisting_coverage").reason_codes == ()
    assert _decision(packet, "corporate_action_coverage").status == "passed"


@pytest.mark.parametrize(
    "suspension_row_id,reactivation_row_id",
    [
        ("event-a-suspension", "event-z-reactivation"),
        ("event-z-suspension", "event-a-reactivation"),
    ],
)
def test_same_timestamp_reactivation_is_blocked_regardless_of_row_id_order(
    tmp_path,
    suspension_row_id,
    reactivation_row_id,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_simultaneous_transitions(rows):
        base = rows[0]
        rows.extend(
            [
                {
                    **base,
                    "event_row_id": suspension_row_id,
                    "event_type": "suspension",
                    "effective_at": "2020-02-01T00:00:00Z",
                    "listing_state_after": "suspended",
                    "source_ref": (
                        f"fixture://event/{suspension_row_id}"
                    ),
                    "source_published_at": "2020-02-01T00:00:00Z",
                    "retrieved_at": "2020-02-02T00:00:00Z",
                },
                {
                    **base,
                    "event_row_id": reactivation_row_id,
                    "event_type": "reactivation",
                    "effective_at": "2020-02-01T00:00:00Z",
                    "listing_state_after": "active",
                    "source_ref": (
                        f"fixture://event/{reactivation_row_id}"
                    ),
                    "source_published_at": "2020-02-01T00:00:00Z",
                    "retrieved_at": "2020-02-02T00:00:00Z",
                },
            ]
        )

    _rewrite_csv_and_manifest(
        manifest,
        "events",
        add_simultaneous_transitions,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "delisting_coverage").status == "blocked"
    assert _decision(packet, "delisting_coverage").reason_codes == (
        "delisting_transition_invalid",
    )
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").reason_codes == ()


def test_multiple_reactivation_roots_fail_closed_as_ambiguous_lineage(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_transitions(rows):
        base = rows[0]
        rows.extend(
            [
                {
                    **base,
                    "event_row_id": "event-suspension",
                    "event_type": "suspension",
                    "effective_at": "2020-02-01T00:00:00Z",
                    "listing_state_after": "suspended",
                    "source_ref": "fixture://event/event-suspension",
                    "source_published_at": "2020-02-01T00:00:00Z",
                    "retrieved_at": "2020-02-02T00:00:00Z",
                },
                {
                    **base,
                    "event_row_id": "event-reactivation-1",
                    "event_type": "reactivation",
                    "effective_at": "2020-03-01T00:00:00Z",
                    "listing_state_after": "active",
                    "source_ref": "fixture://event/event-reactivation-1",
                    "source_published_at": "2020-03-01T00:00:00Z",
                    "retrieved_at": "2020-03-02T00:00:00Z",
                },
                {
                    **base,
                    "event_row_id": "event-reactivation-2",
                    "event_type": "reactivation",
                    "effective_at": "2020-04-01T00:00:00Z",
                    "listing_state_after": "active",
                    "source_ref": "fixture://event/event-reactivation-2",
                    "source_published_at": "2020-04-01T00:00:00Z",
                    "retrieved_at": "2020-04-02T00:00:00Z",
                },
            ]
        )

    _rewrite_csv_and_manifest(manifest, "events", add_transitions)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "delisting_coverage").status == "blocked"
    assert _decision(packet, "delisting_coverage").reason_codes == (
        "lineage_multiple_roots",
    )
    assert _decision(packet, "corporate_action_coverage").status == "passed"


def test_intervening_active_transition_invalidates_later_reactivation(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_transitions(rows):
        base = rows[0]
        rows.extend(
            [
                {
                    **base,
                    "event_row_id": "event-suspension",
                    "event_type": "suspension",
                    "effective_at": "2020-02-01T00:00:00Z",
                    "listing_state_after": "suspended",
                    "source_ref": "fixture://event/event-suspension",
                    "source_published_at": "2020-02-01T00:00:00Z",
                    "retrieved_at": "2020-02-02T00:00:00Z",
                },
                {
                    **base,
                    "event_row_id": "event-active",
                    "event_type": "listing",
                    "effective_at": "2020-03-01T00:00:00Z",
                    "listing_state_after": "active",
                    "source_ref": "fixture://event/event-active",
                    "source_published_at": "2020-03-01T00:00:00Z",
                    "retrieved_at": "2020-03-02T00:00:00Z",
                    "supersedes_event_row_id": "event-1",
                },
                {
                    **base,
                    "event_row_id": "event-reactivation",
                    "event_type": "reactivation",
                    "effective_at": "2020-04-01T00:00:00Z",
                    "listing_state_after": "active",
                    "source_ref": "fixture://event/event-reactivation",
                    "source_published_at": "2020-04-01T00:00:00Z",
                    "retrieved_at": "2020-04-02T00:00:00Z",
                },
            ]
        )

    _rewrite_csv_and_manifest(manifest, "events", add_transitions)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "delisting_coverage").status == "blocked"
    assert _decision(packet, "delisting_coverage").reason_codes == (
        "delisting_transition_invalid",
    )
    assert _decision(packet, "corporate_action_coverage").status == "passed"


def test_superseded_invalid_event_root_does_not_affect_coverage(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def replace_with_revision(rows):
        rows[0].update(
            event_type="suspension",
            listing_state_after="active",
            effective_at="2020-02-01T00:00:00Z",
            source_published_at="2020-02-01T00:00:00Z",
            retrieved_at="2020-02-02T00:00:00Z",
        )
        rows.append(
            {
                **rows[0],
                "event_row_id": "event-suspension-revision",
                "listing_state_after": "suspended",
                "source_ref": "fixture://event/suspension-revision",
                "source_published_at": "2020-03-01T00:00:00Z",
                "retrieved_at": "2020-03-02T00:00:00Z",
                "supersedes_event_row_id": rows[0]["event_row_id"],
            }
        )

    _rewrite_csv_and_manifest(manifest, "events", replace_with_revision)
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            {"listing": "not_applicable", "suspension": "required"}
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "delisting_coverage").status == "passed"
    assert _decision(packet, "delisting_coverage").reason_codes == ()
    assert not any(
        row.row_id == "event-1"
        and "delisting_transition_invalid" in row.reason_codes
        for row in packet.excluded
    )


def test_cutoff_visible_event_revision_is_consumed_leaf(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def replace_with_revision(rows):
        rows[0].update(
            event_type="merger",
            successor_security_id="",
        )
        rows.append(
            {
                **rows[0],
                "event_row_id": "event-merger-revision",
                "successor_security_id": "sec-successor",
                "source_ref": "fixture://event/merger-revision",
                "source_published_at": "2020-02-01T00:00:00Z",
                "retrieved_at": "2020-02-02T00:00:00Z",
                "supersedes_event_row_id": rows[0]["event_row_id"],
            }
        )

    _rewrite_csv_and_manifest(manifest, "events", replace_with_revision)
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            {"listing": "not_applicable", "merger": "required"}
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").reason_codes == ()


def test_post_evaluation_invalid_reactivation_does_not_poison_prior_cutoff(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_events(rows):
        rows.append(
            {
                **rows[0],
                "event_row_id": "event-suspension",
                "event_type": "suspension",
                "effective_at": "2020-02-01T00:00:00Z",
                "listing_state_after": "suspended",
                "source_ref": "fixture://event/suspension",
                "source_published_at": "2020-02-01T00:00:00Z",
                "retrieved_at": "2020-02-02T00:00:00Z",
            }
        )
        rows.append(
            {
                **rows[0],
                "event_row_id": "event-future-invalid-reactivation",
                "event_type": "reactivation",
                "effective_at": "2020-03-01T00:00:00Z",
                "listing_state_after": "suspended",
                "source_ref": "fixture://event/future-reactivation",
                "source_published_at": "2022-01-01T00:00:00Z",
                "retrieved_at": "2022-01-02T00:00:00Z",
            }
        )

    _rewrite_csv_and_manifest(manifest, "events", add_events)
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            {"suspension": "required"}
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "delisting_coverage").status == "passed"
    assert _decision(packet, "delisting_coverage").reason_codes == ()
    assert {
        row.row_id: row.reason_codes
        for row in packet.excluded
        if row.row_id == "event-future-invalid-reactivation"
    } == {
        "event-future-invalid-reactivation": (
            "cutoff_unrelated_scope_invisible",
        )
    }


@pytest.mark.parametrize(
    "mutation,expected_reason,decision_area",
    [
        ("missing_parent", "lineage_missing_parent", "corporate_action_coverage"),
        ("fork", "lineage_fork", "corporate_action_coverage"),
        ("cycle", "lineage_cycle", "corporate_action_coverage"),
        ("cross_scope", "lineage_cross_scope_parent", "delisting_coverage"),
        ("reversed", "lineage_order_reversed", "corporate_action_coverage"),
    ],
)
def test_event_lineage_failures_block_through_public_validator(
    tmp_path,
    mutation,
    expected_reason,
    decision_area,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def mutate(rows):
        base = rows[0]
        if mutation == "missing_parent":
            base["supersedes_event_row_id"] = "missing-event"
        elif mutation == "fork":
            for suffix, month in (("a", "02"), ("b", "03")):
                rows.append(
                    {
                        **base,
                        "event_row_id": f"event-child-{suffix}",
                        "source_ref": f"fixture://event/child-{suffix}",
                        "source_published_at": (
                            f"2020-{month}-01T00:00:00Z"
                        ),
                        "retrieved_at": f"2020-{month}-02T00:00:00Z",
                        "supersedes_event_row_id": base["event_row_id"],
                    }
                )
        elif mutation == "cycle":
            base["supersedes_event_row_id"] = "event-cycle"
            rows.append(
                {
                    **base,
                    "event_row_id": "event-cycle",
                    "source_ref": "fixture://event/cycle",
                    "source_published_at": "2020-02-01T00:00:00Z",
                    "retrieved_at": "2020-02-02T00:00:00Z",
                    "supersedes_event_row_id": "event-1",
                }
            )
        elif mutation == "cross_scope":
            rows.append(
                {
                    **base,
                    "event_row_id": "event-cross-scope",
                    "event_type": "suspension",
                    "listing_state_after": "suspended",
                    "source_ref": "fixture://event/cross-scope",
                    "source_published_at": "2020-02-01T00:00:00Z",
                    "retrieved_at": "2020-02-02T00:00:00Z",
                    "supersedes_event_row_id": "event-1",
                }
            )
        elif mutation == "reversed":
            rows.append(
                {
                    **base,
                    "event_row_id": "event-reversed",
                    "source_ref": "fixture://event/reversed",
                    "source_published_at": "2020-01-01T00:00:00Z",
                    "retrieved_at": "2020-01-01T00:00:00Z",
                    "supersedes_event_row_id": "event-1",
                }
            )

    _rewrite_csv_and_manifest(manifest, "events", mutate)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, decision_area).status == "blocked"
    assert expected_reason in _decision(
        packet,
        decision_area,
    ).reason_codes
    assert any(
        expected_reason in row.reason_codes
        for row in packet.excluded
        if row.contract == "events"
    )
    assert packet.analysis_eligible is False


def test_duplicate_event_row_ids_are_globally_excluded(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def duplicate(rows):
        rows.append(
            {
                **rows[0],
                "security_id": "sec-duplicate",
                "source_ref": "fixture://event/duplicate",
                "source_published_at": "2022-01-01T00:00:00Z",
                "retrieved_at": "2022-01-02T00:00:00Z",
            }
        )

    _rewrite_csv_and_manifest(manifest, "events", duplicate)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "technical_validity").status == "blocked"
    assert _decision(packet, "technical_validity").reason_codes == (
        "schema_event_row_id_duplicate",
    )
    duplicate_exclusions = [
        row
        for row in packet.excluded
        if row.contract == "events" and row.row_id == "event-1"
    ]
    assert len(duplicate_exclusions) == 2
    assert all(
        row.reason_codes == ("schema_event_row_id_duplicate",)
        for row in duplicate_exclusions
    )
    assert packet.analysis_eligible is False


def test_event_lineage_aggregates_across_cutoffs_and_canonicalizes_exclusions(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_later_fork(rows):
        base = rows[0]
        for suffix, month in (("a", "01"), ("b", "02")):
            rows.append(
                {
                    **base,
                    "event_row_id": f"event-later-child-{suffix}",
                    "source_ref": f"fixture://event/later-child-{suffix}",
                    "source_published_at": (
                        f"2022-{month}-01T00:00:00Z"
                    ),
                    "retrieved_at": f"2022-{month}-02T00:00:00Z",
                    "supersedes_event_row_id": base["event_row_id"],
                }
            )

    def add_later_evaluations(rows):
        rows.extend(
            {
                **row,
                "evaluation_row_id": (
                    f"{row['evaluation_row_id']}-later"
                ),
                "evaluation_at": "2023-01-01T00:00:00Z",
                "available_at": "2023-01-01T00:00:00Z",
                "source_ref": f"{row['source_ref']}/later",
            }
            for row in list(rows)
        )

    _rewrite_csv_and_manifest(manifest, "events", add_later_fork)
    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        add_later_evaluations,
    )
    _rewrite_manifest(
        manifest,
        lambda raw: raw.update(
            observation_cutoff_at="2023-01-01T00:00:00Z",
        ),
    )

    packet = validate_point_in_time_universe(
        manifest,
        registry,
        top_n=100,
    )

    assert _decision(packet, "corporate_action_coverage").status == "blocked"
    assert "lineage_fork" in _decision(
        packet,
        "corporate_action_coverage",
    ).reason_codes
    later_child_exclusions = [
        row
        for row in packet.excluded
        if row.row_id == "event-later-child-a"
    ]
    assert len(later_child_exclusions) == 1
    assert later_child_exclusions[0].reason_codes == (
        "cutoff_later_revision_invisible",
        "lineage_fork",
    )


def test_unrelated_security_event_cannot_satisfy_member_event_coverage(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        lambda rows: rows[0].update(
            security_id="sec-unrelated",
            source_ref="fixture://event/unrelated-security",
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "membership_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "blocked"
    assert _decision(
        packet,
        "corporate_action_coverage",
    ).reason_codes == ("corporate_action_evidence_missing",)
    assert packet.analysis_eligible is False


def test_partition_invalid_evaluation_is_not_an_event_cutoff(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_invalid_evaluation(rows):
        rows.append(
            {
                **rows[0],
                "evaluation_row_id": "eval-invalid-partition",
                "evaluation_at": "2019-01-01T00:00:00Z",
                "available_at": "2019-01-01T00:00:00Z",
                "partition": "test",
                "source_ref": "fixture://evaluation/invalid-partition",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        add_invalid_evaluation,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "leakage_safe").status == "blocked"
    assert "partition_assignment_invalid" in _decision(
        packet,
        "leakage_safe",
    ).reason_codes
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").reason_codes == ()


def test_no_valid_evaluation_fails_required_event_coverage_closed(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _replace_contract_rows(manifest, "evaluations", [])

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "membership_coverage").status == "blocked"
    assert _decision(packet, "corporate_action_coverage").status == "blocked"
    assert _decision(
        packet,
        "corporate_action_coverage",
    ).reason_codes == ("corporate_action_evidence_missing",)
    assert packet.analysis_eligible is False


@pytest.mark.parametrize(
    "listing_row_id,suspension_row_id",
    [
        ("event-a-listing", "event-z-suspension"),
        ("event-z-listing", "event-a-suspension"),
    ],
)
def test_simultaneous_conflicting_listing_states_fail_closed_independent_of_ids(
    tmp_path,
    listing_row_id,
    suspension_row_id,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_conflicting_transitions(rows):
        rows[0].update(event_row_id=listing_row_id)
        base = rows[0]
        rows.extend(
            [
                {
                    **base,
                    "event_row_id": suspension_row_id,
                    "event_type": "suspension",
                    "listing_state_after": "suspended",
                    "source_ref": (
                        f"fixture://event/{suspension_row_id}"
                    ),
                },
                {
                    **base,
                    "event_row_id": "event-reactivation",
                    "event_type": "reactivation",
                    "effective_at": "2020-02-01T00:00:00Z",
                    "listing_state_after": "active",
                    "source_ref": "fixture://event/reactivation",
                    "source_published_at": "2020-02-01T00:00:00Z",
                    "retrieved_at": "2020-02-02T00:00:00Z",
                },
            ]
        )

    _rewrite_csv_and_manifest(
        manifest,
        "events",
        add_conflicting_transitions,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert _decision(packet, "delisting_coverage").status == "blocked"
    assert _decision(packet, "delisting_coverage").reason_codes == (
        "delisting_transition_invalid",
    )
    assert packet.analysis_eligible is False


def test_technical_pass_does_not_promote_unverified_rights(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    registry.write_text(
        registry.read_text().replace(
            "commercial_use: approved",
            "commercial_use: unverified",
        ),
        encoding="utf-8",
    )
    raw = json.loads(manifest.read_text())
    raw["source_rights_registry_sha256"] = hashlib.sha256(
        registry.read_bytes()
    ).hexdigest()
    manifest.write_text(json.dumps(raw), encoding="utf-8")

    packet = validate_point_in_time_universe(manifest, registry)

    assert packet.decisions["technical_validity"].status == "passed"
    assert packet.decisions["source_rights_eligibility"].status == "blocked"
    assert packet.decisions["source_rights_eligibility"].reason_codes == (
        "source_rights_commercial_rights_unverified",
    )
    assert packet.decisions["corporate_action_coverage"].status == "passed"
    assert packet.decisions["delisting_coverage"].status == "not_applicable"
    assert packet.analysis_eligible is False


@pytest.mark.parametrize(
    "contract,missing_scope,event_type,expected_delisting_status",
    [
        ("security_identity", "security_identity", None, "not_applicable"),
        ("membership", "universe_membership", None, "not_applicable"),
        ("events", "corporate_actions", "listing", "not_applicable"),
        ("events", "delistings", "delisting", "passed"),
    ],
)
def test_exact_source_scope_mapping_blocks_only_rights_state(
    tmp_path,
    contract,
    missing_scope,
    event_type,
    expected_delisting_status,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    source_id = f"{missing_scope}_source"

    def isolate_source(rows):
        for row in rows:
            row["source_id"] = source_id
        if event_type == "delisting":
            rows[0].update(
                event_type="delisting",
                listing_state_after="delisted",
            )

    _rewrite_csv_and_manifest(
        manifest,
        contract,
        isolate_source,
    )
    all_scopes = (
        "security_identity",
        "universe_membership",
        "corporate_actions",
        "delistings",
    )
    _append_registry_source(
        registry,
        source_id,
        tuple(scope for scope in all_scopes if scope != missing_scope),
    )

    def allow_isolated_source(raw):
        raw["allowed_source_ids"].append(source_id)
        if event_type == "delisting":
            raw["corporate_action_policy"]["listing"] = "not_applicable"
            raw["corporate_action_policy"]["delisting"] = "required"

    _rewrite_manifest(manifest, allow_isolated_source)
    _refresh_registry_digest(manifest, registry)

    packet = validate_point_in_time_universe(manifest, registry)

    assert packet.decisions["technical_validity"].status == "passed"
    assert packet.decisions["identity_coverage"].status == "passed"
    assert packet.decisions["membership_coverage"].status == "passed"
    assert packet.decisions["corporate_action_coverage"].status == "passed"
    assert (
        packet.decisions["delisting_coverage"].status
        == expected_delisting_status
    )
    assert packet.decisions["source_rights_eligibility"].status == "blocked"
    assert packet.decisions["source_rights_eligibility"].reason_codes == (
        "source_rights_field_scope_missing",
    )
    assert packet.analysis_eligible is False


def test_allowed_unknown_source_has_exact_rights_reasons(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(source_id="unknown_source"),
    )
    _rewrite_manifest(
        manifest,
        lambda raw: raw["allowed_source_ids"].append("unknown_source"),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert packet.decisions["technical_validity"].status == "passed"
    assert packet.decisions["identity_coverage"].status == "passed"
    assert packet.decisions["source_rights_eligibility"].status == "blocked"
    assert packet.decisions["source_rights_eligibility"].reason_codes == (
        "source_rights_field_scope_missing",
        "source_rights_unknown_source",
    )
    assert packet.decisions["corporate_action_coverage"].status == "passed"
    assert packet.decisions["delisting_coverage"].status == "not_applicable"


def test_registered_approved_source_not_in_allowlist_is_blocked_exactly(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    source_id = "registered_but_not_allowed"
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(source_id=source_id),
    )
    _append_registry_source(
        registry,
        source_id,
        ("security_identity",),
    )
    _refresh_registry_digest(manifest, registry)

    packet = validate_point_in_time_universe(manifest, registry)

    assert packet.decisions["technical_validity"].status == "passed"
    assert packet.decisions["identity_coverage"].status == "passed"
    assert packet.decisions["source_rights_eligibility"].status == "blocked"
    assert packet.decisions["source_rights_eligibility"].reason_codes == (
        "source_rights_source_not_allowed",
    )
    assert packet.decisions["corporate_action_coverage"].status == "passed"
    assert packet.decisions["delisting_coverage"].status == "not_applicable"


@pytest.mark.parametrize(
    "contract,column",
    [
        ("security_identity", "source_published_at"),
        ("security_identity", "retrieved_at"),
        ("membership", "observation_at"),
        ("membership", "source_published_at"),
        ("membership", "retrieved_at"),
        ("events", "effective_at"),
        ("events", "source_published_at"),
        ("events", "retrieved_at"),
    ],
)
def test_post_cutoff_evidence_is_excluded_without_poisoning_independent_states(
    tmp_path,
    contract,
    column,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        contract,
        lambda rows: rows[0].update(
            {column: "2022-01-01T00:00:00Z"}
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "temporal_validity").status == "blocked"
    assert _decision(packet, "leakage_safe").status == "blocked"
    assert "leakage_post_cutoff_evidence" in _decision(
        packet,
        "leakage_safe",
    ).reason_codes
    assert any(
        row.contract == contract
        and "leakage_post_cutoff_evidence" in row.reason_codes
        for row in packet.excluded
    )
    for independent in (
        "technical_validity",
        "identity_coverage",
        "membership_coverage",
        "source_rights_eligibility",
    ):
        assert _decision(packet, independent).status == "passed"
    if contract == "events":
        assert _decision(
            packet,
            "corporate_action_coverage",
        ).reason_codes == ("corporate_action_evidence_missing",)
    else:
        assert _decision(
            packet,
            "corporate_action_coverage",
        ).status == "passed"
    assert _decision(packet, "delisting_coverage").status == "not_applicable"
    assert packet.analysis_eligible is False


def test_later_revision_is_invisible_at_earlier_evaluation(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_later_revision(rows):
        rows.append(
            {
                **rows[0],
                "membership_row_id": "member-late",
                "membership_state": "excluded",
                "source_ref": "fixture://membership/late",
                "source_published_at": "2022-01-01T00:00:00Z",
                "retrieved_at": "2022-01-02T00:00:00Z",
                "supersedes_membership_row_id": rows[0][
                    "membership_row_id"
                ],
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "membership",
        add_later_revision,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _digest_by_universe(packet)["bench-1"].member_count == 1
    assert _digest_by_universe(packet)["research-1"].member_count == 1
    assert _decision(packet, "temporal_validity").status == "passed"
    assert _decision(packet, "leakage_safe").status == "passed"
    assert next(
        row
        for row in packet.excluded
        if row.row_id == "member-late"
    ).reason_codes == ("cutoff_later_revision_invisible",)
    assert packet.analysis_eligible is True


def test_repeated_validation_reproduces_all_canonical_outputs(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    first = validate_point_in_time_universe(manifest, registry)
    second = validate_point_in_time_universe(manifest, registry)

    assert first.membership_digests == second.membership_digests
    assert first.decisions == second.decisions
    assert first.excluded == second.excluded
    assert tuple(first.decisions) == (
        "manifest_integrity",
        "technical_validity",
        "temporal_validity",
        "identity_coverage",
        "membership_coverage",
        "corporate_action_coverage",
        "delisting_coverage",
        "source_rights_eligibility",
        "reproduction_ready",
        "leakage_safe",
    )
    assert {
        digest.universe_id: digest.member_count
        for digest in first.membership_digests
    } == {"bench-1": 1, "research-1": 1}
    assert {
        digest.universe_id: digest.sha256
        for digest in first.membership_digests
    } == {
        "bench-1": _sha256_members("sec-1"),
        "research-1": _sha256_members("sec-1"),
    }
    assert all(
        decision.reason_codes
        == tuple(sorted(set(decision.reason_codes)))
        for decision in first.decisions.values()
    )
    assert all(
        row.reason_codes == tuple(sorted(set(row.reason_codes)))
        for row in first.excluded
    )


@pytest.mark.parametrize(
    "policy,reason",
    [
        (
            {
                "kind": "train_validation_test",
                "train_end_at": "2020-07-01T00:00:00Z",
                "validation_start_at": "2020-06-01T00:00:00Z",
                "validation_end_at": "2020-09-01T00:00:00Z",
                "test_start_at": "2020-10-01T00:00:00Z",
            },
            "partition_overlap",
        ),
        (
            {
                "kind": "train_validation_test",
                "train_end_at": "2020-06-01T00:00:00Z",
                "validation_start_at": "2020-07-01T00:00:00Z",
                "validation_end_at": "2020-05-01T00:00:00Z",
                "test_start_at": "2020-10-01T00:00:00Z",
            },
            "partition_order_invalid",
        ),
        (
            {"kind": "train_validation_test"},
            "partition_schema_invalid",
        ),
        (
            {"kind": "walk_forward", "minimum_history_count": 0},
            "partition_minimum_history_invalid",
        ),
    ],
)
def test_partition_policy_failures_are_canonical_and_fail_closed(
    policy,
    reason,
):
    from src.point_in_time_universe import _partition_decision

    decision = _partition_decision(
        SimpleNamespace(evaluation_policy=policy),
        (),
    )

    assert decision.area == "leakage_safe"
    assert decision.status == "blocked"
    assert reason in decision.reason_codes
    assert decision.reason_codes == tuple(sorted(set(decision.reason_codes)))


@pytest.mark.parametrize(
    "contract,digests,reason",
    [
        (
            "unsupported_v2",
            (),
            "reproduction_contract_unsupported",
        ),
        (
            "membership_count_and_sha256_at_cutoff_v1",
            (
                ("bench-1", "2021-01-01T00:00:00Z", 1, "a" * 64),
                ("bench-1", "2021-01-01T00:00:00Z", 1, "b" * 64),
            ),
            "reproduction_duplicate_evaluation",
        ),
        (
            "membership_count_and_sha256_at_cutoff_v1",
            (
                ("bench-1", "2021-01-01T00:00:00Z", 1, "g" * 64),
            ),
            "reproduction_digest_invalid",
        ),
    ],
)
def test_reproduction_failures_block_independently(
    contract,
    digests,
    reason,
):
    from src.point_in_time_universe import (
        MembershipDigest,
        _reproduction_decision,
    )

    decision = _reproduction_decision(
        SimpleNamespace(reproduction_contract=contract),
        tuple(MembershipDigest(*digest) for digest in digests),
    )

    assert decision.area == "reproduction_ready"
    assert decision.status == "blocked"
    assert decision.reason_codes == (reason,)


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("no_evaluations", "membership_no_evaluation"),
        ("benchmark_only", "membership_research_universe_missing"),
        ("research_only", "membership_benchmark_missing"),
        ("all_excluded", "membership_no_eligible_members"),
    ],
)
def test_empty_or_one_sided_packages_fail_closed(tmp_path, mutation, reason):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    mutate_package_for_empty_case(manifest, mutation)

    packet = validate_point_in_time_universe(manifest, registry)

    assert packet.analysis_eligible is False
    assert reason in {
        code
        for decision in packet.decisions.values()
        for code in decision.reason_codes
    }


def test_valid_fixture_passes_all_decisions_and_is_analysis_eligible(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    packet = validate_point_in_time_universe(manifest, registry)

    assert tuple(packet.decisions) == (
        "manifest_integrity",
        "technical_validity",
        "temporal_validity",
        "identity_coverage",
        "membership_coverage",
        "corporate_action_coverage",
        "delisting_coverage",
        "source_rights_eligibility",
        "reproduction_ready",
        "leakage_safe",
    )
    assert {
        area: decision.status
        for area, decision in packet.decisions.items()
    } == {
        "manifest_integrity": "passed",
        "technical_validity": "passed",
        "temporal_validity": "passed",
        "identity_coverage": "passed",
        "membership_coverage": "passed",
        "corporate_action_coverage": "passed",
        "delisting_coverage": "not_applicable",
        "source_rights_eligibility": "passed",
        "reproduction_ready": "passed",
        "leakage_safe": "passed",
    }
    assert packet.analysis_eligible is True


def test_every_emitted_exclusion_uses_an_approved_stable_reason(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    observed_by_case = {}
    for case in EXCLUSION_MUTATION_CASES:
        case_root = tmp_path / case
        case_root.mkdir()
        manifest, registry = build_valid_package(case_root)
        _mutate_exclusion_case(manifest, case)
        packet = validate_point_in_time_universe(
            manifest,
            registry,
            top_n=1000,
        )
        observed_by_case[case] = {
            code
            for item in packet.excluded
            for code in item.reason_codes
        }

    observed = set().union(*observed_by_case.values())
    observed_prefixes = {
        prefix
        for prefix in EXPECTED_REASON_PREFIXES
        if any(code.startswith(prefix) for code in observed)
    }

    assert all(observed_by_case.values())
    assert observed == EXPECTED_EXCLUSION_CODES
    assert observed_prefixes == EXPECTED_EXCLUSION_PREFIXES
    assert all(
        any(code.startswith(prefix) for prefix in EXPECTED_REASON_PREFIXES)
        for code in observed
    )


def test_source_rights_reasons_are_decision_only_not_fabricated_exclusions(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    registry.write_text(
        registry.read_text(encoding="utf-8").replace(
            "commercial_use: approved",
            "commercial_use: unverified",
        ),
        encoding="utf-8",
    )
    _refresh_registry_digest(manifest, registry)

    packet = validate_point_in_time_universe(manifest, registry)

    assert packet.decisions["source_rights_eligibility"].reason_codes == (
        "source_rights_commercial_rights_unverified",
    )
    assert all(
        not code.startswith("source_rights_")
        for item in packet.excluded
        for code in item.reason_codes
    )


def test_validator_result_is_unchanged_when_current_universe_files_change(
    tmp_path,
    monkeypatch,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    monkeypatch.chdir(tmp_path)
    first = validate_point_in_time_universe(manifest, registry)
    data = tmp_path / "data"
    data.mkdir()
    current = data / "universe.csv"
    master = data / "universe_master.csv"
    current.write_text("ticker\nZZZ\n", encoding="utf-8")
    master.write_text(
        "ticker,is_active_listing\nAAA,false\n",
        encoding="utf-8",
    )
    after_add = validate_point_in_time_universe(manifest, registry)
    current.write_text("ticker\nAAA\nBBB\n", encoding="utf-8")
    master.write_text(
        "ticker,is_active_listing\nZZZ,true\n",
        encoding="utf-8",
    )
    after_change = validate_point_in_time_universe(manifest, registry)

    assert first == after_add == after_change


def test_validator_uses_verified_contract_bytes_when_path_changes_after_load(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe as universe_module

    manifest, registry = build_valid_package(tmp_path)
    real_load = universe_module.load_universe_package

    def load_then_replace_contract(manifest_path, registry_path):
        package = real_load(manifest_path, registry_path)
        identity_path = package.files["security_identity"]
        identity_path.write_text(
            identity_path.read_text(encoding="utf-8").replace(",AAA,", ",RACED,"),
            encoding="utf-8",
        )
        return package

    monkeypatch.setattr(
        universe_module,
        "load_universe_package",
        load_then_replace_contract,
    )

    packet = universe_module.validate_point_in_time_universe(manifest, registry)

    assert packet.decisions["manifest_integrity"].status == "passed"
    assert packet.display_tickers["sec-1"] == "AAA"
    assert "RACED" not in packet.display_tickers.values()


def test_validator_uses_verified_registry_bytes_when_path_changes_after_load(
    tmp_path,
    monkeypatch,
):
    import src.point_in_time_universe as universe_module

    manifest, registry = build_valid_package(tmp_path)
    real_load = universe_module.load_universe_package

    def load_then_replace_registry(manifest_path, registry_path):
        package = real_load(manifest_path, registry_path)
        registry.write_text(
            registry.read_text(encoding="utf-8").replace(
                "commercial_use: approved",
                "commercial_use: unverified",
            ),
            encoding="utf-8",
        )
        return package

    monkeypatch.setattr(
        universe_module,
        "load_universe_package",
        load_then_replace_registry,
    )

    packet = universe_module.validate_point_in_time_universe(manifest, registry)

    assert packet.decisions["manifest_integrity"].status == "passed"
    assert packet.decisions["source_rights_eligibility"].status == "passed"
    assert not packet.decisions["source_rights_eligibility"].reason_codes


def test_blocked_independent_decision_prevents_final_eligibility(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    registry.write_text(
        registry.read_text().replace(
            "commercial_use: approved",
            "commercial_use: unverified",
        ),
        encoding="utf-8",
    )
    _refresh_registry_digest(manifest, registry)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "source_rights_eligibility").status == "blocked"
    assert _decision(packet, "delisting_coverage").status == "not_applicable"
    assert packet.analysis_eligible is False


def test_not_applicable_is_accepted_only_for_delisting_contract(tmp_path):
    from src.point_in_time_universe import (
        Decision,
        _final_eligibility,
        validate_point_in_time_universe,
    )

    manifest, registry = build_valid_package(tmp_path)
    packet = validate_point_in_time_universe(manifest, registry)
    decisions = dict(packet.decisions)
    decisions["temporal_validity"] = Decision(
        "temporal_validity",
        "not_applicable",
        (),
    )
    declared = json.loads(manifest.read_text())["declared_universes"]

    assert _decision(packet, "delisting_coverage").status == "not_applicable"
    assert packet.analysis_eligible is True
    assert _final_eligibility(
        decisions,
        packet.membership_digests,
        declared,
    ) is False


def test_evaluation_after_manifest_cutoff_is_classified_not_silently_dropped(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_post_manifest_evaluation(rows):
        rows.append(
            {
                **rows[-1],
                "evaluation_row_id": "eval-after-manifest-cutoff",
                "evaluation_at": "2022-01-01T00:00:00Z",
                "available_at": "2022-01-01T00:00:00Z",
                "source_ref": "fixture://evaluation/after-manifest-cutoff",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        add_post_manifest_evaluation,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "temporal_validity").status == "blocked"
    assert _decision(packet, "temporal_validity").reason_codes == (
        "cutoff_evaluation_after_manifest",
    )
    assert _decision(packet, "leakage_safe").status == "blocked"
    assert (
        "leakage_evaluation_after_manifest_cutoff"
        in _decision(packet, "leakage_safe").reason_codes
    )
    assert _decision(packet, "reproduction_ready").status == "blocked"
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_evaluation_after_manifest_cutoff",
    )
    assert any(
        row.contract == "evaluations"
        and row.row_id == "eval-after-manifest-cutoff"
        and row.reason_codes
        == (
            "cutoff_evaluation_after_manifest",
            "leakage_evaluation_after_manifest_cutoff",
            "reproduction_evaluation_after_manifest_cutoff",
        )
        for row in packet.excluded
    )
    assert tuple(
        digest.universe_id
        for digest in packet.membership_digests
    ) == ("bench-1", "research-1")
    assert packet.analysis_eligible is False


def test_walk_forward_policy_rejects_non_walk_forward_evaluation_rows(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        lambda rows: [
            row.update(partition="test")
            for row in rows
        ],
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "leakage_safe").status == "blocked"
    assert _decision(packet, "leakage_safe").reason_codes == (
        "partition_assignment_invalid",
    )
    assert {
        row.row_id: row.reason_codes
        for row in packet.excluded
        if row.contract == "evaluations"
    } == {
        "eval-bench-1": ("partition_assignment_invalid",),
        "eval-research-1": ("partition_assignment_invalid",),
    }
    assert packet.analysis_eligible is False


def test_train_validation_test_policy_enforces_row_time_boundaries(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_manifest(
        manifest,
        lambda raw: raw.update(
            evaluation_policy={
                "kind": "train_validation_test",
                "train_end_at": "2020-06-01T00:00:00Z",
                "validation_start_at": "2020-08-01T00:00:00Z",
                "validation_end_at": "2021-06-01T00:00:00Z",
                "test_start_at": "2021-08-01T00:00:00Z",
            }
        ),
    )
    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        lambda rows: [
            row.update(
                evaluation_at="2020-07-01T00:00:00Z",
                available_at="2020-07-01T00:00:00Z",
                partition="train",
            )
            for row in rows
        ],
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "leakage_safe").status == "blocked"
    assert _decision(packet, "leakage_safe").reason_codes == (
        "partition_boundary_unassigned",
    )
    assert all(
        row.reason_codes == ("partition_boundary_unassigned",)
        for row in packet.excluded
        if row.contract == "evaluations"
    )
    assert packet.analysis_eligible is False


def test_train_validation_test_policy_rejects_wrong_row_assignment(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_manifest(
        manifest,
        lambda raw: raw.update(
            evaluation_policy={
                "kind": "train_validation_test",
                "train_end_at": "2020-06-01T00:00:00Z",
                "validation_start_at": "2020-08-01T00:00:00Z",
                "validation_end_at": "2021-06-01T00:00:00Z",
                "test_start_at": "2021-08-01T00:00:00Z",
            }
        ),
    )
    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        lambda rows: [
            row.update(partition="train")
            for row in rows
        ],
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "leakage_safe").status == "blocked"
    assert _decision(packet, "leakage_safe").reason_codes == (
        "partition_assignment_invalid",
    )
    assert all(
        row.reason_codes == ("partition_assignment_invalid",)
        for row in packet.excluded
        if row.contract == "evaluations"
    )
    assert packet.analysis_eligible is False


def test_walk_forward_minimum_history_uses_actual_universe_evaluations(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_manifest(
        manifest,
        lambda raw: raw.update(
            evaluation_policy={
                "kind": "walk_forward",
                "minimum_history_count": 2,
            }
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "leakage_safe").status == "blocked"
    assert _decision(packet, "leakage_safe").reason_codes == (
        "partition_minimum_history_unmet",
    )
    assert {
        row.row_id: row.reason_codes
        for row in packet.excluded
        if row.contract == "evaluations"
    } == {
        "eval-bench-1": ("partition_minimum_history_unmet",),
        "eval-research-1": ("partition_minimum_history_unmet",),
    }
    assert packet.analysis_eligible is False


def test_later_identity_and_event_revisions_do_not_poison_earlier_evaluation(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_later_identity_revision(rows):
        rows.append(
            {
                **rows[0],
                "identity_row_id": "id-later-revision",
                "ticker": "BBB",
                "valid_from": "2022-01-01T00:00:00Z",
                "source_ref": "fixture://identity/later-revision",
                "source_published_at": "2022-01-01T00:00:00Z",
                "retrieved_at": "2022-01-02T00:00:00Z",
                "supersedes_identity_row_id": rows[0][
                    "identity_row_id"
                ],
            }
        )

    def add_later_event_revision(rows):
        rows.append(
            {
                **rows[0],
                "event_row_id": "event-later-revision",
                "effective_at": "2022-01-01T00:00:00Z",
                "source_ref": "fixture://event/later-revision",
                "source_published_at": "2022-01-01T00:00:00Z",
                "retrieved_at": "2022-01-02T00:00:00Z",
                "supersedes_event_row_id": rows[0]["event_row_id"],
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        add_later_identity_revision,
    )
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        add_later_event_revision,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "temporal_validity").status == "passed"
    assert _decision(packet, "leakage_safe").status == "passed"
    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert packet.display_tickers == {"sec-1": "AAA"}
    assert {
        row.row_id: row.reason_codes
        for row in packet.excluded
        if row.row_id
        in {"id-later-revision", "event-later-revision"}
    } == {
        "event-later-revision": ("cutoff_later_revision_invisible",),
        "id-later-revision": ("cutoff_later_revision_invisible",),
    }
    assert packet.analysis_eligible is True


def test_unrelated_future_identity_and_event_scopes_do_not_poison_evaluation(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_unrelated_identity(rows):
        rows.append(
            {
                **rows[0],
                "identity_row_id": "id-unrelated-future",
                "security_id": "sec-unrelated",
                "issuer_id": "issuer-unrelated",
                "ticker": "ZZZ",
                "valid_from": "2022-01-01T00:00:00Z",
                "source_ref": "fixture://identity/unrelated-future",
                "source_published_at": "2022-01-01T00:00:00Z",
                "retrieved_at": "2022-01-02T00:00:00Z",
                "supersedes_identity_row_id": "",
            }
        )

    def add_unrelated_event(rows):
        rows.append(
            {
                **rows[0],
                "event_row_id": "event-unrelated-future",
                "security_id": "sec-unrelated",
                "effective_at": "2022-01-01T00:00:00Z",
                "source_ref": "fixture://event/unrelated-future",
                "source_published_at": "2022-01-01T00:00:00Z",
                "retrieved_at": "2022-01-02T00:00:00Z",
                "supersedes_event_row_id": "",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        add_unrelated_identity,
    )
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        add_unrelated_event,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "temporal_validity").status == "passed"
    assert _decision(packet, "leakage_safe").status == "passed"
    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert {
        row.row_id: row.reason_codes
        for row in packet.excluded
        if row.row_id
        in {"id-unrelated-future", "event-unrelated-future"}
    } == {
        "event-unrelated-future": ("cutoff_unrelated_scope_invisible",),
        "id-unrelated-future": ("cutoff_unrelated_scope_invisible",),
    }
    assert packet.analysis_eligible is True


def test_complete_snapshot_valid_fixture_remains_eligible_and_deterministic(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    first = validate_point_in_time_universe(manifest, registry)
    second = validate_point_in_time_universe(manifest, registry)

    assert _decision(first, "membership_coverage").status == "passed"
    assert _decision(first, "reproduction_ready").status == "passed"
    assert first.membership_digests == second.membership_digests
    assert first.analysis_eligible is True


def test_complete_snapshot_uses_only_explicit_rows_from_latest_snapshot(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_second_identity(rows):
        rows.append(
            {
                **rows[0],
                "identity_row_id": "id-2",
                "security_id": "sec-2",
                "issuer_id": "issuer-2",
                "ticker": "BBB",
                "source_ref": "fixture://identity/id-2",
            }
        )

    def add_later_benchmark_snapshot(rows):
        rows.append(
            {
                **rows[0],
                "membership_row_id": "member-bench-later",
                "security_id": "sec-2",
                "effective_from": "2020-06-01T00:00:00Z",
                "observation_at": "2020-06-01T00:00:00Z",
                "source_ref": "fixture://membership/bench-later",
                "source_published_at": "2020-06-01T00:00:00Z",
                "retrieved_at": "2020-06-02T00:00:00Z",
            }
        )

    def add_second_listing_event(rows):
        rows.append(
            {
                **rows[0],
                "event_row_id": "event-sec-2-listing",
                "security_id": "sec-2",
                "source_ref": "fixture://event/sec-2-listing",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        add_second_identity,
    )
    _rewrite_csv_and_manifest(
        manifest,
        "membership",
        add_later_benchmark_snapshot,
    )
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        add_second_listing_event,
    )

    packet = validate_point_in_time_universe(manifest, registry)
    digests = _digest_by_universe(packet)

    assert _decision(packet, "membership_coverage").status == "passed"
    assert digests["bench-1"].member_count == 1
    assert digests["bench-1"].sha256 == _sha256_members("sec-2")
    assert digests["research-1"].member_count == 1
    assert digests["research-1"].sha256 == _sha256_members("sec-1")
    assert packet.analysis_eligible is True


def test_event_history_is_blocked_without_a_trusted_membership_digest(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_manifest(
        manifest,
        lambda raw: raw.update(coverage_semantics="event_history"),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "membership_coverage").status == "blocked"
    assert _decision(packet, "membership_coverage").reason_codes == (
        "membership_coverage_semantics_unsupported",
    )
    assert _decision(packet, "reproduction_ready").status == "blocked"
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_coverage_semantics_unsupported",
    )
    assert packet.membership_digests == ()
    assert packet.analysis_eligible is False


@pytest.mark.parametrize("member", [True, False])
def test_reversed_identity_interval_is_excluded_for_member_and_non_member(
    tmp_path,
    member,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def reverse_interval(rows):
        if member:
            rows[0].update(
                valid_from="2020-06-01T00:00:00Z",
                valid_to="2020-05-01T00:00:00Z",
            )
        else:
            rows.append(
                {
                    **rows[0],
                    "identity_row_id": "id-reversed-non-member",
                    "security_id": "sec-non-member",
                    "issuer_id": "issuer-non-member",
                    "source_ref": (
                        "fixture://identity/id-reversed-non-member"
                    ),
                    "valid_from": "2020-06-01T00:00:00Z",
                    "valid_to": "2020-05-01T00:00:00Z",
                }
            )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        reverse_interval,
    )

    packet = validate_point_in_time_universe(manifest, registry)
    row_id = "id-1" if member else "id-reversed-non-member"

    assert _decision(packet, "technical_validity").status == "blocked"
    assert _decision(packet, "technical_validity").reason_codes == (
        "schema_identity_interval_reversed",
    )
    assert (
        "security_identity",
        row_id,
        ("schema_identity_interval_reversed",),
    ) in {
        (row.contract, row.row_id, row.reason_codes)
        for row in packet.excluded
    }
    assert packet.analysis_eligible is False


@pytest.mark.parametrize("active", [True, False])
def test_reversed_membership_interval_is_excluded_when_active_or_irrelevant(
    tmp_path,
    active,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def reverse_interval(rows):
        if active:
            rows[0].update(
                effective_from="2020-06-01T00:00:00Z",
                effective_to="2020-05-01T00:00:00Z",
            )
        else:
            rows.append(
                {
                    **rows[0],
                    "membership_row_id": "member-reversed-irrelevant",
                    "security_id": "sec-non-member",
                    "membership_state": "excluded",
                    "effective_from": "2020-06-01T00:00:00Z",
                    "effective_to": "2020-05-01T00:00:00Z",
                    "source_ref": (
                        "fixture://membership/reversed-irrelevant"
                    ),
                }
            )

    _rewrite_csv_and_manifest(
        manifest,
        "membership",
        reverse_interval,
    )

    packet = validate_point_in_time_universe(manifest, registry)
    row_id = (
        "member-bench-1" if active else "member-reversed-irrelevant"
    )

    assert _decision(packet, "technical_validity").status == "blocked"
    assert _decision(packet, "technical_validity").reason_codes == (
        "schema_membership_interval_reversed",
    )
    assert (
        "membership",
        row_id,
        ("schema_membership_interval_reversed",),
    ) in {
        (row.contract, row.row_id, row.reason_codes)
        for row in packet.excluded
    }
    assert packet.analysis_eligible is False


@pytest.mark.parametrize("across_universes", [False, True])
def test_duplicate_evaluation_ids_exclude_every_ambiguous_row(
    tmp_path,
    across_universes,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def duplicate_evaluation(rows):
        if across_universes:
            rows[1]["evaluation_row_id"] = rows[0]["evaluation_row_id"]
        else:
            rows.append(
                {
                    **rows[0],
                    "source_ref": "fixture://evaluation/bench-duplicate",
                }
            )

    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        duplicate_evaluation,
    )

    packet = validate_point_in_time_universe(manifest, registry)
    duplicate_id = "eval-bench-1"
    duplicate_exclusions = [
        row
        for row in packet.excluded
        if row.contract == "evaluations" and row.row_id == duplicate_id
    ]

    assert _decision(packet, "technical_validity").status == "blocked"
    assert _decision(packet, "technical_validity").reason_codes == (
        "schema_evaluation_row_id_duplicate",
    )
    assert len(duplicate_exclusions) == 2
    assert all(
        row.reason_codes == ("schema_evaluation_row_id_duplicate",)
        for row in duplicate_exclusions
    )
    assert all(
        digest.universe_id != "bench-1"
        for digest in packet.membership_digests
    )
    if across_universes:
        assert packet.membership_digests == ()
    assert packet.analysis_eligible is False


def test_distinct_evaluation_ids_at_same_timestamp_remain_valid(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def add_distinct_same_cutoff(rows):
        rows.append(
            {
                **rows[0],
                "evaluation_row_id": "eval-bench-distinct-2",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        add_distinct_same_cutoff,
    )

    packet = validate_point_in_time_universe(manifest, registry)
    benchmark_digests = [
        digest
        for digest in packet.membership_digests
        if (
            digest.universe_id == "bench-1"
            and digest.evaluation_at == "2021-01-01T00:00:00Z"
        )
    ]

    assert _decision(packet, "technical_validity").status == "passed"
    assert _decision(packet, "reproduction_ready").status == "passed"
    assert len(benchmark_digests) == 1
    assert {
        digest.universe_id for digest in packet.membership_digests
    } == {"bench-1", "research-1"}
    assert packet.analysis_eligible is True
