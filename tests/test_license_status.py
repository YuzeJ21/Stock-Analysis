from pathlib import Path

from src.license_status import NO_LICENSE_SHARE_BOUNDARY, build_license_status, render_license_status


def test_build_license_status_without_root_license_keeps_portfolio_demo_boundary(tmp_path: Path):
    (tmp_path / "README.md").write_text(
        "Reuse rights are not granted until a license is added.\n",
        encoding="utf-8",
    )

    status = build_license_status(tmp_path)

    assert status["license_present"] is False
    assert status["share_status"] == "portfolio_demo_only"
    assert status["next_decision"] == "choose_license_before_open_source_claim"
    assert status["safe_to_share_boundary"] == NO_LICENSE_SHARE_BOUNDARY
    assert status["next_safe_command"] == "docs/LICENSE_DECISION_GUIDE.md"
    assert status["decision_options"] == [
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


def test_render_license_status_names_owner_decision_and_stop_rule(tmp_path: Path):
    (tmp_path / "README.md").write_text(
        "Reuse rights are not granted until a license is added.\n",
        encoding="utf-8",
    )

    rendered = render_license_status(build_license_status(tmp_path))

    assert "License Status" in rendered
    assert "share_status: portfolio_demo_only" in rendered
    assert "next_decision: choose_license_before_open_source_claim" in rendered
    assert "next_safe_command: docs/LICENSE_DECISION_GUIDE.md" in rendered
    assert "Decision options:" in rendered
    assert "- Portfolio showcase only | Keep no license for now | Visitors can read the code, but reuse rights are not granted." in rendered
    assert "- Let others reuse with attribution | Add MIT or Apache-2.0 | Visitors can reuse under the selected license terms." in rendered
    assert "- Keep stronger control | Add a custom or proprietary notice | Visitors should ask before reuse; use legal review for custom wording." in rendered
    assert "Do not claim open-source or reuse rights until a root LICENSE is selected" in rendered
    assert "Product screenshots and demo evidence may be shared as portfolio context only" in rendered
    assert "do not grant copying, redistribution, adaptation, or software reuse rights" in rendered
