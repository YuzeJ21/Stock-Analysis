from src.trusted_data_pilot import (
    build_trusted_data_pilot_candidates,
    pilot_evidence_row_template,
    pilot_lane_label,
    pilot_local_file_status,
    pilot_operator_decision,
    pilot_outcome_checklist_lines,
    pilot_primary_missing_input,
    pilot_proof_story_lines,
    pilot_public_shortlist,
    pilot_quick_path_lines,
    pilot_rank_reason,
    pilot_rejected_report_path,
    pilot_review_path,
    pilot_review_board_row,
    pilot_secondary_locked_context,
    pilot_selection_brief,
    pilot_skip_condition,
    pilot_trusted_row_path,
    render_trusted_data_pilot_candidates,
    render_trusted_data_pilot_packet,
)


def _write_text(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    assert pilot_lane_label("fundamentals_dcf") == "Fundamentals / DCF proof path"
    assert pilot_lane_label("peer_mapping") == "Peer mapping proof path"
    assert pilot_lane_label("peer_valuation_inputs") == "Peer valuation inputs proof path"
    assert pilot_lane_label("optional_context_locked") == "Optional context proof path"
    assert pilot_lane_label("unexpected") == "Trusted-data proof path"


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
    assert pilot_rejected_report_path(fundamentals) == "data/rejected/fundamentals_import_rejected.csv"
    assert pilot_rejected_report_path(peers) == "data/rejected/peers_import_rejected.csv"


def test_pilot_local_file_status_surfaces_reviewable_file_state(tmp_path):
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
    _write_text(tmp_path / "data" / "imports" / "fundamentals.csv", "ticker,revenue\nCRDO,1\nMETA,2\n")
    _write_text(tmp_path / "data" / "imports" / "peers.csv", "ticker,peer_ticker,source\nMU,NVDA,source note\n")
    _write_text(tmp_path / "data" / "staged" / "fundamentals" / "crdo.csv", "ticker,revenue\nCRDO,1\n")
    _write_text(tmp_path / "data" / "rejected" / "fundamentals_import_rejected.csv", "source_file,source_row,ticker,rejection_reason\n")

    fundamentals_status = pilot_local_file_status(fundamentals, root=tmp_path).lower()
    peer_status = pilot_local_file_status(peers, root=tmp_path).lower()

    assert "fundamentals import 2 data row(s)" in fundamentals_status
    assert "staged fundamentals 1 file(s)" in fundamentals_status
    assert "rejected-row report present" in fundamentals_status
    assert "file presence is not proof" in fundamentals_status
    assert "rows still require source review" in fundamentals_status
    assert "peer import 1 data row(s)" in peer_status
    assert "rejected-row report missing" in peer_status
    assert "file presence is not proof" in peer_status
    assert "source-backed relationship review" in peer_status
    assert "buy" not in fundamentals_status + peer_status
    assert "sell" not in fundamentals_status + peer_status


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

    assert reason == "active-universe public-demo name; fundamentals / dcf proof path; priority 1; missing revenue, free-cash-flow margin."
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


def test_pilot_evidence_row_template_is_copyable_and_data_honest():
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

    row = pilot_evidence_row_template(candidate)

    assert row.startswith("CRDO | before: run report | after: rerun report | revenue, free-cash-flow margin |")
    assert "make imports-validate && make imports-preview && make imports-apply" in row
    assert "outputs/stock_reports/crdo.md" in row
    assert "keep visible if source proof is unavailable or readiness remains blocked" in row
    assert "fcf_margin" not in row
    assert "buy" not in row.lower()
    assert "sell" not in row.lower()


def test_pilot_primary_missing_input_separates_secondary_optional_context():
    candidate = build_trusted_data_pilot_candidates(
        [],
        [],
        [
            {
                "ticker": "MU",
                "asset_type": "company",
                "in_active_universe": "True",
                "peer_ready": "False",
                "missing_data": "peers: needs at least 2 peers with momentum-ready price history; earnings: trusted local CSV input; analyst_estimates: trusted local CSV input",
                "next_action": "make focus-peers TICKER=MU",
            }
        ],
        top_n=10,
    )[0]

    assert pilot_primary_missing_input(candidate) == "peers: needs at least 2 peers with momentum-ready price history"
    assert pilot_secondary_locked_context(candidate) == "earnings: trusted local CSV input; analyst estimates: trusted local CSV input"
    assert pilot_rank_reason(candidate).endswith(
        "missing peers: needs at least 2 peers with momentum-ready price history."
    )
    assert pilot_evidence_row_template(candidate).startswith(
        "MU | before: run report | after: rerun report | peers: needs at least 2 peers with momentum-ready price history |"
    )


def test_pilot_review_board_row_makes_continue_skip_and_evidence_explicit():
    candidate = build_trusted_data_pilot_candidates(
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
    )[0]

    row = pilot_review_board_row(candidate)
    rendered = row.lower()

    assert "meta: continue if source proof exists" in rendered
    assert "skip for now if trusted sec or manual fundamentals rows are not reviewable" in rendered
    assert "make trusted-data-pilot-packet ticker=meta" in rendered
    assert "evidence row:" in rendered
    assert "outputs/stock_reports/meta.md" in rendered
    assert "placeholder" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_pilot_skip_condition_is_lane_specific():
    candidates = build_trusted_data_pilot_candidates(
        [
            {
                "ticker": "META",
                "priority": "1",
                "dcf_ready": "False",
                "missing_required_for_dcf": "shares_outstanding",
            }
        ],
        [
            {
                "ticker": "MU",
                "priority": "2",
                "peer_blocker_type": "missing_peer_mapping",
                "missing_peer_reason": "needs source-backed peer mappings",
            },
        ],
        [
            {"ticker": "META", "asset_type": "company", "in_active_universe": "True"},
            {"ticker": "MU", "asset_type": "company", "in_active_universe": "True"},
        ],
        top_n=10,
    )

    rendered = " ".join(pilot_skip_condition(candidate) for candidate in candidates).lower()

    assert "trusted sec or manual fundamentals rows are not reviewable" in rendered
    assert "peer relationships cannot be supported by a source note" in rendered
    assert "placeholder" not in rendered


def test_pilot_selection_brief_explains_how_to_choose_small_pilot():
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
        [
            {
                "ticker": "MU",
                "priority": "2",
                "peer_blocker_type": "missing_peer_mapping",
                "missing_peer_reason": "needs source-backed peer mappings",
                "focus_command": "make focus-peers TICKER=MU",
            }
        ],
        [
            {"ticker": "META", "asset_type": "company", "in_active_universe": "True"},
            {"ticker": "MU", "asset_type": "company", "in_active_universe": "True"},
        ],
        top_n=10,
    )

    brief = "\n".join(pilot_selection_brief(candidates))

    assert "choose 5-10 operating companies only when you can review source proof" in brief
    assert "2 active-universe candidate(s)" in brief
    assert "Fundamentals / DCF proof path: 1" in brief
    assert "Peer mapping proof path: 1" in brief
    assert "make trusted-data-pilot TICKERS=MU,META TOP_N=2" in brief
    assert "after choosing active/demo names" in brief
    assert "No broad-universe overflow is needed for the first pilot shortlist." in brief
    assert "before report, lane review, trusted source row" in brief
    assert "keep that ticker blocked and move to the next candidate" in brief
    assert "placeholder" in brief
    assert "recommend" not in brief.lower()


def test_pilot_public_shortlist_prefers_active_and_demo_names_before_broad_fillers(tmp_path):
    candidates = build_trusted_data_pilot_candidates(
        [
            {
                "ticker": "AAPG",
                "priority": "1",
                "dcf_ready": "False",
                "missing_required_for_dcf": "revenue",
                "focus_command": "make focus-fundamentals TICKER=AAPG",
            },
            {
                "ticker": "META",
                "priority": "1",
                "dcf_ready": "False",
                "missing_required_for_dcf": "shares_outstanding",
                "focus_command": "make focus-fundamentals TICKER=META",
            },
            {
                "ticker": "AARD",
                "priority": "1",
                "dcf_ready": "False",
                "missing_required_for_dcf": "revenue",
                "focus_command": "make focus-fundamentals TICKER=AARD",
            },
        ],
        [],
        [
            {"ticker": "AAPG", "asset_type": "company", "in_active_universe": "False"},
            {"ticker": "META", "asset_type": "company", "in_active_universe": "True"},
            {"ticker": "AARD", "asset_type": "company", "in_active_universe": "False"},
        ],
        top_n=10,
    )

    shortlist = pilot_public_shortlist(candidates)
    brief = "\n".join(pilot_selection_brief(candidates))
    _write_text(tmp_path / "data" / "imports" / "fundamentals.csv", "ticker,revenue\nMETA,1\n")
    _write_text(tmp_path / "data" / "rejected" / "fundamentals_import_rejected.csv", "source_file,source_row,ticker,rejection_reason\n")

    rendered = render_trusted_data_pilot_candidates(candidates, root=tmp_path)

    assert [candidate.ticker for candidate in candidates] == ["META", "AAPG", "AARD"]
    assert [candidate.ticker for candidate in shortlist] == ["META"]
    assert "Suggested pilot command after choosing active/demo names: make trusted-data-pilot TICKERS=META TOP_N=1" in brief
    assert "Optional broad-universe overflow: AAPG, AARD; use only after source proof exists." in brief
    assert "move to the next active/demo candidate: make trusted-data-pilot TICKERS=META TOP_N=1" in rendered
    assert "make trusted-data-pilot TICKERS=META,AAPG,AARD TOP_N=3" not in rendered


def test_pilot_selection_brief_handles_empty_queue_without_forcing_data():
    brief = "\n".join(pilot_selection_brief([]))

    assert "no company candidates matched" in brief
    assert "do not force a pilot" in brief
    assert "before importing rows" in brief


def test_pilot_quick_path_lines_show_first_action_before_detailed_evidence():
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

    quick_path = "\n".join(pilot_quick_path_lines(candidates))

    assert "Shortlist: META." in quick_path
    assert "Start with one packet: make trusted-data-pilot-packet TICKER=META" in quick_path
    assert "Review its lane: make sec-stage-queue TOP_N=25 -> make focus-fundamentals TICKER=META" in quick_path
    assert "Trusted input target: data/staged/fundamentals/ or data/imports/fundamentals.csv" in quick_path
    assert "Stop if source proof is unavailable: keep META visibly blocked" in quick_path
    assert "Evidence required:" not in quick_path


def test_pilot_proof_story_lines_explain_loop_without_claiming_data_changed():
    candidate = build_trusted_data_pilot_candidates(
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
        top_n=10,
    )[0]

    story = "\n".join(pilot_proof_story_lines(candidate))

    assert "snapshot current readiness and generate a before report" in story
    assert "review CRDO in the Fundamentals / DCF proof path" in story
    assert "validate, preview, and check rejected rows" in story
    assert "only the rebuilt report can prove the lane changed" in story
    assert "keep the blocker visible and move to the next candidate" in story
    assert "buy" not in story.lower()
    assert "sell" not in story.lower()
    assert "recommend" not in story.lower()


def test_pilot_outcome_checklist_keeps_supported_blocked_and_skip_states_clear():
    candidate = build_trusted_data_pilot_candidates(
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
        top_n=10,
    )[0]

    rendered = "\n".join(pilot_outcome_checklist_lines(candidate)).lower()

    assert "supported: crdo moves forward only if rebuilt readiness and the regenerated report show the lane is ready" in rendered
    assert "still blocked: keep revenue visible" in rendered
    assert "skip: if source proof is unavailable" in rendered
    assert "placeholder rows" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "recommend" not in rendered


def test_render_trusted_data_pilot_candidates_is_read_only_and_actionable(tmp_path):
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

    _write_text(tmp_path / "data" / "imports" / "fundamentals.csv", "ticker,revenue\nMETA,1\n")
    _write_text(tmp_path / "data" / "rejected" / "fundamentals_import_rejected.csv", "source_file,source_row,ticker,rejection_reason\n")

    rendered = render_trusted_data_pilot_candidates(candidates, root=tmp_path)

    assert "Read-only: this command ranks current local blockers" in rendered
    assert "does not refresh, import, edit CSVs, or change readiness outputs" in rendered
    assert "Pilot lanes are plain-English proof paths" in rendered
    assert "How to choose the pilot:" in rendered
    assert "Quick path:" in rendered
    assert "Shortlist: META." in rendered
    assert "Start with one packet: make trusted-data-pilot-packet TICKER=META" in rendered
    assert "What the proof loop proves:" in rendered
    assert "Baseline: snapshot current readiness and generate a before report so the starting mode is visible." in rendered
    assert "Source proof: review META in the Fundamentals / DCF proof path and add rows only when the source evidence is trusted." in rendered
    assert "Rebuild: rerun readiness and the stock report; only the rebuilt report can prove the lane changed." in rendered
    assert "How to read the outcome:" in rendered
    assert "Supported: META moves forward only if rebuilt readiness and the regenerated report show the lane is ready." in rendered
    assert "Still blocked: keep shares outstanding visible when validation fails, rejected rows appear, or the report remains locked." in rendered
    assert "Skip: if source proof is unavailable, do not apply placeholder rows; move to the next shortlisted company." in rendered
    assert rendered.index("Quick path:") < rendered.index("What the proof loop proves:") < rendered.index("How to read the outcome:") < rendered.index("Compact review board:")
    assert rendered.index("Quick path:") < rendered.index("Compact review board:")
    assert "Compact review board:" in rendered
    assert "Detailed review board:" not in rendered
    assert "META: Fundamentals / DCF proof path; missing input: shares outstanding; packet make trusted-data-pilot-packet TICKER=META; skip if source proof is unavailable." in rendered
    assert "META: continue if source proof exists" not in rendered
    assert "Skip for now if trusted SEC or manual fundamentals rows are not reviewable." not in rendered
    assert "evidence row: META | before: run report | after: rerun report" not in rendered
    assert "Pilot selection rule: choose 5-10 operating companies only when you can review source proof" in rendered
    assert "Suggested pilot command after choosing active/demo names: make trusted-data-pilot TICKERS=META TOP_N=1" in rendered
    assert "No broad-universe overflow is needed for the first pilot shortlist." in rendered
    assert "Useful pilot win: before report, lane review, trusted source row" in rendered
    assert "1. META - Fundamentals / DCF proof path" not in rendered
    assert "Need local proof detail? Rerun with `make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1`." in rendered
    assert "Rank reason: active-universe public-demo name; fundamentals / dcf proof path; priority 1; missing shares outstanding." not in rendered
    assert "Next decision: Choose this company only if you can review trusted SEC or manual fundamentals rows" not in rendered
    assert (
        "Decision gate: continue only if you have trusted SEC or manual fundamentals rows for the missing DCF fields"
        not in rendered
    )
    assert "Decision gate: Decision gate:" not in rendered
    assert "do not apply placeholder rows just to make the report look complete" not in rendered
    assert "fundamentals_dcf" not in rendered
    assert "Packet command: make trusted-data-pilot-packet TICKER=META" not in rendered
    assert "Lane check: make focus-fundamentals TICKER=META" not in rendered
    assert "Review path: make sec-stage-queue TOP_N=25 -> make focus-fundamentals TICKER=META" not in rendered
    assert "Trusted row target: data/staged/fundamentals/ or data/imports/fundamentals.csv" not in rendered
    assert "Trusted input target: data/staged/fundamentals/ or data/imports/fundamentals.csv" in rendered
    assert "Local file status: fundamentals import 1 data row(s); staged fundamentals missing; rejected-row report present." not in rendered
    assert "Validate/apply only reviewed rows: make imports-validate && make imports-preview && make imports-apply" in rendered
    assert "make imports-validate && make imports-preview && make imports-apply" in rendered
    assert "2. make trusted-data-pilot-packet TICKER=META" in rendered
    assert "3. Review the lane blocker: make sec-stage-queue TOP_N=25 -> make focus-fundamentals TICKER=META" in rendered
    assert "4. Prepare trusted rows only if the source review passes: data/staged/fundamentals/ or data/imports/fundamentals.csv" in rendered
    assert "6. Check rejected-row report: data/rejected/fundamentals_import_rejected.csv" in rendered
    assert "7. Rebuild lane proof: make readiness && make dcf-readiness && make stock-report-md TICKER=META" in rendered
    assert "Evidence expectation: Evidence required: before report, lane review output" not in rendered
    assert "Do not call META available until the rebuilt report proves the lane changed." not in rendered
    assert "8. If still blocked, keep the blocker visible and move to the next active/demo candidate: make trusted-data-pilot TICKERS=META TOP_N=1" in rendered
    assert "8. make stock-report-md" not in rendered
    assert "QQQ and SMH are excluded from this company pilot list" in rendered
    assert "Stop condition: if trusted source rows are unavailable" in rendered

    verbose = render_trusted_data_pilot_candidates(candidates, root=tmp_path, verbose=True)

    assert "Verbose candidate details:" in verbose
    assert "Need local proof detail?" not in verbose
    assert "1. META - Fundamentals / DCF proof path" in verbose
    assert "Rank reason: active-universe public-demo name; fundamentals / dcf proof path; priority 1; missing shares outstanding." in verbose
    assert "Next decision: Choose this company only if you can review trusted SEC or manual fundamentals rows" in verbose
    assert (
        "Decision gate: continue only if you have trusted SEC or manual fundamentals rows for the missing DCF fields"
        in verbose
    )
    assert "do not apply placeholder rows just to make the report look complete" in verbose
    assert "Packet command: make trusted-data-pilot-packet TICKER=META" in verbose
    assert "Lane check: make focus-fundamentals TICKER=META" in verbose
    assert "Review path: make sec-stage-queue TOP_N=25 -> make focus-fundamentals TICKER=META" in verbose
    assert "Local file status: fundamentals import 1 data row(s); staged fundamentals missing; rejected-row report present. File presence is not proof." in verbose
    assert "Rejected-row report to review: data/rejected/fundamentals_import_rejected.csv" in verbose
    assert "Evidence expectation: Evidence required: before report, lane review output" in verbose
    assert "Evidence row: META | before: run report | after: rerun report" in verbose
    assert "Do not call META available until the rebuilt report proves the lane changed." in verbose


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

    assert "1. MU - Peer mapping proof path" not in rendered
    assert "peer_mapping" not in rendered
    assert "Packet command: make trusted-data-pilot-packet TICKER=MU" not in rendered
    assert "Lane check: make focus-peers TICKER=MU" not in rendered
    assert "3. Review the lane blocker: make peer-mapping-queue TOP_N=25 -> make focus-peers TICKER=MU" in rendered
    assert "Trusted row target: data/imports/peers.csv plus reviewed peer price/fundamentals rows when needed" not in rendered
    assert "Trusted input target: data/imports/peers.csv plus reviewed peer price/fundamentals rows when needed" in rendered
    assert "MU: Peer mapping proof path; missing input: needs at least 2 source-backed peer mappings; packet make trusted-data-pilot-packet TICKER=MU; skip if source proof is unavailable." in rendered
    assert "Rejected-row report to review: data/rejected/peers_import_rejected.csv" not in rendered
    assert (
        "Decision gate: continue only if you have source-backed peer relationships, not sector or industry similarity alone"
        not in rendered
    )
    assert "Decision gate: Decision gate:" not in rendered
    assert "leave peer valuation blocked and show peer context only when supported" not in rendered
    assert "7. Rebuild lane proof: make readiness && make peer-mapping-queue TOP_N=25 && make stock-report-md TICKER=MU" in rendered
    assert "8. make readiness && make dcf-readiness" not in rendered
    assert "sector or industry fallback" not in rendered.lower()

    verbose = render_trusted_data_pilot_candidates(candidates, verbose=True)

    assert "1. MU - Peer mapping proof path" in verbose
    assert "Packet command: make trusted-data-pilot-packet TICKER=MU" in verbose
    assert "Lane check: make focus-peers TICKER=MU" in verbose
    assert "Trusted row target: data/imports/peers.csv plus reviewed peer price/fundamentals rows when needed" in verbose
    assert "Rejected-row report to review: data/rejected/peers_import_rejected.csv" in verbose
    assert (
        "Decision gate: continue only if you have source-backed peer relationships, not sector or industry similarity alone"
        in verbose
    )
    assert "leave peer valuation blocked and show peer context only when supported" in verbose
    assert "sector or industry fallback" in verbose.lower()


def test_render_trusted_data_pilot_candidates_names_first_fundamentals_demo_when_peer_first():
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
        [
            {
                "ticker": "MU",
                "priority": "2",
                "peer_blocker_type": "peer_valuation_inputs",
                "missing_peer_reason": "peer fundamentals or peer price/market-cap context",
                "focus_command": "make focus-peers TICKER=MU",
                "validation_sequence": "make peer-mapping-queue TOP_N=25 -> make focus-peers TICKER=MU -> make focus-fundamentals TICKER=SNDK",
            }
        ],
        [
            {"ticker": "MU", "asset_type": "company", "in_active_universe": "True"},
            {"ticker": "CRDO", "asset_type": "company", "in_active_universe": "True"},
        ],
        top_n=10,
    )

    rendered = render_trusted_data_pilot_candidates(candidates).lower()

    assert "shortlist: mu, crdo." in rendered
    assert "start with one packet: make trusted-data-pilot-packet ticker=mu" in rendered
    assert "for a fundamentals/dcf proof demo, use make trusted-data-pilot-packet ticker=crdo" in rendered
    assert "review its lane: make peer-mapping-queue top_n=25 -> make focus-peers ticker=mu -> make focus-fundamentals ticker=sndk" in rendered
    assert "do not apply placeholder rows" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_trusted_data_pilot_uses_peer_valuation_lane_for_mapped_dcf_ready_rows():
    candidates = build_trusted_data_pilot_candidates(
        [
            {
                "ticker": "MU",
                "priority": "2",
                "dcf_ready": "True",
                "has_peer_mapping": "True",
                "peer_ready": "False",
                "missing_required_for_dcf": "",
                "missing_required_for_peer_relative": "peer fundamentals or peer price/market-cap context",
                "focus_command": "make focus-fundamentals TICKER=SNDK",
                "recommended_action": "Complete trusted peer fundamentals or peer price history before treating peer-relative context as ready.",
            }
        ],
        [],
        [{"ticker": "MU", "asset_type": "company", "in_active_universe": "True"}],
        top_n=10,
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.lane == "peer_valuation_inputs"
    assert candidate.next_command == "make focus-peers TICKER=MU"
    assert "make focus-fundamentals TICKER=SNDK" in candidate.validation_path
    assert "reviewed mapped-peer fundamentals" in pilot_trusted_row_path(candidate)
    assert "use data/imports/peers.csv only if mappings change" in pilot_trusted_row_path(candidate)
    assert "data/rejected/fundamentals_import_rejected.csv" in pilot_rejected_report_path(candidate)
    assert "data/rejected/price_import_rejected.csv" in pilot_rejected_report_path(candidate)

    rendered = render_trusted_data_pilot_candidates(candidates)

    assert "MU: Peer valuation inputs proof path" in rendered
    assert "missing input: peer fundamentals or peer price/market-cap context" in rendered
    assert "Review its lane: make peer-mapping-queue TOP_N=25 -> make focus-peers TICKER=MU -> make focus-fundamentals TICKER=SNDK" in rendered
    assert "Trusted input target: reviewed mapped-peer fundamentals in data/imports/fundamentals.csv or verified peer price history" in rendered
    assert "Peer mapping proof path" not in rendered


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

    rendered = render_trusted_data_pilot_candidates(candidates, verbose=True)

    assert "Review path: make peer-mapping-queue TOP_N=25 -> make focus-peers TICKER=MU" in rendered
    assert "3. Review the lane blocker: make peer-mapping-queue TOP_N=25 -> make focus-peers TICKER=MU" in rendered
    assert "make templates -> fill source-backed peers" not in rendered


def test_render_trusted_data_pilot_packet_prints_one_company_proof_loop(tmp_path):
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

    _write_text(tmp_path / "data" / "imports" / "fundamentals.csv", "ticker,revenue\nCRDO,1\n")
    _write_text(tmp_path / "data" / "rejected" / "fundamentals_import_rejected.csv", "source_file,source_row,ticker,rejection_reason\n")

    rendered = render_trusted_data_pilot_packet(candidates[0], requested_ticker="CRDO", root=tmp_path)

    assert "Trusted Data Pilot Evidence Packet" in rendered
    assert "Read-only: this command prints a one-company proof loop" in rendered
    assert "Ticker: CRDO" in rendered
    assert "Pilot lane: Fundamentals / DCF proof path" in rendered
    assert "fundamentals_dcf" not in rendered
    assert "Rank reason: active-universe public-demo name; fundamentals / dcf proof path; priority 1; missing revenue, free-cash-flow margin." in rendered
    assert "Primary lane input: revenue, free-cash-flow margin" in rendered
    assert "Secondary locked context:" not in rendered
    assert "fcf_margin" not in rendered
    assert "Next decision: Choose this company only if you can review trusted SEC or manual fundamentals rows" in rendered
    assert (
        "Decision gate: continue only if you have trusted SEC or manual fundamentals rows for the missing DCF fields"
        in rendered
    )
    assert "If not, leave fundamentals and DCF blocked" in rendered
    assert "do not apply placeholder rows just to make the report look complete" in rendered
    assert "Trusted row target: data/staged/fundamentals/ or data/imports/fundamentals.csv" in rendered
    assert "Local file status: fundamentals import 1 data row(s); staged fundamentals missing; rejected-row report present. File presence is not proof." in rendered
    assert "One-company evidence packet:" in rendered
    assert "What this proves before any conclusion changes:" in rendered
    assert "Baseline: snapshot current readiness and generate a before report so the starting mode is visible." in rendered
    assert "Source proof: review CRDO in the Fundamentals / DCF proof path and add rows only when the source evidence is trusted." in rendered
    assert "Validation: validate, preview, and check rejected rows before applying any local CSV change." in rendered
    assert "Rebuild: rerun readiness and the stock report; only the rebuilt report can prove the lane changed." in rendered
    assert "How to read the outcome:" in rendered
    assert "Supported: CRDO moves forward only if rebuilt readiness and the regenerated report show the lane is ready." in rendered
    assert "Still blocked: keep revenue, free-cash-flow margin visible when validation fails, rejected rows appear, or the report remains locked." in rendered
    assert "Skip: if source proof is unavailable, do not apply placeholder rows; move to the next shortlisted company." in rendered
    assert "1. Baseline readiness: make readiness-snapshot" in rendered
    assert "2. Before report: make stock-report-md TICKER=CRDO" in rendered
    assert "3. Focused blocker check: make focus-fundamentals TICKER=CRDO" in rendered
    assert "4. Prepare or stage trusted rows only if source review passes: data/staged/fundamentals/ or data/imports/fundamentals.csv" in rendered
    assert "5. Validate/apply only reviewed rows: make imports-validate && make imports-preview && make imports-apply" in rendered
    assert "6. Check rejected-row report: data/rejected/fundamentals_import_rejected.csv" in rendered
    assert "make readiness && make dcf-readiness && make stock-report-md TICKER=CRDO" in rendered
    assert "7. Rebuild proof and after report:" in rendered
    assert "8. After report:" not in rendered
    assert "8. Record the evidence row and keep any remaining blocker visible." in rendered
    assert "Evidence required: before report, lane review output, trusted source row or source note" in rendered
    assert "Do not call CRDO available until the rebuilt report proves the lane changed." in rendered
    assert "Evidence table row to record:" in rendered
    assert "ticker | before_mode | after_mode | changed_inputs | validation_commands | report_path | still_blocked_reason" in rendered
    assert "CRDO | before: run report | after: rerun report | revenue, free-cash-flow margin" in rendered
    assert "outputs/stock_reports/crdo.md" in rendered
    assert "keep visible if source proof is unavailable or readiness remains blocked" in rendered
    assert "still_blocked_reason" in rendered
    assert "Stop condition: if trusted source rows are unavailable" in rendered


def test_render_trusted_data_pilot_packet_separates_primary_lane_from_optional_context(tmp_path):
    candidates = build_trusted_data_pilot_candidates(
        [],
        [],
        [
            {
                "ticker": "MU",
                "asset_type": "company",
                "in_active_universe": "True",
                "peer_ready": "False",
                "missing_data": "peers: needs at least 2 peers with momentum-ready price history; earnings: trusted local CSV input; analyst_estimates: trusted local CSV input",
                "next_action": "make focus-peers TICKER=MU",
            }
        ],
        top_n=10,
    )
    _write_text(tmp_path / "data" / "imports" / "peers.csv", "ticker,peer_ticker,source\nMU,NVDA,source note\n")

    rendered = render_trusted_data_pilot_packet(candidates[0], requested_ticker="MU", root=tmp_path)

    assert "Primary lane input: peers: needs at least 2 peers with momentum-ready price history" in rendered
    assert "Secondary locked context: earnings: trusted local CSV input; analyst estimates: trusted local CSV input" in rendered
    assert "Rank reason: active-universe public-demo name; peer mapping proof path; priority 2; missing peers: needs at least 2 peers with momentum-ready price history." in rendered
    assert "MU | before: run report | after: rerun report | peers: needs at least 2 peers with momentum-ready price history |" in rendered
    assert "analyst_estimates" not in rendered
    assert "buy" not in rendered.lower()
    assert "sell" not in rendered.lower()


def test_render_trusted_data_pilot_packet_handles_non_candidate_without_inventing_data():
    rendered = render_trusted_data_pilot_packet(None, requested_ticker="QQQ")

    assert "No operating-company pilot candidate matched QQQ." in rendered
    assert "make trusted-data-pilot-candidates TOP_N=10" in rendered
    assert "QQQ and SMH are not operating-company DCF pilot targets" in rendered
