from pathlib import Path

from src.browser_qa_evidence import (
    BrowserQaEvidence,
    browser_qa_evidence_rows,
    browser_qa_evidence_verdict,
    image_size,
    main,
)


def _write_png(path: Path, width: int = 1200, height: int = 627) -> None:
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )


def _write_jpeg(path: Path, width: int = 1280, height: int = 720) -> None:
    path.write_bytes(
        b"\xff\xd8"
        b"\xff\xe0\x00\x04\x00\x00"
        b"\xff\xc0\x00\x11\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
        b"\xff\xd9"
    )


def test_image_size_reads_png_and_jpeg_dimensions(tmp_path):
    png = tmp_path / "asset.png"
    jpg = tmp_path / "asset.jpg"
    _write_png(png, width=1200, height=627)
    _write_jpeg(jpg, width=1280, height=720)

    assert image_size(png) == (1200, 627)
    assert image_size(jpg) == (1280, 720)


def test_browser_qa_evidence_rows_keep_routes_assets_and_boundaries_visible(tmp_path):
    asset = tmp_path / "docs" / "assets" / "linkedin-public-dashboard.png"
    asset.parent.mkdir(parents=True)
    _write_png(asset, width=1200, height=627)
    evidence = (
        BrowserQaEvidence(
            name="Public dashboard",
            path=Path("docs/assets/linkedin-public-dashboard.png"),
            route="http://localhost:8501/?mode=public",
            expected_markers=("research-loop-strip", "Public visitor mode"),
            min_width=1200,
            min_height=600,
            use="LinkedIn thumbnail.",
        ),
    )

    rows = browser_qa_evidence_rows(tmp_path, evidence)
    rendered = " ".join(str(value) for row in rows for value in row.values()).lower()

    assert rows[0]["State"] == "ready"
    assert rows[0]["Dimensions"].startswith("1200x627")
    assert "localhost:8501/?mode=public" in rendered
    assert "research-loop-strip" in rendered
    assert "linkedin thumbnail" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_browser_qa_evidence_verdict_blocks_missing_or_small_assets(tmp_path):
    asset = tmp_path / "docs" / "assets" / "small.png"
    asset.parent.mkdir(parents=True)
    _write_png(asset, width=400, height=300)
    evidence = (
        BrowserQaEvidence(
            name="Small asset",
            path=Path("docs/assets/small.png"),
            route="http://localhost:8501/?mode=public",
            expected_markers=("Public visitor mode",),
            min_width=1200,
            min_height=600,
            use="Too small for public evidence.",
        ),
        BrowserQaEvidence(
            name="Missing asset",
            path=Path("docs/assets/missing.png"),
            route="http://localhost:8501/?mode=operator&page=data-health",
            expected_markers=("Operator Queue",),
            min_width=1000,
            min_height=600,
            use="Missing evidence.",
        ),
    )

    rows = browser_qa_evidence_rows(tmp_path, evidence)

    assert [row["State"] for row in rows] == ["blocked", "blocked"]
    assert browser_qa_evidence_verdict(rows) == "blocked"


def test_browser_qa_evidence_cli_is_read_only_and_research_safe(tmp_path, capsys):
    asset = tmp_path / "docs" / "assets" / "linkedin-public-dashboard.png"
    asset.parent.mkdir(parents=True)
    _write_png(asset, width=1200, height=627)

    exit_code = main(["--root", str(tmp_path)])
    output = capsys.readouterr().out.lower()

    assert exit_code == 0
    assert "read-only" in output
    assert "real streamlit screenshots" in output
    assert "does not unlock fundamentals" in output
    assert "investment advice" in output
    assert "trade instructions" in output
    assert "buy" not in output
    assert "sell" not in output
