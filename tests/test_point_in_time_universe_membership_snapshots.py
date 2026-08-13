from __future__ import annotations

import pytest

from tests.point_in_time_universe_remediation_fixtures import (
    add_second_security_evidence,
)
from tests.point_in_time_universe_fixture import build_valid_package
from tests.test_point_in_time_universe import (
    _decision,
    _read_contract_rows,
    _replace_contract_rows,
    _sha256_members,
)
from tests.test_point_in_time_universe_cli import (
    _run_cli,
    _snapshot,
)
from tests.test_point_in_time_universe_contracts import (
    _rewrite_csv_and_manifest,
)


OMISSION_REASON = "membership_snapshot_omission_unexplained"
LATEST_SNAPSHOT_AT = "2020-06-01T00:00:00Z"


def _membership_row(
    rows,
    *,
    security_id: str,
    state: str,
    row_id: str,
    observation_at: str = LATEST_SNAPSHOT_AT,
    source_published_at: str = LATEST_SNAPSHOT_AT,
    retrieved_at: str = "2020-06-02T00:00:00Z",
    supersedes: str = "",
):
    base = next(row for row in rows if row["universe_id"] == "bench-1")
    return {
        **base,
        "membership_row_id": row_id,
        "security_id": security_id,
        "membership_state": state,
        "effective_from": observation_at,
        "observation_at": observation_at,
        "source_ref": f"fixture://membership/{row_id}",
        "source_published_at": source_published_at,
        "retrieved_at": retrieved_at,
        "supersedes_membership_row_id": supersedes,
    }


def _configure_later_benchmark_snapshot(
    manifest,
    *,
    restatement: str | None = None,
    invalid_exclusion: str | None = None,
) -> None:
    add_second_security_evidence(manifest)

    def mutate(rows):
        rows.append(
            _membership_row(
                rows,
                security_id="sec-2",
                state="included",
                row_id="member-bench-sec-2-latest",
            )
        )
        if restatement is not None:
            rows.append(
                _membership_row(
                    rows,
                    security_id="sec-1",
                    state=restatement,
                    row_id="member-bench-sec-1-latest",
                    supersedes="member-bench-1",
                )
            )
        elif invalid_exclusion == "wrong_timestamp":
            rows.append(
                _membership_row(
                    rows,
                    security_id="sec-1",
                    state="excluded",
                    row_id="member-bench-sec-1-wrong-time",
                    observation_at="2020-05-01T00:00:00Z",
                    source_published_at="2020-05-01T00:00:00Z",
                    retrieved_at="2020-05-02T00:00:00Z",
                    supersedes="member-bench-1",
                )
            )
        elif invalid_exclusion == "future":
            rows.append(
                _membership_row(
                    rows,
                    security_id="sec-1",
                    state="excluded",
                    row_id="member-bench-sec-1-future",
                    observation_at="2022-01-01T00:00:00Z",
                    source_published_at="2022-01-01T00:00:00Z",
                    retrieved_at="2022-01-02T00:00:00Z",
                    supersedes="member-bench-1",
                )
            )
        elif invalid_exclusion == "unavailable":
            rows.append(
                _membership_row(
                    rows,
                    security_id="sec-1",
                    state="excluded",
                    row_id="member-bench-sec-1-unavailable",
                    source_published_at="2020-06-01T00:00:00Z",
                    retrieved_at="2022-01-01T00:00:00Z",
                    supersedes="member-bench-1",
                )
            )
        elif invalid_exclusion == "superseded":
            rows.append(
                _membership_row(
                    rows,
                    security_id="sec-1",
                    state="excluded",
                    row_id="member-bench-sec-1-superseded",
                    supersedes="member-bench-1",
                )
            )
            rows.append(
                _membership_row(
                    rows,
                    security_id="sec-1",
                    state="excluded",
                    row_id="member-bench-sec-1-correction",
                    observation_at="2020-05-01T00:00:00Z",
                    source_published_at="2020-07-01T00:00:00Z",
                    retrieved_at="2020-07-02T00:00:00Z",
                    supersedes="member-bench-sec-1-superseded",
                )
            )
        elif invalid_exclusion == "ambiguous":
            rows.append(
                _membership_row(
                    rows,
                    security_id="sec-1",
                    state="excluded",
                    row_id="member-bench-sec-1-ambiguous",
                )
            )

    _rewrite_csv_and_manifest(manifest, "membership", mutate)


def _omission_exclusions(packet):
    return tuple(
        row
        for row in packet.excluded
        if OMISSION_REASON in row.reason_codes
    )


def test_latest_complete_snapshot_blocks_unexplained_prior_member_omission(
    tmp_path,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _configure_later_benchmark_snapshot(manifest)

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "membership_coverage").status == "blocked"
    assert OMISSION_REASON in _decision(
        packet,
        "membership_coverage",
    ).reason_codes
    assert _decision(packet, "reproduction_ready").status == "blocked"
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )
    assert {
        (digest.universe_id, digest.evaluation_at)
        for digest in packet.membership_digests
    } == {("research-1", "2021-01-01T00:00:00Z")}
    assert _omission_exclusions(packet)[0].row_id == "member-bench-1"
    assert _omission_exclusions(packet)[0].reason_codes == (OMISSION_REASON,)
    assert packet.analysis_eligible is False
    assert packet.analysis_eligible_rows == ()


def test_latest_snapshot_explicit_exclusion_closes_omission_gate(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _configure_later_benchmark_snapshot(
        manifest,
        restatement="excluded",
    )

    packet = validate_point_in_time_universe(manifest, registry)
    digests = {
        digest.universe_id: digest
        for digest in packet.membership_digests
    }

    assert _decision(packet, "membership_coverage").status == "passed"
    assert _decision(packet, "reproduction_ready").status == "passed"
    assert digests["bench-1"].member_count == 1
    assert digests["bench-1"].sha256 == _sha256_members("sec-2")
    assert _omission_exclusions(packet) == ()
    assert packet.analysis_eligible is True


def test_latest_snapshot_repeated_inclusion_closes_omission_gate(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _configure_later_benchmark_snapshot(
        manifest,
        restatement="included",
    )

    packet = validate_point_in_time_universe(manifest, registry)
    bench = next(
        digest
        for digest in packet.membership_digests
        if digest.universe_id == "bench-1"
    )

    assert _decision(packet, "membership_coverage").status == "passed"
    assert _decision(packet, "reproduction_ready").status == "passed"
    assert bench.member_count == 2
    assert bench.sha256 == _sha256_members("sec-1", "sec-2")
    assert _omission_exclusions(packet) == ()
    assert packet.analysis_eligible is True


@pytest.mark.parametrize(
    "invalid_exclusion",
    (
        "wrong_timestamp",
        "future",
        "unavailable",
        "superseded",
        "ambiguous",
    ),
)
def test_non_authoritative_exclusion_does_not_close_latest_snapshot_gate(
    tmp_path,
    invalid_exclusion,
):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _configure_later_benchmark_snapshot(
        manifest,
        invalid_exclusion=invalid_exclusion,
    )

    packet = validate_point_in_time_universe(manifest, registry)

    assert _decision(packet, "membership_coverage").status == "blocked"
    assert OMISSION_REASON in _decision(
        packet,
        "membership_coverage",
    ).reason_codes
    assert all(
        digest.universe_id != "bench-1"
        for digest in packet.membership_digests
    )
    assert _omission_exclusions(packet)[0].row_id == "member-bench-1"
    assert packet.analysis_eligible is False
    assert packet.analysis_eligible_rows == ()


def test_snapshot_omission_is_input_order_deterministic(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    packets = []
    for index, reverse in enumerate((False, True)):
        root = tmp_path / str(index)
        root.mkdir()
        manifest, registry = build_valid_package(root)
        _configure_later_benchmark_snapshot(manifest)
        if reverse:
            _replace_contract_rows(
                manifest,
                "membership",
                list(reversed(_read_contract_rows(manifest, "membership"))),
            )
        packets.append(
            validate_point_in_time_universe(manifest, registry)
        )

    first, second = packets
    assert first.decisions == second.decisions
    assert first.membership_digests == second.membership_digests
    assert {
        (row.row_id, row.reason_codes)
        for row in first.excluded
    } == {
        (row.row_id, row.reason_codes)
        for row in second.excluded
    }
    assert first.analysis_eligible_rows == second.analysis_eligible_rows == ()


def test_snapshot_omission_is_universe_and_evaluation_scoped(tmp_path):
    from src.point_in_time_universe import validate_point_in_time_universe

    manifest, registry = build_valid_package(tmp_path)
    _configure_later_benchmark_snapshot(manifest)

    def add_earlier_benchmark_evaluation(rows):
        base = next(row for row in rows if row["universe_id"] == "bench-1")
        rows.append(
            {
                **base,
                "evaluation_row_id": "eval-bench-earlier",
                "evaluation_at": "2020-03-01T00:00:00Z",
                "available_at": "2020-03-01T00:00:00Z",
                "source_ref": "fixture://evaluation/bench-earlier",
            }
        )

    _rewrite_csv_and_manifest(
        manifest,
        "evaluations",
        add_earlier_benchmark_evaluation,
    )

    packet = validate_point_in_time_universe(manifest, registry)

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
            "2020-03-01T00:00:00Z",
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
    assert {
        row.row_id
        for row in _omission_exclusions(packet)
    } == {"member-bench-1"}
    assert all(
        row.row_id != "member-research-1"
        for row in _omission_exclusions(packet)
    )
    assert _decision(packet, "reproduction_ready").reason_codes == (
        "reproduction_digest_missing",
    )


@pytest.mark.parametrize("command", ("status", "preview"))
def test_snapshot_omission_is_cli_readable_and_write_free(
    tmp_path,
    command,
):
    manifest, registry = build_valid_package(tmp_path)
    _configure_later_benchmark_snapshot(manifest)
    before = _snapshot(tmp_path)

    result = _run_cli(
        command,
        "--manifest",
        str(manifest),
        "--registry",
        str(registry),
    )

    assert result.returncode == 0
    assert "membership_coverage: blocked" in result.stdout
    assert OMISSION_REASON in result.stdout
    assert "reproduction_ready: blocked" in result.stdout
    assert "reproduction_digest_missing" in result.stdout
    assert "Traceback" not in result.stderr
    assert _snapshot(tmp_path) == before
