import pandas as pd

from src import data_health_trusted_pilot_console as pilot_console


def test_trusted_pilot_cards_bridge_blockers_to_small_ranked_pilot():
    cards = pilot_console.trusted_pilot_cards(
        {
            "price_ready": 240,
            "fundamentals_ready": 23,
            "dcf_ready": 23,
            "peer_ready": 9,
            "earnings_ready": 0,
            "analyst_estimates_ready": 0,
        }
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["PILOT STEP 1", "PILOT STEP 2", "PILOT STEP 3"]
    assert cards[0]["command"] == "make trusted-data-pilot-candidates TOP_N=10"
    assert cards[1]["command"] == "make trusted-data-pilot-packet TICKER=<ticker>"
    assert cards[2]["command"] == "make trusted-data-pilot TICKERS=<chosen names> TOP_N=10"
    assert "217 price-ready company row(s) still need trusted fundamentals or dcf inputs" in rendered
    assert "small ranked pilot instead of the full universe" in rendered
    assert "only the rebuilt readiness and stock report can prove the lane changed" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_trusted_pilot_preview_frame_and_selection_note_are_capped_and_research_safe(tmp_path):
    fundamentals = pd.DataFrame(
        [
            {
                "ticker": "META",
                "priority": "1",
                "dcf_ready": "False",
                "missing_required_for_dcf": "shares_outstanding, fcf_margin",
                "focus_command": "make focus-fundamentals TICKER=META",
            }
        ]
    )
    peers = pd.DataFrame(
        [
            {
                "ticker": "MU",
                "priority": "2",
                "peer_blocker_type": "missing_peer_mapping",
                "missing_peer_reason": "needs source-backed peer mappings",
                "focus_command": "make focus-peers TICKER=MU",
            }
        ]
    )
    readiness = pd.DataFrame(
        [
            {"ticker": "META", "asset_type": "company", "in_active_universe": "True"},
            {"ticker": "MU", "asset_type": "company", "in_active_universe": "True"},
        ]
    )

    frame = pilot_console.trusted_pilot_preview_frame(fundamentals, peers, readiness, root=tmp_path, limit=2)
    note = pilot_console.trusted_pilot_selection_note(fundamentals, peers, readiness, limit=10)
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()
    note_rendered = note.lower()

    assert list(frame["Ticker"]) == ["MU", "META"]
    assert "peer mapping proof path" in rendered
    assert "fundamentals / dcf proof path" in rendered
    assert "shares outstanding, free-cash-flow margin" in rendered
    assert "fcf_margin" not in rendered
    assert "make trusted-data-pilot-packet ticker=mu" in rendered
    assert "local file status:" in rendered
    assert "choose 5-10 operating companies only when you can review source proof" in note_rendered
    assert "quick path:" in note_rendered
    assert "rather than filling placeholder data" in note_rendered
    assert "recommend" not in note_rendered
    assert "buy" not in rendered + note_rendered
    assert "sell" not in rendered + note_rendered


def test_trusted_pilot_lane_board_and_cards_keep_locked_lanes_visible():
    fundamentals = pd.DataFrame(
        [
            {
                "ticker": "META",
                "priority": "1",
                "dcf_ready": "False",
                "missing_required_for_dcf": "shares_outstanding, fcf_margin",
                "focus_command": "make focus-fundamentals TICKER=META",
            }
        ]
    )
    peers = pd.DataFrame(
        [
            {
                "ticker": "MU",
                "priority": "2",
                "peer_blocker_type": "missing_peer_mapping",
                "missing_peer_reason": "needs source-backed peer mappings",
                "focus_command": "make focus-peers TICKER=MU",
            }
        ]
    )
    readiness = pd.DataFrame(
        [
            {"ticker": "META", "asset_type": "company", "in_active_universe": "True"},
            {"ticker": "MU", "asset_type": "company", "in_active_universe": "True"},
        ]
    )

    frame = pilot_console.trusted_pilot_lane_board_frame(fundamentals, peers, readiness, limit=10)
    cards = pilot_console.trusted_pilot_lane_cards(frame, limit=3)
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()
    card_rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert list(frame["Lane"]) == [
        "Fundamentals / DCF proof path",
        "Peer mapping proof path",
        "Peer valuation inputs proof path",
        "Optional context proof path",
        "Price coverage dry-run path",
    ]
    assert "earnings and analyst estimates remain locked unless trusted local rows exist" in rendered
    assert "rows are not applied from this board" in card_rendered
    assert "validate, preview, rejected-row checks, and rebuilt readiness must prove any change" in card_rendered
    assert "locked" in rendered
    assert "buy" not in rendered + card_rendered
    assert "sell" not in rendered + card_rendered


def test_trusted_pilot_lane_cards_empty_state_routes_to_project_status():
    cards = pilot_console.trusted_pilot_lane_cards(pd.DataFrame(), limit=3)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["command"] == "make project-status"
    assert "provider setup" in rendered
    assert "trusted-data-pilot-candidates top_n=10 after rebuilding readiness outputs" not in rendered


def test_trusted_pilot_preview_cards_summarize_top_candidate_without_advice():
    preview = pd.DataFrame(
        [
            {
                "Ticker": "MU",
                "Pilot Lane": "Peer mapping proof",
                "Scope": "Active universe",
                "Rank Reason": "active-universe public-demo name; peer mapping proof; priority 2; missing needs source-backed peers.",
                "Missing Input": "needs source-backed peer mappings; analyst_estimates: trusted local CSV input",
                "Review Decision": "Choose this company only if you can document source-backed peer relationships.",
                "Review Path": "make peer-mapping-queue TOP_N=25 -> make focus-peers TICKER=MU",
                "Trusted Input Target": "data/imports/peers.csv plus reviewed peer price/fundamentals rows when needed",
                "Skip If": "Skip for now if peer relationships cannot be supported by a source note.",
                "Packet Command": "make trusted-data-pilot-packet TICKER=MU",
                "Next Command": "make focus-peers TICKER=MU",
                "Proof After Data Changes": "make readiness && make peer-mapping-queue TOP_N=25 && make stock-report-md TICKER=MU",
            }
        ]
    )

    cards = pilot_console.trusted_pilot_preview_cards(preview, limit=1)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["kicker"] == "PILOT CANDIDATE"
    assert cards[0]["title"] == "MU: Peer mapping proof"
    assert cards[0]["command"] == "make trusted-data-pilot-packet TICKER=MU"
    assert cards[0]["badges"] == ["Active universe", "read-only"]
    assert "missing input: needs source-backed peer mappings; analyst estimates: trusted local csv input" in rendered
    assert "analyst_estimates" not in rendered
    assert "outcome: supported only after rebuilt readiness and the regenerated report prove it" in rendered
    assert "recommend" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
