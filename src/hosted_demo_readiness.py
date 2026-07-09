from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from src.paths import resolve_project_root


@dataclass(frozen=True)
class HostedDemoCheck:
    name: str
    status: str
    detail: str
    command: str
    boundary: str


REQUIRED_RUNTIME_PACKAGES = ("streamlit", "pandas", "numpy", "PyYAML")
OPTIONAL_SECRET_NAMES = ("FMP_API_KEY", "ALPHA_VANTAGE_API_KEY", "FINNHUB_API_KEY")
OPTIONAL_STREAMLIT_SECRET_NAMES = OPTIONAL_SECRET_NAMES + ("IBKR_HOST", "IBKR_PORT", "IBKR_CLIENT_ID")
HOSTED_DEMO_ENV_FILE = "config/hosted_demo.env"
HOSTED_DEMO_EXAMPLE_FILE = "config/hosted_demo.env.example"
HOSTED_DEMO_URL_NAME = "HOSTED_DEMO_URL"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _package_present(requirements: str, package: str) -> bool:
    return any(
        line.strip().lower().startswith(package.lower())
        for line in requirements.splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def _read_simple_env_value(body: str, name: str) -> str:
    prefix = f"{name}="
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or not line.startswith(prefix):
            continue
        value = line[len(prefix) :].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        return value.strip()
    return ""


def _hosted_public_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    return base if "?" in base else f"{base}/?mode=public"


def read_hosted_demo_url(root: Path | str | None = None) -> str:
    env_value = os.getenv(HOSTED_DEMO_URL_NAME, "").strip()
    if env_value:
        return env_value
    project_root = resolve_project_root(Path(root or "."))
    hosted_env_path = project_root / HOSTED_DEMO_ENV_FILE
    hosted_env_body = _read_text(hosted_env_path)
    return _read_simple_env_value(hosted_env_body, HOSTED_DEMO_URL_NAME)


def build_hosted_demo_readiness(root: Path | str | None = None) -> list[HostedDemoCheck]:
    project_root = resolve_project_root(Path(root or "."))
    dashboard_path = project_root / "dashboard.py"
    requirements_path = project_root / "requirements.txt"
    hosted_doc_path = project_root / "docs" / "HOSTED_DEMO_DEPLOYMENT.md"
    secrets_template_path = project_root / ".streamlit" / "secrets.toml.example"
    hosted_env_example_path = project_root / HOSTED_DEMO_EXAMPLE_FILE

    dashboard_body = _read_text(dashboard_path)
    requirements_body = _read_text(requirements_path)
    hosted_doc_body = _read_text(hosted_doc_path)
    secrets_template_body = _read_text(secrets_template_path)
    hosted_env_example_body = _read_text(hosted_env_example_path)
    configured_hosted_url = read_hosted_demo_url(project_root)

    entrypoint_ready = dashboard_path.exists() and "src.dashboard" in dashboard_body
    missing_packages = [
        package
        for package in REQUIRED_RUNTIME_PACKAGES
        if not _package_present(requirements_body, package)
    ]
    requirements_ready = requirements_path.exists() and not missing_packages
    hosted_doc_ready = hosted_doc_path.exists() and "No public hosted Streamlit URL is configured" in hosted_doc_body
    missing_secret_names = [
        name for name in OPTIONAL_STREAMLIT_SECRET_NAMES if name not in secrets_template_body
    ]
    secrets_template_ready = secrets_template_path.exists() and not missing_secret_names
    hosted_url_template_ready = (
        hosted_env_example_path.exists() and HOSTED_DEMO_URL_NAME in hosted_env_example_body
    )
    hosted_url_status = "manual_verify_required" if configured_hosted_url else "external_account_required"
    hosted_url_detail = (
        "Configured hosted URL still needs the five-page public workflow check before public copy changes: "
        f"{configured_hosted_url}"
        if configured_hosted_url
        else "No public hosted Streamlit URL is configured in this repository; local public mode is "
        "http://localhost:8501/?mode=public."
    )
    hosted_url_command = (
        f"open {_hosted_public_url(configured_hosted_url)}"
        if configured_hosted_url
        else "make dashboard"
    )

    return [
        HostedDemoCheck(
            name="Streamlit entrypoint",
            status="ready" if entrypoint_ready else "missing",
            detail=(
                "Use root dashboard.py as the hosted Streamlit entrypoint."
                if entrypoint_ready
                else "Root dashboard.py must wrap src.dashboard before hosting."
            ),
            command="streamlit run dashboard.py --server.headless true",
            boundary="Hosted entrypoint only; it does not refresh data or unlock blocked inputs.",
        ),
        HostedDemoCheck(
            name="Runtime dependency manifest",
            status="ready" if requirements_ready else "missing",
            detail=(
                "requirements.txt contains the hosted baseline runtime packages."
                if requirements_ready
                else f"requirements.txt is missing: {', '.join(missing_packages) or 'runtime package list'}"
            ),
            command="pip install -r requirements.txt",
            boundary="Provider extras and broker-style packages stay out of the hosted baseline.",
        ),
        HostedDemoCheck(
            name="Deployment guide",
            status="ready" if hosted_doc_ready else "missing",
            detail=(
                "docs/HOSTED_DEMO_DEPLOYMENT.md names the external account and verification boundary."
                if hosted_doc_ready
                else "Add or refresh docs/HOSTED_DEMO_DEPLOYMENT.md before publishing a hosted URL."
            ),
            command="open docs/HOSTED_DEMO_DEPLOYMENT.md",
            boundary="Documentation only; it is not proof that a hosted URL exists.",
        ),
        HostedDemoCheck(
            name="Hosted secrets template",
            status="ready" if secrets_template_ready else "missing",
            detail=(
                "Blank .streamlit/secrets.toml.example lists optional hosted secret names only."
                if secrets_template_ready
                else "Add .streamlit/secrets.toml.example with blank hosted secret names: "
                f"{', '.join(missing_secret_names) or 'template file'}"
            ),
            command="copy names from .streamlit/secrets.toml.example into the hosting platform secrets UI",
            boundary="Template only; never commit .streamlit/secrets.toml, real keys, tokens, account IDs, or broker sessions.",
        ),
        HostedDemoCheck(
            name="Hosted URL config template",
            status="ready" if hosted_url_template_ready else "missing",
            detail=(
                f"Blank {HOSTED_DEMO_EXAMPLE_FILE} documents {HOSTED_DEMO_URL_NAME} for later deployment handoff."
                if hosted_url_template_ready
                else f"Add {HOSTED_DEMO_EXAMPLE_FILE} with blank {HOSTED_DEMO_URL_NAME}."
            ),
            command=f"copy {HOSTED_DEMO_EXAMPLE_FILE} to {HOSTED_DEMO_ENV_FILE} only after a hosted URL exists",
            boundary=(
                "Template only; a URL marker is not proof until the hosted app opens and the public workflow is verified."
            ),
        ),
        HostedDemoCheck(
            name="Hosted URL",
            status=hosted_url_status,
            detail=hosted_url_detail,
            command=hosted_url_command,
            boundary="do not claim hosted availability until a public URL is opened and verified.",
        ),
        HostedDemoCheck(
            name="Secrets boundary",
            status="manual_gate",
            detail=(
                "Optional provider keys belong in the hosting platform secrets UI or ignored local files: "
                f"{', '.join(OPTIONAL_SECRET_NAMES)}."
            ),
            command="make provider-setup-checklist",
            boundary="Never commit provider keys, account identifiers, tokens, or broker/session files.",
        ),
        HostedDemoCheck(
            name="Public verification",
            status="manual_gate",
            detail=(
                "Run public gates after hosting-specific changes; screenshots are product evidence only "
                "and not data freshness proof."
            ),
            command="make public-check && make browser-qa-evidence",
            boundary=(
                "Research-only: not investment advice, no broker trading, no order routing, "
                "no auto-trading, and no direct buy/sell instructions."
            ),
        ),
    ]


def render_hosted_demo_readiness(checks: list[HostedDemoCheck]) -> str:
    lines = [
        "Hosted Demo Readiness",
        "Read-only: this command does not deploy, open accounts, print secrets, refresh data, stage files, commit, or push.",
        "",
    ]
    for check in checks:
        lines.extend(
            [
                f"- {check.name}: {check.status}",
                f"  detail: {check.detail}",
                f"  command: {check.command}",
                f"  boundary: {check.boundary}",
            ]
        )
    lines.extend(
        [
            "",
            "Next safe hosted-demo step:",
            "- If all repo-side checks are ready, choose an external Streamlit host/account and follow docs/HOSTED_DEMO_DEPLOYMENT.md.",
            "- Keep GitHub as the public link until the hosted URL opens successfully and public gates pass.",
            "",
            "Hosted link decision ladder:",
            "- No hosted URL: use the GitHub repository link and local make dashboard workflow.",
            "- Hosted URL configured: open the public route, verify the five-page workflow, then rerun public gates before changing README or LinkedIn copy.",
            "- Hosted URL opens: verify the five-page public workflow, then rerun make public-check and make browser-qa-evidence.",
            "- Provider keys added: run make provider-setup-checklist and one reviewed provider smoke; setup alone does not prove coverage.",
            "- Hosted route changes copy or layout: keep the GitHub link until the public path and research-only gates are rechecked.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Print hosted demo readiness without deploying.")
    parser.add_argument("--root", default=".", help="Project root")
    args = parser.parse_args()

    root = resolve_project_root(Path(args.root))
    print(render_hosted_demo_readiness(build_hosted_demo_readiness(root)))


if __name__ == "__main__":
    main()
