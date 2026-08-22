from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pandas as pd

from src import readiness_preview
from src.commercial_source_rights import SourceRights
from src.dcf_price_lineage import review_dcf_price_lineage
from src.readiness_evidence_remediation import (
    build_readiness_evidence_remediation,
    build_remediation_from_preview,
    render_readiness_evidence_remediation,
    render_readiness_evidence_remediation_json,
)
from src.readiness_preview import (
    compare_readiness_frames,
    review_readiness_changes,
    review_readiness_promotions,
)


def _readiness_row(ticker: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "ticker": ticker,
        "name": f"{ticker} Software",
        "asset_type": "company",
        "overall_readiness_state": "blocked",
        "price_ready": False,
        "momentum_ready": False,
        "fundamentals_ready": False,
        "dcf_ready": False,
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "ready_features": "",
        "partial_features": "",
        "blocked_features": "fundamentals, dcf",
        "excluded_features": "",
    }
    row.update(overrides)
    return row


def _rights(
    source_id: str,
    *,
    commercial_use: str = "approved",
    supported_fields: tuple[str, ...],
) -> SourceRights:
    return SourceRights(
        source_id=source_id,
        display_name=source_id,
        permitted_use="source_backed_research",
        commercial_use=commercial_use,
        redistribution="derived_data_only",
        storage_limits="reviewed local rows",
        attribution="required",
        rate_limits="provider terms",
        authentication="provider specific",
        expected_freshness="event driven",
        supported_fields=supported_fields,
        fallback_priority=1,
    )


def _registry() -> dict[str, SourceRights]:
    return {
        "full_fundamentals": _rights(
            "full_fundamentals",
            supported_fields=("revenue", "free_cash_flow", "fcf_margin", "shares_outstanding"),
        ),
        "scope_gap": _rights("scope_gap", supported_fields=("revenue",)),
        "approved_prices": _rights("approved_prices", supported_fields=("prices",)),
    }


def _promotion_fixture():
    saved = pd.DataFrame(
        [
            _readiness_row("AAA"),
            _readiness_row("BBB"),
            _readiness_row("CCC"),
            _readiness_row("DDD"),
            _readiness_row("EEE"),
            _readiness_row("EXC"),
        ]
    )
    proposed = pd.DataFrame(
        [
            _readiness_row("AAA", fundamentals_ready=True, dcf_ready=True),
            _readiness_row("BBB", fundamentals_ready=True),
            _readiness_row("CCC", fundamentals_ready=True, dcf_ready=True),
            _readiness_row("DDD", fundamentals_ready=True, dcf_ready=True),
            _readiness_row("EEE", fundamentals_ready=True),
            _readiness_row(
                "EXC",
                name="Example Bank Corp",
                excluded_features="dcf",
                blocked_features="fundamentals",
            ),
            _readiness_row("ADD"),
        ]
    )
    fundamentals = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "source": "full_fundamentals; filing_document",
                "as_of_date": "2025-12-31",
                "source_ref": "filing:AAA",
            },
            {
                "ticker": "BBB",
                "source": "scope_gap",
                "as_of_date": "2025-12-31",
                "source_ref": "filing:BBB",
            },
            {
                "ticker": "CCC",
                "source": "full_fundamentals",
                "as_of_date": "2025-12-31",
                "source_ref": "filing:CCC",
            },
            {
                "ticker": "DDD",
                "source": "full_fundamentals",
                "as_of_date": "2025-12-31",
                "source_ref": "filing:DDD",
            },
            {
                "ticker": "EEE",
                "source": "full_fundamentals",
                "as_of_date": "2025-12-31",
                "source_ref": "",
            },
        ]
    )
    prices = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "date": "2026-01-03",
                "close": 10,
                "source": "approved_prices",
                "source_ref": "price:AAA",
                "retrieved_at": "2026-01-04T23:00:00Z",
            },
            {
                "ticker": "CCC",
                "date": "2026-01-03",
                "close": 10,
                "source": "approved_prices",
                "source_ref": "price:CCC",
                "retrieved_at": "2026-01-04T23:00:00",
            },
            {
                "ticker": "DDD",
                "date": "2026-01-03",
                "close": 10,
                "source": "approved_prices",
                "source_ref": "price:DDD:1",
                "retrieved_at": "2026-01-04T23:00:00Z",
            },
            {
                "ticker": "DDD",
                "date": "2026-01-03",
                "close": 11,
                "source": "approved_prices",
                "source_ref": "price:DDD:2",
                "retrieved_at": "2026-01-04T23:00:00Z",
            },
        ]
    )
    preview = compare_readiness_frames(saved, proposed, top_n=20)
    return replace(
        preview,
        promotion_review=review_readiness_promotions(
            saved,
            proposed,
            fundamentals,
            rights_registry=_registry(),
            top_n=20,
        ),
        change_review=review_readiness_changes(saved, proposed, fundamentals),
        dcf_price_lineage_review=review_dcf_price_lineage(
            saved,
            proposed,
            prices,
            rights_registry=_registry(),
            review_cutoff="2026-01-05T00:00:00Z",
            top_n=20,
        ),
    )


def _tree_manifest(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_queue_combines_independent_fail_closed_blockers_without_splitting_sources():
    packet = build_remediation_from_preview(_promotion_fixture(), top_n=20)
    by_key = {(item.ticker, item.feature): item for item in packet.candidates}

    assert packet.status == "inspection_only"
    assert packet.changed_ticker_count == 7
    assert packet.added_ticker_count == 1
    assert packet.removed_ticker_count == 0
    assert packet.fundamentals_promotion_count == 5
    assert packet.dcf_promotion_count == 3
    assert packet.method_fit_exclusion_counts == (("dcf", 1),)
    assert packet.canonical_apply_authorized is False
    assert packet.readiness_materialization_authorized is False
    assert packet.source_rights_change_authorized is False
    assert packet.repository_writes == ()

    composite = by_key[("AAA", "fundamentals")]
    assert composite.fundamentals_source == "full_fundamentals; filing_document"
    assert composite.rights_status == "unknown_source"
    assert composite.status == "withheld"
    assert "exact_source_rights" in composite.independent_blockers
    assert "registered_field_scope" in composite.independent_blockers

    scope_gap = by_key[("BBB", "fundamentals")]
    assert scope_gap.rights_status == "approved"
    assert scope_gap.missing_registered_fields == (
        "free_cash_flow",
        "fcf_margin",
        "shares_outstanding",
    )
    assert scope_gap.independent_blockers == ("registered_field_scope",)

    temporal = by_key[("CCC", "dcf")]
    assert temporal.price_temporal_status == "temporal_review_required"
    assert "temporal_evidence" in temporal.independent_blockers

    ambiguous = by_key[("DDD", "dcf")]
    assert ambiguous.price_source == "<ambiguous>"
    assert "price_lineage" in ambiguous.independent_blockers

    provenance = by_key[("EEE", "fundamentals")]
    assert provenance.missing_provenance_fields == ("source_reference",)
    assert provenance.independent_blockers == ("provenance",)


def test_queue_is_closest_first_capped_and_json_is_byte_identical():
    preview = _promotion_fixture()
    first = build_remediation_from_preview(preview, top_n=3)
    second = build_remediation_from_preview(preview, top_n=3)

    assert first.candidate_count == 8
    assert len(first.candidates) == 3
    assert [(item.ticker, item.feature) for item in first.candidates] == [
        ("CCC", "fundamentals"),
        ("DDD", "fundamentals"),
        ("BBB", "fundamentals"),
    ]
    assert render_readiness_evidence_remediation_json(first) == render_readiness_evidence_remediation_json(second)
    payload = json.loads(render_readiness_evidence_remediation_json(first))
    assert payload["repository_writes"] == []
    assert payload["candidates"][0]["next_review_instruction"]


def test_queue_fails_closed_on_an_unclassified_upstream_blocker():
    preview = _promotion_fixture()
    assert preview.promotion_review is not None
    evidence_rows = tuple(
        replace(item, blockers=("future_evidence_gate:blocked",))
        if item.ticker == "CCC"
        else item
        for item in preview.promotion_review.evidence_rows
    )
    preview = replace(
        preview,
        promotion_review=replace(preview.promotion_review, evidence_rows=evidence_rows),
    )

    packet = build_remediation_from_preview(preview, top_n=20)
    candidate = next(
        item for item in packet.candidates if item.ticker == "CCC" and item.feature == "fundamentals"
    )

    assert candidate.status == "withheld"
    assert "unclassified_evidence_blocker" in candidate.independent_blockers
    assert "fundamentals:future_evidence_gate:blocked" in candidate.blocker_details


def test_rights_instruction_names_only_sources_with_unresolved_rights():
    preview = _promotion_fixture()
    fundamentals_blocked = build_remediation_from_preview(preview, top_n=20)
    aaa_dcf = next(
        item
        for item in fundamentals_blocked.candidates
        if item.ticker == "AAA" and item.feature == "dcf"
    )

    assert "full_fundamentals; filing_document" in aaa_dcf.next_review_instruction
    assert "approved_prices" not in aaa_dcf.next_review_instruction

    assert preview.dcf_price_lineage_review is not None
    price_rows = tuple(
        replace(
            item,
            source_id="unknown_prices",
            rights_status="unknown_source",
            temporal_status="temporal_complete",
            retrieved_at="2026-01-04T23:00:00+00:00",
            missing_provenance_fields=(),
            blockers=("commercial_rights:unknown_source",),
        )
        if item.ticker == "CCC"
        else item
        for item in preview.dcf_price_lineage_review.evidence_rows
    )
    price_blocked_preview = replace(
        preview,
        dcf_price_lineage_review=replace(
            preview.dcf_price_lineage_review,
            evidence_rows=price_rows,
        ),
    )
    price_blocked = build_remediation_from_preview(price_blocked_preview, top_n=20)
    ccc_dcf = next(
        item
        for item in price_blocked.candidates
        if item.ticker == "CCC" and item.feature == "dcf"
    )

    assert "unknown_prices" in ccc_dcf.next_review_instruction
    assert "full_fundamentals" not in ccc_dcf.next_review_instruction


def test_queue_empty_set_and_text_preserve_inspection_only_boundary():
    saved = pd.DataFrame([_readiness_row("AAA")])
    preview = compare_readiness_frames(saved, saved.copy(), top_n=5)
    preview = replace(
        preview,
        promotion_review=review_readiness_promotions(
            saved,
            saved.copy(),
            pd.DataFrame(),
            rights_registry={},
            top_n=5,
        ),
        change_review=review_readiness_changes(saved, saved.copy(), pd.DataFrame()),
        dcf_price_lineage_review=review_dcf_price_lineage(
            saved,
            saved.copy(),
            pd.DataFrame(),
            rights_registry={},
            top_n=5,
        ),
    )

    packet = build_remediation_from_preview(preview, top_n=5)
    rendered = render_readiness_evidence_remediation(packet)

    assert packet.candidate_count == 0
    assert packet.candidates == ()
    assert "Status: inspection_only" in rendered
    assert "canonical_apply_authorized=false" in rendered
    assert "readiness_materialization_authorized=false" in rendered
    assert "source_rights_change_authorized=false" in rendered
    assert "repository_writes=[]" in rendered
    lowered = rendered.lower()
    for unsafe in ("buy", "sell", "order routing", "auto-trading"):
        assert unsafe not in lowered


def test_build_uses_full_existing_preview_evidence_and_writes_nothing(tmp_path: Path, monkeypatch):
    reports = tmp_path / "data" / "reports"
    reports.mkdir(parents=True)
    saved = pd.DataFrame([_readiness_row("AAA")])
    proposed = pd.DataFrame([_readiness_row("AAA", fundamentals_ready=True)])
    saved.to_csv(reports / "ticker_readiness_report.csv", index=False)
    pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "source": "full_fundamentals",
                "as_of_date": "2025-12-31",
                "source_ref": "filing:AAA",
            }
        ]
    ).to_csv(tmp_path / "data" / "fundamentals.csv", index=False)

    def _build(*args: object, **kwargs: object) -> dict[str, pd.DataFrame]:
        assert kwargs["write_outputs"] is False
        return {"ticker_readiness_report": proposed}

    monkeypatch.setattr(readiness_preview, "build_ticker_readiness_report", _build)
    before = _tree_manifest(tmp_path)

    packet = build_readiness_evidence_remediation(
        tmp_path,
        top_n=1,
        rights_registry=_registry(),
        review_cutoff="2026-01-05T00:00:00Z",
    )

    assert packet.saved_snapshot_identity.startswith("sha256:")
    assert packet.proposed_snapshot_identity.startswith("sha256:")
    assert packet.candidate_count == 1
    assert _tree_manifest(tmp_path) == before
