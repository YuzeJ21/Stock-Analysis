from __future__ import annotations


def public_home_loop_cards(summary: dict[str, object]) -> list[dict[str, object]]:
    """Return first-scan public workflow cards for the Home page."""

    master = int(summary.get("master_universe") or summary.get("universe_count") or 0)
    price_ready = int(summary.get("price_ready") or 0)
    dcf_ready = int(summary.get("dcf_ready") or 0)
    peer_ready = int(summary.get("peer_ready") or 0)
    blocked = int(summary.get("blocked_by_data") or summary.get("blocked") or max(master - dcf_ready, 0))
    return [
        {
            "kicker": "READ THIS FIRST",
            "title": "Broad price coverage, gated deeper research",
            "body": (
                f"{price_ready:,}/{master:,} tracked names have price coverage. "
                f"{dcf_ready:,} are DCF-ready and {peer_ready:,} are peer-ready; deeper sections stay locked until trusted inputs exist."
            ),
            "badges": ["readiness first", "no inferred gaps"],
        },
        {
            "kicker": "CONNECTED PATH",
            "title": "Home -> one ticker -> Data Health -> proof history",
            "body": (
                "Home shows coverage. Single-Stock Report shows what can be reviewed now. "
                "Data Health explains missing source inputs. Proof history is checked before trusting a changed state."
            ),
            "badges": ["one loop", "real workflow"],
        },
        {
            "kicker": "STOP RULE",
            "title": f"{blocked:,} blocked states remain visible",
            "body": (
                "If fundamentals, shares, peers, earnings, estimates, valuation inputs, or metrics are missing, "
                "the product keeps the section blocked or excluded instead of filling the gap."
            ),
            "badges": ["no data, no conclusion", "research-only"],
        },
    ]


def public_home_visitor_path_cards(summary: dict[str, object]) -> list[dict[str, object]]:
    """Return the public first-scan journey without operator command detail."""

    master = int(summary.get("master_universe") or summary.get("universe_count") or 0)
    price_ready = int(summary.get("price_ready") or 0)
    dcf_ready = int(summary.get("dcf_ready") or 0)
    peer_ready = int(summary.get("peer_ready") or 0)
    blocked = int(summary.get("blocked_by_data") or summary.get("blocked") or max(master - dcf_ready, 0))
    return [
        {
            "kicker": "STEP 1",
            "title": "Start with readiness",
            "body": (
                f"{price_ready:,}/{master:,} tracked names have price coverage. "
                "The first question is what the local data can support today."
            ),
            "badges": ["home", "readiness first"],
        },
        {
            "kicker": "STEP 2",
            "title": "Open one ticker",
            "body": (
                "Single-Stock Report shows the selected ticker, what can be reviewed now, "
                "what is blocked or excluded, and where Data Health fits next."
            ),
            "badges": ["one ticker", "plain English"],
        },
        {
            "kicker": "STEP 3",
            "title": "Route locks to Data Health",
            "body": (
                f"{blocked:,} blocked states stay visible. Data Health names the source-proof lane, manual gate, and stop rule "
                "without making visitors read raw CSV tables first."
            ),
            "badges": ["source proof", "no raw tables first"],
        },
        {
            "kicker": "STEP 4",
            "title": "Trust only after proof",
            "body": (
                f"{dcf_ready:,} DCF-ready and {peer_ready:,} peer-ready names can support deeper review today. "
                "Changed states need rebuilt readiness and proof history before interpretation."
            ),
            "badges": ["proof history", "research-only"],
        },
    ]
