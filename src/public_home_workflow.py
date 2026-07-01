from __future__ import annotations


def _format_optional_text(value: object, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "<na>"}:
        return fallback
    return text


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


def public_home_current_data_coverage_cards(summary: dict[str, object]) -> list[dict[str, object]]:
    """Return the public Home coverage snapshot cards without renderer dependencies."""

    master = int(summary.get("master_universe") or summary.get("master_count") or summary.get("universe_count") or 0)
    active = int(summary.get("active_universe") or summary.get("active_count") or 0)
    blocked = int(summary.get("blocked_by_data") or summary.get("blocked") or 0)
    partial = int(summary.get("partial") or 0)
    updated_at = _format_optional_text(summary.get("updated_at"), "Run make readiness for the latest timestamp")

    def _coverage_line(label: str, key: str, *, blocked_key: str | None = None) -> str:
        ready = int(summary.get(key) or 0)
        denominator = master or 0
        pct = (ready / denominator * 100) if denominator else 0.0
        blocked_count = int(summary.get(blocked_key) or max(denominator - ready, 0)) if blocked_key else max(denominator - ready, 0)
        return f"{label}: {ready:,}/{denominator:,} ready ({pct:.1f}%); {blocked_count:,} still locked."

    return [
        {
            "kicker": "CURRENT SNAPSHOT",
            "title": f"{master:,} tracked / {active:,} active",
            "body": (
                f"{partial:,} tickers have partial coverage and {blocked:,} are blocked by data. "
                f"Snapshot timestamp: {updated_at}."
            ),
            "badges": ["public snapshot", "row-limited"],
            "command": "make status-check TOP_N=5",
        },
        {
            "kicker": "BREADTH",
            "title": "Price and setup coverage",
            "body": (
                f"{_coverage_line('Price', 'price_ready')} "
                f"{_coverage_line('Momentum', 'momentum_ready')} "
                "Use the capped dry run before changing local CSVs."
            ),
            "badges": ["biggest unlock", "dry-run first"],
            "command": "make price-refresh-loop DRY_RUN=1",
        },
        {
            "kicker": "DEPTH",
            "title": "Fundamentals and DCF coverage",
            "body": (
                f"{_coverage_line('Fundamentals', 'fundamentals_ready')} "
                f"{_coverage_line('DCF', 'dcf_ready')} "
                "DCF-ready means scenario math can be reviewed; blocked does not mean negative."
            ),
            "badges": ["valuation gated", "trusted rows only"],
            "command": "make fundamentals-source-ladder-queue TOP_N=25",
        },
        {
            "kicker": "RELATIVE CONTEXT",
            "title": "Peer coverage",
            "body": (
                f"{_coverage_line('Peers', 'peer_ready')} "
                "Peer trend and peer valuation remain separate; missing mappings are not inferred from sector labels."
            ),
            "badges": ["source-backed peers", "no fallback as fact"],
            "command": "make peer-mapping-queue TOP_N=25",
        },
        {
            "kicker": "OPTIONAL CONTEXT",
            "title": "Earnings and analyst estimates",
            "body": (
                f"{_coverage_line('Earnings', 'earnings_ready')} "
                f"{_coverage_line('Analyst estimates', 'analyst_estimates_ready')} "
                "Zero ready rows means intentionally locked until trusted local inputs exist."
            ),
            "badges": ["schema first", "not inferred"],
            "command": "make optional-context-worklist TOP_N=25",
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
            "badges": ["source proof", "visitor first"],
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
            "title": "Home -> Stock Selector -> one ticker -> Data Health -> Proof History",
            "body": (
                "Home shows coverage. Stock Selector filters readiness-backed candidates. "
                "Single-Stock Report shows what can be reviewed now. Data Health explains missing source inputs. "
                "Proof History is checked before trusting a changed state."
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
            "title": "Choose a candidate, then open one ticker",
            "body": (
                "Stock Selector narrows readiness-backed candidates before Single-Stock Report shows the selected ticker, "
                "what can be reviewed now, what is blocked or excluded, and where Data Health fits next."
            ),
            "badges": ["selector", "one ticker"],
        },
        {
            "kicker": "STEP 3",
            "title": "Route locks to Data Health",
            "body": (
                f"{blocked:,} blocked states stay visible. Data Health names the source-proof lane, manual gate, and stop rule "
                "without making visitors read raw CSV tables first."
            ),
            "badges": ["source proof", "evidence collapsed"],
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

    selector_body = (
        "Filter readiness-backed research candidates before choosing the next ticker review path."
    )
    selector_tone = "neutral"
    if price_ready <= 0:
        selector_body = (
            "Candidate pages should stay empty when local data cannot support them; use Data Health and proof history first."
        )
        selector_tone = "warning"

    return [
        (
            "Review one stock",
            review_body,
            "?mode=public&page=single-stock-report&ticker=NVDA&open=1",
            "neutral",
        ),
        (
            "Explore ready names",
            selector_body,
            "?mode=public&page=stock-selector",
            selector_tone,
        ),
        (
            "Check data coverage",
            improve_body,
            "?mode=public&page=data-health&drawer=proof",
            improve_tone,
        ),
        (
            "Inspect proof",
            proof_body,
            "?mode=public&page=proof-history",
            "neutral",
        ),
    ]


def public_home_real_workflow_cards(summary: dict[str, object]) -> list[dict[str, object]]:
    """Return the connected public workflow cards used behind the optional Home drawer."""

    price_ready = int(summary.get("price_ready") or 0)
    dcf_ready = int(summary.get("dcf_ready") or 0)
    peer_ready = int(summary.get("peer_ready") or 0)
    earnings_ready = int(summary.get("earnings_ready") or 0)
    estimates_ready = int(summary.get("analyst_estimates_ready") or summary.get("analyst_ready") or 0)
    depth_locked = max(price_ready - dcf_ready, 0)
    peer_locked = max(dcf_ready - peer_ready, 0)
    optional_ready = earnings_ready + estimates_ready

    return [
        {
            "kicker": "WORKFLOW 1",
            "title": "Start with the live readiness snapshot",
            "body": (
                f"{price_ready:,} price-ready, {dcf_ready:,} DCF-ready, and {peer_ready:,} peer-ready names are available in the saved local snapshot. "
                "Use this as the entry point before opening ticker pages or proof drawers."
            ),
            "badges": ["readiness first", "live local state"],
            "command": "make status-check TOP_N=5",
        },
        {
            "kicker": "WORKFLOW 2",
            "title": "Review one ticker from the current state",
            "body": (
                "Open a Single-Stock Report to see ready, blocked, excluded, and monitor-only sections for one ticker. "
                "Use example tickers only as state samples; the workflow also works for any local ticker."
            ),
            "badges": ["one ticker", "state-based"],
            "command": "make stock-report-md TICKER=<ticker>",
        },
        {
            "kicker": "WORKFLOW 3",
            "title": "Route locked sections to Data Health",
            "body": (
                f"{depth_locked:,} price-ready names still need trusted fundamentals before deeper company review, and {peer_locked:,} DCF-ready names still need peer inputs. "
                "Data Health shows the source-proof lane, stop rule, and copy-only next command."
            ),
            "badges": ["blocked stays visible", "source proof"],
            "command": "make data-coverage-proof-queues TOP_N=10",
        },
        {
            "kicker": "WORKFLOW 4",
            "title": "Record proof before trusting a changed state",
            "body": (
                f"{optional_ready:,} optional earnings or estimate lanes have ready rows today; unavailable optional context stays locked. "
                "After any reviewed data change, rebuild readiness and use proof history before reading the changed report."
            ),
            "badges": ["proof before interpretation", "research-only"],
            "command": "make pilot-readiness-check TOP_N=10",
        },
    ]


def public_home_next_step_cards(summary: dict[str, object]) -> list[dict[str, object]]:
    """Return copy-ready public Home next-step cards gated by readiness state."""

    price_ready = int(summary.get("price_ready") or 0)
    master = int(summary.get("master_universe") or summary.get("universe_count") or 0)
    dcf_ready = int(summary.get("dcf_ready") or 0)
    peer_ready = int(summary.get("peer_ready") or 0)
    earnings_ready = int(summary.get("earnings_ready") or 0)
    estimates_ready = int(summary.get("analyst_estimates_ready") or summary.get("analyst_ready") or 0)

    if price_ready < master:
        primary = {
            "kicker": "BEST NEXT STEP",
            "title": "Expand price coverage",
            "body": (
                "More tickers need daily price history before momentum, liquidity, and market-context views become useful. "
                "Start with the scalable dry run so you can review a capped batch plan instead of repeating 25-ticker refreshes manually."
            ),
            "badges": ["biggest blocker", "dry run first"],
            "command": "make price-refresh-loop DRY_RUN=1",
        }
    elif dcf_ready <= peer_ready:
        primary = {
            "kicker": "BEST NEXT STEP",
            "title": "Add trusted fundamentals",
            "body": (
                "Fundamentals unlock DCF and better company-level research. Use the source ladder so SEC, "
                "Yahoo/yfinance, and configured API fallbacks are tried before any blocker is recorded."
            ),
            "badges": ["deep research"],
            "command": "make fundamentals-source-ladder-queue TOP_N=25",
        }
    else:
        primary = {
            "kicker": "BEST NEXT STEP",
            "title": "Add source-backed peers",
            "body": "Peer mappings unlock peer comparison for DCF-ready companies. Do not use guessed peer relationships.",
            "badges": ["peer research"],
            "command": "make peer-mapping-queue TOP_N=25",
        }

    optional_title = "Optional context is locked"
    optional_body = "Earnings and analyst estimates are not broken; they are waiting for trusted inputs."
    if earnings_ready or estimates_ready:
        optional_title = "Optional context is available"
        optional_body = "Some earnings or estimate data is available. Review it as context, not as a recommendation."

    return [
        primary,
        {
            "kicker": "START HERE",
            "title": "Read the ready sections first",
            "body": "Start with names that have enough local data for the view you opened. Blocked rows are useful, but they are a missing-data list, not a conclusion list.",
            "badges": ["visitor friendly"],
            "command": "make stock-report-md TICKER=NVDA",
        },
        {
            "kicker": "WHAT STAYS LOCKED",
            "title": "No data, no conclusion",
            "body": "If valuation, peers, earnings, or estimates are missing, the app keeps that analysis unavailable until trusted local rows exist.",
            "badges": ["research-only"],
            "command": "make data-wizard TOP_N=10",
        },
        {
            "kicker": "OPTIONAL DATA",
            "title": optional_title,
            "body": optional_body,
            "badges": ["not required"],
            "command": "make optional-context-worklist TOP_N=25",
        },
        {
            "kicker": "PROOF PATH",
            "title": "Prove the new state before reading conclusions",
            "body": (
                "After a refresh or import, rerun readiness before interpreting changed cards. "
                "Then review the local status snapshot and reopen Home so ready and locked counts are current."
            ),
            "badges": ["proof first", "copy-only"],
            "command": "make readiness && make status-check TOP_N=5",
        },
        {
            "kicker": "PILOT PATH",
            "title": "Improve 5-10 companies first",
            "body": (
                "Do not try to make the full universe analysis-ready at once. For a small trusted-data pilot, start with the status gate. Run project status first, then open the read-only "
                "candidate list only when executable company candidates exist; use the provider setup checklist when source-proof queues are exhausted. "
                "Improve prices, fundamentals, DCF fields, and peers only where source proof exists. "
                "Inspect one company packet before applying rows; if source proof is missing, keep the ticker visibly blocked "
                "and move to the next candidate."
            ),
            "badges": ["trusted data", "pilot"],
            "command": "make project-status",
        },
    ]
