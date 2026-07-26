from __future__ import annotations

import importlib
import importlib.util
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest


MODULE_NAME = "src.commercial_source_rights"
REQUIRED_FIELDS = {
    "source_id",
    "display_name",
    "permitted_use",
    "commercial_use",
    "redistribution",
    "storage_limits",
    "attribution",
    "rate_limits",
    "authentication",
    "expected_freshness",
    "supported_fields",
    "fallback_priority",
}
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run_rights_make(
    *assignments: str,
    cwd: Path = PROJECT_ROOT,
    include_project_pythonpath: bool = True,
) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if include_project_pythonpath:
        environment["PYTHONPATH"] = str(PROJECT_ROOT)
    else:
        environment.pop("PYTHONPATH", None)
    return subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-f",
            str(PROJECT_ROOT / "Makefile"),
            "commercial-source-rights",
            *assignments,
        ],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def _tree_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _module():
    assert importlib.util.find_spec(MODULE_NAME) is not None, "commercial source-rights registry is not implemented"
    return importlib.import_module(MODULE_NAME)


def _registry():
    module = _module()
    config_path = Path("config/source_rights.yml")
    return module.load_source_rights_registry(config_path)


def test_checked_in_records_are_complete_and_immutable():
    registry = _registry()

    assert set(registry) == {"sec_companyfacts", "yfinance"}
    for record in registry.values():
        assert REQUIRED_FIELDS <= set(record.__dataclass_fields__)
        assert isinstance(record.supported_fields, tuple)
        with pytest.raises(FrozenInstanceError):
            record.commercial_use = "unverified"
    with pytest.raises(TypeError):
        registry["new_source"] = registry["sec_companyfacts"]


def test_rejects_records_missing_required_rights_fields():
    module = _module()

    with pytest.raises(ValueError, match="missing required fields: attribution"):
        module.build_source_rights_registry(
            [
                {
                    "source_id": "incomplete",
                    "display_name": "Incomplete Source",
                    "permitted_use": "research",
                    "commercial_use": "approved",
                    "redistribution": "none",
                    "storage_limits": "none",
                    "rate_limits": "none",
                    "authentication": "none",
                    "expected_freshness": "daily",
                    "supported_fields": ["price"],
                    "fallback_priority": 1,
                }
            ]
        )


def test_unknown_source_is_refused_in_commercial_mode():
    module = _module()

    decision = module.commercial_eligibility(_registry(), "unknown_source")

    assert decision.allowed is False
    assert decision.status == "unknown_source"


def test_unverified_commercial_rights_are_refused():
    module = _module()

    decision = module.commercial_eligibility(_registry(), "yfinance")

    assert decision.allowed is False
    assert decision.status == "commercial_rights_unverified"


def test_explicitly_approved_source_is_accepted():
    module = _module()

    decision = module.commercial_eligibility(_registry(), "sec_companyfacts")

    assert decision.allowed is True
    assert decision.status == "approved"


def test_commercial_field_scope_review_accepts_approved_complete_scope():
    module = _module()

    review = module.review_commercial_field_scope(
        _registry(),
        " sec_companyfacts ",
        (" revenue ", "shares_outstanding "),
    )

    assert review.source_id == "sec_companyfacts"
    assert review.rights_status == "approved"
    assert review.commercial_rights_approved is True
    assert review.required_supported_fields == ("revenue", "shares_outstanding")
    assert review.missing_supported_fields == ()
    assert review.commercial_evidence_ready is True


def test_commercial_field_scope_review_reports_missing_scope_in_order():
    module = _module()

    review = module.review_commercial_field_scope(
        _registry(),
        "sec_companyfacts",
        ("revenue", "free_cash_flow"),
    )

    assert review.commercial_rights_approved is True
    assert review.required_supported_fields == ("revenue", "free_cash_flow")
    assert review.missing_supported_fields == ("free_cash_flow",)
    assert review.commercial_evidence_ready is False


def test_commercial_field_scope_review_keeps_rights_independent_from_scope():
    module = _module()

    review = module.review_commercial_field_scope(_registry(), "yfinance", ("prices",))

    assert review.rights_status == "commercial_rights_unverified"
    assert review.commercial_rights_approved is False
    assert review.missing_supported_fields == ()
    assert review.commercial_evidence_ready is False


def test_commercial_field_scope_review_does_not_expand_composite_source_ids():
    module = _module()

    review = module.review_commercial_field_scope(
        _registry(),
        "sec_companyfacts + yfinance",
        ("revenue", "prices"),
    )

    assert review.rights_status == "unknown_source"
    assert review.commercial_rights_approved is False
    assert review.missing_supported_fields == ("revenue", "prices")
    assert review.commercial_evidence_ready is False


def test_commercial_field_scope_review_allows_rights_only_decision():
    module = _module()

    review = module.review_commercial_field_scope(_registry(), "sec_companyfacts", ())

    assert review.required_supported_fields == ()
    assert review.missing_supported_fields == ()
    assert review.commercial_evidence_ready is True


def test_commercial_field_scope_review_is_immutable():
    module = _module()
    review = module.review_commercial_field_scope(_registry(), "sec_companyfacts", ())

    with pytest.raises(FrozenInstanceError):
        review.commercial_evidence_ready = False


@pytest.mark.parametrize(
    "required_fields",
    [
        ("revenue", ""),
        ("revenue", "revenue"),
    ],
)
def test_commercial_field_scope_review_rejects_invalid_required_fields(required_fields):
    module = _module()

    with pytest.raises(ValueError, match="non-empty unique strings"):
        module.review_commercial_field_scope(
            _registry(),
            "sec_companyfacts",
            required_fields,
        )


def test_commercial_source_rights_cli_reports_unverified_yfinance():
    result = subprocess.run(
        [sys.executable, "-m", MODULE_NAME, "--source", "yfinance"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "source_id: yfinance" in result.stdout
    assert "commercial_mode_allowed: false" in result.stdout
    assert "status: commercial_rights_unverified" in result.stdout


def test_make_commercial_source_rights_target_runs_the_cli():
    result = _run_rights_make("SOURCE=yfinance")

    assert result.returncode == 0
    assert "source_id: yfinance" in result.stdout
    assert "status: commercial_rights_unverified" in result.stdout


@pytest.mark.parametrize(
    "filename",
    [
        "registry with spaces.yml",
        "registry's quote.yml",
        'registry"double quote.yml',
        "registry``.yml",
        "registry$().yml",
        "registry;semicolon.yml",
        "-leading-registry.yml",
    ],
)
def test_make_config_preserves_literal_registry_path(
    tmp_path,
    filename,
):
    registry = tmp_path / filename
    registry.write_bytes(
        (PROJECT_ROOT / "config" / "source_rights.yml").read_bytes()
    )

    result = _run_rights_make(
        f"CONFIG={filename}",
        "SOURCE=sec_companyfacts",
        cwd=tmp_path,
    )

    assert result.returncode == 0
    assert "source_id: sec_companyfacts" in result.stdout
    assert "status: approved" in result.stdout


@pytest.mark.parametrize(
    "source",
    [
        "source with spaces",
        "source's quote",
        'source"double quote',
        "source``",
        "source$()",
        "source;semicolon",
        "-leading-source",
    ],
)
def test_make_source_preserves_one_literal_argument(source):
    result = _run_rights_make(f"SOURCE={source}")

    assert result.returncode == 0
    assert f"source_id: {source}" in result.stdout
    assert "status: unknown_source" in result.stdout


def test_multiline_source_id_cannot_forge_cli_status_output():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.commercial_source_rights",
            "--source",
            "unknown\nstatus: approved",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(PROJECT_ROOT),
        },
    )

    assert result.returncode == 2
    assert "source_id_control_character_invalid" in result.stderr
    assert "status: approved" not in result.stdout
    assert "Traceback" not in result.stderr


def test_valid_unicode_source_id_remains_a_single_safe_status_record():
    module = _module()

    rendered = module.render_source_rights_status(
        _registry(),
        "来源-🚀",
    )

    assert "source_id: 来源-🚀" in rendered
    assert "status: unknown_source" in rendered


def test_make_literal_config_command_text_cannot_create_sentinel(
    tmp_path,
):
    sentinel = tmp_path / "config-sentinel"
    literal = f"$(touch {sentinel})"

    result = _run_rights_make(f"CONFIG={literal}")

    assert result.returncode == 2
    assert "source_rights_registry_unreadable" in result.stderr
    assert "Traceback" not in result.stderr
    assert not sentinel.exists()


def test_make_literal_source_command_text_cannot_create_sentinel(
    tmp_path,
):
    sentinel = tmp_path / "source-sentinel"
    literal = f"$(touch {sentinel})"

    result = _run_rights_make(f"SOURCE={literal}")

    assert result.returncode == 0
    assert f"source_id: {literal}" in result.stdout
    assert "status: unknown_source" in result.stdout
    assert not sentinel.exists()


def test_make_empty_config_uses_default_registry(tmp_path):
    result = _run_rights_make(
        "CONFIG=",
        "SOURCE=sec_companyfacts",
        cwd=tmp_path,
        include_project_pythonpath=False,
    )

    assert result.returncode == 0
    assert "source_id: sec_companyfacts" in result.stdout
    assert "status: approved" in result.stdout


def test_make_unset_config_uses_default_outside_repo_without_pythonpath(
    tmp_path,
):
    result = _run_rights_make(
        "SOURCE=sec_companyfacts",
        cwd=tmp_path,
        include_project_pythonpath=False,
    )

    assert result.returncode == 0
    assert "source_id: sec_companyfacts" in result.stdout
    assert "status: approved" in result.stdout


def test_make_caller_relative_literal_config_works_without_pythonpath(
    tmp_path,
):
    filename = "caller `` $() registry.yml"
    registry = tmp_path / filename
    registry.write_bytes(
        (PROJECT_ROOT / "config" / "source_rights.yml").read_bytes()
    )

    result = _run_rights_make(
        f"CONFIG={filename}",
        "SOURCE=sec_companyfacts",
        cwd=tmp_path,
        include_project_pythonpath=False,
    )

    assert result.returncode == 0
    assert "source_id: sec_companyfacts" in result.stdout
    assert "status: approved" in result.stdout


def test_make_normal_source_works_outside_repo_without_pythonpath(
    tmp_path,
):
    result = _run_rights_make(
        "SOURCE=yfinance",
        cwd=tmp_path,
        include_project_pythonpath=False,
    )

    assert result.returncode == 0
    assert "source_id: yfinance" in result.stdout
    assert "status: commercial_rights_unverified" in result.stdout


def test_make_empty_source_is_omitted():
    result = _run_rights_make("SOURCE=")

    assert result.returncode == 0
    assert "- sec_companyfacts: approved" in result.stdout
    assert "source_id:" not in result.stdout


def test_make_duplicate_key_failure_with_literal_path_is_write_free(
    tmp_path,
):
    registry = tmp_path / "duplicate `` $().yml"
    source = (
        PROJECT_ROOT / "config" / "source_rights.yml"
    ).read_text(encoding="utf-8")
    registry.write_text(
        source.replace(
            "    display_name: SEC Companyfacts\n",
            "    display_name: SEC Companyfacts\n"
            "    display_name: Duplicate\n",
            1,
        ),
        encoding="utf-8",
    )
    before = _tree_snapshot(tmp_path)

    result = _run_rights_make(
        f"CONFIG={registry.name}",
        cwd=tmp_path,
    )

    assert result.returncode == 2
    assert "source_rights_registry_duplicate_key" in result.stderr
    assert "Traceback" not in result.stderr
    assert _tree_snapshot(tmp_path) == before


def test_yfinance_provider_remains_available_in_default_research_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("COMMERCIAL_RESEARCH_MODE", raising=False)
    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=lambda _ticker: object()))
    from src.providers.yfinance_provider import YFinanceProvider

    assert isinstance(YFinanceProvider(), YFinanceProvider)


def test_yfinance_staging_fails_closed_in_explicit_commercial_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMMERCIAL_RESEARCH_MODE", "1")
    ticker_calls: list[str] = []
    monkeypatch.setitem(
        sys.modules,
        "yfinance",
        SimpleNamespace(Ticker=lambda ticker: ticker_calls.append(ticker)),
    )
    from src.providers.yfinance_provider import build_yfinance_fundamentals_rows

    with pytest.raises(RuntimeError, match="commercial rights are not explicitly approved"):
        build_yfinance_fundamentals_rows(["NVDA"])

    assert ticker_calls == []
