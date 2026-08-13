from src.peer_read_through_map import build_peer_read_through_map, peer_read_through_rows


def _payload(*, target_period: str | None = "2026-Q2") -> dict[str, object]:
    return {
        "ticker": "ALFA",
        "asset_type": "company",
        "earnings_summary": {"fiscal_period": target_period},
        "valuation_readiness": {
            "peer_summary": {
                "trusted_relationships": [
                    {
                        "ticker": "ALFA",
                        "peer_ticker": "BETA",
                        "peer_group": "cloud infrastructure",
                        "industry": "Cloud platforms",
                        "peer_role": "core_peer",
                        "relationship_rationale": "Cloud platforms with comparable enterprise customer exposure.",
                        "comparability_basis": "business model; customer mix; growth and margin profile",
                        "valuation_anchor_eligible": "yes",
                        "source": "https://example.test/peer-source",
                        "as_of_date": "2026-06-30",
                        "peer_result": {
                            "fiscal_period": "2026-Q2",
                            "last_earnings_date": "2026-07-10",
                            "eps_actual": 1.2,
                            "revenue_actual": 2500.0,
                            "source": {"provider": "local:earnings.csv", "freshness": "dataset row as of 2026-07-10"},
                        },
                    }
                ],
                "candidate_relationships": [
                    {
                        "ticker": "ALFA",
                        "peer_ticker": "GAMMA",
                        "candidate_state": "research_only",
                        "peer_group": "cloud infrastructure",
                        "source": "classification fallback",
                        "as_of_date": "2026-06-30",
                    }
                ],
            }
        },
    }


def test_trusted_relationship_with_result_and_explicit_periods_is_reviewable_context():
    result = build_peer_read_through_map(_payload(), profile_key="demo")

    edge = result.edges[0]
    assert edge.peer_ticker == "BETA"
    assert edge.relationship_state == "trusted_peer_ready"
    assert edge.peer_role == "core_peer"
    assert edge.comparability_state == "reviewed_comparable"
    assert edge.valuation_anchor_state == "eligible"
    assert edge.business_overlap == "Cloud platforms with comparable enterprise customer exposure."
    assert edge.fiscal_timing == "ALFA 2026-Q2 / BETA 2026-Q2"
    assert edge.result_evidence == "Revenue actual and EPS actual"
    assert edge.read_through_state == "reviewable_context"
    assert "forecast" in edge.boundary.lower()


def test_candidate_relationship_never_becomes_trusted_or_reviewable():
    result = build_peer_read_through_map(_payload(), profile_key="demo")

    candidate = next(edge for edge in result.edges if edge.peer_ticker == "GAMMA")
    assert candidate.relationship_state == "candidate_context_only"
    assert candidate.read_through_state == "candidate_context_only"
    assert candidate.result_evidence == "Not reviewed"
    assert result.reviewable_count == 1
    assert result.valuation_anchor_count == 1


def test_trusted_relationship_without_result_fails_closed():
    payload = _payload()
    payload["valuation_readiness"]["peer_summary"]["trusted_relationships"][0]["peer_result"] = {
        "last_earnings_date": "2026-07-10",
        "source": {"provider": "local:earnings.csv"},
    }

    edge = build_peer_read_through_map(payload, profile_key="demo").edges[0]

    assert edge.read_through_state == "awaiting_peer_result"
    assert edge.result_evidence == "No source-backed actual result"


def test_trusted_result_without_explicit_fiscal_timing_is_withheld():
    result = build_peer_read_through_map(_payload(target_period=None), profile_key="demo")

    edge = result.edges[0]
    assert edge.read_through_state == "awaiting_fiscal_timing"
    assert edge.fiscal_timing == "Not established"


def test_missing_relationship_provenance_cannot_be_trusted():
    payload = _payload()
    trusted = payload["valuation_readiness"]["peer_summary"]["trusted_relationships"][0]
    trusted["source"] = ""

    edge = build_peer_read_through_map(payload, profile_key="demo").edges[0]

    assert edge.relationship_state == "awaiting_relationship_proof"
    assert edge.read_through_state == "awaiting_relationship_proof"


def test_legacy_trusted_relationship_keeps_result_context_but_withholds_valuation_anchor():
    payload = _payload()
    trusted = payload["valuation_readiness"]["peer_summary"]["trusted_relationships"][0]
    for key in ("peer_role", "relationship_rationale", "comparability_basis", "valuation_anchor_eligible"):
        trusted.pop(key)

    result = build_peer_read_through_map(payload, profile_key="demo")
    edge = result.edges[0]

    assert edge.relationship_state == "trusted_peer_ready"
    assert edge.read_through_state == "reviewable_context"
    assert edge.peer_role == "unreviewed"
    assert edge.comparability_state == "unreviewed"
    assert edge.valuation_anchor_state == "withheld"
    assert "peer_role_missing" in edge.evidence_quality_blockers
    assert result.valuation_anchor_count == 0
    assert result.comparability_withheld_count == 1


def test_aspirational_peer_is_explicit_context_only_not_a_valuation_anchor():
    payload = _payload()
    trusted = payload["valuation_readiness"]["peer_summary"]["trusted_relationships"][0]
    trusted["peer_role"] = "aspirational_peer"

    edge = build_peer_read_through_map(payload, profile_key="demo").edges[0]

    assert edge.comparability_state == "context_only"
    assert edge.valuation_anchor_state == "withheld"


def test_non_company_assets_are_excluded():
    payload = _payload()
    payload["asset_type"] = "etf"

    result = build_peer_read_through_map(payload, profile_key="demo")

    assert result.status == "excluded"
    assert result.edges == ()
    assert result.reviewable_count == 0


def test_identity_is_deterministic_and_rows_keep_trust_boundary():
    first = build_peer_read_through_map(_payload(), profile_key="demo")
    second = build_peer_read_through_map(_payload(), profile_key="demo")

    assert first.map_identity == second.map_identity
    rows = peer_read_through_rows(first)
    assert rows[0]["Relationship"] == "Trusted peer"
    assert rows[0]["Peer Role"] == "Core peer"
    assert rows[0]["Comparability"] == "Reviewed comparable"
    assert rows[0]["Valuation Anchor"] == "Eligible"
    assert rows[1]["Relationship"] == "Candidate context only"
    assert all("buy" not in str(row).lower() for row in rows)
