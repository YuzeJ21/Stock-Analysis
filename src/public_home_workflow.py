from __future__ import annotations


def public_home_first_30_second_cards(summary: dict[str, object]) -> list[dict[str, object]]:
    """Return a compact public explanation before workflow details."""

    master = int(summary.get("master_universe") or summary.get("universe_count") or 0)
    price_ready = int(summary.get("price_ready") or 0)
    dcf_ready = int(summary.get("dcf_ready") or 0)
    peer_ready = int(summary.get("peer_ready") or 0)
    blocked = int(summary.get("blocked_by_data") or summary.get("blocked") or max(master - dcf_ready, 0))
    return [
        {
            "kicker": "WHAT THIS IS",
            "title": "A readiness-first research workflow",
            "body": (
                "The app checks local data coverage before showing analysis. "
                "Ready, blocked, partial, and excluded states stay visible instead of being blended into one score."
            ),
            "badges": ["research-only", "data readiness first"],
        },
        {
            "kicker": "HOW TO READ IT",
            "title": f"{price_ready:,}/{master:,} price-ready; deeper work is gated",
            "body": (
                f"{dcf_ready:,} names are DCF-ready and {peer_ready:,} are peer-ready today. "
                "Use Home for the snapshot, Single-Stock Report for one ticker, and Data Health for source-proof gaps."
            ),
            "badges": ["one connected loop", "proof before analysis"],
        },
        {
            "kicker": "WHEN TO STOP",
            "title": f"{blocked:,} blocked states remain withheld",
            "body": (
                "If trusted fundamentals, shares, peers, earnings, estimates, valuation inputs, or metrics are missing, "
                "the product stops at the data gap and keeps the conclusion unavailable."
            ),
            "badges": ["no data, no conclusion", "blocked stays blocked"],
        },
    ]


def public_home_review_map_cards(summary: dict[str, object]) -> list[dict[str, object]]:
    """Return the public Home review map without terminal or operator detail."""

    master = int(summary.get("master_universe") or summary.get("universe_count") or 0)
    price_ready = int(summary.get("price_ready") or 0)
    dcf_ready = int(summary.get("dcf_ready") or 0)
    peer_ready = int(summary.get("peer_ready") or 0)
    blocked = int(summary.get("blocked_by_data") or summary.get("blocked") or max(master - dcf_ready, 0))
    return [
        {
            "kicker": "CURRENT STEP",
            "title": "Start from the readiness snapshot",
            "body": (
                f"{price_ready:,}/{master:,} tracked names have price coverage. "
                "The Home page answers what the local data can support before any interpretation."
            ),
            "badges": ["snapshot", "ready vs blocked"],
        },
        {
            "kicker": "REVIEW NOW",
            "title": "Open one ticker only after the state is clear",
            "body": (
                f"{dcf_ready:,} names are DCF-ready and {peer_ready:,} are peer-ready. "
                "Single-Stock Report starts with what can be reviewed now, what is blocked, and where proof fits next."
            ),
            "badges": ["one ticker", "review scope"],
        },
        {
            "kicker": "NEXT SAFE ACTION",
            "title": "Route missing inputs to Data Health",
            "body": (
                f"{blocked:,} blocked states remain source-proof work. "
                "Data Health keeps the source lane, manual gate, proof packet, and stop rule together."
            ),
            "badges": ["source proof", "no raw tables first"],
        },
        {
            "kicker": "STOP RULE",
            "title": "Do not conclude from missing inputs",
            "body": (
                "If trusted fundamentals, shares, peers, earnings, estimates, valuation inputs, or metrics are unavailable, "
                "the section stays blocked or excluded until reviewed proof exists."
            ),
            "badges": ["no data, no conclusion", "research-only"],
        },
    ]


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


def public_home_route_choice_cards(summary: dict[str, object]) -> list[tuple[str, str, str, str]]:
    """Return public Home route choices without terminal or operator detail."""

    master = int(summary.get("master_universe") or summary.get("universe_count") or 0)
    price_ready = int(summary.get("price_ready") or 0)
    dcf_ready = int(summary.get("dcf_ready") or 0)
    peer_ready = int(summary.get("peer_ready") or 0)
    earnings_ready = int(summary.get("earnings_ready") or 0)
    estimates_ready = int(summary.get("analyst_estimates_ready") or summary.get("analyst_ready") or 0)

    has_price_gap = bool(master and price_ready < master)
    has_depth_gap = price_ready > dcf_ready or dcf_ready > peer_ready or earnings_ready == 0 or estimates_ready == 0
    data_gap_count = max(master - price_ready, 0) if master else 0

    review_body = "Start here for ticker-level review: choose any local ticker and read what is ready, blocked, excluded, or monitor-only."
    if dcf_ready > 0:
        review_body = (
            f"Start here: {dcf_ready} ticker(s) have DCF-ready local inputs. "
            "Open a report, read supported sections first, then route locked fields to Data Health."
        )
    elif price_ready > 0:
        review_body = (
            f"Start here for ticker-level proof: {price_ready} ticker(s) can support setup review; "
            "valuation stays gated where trusted fundamentals are missing."
        )

    improve_body = (
        "Use this when a section is locked. It shows the next trusted input, review path, validation boundary, and proof step."
    )
    improve_tone = "neutral"
    if has_price_gap or has_depth_gap:
        improve_tone = "warning"
        gap_note = f"{data_gap_count:,} ticker(s) still need price coverage. " if data_gap_count else ""
        improve_body = (
            f"Best next for coverage: {gap_note}Open Data Health for the trusted-data pilot path; "
            "fundamentals, source-backed peers, earnings, and estimates remain gated until trusted local rows exist."
        )

    proof_body = (
        "Check the latest readiness snapshot, reviewed batch packet, proof ledger, and still-blocked fields before trusting a changed state."
    )
    if price_ready <= 0:
        proof_body = "Open proof history first; candidate pages should stay empty when local data cannot support them."
    elif has_depth_gap:
        proof_body = "Use proof history to see why available price coverage does not automatically unlock fundamentals, peer valuation, earnings, or estimates."

    return [
        (
            "Review one stock",
            review_body,
            "Single-Stock Report",
            "neutral",
        ),
        (
            "Improve data coverage",
            improve_body,
            "Data Health",
            improve_tone,
        ),
        (
            "Inspect proof",
            proof_body,
            "Data Health",
            "neutral",
        ),
    ]
