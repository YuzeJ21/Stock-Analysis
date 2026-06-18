import pandas as pd

from src.data_health_proof_closeout_summary import proof_closeout_summary_cards, proof_closeout_summary_frame


def test_proof_closeout_summary_flags_unfinished_lane_without_advice_language():
    dcf_closeout = pd.DataFrame(
        [
            {
                "Closeout Status": "supported",
                "Latest Outcome": "supported",
                "Comparison Status": "ready",
                "Evidence Remaining": "No remaining evidence gates.",
                "Next Safest Action": "make dcf-input-proof-queue TOP_N=10",
                "Closeout Boundary": "Closeout rows are data-readiness proof states only.",
            }
        ]
    )
    peer_closeout = pd.DataFrame(
        [
            {
                "Closeout Status": "not_recorded",
                "Latest Outcome": "not_recorded",
                "Comparison Status": "deferred",
                "Evidence Remaining": "Source-review intake: proposed_peer_ticker missing",
                "Next Safest Action": "make peer-mapping-source-review TOP_N=10",
                "Closeout Boundary": "Closeout rows are peer-readiness proof states only.",
            }
        ]
    )

    frame = proof_closeout_summary_frame(dcf_closeout, peer_closeout)
    cards = proof_closeout_summary_cards(dcf_closeout, peer_closeout)
    rendered = " ".join(
        frame.astype(str).to_numpy().flatten().tolist()
        + [str(value) for card in cards for value in card.values()]
    ).lower()

    assert frame["Proof Lane"].tolist() == ["DCF proof closeout", "Peer proof closeout"]
    assert frame.iloc[0]["Lane URL"] == "?mode=operator&page=data-health&lane=fundamentals"
    assert frame.iloc[1]["Lane URL"] == "?mode=operator&page=data-health&lane=peers"
    assert cards[0]["title"] == "1 proof lane(s) need closeout review"
    assert cards[0]["command"] == "?mode=operator&page=data-health&lane=peers"
    assert "closeout states: supported: 1; not_recorded: 1" in rendered
    assert "data-readiness evidence, not analysis or recommendation output" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_proof_closeout_summary_uses_not_loaded_fallbacks():
    frame = proof_closeout_summary_frame(None, None)
    cards = proof_closeout_summary_cards(None, None)

    assert frame["Closeout Status"].tolist() == ["not_loaded", "not_loaded"]
    assert frame["Latest Outcome"].tolist() == ["not_recorded", "not_recorded"]
    assert cards[0]["title"] == "2 proof lane(s) need closeout review"
    assert cards[0]["command"] == "?mode=operator&page=data-health&lane=fundamentals"
