from pathlib import Path
import csv


def test_trusted_peer_pilot_template_keeps_source_review_separate_from_imports():
    path = Path("docs/TRUSTED_PEER_PILOT_SOURCE_TEMPLATE.csv")
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))

    assert rows
    header = rows[0].keys()
    for column in (
        "ticker",
        "peer_ticker",
        "peer_group",
        "sector",
        "industry",
        "source_type",
        "source_title",
        "source",
        "source_accessed_date",
        "as_of_date",
        "relationship_rationale",
        "source_evidence_note",
        "reviewer",
        "review_date",
        "source_proof_status",
        "import_row_ready",
    ):
        assert column in header

    body = path.read_text(encoding="utf-8")
    assert "candidate_context_only" in body
    assert "do not import until source proof is reviewed" in body
    assert "copy only import-schema fields into the guard" in body


def test_peer_pilot_docs_route_template_through_writeback_guard():
    readme = Path("README.md").read_text(encoding="utf-8")
    runbook = Path("docs/PILOT_RUNBOOK.md").read_text(encoding="utf-8")

    for body in (readme, runbook):
        assert "docs/TRUSTED_PEER_PILOT_SOURCE_TEMPLATE.csv" in body
        assert "make peer-mapping-writeback-guard" in body
        assert "candidate_context_only" in body
        assert "source-backed" in body

    assert "guessed peers or file row counts do not become valuation" in readme
    assert "candidate context stays out of trusted proof" in readme
    assert "cp docs/TRUSTED_PEER_PILOT_SOURCE_TEMPLATE.csv /tmp/stock-command-center-trusted-peer-pilot.csv" in runbook
    assert "only source-backed relationships that pass `peer-mapping-writeback-guard`" in runbook
    assert "source_evidence_note" in runbook
    assert "review-only fields, not import columns" in runbook
    assert "do not bypass it by pasting the full review sheet into the import file" in runbook
