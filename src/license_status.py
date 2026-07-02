"""Read-only license status surface for pilot/share packaging."""

from __future__ import annotations

import argparse
from pathlib import Path


DECISION_OPTIONS = [
    {
        "goal": "Portfolio showcase only",
        "path": "Keep no license for now",
        "visitor_expectation": "Visitors can read the code, but reuse rights are not granted.",
    },
    {
        "goal": "Let others reuse with attribution",
        "path": "Add MIT or Apache-2.0",
        "visitor_expectation": "Visitors can reuse under the selected license terms.",
    },
    {
        "goal": "Keep stronger control",
        "path": "Add a custom or proprietary notice",
        "visitor_expectation": "Visitors should ask before reuse; use legal review for custom wording.",
    },
]

NO_LICENSE_SHARE_BOUNDARY = (
    "Share as portfolio/demo only; do not describe as open source or grant reuse rights. "
    "Product screenshots and demo evidence may be shared as portfolio context only; they do not grant "
    "copying, redistribution, adaptation, or software reuse rights."
)


def build_license_status(root: Path) -> dict[str, object]:
    license_path = root / "LICENSE"
    has_license = license_path.exists()
    if has_license:
        share_status = "license_present"
        next_decision = "confirm_readme_license_wording"
        owner_decision_required = False
        boundary = "Root LICENSE is present; confirm README wording matches the selected license."
        stop_rule = "Stop if README License wording conflicts with the selected license."
    else:
        share_status = "portfolio_demo_only"
        next_decision = "choose_license_before_open_source_claim"
        owner_decision_required = True
        boundary = NO_LICENSE_SHARE_BOUNDARY
        stop_rule = "Do not claim open-source or reuse rights until a root LICENSE is selected."
    return {
        "license_present": has_license,
        "share_status": share_status,
        "next_decision": next_decision,
        "owner_decision_required": owner_decision_required,
        "safe_to_share_boundary": boundary,
        "next_safe_command": "docs/LICENSE_DECISION_GUIDE.md",
        "decision_options": DECISION_OPTIONS,
        "stop_rule": stop_rule,
        "research_boundary": (
            "License status is a sharing/reuse gate only; it does not refresh data, "
            "unlock blocked inputs, or change research readiness."
        ),
    }


def render_license_status(status: dict[str, object]) -> str:
    lines = [
        "License Status",
        "Read-only: this command does not add a license, rewrite docs, stage files, or grant reuse rights.",
        f"license_present: {str(status.get('license_present')).lower()}",
        f"share_status: {status.get('share_status')}",
        f"next_decision: {status.get('next_decision')}",
        f"owner_decision_required: {str(status.get('owner_decision_required')).lower()}",
        f"safe_to_share_boundary: {status.get('safe_to_share_boundary')}",
        f"next_safe_command: {status.get('next_safe_command')}",
        "Decision options:",
    ]
    decision_options = status.get("decision_options", [])
    if isinstance(decision_options, list):
        for option in decision_options:
            if not isinstance(option, dict):
                continue
            lines.append(
                "- "
                f"{option.get('goal')} | "
                f"{option.get('path')} | "
                f"{option.get('visitor_expectation')}"
            )
    lines.extend([
        f"stop_rule: {status.get('stop_rule')}",
        f"research_boundary: {status.get('research_boundary')}",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print the read-only license status gate.")
    parser.add_argument("--root", default=".", help="Repository root.")
    args = parser.parse_args(argv)
    print(render_license_status(build_license_status(Path(args.root))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
