import pandas as pd

from src.commercial_source_rights import SourceRights
from src.golden_evidence_cohort import GoldenEvidenceCohort, GoldenEvidenceMember
from src.golden_price_lineage_proof import (
    build_golden_price_lineage_proof,
    render_golden_price_lineage_proof,
    render_golden_price_lineage_proof_json,
)


def _rights(
    source_id: str,
    *,
    commercial_use: str = "approved",
    supported_fields: tuple[str, ...] = ("prices",),
) -> SourceRights:
    return SourceRights(
        source_id=source_id,
        display_name=source_id,
        permitted_use="source_backed_research",
        commercial_use=commercial_use,
        redistribution="derived_data_only",
        storage_limits="reviewed rows only",
        attribution="required",
        rate_limits="provider terms",
        authentication="none",
        expected_freshness="market_data_dependent",
        supported_fields=supported_fields,
        fallback_priority=1,
    )


def _member(
    ticker: str,
    role: str,
    *,
    asset_type: str = "company",
) -> GoldenEvidenceMember:
    return GoldenEvidenceMember(
        ticker=ticker,
        asset_type=asset_type,
        cohort_role=role,
        selection_reason="fixture",
        state="fixture",
        saved_readiness_identity=f"saved:{ticker}",
        proposed_readiness_identity=f"proposed:{ticker}",
        usable_evidence_lanes=(),
        withheld_evidence_lanes=("price_lineage",),
        source_identifiers=(),
        source_rights_states=(),
        missing_registered_fields=("prices",),
        provenance_omissions=(),
        temporal_evidence_omissions=(),
        price_lineage_omissions=("source", "source_ref", "retrieved_at"),
        method_fit_exclusions=("non_operating_asset_type",) if role == "method_fit_exclusion" else (),
        independent_blockers=("price_lineage",),
        owner_decision_required=False,
        next_evidence_review_action="fixture",
        saved_research_loop_status="partial_saved_evidence_only",
        research_only_boundary="Research workflow evidence only; no security action guidance.",
    )


def _cohort() -> GoldenEvidenceCohort:
    return GoldenEvidenceCohort(
        status="inspection_only",
        saved_snapshot_identity="saved:cohort",
        proposed_snapshot_identity="proposed:cohort",
        members=(
            _member("AMD", "saved_operating_company"),
            _member("AVGO", "saved_operating_company"),
            _member("COHR", "saved_operating_company"),
            _member("ABAT", "evidence_gap_control"),
            _member("QQQ", "method_fit_exclusion", asset_type="etf"),
        ),
        top_n=5,
    )


def _price_rows(ticker: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": "2026-08-19",
                "ticker": ticker,
                "open": 99.0,
                "high": 102.0,
                "low": 98.0,
                "close": 101.0,
                "adj_close": 101.0,
                "volume": 1000,
            },
            {
                "date": "2026-08-20",
                "ticker": ticker,
                "open": 100.0,
                "high": 103.0,
                "low": 99.0,
                "close": 102.0,
                "adj_close": 102.0,
                "volume": 1100,
            },
        ]
    )


class FakeYahooSource:
    source_id = "yahoo"

    def __init__(self, payloads: dict[str, pd.DataFrame | None]) -> None:
        self.payloads = payloads
        self.calls: list[str] = []
        self.last_source_reference = ""
        self.last_retrieved_at = ""

    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        self.calls.append(ticker)
        payload = self.payloads.get(ticker)
        if payload is None:
            self.last_source_reference = ""
            self.last_retrieved_at = ""
            return pd.DataFrame(), [f"{ticker}: source unavailable"]
        self.last_source_reference = f"yahoo-chart:{ticker}:sha256:{ticker.lower()}-fixture"
        self.last_retrieved_at = "2026-08-22T20:30:00+00:00"
        return payload.copy(), [f"{ticker}: research-grade candidate"]


def test_preview_names_exact_operating_targets_without_fetching_or_borrowing_yfinance_rights():
    packet = build_golden_price_lineage_proof(
        _cohort(),
        rights_registry={"yfinance": _rights("yfinance")},
        live=False,
    )

    assert packet.status == "collection_not_requested"
    assert [member.ticker for member in packet.members] == ["AMD", "AVGO", "COHR", "ABAT"]
    assert packet.method_fit_exclusions == ("QQQ",)
    assert all(member.collection_status == "not_requested" for member in packet.members)
    assert all(member.source_id == "yahoo" for member in packet.members)
    assert all(member.rights_status == "unknown_source" for member in packet.members)
    assert all(member.price_scope_status == "review_required" for member in packet.members)
    assert packet.live_collection_performed is False
    assert packet.candidate_collected_count == 0
    assert packet.collection_incomplete_count == 4
    assert packet.activation_authorized is False
    assert packet.repository_writes == ()


def test_live_collection_preserves_exact_candidate_evidence_and_stays_rights_blocked():
    source = FakeYahooSource(
        {ticker: _price_rows(ticker) for ticker in ("AMD", "AVGO", "COHR", "ABAT", "QQQ")}
    )

    packet = build_golden_price_lineage_proof(
        _cohort(),
        rights_registry={"yfinance": _rights("yfinance")},
        live=True,
        source=source,
        review_cutoff="2026-08-22T21:00:00Z",
    )

    assert source.calls == ["AMD", "AVGO", "COHR", "ABAT"]
    assert packet.status == "candidate_evidence_collected_rights_blocked"
    assert packet.method_fit_exclusions == ("QQQ",)
    assert all(member.collection_status == "candidate_collected" for member in packet.members)
    assert all(member.observation_date == "2026-08-20" for member in packet.members)
    assert all(member.close == 102.0 for member in packet.members)
    assert all(member.source_reference.endswith(f"{member.ticker.lower()}-fixture") for member in packet.members)
    assert all(member.retrieved_at == "2026-08-22T20:30:00+00:00" for member in packet.members)
    assert all(member.temporal_status == "temporal_complete" for member in packet.members)
    assert all(member.rights_status == "unknown_source" for member in packet.members)
    assert all(member.price_scope_status == "review_required" for member in packet.members)
    assert all(member.owner_decision_required for member in packet.members)
    assert all(
        member.blockers == (
            "commercial_rights:unknown_source",
            "registered_price_scope_incomplete",
        )
        for member in packet.members
    )
    assert packet.activation_authorized is False
    assert packet.repository_writes == ()


def test_approved_exact_yahoo_source_can_be_reviewable_but_never_authorizes_activation():
    source = FakeYahooSource({ticker: _price_rows(ticker) for ticker in ("AMD", "AVGO", "COHR", "ABAT")})

    packet = build_golden_price_lineage_proof(
        _cohort(),
        rights_registry={"yahoo": _rights("yahoo")},
        live=True,
        source=source,
        review_cutoff="2026-08-22T21:00:00Z",
    )

    assert packet.status == "candidate_evidence_reviewable"
    assert all(member.rights_status == "approved" for member in packet.members)
    assert all(member.price_scope_status == "complete" for member in packet.members)
    assert all(member.blockers == () for member in packet.members)
    assert all(member.owner_decision_required is False for member in packet.members)
    assert packet.activation_authorized is False
    assert packet.canonical_apply_authorized is False
    assert packet.readiness_materialization_authorized is False
    assert packet.source_rights_change_authorized is False


def test_fetch_failure_and_ambiguous_latest_rows_fail_closed_without_padding():
    ambiguous = _price_rows("AVGO")
    ambiguous = pd.concat([ambiguous, ambiguous.tail(1)], ignore_index=True)
    source = FakeYahooSource(
        {
            "AMD": None,
            "AVGO": ambiguous,
            "COHR": _price_rows("COHR"),
            "ABAT": _price_rows("ABAT"),
        }
    )

    packet = build_golden_price_lineage_proof(
        _cohort(),
        rights_registry={"yahoo": _rights("yahoo")},
        live=True,
        source=source,
        review_cutoff="2026-08-22T21:00:00Z",
    )

    assert packet.status == "candidate_collection_incomplete"
    assert [member.ticker for member in packet.members] == ["AMD", "AVGO", "COHR", "ABAT"]
    assert packet.members[0].collection_status == "fetch_failed"
    assert packet.members[0].blockers == ("candidate_fetch_failed",)
    assert packet.members[1].collection_status == "ambiguous_latest_candidate"
    assert packet.members[1].blockers == ("ambiguous_latest_candidate_row",)
    assert len(packet.members) == 4


def test_renderers_are_deterministic_and_keep_all_authorization_boundaries_visible():
    packet = build_golden_price_lineage_proof(
        _cohort(),
        rights_registry={"yfinance": _rights("yfinance")},
        live=False,
    )

    assert render_golden_price_lineage_proof_json(packet) == render_golden_price_lineage_proof_json(packet)
    rendered = render_golden_price_lineage_proof(packet)
    assert "live_collection_performed=false" in rendered
    assert "method_fit_exclusions=QQQ" in rendered
    assert "activation_authorized=false" in rendered
    assert "canonical_apply_authorized=false" in rendered
    assert "readiness_materialization_authorized=false" in rendered
    assert "source_rights_change_authorized=false" in rendered
    assert "repository_writes=[]" in rendered
    assert "Research workflow evidence only; no security action guidance." in rendered
