import hashlib
import json

import pytest

from tests.point_in_time_universe_fixture import build_valid_package
from tests.test_point_in_time_universe_contracts import _rewrite_csv_and_manifest


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
                "effective_at": "2022-01-01T00:00:00Z",
                "listing_state_after": "delisted",
                "source_ref": "fixture://event/event-2",
                "source_published_at": "2022-01-01T00:00:00Z",
                "retrieved_at": "2022-01-02T00:00:00Z",
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


def test_repeated_reactivation_is_blocked_by_current_listing_state(tmp_path):
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
        "delisting_transition_invalid",
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
