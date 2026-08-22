from dataclasses import replace
import json
from pathlib import Path
from typing import Mapping

import pandas as pd

from src.commercial_source_rights import SourceRights
from src.golden_evidence_cohort import (
    build_golden_evidence_cohort,
    build_golden_evidence_cohort_from_evidence,
    main as golden_evidence_main,
    render_golden_evidence_cohort,
    render_golden_evidence_cohort_json,
)
from src.readiness_preview import (
    compare_readiness_frames,
    review_dcf_price_lineage,
    review_readiness_changes,
    review_readiness_promotions,
)


def _rights(source_id: str, *, supported_fields: tuple[str, ...], commercial_use: str = "approved") -> SourceRights:
    return SourceRights(
        source_id=source_id,
        display_name=source_id,
        permitted_use="source_backed_research",
        commercial_use=commercial_use,
        redistribution="derived_data_only",
        storage_limits="reviewed local rows",
        attribution="required",
        rate_limits="provider terms",
        authentication="none",
        expected_freshness="filing_driven",
        supported_fields=supported_fields,
        fallback_priority=1,
    )


def _registry() -> dict[str, SourceRights]:
    return {
        "approved_fundamentals": _rights(
            "approved_fundamentals",
            supported_fields=("revenue", "shares_outstanding", "filing_dates"),
        ),
        "scope_gap": _rights("scope_gap", supported_fields=("revenue",)),
        "approved_prices": _rights("approved_prices", supported_fields=("prices",)),
    }


def _readiness_row(ticker: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "ticker": ticker,
        "name": f"{ticker} Example",
        "asset_type": "company",
        "in_active_universe": True,
        "overall_readiness_state": "partial",
        "price_ready": True,
        "momentum_ready": True,
        "fundamentals_ready": True,
        "dcf_ready": True,
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "ready_features": "price, fundamentals, dcf",
        "partial_features": "",
        "blocked_features": "peer, earnings, analyst_estimates",
        "excluded_features": "",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    row.update(overrides)
    return row


def _default_fundamentals() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": ticker,
                "revenue": 100.0,
                "free_cash_flow": 20.0,
                "fcf_margin": 0.2,
                "shares_outstanding": 10.0,
                "source": "approved_fundamentals; filing_document" if ticker == "AAA" else "approved_fundamentals",
                "as_of_date": "2025-12-31",
                "sec_accession": f"filing:{ticker}",
            }
            for ticker in ("AAA", "BBB", "CCC")
        ]
        + [
            {
                "ticker": "ABAT",
                "revenue": 100.0,
                "free_cash_flow": 20.0,
                "fcf_margin": 0.2,
                "shares_outstanding": 10.0,
                "source": "scope_gap",
                "as_of_date": "2025-12-31",
                "sec_accession": "filing:ABAT",
            }
        ]
    )


def _packet(
    *,
    prices: pd.DataFrame | None = None,
    abat_source: str = "scope_gap",
    fundamentals: pd.DataFrame | None = None,
    include_etf: bool = True,
    method_asset_type: str = "etf",
    method_dcf_ready: bool = False,
    method_core_evidence: bool = False,
    rights_registry: Mapping[str, SourceRights] | None = None,
):
    registry = rights_registry if rights_registry is not None else _registry()
    saved = pd.DataFrame(
        [
            _readiness_row("AAA"),
            _readiness_row("BBB"),
            _readiness_row("CCC"),
            _readiness_row(
                "ABAT",
                in_active_universe=False,
                fundamentals_ready=False,
                dcf_ready=False,
                ready_features="price",
                blocked_features="fundamentals, dcf, peer, earnings, analyst_estimates",
            ),
            _readiness_row(
                "QQQ",
                asset_type=method_asset_type,
                dcf_ready=method_dcf_ready,
                ready_features="price, fundamentals, dcf" if method_dcf_ready else "price",
                blocked_features="fundamentals, peer, earnings, analyst_estimates",
                excluded_features="dcf",
            ),
        ]
    )
    if not include_etf:
        saved = saved.loc[saved["ticker"] != "QQQ"].copy()
    proposed = saved.copy()
    proposed.loc[proposed["ticker"] == "ABAT", ["fundamentals_ready", "dcf_ready"]] = True
    proposed.loc[proposed["ticker"] == "ABAT", "ready_features"] = "price, fundamentals, dcf"
    proposed.loc[proposed["ticker"] == "ABAT", "blocked_features"] = "peer, earnings, analyst_estimates"
    proposed = pd.concat(
        [
            proposed,
            pd.DataFrame(
                [
                    _readiness_row(
                        "NEW",
                        fundamentals_ready=True,
                        dcf_ready=True,
                        in_active_universe=False,
                    )
                ]
            ),
        ],
        ignore_index=True,
    )
    universe = pd.DataFrame(
        [
            {"ticker": "AAA", "asset_type": "company", "is_active_listing": True, "name": "AAA Example"},
            {"ticker": "BBB", "asset_type": "company", "is_active_listing": True, "name": "BBB Example"},
            {"ticker": "CCC", "asset_type": "company", "is_active_listing": True, "name": "CCC Example"},
            {"ticker": "ABAT", "asset_type": "company", "is_active_listing": True, "name": "ABAT Example"},
            {"ticker": "QQQ", "asset_type": method_asset_type, "is_active_listing": True, "name": "QQQ Example"},
            {"ticker": "NEW", "asset_type": "company", "is_active_listing": True, "name": "New Example"},
        ]
    )
    if fundamentals is None:
        fundamentals = _default_fundamentals()
        fundamentals.loc[fundamentals["ticker"] == "ABAT", "source"] = abat_source
        if method_core_evidence:
            fundamentals = pd.concat(
                [
                    fundamentals,
                    pd.DataFrame(
                        [
                            {
                                "ticker": "QQQ",
                                "revenue": 100.0,
                                "free_cash_flow": 20.0,
                                "fcf_margin": 0.2,
                                "shares_outstanding": 10.0,
                                "source": "approved_fundamentals",
                                "as_of_date": "2025-12-31",
                                "sec_accession": "filing:QQQ",
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )
    if prices is None:
        prices = pd.DataFrame(
            [
                {"ticker": ticker, "date": "2026-01-03", "close": 10.0, "source": "approved_prices", "source_ref": f"price:{ticker}", "retrieved_at": "2026-01-04T01:00:00Z"}
                for ticker in (("AAA", "BBB", "CCC", "QQQ") if method_core_evidence else ("AAA", "BBB", "CCC"))
            ]
            + [
                {"ticker": "ABAT", "date": "2026-01-03", "close": 10.0, "source": "", "source_ref": "", "retrieved_at": ""}
            ]
        )
    preview = compare_readiness_frames(saved, proposed, top_n=20)
    preview = replace(
        preview,
        promotion_review=review_readiness_promotions(
            saved, proposed, fundamentals, rights_registry=registry, top_n=20
        ),
        change_review=review_readiness_changes(saved, proposed, fundamentals),
        dcf_price_lineage_review=review_dcf_price_lineage(
            saved,
            proposed,
            prices,
            rights_registry=registry,
            review_cutoff="2026-01-06T00:00:00Z",
            top_n=20,
        ),
    )
    return build_golden_evidence_cohort_from_evidence(
        saved,
        proposed,
        universe,
        fundamentals,
        prices,
        preview=preview,
        rights_registry=registry,
        top_n=5,
        review_cutoff="2026-01-06T00:00:00Z",
    )


def test_packet_keeps_the_five_roles_fail_closed_and_preserves_composite_identifiers():
    packet = _packet()

    assert [(member.ticker, member.cohort_role) for member in packet.members] == [
        ("AAA", "saved_operating_company"),
        ("BBB", "saved_operating_company"),
        ("CCC", "saved_operating_company"),
        ("ABAT", "evidence_gap_control"),
        ("QQQ", "method_fit_exclusion"),
    ]
    assert packet.inspection_only is True
    assert packet.canonical_apply_authorized is False
    assert packet.readiness_materialization_authorized is False
    assert packet.source_rights_change_authorized is False
    assert packet.recommendation_authorized is False
    assert packet.repository_writes == ()

    composite = packet.members[0]
    assert "approved_fundamentals; filing_document" in composite.source_identifiers
    assert all("filing_document" not in value or value == "approved_fundamentals; filing_document" for value in composite.source_identifiers)

    abat = packet.members[3]
    assert abat.state == "withheld_price_lineage"
    assert "registered_field_scope" in abat.independent_blockers
    assert "price_lineage" in abat.independent_blockers
    assert "temporal_evidence" in abat.independent_blockers
    assert "exact_source_rights" in abat.independent_blockers
    assert "free_cash_flow" in abat.missing_registered_fields
    assert "source" in abat.price_lineage_omissions
    assert "missing_retrieved_at" in abat.temporal_evidence_omissions

    qqq = packet.members[4]
    assert qqq.state == "method_fit_excluded"
    assert qqq.method_fit_exclusions == ("non_operating_asset_type",)

    for member in packet.members:
        assert member.state not in {"activated", "current", "approved", "commercially_eligible"}
        assert member.saved_research_loop_status == "partial_saved_evidence_only"


def test_packet_never_pads_categories_and_json_is_deterministic_under_input_ties():
    first = _packet(include_etf=False)
    second = _packet(include_etf=False)
    capped = build_golden_evidence_cohort_from_evidence(
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        preview=compare_readiness_frames(pd.DataFrame(), pd.DataFrame(), top_n=1),
        rights_registry=_registry(),
        top_n=5,
    )

    assert [(member.ticker, member.cohort_role) for member in first.members] == [
        ("AAA", "saved_operating_company"),
        ("BBB", "saved_operating_company"),
        ("CCC", "saved_operating_company"),
        ("ABAT", "evidence_gap_control"),
    ]
    assert render_golden_evidence_cohort_json(first) == render_golden_evidence_cohort_json(second)
    assert capped.members == ()
    assert capped.status == "inspection_only"
    assert capped.inspection_only is True


def test_packet_reuses_price_lineage_review_for_missing_malformed_and_ambiguous_latest_rows():
    missing = _packet()
    malformed = _packet(
        prices=pd.DataFrame(
            [{"ticker": "ABAT", "date": "2026-01-03", "close": 10.0, "source": "approved_prices", "source_ref": "price:ABAT", "retrieved_at": "not-a-timestamp"}]
        )
    )
    ambiguous = _packet(
        prices=pd.DataFrame(
            [
                {"ticker": "ABAT", "date": "2026-01-03", "close": 10.0, "source": "approved_prices", "source_ref": "price:ABAT:1", "retrieved_at": "2026-01-04T01:00:00Z"},
                {"ticker": "ABAT", "date": "2026-01-03", "close": 11.0, "source": "approved_prices", "source_ref": "price:ABAT:2", "retrieved_at": "2026-01-04T01:00:00Z"},
            ]
        )
    )

    assert "missing_retrieved_at" in missing.members[3].temporal_evidence_omissions
    assert "invalid_retrieved_at" in malformed.members[3].temporal_evidence_omissions
    assert "ambiguous_latest_price_row" in ambiguous.members[3].price_lineage_omissions
    assert ambiguous.members[3].state == "withheld_price_lineage"


def test_real_saved_packet_has_the_verified_base_roles_and_never_uses_action_language():
    root = Path.cwd()
    packet = build_golden_evidence_cohort(root, top_n=5)
    rendered = render_golden_evidence_cohort_json(packet).lower()

    assert [member.ticker for member in packet.members] == ["AMD", "AVGO", "COHR", "ABAT", "QQQ"]
    assert json.loads(rendered)["repository_writes"] == []
    for forbidden in ("buy", "sell", "return", "target", "upside", "allocation", "position sizing"):
        assert forbidden not in rendered


def test_filing_date_is_withheld_when_the_registered_field_has_no_saved_value():
    packet = _packet()

    assert "filing_date" not in packet.members[1].usable_evidence_lanes
    assert "filing_date" in packet.members[1].withheld_evidence_lanes


def test_explicit_empty_rights_registry_is_not_replaced_by_configured_rights(monkeypatch):
    import src.golden_evidence_cohort as golden_evidence_cohort
    import src.readiness_engine as readiness_engine

    saved = pd.read_csv(Path.cwd() / "data" / "reports" / "ticker_readiness_report.csv")
    proposed = saved.copy()
    preview = compare_readiness_frames(saved, proposed, top_n=5)

    monkeypatch.setattr(golden_evidence_cohort, "build_readiness_impact_preview", lambda *args, **kwargs: preview)
    monkeypatch.setattr(
        readiness_engine,
        "build_ticker_readiness_report",
        lambda *args, **kwargs: {"ticker_readiness_report": proposed},
    )
    monkeypatch.setattr(
        golden_evidence_cohort,
        "load_source_rights_registry",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("configured registry must not be loaded")),
    )

    packet = build_golden_evidence_cohort(Path.cwd(), rights_registry={})

    assert packet.inspection_only is True


def test_default_text_packet_exposes_the_complete_member_contract():
    packet = _packet()
    rendered = render_golden_evidence_cohort(packet)

    for field in (
        "asset_type",
        "saved_readiness_identity",
        "proposed_readiness_identity",
        "missing_registered_fields",
        "provenance_omissions",
        "temporal_evidence_omissions",
        "price_lineage_omissions",
        "method_fit_exclusions",
        "owner_decision_required",
        "saved_research_loop_status",
        "research_only_boundary",
    ):
        assert f"  {field}=" in rendered


def test_missing_price_identity_and_its_rights_state_remain_explicit():
    abat = _packet().members[3]

    assert "<missing>" in abat.source_identifiers
    assert "<missing>:unknown_source" in abat.source_rights_states


def test_literal_index_asset_type_can_fill_the_method_fit_role_deterministically():
    packet = _packet(method_asset_type="index")

    assert packet.members[-1].ticker == "QQQ"
    assert packet.members[-1].asset_type == "index"
    assert packet.members[-1].state == "method_fit_excluded"
    assert packet.members[-1].method_fit_exclusions == ("non_operating_asset_type",)


def test_completed_price_and_fcf_evidence_is_usable_but_independent_blockers_remain_withheld():
    registry = {
        **_registry(),
        "approved_fundamentals": _rights(
            "approved_fundamentals",
            supported_fields=(
                "revenue",
                "free_cash_flow",
                "fcf_margin",
                "shares_outstanding",
                "filing_dates",
            ),
        ),
    }
    packet = _packet(rights_registry=registry)
    bbb = packet.members[1]
    abat = packet.members[3]

    assert {"price_lineage", "free_cash_flow", "fcf_margin"} <= set(bbb.usable_evidence_lanes)
    assert not {"price_lineage", "free_cash_flow", "fcf_margin"} & set(bbb.withheld_evidence_lanes)
    assert "free_cash_flow" not in abat.usable_evidence_lanes
    assert "registered_field_scope" in abat.independent_blockers


def test_malformed_or_nonfinite_fundamentals_stay_withheld_without_dcf_activation():
    fundamentals = _default_fundamentals().astype(object)
    bbb = fundamentals["ticker"] == "BBB"
    fundamentals.loc[bbb, "revenue"] = "not-a-number"
    fundamentals.loc[bbb, "free_cash_flow"] = float("nan")
    fundamentals.loc[bbb, "fcf_margin"] = True
    fundamentals.loc[bbb, "shares_outstanding"] = "inf"
    fundamentals.loc[bbb, "sec_filed_date"] = "not-a-date"
    registry = {
        **_registry(),
        "approved_fundamentals": _rights(
            "approved_fundamentals",
            supported_fields=(
                "revenue",
                "free_cash_flow",
                "fcf_margin",
                "shares_outstanding",
                "filing_dates",
            ),
        ),
    }

    member = _packet(fundamentals=fundamentals, rights_registry=registry).members[1]

    malformed_lanes = {
        "revenue",
        "free_cash_flow",
        "fcf_margin",
        "shares_outstanding",
        "filing_date",
    }
    assert not malformed_lanes & set(member.usable_evidence_lanes)
    assert malformed_lanes <= set(member.withheld_evidence_lanes)
    assert "dcf" not in member.usable_evidence_lanes
    assert "dcf" in member.withheld_evidence_lanes
    assert member.state not in {"activated", "current", "approved", "commercially_eligible"}


def test_finite_numeric_strings_and_a_valid_filing_date_remain_usable():
    fundamentals = _default_fundamentals().astype(object)
    bbb = fundamentals["ticker"] == "BBB"
    fundamentals.loc[bbb, "revenue"] = "100.25"
    fundamentals.loc[bbb, "free_cash_flow"] = "20.5"
    fundamentals.loc[bbb, "fcf_margin"] = "0.204"
    fundamentals.loc[bbb, "shares_outstanding"] = "10"
    fundamentals.loc[bbb, "sec_filed_date"] = "2026-01-02"
    registry = {
        **_registry(),
        "approved_fundamentals": _rights(
            "approved_fundamentals",
            supported_fields=(
                "revenue",
                "free_cash_flow",
                "fcf_margin",
                "shares_outstanding",
                "filing_dates",
            ),
        ),
    }

    member = _packet(fundamentals=fundamentals, rights_registry=registry).members[1]

    assert {
        "revenue",
        "free_cash_flow",
        "fcf_margin",
        "shares_outstanding",
        "filing_date",
        "price_lineage",
        "dcf",
    } <= set(member.usable_evidence_lanes)


def test_duplicate_fundamentals_preserve_every_exact_source_and_rights_state():
    fundamentals = _default_fundamentals()
    duplicate = dict(fundamentals.loc[fundamentals["ticker"] == "BBB"].iloc[0])
    duplicate["source"] = "unresolved_feed; filing_copy"
    duplicate["sec_accession"] = "filing:BBB:duplicate"
    fundamentals = pd.concat([fundamentals, pd.DataFrame([duplicate])], ignore_index=True)
    registry = {
        **_registry(),
        "approved_fundamentals": _rights(
            "approved_fundamentals",
            supported_fields=(
                "revenue",
                "free_cash_flow",
                "fcf_margin",
                "shares_outstanding",
                "filing_dates",
            ),
        ),
    }

    member = _packet(fundamentals=fundamentals, rights_registry=registry).members[1]

    assert member.source_identifiers == (
        "approved_fundamentals",
        "unresolved_feed; filing_copy",
        "approved_prices",
    )
    assert member.source_rights_states == (
        "approved_fundamentals:approved",
        "unresolved_feed; filing_copy:unknown_source",
        "approved_prices:approved",
    )
    assert member.provenance_omissions == ("fundamentals_row",)
    assert member.independent_blockers[:3] == (
        "provenance",
        "exact_source_rights",
        "registered_field_scope",
    )
    assert member.state == "withheld_provenance"
    assert member.owner_decision_required is True
    assert not {
        "revenue",
        "free_cash_flow",
        "fcf_margin",
        "shares_outstanding",
        "filing_date",
        "dcf",
    } & set(member.usable_evidence_lanes)


def test_duplicate_full_scope_sources_are_provenance_blocked_without_owner_scope_decision():
    fundamentals = _default_fundamentals()
    duplicate = dict(fundamentals.loc[fundamentals["ticker"] == "BBB"].iloc[0])
    duplicate["source"] = "approved_duplicate"
    duplicate["sec_accession"] = "filing:BBB:duplicate"
    fundamentals = pd.concat([fundamentals, pd.DataFrame([duplicate])], ignore_index=True)
    full_scope = (
        "revenue",
        "free_cash_flow",
        "fcf_margin",
        "shares_outstanding",
        "filing_dates",
    )
    registry = {
        **_registry(),
        "approved_fundamentals": _rights(
            "approved_fundamentals", supported_fields=full_scope
        ),
        "approved_duplicate": _rights(
            "approved_duplicate", supported_fields=full_scope
        ),
    }

    member = _packet(fundamentals=fundamentals, rights_registry=registry).members[1]

    assert member.source_rights_states[:2] == (
        "approved_fundamentals:approved",
        "approved_duplicate:approved",
    )
    assert member.missing_registered_fields == ()
    assert member.independent_blockers == ("provenance",)
    assert member.owner_decision_required is False
    assert member.state == "withheld_provenance"


def test_duplicate_mixed_scope_sources_keep_exact_missing_field_owner_decision():
    fundamentals = _default_fundamentals()
    duplicate = dict(fundamentals.loc[fundamentals["ticker"] == "BBB"].iloc[0])
    duplicate["source"] = "approved_partial_duplicate"
    duplicate["sec_accession"] = "filing:BBB:duplicate"
    fundamentals = pd.concat([fundamentals, pd.DataFrame([duplicate])], ignore_index=True)
    full_scope = (
        "revenue",
        "free_cash_flow",
        "fcf_margin",
        "shares_outstanding",
        "filing_dates",
    )
    registry = {
        **_registry(),
        "approved_fundamentals": _rights(
            "approved_fundamentals", supported_fields=full_scope
        ),
        "approved_partial_duplicate": _rights(
            "approved_partial_duplicate", supported_fields=("revenue",)
        ),
    }

    member = _packet(fundamentals=fundamentals, rights_registry=registry).members[1]

    assert member.missing_registered_fields == (
        "free_cash_flow",
        "fcf_margin",
        "shares_outstanding",
        "filing_dates",
    )
    assert member.independent_blockers == (
        "provenance",
        "registered_field_scope",
    )
    assert member.owner_decision_required is True
    assert member.state == "withheld_provenance"


def test_saved_dcf_is_usable_only_with_all_completed_saved_core_evidence():
    registry = {
        **_registry(),
        "approved_fundamentals": _rights(
            "approved_fundamentals",
            supported_fields=(
                "revenue",
                "free_cash_flow",
                "fcf_margin",
                "shares_outstanding",
                "filing_dates",
            ),
        ),
    }
    completed = _packet(rights_registry=registry).members[1]
    price_blocked = _packet(
        rights_registry=registry,
        prices=pd.DataFrame(
            [
                {
                    "ticker": "BBB",
                    "date": "2026-01-03",
                    "close": 10.0,
                    "source": "approved_prices",
                    "source_ref": "price:BBB",
                    "retrieved_at": "",
                }
            ]
        ),
    ).members[1]

    assert "dcf" in completed.usable_evidence_lanes
    assert "dcf" not in completed.withheld_evidence_lanes
    assert "dcf" not in price_blocked.usable_evidence_lanes
    assert "dcf" in price_blocked.withheld_evidence_lanes
    assert "temporal_evidence" in price_blocked.independent_blockers


def test_control_next_action_matches_the_merged_primary_price_lineage_blocker():
    abat = _packet().members[3]

    assert abat.state == "withheld_price_lineage"
    assert abat.independent_blockers[0] == "price_lineage"
    assert abat.next_evidence_review_action.startswith("Review exact latest-price lineage for ABAT:")
    assert "provider" in abat.next_evidence_review_action.lower()


def test_exact_rights_action_lists_only_the_unresolved_exact_source_identifiers():
    registry = {
        **_registry(),
        "approved_fundamentals": _rights(
            "approved_fundamentals",
            supported_fields=(
                "revenue",
                "free_cash_flow",
                "fcf_margin",
                "shares_outstanding",
                "filing_dates",
            ),
        ),
    }
    bbb = _packet(
        rights_registry=registry,
        prices=pd.DataFrame(
            [
                {
                    "ticker": "BBB",
                    "date": "2026-01-03",
                    "close": 10.0,
                    "source": "unknown_prices",
                    "source_ref": "price:BBB",
                    "retrieved_at": "2026-01-04T01:00:00Z",
                }
            ]
        ),
    ).members[1]

    assert bbb.independent_blockers[0] == "exact_source_rights"
    assert "approved_fundamentals:approved" in bbb.source_rights_states
    assert "unknown_prices:unknown_source" in bbb.source_rights_states
    assert "unknown_prices" in bbb.next_evidence_review_action
    assert "approved_fundamentals" not in bbb.next_evidence_review_action


def test_unresolved_composite_fundamental_rights_drive_the_primary_owner_action():
    member = _packet().members[0]

    assert member.source_identifiers == (
        "approved_fundamentals; filing_document",
        "approved_prices",
    )
    assert member.source_rights_states == (
        "approved_fundamentals; filing_document:unknown_source",
        "approved_prices:approved",
    )
    assert member.independent_blockers[:2] == (
        "exact_source_rights",
        "registered_field_scope",
    )
    assert member.state == "withheld_exact_source_rights"
    assert member.owner_decision_required is True
    assert member.next_evidence_review_action == (
        "Owner decision required for exact-source commercial rights on AAA: "
        "approved_fundamentals; filing_document; keep identifiers intact."
    )


def test_owner_decision_requires_only_rights_or_registered_scope_authority():
    full_registry = {
        **_registry(),
        "approved_fundamentals": _rights(
            "approved_fundamentals",
            supported_fields=(
                "revenue",
                "free_cash_flow",
                "fcf_margin",
                "shares_outstanding",
                "filing_dates",
            ),
        ),
    }
    temporal_only = _packet(
        rights_registry=full_registry,
        prices=pd.DataFrame(
            [
                {
                    "ticker": "BBB",
                    "date": "2026-01-03",
                    "close": 10.0,
                    "source": "approved_prices",
                    "source_ref": "price:BBB",
                    "retrieved_at": "2026-01-03T00:00:00Z",
                }
            ]
        ),
    ).members[1]
    rights_member = _packet(
        rights_registry=full_registry,
        prices=pd.DataFrame(
            [
                {
                    "ticker": "BBB",
                    "date": "2026-01-03",
                    "close": 10.0,
                    "source": "unknown_prices",
                    "source_ref": "price:BBB",
                    "retrieved_at": "2026-01-04T01:00:00Z",
                }
            ]
        ),
    ).members[1]
    scope_member = _packet(
        prices=pd.DataFrame(
            [
                {
                    "ticker": "ABAT",
                    "date": "2026-01-03",
                    "close": 10.0,
                    "source": "approved_prices",
                    "source_ref": "price:ABAT",
                    "retrieved_at": "2026-01-04T01:00:00Z",
                }
            ]
        ),
    ).members[3]

    assert temporal_only.independent_blockers == ("temporal_evidence",)
    assert temporal_only.owner_decision_required is False
    assert "exact_source_rights" in rights_member.independent_blockers
    assert rights_member.owner_decision_required is True
    assert scope_member.independent_blockers == ("registered_field_scope",)
    assert scope_member.owner_decision_required is True


def test_method_fit_exclusion_overrides_stale_saved_dcf_and_completed_core_evidence():
    registry = {
        **_registry(),
        "approved_fundamentals": _rights(
            "approved_fundamentals",
            supported_fields=(
                "revenue",
                "free_cash_flow",
                "fcf_margin",
                "shares_outstanding",
                "filing_dates",
            ),
        ),
    }
    qqq = _packet(
        method_asset_type="index",
        method_dcf_ready=True,
        method_core_evidence=True,
        rights_registry=registry,
    ).members[-1]

    assert qqq.state == "method_fit_excluded"
    assert qqq.method_fit_exclusions == ("non_operating_asset_type",)
    assert "dcf" not in qqq.usable_evidence_lanes


def test_missing_saved_snapshot_is_explicit_and_cli_exits_nonzero_in_text_and_json(
    tmp_path: Path,
    capsys,
):
    missing_data = tmp_path / "missing-data"
    packet = build_golden_evidence_cohort(
        Path.cwd(),
        data_dir=missing_data,
        rights_registry={},
    )

    assert packet.status == "missing_saved_snapshot"
    assert packet.members == ()
    assert packet.inspection_only is True
    assert packet.canonical_apply_authorized is False
    assert packet.readiness_materialization_authorized is False
    assert packet.source_rights_change_authorized is False
    assert packet.recommendation_authorized is False
    assert packet.repository_writes == ()

    text_exit = golden_evidence_main(
        ["--project-root", str(Path.cwd()), "--data-dir", str(missing_data)]
    )
    text_output = capsys.readouterr().out
    json_exit = golden_evidence_main(
        [
            "--project-root",
            str(Path.cwd()),
            "--data-dir",
            str(missing_data),
            "--json",
        ]
    )
    json_output = capsys.readouterr().out

    assert text_exit == 2
    assert "status=missing_saved_snapshot" in text_output
    assert "inspection_only=true" in text_output
    assert "canonical_apply_authorized=false" in text_output
    assert "readiness_materialization_authorized=false" in text_output
    assert "source_rights_change_authorized=false" in text_output
    assert "recommendation_authorized=false" in text_output
    assert "repository_writes=[]" in text_output
    assert json_exit == 2
    payload = json.loads(json_output)
    assert payload["status"] == "missing_saved_snapshot"
    assert payload["inspection_only"] is True
    assert payload["canonical_apply_authorized"] is False
    assert payload["readiness_materialization_authorized"] is False
    assert payload["source_rights_change_authorized"] is False
    assert payload["recommendation_authorized"] is False
    assert payload["repository_writes"] == []
