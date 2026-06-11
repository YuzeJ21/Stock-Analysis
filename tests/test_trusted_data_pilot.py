from src.trusted_data_pilot import build_trusted_data_pilot_candidates, render_trusted_data_pilot_candidates


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
    assert "1. META - fundamentals_dcf" in rendered
    assert "make focus-fundamentals TICKER=META" in rendered
    assert "make imports-validate && make imports-preview && make imports-apply" in rendered
    assert "QQQ and SMH are excluded from this company pilot queue" in rendered
    assert "Stop condition: if trusted source rows are unavailable" in rendered
