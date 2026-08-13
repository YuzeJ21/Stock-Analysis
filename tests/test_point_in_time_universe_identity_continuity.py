from __future__ import annotations

import pytest
from tests.point_in_time_universe_fixture import build_valid_package
from tests.test_point_in_time_universe import (
    _decision,
    _mutate_identity_lineage_exclusion,
    _read_contract_rows,
    _replace_contract_rows,
    _rewrite_manifest,
    _sha256_members,
)
from tests.test_point_in_time_universe_cli import (
    _run_cli,
    _snapshot,
)
from tests.test_point_in_time_universe_contracts import (
    _rewrite_csv_and_manifest,
)
from tests.point_in_time_universe_remediation_fixtures import (
    STABLE_MEMBER_DIGEST,
    add_second_security_evidence,
    append_action_event,
)


REUSE_REASON = "identity_security_id_reused_across_issuers"


def _append_identity_interval(
    manifest,
    *,
    issuer_id: str,
    security_id: str = "sec-1",
    valid_from: str = "2020-06-01T00:00:00Z",
    visible_at_cutoff: bool = True,
    linked: bool = True,
) -> None:
    def mutate(rows):
        prior = next(
            row
            for row in rows
            if row["security_id"] == security_id
        )
        prior["valid_to"] = valid_from
        rows.append(
            {
                **prior,
                "identity_row_id": f"{prior['identity_row_id']}-later",
                "issuer_id": issuer_id,
                "valid_from": valid_from,
                "valid_to": "",
                "source_ref": f"{prior['source_ref']}/later",
                "source_published_at": (
                    valid_from
                    if visible_at_cutoff
                    else "2022-01-01T00:00:00Z"
                ),
                "retrieved_at": (
                    valid_from
                    if visible_at_cutoff
                    else "2022-01-02T00:00:00Z"
                ),
                "supersedes_identity_row_id": (
                    prior["identity_row_id"] if linked else ""
                ),
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def _append_same_effective_issuer_correction(manifest) -> None:
    def mutate(rows):
        erroneous = rows[0]
        erroneous["issuer_id"] = "issuer-erroneous"
        rows.append(
            {
                **erroneous,
                "identity_row_id": "id-issuer-correction",
                "issuer_id": "issuer-1",
                "source_ref": "fixture://identity/issuer-correction",
                "source_published_at": "2020-06-01T00:00:00Z",
                "retrieved_at": "2020-06-02T00:00:00Z",
                "supersedes_identity_row_id": (
                    erroneous["identity_row_id"]
                ),
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def _move_evaluations_to_2023(manifest) -> None:
    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        lambda rows: [
            row.update(
                evaluation_at="2023-01-01T00:00:00Z",
                available_at="2023-01-01T00:00:00Z",
            )
            for row in rows
        ],
    )
    _rewrite_manifest(
        manifest,
        lambda raw: raw.update(
            observation_cutoff_at="2023-01-01T00:00:00Z",
            evaluation_policy={
                "kind": "train_validation_test",
                "train_end_at": "2023-01-01T00:00:00Z",
                "validation_start_at": "2023-01-02T00:00:00Z",
                "validation_end_at": "2023-01-03T00:00:00Z",
                "test_start_at": "2023-01-04T00:00:00Z",
            },
        ),
    )


@pytest.mark.parametrize("with_action_event", (False, True))
def test_security_id_cannot_cross_issuers_even_with_action_event(
    tmp_path,
    with_action_event,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_identity_interval(manifest, issuer_id="issuer-2")
    if with_action_event:
        append_action_event(manifest, "ticker_change")

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "blocked"
    assert _decision(packet, "identity_coverage").reason_codes == (
        REUSE_REASON,
    )
    assert _decision(packet, "membership_coverage").status == "passed"
    assert _decision(packet, "reproduction_ready").status == "blocked"
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )
    assert {
        row.row_id: row.reason_codes
        for row in packet.excluded
        if REUSE_REASON in row.reason_codes
    } == {"id-1-later": (REUSE_REASON,)}
    assert packet.membership_digests == ()
    assert packet.display_tickers == {}
    assert packet.analysis_eligible is False
    assert packet.analysis_eligible_rows == ()


def test_unlinked_adjacent_cross_issuer_intervals_cannot_silently_pass(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_identity_interval(
        manifest,
        issuer_id="issuer-2",
        linked=False,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "blocked"
    assert REUSE_REASON in _decision(
        packet,
        "identity_coverage",
    ).reason_codes
    assert packet.membership_digests == ()
    assert packet.analysis_eligible_rows == ()


def test_same_issuer_identity_history_remains_valid(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_identity_interval(manifest, issuer_id="issuer-1")

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "reproduction_ready").status == "passed"
    assert packet.display_tickers == {"sec-1": "AAA"}
    assert packet.membership_digests
    assert packet.analysis_eligible is True


def test_same_effective_supersession_can_correct_erroneous_issuer(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_same_effective_issuer_correction(manifest)

    packet = validate_point_in_time_universe(manifest, registry)
    eligible_identity_ids = {
        row.row_id
        for row in packet.analysis_eligible_rows
        if row.contract == "security_identity"
    }

    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "reproduction_ready").status == "passed"
    assert eligible_identity_ids == {"id-issuer-correction"}
    assert packet.analysis_eligible is True


def test_adjacent_interval_on_separate_security_id_is_independent(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def append_other_security(rows):
        rows.append(
            {
                **rows[0],
                "identity_row_id": "id-other-security",
                "security_id": "sec-other",
                "issuer_id": "issuer-other",
                "valid_from": "2020-06-01T00:00:00Z",
                "source_ref": "fixture://identity/other-security",
                "supersedes_identity_row_id": "",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        append_other_security,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "passed"
    assert packet.analysis_eligible is True


def test_post_cutoff_issuer_change_is_invisible_until_later_evaluation(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    early_root = tmp_path / "early"
    early_root.mkdir()
    early_manifest, early_registry = build_valid_package(early_root)
    _append_identity_interval(
        early_manifest,
        issuer_id="issuer-2",
        valid_from="2022-01-01T00:00:00Z",
        visible_at_cutoff=False,
    )

    early = validate_point_in_time_universe(
        early_manifest,
        early_registry,
    )

    later_root = tmp_path / "later"
    later_root.mkdir()
    later_manifest, later_registry = build_valid_package(later_root)
    _append_identity_interval(
        later_manifest,
        issuer_id="issuer-2",
        valid_from="2022-01-01T00:00:00Z",
        visible_at_cutoff=False,
    )
    _move_evaluations_to_2023(later_manifest)

    later = validate_point_in_time_universe(
        later_manifest,
        later_registry,
    )

    assert _decision(early, "identity_coverage").status == "passed"
    assert early.analysis_eligible is True
    assert _decision(later, "identity_coverage").reason_codes == (
        REUSE_REASON,
    )
    assert later.membership_digests == ()
    assert later.analysis_eligible is False


def test_cross_issuer_identity_fork_remains_lineage_blocked(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def append_fork(rows):
        prior = rows[0]
        prior["valid_to"] = "2020-06-01T00:00:00Z"
        for suffix, issuer_id in (
            ("a", "issuer-2"),
            ("b", "issuer-3"),
        ):
            rows.append(
                {
                    **prior,
                    "identity_row_id": f"id-fork-{suffix}",
                    "issuer_id": issuer_id,
                    "valid_from": "2020-06-01T00:00:00Z",
                    "valid_to": "",
                    "source_ref": f"fixture://identity/fork-{suffix}",
                    "source_published_at": "2020-06-01T00:00:00Z",
                    "retrieved_at": "2020-06-02T00:00:00Z",
                    "supersedes_identity_row_id": prior["identity_row_id"],
                }
            )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        append_fork,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "blocked"
    assert _decision(packet, "identity_coverage").reason_codes == (
        "lineage_fork",
    )
    assert packet.analysis_eligible is False


def test_unicode_issuer_change_is_stable_id_reuse(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(issuer_id="發行人-甲-🚀"),
    )
    _append_identity_interval(
        manifest,
        issuer_id="發行人-乙-🚀",
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").reason_codes == (
        REUSE_REASON,
    )
    assert packet.membership_digests == ()
    assert packet.analysis_eligible_rows == ()


@pytest.mark.parametrize("command", ("status", "preview"))
def test_stable_id_reuse_is_cli_readable_and_write_free(
    tmp_path,
    command,
):
    manifest, registry = build_valid_package(tmp_path)
    _append_identity_interval(manifest, issuer_id="issuer-2")
    before = _snapshot(tmp_path)

    result = _run_cli(
        command,
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )

    assert result.returncode == 0
    assert "identity_coverage: blocked" in result.stdout
    assert REUSE_REASON in result.stdout
    assert "reproduction_ready: blocked" in result.stdout
    assert "reproduction_digest_missing" in result.stdout
    assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before


def _append_cross_issuer_fork(manifest) -> None:
    def mutate(rows):
        prior = rows[0]
        prior["valid_to"] = "2020-06-01T00:00:00Z"
        for suffix, issuer_id in (
            ("a", "issuer-2"),
            ("b", "issuer-3"),
        ):
            rows.append(
                {
                    **prior,
                    "identity_row_id": f"id-fork-{suffix}",
                    "issuer_id": issuer_id,
                    "valid_from": "2020-06-01T00:00:00Z",
                    "valid_to": "",
                    "source_ref": f"fixture://identity/fork-{suffix}",
                    "source_published_at": "2020-06-01T00:00:00Z",
                    "retrieved_at": "2020-06-02T00:00:00Z",
                    "supersedes_identity_row_id": prior["identity_row_id"],
                }
            )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def _make_research_consume_second_security(manifest) -> None:
    add_second_security_evidence(manifest)

    def mutate(rows):
        research = next(
            row
            for row in rows
            if row["universe_id"] == "research-1"
        )
        research.update(
            membership_row_id="member-research-sec-2",
            security_id="sec-2",
            source_ref="fixture://membership/research-sec-2",
        )

    _rewrite_csv_and_manifest(manifest, "membership", mutate)


def _reverse_contract_rows(manifest) -> None:
    for contract in (
        "security_identity",
        "membership",
        "events",
        "evaluations",
    ):
        _replace_contract_rows(
            manifest,
            contract,
            list(reversed(_read_contract_rows(manifest, contract))),
        )


def _digest_keys(packet):
    return {
        (digest.universe_id, digest.evaluation_at)
        for digest in packet.membership_digests
    }


def test_cross_issuer_fork_suppresses_every_consuming_packet_digest(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_cross_issuer_fork(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").reason_codes == (
        "lineage_fork",
    )
    assert packet.membership_digests == ()
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )
    assert packet.analysis_eligible is False
    assert packet.analysis_eligible_rows == ()


@pytest.mark.parametrize("reverse", (False, True))
def test_reuse_suppression_is_packet_scoped_and_order_deterministic(
    tmp_path,
    reverse,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _make_research_consume_second_security(manifest)
    _append_identity_interval(manifest, issuer_id="issuer-reused")
    if reverse:
        _reverse_contract_rows(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").reason_codes == (
        REUSE_REASON,
    )
    assert len(packet.membership_digests) == 1
    research = packet.membership_digests[0]
    assert (
        research.universe_id,
        research.evaluation_at,
        research.member_count,
        research.sha256,
    ) == (
        "research-1",
        "2021-01-01T00:00:00Z",
        1,
        _sha256_members("sec-2"),
    )
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )
    assert packet.analysis_eligible is False
    assert packet.analysis_eligible_rows == ()


def test_fork_suppression_is_scoped_across_multiple_evaluations(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _make_research_consume_second_security(manifest)
    _append_cross_issuer_fork(manifest)

    def add_early_benchmark_evaluation(rows):
        benchmark = next(
            row
            for row in rows
            if row["universe_id"] == "bench-1"
        )
        rows.append(
            {
                **benchmark,
                "evaluation_row_id": "eval-bench-early",
                "evaluation_at": "2020-03-01T00:00:00Z",
                "available_at": "2020-03-01T00:00:00Z",
                "source_ref": "fixture://evaluation/bench-early",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        add_early_benchmark_evaluation,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _digest_keys(packet) == {
        ("bench-1", "2020-03-01T00:00:00Z"),
        ("research-1", "2021-01-01T00:00:00Z"),
    }
    assert all(
        not (
            digest.universe_id == "bench-1"
            and digest.evaluation_at == "2021-01-01T00:00:00Z"
        )
        for digest in packet.membership_digests
    )
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )
    assert packet.analysis_eligible is False
    assert packet.analysis_eligible_rows == ()


def _append_deep_cross_issuer_fork(manifest) -> None:
    def mutate(rows):
        root = rows[0]
        root["valid_to"] = "2020-06-01T00:00:00Z"
        middle = {
            **root,
            "identity_row_id": "id-middle-issuer-2",
            "issuer_id": "issuer-2",
            "valid_from": "2020-06-01T00:00:00Z",
            "valid_to": "2020-09-01T00:00:00Z",
            "source_ref": "fixture://identity/middle-issuer-2",
            "source_published_at": "2020-06-01T00:00:00Z",
            "retrieved_at": "2020-06-02T00:00:00Z",
            "supersedes_identity_row_id": root["identity_row_id"],
        }
        rows.append(middle)
        branch_a = {
            **middle,
            "identity_row_id": "id-branch-a-issuer-2",
            "valid_from": "2020-09-01T00:00:00Z",
            "valid_to": "2020-12-01T00:00:00Z",
            "source_ref": "fixture://identity/branch-a-issuer-2",
            "source_published_at": "2020-09-01T00:00:00Z",
            "retrieved_at": "2020-09-02T00:00:00Z",
            "supersedes_identity_row_id": middle["identity_row_id"],
        }
        branch_b = {
            **middle,
            "identity_row_id": "id-branch-b-issuer-2",
            "valid_from": "2020-09-01T00:00:00Z",
            "valid_to": "",
            "source_ref": "fixture://identity/branch-b-issuer-2",
            "source_published_at": "2020-09-01T00:00:00Z",
            "retrieved_at": "2020-09-02T00:00:00Z",
            "supersedes_identity_row_id": middle["identity_row_id"],
        }
        rows.extend((branch_a, branch_b))
        rows.append(
            {
                **branch_a,
                "identity_row_id": "id-grandchild-issuer-2",
                "valid_from": "2020-12-01T00:00:00Z",
                "valid_to": "",
                "source_ref": "fixture://identity/grandchild-issuer-2",
                "source_published_at": "2020-12-01T00:00:00Z",
                "retrieved_at": "2020-12-02T00:00:00Z",
                "supersedes_identity_row_id": branch_a[
                    "identity_row_id"
                ],
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def _append_later_corrected_issuer_history(manifest) -> None:
    def mutate(rows):
        correction = next(
            row
            for row in rows
            if row["identity_row_id"] == "id-issuer-correction"
        )
        erroneous = next(
            row
            for row in rows
            if row["identity_row_id"]
            == correction["supersedes_identity_row_id"]
        )
        erroneous["valid_to"] = "2020-09-01T00:00:00Z"
        correction["valid_to"] = "2020-09-01T00:00:00Z"
        rows.append(
            {
                **correction,
                "identity_row_id": "id-corrected-issuer-later",
                "valid_from": "2020-09-01T00:00:00Z",
                "valid_to": "",
                "source_ref": "fixture://identity/corrected-later",
                "source_published_at": "2020-09-01T00:00:00Z",
                "retrieved_at": "2020-09-02T00:00:00Z",
                "supersedes_identity_row_id": correction[
                    "identity_row_id"
                ],
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def test_deep_cross_issuer_fork_propagates_through_descendants(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_deep_cross_issuer_fork(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").reason_codes == (
        "lineage_fork",
    )
    assert packet.membership_digests == ()
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )
    assert packet.analysis_eligible_rows == ()


@pytest.mark.parametrize("reverse", (False, True))
def test_deep_reuse_suppression_is_scoped_and_order_deterministic(
    tmp_path,
    reverse,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _make_research_consume_second_security(manifest)
    _append_deep_cross_issuer_fork(manifest)
    if reverse:
        _reverse_contract_rows(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    assert len(packet.membership_digests) == 1
    research = packet.membership_digests[0]
    assert (
        research.universe_id,
        research.evaluation_at,
        research.member_count,
        research.sha256,
    ) == (
        "research-1",
        "2021-01-01T00:00:00Z",
        1,
        _sha256_members("sec-2"),
    )
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )
    assert packet.analysis_eligible_rows == ()


def test_deep_reuse_propagation_is_cutoff_and_evaluation_scoped(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _make_research_consume_second_security(manifest)
    _append_deep_cross_issuer_fork(manifest)

    def add_early_benchmark_evaluation(rows):
        benchmark = next(
            row
            for row in rows
            if row["universe_id"] == "bench-1"
        )
        rows.append(
            {
                **benchmark,
                "evaluation_row_id": "eval-bench-before-reuse",
                "evaluation_at": "2020-03-01T00:00:00Z",
                "available_at": "2020-03-01T00:00:00Z",
                "source_ref": "fixture://evaluation/bench-before-reuse",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        add_early_benchmark_evaluation,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _digest_keys(packet) == {
        ("bench-1", "2020-03-01T00:00:00Z"),
        ("research-1", "2021-01-01T00:00:00Z"),
    }
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )
    assert packet.analysis_eligible_rows == ()


def _append_invalid_same_effective_correction(
    manifest,
    mode: str,
) -> None:
    def mutate(rows):
        root = rows[0]
        root["valid_to"] = "2020-06-01T00:00:00Z"
        middle = {
            **root,
            "identity_row_id": "id-issuer-2-interval",
            "issuer_id": "issuer-2",
            "valid_from": "2020-06-01T00:00:00Z",
            "valid_to": "",
            "source_ref": "fixture://identity/issuer-2-interval",
            "source_published_at": "2020-06-01T00:00:00Z",
            "retrieved_at": "2020-06-02T00:00:00Z",
            "supersedes_identity_row_id": root["identity_row_id"],
        }
        correction = {
            **middle,
            "identity_row_id": "id-invalid-issuer-1-correction",
            "issuer_id": "issuer-1",
            "source_ref": "fixture://identity/invalid-correction",
            "source_published_at": "2020-07-01T00:00:00Z",
            "retrieved_at": "2020-07-02T00:00:00Z",
            "supersedes_identity_row_id": middle["identity_row_id"],
        }
        if mode == "lineage_order_reversed":
            correction.update(
                source_published_at="2020-06-01T00:00:00Z",
                retrieved_at="2020-06-01T00:00:00Z",
            )
        elif mode == "unavailable":
            correction.update(
                source_published_at="2022-01-01T00:00:00Z",
                retrieved_at="2022-01-02T00:00:00Z",
            )
        elif mode == "lineage_cross_scope_parent":
            correction.update(
                security_id="sec-other",
                source_ref="fixture://identity/cross-scope-correction",
            )
        elif mode == "lineage_cycle":
            middle["supersedes_identity_row_id"] = correction[
                "identity_row_id"
            ]
        elif mode != "lineage_fork":
            raise AssertionError(f"unsupported mode: {mode}")

        rows.extend((middle, correction))
        if mode == "lineage_fork":
            rows.append(
                {
                    **correction,
                    "identity_row_id": "id-second-issuer-1-correction",
                    "source_ref": (
                        "fixture://identity/second-invalid-correction"
                    ),
                    "source_published_at": "2020-08-01T00:00:00Z",
                    "retrieved_at": "2020-08-02T00:00:00Z",
                }
            )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def test_reversed_same_effective_correction_cannot_erase_raw_issuer(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _make_research_consume_second_security(manifest)
    _append_invalid_same_effective_correction(
        manifest,
        "lineage_order_reversed",
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert "lineage_order_reversed" in _decision(
        packet,
        "identity_coverage",
    ).reason_codes
    assert len(packet.membership_digests) == 1
    research = packet.membership_digests[0]
    assert (
        research.universe_id,
        research.member_count,
        research.sha256,
    ) == (
        "research-1",
        1,
        _sha256_members("sec-2"),
    )
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )
    assert packet.analysis_eligible_rows == ()


@pytest.mark.parametrize(
    "mode",
    (
        "lineage_order_reversed",
        "unavailable",
        "lineage_cross_scope_parent",
        "lineage_fork",
        "lineage_cycle",
    ),
)
def test_invalid_same_effective_correction_preserves_raw_issuer_evidence(
    tmp_path,
    mode,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_invalid_same_effective_correction(manifest, mode)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "blocked"
    assert packet.membership_digests == ()
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )
    assert packet.analysis_eligible_rows == ()


def test_valid_same_effective_correction_remains_authoritative(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_same_effective_issuer_correction(manifest)
    _append_later_corrected_issuer_history(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "reproduction_ready").status == "passed"
    assert len(packet.membership_digests) == 2
    assert packet.analysis_eligible is True


def test_generic_same_issuer_fork_keeps_legacy_empty_digests(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _mutate_identity_lineage_exclusion(manifest, "lineage_fork")

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").reason_codes == (
        "lineage_fork",
    )
    assert len(packet.membership_digests) == 2
    assert all(
        digest.member_count == 0
        and digest.sha256 == _sha256_members()
        for digest in packet.membership_digests
    )
    assert _decision(packet, "reproduction_ready").status == "passed"


def _append_later_same_issuer_fork(manifest) -> None:
    def mutate(rows):
        parent = next(
            row
            for row in rows
            if row["identity_row_id"] == "id-corrected-issuer-later"
        )
        parent["valid_to"] = "2020-12-01T00:00:00Z"
        for suffix in ("a", "b"):
            rows.append(
                {
                    **parent,
                    "identity_row_id": f"id-later-fork-{suffix}",
                    "valid_from": "2020-12-01T00:00:00Z",
                    "valid_to": "",
                    "source_ref": (
                        f"fixture://identity/later-fork-{suffix}"
                    ),
                    "source_published_at": "2020-12-01T00:00:00Z",
                    "retrieved_at": "2020-12-02T00:00:00Z",
                    "supersedes_identity_row_id": parent[
                        "identity_row_id"
                    ],
                }
            )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def _append_valid_correction_then_later_fork(manifest) -> None:
    _append_same_effective_issuer_correction(manifest)
    _append_later_corrected_issuer_history(manifest)
    _append_later_same_issuer_fork(manifest)


@pytest.mark.parametrize("reverse", (False, True))
def test_later_fork_does_not_resurrect_corrected_parent(
    tmp_path,
    reverse,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_valid_correction_then_later_fork(manifest)
    if reverse:
        _reverse_contract_rows(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").reason_codes == (
        "lineage_fork",
    )
    assert len(packet.membership_digests) == 2
    assert all(
        digest.member_count == 0
        and digest.sha256 == _sha256_members()
        for digest in packet.membership_digests
    )
    assert _decision(packet, "reproduction_ready").status == "passed"
    assert packet.analysis_eligible is False
    assert packet.analysis_eligible_rows == ()


def test_later_fork_preserves_unrelated_scope_digest(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _make_research_consume_second_security(manifest)
    _append_valid_correction_then_later_fork(manifest)

    packet = validate_point_in_time_universe(manifest, registry)
    digests = {
        digest.universe_id: digest
        for digest in packet.membership_digests
    }

    assert set(digests) == {"bench-1", "research-1"}
    assert (
        digests["bench-1"].member_count,
        digests["bench-1"].sha256,
    ) == (0, _sha256_members())
    assert (
        digests["research-1"].member_count,
        digests["research-1"].sha256,
    ) == (1, _sha256_members("sec-2"))
    assert _decision(packet, "reproduction_ready").status == "passed"
    assert packet.analysis_eligible_rows == ()


def _append_direct_same_issuer_fork_from_correction(manifest) -> None:
    _append_same_effective_issuer_correction(manifest)

    def mutate(rows):
        correction = next(
            row
            for row in rows
            if row["identity_row_id"] == "id-issuer-correction"
        )
        erroneous = next(
            row
            for row in rows
            if row["identity_row_id"]
            == correction["supersedes_identity_row_id"]
        )
        erroneous["valid_to"] = "2020-06-01T00:00:00Z"
        correction["valid_to"] = "2020-06-01T00:00:00Z"
        for suffix in ("a", "b"):
            rows.append(
                {
                    **correction,
                    "identity_row_id": f"id-direct-fork-{suffix}",
                    "valid_from": "2020-06-01T00:00:00Z",
                    "valid_to": "",
                    "source_ref": (
                        f"fixture://identity/direct-fork-{suffix}"
                    ),
                    "source_published_at": "2020-07-01T00:00:00Z",
                    "retrieved_at": "2020-07-02T00:00:00Z",
                    "supersedes_identity_row_id": correction[
                        "identity_row_id"
                    ],
                }
            )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def _assert_generic_fork_reproduction(packet) -> None:
    assert _decision(packet, "identity_coverage").reason_codes == (
        "lineage_fork",
    )
    assert len(packet.membership_digests) == 2
    assert all(
        digest.member_count == 0
        and digest.sha256 == _sha256_members()
        for digest in packet.membership_digests
    )
    assert _decision(packet, "reproduction_ready").status == "passed"
    assert packet.analysis_eligible_rows == ()


@pytest.mark.parametrize("reverse", (False, True))
def test_direct_fork_from_correction_keeps_correction_authoritative(
    tmp_path,
    reverse,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_direct_same_issuer_fork_from_correction(manifest)
    if reverse:
        _reverse_contract_rows(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    _assert_generic_fork_reproduction(packet)


def test_competing_corrections_from_erroneous_parent_still_block_digest(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_invalid_same_effective_correction(
        manifest,
        "lineage_fork",
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert packet.membership_digests == ()
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )


def test_intervening_corrected_interval_before_fork_remains_authoritative(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_valid_correction_then_later_fork(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    _assert_generic_fork_reproduction(packet)


def _append_outgoing_descendant_error(
    manifest,
    mode: str,
) -> None:
    _append_same_effective_issuer_correction(manifest)

    def mutate(rows):
        correction = next(
            row
            for row in rows
            if row["identity_row_id"] == "id-issuer-correction"
        )
        erroneous = next(
            row
            for row in rows
            if row["identity_row_id"]
            == correction["supersedes_identity_row_id"]
        )
        descendant = {
            **correction,
            "identity_row_id": f"id-outgoing-{mode}",
            "valid_from": "2020-06-01T00:00:00Z",
            "valid_to": "",
            "source_ref": f"fixture://identity/outgoing-{mode}",
            "source_published_at": "2020-07-01T00:00:00Z",
            "retrieved_at": "2020-07-02T00:00:00Z",
            "supersedes_identity_row_id": correction[
                "identity_row_id"
            ],
        }
        if mode == "lineage_order_reversed":
            erroneous["valid_to"] = "2020-06-01T00:00:00Z"
            correction["valid_to"] = "2020-06-01T00:00:00Z"
            descendant.update(
                source_published_at="2020-06-01T00:00:00Z",
                retrieved_at="2020-06-01T00:00:00Z",
            )
        elif mode == "lineage_cross_scope_parent":
            erroneous["valid_to"] = "2020-06-01T00:00:00Z"
            correction["valid_to"] = "2020-06-01T00:00:00Z"
            descendant["security_id"] = "sec-descendant-other"
        elif mode == "unavailable":
            descendant.update(
                source_published_at="2022-01-01T00:00:00Z",
                retrieved_at="2022-01-02T00:00:00Z",
            )
        elif mode != "identity_interval_overlap":
            raise AssertionError(f"unsupported mode: {mode}")
        rows.append(descendant)

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def _append_multigeneration_corrections_with_outgoing_error(
    manifest,
) -> None:
    _append_same_effective_issuer_correction(manifest)

    def mutate(rows):
        first = next(
            row
            for row in rows
            if row["identity_row_id"] == "id-issuer-correction"
        )
        erroneous = next(
            row
            for row in rows
            if row["identity_row_id"]
            == first["supersedes_identity_row_id"]
        )
        erroneous["valid_to"] = "2020-06-01T00:00:00Z"
        first["valid_to"] = "2020-06-01T00:00:00Z"
        second = {
            **first,
            "identity_row_id": "id-second-valid-correction",
            "issuer_id": "issuer-final",
            "source_ref": "fixture://identity/second-valid-correction",
            "source_published_at": "2020-08-01T00:00:00Z",
            "retrieved_at": "2020-08-02T00:00:00Z",
            "supersedes_identity_row_id": first["identity_row_id"],
        }
        rows.append(second)
        rows.append(
            {
                **second,
                "identity_row_id": "id-second-cross-scope-descendant",
                "security_id": "sec-descendant-other",
                "valid_from": "2020-06-01T00:00:00Z",
                "valid_to": "",
                "source_ref": (
                    "fixture://identity/second-cross-scope-descendant"
                ),
                "source_published_at": "2020-09-01T00:00:00Z",
                "retrieved_at": "2020-09-02T00:00:00Z",
                "supersedes_identity_row_id": second[
                    "identity_row_id"
                ],
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def _assert_error_keeps_reproduction_digest(packet, reason: str) -> None:
    assert reason in _decision(
        packet,
        "identity_coverage",
    ).reason_codes
    assert len(packet.membership_digests) == 2
    assert all(
        digest.member_count == 0
        and digest.sha256 == _sha256_members()
        for digest in packet.membership_digests
    )
    assert _decision(packet, "reproduction_ready").status == "passed"
    assert packet.analysis_eligible_rows == ()


@pytest.mark.parametrize(
    "mode",
    (
        "lineage_order_reversed",
        "lineage_cross_scope_parent",
    ),
)
def test_outgoing_descendant_error_does_not_revoke_incoming_correction(
    tmp_path,
    mode,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_outgoing_descendant_error(manifest, mode)

    packet = validate_point_in_time_universe(manifest, registry)

    _assert_error_keeps_reproduction_digest(packet, mode)


def test_unavailable_descendant_does_not_revoke_visible_correction(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_outgoing_descendant_error(manifest, "unavailable")

    packet = validate_point_in_time_universe(manifest, registry)

    assert len(packet.membership_digests) == 2
    assert all(
        digest.member_count == 1
        and digest.sha256 == _sha256_members("sec-1")
        for digest in packet.membership_digests
    )
    assert _decision(packet, "reproduction_ready").status == "passed"


def test_overlapping_descendant_does_not_revoke_incoming_correction(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_outgoing_descendant_error(
        manifest,
        "identity_interval_overlap",
    )

    packet = validate_point_in_time_universe(manifest, registry)

    _assert_error_keeps_reproduction_digest(
        packet,
        "identity_interval_overlap",
    )


def test_multigeneration_corrections_survive_later_outgoing_error(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_multigeneration_corrections_with_outgoing_error(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    _assert_error_keeps_reproduction_digest(
        packet,
        "lineage_cross_scope_parent",
    )


@pytest.mark.parametrize(
    "mode",
    ("lineage_order_reversed", "lineage_cycle"),
)
def test_invalid_correction_edge_remains_non_authoritative(tmp_path, mode):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_invalid_same_effective_correction(manifest, mode)

    packet = validate_point_in_time_universe(manifest, registry)

    assert packet.membership_digests == ()
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )


def _append_invalid_correction_sibling(
    manifest,
    mode: str,
) -> None:
    _append_same_effective_issuer_correction(manifest)

    def mutate(rows):
        erroneous = next(
            row
            for row in rows
            if row["identity_row_id"] == "id-1"
        )
        sibling = {
            **erroneous,
            "identity_row_id": f"id-invalid-sibling-{mode}",
            "issuer_id": "issuer-1",
            "source_ref": f"fixture://identity/invalid-sibling-{mode}",
            "source_published_at": "2020-08-01T00:00:00Z",
            "retrieved_at": "2020-08-02T00:00:00Z",
            "supersedes_identity_row_id": erroneous[
                "identity_row_id"
            ],
        }
        if mode == "lineage_cross_scope_parent":
            sibling["security_id"] = "sec-cross-scope-sibling"
        elif mode == "wrong_security":
            sibling["security_id"] = "sec-wrong-security-sibling"
        elif mode == "wrong_start":
            sibling["valid_from"] = "2020-06-01T00:00:00Z"
        elif mode == "lineage_cycle":
            erroneous["supersedes_identity_row_id"] = sibling[
                "identity_row_id"
            ]
        elif mode == "unavailable":
            sibling.update(
                source_published_at="2022-01-01T00:00:00Z",
                retrieved_at="2022-01-02T00:00:00Z",
            )
        else:
            raise AssertionError(f"unsupported mode: {mode}")
        rows.append(sibling)

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def _append_second_valid_correction_candidate(manifest) -> None:
    _append_same_effective_issuer_correction(manifest)

    def mutate(rows):
        correction = next(
            row
            for row in rows
            if row["identity_row_id"] == "id-issuer-correction"
        )
        rows.append(
            {
                **correction,
                "identity_row_id": "id-second-valid-correction-candidate",
                "source_ref": (
                    "fixture://identity/second-valid-correction-candidate"
                ),
                "source_published_at": "2020-08-01T00:00:00Z",
                "retrieved_at": "2020-08-02T00:00:00Z",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize(
    ("mode", "expected_reason"),
    (
        (
            "lineage_cross_scope_parent",
            "lineage_cross_scope_parent",
        ),
        ("wrong_security", "lineage_cross_scope_parent"),
        ("wrong_start", "lineage_fork"),
        ("lineage_cycle", "lineage_cycle"),
    ),
)
def test_invalid_sibling_does_not_compete_with_valid_correction(
    tmp_path,
    mode,
    expected_reason,
    reverse,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_invalid_correction_sibling(manifest, mode)
    if reverse:
        _reverse_contract_rows(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    _assert_error_keeps_reproduction_digest(
        packet,
        expected_reason,
    )


def test_unavailable_sibling_does_not_compete_at_cutoff(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_invalid_correction_sibling(manifest, "unavailable")

    packet = validate_point_in_time_universe(manifest, registry)

    assert len(packet.membership_digests) == 2
    assert all(
        digest.member_count == 1
        and digest.sha256 == _sha256_members("sec-1")
        for digest in packet.membership_digests
    )
    assert _decision(packet, "reproduction_ready").status == "passed"


def test_two_valid_correction_candidates_remain_non_authoritative(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_second_valid_correction_candidate(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    assert "lineage_fork" in _decision(
        packet,
        "identity_coverage",
    ).reason_codes
    assert packet.membership_digests == ()
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )
    assert packet.analysis_eligible_rows == ()


def test_outgoing_descendant_remains_separate_from_incoming_candidates(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_outgoing_descendant_error(
        manifest,
        "lineage_cross_scope_parent",
    )

    packet = validate_point_in_time_universe(manifest, registry)

    _assert_error_keeps_reproduction_digest(
        packet,
        "lineage_cross_scope_parent",
    )


def _append_duplicate_correction_child(
    manifest,
    mode: str,
) -> None:
    _append_same_effective_issuer_correction(manifest)

    def mutate(rows):
        correction = next(
            row
            for row in rows
            if row["identity_row_id"] == "id-issuer-correction"
        )
        duplicate = {
            **correction,
            "source_ref": f"fixture://identity/duplicate-child-{mode}",
            "source_published_at": "2020-08-01T00:00:00Z",
            "retrieved_at": "2020-08-02T00:00:00Z",
        }
        if mode == "cross_scope":
            duplicate["security_id"] = "sec-duplicate-child-other"
        elif mode == "wrong_start":
            duplicate["valid_from"] = "2020-06-01T00:00:00Z"
        elif mode == "order_reversed":
            duplicate.update(
                source_published_at="2020-01-01T00:00:00Z",
                retrieved_at="2020-01-01T00:00:00Z",
            )
        elif mode == "unavailable":
            duplicate.update(
                source_published_at="2022-01-01T00:00:00Z",
                retrieved_at="2022-01-02T00:00:00Z",
            )
        else:
            raise AssertionError(f"unsupported mode: {mode}")
        rows.append(duplicate)

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def _append_duplicate_correction_parent(
    manifest,
    mode: str,
) -> None:
    _append_same_effective_issuer_correction(manifest)

    def mutate(rows):
        parent = next(
            row
            for row in rows
            if row["identity_row_id"] == "id-1"
        )
        duplicate = {
            **parent,
            "source_ref": f"fixture://identity/duplicate-parent-{mode}",
            "source_published_at": "2020-09-01T00:00:00Z",
            "retrieved_at": "2020-09-02T00:00:00Z",
        }
        if mode == "cross_scope":
            duplicate["security_id"] = "sec-duplicate-parent-other"
        elif mode == "same_scope":
            pass
        elif mode == "unavailable":
            duplicate.update(
                source_published_at="2022-01-01T00:00:00Z",
                retrieved_at="2022-01-02T00:00:00Z",
            )
        else:
            raise AssertionError(f"unsupported mode: {mode}")
        rows.append(duplicate)

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def _assert_duplicate_endpoint_is_non_authoritative(packet) -> None:
    assert "lineage_duplicate_id" in _decision(
        packet,
        "identity_coverage",
    ).reason_codes
    assert packet.membership_digests == ()
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )
    assert packet.analysis_eligible_rows == ()


@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize(
    "mode",
    ("cross_scope", "wrong_start", "order_reversed"),
)
def test_duplicate_child_id_cannot_authorize_valid_looking_correction(
    tmp_path,
    mode,
    reverse,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_duplicate_correction_child(manifest, mode)
    if reverse:
        _reverse_contract_rows(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    _assert_duplicate_endpoint_is_non_authoritative(packet)


@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("mode", ("same_scope", "cross_scope"))
def test_duplicate_parent_id_cannot_authorize_correction(
    tmp_path,
    mode,
    reverse,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_duplicate_correction_parent(manifest, mode)
    if reverse:
        _reverse_contract_rows(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    _assert_duplicate_endpoint_is_non_authoritative(packet)


@pytest.mark.parametrize("endpoint", ("child", "parent"))
def test_post_cutoff_duplicate_endpoint_does_not_revoke_correction(
    tmp_path,
    endpoint,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    if endpoint == "child":
        _append_duplicate_correction_child(manifest, "unavailable")
    else:
        _append_duplicate_correction_parent(manifest, "unavailable")

    packet = validate_point_in_time_universe(manifest, registry)

    assert len(packet.membership_digests) == 2
    assert all(
        digest.member_count == 1
        and digest.sha256 == _sha256_members("sec-1")
        for digest in packet.membership_digests
    )
    assert _decision(packet, "reproduction_ready").status == "passed"


def _build_duplicate_target_chain(
    manifest,
    *,
    duplicate_available: bool = True,
    include_duplicate: bool = True,
    reverse: bool = False,
) -> None:
    def mutate_identities(rows):
        grandparent = rows[0]
        grandparent.update(
            identity_row_id="id-duplicated-grandparent",
            issuer_id="issuer-erroneous",
            valid_to="2020-06-01T00:00:00Z",
            source_ref="fixture://identity/grandparent-sec-1",
        )
        duplicate = {
            **grandparent,
            "security_id": "sec-duplicate-scope",
            "issuer_id": "issuer-duplicate-scope",
            "source_ref": "fixture://identity/grandparent-duplicate",
            "source_published_at": (
                "2020-01-01T00:00:00Z"
                if duplicate_available
                else "2022-01-01T00:00:00Z"
            ),
            "retrieved_at": (
                "2020-01-02T00:00:00Z"
                if duplicate_available
                else "2022-01-02T00:00:00Z"
            ),
        }
        later = {
            **grandparent,
            "identity_row_id": "id-later-interval",
            "valid_from": "2020-06-01T00:00:00Z",
            "valid_to": "",
            "source_ref": "fixture://identity/later-interval",
            "source_published_at": "2020-06-01T00:00:00Z",
            "retrieved_at": "2020-06-02T00:00:00Z",
            "supersedes_identity_row_id": (
                grandparent["identity_row_id"]
            ),
        }
        correction = {
            **later,
            "identity_row_id": "id-later-interval-correction",
            "issuer_id": "issuer-1",
            "source_ref": "fixture://identity/later-correction",
            "source_published_at": "2020-07-01T00:00:00Z",
            "retrieved_at": "2020-07-02T00:00:00Z",
            "supersedes_identity_row_id": later["identity_row_id"],
        }
        unrelated = {
            **grandparent,
            "identity_row_id": "id-unrelated",
            "security_id": "sec-unrelated",
            "issuer_id": "issuer-unrelated",
            "valid_to": "",
            "source_ref": "fixture://identity/unrelated",
            "supersedes_identity_row_id": "",
        }
        replacement = [grandparent]
        if include_duplicate:
            replacement.append(duplicate)
        replacement.extend((later, correction, unrelated))
        if reverse:
            replacement.reverse()
        rows[:] = replacement

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate_identities,
    )

    def consume_unrelated_scope(rows):
        research = next(
            row
            for row in rows
            if row["universe_id"] == "research-1"
        )
        research.update(
            security_id="sec-unrelated",
            source_ref="fixture://membership/research-unrelated",
        )

    _rewrite_csv_and_manifest(
        manifest,
        "membership",
        consume_unrelated_scope,
    )


def _decision_signature(packet):
    return tuple(
        (area, item.status, item.reason_codes)
        for area, item in packet.decisions.items()
    )


def _assert_affected_scope_fails_closed(packet) -> None:
    assert _decision(packet, "identity_coverage").status == "blocked"
    assert _decision(packet, "identity_coverage").reason_codes == (
        "lineage_duplicate_id",
    )
    assert len(packet.membership_digests) == 1
    research = packet.membership_digests[0]
    assert (
        research.universe_id,
        research.member_count,
        research.sha256,
    ) == (
        "research-1",
        1,
        _sha256_members("sec-unrelated"),
    )
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )
    assert packet.analysis_eligible_rows == ()


def test_duplicate_supersedes_target_is_input_order_independent(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    forward_root = tmp_path / "forward"
    forward_root.mkdir()
    forward_manifest, forward_registry = build_valid_package(
        forward_root
    )
    _build_duplicate_target_chain(forward_manifest)

    reverse_root = tmp_path / "reverse"
    reverse_root.mkdir()
    reverse_manifest, reverse_registry = build_valid_package(
        reverse_root
    )
    _build_duplicate_target_chain(reverse_manifest, reverse=True)

    forward = validate_point_in_time_universe(
        forward_manifest,
        forward_registry,
    )
    reverse = validate_point_in_time_universe(
        reverse_manifest,
        reverse_registry,
    )

    assert _decision_signature(forward) == _decision_signature(reverse)
    assert (
        forward.exclusion_reason_counts
        == reverse.exclusion_reason_counts
    )
    _assert_affected_scope_fails_closed(forward)
    _assert_affected_scope_fails_closed(reverse)


def test_ambiguous_parent_cannot_authorize_fork_inference(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _build_duplicate_target_chain(manifest)

    def append_second_child(rows):
        first_child = next(
            row
            for row in rows
            if row["identity_row_id"] == "id-later-interval"
        )
        rows.append(
            {
                **first_child,
                "identity_row_id": "id-later-sibling",
                "source_ref": "fixture://identity/later-sibling",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        append_second_child,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").reason_codes == (
        "lineage_duplicate_id",
    )
    assert "lineage_fork" not in packet.exclusion_reason_counts
    _assert_affected_scope_fails_closed(packet)


def test_post_cutoff_duplicate_target_matches_unique_target(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    unique_root = tmp_path / "unique"
    unique_root.mkdir()
    unique_manifest, unique_registry = build_valid_package(unique_root)
    _build_duplicate_target_chain(
        unique_manifest,
        include_duplicate=False,
    )

    unavailable_root = tmp_path / "unavailable"
    unavailable_root.mkdir()
    unavailable_manifest, unavailable_registry = build_valid_package(
        unavailable_root
    )
    _build_duplicate_target_chain(
        unavailable_manifest,
        duplicate_available=False,
    )

    unique = validate_point_in_time_universe(
        unique_manifest,
        unique_registry,
    )
    unavailable = validate_point_in_time_universe(
        unavailable_manifest,
        unavailable_registry,
    )

    assert _decision_signature(unique) == _decision_signature(
        unavailable
    )
    assert unique.membership_digests == unavailable.membership_digests
    assert "lineage_duplicate_id" not in _decision(
        unavailable,
        "identity_coverage",
    ).reason_codes


def _append_identity_revision(
    manifest,
    *,
    ticker: str = "AAA",
    exchange: str = "XNYS",
    same_valid_from: bool = False,
) -> None:
    def mutate(rows):
        prior = rows[0]
        if not same_valid_from:
            prior["valid_to"] = "2020-06-01T00:00:00Z"
        rows.append(
            {
                **prior,
                "identity_row_id": "id-2",
                "ticker": ticker,
                "exchange": exchange,
                "valid_from": (
                    prior["valid_from"]
                    if same_valid_from
                    else "2020-06-01T00:00:00Z"
                ),
                "valid_to": "",
                "source_ref": "fixture://identity/id-2",
                "source_published_at": "2020-06-01T00:00:00Z",
                "retrieved_at": "2020-06-02T00:00:00Z",
                "supersedes_identity_row_id": prior["identity_row_id"],
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def _assert_action_reconciliation_blocked(packet) -> None:
    assert _decision(packet, "technical_validity").status == "passed"
    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "blocked"
    assert "corporate_action_evidence_missing" in _decision(
        packet,
        "corporate_action_coverage",
    ).reason_codes
    assert packet.analysis_eligible is False


def test_ticker_transition_requires_event_even_when_policy_is_not_applicable(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_identity_revision(manifest, ticker="BBB")

    packet = validate_point_in_time_universe(manifest, registry)

    _assert_action_reconciliation_blocked(packet)
    assert packet.display_tickers == {"sec-1": "BBB"}


@pytest.mark.parametrize(
    ("mutation", "event_options"),
    [
        ("missing", None),
        ("wrong_security", {"security_id": "sec-other"}),
        (
            "wrong_time",
            {"effective_at": "2020-07-01T00:00:00Z"},
        ),
        ("post_cutoff", {"visible_at_cutoff": False}),
    ],
)
def test_required_ticker_event_must_match_identity_transition(
    tmp_path,
    mutation,
    event_options,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_identity_revision(manifest, ticker="BBB")
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            {"ticker_change": "required"}
        ),
    )
    if event_options is not None:
        append_action_event(
            manifest,
            "ticker_change",
            **event_options,
        )

    packet = validate_point_in_time_universe(manifest, registry)

    _assert_action_reconciliation_blocked(packet)
    assert packet.display_tickers == {"sec-1": "BBB"}, mutation


@pytest.mark.parametrize(
    ("field", "event_type", "revision"),
    [
        ("ticker", "ticker_change", {"ticker": "BBB"}),
        ("exchange", "exchange_change", {"exchange": "XNAS"}),
    ],
)
def test_exact_identity_transition_event_reconciles_action(
    tmp_path,
    field,
    event_type,
    revision,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_identity_revision(manifest, **revision)
    append_action_event(manifest, event_type)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").reason_codes == ()
    assert {
        (
            digest.universe_id,
            digest.member_count,
            digest.sha256,
        )
        for digest in packet.membership_digests
    } == {
        ("bench-1", 1, STABLE_MEMBER_DIGEST),
        ("research-1", 1, STABLE_MEMBER_DIGEST),
    }
    assert packet.analysis_eligible is True, field


@pytest.mark.parametrize(
    ("present_event_types", "expected_status"),
    [
        (("ticker_change",), "blocked"),
        (("exchange_change",), "blocked"),
        (("ticker_change", "exchange_change"), "passed"),
    ],
)
def test_simultaneous_ticker_and_exchange_transition_requires_both_events(
    tmp_path,
    present_event_types,
    expected_status,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_identity_revision(
        manifest,
        ticker="BBB",
        exchange="XNAS",
    )
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            {
                "ticker_change": "required",
                "exchange_change": "required",
            }
        ),
    )
    for event_type in present_event_types:
        append_action_event(manifest, event_type)

    packet = validate_point_in_time_universe(manifest, registry)

    assert (
        _decision(packet, "corporate_action_coverage").status
        == expected_status
    )
    assert packet.analysis_eligible is (expected_status == "passed")


def test_same_ticker_on_different_security_does_not_create_action_requirement(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def append_other_security(rows):
        rows.append(
            {
                **rows[0],
                "identity_row_id": "id-other-security",
                "security_id": "sec-other",
                "issuer_id": "issuer-other",
                "source_ref": "fixture://identity/other-security",
                "supersedes_identity_row_id": "",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        append_other_security,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert packet.analysis_eligible is True


def test_same_valid_from_identity_correction_is_not_a_market_action(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_identity_revision(
        manifest,
        ticker="BBB",
        exchange="XNAS",
        same_valid_from=True,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert packet.display_tickers == {"sec-1": "BBB"}
    assert packet.analysis_eligible is True


def _append_identity_transition(
    manifest,
    *,
    ticker: str = "AAA",
    exchange: str = "XNYS",
) -> None:
    def mutate(rows):
        prior = rows[0]
        prior["valid_to"] = "2020-06-01T00:00:00Z"
        rows.append(
            {
                **prior,
                "identity_row_id": "id-new-identity",
                "ticker": ticker,
                "exchange": exchange,
                "valid_from": "2020-06-01T00:00:00Z",
                "valid_to": "",
                "source_ref": "fixture://identity/new-identity",
                "source_published_at": "2020-06-01T00:00:00Z",
                "retrieved_at": "2020-06-02T00:00:00Z",
                "supersedes_identity_row_id": prior["identity_row_id"],
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


@pytest.mark.parametrize(
    "revision",
    [
        {"ticker": "BBB"},
        {"exchange": "XNAS"},
        {"ticker": "BBB", "exchange": "XNAS"},
    ],
)
def test_identity_transition_groups_action_requirement_by_stable_security(
    tmp_path,
    revision,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_identity_transition(manifest, **revision)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "blocked"
    assert "corporate_action_evidence_missing" in _decision(
        packet,
        "corporate_action_coverage",
    ).reason_codes
    assert packet.analysis_eligible is False


@pytest.mark.parametrize(
    ("event_type", "revision"),
    [
        ("ticker_change", {"ticker": "BBB"}),
        ("exchange_change", {"exchange": "XNAS"}),
    ],
)
def test_exact_event_reconciles_identity_transition(
    tmp_path,
    event_type,
    revision,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_identity_transition(manifest, **revision)
    append_action_event(manifest, event_type)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert packet.analysis_eligible is True


@pytest.mark.parametrize(
    ("present_event_types", "expected_status"),
    [
        (("ticker_change",), "blocked"),
        (("exchange_change",), "blocked"),
        (("ticker_change", "exchange_change"), "passed"),
    ],
)
def test_identity_transition_changing_both_fields_requires_both_events(
    tmp_path,
    present_event_types,
    expected_status,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_identity_transition(
        manifest,
        ticker="BBB",
        exchange="XNAS",
    )
    for event_type in present_event_types:
        append_action_event(manifest, event_type)

    packet = validate_point_in_time_universe(manifest, registry)

    assert (
        _decision(packet, "corporate_action_coverage").status
        == expected_status
    )
    assert packet.analysis_eligible is (expected_status == "passed")


def _append_known_future_child(manifest) -> None:
    def mutate(rows):
        prior = rows[0]
        prior["valid_to"] = "2022-01-01T00:00:00Z"
        rows.append(
            {
                **prior,
                "identity_row_id": "id-future-child",
                "ticker": "BBB",
                "valid_from": "2022-01-01T00:00:00Z",
                "valid_to": "",
                "source_ref": "fixture://identity/future-child",
                "source_published_at": "2020-06-01T00:00:00Z",
                "retrieved_at": "2020-06-02T00:00:00Z",
                "supersedes_identity_row_id": prior["identity_row_id"],
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )




def test_known_future_child_does_not_erase_active_ancestor_at_early_cutoff(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_known_future_child(manifest)

    packet = validate_point_in_time_universe(manifest, registry)
    eligible_identity_ids = {
        row.row_id
        for row in packet.analysis_eligible_rows
        if row.contract == "security_identity"
    }

    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert packet.display_tickers == {"sec-1": "AAA"}
    assert eligible_identity_ids == {"id-1"}
    assert {
        digest.sha256
        for digest in packet.membership_digests
    } == {STABLE_MEMBER_DIGEST}
    assert packet.analysis_eligible is True


@pytest.mark.parametrize(
    ("with_event", "expected_status"),
    [
        (False, "blocked"),
        (True, "passed"),
    ],
)
def test_future_identity_transition_is_reconciled_when_it_becomes_effective(
    tmp_path,
    with_event,
    expected_status,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_known_future_child(manifest)
    _move_evaluations_to_2023(manifest)
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            {"ticker_change": "required"}
        ),
    )
    if with_event:
        append_action_event(
            manifest,
            "ticker_change",
            effective_at="2022-01-01T00:00:00Z",
        )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "passed"
    assert (
        _decision(packet, "corporate_action_coverage").status
        == expected_status
    )
    assert packet.display_tickers == {"sec-1": "BBB"}
    assert packet.analysis_eligible is (expected_status == "passed")


def test_adjacent_interval_on_different_security_is_independent(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)

    def append_other_security(rows):
        rows.append(
            {
                **rows[0],
                "identity_row_id": "id-other-security",
                "security_id": "sec-other",
                "issuer_id": "issuer-other",
                "ticker": "BBB",
                "valid_from": "2020-06-01T00:00:00Z",
                "source_ref": "fixture://identity/other-security",
                "supersedes_identity_row_id": "",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        append_other_security,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert packet.analysis_eligible is True


REASON = "schema_identity_issuer_matches_security"


def _collapse_identity_identifiers(manifest) -> None:
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(
            issuer_id=rows[0]["security_id"],
        ),
    )


def test_issuer_identifier_cannot_equal_security_identifier(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _collapse_identity_identifiers(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "technical_validity").status == "blocked"
    assert _decision(packet, "technical_validity").reason_codes == (REASON,)
    assert any(
        row.contract == "security_identity"
        and row.row_id == "id-1"
        and row.reason_codes == (REASON,)
        for row in packet.excluded
    )
    assert packet.analysis_eligible is False
    assert packet.analysis_eligible_rows == ()


@pytest.mark.parametrize("command", ("status", "preview"))
def test_equal_identity_identifiers_are_cli_readable_and_write_free(
    tmp_path,
    command,
):
    manifest, registry = build_valid_package(tmp_path)
    _collapse_identity_identifiers(manifest)
    before = _snapshot(tmp_path)

    result = _run_cli(
        command,
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )

    assert result.returncode == 0
    assert "technical_validity: blocked" in result.stdout
    assert REASON in result.stdout
    assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before


def test_distinct_unicode_security_and_issuer_identifiers_remain_valid(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    security_id = "證券-β-🚀"
    issuer_id = "發行人-β-🚀"
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(
            security_id=security_id,
            issuer_id=issuer_id,
        ),
    )
    for contract in ("membership", "events"):
        _rewrite_csv_and_manifest(
            manifest,
            contract,
            lambda rows: [
                row.update(security_id=security_id)
                for row in rows
            ],
        )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "technical_validity").status == "passed"
    assert _decision(packet, "identity_coverage").status == "passed"
    assert packet.analysis_eligible is True
