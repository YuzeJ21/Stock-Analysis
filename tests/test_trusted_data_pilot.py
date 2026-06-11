from src.trusted_data_pilot import (
    build_trusted_data_pilot_candidates,
    pilot_lane_label,
    pilot_operator_decision,
    pilot_rank_reason,
    pilot_review_path,
    pilot_trusted_row_path,
    render_trusted_data_pilot_candidates,
    render_trusted_data_pilot_packet,
)


def test_trusted_data_pilot_candidates_prioritize_active_company_blockers():
    readiness_rows = [
        {"ticker": "META", "asset_type": "company", "in_active_universe": "True"},
        {"ticker": "CRDO", "asset_type": "company", "in_active_universe": "True"},
        {"ticker": "APLD", "asset_type": "company", "in_active_universe": "False"},
        {"ticker": "SPAC", "name": "Example Acquisition Corp.", "asset_type": "company", "in_active_universe": "False"},
        {"ticker": "QQQ", "asset_type": "etf", "in_active_universe": "True"},
        {"ticker": "SMH", "asset_type": "etf", "in_active_universe": "True"},
    ]
    fundamentals_rows = [
        {
            "ticker": "APLD",
            "priority": "1",
            "dcf_ready": "False",
            "missing_required_for_dcf": "free_cash_flow, revenue",
            "focus_command": "make focus-fundamentals TICKER=APLD",
        },
        {
            "ticker": "META",
            "priority": "1",
            "dcf_ready": "False",
            "missing_required_for_dcf": "shares_outstanding",
            "focus_command": "make focus-fundamentals TICKER=META",
        },
        {
            "ticker": "SPAC",
            "priority": "1",
            "dcf_ready": "False",
            "missing_required_for_dcf": "free_cash_flow",
            "focus_command": "make focus-fundamentals TICKER=SPAC",
        },
    ]
    peer_rows = [
        {
            "ticker": "QQQ",
            "priority": "1",
            "peer_blocker_type": "missing_peer_mapping",
            "missing_peer_reason": "needs at least 2 source-backed peer mappings",
            "focus_command": "make focus-peers TICKER=QQQ",
        },
        {
            "ticker": "SMH",
            "priority": "1",
            "peer_blocker_type": "missing_peer_mapping",
            "missing_peer_reason": "needs at least 2 source-backed peer mappings",
            "focus_command": "make focus-peers TICKER=SMH",
        },
        {
            "ticker": "CRDO",
            "priority": "2",
            "peer_blocker_type": "peer_fundamentals_missing",
            "missing_peer_reason": "peer trend comparison ready; peer valuation still requires peer_valuation_ready",
            "next_action_summary": "Add trusted peer fundamentals before showing peer valuation conclusions.",
            "focus_command": "make focus-peers TICKER=CRDO",
            "validation_sequence": "make focus-fundamentals TICKER=<peer> -> make imports-validate",
        },
    ]

    candidates = build_trusted_data_pilot_candidates(
        fundamentals_rows,
        peer_rows,
        readiness_rows,
        top_n=10,
    )

    assert [candidate.ticker for candidate in candidates] == ["CRDO", "META", "APLD"]
    assert candidates[0].lane == "peer_valuation_inputs"
    assert candidates[1].lane == "fundamentals_dcf"
    assert all(candidate.ticker not in {"QQQ", "SMH"} for candidate in candidates)
    assert all(candidate.ticker != "SPAC" for candidate in candidates)


def test_trusted_data_pilot_candidates_honor_ticker_filter():
    candidates = build_trusted_data_pilot_candidates(
        [
            {
                "ticker": "META",
                "priority": "1",
                "dcf_ready": "False",
                "missing_required_for_dcf": "shares_outstanding",
                "focus_command": "make focus-fundamentals TICKER=META",
            },
            {
                "ticker": "APLD",
                "priority": "1",
                "dcf_ready": "False",
                "missing_required_for_dcf": "revenue",
                "focus_command": "make focus-fundamentals TICKER=APLD",
            },
        ],
        [],
        [
            {"ticker": "META", "asset_type": "company", "in_active_universe": "True"},
            {"ticker": "APLD", "asset_type": "company", "in_active_universe": "False"},
        ],
        tickers="META",
        top_n=10,
    )

    assert [candidate.ticker for candidate in candidates] == ["META"]


def test_pilot_lane_label_translates_internal_codes_for_visitors():
    assert pilot_lane_label("fundamentals_dcf") == "Fundamentals / DCF unlock"
    assert pilot_lane_label("peer_mapping") == "Peer mapping unlock"
    assert pilot_lane_label("peer_valuation_inputs") == "Peer valuation inputs unlock"
    assert pilot_lane_label("optional_context_locked") == "Optional context unlock"
    assert pilot_lane_label("unexpected") == "Trusted-data unlock"


def test_pilot_review_path_separates_review_from_validate_apply_steps():
    path = (
        "make peer-mapping-queue TOP_N=25 -> make focus-peers TICKER=MU -> "
        "make imports-validate -> make imports-preview -> make imports-apply"
    )

    rendered = pilot_review_path(path)

    assert rendered == "make peer-mapping-queue TOP_N=25 -> make focus-peers TICKER=MU"
    assert "imports-validate" not in rendered
    assert pilot_review_path("") == "make trusted-data-pilot-candidates TOP_N=10"


def test_pilot_trusted_row_path_points_to_lane_specific_local_inputs():
    fundamentals = build_trusted_data_pilot_candidates(
        [
            {
                "ticker": "CRDO",
                "priority": "1",
                "dcf_ready": "False",
                "missing_required_for_dcf": "revenue",
                "focus_command": "make focus-fundamentals TICKER=CRDO",
            }
        ],
        [],
        [{"ticker": "CRDO", "asset_type": "company", "in_active_universe": "True"}],
    )[0]
    peers = build_trusted_data_pilot_candidates(
        [],
        [
            {
                "ticker": "MU",
                "priority": "2",
                "peer_blocker_type": "missing_peer_mapping",
                "missing_peer_reason": "needs source-backed peer mappings",
                "focus_command": "make focus-peers TICKER=MU",
            }
        ],
        [{"ticker": "MU", "asset_type": "company", "in_active_universe": "True"}],
    )[0]

    assert pilot_trusted_row_path(fundamentals) == "data/staged/fundamentals/ or data/imports/fundamentals.csv"
    assert pilot_trusted_row_path(peers) == "data/imports/peers.csv plus reviewed peer price/fundamentals rows when needed"


def test_pilot_rank_reason_explains_queue_position_without_new_data():
    candidate = build_trusted_data_pilot_candidates(
        [
            {
                "ticker": "CRDO",
                "priority": "1",
                "dcf_ready": "False",
                "missing_required_for_dcf": "revenue, fcf_margin",
                "focus_command": "make focus-fundamentals TICKER=CRDO",
            }
        ],
        [],
        [{"ticker": "CRDO", "asset_type": "company", "in_active_universe": "True"}],
    )[0]

    reason = pilot_rank_reason(candidate)

    assert reason == "active-universe public-demo name; fundamentals / dcf unlock; priority 1; missing revenue, free-cash-flow margin."
    assert "price target" not in reason.lower()
    assert "recommend" not in reason.lower()


def test_pilot_operator_decision_keeps_each_lane_data_honest():
    fundamentals = build_trusted_data_pilot_candidates(
        [
            {
                "ticker": "CRDO",
                "priority": "1",
                "dcf_ready": "False",
                "missing_required_for_dcf": "revenue",
                "focus_command": "make focus-fundamentals TICKER=CRDO",
            }
        ],
        [],
        [{"ticker": "CRDO", "asset_type": "company", "in_active_universe": "True"}],
    )[0]
    peer_candidates = build_trusted_data_pilot_candidates(
        [],
        [
            {
                "ticker": "MU",
                "priority": "2",
                "peer_blocker_type": "missing_peer_mapping",
                "missing_peer_reason": "needs source-backed peer mappings",
                "focus_command": "make focus-peers TICKER=MU",
            },
            {
                "ticker": "NVDA",
                "priority": "2",
                "peer_blocker_type": "peer_fundamentals_missing",
                "missing_peer_reason": "peer valuation needs peer fundamentals",
                "focus_command": "make focus-peers TICKER=NVDA",
            },
        ],
        [
            {"ticker": "MU", "asset_type": "company", "in_active_universe": "True"},
            {"ticker": "NVDA", "asset_type": "company", "in_active_universe": "True"},
        ],
        top_n=10,
    )

    rendered = " ".join(
        [
            pilot_operator_decision(fundamentals),
            pilot_operator_decision(peer_candidates[0]),
            pilot_operator_decision(peer_candidates[1]),
        ]
    ).lower()

    assert "trusted sec or manual fundamentals rows" in rendered
    assert "source-backed peer relationships" in rendered
    assert "sector or industry similarity is research context" in rendered
    assert "mapped peers also have trusted peer valuation inputs" in rendered
    assert "keep peer valuation blocked" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_render_trusted_data_pilot_candidates_is_read_only_and_actionable():
    candidates = build_trusted_data_pilot_candidates(
        [
            {
                "ticker": "META",
                "priority": "1",
                "dcf_ready": "False",
                "missing_required_for_dcf": "shares_outstanding",
                "focus_command": "make focus-fundamentals TICKER=META",
            }
        ],
        [],
        [{"ticker": "META", "asset_type": "company", "in_active_universe": "True"}],
        top_n=10,
    )

    rendered = render_trusted_data_pilot_candidates(candidates)

    assert "Read-only: this command ranks current local blockers" in rendered
    assert "does not refresh, import, edit CSVs, or change readiness outputs" in rendered
    assert "Pilot lanes are plain-English unlock paths" in rendered
    assert "1. META - Fundamentals / DCF unlock" in rendered
    assert "Rank reason: active-universe public-demo name; fundamentals / dcf unlock; priority 1; missing shares outstanding." in rendered
    assert "Operator decision: Choose this company only if you can review trusted SEC or manual fundamentals rows" in rendered
    assert "fundamentals_dcf" not in rendered
    assert "make focus-fundamentals TICKER=META" in rendered
    assert "Review path: make sec-stage-queue TOP_N=25 -> make focus-fundamentals TICKER=META" in rendered
    assert "Trusted row target: data/staged/fundamentals/ or data/imports/fundamentals.csv" in rendered
    assert "Validate/apply only reviewed rows: make imports-validate && make imports-preview && make imports-apply" in rendered
    assert "make imports-validate && make imports-preview && make imports-apply" in rendered
    assert "2. make trusted-data-pilot-packet TICKER=META" in rendered
    assert "3. Review the lane blocker: make sec-stage-queue TOP_N=25 -> make focus-fundamentals TICKER=META" in rendered
    assert "4. Prepare trusted rows only if the source review passes: data/staged/fundamentals/ or data/imports/fundamentals.csv" in rendered
    assert "6. Rebuild lane proof: make readiness && make dcf-readiness && make stock-report-md TICKER=META" in rendered
    assert "Evidence expectation: Evidence required: before report, lane review output" in rendered
    assert "Do not call META unlocked until the rebuilt report proves the lane changed." in rendered
    assert "7. If still blocked, keep the blocker visible and move to the next candidate: make trusted-data-pilot TICKERS=META TOP_N=1" in rendered
    assert "8. make stock-report-md" not in rendered
    assert "QQQ and SMH are excluded from this company pilot queue" in rendered
    assert "Stop condition: if trusted source rows are unavailable" in rendered


def test_render_trusted_data_pilot_candidates_uses_peer_proof_for_peer_led_loop():
    candidates = build_trusted_data_pilot_candidates(
        [],
        [
            {
                "ticker": "MU",
                "priority": "2",
                "peer_blocker_type": "missing_peer_mapping",
                "missing_peer_reason": "needs at least 2 source-backed peer mappings",
                "focus_command": "make focus-peers TICKER=MU",
                "validation_sequence": "make peer-mapping-queue TOP_N=25 -> make focus-peers TICKER=MU -> make imports-validate -> make imports-preview -> make imports-apply",
            }
        ],
        [{"ticker": "MU", "asset_type": "company", "in_active_universe": "True"}],
        top_n=10,
    )

    rendered = render_trusted_data_pilot_candidates(candidates)

    assert "1. MU - Peer mapping unlock" in rendered
    assert "peer_mapping" not in rendered
    assert "3. Review the lane blocker: make peer-mapping-queue TOP_N=25 -> make focus-peers TICKER=MU" in rendered
    assert "Trusted row target: data/imports/peers.csv plus reviewed peer price/fundamentals rows when needed" in rendered
    assert "6. Rebuild lane proof: make readiness && make peer-mapping-queue TOP_N=25 && make stock-report-md TICKER=MU" in rendered
    assert "7. make readiness && make dcf-readiness" not in rendered
    assert "sector or industry fallback" in rendered.lower()


def test_render_trusted_data_pilot_candidates_uses_specific_peer_review_path_by_default():
    candidates = build_trusted_data_pilot_candidates(
        [],
        [
            {
                "ticker": "MU",
                "priority": "2",
                "peer_blocker_type": "missing_peer_mapping",
                "missing_peer_reason": "needs at least 2 source-backed peer mappings",
                "focus_command": "make focus-peers TICKER=MU",
            }
        ],
        [{"ticker": "MU", "asset_type": "company", "in_active_universe": "True"}],
        top_n=10,
    )

    rendered = render_trusted_data_pilot_candidates(candidates)

    assert "Review path: make peer-mapping-queue TOP_N=25 -> make focus-peers TICKER=MU" in rendered
    assert "3. Review the lane blocker: make peer-mapping-queue TOP_N=25 -> make focus-peers TICKER=MU" in rendered
    assert "make templates -> fill source-backed peers" not in rendered


def test_render_trusted_data_pilot_packet_prints_one_company_proof_loop():
    candidates = build_trusted_data_pilot_candidates(
        [
            {
                "ticker": "CRDO",
                "priority": "1",
                "dcf_ready": "False",
                "missing_required_for_dcf": "revenue, fcf_margin",
                "focus_command": "make focus-fundamentals TICKER=CRDO",
            }
        ],
        [],
        [{"ticker": "CRDO", "asset_type": "company", "in_active_universe": "True"}],
        top_n=10,
    )

    rendered = render_trusted_data_pilot_packet(candidates[0], requested_ticker="CRDO")

    assert "Trusted Data Pilot Evidence Packet" in rendered
    assert "Read-only: this command prints a one-company proof loop" in rendered
    assert "Ticker: CRDO" in rendered
    assert "Pilot lane: Fundamentals / DCF unlock" in rendered
    assert "fundamentals_dcf" not in rendered
    assert "Rank reason: active-universe public-demo name; fundamentals / dcf unlock; priority 1; missing revenue, free-cash-flow margin." in rendered
    assert "Missing trusted input: revenue, free-cash-flow margin" in rendered
    assert "fcf_margin" not in rendered
    assert "Operator decision: Choose this company only if you can review trusted SEC or manual fundamentals rows" in rendered
    assert "Trusted row target: data/staged/fundamentals/ or data/imports/fundamentals.csv" in rendered
    assert "One-company evidence packet:" in rendered
    assert "1. Baseline readiness: make readiness-snapshot" in rendered
    assert "2. Before report: make stock-report-md TICKER=CRDO" in rendered
    assert "3. Focused blocker check: make focus-fundamentals TICKER=CRDO" in rendered
    assert "4. Prepare or stage trusted rows only if source review passes: data/staged/fundamentals/ or data/imports/fundamentals.csv" in rendered
    assert "5. Validate/apply only reviewed rows: make imports-validate && make imports-preview && make imports-apply" in rendered
    assert "make readiness && make dcf-readiness && make stock-report-md TICKER=CRDO" in rendered
    assert "6. Rebuild proof and after report:" in rendered
    assert "7. After report:" not in rendered
    assert "7. Record the evidence row and keep any remaining blocker visible." in rendered
    assert "Evidence required: before report, lane review output, trusted source row or source note" in rendered
    assert "Do not call CRDO unlocked until the rebuilt report proves the lane changed." in rendered
    assert "still_blocked_reason" in rendered
    assert "Stop condition: if trusted source rows are unavailable" in rendered


def test_render_trusted_data_pilot_packet_handles_non_candidate_without_inventing_data():
    rendered = render_trusted_data_pilot_packet(None, requested_ticker="QQQ")

    assert "No operating-company pilot candidate matched QQQ." in rendered
    assert "make trusted-data-pilot-candidates TOP_N=10" in rendered
    assert "QQQ and SMH are not operating-company DCF pilot targets" in rendered
