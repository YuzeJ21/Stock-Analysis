from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import pytest
from tests.point_in_time_universe_fixture import build_valid_package
from tests.test_point_in_time_universe import (
    _decision,
    _refresh_contract_digest,
    _refresh_registry_digest,
    _rewrite_manifest,
)
from tests.test_point_in_time_universe_cli import (
    _run_cli,
    _run_make,
    _snapshot,
)
from tests.test_point_in_time_universe_contracts import (
    _rewrite_csv_and_manifest,
)
from tests.point_in_time_universe_remediation_fixtures import (
    add_successor_identity,
    append_identity_correction,
    replace_membership_with_successor,
    require_event,
    set_identity_valid_from,
    set_successor_event,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _duplicate_manifest_key(manifest, depth: str) -> None:
    text = manifest.read_text(encoding="utf-8")
    if depth == "top":
        needle = '"dataset_id": "fixture-dataset"'
    else:
        needle = '"contract": "security_identity"'
    manifest.write_text(
        text.replace(needle, f"{needle}, {needle}", 1),
        encoding="utf-8",
    )


def _duplicate_registry_key(manifest, registry, depth: str) -> None:
    text = registry.read_text(encoding="utf-8")
    if depth == "top":
        duplicate = text.replace("sources:\n", "sources_duplicate:\n", 1)
        text = f"{text}{duplicate.replace('sources_duplicate:', 'sources:', 1)}"
    else:
        needle = "  - source_id: fixture_source\n"
        duplicate = "    source_id: fixture_source\n"
        text = text.replace(needle, f"{needle}{duplicate}", 1)
    registry.write_text(text, encoding="utf-8")
    _refresh_registry_digest(manifest, registry)


@pytest.mark.parametrize(
    ("resource", "depth", "error"),
    [
        ("manifest", "top", "manifest_duplicate_key"),
        ("manifest", "nested", "manifest_duplicate_key"),
        ("registry", "top", "source_rights_registry_duplicate_key"),
        ("registry", "nested", "source_rights_registry_duplicate_key"),
    ],
)
def test_duplicate_mapping_keys_fail_validator_cli_and_make_without_writes(
    tmp_path,
    resource,
    depth,
    error,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    if resource == "manifest":
        _duplicate_manifest_key(manifest, depth)
    else:
        _duplicate_registry_key(manifest, registry, depth)
    before = _snapshot(tmp_path)

    with pytest.raises(ValueError, match=f"^{error}$"):
        validate_point_in_time_universe(manifest, registry)

    cli = _run_cli(
        "status",
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )
    make = _run_make(
        "point-in-time-universe-status",
        f"MANIFEST={manifest}",
        f"REGISTRY={registry}",
    )

    for result in (cli, make):
        assert result.returncode == 2
        assert error in result.stderr
        assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before


def test_duplicate_rights_keys_fail_rights_cli_and_make_without_writes(
    tmp_path,
):
    manifest, registry = build_valid_package(tmp_path)
    _duplicate_registry_key(manifest, registry, "nested")
    before = _snapshot(tmp_path)

    cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.commercial_source_rights",
            "--config",
            str(registry),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    make = _run_make(
        "commercial-source-rights",
        f"CONFIG={registry}",
    )

    for result in (cli, make):
        assert result.returncode == 2
        assert "source_rights_registry_duplicate_key" in result.stderr
        assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize(
    ("location", "value", "error"),
    [
        (
            "manifest_created_at",
            "2030-W01-2T00:00:00Z",
            "manifest_created_at_invalid",
        ),
        (
            "manifest_created_at",
            "2030-01-01T00:00Z",
            "manifest_created_at_invalid",
        ),
        (
            "train_end_at",
            "2020-W53-5T00:00:00Z",
            "manifest_evaluation_policy_invalid",
        ),
        (
            "train_end_at",
            "2021-01-01T00:00Z",
            "manifest_evaluation_policy_invalid",
        ),
    ],
)
def test_manifest_and_policy_timestamps_require_strict_rfc3339_utc(
    tmp_path,
    location,
    value,
    error,
):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)

    def mutate(raw):
        if location == "train_end_at":
            raw["evaluation_policy"][location] = value
        else:
            raw[location] = value

    _rewrite_manifest(manifest, mutate)

    with pytest.raises(ValueError, match=f"^{error}$"):
        load_universe_package(manifest, registry)


def test_malformed_contract_header_stops_validator_cli_and_make_without_writes(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    identity = manifest.parent / "identity.csv"
    identity.write_text(
        identity.read_text(encoding="utf-8").replace("issuer_id,", "", 1),
        encoding="utf-8",
    )
    _refresh_contract_digest(manifest, "security_identity")
    before = _snapshot(tmp_path)

    with pytest.raises(
        ValueError,
        match="^package_csv_columns_invalid$",
    ):
        validate_point_in_time_universe(manifest, registry)

    cli = _run_cli(
        "preview",
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )
    make = _run_make(
        "point-in-time-universe-preview",
        f"MANIFEST={manifest}",
        f"REGISTRY={registry}",
    )

    for result in (cli, make):
        assert result.returncode == 2
        assert "package_csv_columns_invalid" in result.stderr
        assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before










def test_present_event_cannot_contradict_not_applicable_manifest_policy(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            {"listing": "not_applicable"}
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "technical_validity").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "blocked"
    assert _decision(
        packet,
        "corporate_action_coverage",
    ).reason_codes == ("corporate_action_policy_not_applicable",)
    assert packet.analysis_eligible is False


@pytest.mark.parametrize(
    ("event_type", "listing_state_after", "updates"),
    [
        ("listing", "delisted", {}),
        ("listing", "suspended", {}),
    ],
)
def test_corporate_action_listing_state_contract_is_explicit(
    tmp_path,
    event_type,
    listing_state_after,
    updates,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        lambda rows: rows[0].update(
            event_type=event_type,
            listing_state_after=listing_state_after,
            **updates,
        ),
    )
    if event_type != "listing":
        require_event(manifest, event_type)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "technical_validity").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "blocked"
    assert _decision(
        packet,
        "corporate_action_coverage",
    ).reason_codes == ("corporate_action_listing_state_invalid",)
    assert _decision(packet, "delisting_coverage").status == "not_applicable"
    assert packet.analysis_eligible is False


def test_active_split_remains_analysis_eligible(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        lambda rows: rows[0].update(
            event_type="split",
            ratio_numerator="2",
            ratio_denominator="1",
            listing_state_after="active",
        ),
    )
    require_event(manifest, "split")

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "technical_validity").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").reason_codes == ()
    assert packet.analysis_eligible is True


@pytest.mark.parametrize(
    ("successor_security_id", "reason"),
    [
        ("sec-1", "corporate_action_successor_self"),
        ("unknown", "corporate_action_successor_invalid"),
        ("ambiguous", "corporate_action_successor_invalid"),
        ("sec-without-identity", "corporate_action_successor_identity_missing"),
    ],
)
def test_successor_must_be_distinct_explicit_and_cutoff_resolvable(
    tmp_path,
    successor_security_id,
    reason,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    set_successor_event(manifest, successor_security_id)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "technical_validity").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "blocked"
    assert reason in _decision(
        packet,
        "corporate_action_coverage",
    ).reason_codes
    assert packet.analysis_eligible is False


def test_ambiguous_cutoff_valid_successor_identity_is_blocked(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    add_successor_identity(manifest, "sec-successor")

    def add_ambiguous_identity(rows):
        rows.append(
            {
                **rows[-1],
                "identity_row_id": "id-successor-ambiguous",
                "issuer_id": "issuer-successor-ambiguous",
                "ticker": "OTHER",
                "source_ref": "fixture://identity/id-successor-ambiguous",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        add_ambiguous_identity,
    )
    set_successor_event(manifest, "sec-successor")

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == "blocked"
    assert (
        "corporate_action_successor_identity_ambiguous"
        in _decision(packet, "corporate_action_coverage").reason_codes
    )
    assert packet.analysis_eligible is False


def test_resolved_successor_cannot_leave_stale_original_membership_digest(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    add_successor_identity(manifest, "sec-successor")
    set_successor_event(manifest, "sec-successor")

    packet = validate_point_in_time_universe(manifest, registry)

    assert {item.sha256 for item in packet.membership_digests} == {
        hashlib.sha256(b"sec-1").hexdigest()
    }
    assert _decision(packet, "corporate_action_coverage").status == "blocked"
    assert (
        "corporate_action_successor_membership_inconsistent"
        in _decision(packet, "corporate_action_coverage").reason_codes
    )
    assert packet.analysis_eligible is False


def test_resolved_spinoff_successor_can_retain_parent_membership(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    add_successor_identity(manifest, "sec-spinoff")
    set_successor_event(
        manifest,
        "sec-spinoff",
        event_type="spinoff",
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert {item.sha256 for item in packet.membership_digests} == {
        hashlib.sha256(b"sec-1").hexdigest()
    }
    assert _decision(packet, "technical_validity").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").reason_codes == ()
    assert packet.analysis_eligible is True


def test_valid_unicode_successor_transition_is_deterministic_without_inference(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    successor_security_id = "後継-𐐷-🚀"
    add_successor_identity(manifest, successor_security_id)
    set_successor_event(manifest, successor_security_id)
    replace_membership_with_successor(
        manifest,
        successor_security_id,
    )

    first = validate_point_in_time_universe(manifest, registry)
    second = validate_point_in_time_universe(manifest, registry)
    expected_digest = hashlib.sha256(
        successor_security_id.encode("utf-8")
    ).hexdigest()

    assert first == second
    assert first.analysis_eligible is True
    assert _decision(first, "corporate_action_coverage").status == "passed"
    assert {item.sha256 for item in first.membership_digests} == {
        expected_digest
    }
    assert all(
        reference.row_id != "member-bench-1"
        and reference.row_id != "member-research-1"
        for reference in first.analysis_eligible_rows
    )


@pytest.mark.parametrize(
    ("location", "error"),
    [
        ("manifest_created_at", "manifest_created_at_invalid"),
        ("train_end_at", "manifest_evaluation_policy_invalid"),
    ],
)
def test_manifest_timestamp_precision_above_microseconds_is_rejected(
    tmp_path,
    location,
    error,
):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)

    def mutate(raw):
        value = "2030-01-01T00:00:00.0000001Z"
        if location == "train_end_at":
            raw["evaluation_policy"][location] = (
                "2021-01-01T00:00:00.0000001Z"
            )
        else:
            raw[location] = value

    _rewrite_manifest(manifest, mutate)

    with pytest.raises(ValueError, match=f"^{error}$"):
        load_universe_package(manifest, registry)


def test_contract_timestamp_100ns_after_cutoff_cannot_truncate_into_cutoff(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(
            retrieved_at="2021-01-01T00:00:00.0000001Z",
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "technical_validity").status == "blocked"
    assert _decision(packet, "technical_validity").reason_codes == (
        "schema_timestamp_invalid",
    )
    assert packet.analysis_eligible is False


@pytest.mark.parametrize("fraction", (".1", ".123456"))
def test_manifest_and_contract_timestamp_precision_boundaries_are_valid(
    tmp_path,
    fraction,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_manifest(
        manifest,
        lambda raw: raw.update(
            manifest_created_at=(
                f"2030-01-01T00:00:00{fraction}Z"
            ),
            observation_cutoff_at=(
                f"2021-01-01T00:00:00{fraction}Z"
            ),
        ),
    )
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(
            valid_from=f"2020-01-01T00:00:00{fraction}Z",
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "manifest_integrity").status == "passed"
    assert _decision(packet, "technical_validity").status == "passed"
    assert packet.analysis_eligible is True




def _set_identity_valid_to(
    manifest,
    security_id: str,
    valid_to: str,
) -> None:
    def mutate(rows):
        target = next(
            row
            for row in rows
            if row["security_id"] == security_id
        )
        target["valid_to"] = valid_to

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def _append_later_identity_interval(
    manifest,
    security_id: str,
) -> None:
    def mutate(rows):
        prior = next(
            row
            for row in rows
            if row["security_id"] == security_id
        )
        prior["valid_to"] = "2020-07-01T00:00:00Z"
        rows.append(
            {
                **prior,
                "identity_row_id": (
                    f"{prior['identity_row_id']}-later-interval"
                ),
                "valid_from": "2020-07-01T00:00:00Z",
                "valid_to": "",
                "source_ref": (
                    f"{prior['source_ref']}/later-interval"
                ),
                "source_published_at": "2020-07-01T00:00:00Z",
                "retrieved_at": "2020-07-02T00:00:00Z",
                "supersedes_identity_row_id": prior["identity_row_id"],
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )




def _append_identity_child_correction(
    manifest,
    security_id: str,
    *,
    valid_from: str,
    visible_at_cutoff: bool = True,
) -> None:
    def mutate(rows):
        prior = [
            row
            for row in rows
            if row["security_id"] == security_id
        ][-1]
        published = (
            "2020-08-01T00:00:00Z"
            if visible_at_cutoff
            else "2022-01-01T00:00:00Z"
        )
        retrieved = (
            "2020-08-02T00:00:00Z"
            if visible_at_cutoff
            else "2022-01-02T00:00:00Z"
        )
        rows.append(
            {
                **prior,
                "identity_row_id": (
                    f"{prior['identity_row_id']}-correction"
                ),
                "ticker": f"{prior['ticker']}-CORRECTED",
                "exchange": "ARCX",
                "valid_from": valid_from,
                "valid_to": "",
                "source_ref": f"{prior['source_ref']}/correction",
                "source_published_at": published,
                "retrieved_at": retrieved,
                "supersedes_identity_row_id": prior["identity_row_id"],
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def _action_package(
    tmp_path,
    event_type: str,
    identity_role: str,
):
    manifest, registry = build_valid_package(tmp_path)
    successor = f"sec-{event_type}-correction-{identity_role}"
    add_successor_identity(manifest, successor)
    set_successor_event(
        manifest,
        successor,
        event_type=event_type,
    )
    if event_type in {"merger", "acquisition"}:
        replace_membership_with_successor(manifest, successor)
    target = "sec-1" if identity_role == "predecessor" else successor
    return manifest, registry, target


@pytest.mark.parametrize(
    ("identity_role", "reason"),
    [
        (
            "predecessor",
            "corporate_action_predecessor_identity_missing",
        ),
        (
            "successor",
            "corporate_action_successor_identity_missing",
        ),
    ],
)
def test_action_identities_must_resolve_at_event_effective_time(
    tmp_path,
    identity_role,
    reason,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    add_successor_identity(manifest, "sec-successor")
    set_successor_event(manifest, "sec-successor")
    replace_membership_with_successor(manifest, "sec-successor")
    target_security_id = (
        "sec-1"
        if identity_role == "predecessor"
        else "sec-successor"
    )
    set_identity_valid_from(
        manifest,
        target_security_id,
        "2020-07-01T00:00:00Z",
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "technical_validity").status == "passed"
    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == (
        "blocked"
    )
    assert reason in _decision(
        packet,
        "corporate_action_coverage",
    ).reason_codes
    assert packet.analysis_eligible is False


@pytest.mark.parametrize(
    "event_type",
    ("merger", "acquisition", "spinoff"),
)
def test_valid_action_identities_resolve_at_event_effective_time(
    tmp_path,
    event_type,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    successor = f"sec-{event_type}"
    add_successor_identity(manifest, successor)
    set_successor_event(
        manifest,
        successor,
        event_type=event_type,
    )
    if event_type in {"merger", "acquisition"}:
        replace_membership_with_successor(manifest, successor)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert packet.analysis_eligible is True


@pytest.mark.parametrize("event_type", ("merger", "acquisition"))
def test_replacement_identity_boundary_resolves_both_endpoints(
    tmp_path,
    event_type,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    successor = f"sec-{event_type}-boundary"
    add_successor_identity(manifest, successor)
    set_successor_event(
        manifest,
        successor,
        event_type=event_type,
    )
    replace_membership_with_successor(manifest, successor)
    _set_identity_valid_to(
        manifest,
        "sec-1",
        "2020-06-01T00:00:00Z",
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert packet.analysis_eligible is True


@pytest.mark.parametrize(
    ("event_type", "identity_role"),
    [
        ("merger", "predecessor"),
        ("merger", "successor"),
        ("acquisition", "predecessor"),
        ("acquisition", "successor"),
        ("spinoff", "predecessor"),
        ("spinoff", "successor"),
    ],
)
def test_action_endpoint_uses_earlier_lineage_valid_identity_interval(
    tmp_path,
    event_type,
    identity_role,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    successor = f"sec-{event_type}-history-{identity_role}"
    add_successor_identity(manifest, successor)
    set_successor_event(
        manifest,
        successor,
        event_type=event_type,
    )
    if event_type in {"merger", "acquisition"}:
        replace_membership_with_successor(manifest, successor)
    _append_later_identity_interval(
        manifest,
        "sec-1" if identity_role == "predecessor" else successor,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "identity_coverage").status == "passed"
    assert _decision(packet, "corporate_action_coverage").status == "passed"
    assert packet.analysis_eligible is True


@pytest.mark.parametrize(
    ("event_type", "identity_role", "reason"),
    [
        (
            "merger",
            "predecessor",
            "corporate_action_predecessor_identity_missing",
        ),
        (
            "merger",
            "successor",
            "corporate_action_successor_identity_missing",
        ),
        (
            "acquisition",
            "predecessor",
            "corporate_action_predecessor_identity_missing",
        ),
        (
            "acquisition",
            "successor",
            "corporate_action_successor_identity_missing",
        ),
        (
            "spinoff",
            "predecessor",
            "corporate_action_predecessor_identity_missing",
        ),
        (
            "spinoff",
            "successor",
            "corporate_action_successor_identity_missing",
        ),
    ],
)
def test_visible_identity_correction_replaces_superseded_interval(
    tmp_path,
    event_type,
    identity_role,
    reason,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry, target = _action_package(
        tmp_path,
        event_type,
        identity_role,
    )
    append_identity_correction(
        manifest,
        target,
        valid_from=(
            "2020-01-01T00:00:00Z"
            if identity_role == "predecessor"
            else "2020-07-01T00:00:00Z"
        ),
        valid_to=(
            "2020-05-01T00:00:00Z"
            if identity_role == "predecessor"
            else ""
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == (
        "blocked"
    )
    assert _decision(
        packet,
        "corporate_action_coverage",
    ).reason_codes == (reason,)
    assert packet.analysis_eligible is False


@pytest.mark.parametrize(
    ("event_type", "identity_role"),
    [
        ("merger", "predecessor"),
        ("merger", "successor"),
        ("acquisition", "predecessor"),
        ("acquisition", "successor"),
        ("spinoff", "predecessor"),
        ("spinoff", "successor"),
    ],
)
def test_visible_identity_correction_covering_event_is_valid(
    tmp_path,
    event_type,
    identity_role,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry, target = _action_package(
        tmp_path,
        event_type,
        identity_role,
    )
    append_identity_correction(
        manifest,
        target,
        valid_from=(
            "2020-01-01T00:00:00Z"
            if identity_role == "predecessor"
            else "2020-06-01T00:00:00Z"
        ),
        valid_to=(
            "2020-06-01T00:00:00Z"
            if (
                identity_role == "predecessor"
                and event_type in {"merger", "acquisition"}
            )
            else ""
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == "passed"


@pytest.mark.parametrize(
    ("event_type", "identity_role"),
    [
        ("merger", "predecessor"),
        ("merger", "successor"),
        ("acquisition", "predecessor"),
        ("acquisition", "successor"),
        ("spinoff", "predecessor"),
        ("spinoff", "successor"),
    ],
)
def test_post_cutoff_identity_correction_does_not_change_event_view(
    tmp_path,
    event_type,
    identity_role,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry, target = _action_package(
        tmp_path,
        event_type,
        identity_role,
    )
    append_identity_correction(
        manifest,
        target,
        valid_from=(
            "2020-01-01T00:00:00Z"
            if identity_role == "predecessor"
            else "2020-07-01T00:00:00Z"
        ),
        valid_to=(
            "2020-05-01T00:00:00Z"
            if identity_role == "predecessor"
            else ""
        ),
        visible_at_cutoff=False,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == "passed"


@pytest.mark.parametrize(
    ("event_type", "identity_role", "reason"),
    [
        (
            "merger",
            "predecessor",
            "corporate_action_predecessor_identity_missing",
        ),
        (
            "merger",
            "successor",
            "corporate_action_successor_identity_missing",
        ),
        (
            "acquisition",
            "predecessor",
            "corporate_action_predecessor_identity_missing",
        ),
        (
            "acquisition",
            "successor",
            "corporate_action_successor_identity_missing",
        ),
        (
            "spinoff",
            "predecessor",
            "corporate_action_predecessor_identity_missing",
        ),
        (
            "spinoff",
            "successor",
            "corporate_action_successor_identity_missing",
        ),
    ],
)
def test_child_correction_cannot_leave_obsolete_ancestor_effective(
    tmp_path,
    event_type,
    identity_role,
    reason,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry, target = _action_package(
        tmp_path,
        event_type,
        identity_role,
    )
    _append_later_identity_interval(manifest, target)
    _append_identity_child_correction(
        manifest,
        target,
        valid_from="2020-08-01T00:00:00Z",
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(
        packet,
        "corporate_action_coverage",
    ).reason_codes == (reason,)


def test_post_cutoff_child_correction_preserves_prior_contiguous_view(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry, target = _action_package(
        tmp_path,
        "merger",
        "successor",
    )
    _append_later_identity_interval(manifest, target)
    _append_identity_child_correction(
        manifest,
        target,
        valid_from="2020-08-01T00:00:00Z",
        visible_at_cutoff=False,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "corporate_action_coverage").status == "passed"


def test_spinoff_predecessor_end_boundary_is_not_active_at_event(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry, target = _action_package(
        tmp_path,
        "spinoff",
        "predecessor",
    )
    _set_identity_valid_to(
        manifest,
        target,
        "2020-06-01T00:00:00Z",
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(
        packet,
        "corporate_action_coverage",
    ).reason_codes == (
        "corporate_action_predecessor_identity_missing",
    )


def _append_listing_state_events(
    manifest,
    events: tuple[tuple[str, str, str], ...],
) -> None:
    def mutate(rows):
        base = rows[0]
        for event_type, listing_state_after, date in events:
            rows.append(
                {
                    **base,
                    "event_row_id": f"event-{event_type}-{date}",
                    "event_type": event_type,
                    "effective_at": f"{date}T00:00:00Z",
                    "listing_state_after": listing_state_after,
                    "source_ref": (
                        f"fixture://event/{event_type}/{date}"
                    ),
                    "source_published_at": f"{date}T00:00:00Z",
                    "retrieved_at": f"{date}T12:00:00Z",
                    "supersedes_event_row_id": "",
                }
            )

    _rewrite_csv_and_manifest(manifest, "events", mutate)
    _rewrite_manifest(
        manifest,
        lambda raw: raw["corporate_action_policy"].update(
            {
                event_type: "required"
                for event_type, _, _ in events
            }
        ),
    )


@pytest.mark.parametrize(
    ("event_type", "listing_state_after"),
    [
        ("delisting", "delisted"),
        ("suspension", "suspended"),
    ],
)
def test_first_observed_listing_state_does_not_invent_prior_history(
    tmp_path,
    event_type,
    listing_state_after,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        lambda rows: rows[0].update(
            event_type=event_type,
            listing_state_after=listing_state_after,
        ),
    )
    require_event(manifest, event_type)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "delisting_coverage").status == "passed"
    assert _decision(packet, "delisting_coverage").reason_codes == ()
    assert packet.analysis_eligible is True


def test_active_delisted_suspended_transition_is_rejected(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_listing_state_events(
        manifest,
        (
            ("delisting", "delisted", "2020-06-01"),
            ("suspension", "suspended", "2020-07-01"),
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "delisting_coverage").status == "blocked"
    assert _decision(packet, "delisting_coverage").reason_codes == (
        "delisting_transition_invalid",
    )
    assert packet.analysis_eligible is False


def test_listing_suspension_reactivation_delisting_chronology_is_valid(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _append_listing_state_events(
        manifest,
        (
            ("suspension", "suspended", "2020-04-01"),
            ("reactivation", "active", "2020-05-01"),
            ("delisting", "delisted", "2020-06-01"),
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "technical_validity").status == "passed"
    assert _decision(packet, "delisting_coverage").status == "passed"
    assert _decision(packet, "delisting_coverage").reason_codes == ()
    assert packet.analysis_eligible is True
    assert {item.sha256 for item in packet.membership_digests} == {
        hashlib.sha256(b"sec-1").hexdigest()
    }
