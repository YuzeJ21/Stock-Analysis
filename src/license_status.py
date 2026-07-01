"""Read-only license status surface for pilot/share packaging."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_license_status(root: Path) -> dict[str, object]:
    license_path = root / "LICENSE"
    has_license = license_path.exists()
    if has_license:
        share_status = "license_present"
        next_decision = "confirm_readme_license_wording"
        boundary = "Root LICENSE is present; confirm README wording matches the selected license."
        stop_rule = "Stop if README License wording conflicts with the selected license."
    else:
        share_status = "portfolio_demo_only"
        next_decision = "choose_license_before_open_source_claim"
        boundary = "Share as portfolio/demo only; do not describe as open source or grant reuse rights."
        stop_rule = "Do not claim open-source or reuse rights until a root LICENSE is selected."
    return {
        "license_present": has_license,
        "share_status": share_status,
        "next_decision": next_decision,
        "safe_to_share_boundary": boundary,
        "next_safe_command": "docs/LICENSE_DECISION_GUIDE.md",
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
        f"safe_to_share_boundary: {status.get('safe_to_share_boundary')}",
        f"next_safe_command: {status.get('next_safe_command')}",
        f"stop_rule: {status.get('stop_rule')}",
        f"research_boundary: {status.get('research_boundary')}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print the read-only license status gate.")
    parser.add_argument("--root", default=".", help="Repository root.")
    args = parser.parse_args(argv)
    print(render_license_status(build_license_status(Path(args.root))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
