import pytest

from tests.point_in_time_universe_fixture import build_valid_package
from tests.test_point_in_time_universe_contracts import _rewrite_csv_and_manifest


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
