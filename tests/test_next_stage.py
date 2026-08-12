from src.next_stage import render_next_stage


def _inspection_only_payload():
    return {
        "summary": {
            "tickers_with_prices": 265,
            "tickers_total": 3541,
            "tickers_fundamentals_ready": 175,
            "tickers_dcf_ready": 169,
            "tickers_peer_ready": 9,
        },
        "remaining_public_stage_rows": [
            {
                "Stage": "LinkedIn publish",
                "State": "needs_github_sync",
                "Evidence": "Current branch is ahead.",
                "Next Action": "Owner authorization is required.",
            },
            {
                "Stage": "Source-proof queues",
                "State": "check_project_status",
                "Evidence": "Readiness inspection is required.",
                "Next Action": "make readiness-preview TOP_N=20",
            },
            {
                "Stage": "Generated artifacts",
                "State": "excluded_by_default",
                "Evidence": "Generated churn stays local.",
                "Next Action": "Keep generated churn unstaged.",
            },
            {
                "Stage": "Coverage depth",
                "State": "price_gap_remaining",
                "Evidence": "Coverage remains partial.",
                "Next Action": "Wait for reviewed source evidence.",
            },
        ],
        "workflow_continuation": {
            "State": "continue_with_pending_dependencies",
            "Evidence": "External dependencies remain.",
        },
        "continuation_gate": {
            "state": "inspection_only",
            "next_safe_command": "make readiness-preview TOP_N=20",
            "reason": "Working readiness is not tracked release evidence.",
            "rebuild_command": "",
            "stop_rule": "Do not start broad source work.",
            "suppress_execution": True,
        },
    }


def test_next_stage_uses_manual_verification_ladder_when_hosted_url_is_configured(
    monkeypatch,
):
    monkeypatch.setenv("HOSTED_DEMO_URL", "https://stock-demo.example.com")

    output = render_next_stage(".", top_n=1)

    assert "Hosted demo status: manual_verify_required" in output
    assert "https://stock-demo.example.com" in output
    assert "External unblock conditions (not executable now):" in output
    assert "- Hosted account/environment: manual_verify_required" in output
    assert "Hosted demo is awaiting external setup" not in output


def test_next_stage_keeps_external_account_ladder_without_hosted_url(monkeypatch):
    monkeypatch.delenv("HOSTED_DEMO_URL", raising=False)

    output = render_next_stage(".", top_n=1)

    assert "Hosted demo status: external_account_required" in output
    assert "External unblock conditions (not executable now):" in output
    assert "- Hosted account/environment: external_account_required" in output
    assert "Roadmap continuation: continue_with_pending_dependencies" in output


def test_next_stage_inspection_only_routes_external_setup_out_of_executable_section(
    monkeypatch,
):
    monkeypatch.setattr(
        "src.next_stage.build_project_status_payload",
        lambda *_args, **_kwargs: _inspection_only_payload(),
    )
    monkeypatch.setattr(
        "src.next_stage._hosted_url_status",
        lambda _root: "external_account_required; no hosted account",
    )
    monkeypatch.setattr(
        "src.next_stage._provider_status",
        lambda _root: ("FMP", "-", "make fmp-smoke TICKER=<ticker>"),
    )

    output = render_next_stage(".", top_n=1)
    executable = output.split("Next executable repo-side item:\n", 1)[1].split(
        "\n\nExternal unblock conditions (not executable now):", 1
    )[0]
    external = output.split(
        "External unblock conditions (not executable now):", 1
    )[1]

    assert executable.strip() == "- Readiness inspection: make readiness-preview TOP_N=20"
    assert "hosted" not in executable.lower()
    assert "provider" not in executable.lower()
    assert "public-check" not in executable
    assert "hosted account" in external.lower()
    assert "FMP" in external


def test_next_stage_restores_configured_host_and_provider_actions_when_execution_is_allowed(
    monkeypatch,
):
    payload = _inspection_only_payload()
    payload["continuation_gate"] = {
        "state": "current",
        "next_safe_command": "",
        "reason": "Tracked readiness is available.",
        "rebuild_command": "",
        "stop_rule": "",
        "suppress_execution": False,
    }
    monkeypatch.setattr(
        "src.next_stage.build_project_status_payload",
        lambda *_args, **_kwargs: payload,
    )
    monkeypatch.setattr(
        "src.next_stage._hosted_url_status",
        lambda _root: "manual_verify_required; https://stock-demo.example.com",
    )
    monkeypatch.setattr(
        "src.next_stage._provider_status",
        lambda _root: ("-", "FMP", "make fmp-smoke TICKER=<ticker>"),
    )

    output = render_next_stage(".", top_n=1)
    executable = output.split("Next executable repo-side item:\n", 1)[1].split(
        "\n\nRemaining external unblock conditions:", 1
    )[0]

    assert "make public-check" in executable
    assert "verify the five-page public workflow" in executable
    assert "make fmp-smoke TICKER=<ticker>" in executable
    assert "separate reviewed authorization" in executable
    assert "Hosted account/environment: manual_verify_required" not in output
    assert "Provider credentials: configured=FMP" not in output.split(
        "Remaining external unblock conditions:", 1
    )[1].split("\n\nHosted demo status:", 1)[0]
