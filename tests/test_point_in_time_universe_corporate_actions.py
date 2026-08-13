from __future__ import annotations

import pytest
from tests.point_in_time_universe_fixture import build_valid_package
from tests.test_point_in_time_universe import (
    _append_registry_source,
    _decision,
    _refresh_registry_digest,
    _rewrite_manifest,
)
from tests.test_point_in_time_universe_contracts import (
    _rewrite_csv_and_manifest,
)
from tests.point_in_time_universe_remediation_fixtures import (
    add_successor_identity,
    replace_membership_with_successor,
    require_event,
    set_successor_event,
)


NON_STATE_ACTIONS = (
    "ticker_change",
    "exchange_change",
    "split",
    "reverse_split",
    "merger",
    "acquisition",
    "spinoff",
)


def _configure_non_state_action(
    manifest,
    event_type: str,
    listing_state_after: str,
) -> None:
    if event_type in {"merger", "acquisition", "spinoff"}:
        successor = f"sec-{event_type}-successor"
        add_successor_identity(manifest, successor)
        set_successor_event(
            manifest,
            successor,
            event_type=event_type,
        )
        if event_type in {"merger", "acquisition"}:
            replace_membership_with_successor(manifest, successor)
        _rewrite_csv_and_manifest(
            manifest,
            "events",
            lambda rows: rows[0].update(
                listing_state_after=listing_state_after,
            ),
        )
        return

    def mutate(rows):
        rows[0].update(
            event_type=event_type,
            effective_at="2020-06-01T00:00:00Z",
            successor_security_id="",
            ratio_numerator=(
                "2"
                if event_type == "split"
                else "1"
                if event_type == "reverse_split"
                else ""
            ),
            ratio_denominator=(
                "1"
                if event_type == "split"
                else "10"
                if event_type == "reverse_split"
                else ""
            ),
            listing_state_after=listing_state_after,
            source_published_at="2020-06-01T00:00:00Z",
            retrieved_at="2020-06-02T00:00:00Z",
        )

    _rewrite_csv_and_manifest(manifest, "events", mutate)
    require_event(manifest, event_type)


def _append_matching_state_event(
    manifest,
    listing_state_after: str,
    *,
    security_id: str | None = None,
    effective_at: str | None = None,
    visible_at_cutoff: bool = True,
    required_policy: bool = True,
) -> None:
    event_type = (
        "delisting"
        if listing_state_after == "delisted"
        else "suspension"
    )

    def mutate(rows):
        action = rows[0]
        state_effective_at = effective_at or action["effective_at"]
        rows.append(
            {
                **action,
                "event_row_id": f"event-matching-{event_type}",
                "security_id": security_id or action["security_id"],
                "event_type": event_type,
                "effective_at": state_effective_at,
                "successor_security_id": "",
                "ratio_numerator": "",
                "ratio_denominator": "",
                "listing_state_after": listing_state_after,
                "source_ref": f"fixture://event/matching/{event_type}",
                "source_published_at": (
                    state_effective_at
                    if visible_at_cutoff
                    else "2022-01-01T00:00:00Z"
                ),
                "retrieved_at": (
                    state_effective_at
                    if visible_at_cutoff
                    else "2022-01-02T00:00:00Z"
                ),
                "supersedes_event_row_id": "",
            }
        )

    _rewrite_csv_and_manifest(manifest, "events", mutate)
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            {
                event_type: (
                    "required"
                    if required_policy
                    else "not_applicable"
                )
            }
        ),
    )


@pytest.mark.parametrize("event_type", NON_STATE_ACTIONS)
@pytest.mark.parametrize(
    "listing_state_after",
    ("delisted", "suspended"),
)
def test_restrictive_non_state_action_requires_matching_state_event(
    tmp_path,
    event_type,
    listing_state_after,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _configure_non_state_action(
        manifest,
        event_type,
        listing_state_after,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "technical_validity").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert _decision(packet, "delisting_coverage").status == "blocked"
    assert _decision(
        packet,
        "delisting_coverage",
    ).reason_codes == ("delisting_evidence_missing",)
    assert any(
        row.contract == "events"
        and row.row_id == "event-1"
        and row.reason_codes == ("delisting_evidence_missing",)
        for row in packet.excluded
    )
    assert packet.analysis_eligible is False


@pytest.mark.parametrize("event_type", NON_STATE_ACTIONS)
@pytest.mark.parametrize(
    "listing_state_after",
    ("delisted", "suspended"),
)
def test_matching_state_event_closes_restrictive_non_state_action(
    tmp_path,
    event_type,
    listing_state_after,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _configure_non_state_action(
        manifest,
        event_type,
        listing_state_after,
    )
    _append_matching_state_event(manifest, listing_state_after)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "technical_validity").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert _decision(packet, "delisting_coverage").status == "passed"
    assert _decision(packet, "delisting_coverage").reason_codes == ()
    assert packet.analysis_eligible is True


@pytest.mark.parametrize(
    ("mutation", "matching_options"),
    [
        ("wrong_security", {"security_id": "sec-other"}),
        (
            "wrong_time",
            {"effective_at": "2020-07-01T00:00:00Z"},
        ),
        ("future", {"visible_at_cutoff": False}),
        ("not_applicable", {"required_policy": False}),
    ],
)
def test_matching_state_event_must_match_scope_time_visibility_and_policy(
    tmp_path,
    mutation,
    matching_options,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _configure_non_state_action(
        manifest,
        "ticker_change",
        "delisted",
    )
    _append_matching_state_event(
        manifest,
        "delisted",
        **matching_options,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "technical_validity").status == "passed"
    assert _decision(packet, "delisting_coverage").status == "blocked"
    if mutation != "not_applicable":
        assert "delisting_evidence_missing" in _decision(
            packet,
            "delisting_coverage",
        ).reason_codes
    assert packet.analysis_eligible is False, mutation


def test_active_non_state_action_remains_compatible(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _configure_non_state_action(manifest, "split", "active")

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert _decision(packet, "delisting_coverage").status == "not_applicable"
    assert packet.analysis_eligible is True


@pytest.mark.parametrize(
    "listing_state_after",
    ("delisted", "suspended"),
)
def test_listing_event_cannot_carry_restrictive_state(
    tmp_path,
    listing_state_after,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        lambda rows: rows[0].update(
            listing_state_after=listing_state_after,
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == "blocked"
    assert _decision(
        packet,
        "corporate_action_coverage",
    ).reason_codes == ("corporate_action_listing_state_invalid",)
    assert packet.analysis_eligible is False


def _configure_rights_state_events(
    manifest,
    event_type: str,
    source_id: str,
) -> None:
    def mutate(rows):
        rows[0].update(
            event_type="suspension",
            effective_at="2020-06-01T00:00:00Z",
            listing_state_after="suspended",
            source_id=source_id,
            source_ref="fixture://event/suspension",
            source_published_at="2020-06-01T00:00:00Z",
            retrieved_at="2020-06-02T00:00:00Z",
        )
        if event_type == "reactivation":
            rows.append(
                {
                    **rows[0],
                    "event_row_id": "event-reactivation",
                    "event_type": "reactivation",
                    "effective_at": "2020-07-01T00:00:00Z",
                    "listing_state_after": "active",
                    "source_ref": "fixture://event/reactivation",
                    "source_published_at": "2020-07-01T00:00:00Z",
                    "retrieved_at": "2020-07-02T00:00:00Z",
                    "supersedes_event_row_id": "",
                }
            )

    _rewrite_csv_and_manifest(manifest, "events", mutate)
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            {
                "listing": "not_applicable",
                "suspension": "required",
                event_type: "required",
            }
        ),
    )


@pytest.mark.parametrize(
    ("event_type", "supported_fields", "expected_status"),
    [
        ("suspension", ("corporate_actions",), "blocked"),
        (
            "suspension",
            ("corporate_actions", "delistings"),
            "passed",
        ),
        ("reactivation", ("corporate_actions",), "blocked"),
        (
            "reactivation",
            ("corporate_actions", "delistings"),
            "passed",
        ),
    ],
)
def test_suspension_and_reactivation_require_both_rights_scopes(
    tmp_path,
    event_type,
    supported_fields,
    expected_status,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    source_id = f"{event_type}-source"
    _configure_rights_state_events(manifest, event_type, source_id)
    _append_registry_source(registry, source_id, supported_fields)
    _rewrite_manifest(
        manifest,
        lambda raw: raw["allowed_source_ids"].append(source_id),
    )
    _refresh_registry_digest(manifest, registry)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(
        packet,
        "source_rights_eligibility",
    ).status == expected_status
    if expected_status == "blocked":
        assert _decision(
            packet,
            "source_rights_eligibility",
        ).reason_codes == ("source_rights_field_scope_missing",)
        assert packet.analysis_eligible is False
    else:
        assert _decision(
            packet,
            "source_rights_eligibility",
        ).reason_codes == ()
        assert packet.analysis_eligible is True


def test_delisting_rights_mapping_remains_delistings_only(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    source_id = "delisting-only-source"
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        lambda rows: rows[0].update(
            event_type="delisting",
            listing_state_after="delisted",
            source_id=source_id,
        ),
    )
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            {
                "listing": "not_applicable",
                "delisting": "required",
            }
        ),
    )
    _append_registry_source(
        registry,
        source_id,
        ("delistings",),
    )
    _rewrite_manifest(
        manifest,
        lambda raw: raw["allowed_source_ids"].append(source_id),
    )
    _refresh_registry_digest(manifest, registry)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(
        packet,
        "source_rights_eligibility",
    ).status == "passed"
    assert packet.analysis_eligible is True


def test_pre_action_evaluation_does_not_poison_later_required_coverage(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _configure_non_state_action(manifest, "split", "")
    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        lambda rows: rows[0].update(
            evaluation_at="2020-03-01T00:00:00Z",
            available_at="2020-03-01T00:00:00Z",
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(
        packet,
        "corporate_action_coverage",
    ).status == "passed"
    assert _decision(
        packet,
        "corporate_action_coverage",
    ).reason_codes == ()
    assert _decision(packet, "temporal_validity").status == "passed"
    assert _decision(packet, "leakage_safe").status == "passed"
    assert packet.analysis_eligible is True
