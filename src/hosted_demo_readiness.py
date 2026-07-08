from __future__ import annotations

import argparse
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


def build_hosted_demo_readiness(root: Path | str | None = None) -> list[HostedDemoCheck]:
    project_root = resolve_project_root(Path(root or "."))
    dashboard_path = project_root / "dashboard.py"
    requirements_path = project_root / "requirements.txt"
    hosted_doc_path = project_root / "docs" / "HOSTED_DEMO_DEPLOYMENT.md"

    dashboard_body = _read_text(dashboard_path)
    requirements_body = _read_text(requirements_path)
    hosted_doc_body = _read_text(hosted_doc_path)

    entrypoint_ready = dashboard_path.exists() and "src.dashboard" in dashboard_body
    missing_packages = [
        package
        for package in REQUIRED_RUNTIME_PACKAGES
        if not _package_present(requirements_body, package)
    ]
    requirements_ready = requirements_path.exists() and not missing_packages
    hosted_doc_ready = hosted_doc_path.exists() and "No public hosted Streamlit URL is configured" in hosted_doc_body

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
            name="Hosted URL",
            status="external_account_required",
            detail=(
                "No public hosted Streamlit URL is configured in this repository; local public mode is "
                "http://localhost:8501/?mode=public."
            ),
            command="make dashboard",
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
