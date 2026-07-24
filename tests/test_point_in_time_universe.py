import hashlib

import pytest

from tests.point_in_time_universe_fixture import build_valid_package
from tests.test_point_in_time_universe_contracts import _rewrite_csv_and_manifest


def _sha256_members(*security_ids):
    return hashlib.sha256("\n".join(sorted(security_ids)).encode("utf-8")).hexdigest()


def _decision(packet, area):
    return packet.decisions[area]


def _digest_by_universe(packet):
    return {digest.universe_id: digest for digest in packet.membership_digests}


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
