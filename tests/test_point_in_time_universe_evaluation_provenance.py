from __future__ import annotations

from tests.point_in_time_universe_fixture import build_valid_package
from tests.test_point_in_time_universe import (
    _decision,
    _rewrite_manifest,
    _sha256_members,
)
from tests.test_point_in_time_universe_cli import _run_cli
from tests.test_point_in_time_universe_contracts import (
    _rewrite_csv_and_manifest,
)
import pytest
from tests.point_in_time_universe_remediation_fixtures import (
    add_successor_identity,
    append_identity_correction,
    replace_membership_with_successor,
    set_identity_valid_from,
    set_successor_event,
)


EVALUATION_TIMESTAMPS = (
    "2020-03-01T00:00:00Z",
    "2020-06-01T00:00:00Z",
    "2021-01-01T00:00:00Z",
)


def _configure_walk_forward_package(
    manifest,
    *,
    reverse_input: bool = False,
) -> None:
    _rewrite_manifest(
        manifest,
        lambda raw: raw.update(
            evaluation_policy={
                "kind": "walk_forward",
                "minimum_history_count": 2,
            }
        ),
    )

    def replace_evaluations(rows):
        templates = {
            row["universe_id"]: row
            for row in rows
        }
        replacement = []
        for evaluation_number, evaluation_at in enumerate(
            EVALUATION_TIMESTAMPS,
            start=1,
        ):
            for universe_id in ("bench-1", "research-1"):
                replacement.append(
                    {
                        **templates[universe_id],
                        "evaluation_row_id": (
                            f"eval-{universe_id}-{evaluation_number}"
                        ),
                        "evaluation_at": evaluation_at,
                        "available_at": evaluation_at,
                        "partition": "walk_forward",
                        "source_ref": (
                            "fixture://evaluation/"
                            f"{universe_id}/{evaluation_number}"
                        ),
                    }
                )
        rows[:] = (
            list(reversed(replacement))
            if reverse_input
            else replacement
        )

    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        replace_evaluations,
    )


def _bootstrap_exclusions(packet):
    return {
        row.row_id: row.reason_codes
        for row in packet.excluded
        if row.contract == "evaluations"
    }


def test_walk_forward_bootstrap_exclusions_allow_later_eligible_evaluations(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _configure_walk_forward_package(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "leakage_safe").status == "passed"
    assert _decision(packet, "leakage_safe").reason_codes == ()
    assert _bootstrap_exclusions(packet) == {
        "eval-bench-1-1": ("partition_minimum_history_unmet",),
        "eval-bench-1-2": ("partition_minimum_history_unmet",),
        "eval-research-1-1": ("partition_minimum_history_unmet",),
        "eval-research-1-2": ("partition_minimum_history_unmet",),
    }
    assert {
        (
            digest.universe_id,
            digest.evaluation_at,
            digest.member_count,
            digest.sha256,
        )
        for digest in packet.membership_digests
    } == {
        (
            "bench-1",
            "2021-01-01T00:00:00Z",
            1,
            _sha256_members("sec-1"),
        ),
        (
            "research-1",
            "2021-01-01T00:00:00Z",
            1,
            _sha256_members("sec-1"),
        ),
    }
    assert packet.analysis_eligible is True


def test_walk_forward_bootstrap_semantics_are_input_order_independent(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    (tmp_path / "forward").mkdir()
    (tmp_path / "reverse").mkdir()
    forward_manifest, forward_registry = build_valid_package(
        tmp_path / "forward"
    )
    reverse_manifest, reverse_registry = build_valid_package(
        tmp_path / "reverse"
    )
    _configure_walk_forward_package(forward_manifest)
    _configure_walk_forward_package(
        reverse_manifest,
        reverse_input=True,
    )

    forward = validate_point_in_time_universe(
        forward_manifest,
        forward_registry,
    )
    reverse = validate_point_in_time_universe(
        reverse_manifest,
        reverse_registry,
    )

    assert forward.membership_digests == reverse.membership_digests
    assert _bootstrap_exclusions(forward) == _bootstrap_exclusions(reverse)
    assert forward.decisions == reverse.decisions
    assert forward.analysis_eligible is True
    assert reverse.analysis_eligible is True


def test_walk_forward_preview_shows_bootstrap_exclusions_and_later_digests(
    tmp_path,
):
    manifest, registry = build_valid_package(tmp_path)
    _configure_walk_forward_package(manifest)

    result = _run_cli(
        "preview",
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
        "--top-n",
        "20",
    )

    assert result.returncode == 0
    assert "analysis_eligible: true" in result.stdout
    assert "leakage_safe: passed; reasons=none" in result.stdout
    assert "- partition_minimum_history_unmet: 4" in result.stdout
    assert (
        "- bench-1 @ 2021-01-01T00:00:00Z: members=1; sha256="
        f"{_sha256_members('sec-1')}"
    ) in result.stdout
    assert (
        "- research-1 @ 2021-01-01T00:00:00Z: members=1; sha256="
        f"{_sha256_members('sec-1')}"
    ) in result.stdout
    for row_id in (
        "eval-bench-1-1",
        "eval-bench-1-2",
        "eval-research-1-1",
        "eval-research-1-2",
    ):
        assert (
            f"{row_id}; reasons=partition_minimum_history_unmet"
            in result.stdout
        )


def _semantic_provenance(packet):
    return tuple(
        sorted(
            (
                row.evaluation_row_id,
                row.contract,
                row.row_id,
            )
            for row in packet.analysis_eligible_rows
        )
    )


def _configure_successor_action(
    manifest,
    successor_security_id: str,
    event_type: str,
) -> None:
    add_successor_identity(manifest, successor_security_id)
    set_successor_event(
        manifest,
        successor_security_id,
        event_type=event_type,
    )
    if event_type in {"merger", "acquisition"}:
        replace_membership_with_successor(
            manifest,
            successor_security_id,
        )


def test_parent_retaining_spinoff_includes_both_endpoint_identities(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _configure_successor_action(
        manifest,
        "sec-spinoff-successor",
        "spinoff",
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert packet.analysis_eligible is True
    assert set(_semantic_provenance(packet)) == {
        ("eval-bench-1", "evaluations", "eval-bench-1"),
        ("eval-bench-1", "events", "event-1"),
        ("eval-bench-1", "membership", "member-bench-1"),
        ("eval-bench-1", "security_identity", "id-1"),
        ("eval-bench-1", "security_identity", "id-successor"),
        ("eval-research-1", "evaluations", "eval-research-1"),
        ("eval-research-1", "events", "event-1"),
        (
            "eval-research-1",
            "membership",
            "member-research-1",
        ),
        ("eval-research-1", "security_identity", "id-1"),
        (
            "eval-research-1",
            "security_identity",
            "id-successor",
        ),
    }


def test_replacement_merger_deduplicates_successor_identity_provenance(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _configure_successor_action(
        manifest,
        "sec-merger-successor",
        "merger",
    )

    packet = validate_point_in_time_universe(manifest, registry)
    semantic = _semantic_provenance(packet)

    assert packet.analysis_eligible is True
    for evaluation_row_id in ("eval-bench-1", "eval-research-1"):
        assert semantic.count(
            (
                evaluation_row_id,
                "security_identity",
                "id-successor",
            )
        ) == 1
        assert (
            evaluation_row_id,
            "security_identity",
            "id-1",
        ) in semantic


def test_unicode_successor_provenance_is_deterministic_under_input_order(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    forward_root = tmp_path / "forward"
    reverse_root = tmp_path / "reverse"
    forward_root.mkdir()
    reverse_root.mkdir()
    forward_manifest, forward_registry = build_valid_package(forward_root)
    reverse_manifest, reverse_registry = build_valid_package(reverse_root)
    successor_security_id = "後継-𐐷-🚀"
    for manifest in (forward_manifest, reverse_manifest):
        _configure_successor_action(
            manifest,
            successor_security_id,
            "spinoff",
        )
    _rewrite_csv_and_manifest(
        reverse_manifest,
        "security_identity",
        lambda rows: rows.reverse(),
    )
    _rewrite_csv_and_manifest(
        reverse_manifest,
        "events",
        lambda rows: rows.reverse(),
    )

    forward = validate_point_in_time_universe(
        forward_manifest,
        forward_registry,
    )
    reverse = validate_point_in_time_universe(
        reverse_manifest,
        reverse_registry,
    )

    assert forward.analysis_eligible is True
    assert reverse.analysis_eligible is True
    assert _semantic_provenance(forward) == _semantic_provenance(reverse)
    assert {
        row.row_id
        for row in forward.analysis_eligible_rows
        if row.contract == "security_identity"
    } == {"id-1", "id-successor"}


@pytest.mark.parametrize(
    "endpoint_state",
    ("missing", "ambiguous", "future", "superseded"),
)
def test_unresolved_successor_has_zero_eligible_provenance(
    tmp_path,
    endpoint_state,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    successor_security_id = f"sec-{endpoint_state}-successor"
    if endpoint_state == "missing":
        set_successor_event(manifest, successor_security_id)
    else:
        _configure_successor_action(
            manifest,
            successor_security_id,
            "merger",
        )
        if endpoint_state == "ambiguous":
            _rewrite_csv_and_manifest(
                manifest,
                "security_identity",
                lambda rows: rows.append(
                    {
                        **rows[-1],
                        "identity_row_id": "id-successor-ambiguous",
                        "issuer_id": "issuer-successor-ambiguous",
                        "source_ref": (
                            "fixture://identity/successor-ambiguous"
                        ),
                        "supersedes_identity_row_id": "",
                    }
                ),
            )
        elif endpoint_state == "future":
            set_identity_valid_from(
                manifest,
                successor_security_id,
                "2020-07-01T00:00:00Z",
            )
        else:
            append_identity_correction(
                manifest,
                successor_security_id,
                valid_from="2020-07-01T00:00:00Z",
                valid_to="",
            )

    packet = validate_point_in_time_universe(manifest, registry)

    assert packet.analysis_eligible is False
    assert packet.analysis_eligible_rows == ()
    assert packet.analysis_eligible_row_count == 0


def test_event_time_historical_successor_identity_is_included_when_consumed(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    successor_security_id = "sec-historical-successor"
    _configure_successor_action(
        manifest,
        successor_security_id,
        "spinoff",
    )

    def append_later_successor(rows):
        prior = next(
            row
            for row in rows
            if row["security_id"] == successor_security_id
        )
        prior["valid_to"] = "2020-07-01T00:00:00Z"
        rows.append(
            {
                **prior,
                "identity_row_id": "id-successor-later",
                "valid_from": "2020-07-01T00:00:00Z",
                "valid_to": "",
                "source_ref": "fixture://identity/successor-later",
                "source_published_at": "2020-07-01T00:00:00Z",
                "retrieved_at": "2020-07-02T00:00:00Z",
                "supersedes_identity_row_id": prior["identity_row_id"],
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        append_later_successor,
    )

    packet = validate_point_in_time_universe(manifest, registry)
    successor_provenance_ids = {
        row.row_id
        for row in packet.analysis_eligible_rows
        if (
            row.contract == "security_identity"
            and row.row_id.startswith("id-successor")
        )
    }

    assert packet.analysis_eligible is True
    assert successor_provenance_ids == {"id-successor"}


def test_required_state_event_used_by_decision_is_in_eligible_provenance(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _configure_successor_action(
        manifest,
        "sec-merger-successor",
        "merger",
    )

    def add_delisting_evidence(rows):
        action = rows[0]
        action["listing_state_after"] = "delisted"
        rows.append(
            {
                **action,
                "event_row_id": "event-matching-delisting",
                "event_type": "delisting",
                "successor_security_id": "",
                "listing_state_after": "delisted",
                "source_ref": "fixture://event/matching/delisting",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "events",
        add_delisting_evidence,
    )
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            delisting="required",
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert packet.analysis_eligible is True
    assert {
        row.row_id
        for row in packet.analysis_eligible_rows
        if row.contract == "events"
    } == {"event-1", "event-matching-delisting"}
