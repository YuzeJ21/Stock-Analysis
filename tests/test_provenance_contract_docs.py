from pathlib import Path


def test_provenance_contract_defines_required_metric_and_profile_boundaries():
    body = Path("docs/PROVENANCE_CONTRACT.md").read_text(encoding="utf-8")

    for heading in (
        "## Record Contract",
        "## Lane Requirements",
        "## Freshness Rules",
        "## Method Versioning",
        "## Demo Boundary",
    ):
        assert heading in body
    for field in (
        "readiness_state",
        "source",
        "as_of_date",
        "retrieved_at",
        "method_version",
        "missing_inputs",
        "confidence_boundary",
    ):
        assert f"`{field}`" in body
    assert "candidate_context_only" in body
    assert "must not satisfy trusted-peer readiness" in body
    assert "not data-freshness proof" in body
