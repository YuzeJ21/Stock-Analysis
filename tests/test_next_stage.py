from src.next_stage import render_next_stage


def test_next_stage_uses_manual_verification_ladder_when_hosted_url_is_configured(
    monkeypatch,
):
    monkeypatch.setenv("HOSTED_DEMO_URL", "https://stock-demo.example.com")

    output = render_next_stage(".", top_n=1)

    assert "Hosted demo status: manual_verify_required" in output
    assert "https://stock-demo.example.com" in output
    assert "- If you have a hosted URL: open it, verify the five-page public workflow, then rerun public gates before changing public copy." in output
    assert "after choosing an external host/account" not in output
    assert "Hosted app gate: make hosted-demo-readiness" in output
    assert "Hosted URL is configured but still needs the five-page public workflow check" in output
    assert "Hosted demo is awaiting external setup" not in output


def test_next_stage_keeps_external_account_ladder_without_hosted_url(monkeypatch):
    monkeypatch.delenv("HOSTED_DEMO_URL", raising=False)

    output = render_next_stage(".", top_n=1)

    assert "Hosted demo status: external_account_required" in output
    assert "- If you want a hosted URL: make hosted-demo-readiness, then follow docs/HOSTED_DEMO_DEPLOYMENT.md after choosing an external host/account." in output
    assert "Hosted demo is awaiting external setup (underlying diagnostic: external_account_required)" in output
    assert "Roadmap continuation: continue_with_pending_dependencies" in output
