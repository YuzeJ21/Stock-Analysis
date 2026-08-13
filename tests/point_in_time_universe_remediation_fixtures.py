from __future__ import annotations

from tests.test_point_in_time_universe import _rewrite_manifest
from tests.test_point_in_time_universe_contracts import (
    _rewrite_csv_and_manifest,
)

STABLE_MEMBER_DIGEST = (
    "e54b5c950961a603394187d7f98d6146612751f87d47f95e7076f880a2f25e5b"
)


def walk_forward_rows() -> list[dict[str, str]]:
    return [
        {
            "evaluation_row_id": f"eval-{universe}-{year}",
            "universe_id": universe,
            "evaluation_at": f"{year}-01-01T00:00:00Z",
            "available_at": f"{year}-01-01T00:00:00Z",
            "partition": "walk_forward",
            "source_ref": f"fixture://evaluation/{universe}/{year}",
        }
        for universe in ("bench-1", "research-1")
        for year in (2021, 2022, 2023)
    ]


def add_second_security_evidence(manifest) -> None:
    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        lambda rows: rows.append(
            {
                **rows[0],
                "identity_row_id": "id-2",
                "security_id": "sec-2",
                "issuer_id": "issuer-2",
                "ticker": "BBB",
                "source_ref": "fixture://identity/id-2",
            }
        ),
    )
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        lambda rows: rows.append(
            {
                **rows[0],
                "event_row_id": "event-sec-2-listing",
                "security_id": "sec-2",
                "source_ref": "fixture://event/sec-2-listing",
            }
        ),
    )


def append_action_event(
    manifest,
    event_type: str,
    *,
    security_id: str = "sec-1",
    effective_at: str = "2020-06-01T00:00:00Z",
    visible_at_cutoff: bool = True,
    required_policy: bool = True,
) -> None:
    def mutate(rows):
        rows.append(
            {
                **rows[0],
                "event_row_id": f"event-{event_type}",
                "security_id": security_id,
                "event_type": event_type,
                "effective_at": effective_at,
                "successor_security_id": "",
                "ratio_numerator": "",
                "ratio_denominator": "",
                "listing_state_after": "",
                "source_ref": f"fixture://event/{event_type}",
                "source_published_at": (
                    effective_at
                    if visible_at_cutoff
                    else "2022-01-01T00:00:00Z"
                ),
                "retrieved_at": (
                    effective_at
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


def require_event(manifest, event_type: str) -> None:
    def mutate(raw):
        raw["corporate_action_policy"]["listing"] = "not_applicable"
        raw["corporate_action_policy"][event_type] = "required"

    _rewrite_manifest(manifest, mutate)


def add_successor_identity(
    manifest,
    successor_security_id: str,
) -> None:
    def mutate(rows):
        rows.append(
            {
                **rows[0],
                "identity_row_id": "id-successor",
                "security_id": successor_security_id,
                "issuer_id": "issuer-successor",
                "ticker": "NEXT",
                "valid_from": "2020-06-01T00:00:00Z",
                "source_ref": "fixture://identity/id-successor",
                "source_published_at": "2020-06-01T00:00:00Z",
                "retrieved_at": "2020-06-02T00:00:00Z",
            }
        )

    _rewrite_csv_and_manifest(manifest, "security_identity", mutate)


def set_successor_event(
    manifest,
    successor_security_id: str,
    *,
    event_type: str = "merger",
) -> None:
    _rewrite_csv_and_manifest(
        manifest,
        "events",
        lambda rows: rows[0].update(
            event_type=event_type,
            effective_at="2020-06-01T00:00:00Z",
            successor_security_id=successor_security_id,
            listing_state_after="",
            source_published_at="2020-06-01T00:00:00Z",
            retrieved_at="2020-06-02T00:00:00Z",
        ),
    )
    require_event(manifest, event_type)


def replace_membership_with_successor(
    manifest,
    successor_security_id: str,
) -> None:
    def mutate(rows):
        replacements = []
        for original in rows:
            replacements.extend(
                [
                    {
                        **original,
                        "membership_row_id": (
                            f"{original['membership_row_id']}-excluded"
                        ),
                        "membership_state": "excluded",
                        "effective_from": "2020-06-01T00:00:00Z",
                        "observation_at": "2020-06-01T00:00:00Z",
                        "source_ref": (
                            f"{original['source_ref']}/excluded"
                        ),
                        "source_published_at": "2020-06-01T00:00:00Z",
                        "retrieved_at": "2020-06-02T00:00:00Z",
                        "supersedes_membership_row_id": (
                            original["membership_row_id"]
                        ),
                    },
                    {
                        **original,
                        "membership_row_id": (
                            f"member-successor-{original['universe_id']}"
                        ),
                        "security_id": successor_security_id,
                        "effective_from": "2020-06-01T00:00:00Z",
                        "observation_at": "2020-06-01T00:00:00Z",
                        "source_ref": (
                            "fixture://membership/successor/"
                            f"{original['universe_id']}"
                        ),
                        "source_published_at": "2020-06-01T00:00:00Z",
                        "retrieved_at": "2020-06-02T00:00:00Z",
                        "supersedes_membership_row_id": "",
                    },
                ]
            )
        rows.extend(replacements)

    _rewrite_csv_and_manifest(manifest, "membership", mutate)


def set_identity_valid_from(
    manifest,
    security_id: str,
    valid_from: str,
) -> None:
    def mutate(rows):
        target = next(
            row
            for row in rows
            if row["security_id"] == security_id
        )
        target["valid_from"] = valid_from

    _rewrite_csv_and_manifest(
        manifest,
        "security_identity",
        mutate,
    )


def append_identity_correction(
    manifest,
    security_id: str,
    *,
    valid_from: str,
    valid_to: str,
    visible_at_cutoff: bool = True,
) -> None:
    def mutate(rows):
        prior = next(
            row
            for row in rows
            if row["security_id"] == security_id
        )
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
                "exchange": "XNAS",
                "valid_from": valid_from,
                "valid_to": valid_to,
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
