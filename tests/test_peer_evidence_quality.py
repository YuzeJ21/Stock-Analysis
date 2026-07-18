from src.peer_evidence_quality import assess_peer_evidence, is_valuation_anchor_eligible


def _eligible_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "ticker": "ALFA",
        "peer_ticker": "BETA",
        "source": "https://example.test/peer-proof",
        "as_of_date": "2026-06-30",
        "peer_role": "core_peer",
        "relationship_rationale": "Both companies sell subscription workflow software to large enterprises.",
        "comparability_basis": "business model; customer mix; growth and margin profile",
        "valuation_anchor_eligible": "yes",
    }
    row.update(overrides)
    return row


def test_core_peer_with_complete_review_evidence_is_valuation_anchor_eligible():
    quality = assess_peer_evidence(_eligible_row())

    assert quality.relationship_state == "source_backed"
    assert quality.role_state == "reviewed_role"
    assert quality.comparability_state == "reviewed_comparable"
    assert quality.valuation_anchor_state == "eligible"
    assert quality.blockers == ()
    assert is_valuation_anchor_eligible(_eligible_row()) is True


def test_legacy_relationship_remains_visible_but_fails_closed_for_valuation_anchor():
    quality = assess_peer_evidence(
        {
            "ticker": "ALFA",
            "peer_ticker": "BETA",
            "peer_group": "enterprise software",
            "sector": "Technology",
            "industry": "Software",
            "source": "https://example.test/peer-proof",
            "as_of_date": "2026-06-30",
        }
    )

    assert quality.relationship_state == "source_backed"
    assert quality.role_state == "unreviewed_role"
    assert quality.comparability_state == "unreviewed"
    assert quality.valuation_anchor_state == "withheld"
    assert quality.blockers == (
        "peer_role_missing",
        "relationship_rationale_missing",
        "comparability_basis_missing",
        "valuation_anchor_decision_missing",
    )


def test_secondary_peer_can_anchor_when_explicitly_reviewed():
    quality = assess_peer_evidence(_eligible_row(peer_role="secondary_peer"))

    assert quality.peer_role == "secondary_peer"
    assert quality.valuation_anchor_state == "eligible"


def test_context_only_role_cannot_anchor_even_when_flag_says_yes():
    quality = assess_peer_evidence(_eligible_row(peer_role="aspirational_peer"))

    assert quality.comparability_state == "context_only"
    assert quality.valuation_anchor_state == "withheld"
    assert quality.blockers == ("peer_role_not_anchor_eligible",)


def test_explicit_no_keeps_reviewed_core_peer_as_context_only():
    quality = assess_peer_evidence(_eligible_row(valuation_anchor_eligible="no"))

    assert quality.comparability_state == "context_only"
    assert quality.valuation_anchor_state == "withheld"
    assert quality.blockers == ("valuation_anchor_explicitly_withheld",)


def test_invalid_role_and_missing_comparability_are_named_blockers():
    quality = assess_peer_evidence(
        _eligible_row(peer_role="favorite_peer", comparability_basis="")
    )

    assert quality.role_state == "invalid_role"
    assert quality.comparability_state == "unreviewed"
    assert quality.valuation_anchor_state == "withheld"
    assert quality.blockers == ("peer_role_invalid", "comparability_basis_missing")


def test_missing_relationship_provenance_blocks_anchor_independently():
    quality = assess_peer_evidence(_eligible_row(source="", as_of_date=""))

    assert quality.relationship_state == "provenance_missing"
    assert quality.role_state == "reviewed_role"
    assert quality.comparability_state == "reviewed_comparable"
    assert quality.valuation_anchor_state == "withheld"
    assert quality.blockers == ("relationship_source_missing", "relationship_as_of_missing")


def test_candidate_context_never_enters_trusted_or_anchor_state():
    quality = assess_peer_evidence(_eligible_row(candidate_state="candidate"))

    assert quality.relationship_state == "candidate_context_only"
    assert quality.valuation_anchor_state == "withheld"
    assert quality.blockers == ("candidate_context_not_trusted",)
