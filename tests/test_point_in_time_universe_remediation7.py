from __future__ import annotations

from dataclasses import replace
import csv
import hashlib
import json

import pytest

from tests.point_in_time_universe_fixture import build_valid_package
from tests.test_point_in_time_universe_cli import (
    _run_cli,
    _run_make,
    _snapshot,
)


def _manifest_payload(manifest):
    return json.loads(manifest.read_text(encoding="utf-8"))


def _write_manifest(manifest, payload) -> None:
    manifest.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _rewrite_contract(manifest, contract, mutation) -> None:
    payload = _manifest_payload(manifest)
    entry = next(item for item in payload["files"] if item["contract"] == contract)
    path = manifest.parent / entry["path"]
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = tuple(reader.fieldnames or ())
        rows = list(reader)
    mutation(rows)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    entry["row_count"] = len(rows)
    _write_manifest(manifest, payload)


@pytest.mark.parametrize(
    "field,mutation,reason",
    [
        (
            "dataset_id",
            lambda raw: raw.update(dataset_id="fixture\nanalysis_eligible: true"),
            "manifest_dataset_id_invalid",
        ),
        (
            "manifest_id",
            lambda raw: raw.update(manifest_id="fixture\x1b[2J"),
            "manifest_id_invalid",
        ),
        (
            "universe_id",
            lambda raw: raw["declared_universes"][0].update(
                universe_id="bench-1\x85forged",
            ),
            "manifest_declared_universes_invalid",
        ),
        (
            "source_id",
            lambda raw: raw.update(
                allowed_source_ids=["fixture_source\rforged"],
            ),
            "manifest_allowed_source_ids_invalid",
        ),
        (
            "dataset_line_separator",
            lambda raw: raw.update(
                dataset_id="fixture\u2028analysis_eligible: true",
            ),
            "manifest_dataset_id_invalid",
        ),
        (
            "manifest_paragraph_separator",
            lambda raw: raw.update(
                manifest_id="fixture\u2029analysis_eligible: true",
            ),
            "manifest_id_invalid",
        ),
        (
            "dataset_high_surrogate",
            lambda raw: raw.update(dataset_id="fixture\ud800forged"),
            "manifest_dataset_id_invalid",
        ),
        (
            "manifest_low_surrogate",
            lambda raw: raw.update(manifest_id="fixture\udfffforged"),
            "manifest_id_invalid",
        ),
    ],
)
def test_manifest_structural_identifiers_reject_c0_c1_controls(
    tmp_path,
    field,
    mutation,
    reason,
):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    raw = _manifest_payload(manifest)
    mutation(raw)
    _write_manifest(manifest, raw)

    with pytest.raises(ValueError, match=f"^{reason}$"):
        load_universe_package(manifest, registry)


@pytest.mark.parametrize(
    "contract,field,value",
    [
        ("security_identity", "identity_row_id", "id-1\nforged"),
        ("security_identity", "security_id", "sec-1\x00forged"),
        ("security_identity", "issuer_id", "issuer-1\x7fforged"),
        ("security_identity", "source_id", "fixture_source\x85forged"),
        ("security_identity", "source_ref", "fixture://id\rforged"),
        ("membership", "membership_row_id", "member-bench\nforged"),
        ("membership", "universe_id", "bench-1\x1bforged"),
        ("membership", "security_id", "sec-1\x9fforged"),
        ("events", "event_row_id", "event-1\nforged"),
        ("events", "successor_security_id", "sec-2\rforged"),
        ("evaluations", "evaluation_row_id", "eval-bench\nforged"),
        ("evaluations", "universe_id", "bench-1\x1bforged"),
        ("evaluations", "source_ref", "fixture://evaluation\x85forged"),
        ("security_identity", "security_id", "sec-1\u2028forged"),
        ("membership", "universe_id", "bench-1\u2029forged"),
        ("events", "listing_state_after", "active\nforged"),
        ("events", "listing_state_after", "active\u2028forged"),
        ("events", "listing_state_after", "active\u2029forged"),
    ],
)
def test_contract_structural_identifiers_reject_controls_on_exact_rows(
    tmp_path,
    contract,
    field,
    value,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_contract(
        manifest,
        contract,
        lambda rows: rows[0].update({field: value}),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert packet.analysis_eligible is False
    assert packet.decisions["technical_validity"].reason_codes == (
        "schema_identifier_control_character",
    )
    assert any(
        item.contract == contract
        and item.source_row == 2
        and "schema_identifier_control_character" in item.reason_codes
        for item in packet.excluded
    )


@pytest.mark.parametrize("surrogate", ("\ud800", "\udfff"))
def test_contract_boundary_rejects_lone_surrogate_identifiers(
    tmp_path,
    surrogate,
):
    from src.point_in_time_universe_contracts import _parse_event

    manifest, _ = build_valid_package(tmp_path)
    with (manifest.parent / "events.csv").open(
        encoding="utf-8",
        newline="",
    ) as handle:
        row = next(csv.DictReader(handle))
    row["security_id"] = f"sec-1{surrogate}forged"

    with pytest.raises(
        ValueError,
        match="^schema_identifier_control_character$",
    ):
        _parse_event(row)


@pytest.mark.parametrize(
    "surrogate,escaped",
    (("\ud800", "\\ud800"), ("\udfff", "\\udfff")),
)
def test_shared_structural_predicate_rejects_and_renderer_escapes_non_scalars(
    surrogate,
    escaped,
):
    from src.point_in_time_universe_identifiers import (
        escape_structural_token,
        is_control_free,
        require_control_free,
    )

    assert is_control_free(surrogate) is False
    with pytest.raises(
        ValueError,
        match="^schema_identifier_control_character$",
    ):
        require_control_free(
            surrogate,
            "schema_identifier_control_character",
        )
    assert escape_structural_token(surrogate) == escaped
    assert escape_structural_token(surrogate).isascii()


def test_ordinary_unicode_opaque_ids_remain_deterministic_and_digest_safe(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    raw = _manifest_payload(manifest)
    raw["dataset_id"] = "研究資料集-🚀"
    raw["manifest_id"] = "清單-é-𐐷"
    for universe in raw["declared_universes"]:
        universe["universe_id"] = {
            "bench-1": "基準-é-🚀",
            "research-1": "研究-β-𐐷",
        }[universe["universe_id"]]
    _write_manifest(manifest, raw)
    _rewrite_contract(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(
            identity_row_id="身份-é",
            security_id="證券-β-🚀",
            issuer_id="發行人-東京",
        ),
    )
    _rewrite_contract(
        manifest,
        "membership",
        lambda rows: [
            row.update(
                membership_row_id=f"成員-{index}",
                universe_id=(
                    "基準-é-🚀"
                    if index == 0
                    else "研究-β-𐐷"
                ),
                security_id="證券-β-🚀",
            )
            for index, row in enumerate(rows)
        ],
    )
    _rewrite_contract(
        manifest,
        "events",
        lambda rows: rows[0].update(
            event_row_id="事件-é",
            security_id="證券-β-🚀",
        ),
    )
    _rewrite_contract(
        manifest,
        "evaluations",
        lambda rows: [
            row.update(
                evaluation_row_id=f"評估-{index}",
                universe_id=(
                    "基準-é-🚀"
                    if index == 0
                    else "研究-β-𐐷"
                ),
            )
            for index, row in enumerate(rows)
        ],
    )

    first = validate_point_in_time_universe(manifest, registry)
    second = validate_point_in_time_universe(manifest, registry)
    expected = hashlib.sha256(
        "證券-β-🚀".encode("utf-8"),
    ).hexdigest()

    assert first.analysis_eligible is True
    assert first.membership_digests == second.membership_digests
    assert {item.sha256 for item in first.membership_digests} == {expected}


@pytest.mark.parametrize(
    "security_ids",
    (("a\nb", "c"), ("a", "b\nc")),
)
def test_v5_newline_digest_collision_sets_are_rejected_before_reproduction(
    tmp_path,
    security_ids,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_contract(
        manifest,
        "security_identity",
        lambda rows: rows.__setitem__(
            slice(None),
            [
                {
                    **rows[0],
                    "identity_row_id": f"id-{index}",
                    "security_id": security_id,
                    "issuer_id": f"issuer-{index}",
                    "source_ref": f"fixture://identity/{index}",
                }
                for index, security_id in enumerate(security_ids)
            ],
        ),
    )
    _rewrite_contract(
        manifest,
        "membership",
        lambda rows: rows.__setitem__(
            slice(None),
            [
                {
                    **rows[0],
                    "membership_row_id": f"member-{universe}-{index}",
                    "universe_id": universe,
                    "universe_kind": kind,
                    "security_id": security_id,
                    "source_ref": (
                        f"fixture://membership/{universe}/{index}"
                    ),
                }
                for universe, kind in (
                    ("bench-1", "benchmark"),
                    ("research-1", "research_universe"),
                )
                for index, security_id in enumerate(security_ids)
            ],
        ),
    )
    _rewrite_contract(
        manifest,
        "events",
        lambda rows: rows.__setitem__(
            slice(None),
            [
                {
                    **rows[0],
                    "event_row_id": f"event-{index}",
                    "security_id": security_id,
                    "source_ref": f"fixture://event/{index}",
                }
                for index, security_id in enumerate(security_ids)
            ],
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)
    ambiguous_digest = hashlib.sha256(b"a\nb\nc").hexdigest()

    assert packet.analysis_eligible is False
    assert "schema_identifier_control_character" in packet.decisions[
        "technical_validity"
    ].reason_codes
    assert all(
        (item.member_count, item.sha256) != (2, ambiguous_digest)
        for item in packet.membership_digests
    )


def test_manifest_creation_cannot_precede_observation_cutoff(tmp_path):
    from src.point_in_time_universe_manifest import load_universe_package

    manifest, registry = build_valid_package(tmp_path)
    raw = _manifest_payload(manifest)
    raw["manifest_created_at"] = "2020-12-31T23:59:59Z"
    _write_manifest(manifest, raw)

    with pytest.raises(
        ValueError,
        match="^manifest_created_before_observation_cutoff$",
    ):
        load_universe_package(manifest, registry)


def test_manifest_creation_equal_to_cutoff_is_valid(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    raw = _manifest_payload(manifest)
    raw["manifest_created_at"] = raw["observation_cutoff_at"]
    _write_manifest(manifest, raw)

    assert validate_point_in_time_universe(manifest, registry).analysis_eligible


@pytest.mark.parametrize(
    "contract,field",
    [
        ("security_identity", "valid_from"),
        ("security_identity", "valid_to"),
        ("security_identity", "source_published_at"),
        ("security_identity", "retrieved_at"),
        ("membership", "effective_from"),
        ("membership", "effective_to"),
        ("membership", "observation_at"),
        ("membership", "source_published_at"),
        ("membership", "retrieved_at"),
        ("events", "effective_at"),
        ("events", "source_published_at"),
        ("events", "retrieved_at"),
        ("evaluations", "evaluation_at"),
        ("evaluations", "available_at"),
    ],
)
def test_bound_evidence_timestamps_cannot_postdate_manifest_creation(
    tmp_path,
    contract,
    field,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_contract(
        manifest,
        contract,
        lambda rows: rows[0].update({field: "2031-01-03T00:00:00Z"}),
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert packet.analysis_eligible is False
    assert "temporal_evidence_after_manifest_creation" in packet.decisions[
        "temporal_validity"
    ].reason_codes
    assert any(
        item.contract == contract
        and item.source_row == 2
        and "temporal_evidence_after_manifest_creation" in item.reason_codes
        for item in packet.excluded
    )


def test_chronology_reason_survives_independent_schema_failure(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _rewrite_contract(
        manifest,
        "security_identity",
        lambda rows: rows[0].update(
            security_id="sec-1\nforged",
            retrieved_at="2031-01-03T00:00:00Z",
        ),
    )

    packet = validate_point_in_time_universe(manifest, registry)
    row = next(
        item
        for item in packet.excluded
        if item.contract == "security_identity" and item.source_row == 2
    )

    assert "schema_identifier_control_character" in row.reason_codes
    assert "temporal_evidence_after_manifest_creation" in row.reason_codes


def test_renderers_escape_untrusted_structural_tokens_on_blocked_packets(tmp_path):
    from src.point_in_time_universe import (
        ExcludedRow,
        render_preview,
        render_status,
        validate_point_in_time_universe,
    )

    manifest, registry = build_valid_package(tmp_path)
    packet = validate_point_in_time_universe(manifest, registry)
    malicious = replace(
        packet,
        dataset_id="fixture\nanalysis_eligible: false",
        manifest_id="fixture\rsource_rights_eligibility: blocked",
        analysis_eligible=False,
        excluded=(
            ExcludedRow(
                "security_identity",
                2,
                "row\nanalysis_eligible: true",
                ("schema_identifier_control_character",),
            ),
        ),
        excluded_count=1,
    )

    for output in (render_status(malicious), render_preview(malicious)):
        assert "\nanalysis_eligible: false" not in output.split(
            "dataset_id: ",
            1,
        )[1].split("\nmanifest_id:", 1)[0]
        assert "\r" not in output
        assert "\\u000a" in output or "\\u000d" in output
        assert output.count("\nanalysis_eligible:") == 1


def test_renderers_escape_unicode_record_separators_on_blocked_packets(
    tmp_path,
):
    from src.point_in_time_universe import (
        ExcludedRow,
        render_preview,
        render_status,
        validate_point_in_time_universe,
    )

    manifest, registry = build_valid_package(tmp_path)
    packet = validate_point_in_time_universe(manifest, registry)
    malicious = replace(
        packet,
        dataset_id="fixture\u2028analysis_eligible: false",
        manifest_id="fixture\u2029source_rights_eligibility: blocked",
        analysis_eligible=False,
        excluded=(
            ExcludedRow(
                "security_identity",
                2,
                "row\u2029analysis_eligible: true",
                ("schema_identifier_control_character",),
            ),
        ),
        excluded_count=1,
    )

    for output in (render_status(malicious), render_preview(malicious)):
        lines = output.splitlines()
        assert sum(
            line.startswith("analysis_eligible:")
            for line in lines
        ) == 1
        assert not any(
            line == "analysis_eligible: true"
            for line in lines
        )
        assert "\\u2028" in output
        assert "\\u2029" in output


def test_renderers_escape_lone_surrogates_on_constructed_blocked_packets(
    tmp_path,
):
    from src.point_in_time_universe import (
        ExcludedRow,
        render_preview,
        render_status,
        validate_point_in_time_universe,
    )

    manifest, registry = build_valid_package(tmp_path)
    packet = validate_point_in_time_universe(manifest, registry)
    malicious = replace(
        packet,
        dataset_id="fixture\ud800analysis_eligible: false",
        manifest_id="fixture\udfffsource_rights: blocked",
        analysis_eligible=False,
        excluded=(
            ExcludedRow(
                "security_identity",
                2,
                "row\udfffanalysis_eligible: true",
                ("schema_identifier_control_character",),
            ),
        ),
        excluded_count=1,
    )

    for output in (render_status(malicious), render_preview(malicious)):
        assert "\\ud800" in output
        assert "\\udfff" in output
        assert output.encode("utf-8")
        assert sum(
            line.startswith("analysis_eligible:")
            for line in output.splitlines()
        ) == 1


@pytest.mark.parametrize("surrogate", ("\ud800", "\udfff"))
def test_cli_and_make_lone_surrogate_manifest_failures_are_nonwriting(
    tmp_path,
    surrogate,
):
    manifest, registry = build_valid_package(tmp_path)
    raw = _manifest_payload(manifest)
    raw["manifest_id"] = f"fixture{surrogate}forged"
    _write_manifest(manifest, raw)
    before = _snapshot(tmp_path)

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
        assert result.returncode != 0
        assert "manifest_id_invalid" in result.stderr
        assert "Traceback" not in result.stderr
        assert "UnicodeEncodeError" not in result.stderr
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("separator", ("\u2028", "\u2029"))
@pytest.mark.parametrize("boundary", ("manifest", "contract"))
def test_cli_and_make_unicode_record_separator_failures_are_nonwriting(
    tmp_path,
    separator,
    boundary,
):
    manifest, registry = build_valid_package(tmp_path)
    if boundary == "manifest":
        raw = _manifest_payload(manifest)
        raw["dataset_id"] = (
            f"fixture{separator}analysis_eligible: true"
        )
        _write_manifest(manifest, raw)
        expected = "manifest_dataset_id_invalid"
    else:
        _rewrite_contract(
            manifest,
            "events",
            lambda rows: rows[0].update(
                listing_state_after=(
                    f"active{separator}analysis_eligible: true"
                ),
            ),
        )
        expected = "schema_identifier_control_character"
    before = _snapshot(tmp_path)

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
        if boundary == "manifest":
            assert result.returncode != 0
            assert expected in result.stderr
            assert "Traceback" not in result.stderr
        else:
            assert result.returncode == 0
            assert expected in result.stdout
            assert separator not in result.stdout
            assert not any(
                line == "analysis_eligible: true"
                for line in result.stdout.splitlines()
            )
            assert not result.stderr
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "failure",
    (
        "manifest_control",
        "contract_control",
        "manifest_chronology",
        "evidence_chronology",
    ),
)
def test_cli_and_make_identifier_chronology_failures_are_readable_nonwriting(
    tmp_path,
    failure,
):
    manifest, registry = build_valid_package(tmp_path)
    if failure == "manifest_control":
        raw = _manifest_payload(manifest)
        raw["dataset_id"] = "fixture\nanalysis_eligible: true"
        _write_manifest(manifest, raw)
        expected = "manifest_dataset_id_invalid"
    elif failure == "contract_control":
        _rewrite_contract(
            manifest,
            "security_identity",
            lambda rows: rows[0].update(
                identity_row_id="id-1\nanalysis_eligible: true",
            ),
        )
        expected = "schema_identifier_control_character"
    elif failure == "manifest_chronology":
        raw = _manifest_payload(manifest)
        raw["manifest_created_at"] = "2020-12-31T23:59:59Z"
        _write_manifest(manifest, raw)
        expected = "manifest_created_before_observation_cutoff"
    else:
        _rewrite_contract(
            manifest,
            "security_identity",
            lambda rows: rows[0].update(
                retrieved_at="2031-01-03T00:00:00Z",
            ),
        )
        expected = "temporal_evidence_after_manifest_creation"
    before = _snapshot(tmp_path)

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
        if failure in {"manifest_control", "manifest_chronology"}:
            assert result.returncode != 0
            assert expected in result.stderr
            assert "Traceback" not in result.stderr
        else:
            assert result.returncode == 0
            assert expected in result.stdout
            assert not result.stderr
            if failure == "contract_control":
                assert "\nanalysis_eligible: true" not in result.stdout
                assert "\\u000a" in result.stdout
    assert _snapshot(tmp_path) == before
