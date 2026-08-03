from __future__ import annotations

import pandas as pd

from src import data_health_coverage_delta as coverage_delta


def test_readiness_delta_board_missing_current_keeps_command_out_of_body():
    cards = coverage_delta.readiness_delta_board_cards(pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    body = str(cards[0]["body"]).lower()

    assert cards[0]["title"] == "Current readiness report missing"
    assert cards[0]["command"] == "make readiness-preview TOP_N=20"
    assert "open operator details" in body
    assert "copy-only command" not in body
    assert "make " not in body


def test_readiness_delta_board_handles_missing_prior_snapshot_without_fake_delta():
    current = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "price_ready": [True, False],
            "dcf_ready": [False, False],
            "peer_ready": [False, False],
            "blocked_features": ["dcf, peer", "price, dcf, peer"],
        }
    )

    frame = coverage_delta.readiness_delta_board_frame(current, pd.DataFrame(), pd.DataFrame())
    cards = coverage_delta.readiness_delta_board_cards(current, pd.DataFrame(), pd.DataFrame())
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert frame.loc[frame["Lane"].eq("Price"), "Current Ready"].iloc[0] == 1
    assert frame.loc[frame["Lane"].eq("Price"), "Previous Ready"].iloc[0] == "not available"
    assert frame.loc[frame["Lane"].eq("Price"), "Delta Ready"].iloc[0] == "not available"
    assert cards[0]["title"] == "Current-only baseline"
    assert cards[0]["command"] == "make readiness-snapshot PROFILE=default"
    assert "will not invent before/after changes" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_readiness_delta_board_summarizes_lane_changes_and_artifact_review():
    current = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "price_ready": [True, True, False],
            "fundamentals_ready": [False, True, False],
            "dcf_ready": [False, True, False],
            "peer_ready": [False, False, False],
            "blocked_features": ["dcf, peer", "peer", "price, dcf, peer"],
        }
    )
    previous = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB", "CCC"],
            "price_ready": [True, False, False],
            "fundamentals_ready": [False, False, False],
            "dcf_ready": [False, False, False],
            "peer_ready": [False, False, False],
        }
    )
    proof = pd.DataFrame(
        [
            {
                "Batch ID": "RB-DCF",
                "Review Date": "2026-06-17",
                "Lane": "share_count",
                "Final Outcome": "supported",
                "Generated Artifacts Reviewed": "excluded broad generated churn",
            }
        ]
    )

    frame = coverage_delta.readiness_delta_board_frame(current, previous, proof)
    cards = coverage_delta.readiness_delta_board_cards(current, previous, proof)
    rendered = " ".join(
        frame.astype(str).to_numpy().flatten().tolist()
        + [str(value) for card in cards for value in card.values()]
    ).lower()

    price = frame.loc[frame["Lane"].eq("Price")].iloc[0]
    dcf = frame.loc[frame["Lane"].eq("DCF")].iloc[0]
    peer = frame.loc[frame["Lane"].eq("Peers")].iloc[0]

    assert price["Delta Ready"] == "+1"
    assert price["Newly Ready Tickers"] == "BBB"
    assert dcf["Delta Ready"] == "+1"
    assert dcf["Latest Batch Outcome"] == "supported"
    assert dcf["Generated Artifacts Reviewed"] == "excluded broad generated churn"
    assert int(peer["Still Blocked"]) == 3
    assert cards[0]["command"] == (
        "make reviewed-batch-compare PROFILE=default LANE=<lane> "
        "BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>"
    )
    assert "price +1" in rendered
    assert "dcf +1" in rendered
    assert "generated-artifact review recorded" in rendered
    assert "not recommendations" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_readiness_change_frame_keeps_missing_inputs_visible():
    current = pd.DataFrame(
        {
            "ticker": ["aaa", "bbb"],
            "price_ready": [True, "yes"],
            "dcf_ready": [False, False],
            "blocked_features": ["dcf", "price, dcf"],
        }
    )

    frame = coverage_delta.build_readiness_change_frame(current)
    dcf = frame.loc[frame["feature"].eq("DCF")].iloc[0]

    assert int(dcf["current_ready"]) == 0
    assert int(dcf["current_blocked"]) == 2
    assert pd.isna(dcf["delta_ready"])
