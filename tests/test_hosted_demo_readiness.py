from pathlib import Path

from src.hosted_demo_readiness import build_hosted_demo_readiness, render_hosted_demo_readiness


def test_hosted_demo_readiness_reports_deployable_package_and_external_blocker(tmp_path: Path):
    (tmp_path / "dashboard.py").write_text("from src.dashboard import main\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text(
        "streamlit>=1.44\npandas>=2.2\nnumpy>=1.26\nPyYAML>=6.0\n",
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "HOSTED_DEMO_DEPLOYMENT.md").write_text(
        "# Hosted Demo Deployment\nNo public hosted Streamlit URL is configured in this repository.\n",
        encoding="utf-8",
    )
    (tmp_path / ".streamlit").mkdir()
    (tmp_path / ".streamlit" / "secrets.toml.example").write_text(
        'FMP_API_KEY = ""\n'
        'ALPHA_VANTAGE_API_KEY = ""\n'
        'FINNHUB_API_KEY = ""\n'
        'IBKR_HOST = ""\n'
        'IBKR_PORT = ""\n'
        'IBKR_CLIENT_ID = ""\n',
        encoding="utf-8",
    )

    checks = build_hosted_demo_readiness(tmp_path)
    by_name = {check.name: check for check in checks}
    rendered = render_hosted_demo_readiness(checks)

    assert by_name["Streamlit entrypoint"].status == "ready"
    assert by_name["Runtime dependency manifest"].status == "ready"
    assert by_name["Hosted secrets template"].status == "ready"
    assert by_name["Hosted URL"].status == "external_account_required"
    assert by_name["Secrets boundary"].status == "manual_gate"
    assert by_name["Public verification"].command == "make public-check && make browser-qa-evidence"

    assert "dashboard.py" in rendered
    assert "requirements.txt" in rendered
    assert ".streamlit/secrets.toml.example" in rendered
    assert "http://localhost:8501/?mode=public" in rendered
    assert "external_account_required" in rendered
    assert "never commit .streamlit/secrets.toml" in rendered
    assert "screenshots are product evidence only" in rendered.lower()
    assert "not investment advice" in rendered.lower()
    assert "FMP_API_KEY" in rendered
    assert "do not claim hosted availability until a public URL is opened and verified" in rendered
    assert "Hosted link decision ladder" in rendered
    assert "No hosted URL: use the GitHub repository link and local make dashboard workflow." in rendered
    assert "Hosted URL opens: verify the five-page public workflow, then rerun make public-check and make browser-qa-evidence." in rendered
    assert "Provider keys added: run make provider-setup-checklist and one reviewed provider smoke; setup alone does not prove coverage." in rendered
    assert "Hosted route changes copy or layout: keep the GitHub link until the public path and research-only gates are rechecked." in rendered


def test_hosted_demo_readiness_reports_configured_url_as_manual_verification_gate(tmp_path: Path):
    (tmp_path / "dashboard.py").write_text("from src.dashboard import main\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text(
        "streamlit>=1.44\npandas>=2.2\nnumpy>=1.26\nPyYAML>=6.0\n",
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "HOSTED_DEMO_DEPLOYMENT.md").write_text(
        "# Hosted Demo Deployment\nNo public hosted Streamlit URL is configured in this repository.\n",
        encoding="utf-8",
    )
    (tmp_path / ".streamlit").mkdir()
    (tmp_path / ".streamlit" / "secrets.toml.example").write_text(
        'FMP_API_KEY = ""\n'
        'ALPHA_VANTAGE_API_KEY = ""\n'
        'FINNHUB_API_KEY = ""\n'
        'IBKR_HOST = ""\n'
        'IBKR_PORT = ""\n'
        'IBKR_CLIENT_ID = ""\n',
        encoding="utf-8",
    )
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "hosted_demo.env").write_text(
        'HOSTED_DEMO_URL="https://example-stock-demo.streamlit.app"\n',
        encoding="utf-8",
    )

    checks = build_hosted_demo_readiness(tmp_path)
    by_name = {check.name: check for check in checks}
    rendered = render_hosted_demo_readiness(checks)

    assert by_name["Hosted URL"].status == "manual_verify_required"
    assert "https://example-stock-demo.streamlit.app" in by_name["Hosted URL"].detail
    assert by_name["Hosted URL"].command == "open https://example-stock-demo.streamlit.app/?mode=public"
    assert "manual_verify_required" in rendered
    assert "Configured hosted URL still needs the five-page public workflow check" in rendered
