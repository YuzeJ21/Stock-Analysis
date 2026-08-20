import csv
import json
import os
import re
import subprocess
from pathlib import Path

import pytest


def _makefile_targets(makefile: str | None = None) -> set[str]:
    if makefile is None:
        makefile = Path("Makefile").read_text(encoding="utf-8")
    return set(re.findall(r"^([A-Za-z0-9_.-]+):(?:\s|$)", makefile, flags=re.MULTILINE))


def _tree_manifest(root: Path) -> dict[str, tuple[str, bytes | None]]:
    manifest = {".": ("directory", None)}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            manifest[relative] = ("symlink", os.readlink(path).encode())
        elif path.is_dir():
            manifest[relative] = ("directory", None)
        else:
            manifest[relative] = ("file", path.read_bytes())
    return manifest


def _make_target_block(makefile: str, target: str) -> str:
    match = re.search(
        rf"^{re.escape(target)}:(?P<body>.*?)(?=^[A-Za-z0-9_.-]+:(?:\s|$)|\Z)",
        makefile,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"missing Make target {target}"
    return match.group(0)


def _reachable_make_targets(makefile: str, initial: str) -> set[str]:
    reachable: set[str] = set()
    pending = [initial]
    known = _makefile_targets(makefile)
    while pending:
        target = pending.pop()
        if target in reachable:
            continue
        reachable.add(target)
        block = _make_target_block(makefile, target)
        header = block.splitlines()[0].split(":", 1)[1]
        referenced = {token for token in header.split() if token in known}
        for invocation in re.findall(r"\$\(MAKE\)([^\n]*)", block):
            referenced.update(
                token
                for token in re.findall(r"[A-Za-z0-9_.-]+", invocation)
                if token in known
            )
        for script_name in re.findall(r"\b(scripts/[A-Za-z0-9_.-]+)", block):
            script = Path(script_name).read_text(encoding="utf-8")
            for invocation in re.findall(r"\bmake\s+([^\n]+)", script):
                referenced.update(
                    token
                    for token in re.findall(r"[A-Za-z0-9_.-]+", invocation)
                    if token in known
                )
        pending.extend(sorted(referenced & known))
    return reachable


def test_readiness_release_make_requires_record_and_guard_inputs_without_writing(tmp_path: Path):
    makefile = Path("Makefile").resolve()
    before = _tree_manifest(tmp_path)

    record = subprocess.run(
        ["make", "--no-print-directory", "-f", str(makefile), "readiness-release-record"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    guard = subprocess.run(
        ["make", "--no-print-directory", "-f", str(makefile), "readiness-release-guard"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert record.returncode != 0
    assert "PREVIEW_RECEIPT is required" in record.stderr
    assert guard.returncode != 0
    assert "RECORD_ID is required" in guard.stderr
    assert _tree_manifest(tmp_path) == before


def test_readiness_release_review_make_is_json_and_write_free():
    from src.readiness_release_review import AXIS_NAMES, CANDIDATE_PATHS

    root = Path.cwd()
    before_files = {item.path: (root / item.path).read_bytes() for item in CANDIDATE_PATHS}
    before_status = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        check=True,
    ).stdout

    result = subprocess.run(
        ["make", "--no-print-directory", "readiness-release-review", "TOP_N=1", "JSON=1"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )

    after_files = {item.path: (root / item.path).read_bytes() for item in CANDIDATE_PATHS}
    after_status = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        check=True,
    ).stdout
    payload = json.loads(result.stdout)
    assert result.returncode == 0, result.stderr
    assert len(payload["preview_receipt"]) == 64
    changed_ticker_count = payload["working_to_proposed"]["changed_ticker_count"]
    assert isinstance(changed_ticker_count, int)
    assert changed_ticker_count >= 0
    assert [axis["name"] for axis in payload["axes"]] == list(AXIS_NAMES)
    assert after_files == before_files
    assert after_status == before_status


def test_make_reachability_tracks_every_target_on_recursive_multi_target_lines():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert {
        "verify",
        "test",
        "pipeline",
        "validate-data",
        "onboarding",
    } <= _reachable_make_targets(makefile, "verify")
    assert {
        "daily",
        "pipeline",
        "validate-data",
        "onboarding",
        "status-check",
    } <= _reachable_make_targets(makefile, "daily")


def test_default_and_public_workflow_graphs_cannot_reach_writer_targets():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    public_dependencies = {
        "diff-hygiene-summary",
        "staged-hygiene-check",
        "public-wording-check",
        "test",
        "demo-dashboard-smoke",
        "demo-dashboard-render-smoke",
        "browser-qa-evidence",
        "linkedin-share-check",
        "license-status",
        "demo",
    }
    forbidden_writer_targets = {
        "readiness-materialize",
        "readiness-snapshot",
        "price-refresh",
        "monthly",
        "track-record",
        "research-decisions",
        "project-status",
    }

    public_reachable = _reachable_make_targets(makefile, "public-check")
    assert public_dependencies <= public_reachable
    for initial in (
        "status",
        "pipeline",
        "onboarding",
        "daily",
        "dashboard-smoke",
        "test",
        "verify",
        "validate-all",
        "public-check",
    ):
        reachable = _reachable_make_targets(makefile, initial)
        assert not (reachable & forbidden_writer_targets), (
            initial,
            sorted(reachable & forbidden_writer_targets),
        )


def test_legacy_readiness_make_boundaries_fail_closed_without_writing(tmp_path: Path):
    makefile = Path("Makefile").resolve()
    before = _tree_manifest(tmp_path)

    guard = subprocess.run(
        ["make", "-f", str(makefile), "readiness"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    missing_profile = subprocess.run(
        ["make", "-f", str(makefile), "readiness-materialize"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    missing_confirmation = subprocess.run(
        ["make", "-f", str(makefile), "readiness-materialize", "PROFILE=default"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    missing_snapshot_profile = subprocess.run(
        ["make", "-f", str(makefile), "readiness-snapshot"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert guard.returncode == 2
    assert "deprecated" in guard.stderr.lower()
    assert "make readiness-preview TOP_N=20" in guard.stderr
    assert "CONFIRM_MATERIALIZE=1 make readiness-materialize PROFILE=" in guard.stderr
    assert missing_profile.returncode == 2
    assert "PROFILE is required" in missing_profile.stderr
    assert missing_confirmation.returncode == 2
    assert "CONFIRM_MATERIALIZE=1 is required" in missing_confirmation.stderr
    assert missing_snapshot_profile.returncode == 2
    assert "PROFILE is required" in missing_snapshot_profile.stderr
    assert _tree_manifest(tmp_path) == before


def test_trusted_data_pilot_walkthrough_uses_profile_bound_before_apply_compare_proof():
    result = subprocess.run(
        ["make", "trusted-data-pilot", "PROFILE=local", "TICKERS=NVDA"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "make readiness\n" not in result.stdout
    assert "make readiness &&" not in result.stdout
    assert result.stdout.count("make readiness-snapshot PROFILE=local") >= 2
    for lane in ("prices", "fundamentals", "peers"):
        comparison = (
            f"make reviewed-batch-compare PROFILE=local LANE={lane} "
            "BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>"
        )
        assert comparison in result.stdout
    snapshot_at = result.stdout.index("make readiness-snapshot PROFILE=local")
    validate_at = result.stdout.index("make imports-validate IMPORT_TICKERS=<ticker>")
    preview_at = result.stdout.index("make imports-preview IMPORT_TICKERS=<ticker>")
    apply_at = result.stdout.index("make imports-apply IMPORT_TICKERS=<ticker>")
    compare_at = result.stdout.index("make reviewed-batch-compare PROFILE=local LANE=fundamentals")
    assert snapshot_at < validate_at < preview_at < apply_at < compare_at


@pytest.mark.parametrize("profile", [None, "", "unknown", "<default|demo|local>"])
def test_trusted_data_pilot_walkthrough_fails_closed_without_concrete_profile(profile: str | None):
    command = ["make", "trusted-data-pilot", "TICKERS=NVDA"]
    if profile is not None:
        command.append(f"PROFILE={profile}")

    result = subprocess.run(
        command,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )
    rendered = result.stdout + result.stderr

    assert result.returncode == 2
    assert "PROFILE must be exactly one of: default, demo, local" in rendered
    assert "make readiness-snapshot" not in rendered
    assert "make imports-apply" not in rendered
    assert "make reviewed-batch-compare" not in rendered


def test_default_and_composite_targets_are_guarded_and_exclude_writer_commands():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    forbidden_fragments = (
        "--write-output",
        "--refresh-artifacts",
        "src.readiness_engine",
        "readiness-materialize",
        "price-refresh",
        "monthly",
        "track-record",
        "research-decisions",
        "project-status --write-output",
    )

    assert (
        "NO_WRITE_GUARD = PYTHONDONTWRITEBYTECODE=1 python3 -m "
        "src.no_write_artifact_guard --project-root . --"
    ) in makefile
    for target in (
        "status",
        "pipeline",
        "onboarding",
        "daily",
        "dashboard-smoke",
        "test",
        "verify",
        "validate-all",
    ):
        block = _make_target_block(makefile, target)
        assert "$(NO_WRITE_GUARD)" in block, target
        assert not [fragment for fragment in forbidden_fragments if fragment in block], target


def test_onboarding_uses_read_only_price_coverage_while_price_coverage_target_writes():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    onboarding = _make_target_block(makefile, "onboarding")
    writer = _make_target_block(makefile, "price-coverage")

    assert "src.manual_price_import --coverage-only --read-only" in onboarding
    assert "src.manual_price_import --coverage-only" in writer
    assert "--read-only" not in writer


def test_reviewed_batch_compare_requires_and_forwards_one_profile():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    block = _make_target_block(makefile, "reviewed-batch-compare")

    assert "PROFILE is required: default, demo, or local" in block
    assert '--profile "$(PROFILE)"' in block
    assert "make readiness" not in block

    help_line = next(
        line for line in makefile.splitlines() if "make reviewed-batch-compare" in line and "Compare" in line
    )
    assert "PROFILE=<default|demo|local>" in help_line
    assert "current readiness is composed in memory and no current report is written" in help_line


def test_full_help_keeps_the_five_primary_readiness_boundaries_separate():
    result = subprocess.run(
        ["make", "help-full"], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0
    help_text = result.stdout
    advanced_readiness = help_text.split("Advanced readiness boundaries:\n", 1)[1].split(
        "\n\n", 1
    )[0]
    for boundary in (
        "make readiness-preview [TOP_N=20] In-memory preview",
        "make readiness-snapshot PROFILE=<default|demo|local> Required profile",
        "make reviewed-batch-compare PROFILE=<default|demo|local> [BATCH_ID=<id>] [LANE=prices] [REVIEW_DATE=<yyyy-mm-dd>] Compare a profile-bound prior snapshot; current readiness is composed in memory and no current report is written; Required profile",
        "make readiness        Deprecated no-write guard; exits 2",
        "CONFIRM_MATERIALIZE=1 make readiness-materialize PROFILE=<default|demo|local> Confirmed ignored local materialization",
    ):
        assert boundary in advanced_readiness


def test_sec_fundamentals_preview_is_explicit_capped_and_no_write():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    block = _make_target_block(makefile, "sec-fundamentals-preview")

    assert "TICKERS is required" in block
    assert (
        'PYTHONDONTWRITEBYTECODE=1 python3 -m src.sec_fundamentals_preview --tickers "$(TICKERS)"'
        in block
    )
    assert "--output" not in block
    for forbidden in (
        "sec-stage",
        "imports-apply",
        "readiness-materialize",
        "readiness-release-record",
        "yfinance",
        "yahoo",
        "stooq",
        "fmp",
        "alpha_vantage",
        "finnhub",
    ):
        assert forbidden not in block

    assert (
        "make sec-fundamentals-preview TICKERS=AAPL,NVDA,AMD Official SEC annual comparison; max five explicit tickers; no cache, staging, or apply writes"
        in makefile
    )


def test_sec_fundamentals_patch_preview_launcher_is_explicit_and_no_write():
    missing = subprocess.run(
        ["make", "--dry-run", "sec-fundamentals-patch-preview"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode != 0
    assert "SEC_PREVIEW is required" in missing.stderr

    missing_hashes = subprocess.run(
        [
            "make",
            "--dry-run",
            "sec-fundamentals-patch-preview",
            "SEC_PREVIEW=/tmp/reviewed-sec-preview.json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing_hashes.returncode != 0
    assert "EXPECTED_SEC_PREVIEW_SHA256 is required" in missing_hashes.stderr

    result = subprocess.run(
        [
            "make",
            "--dry-run",
            "sec-fundamentals-patch-preview",
            "SEC_PREVIEW=/tmp/reviewed-sec-preview.json",
            f"EXPECTED_SEC_PREVIEW_SHA256={'1' * 64}",
            f"EXPECTED_CANONICAL_SHA256={'2' * 64}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert (
        "PYTHONDONTWRITEBYTECODE=1 python3 -m src.sec_fundamentals_patch_preview "
        "--sec-preview-path \"/tmp/reviewed-sec-preview.json\" "
        "--canonical-path \"data/fundamentals.csv\" "
        f"--expected-sec-preview-sha256 \"{'1' * 64}\" "
        f"--expected-canonical-sha256 \"{'2' * 64}\""
        in result.stdout
    )
    assert re.search(r'--repository-head "[0-9a-f]{40}"', result.stdout)
    for forbidden in ("--output", "apply", "readiness", "materialize", "provider"):
        assert forbidden not in result.stdout.lower()


def test_sec_fundamentals_patch_apply_launcher_requires_exact_hashes_and_confirmation():
    missing = subprocess.run(
        ["make", "--dry-run", "sec-fundamentals-patch-apply"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode != 0
    assert "PATCH_PREVIEW is required" in missing.stderr

    unconfirmed = subprocess.run(
        [
            "make",
            "--dry-run",
            "sec-fundamentals-patch-apply",
            "PATCH_PREVIEW=/tmp/reviewed-patch.json",
            f"EXPECTED_PATCH_PREVIEW_SHA256={'1' * 64}",
            f"EXPECTED_CANONICAL_SHA256={'2' * 64}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert unconfirmed.returncode != 0
    assert "CONFIRM_EXACT_FOUR_CELL_APPLY=1 is required" in unconfirmed.stderr

    result = subprocess.run(
        [
            "make",
            "--dry-run",
            "sec-fundamentals-patch-apply",
            "PATCH_PREVIEW=/tmp/reviewed-patch.json",
            f"EXPECTED_PATCH_PREVIEW_SHA256={'1' * 64}",
            f"EXPECTED_CANONICAL_SHA256={'2' * 64}",
            "CONFIRM_EXACT_FOUR_CELL_APPLY=1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "python3 -m src.sec_fundamentals_patch_apply" in result.stdout
    assert '--patch-preview-path "/tmp/reviewed-patch.json"' in result.stdout
    assert '--expected-patch-preview-sha256 "' + ("1" * 64) + '"' in result.stdout
    assert '--expected-canonical-sha256 "' + ("2" * 64) + '"' in result.stdout
    assert re.search(r'--repository-head "[0-9a-f]{40}"', result.stdout)
    assert "--authorize-exact-four-cell-apply" in result.stdout
    for forbidden in ("readiness-materialize", "imports-apply", "provider", "currency"):
        assert forbidden not in result.stdout.lower()


def test_reviewed_batch_packet_targets_forward_one_named_profile():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    for target in ("reviewed-batch", "fundamentals-batch-proof", "peer-batch-proof"):
        block = _make_target_block(makefile, target)
        assert '--profile $(or $(PROFILE),default)' in block


def test_tracked_holdings_file_is_sanitized_demo_data():
    holdings_path = Path("data/holdings.csv")
    rows = list(csv.DictReader(holdings_path.read_text(encoding="utf-8").splitlines()))

    assert rows
    for row in rows:
        assert float(row["Shares"]) == 0.0
        assert float(row["CostBasis"]) == 0.0
        assert float(row["PositionPercent"]) == 0.0
        assert "example" in row["OriginalThesis"].lower()


def test_generated_staging_pathspec_files_are_ignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "outputs/staging/" in gitignore
    assert ".env" in gitignore
    assert ".env.local" in gitignore
    assert ".streamlit/secrets.toml" in gitignore
    assert "config/provider_keys.env" in gitignore
    assert "data/local/" in gitignore
    assert "outputs/local/" in gitignore


def test_streamlit_toolbar_uses_viewer_mode_for_public_dashboard():
    config = Path(".streamlit/config.toml").read_text(encoding="utf-8")

    assert "[client]" in config
    assert 'toolbarMode = "viewer"' in config


def test_dashboard_launchers_force_viewer_mode_for_public_demo():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    launcher = Path("scripts/dashboard.sh").read_text(encoding="utf-8")
    smoke = Path("scripts/smoke_dashboard.sh").read_text(encoding="utf-8")

    assert "streamlit run src/dashboard.py --client.toolbarMode viewer --server.headless true" in makefile
    assert "--client.toolbarMode viewer" in launcher
    assert "--server.headless true" in launcher
    assert 'export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"' in launcher
    assert 'export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"' in smoke
    assert 'PYTHONPATH="$(CURDIR):$${PYTHONPATH:-}" streamlit run' in makefile


def test_public_check_requires_a_fresh_dashboard_render_smoke():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "dashboard-render-smoke:" in makefile
    public_check = makefile.split("public-check:", 1)[1].split("\nstatus:", 1)[0]
    assert "$(MAKE) --silent demo-dashboard-render-smoke" in public_check
    assert "$(MAKE) --silent demo-dashboard-smoke" in public_check


def test_makefile_exposes_research_dashboard_render_smoke():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "research-dashboard-render-smoke" in _makefile_targets()
    target = makefile.split("research-dashboard-render-smoke:", 1)[1].split("\n\n", 1)[0]
    assert "python3 -m src.dashboard_render_smoke --routes research" in target


def test_calibration_evidence_bundle_preview_is_explicit_and_read_only():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    assert "calibration-evidence-bundle-preview" in _makefile_targets()
    block = makefile.split("calibration-evidence-bundle-preview:", 1)[1].split("\n\n", 1)[0]
    assert "BUNDLE is required" in block
    assert "python3 -m src.calibration_evidence_bundle preview" in block
    assert '--bundle "$${CALIBRATION_EVIDENCE_BUNDLE}"' in block
    assert "record" not in block
    assert "apply" not in block


def test_calibration_evidence_bundle_preview_rejects_an_implicit_input():
    result = subprocess.run(
        ["make", "calibration-evidence-bundle-preview"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "BUNDLE is required" in result.stderr


def test_dashboard_smoke_uses_an_isolated_fresh_server():
    smoke = Path("scripts/smoke_dashboard.sh").read_text(encoding="utf-8")

    assert 'PORT="${PORT:-0}"' in smoke
    assert 'if [[ "${PORT}" == "0" ]]' in smoke
    assert "Dashboard already healthy" not in smoke
    assert "--server.fileWatcherType none" in smoke
    assert "Dashboard import check passed" in smoke
    assert "Path(dashboard.__file__).resolve()" in smoke
    assert 'PYTHONDONTWRITEBYTECODE=1 REPO_ROOT="${REPO_ROOT}" python3' in smoke
    assert "PYTHONDONTWRITEBYTECODE=1 streamlit run" in smoke


def test_price_mutation_targets_use_the_ignored_local_profile():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    for target in ("price-validate", "price-preview", "price-apply", "price-refresh"):
        block = makefile.split(f"{target}:", 1)[1].split("\n\n", 1)[0]
        assert "STOCK_RESEARCH_DATA_PROFILE=local" in block


def test_price_review_targets_forward_one_explicit_temporal_cutoff():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    for target in ("price-validate", "price-preview", "price-apply"):
        block = makefile.split(f"{target}:", 1)[1].split("\n\n", 1)[0]
        assert '--review-cutoff "$(AS_OF)"' in block
    normalize = makefile.split("price-normalize:", 1)[1].split("\n\n", 1)[0]
    assert "AS_OF is required when RETRIEVED_AT is supplied" in normalize
    assert '--review-cutoff "$(AS_OF)"' in normalize


def test_demo_data_check_only_runs_the_manifest_verifier():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    match = re.search(r"^demo-data-check:\n(?P<body>(?:\t.*\n)+)", makefile, flags=re.MULTILINE)
    assert match is not None
    assert match.group("body").strip() == "@python3 -m src.demo_data_builder --check"


def test_dashboard_resolves_default_data_roots_through_the_profile_layer():
    dashboard = Path("src/dashboard.py").read_text(encoding="utf-8")

    assert "resolve_data_dir(project_root=BASE_DIR)" in dashboard
    assert "resolve_outputs_dir(project_root=BASE_DIR)" in dashboard
    assert "data_dir=DATA_DIR, output_dir=OUTPUTS_DIR" in dashboard
    assert "LocalDataCatalog(BASE_DIR, data_dir=DATA_DIR, outputs_dir=OUTPUTS_DIR)" in dashboard
    assert 'st.caption(f"Data profile: {data_profile.name}")' in dashboard


def test_universe_preview_summary_uses_compact_human_output():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    target = makefile.split("universe-preview-summary:", 1)[1].split("\nuniverse-stage:", 1)[0]

    assert "\t@python3 -m src.universe_builder --preview --preset sp500_smh --max-tickers 50" in target
    assert "--summary-json" not in target


def test_makefile_contains_convenience_targets():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    for target in (
        "help",
        "next-stage",
        "demo",
        "diff-hygiene",
        "trusted-data-pilot-candidates",
        "trusted-data-pilot-packet",
        "reviewed-data-proof",
        "reviewed-data-proof-record",
        "reviewed-batch-proof",
        "reviewed-batch-proof-record",
        "reviewed-batch-compare",
        "reviewed-batch-preflight",
        "lane-outcome-history",
        "price-reviewed-run",
        "public-demo-readiness-pack",
        "linkedin-share-check",
        "public-ux-review-checklist",
        "public-ux-review-checklist-json",
        "public-ux-review-notes",
        "public-ux-review-notes-check",
        "public-ux-review-note",
        "pilot-review-feedback",
        "pilot-share-brief",
        "readiness-ops-center",
        "coverage-frontier",
        "data-coverage-planner",
        "coverage-expansion-loop",
        "readiness-ops-evidence",
        "reviewed-batch",
        "decision-proof-queue",
        "metric-readiness-board",
        "diff-hygiene-summary",
        "pr-range-hygiene-check",
        "diff-hygiene-files",
        "data-release-decision",
        "public-release-package",
        "public-release-handoff",
        "source-activation-guide",
        "universe-scope",
        "staged-hygiene-check",
        "public-wording-check",
        "public-check",
        "status",
        "status-check",
        "test",
        "pipeline",
        "stock-report",
        "stock-report-md",
        "local-tickers",
        "monthly",
        "track-record",
        "validate-data",
        "data-sources-check",
        "data-sources",
        "research-health-check",
        "risk-context",
        "research-health",
        "action-queue-check",
        "action-queue",
        "project-status",
        "project-status-check",
        "verify",
        "validate-all",
        "daily",
        "dashboard",
        "dashboard-smoke",
        "demo-data-build",
        "demo-data-check",
        "demo-dashboard",
        "demo-dashboard-smoke",
        "demo-dashboard-render-smoke",
        "local-profile-seed",
        "sec-stage",
        "sec-validate",
        "sec-preview",
        "sec-apply",
        "import-staging",
        "universe-preview",
        "universe-preview-summary",
        "universe-stage",
        "universe-apply",
        "coverage",
        "data-wizard",
        "unlock-ladder",
        "unlock-summary",
        "command-bundles",
        "command-bundle-details",
        "command-bundle-runbook",
        "bundle-prices",
        "bundle-fundamentals",
        "bundle-peers",
        "bundle-prices-broader",
        "bundle-fundamentals-broader",
        "bundle-peers-broader",
        "detail-prices",
        "detail-fundamentals",
        "detail-peers",
        "detail-prices-broader",
        "detail-fundamentals-broader",
        "detail-peers-broader",
        "runbook-prices",
        "runbook-fundamentals",
        "runbook-peers",
        "runbook-prices-broader",
        "runbook-fundamentals-broader",
        "runbook-peers-broader",
        "focus-price",
        "focus-fundamentals",
        "focus-peers",
        "onboarding",
        "templates",
        "price-status",
        "price-worklist",
        "fundamentals-peer-worklist",
        "optional-context-worklist",
        "optional-context-source-ladder",
        "optional-context-source-ladder-queue",
        "sec-stage-queue",
        "peer-mapping-queue",
        "price-history-batch-closeout",
        "price-validate",
        "price-preview",
        "price-apply",
        "price-refresh",
        "price-refresh-loop",
        "price-normalize",
    ):
        assert f"{target}:" in makefile


def test_price_history_batch_closeout_launcher_is_read_only_and_scoped():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    target = makefile.split("price-history-batch-closeout:", 1)[1].split("\n\n", 1)[0]
    assert "python3 -m src.price_history_batch_closeout" in target
    assert "--top-n $(or $(TOP_N),10)" in target
    assert "$(if $(TICKERS),--tickers $(TICKERS),)" in target
    assert "make price-history-batch-closeout [TOP_N=10] [TICKERS=AIAI,AMAN]" in makefile


def test_price_history_proof_queue_launcher_forwards_include_reviewed_only_when_requested():
    base_environment = {**os.environ, "TOP_N": "1"}
    default = subprocess.run(
        ["make", "--dry-run", "price-history-proof-queue"],
        check=True,
        capture_output=True,
        env=base_environment,
        text=True,
    )
    included = subprocess.run(
        ["make", "--dry-run", "price-history-proof-queue", "INCLUDE_REVIEWED=1"],
        check=True,
        capture_output=True,
        env=base_environment,
        text=True,
    )

    assert "--include-reviewed" not in default.stdout
    assert "--include-reviewed" in included.stdout
    assert "make price-history-proof-queue [TOP_N=10] [TICKERS=AIAI,AMAN] [INCLUDE_REVIEWED=1] Show unreviewed executable blockers by default, or reviewed wait-only rows in audit mode" in Path("Makefile").read_text(encoding="utf-8")


def test_makefile_help_documents_key_workflows():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    for phrase in (
        "help-full:",
        "For the full local command catalog, run: make help-full",
        "next-stage:",
        "python3 -m src.next_stage",
        "Stock Research Command Center convenience commands",
        "First-time path:",
        "Print the clean visitor walkthrough",
        "make status-check TOP_N=5",
        "make stock-report-md TICKER=NVDA",
        "make dashboard-smoke",
        "make dashboard",
        "make trusted-data-pilot TOP_N=10",
        "Print the company-focused trusted-data pilot path",
        "make trusted-data-pilot-candidates TOP_N=10",
        "Rank current company candidates for the next trusted-data pilot",
        "make trusted-data-pilot-packet TICKER=CRDO",
        "Print one company's read-only evidence packet",
        "make trusted-data-pilot-lane LANE=fundamentals_dcf",
        "Print one lane group's ordered proof steps and evidence summary",
        "make reviewed-data-proof",
        "Print the durable reviewed data proof ledger",
        "make reviewed-batch-proof",
        "Print durable reviewed batch proof rows",
        "make reviewed-batch-compare",
        "Compare a profile-bound prior snapshot; current readiness is composed in memory and no current report is written",
        "make reviewed-batch-preflight",
        "Check snapshot, dry-run, compare, proof, and artifact gates",
        "make lane-outcome-history",
        "Summarize lane outcomes from the durable proof ledger",
        "make price-reviewed-run",
        "Print the controlled reviewed capped price run workflow",
        "make data-release-decision",
        "Print keep-local, reviewed-data-release, and cleanup choices after local data-output changes",
        "make public-demo-readiness-pack",
        "Print the small shareable public demo proof set",
        "make linkedin-share-check",
        "Print the final LinkedIn Featured-card checklist",
        "make public-ux-review-checklist",
        "Print the read-only five-page desktop/mobile UX review checklist",
        "make public-ux-review-checklist-json",
        "Print the machine-readable five-page desktop/mobile UX review checklist",
        "make public-ux-review-notes",
        "Write the local Markdown note template for a normal-browser UX review",
        "make public-ux-review-notes-check",
        "Summarize local UX review notes as pending, resolved, or environment-limited",
        "make public-ux-review-note",
        "Record one local UX review note row without staging or refreshing data",
        "make pilot-review-feedback",
        "Print the controlled 10-20 reviewer feedback capture guide",
        "make project-status-check",
        "Print project status without writing dashboard snapshot files",
        "make readiness-ops-center",
        "Print the broad lane-level readiness operations center",
        "make coverage-frontier",
        "Rank batch coverage opportunities by unlock impact",
        "make data-coverage-planner",
        "Print repeatable coverage expansion lanes without changing local data",
        "make coverage-expansion-loop",
        "Print the next reviewed coverage loop from planner to proof",
        "make readiness-ops-evidence",
        "Print the broad lane operations evidence checklist",
        "make reviewed-batch",
        "Preview or write a reviewed batch run packet for a selected lane",
        "make decision-proof-queue",
        "Preview or write the compact decision proof queue from current readiness outputs",
        "make metric-readiness-board [TICKERS=NVDA,META] [TOP_N=10] [BENCHMARKS=SPY,QQQ] [OUTPUT=outputs/metric_readiness_board.csv]",
        "make public-check / public-release-handoff Verify sharing and terminal steps",
        "make demo",
        "make trusted-data-pilot [TICKERS=NVDA,AVGO,AMD,MU,CRDO] [TOP_N=10] Print a read-only company-focused trusted-data pilot plan",
        "make trusted-data-pilot-candidates [TICKERS=NVDA,CRDO,META] [TOP_N=10] Rank read-only company candidates for the next trusted-data pilot",
        "make trusted-data-pilot-packet TICKER=CRDO Print one company's read-only before-report/review/validate/rejected-row/rebuild evidence packet",
        "make trusted-data-pilot-lane LANE=fundamentals_dcf [TICKERS=MU,CRDO,HOOD] [TOP_N=10] Print a read-only lane-group runbook and evidence summary",
        "make reviewed-data-proof [LEDGER=data/reviewed_data_proofs.csv] Print the durable reviewed data proof ledger",
        "make lane-outcome-history [LEDGER=data/reviewed_data_proofs.csv] Print lane outcome history from reviewed proof rows",
        "make reviewed-data-proof-record LANE=<lane> PROOF_ID=<id> PROOF_DATE=<yyyy-mm-dd> FINAL_OUTCOME=<supported|candidate_context_only|still_blocked|skipped|excluded> Record an intentional reviewed proof row",
        "make reviewed-batch-proof [LEDGER=data/reviewed_batch_proofs.csv] Print durable reviewed batch proof rows",
        "make reviewed-batch-proof-record BATCH_ID=<id> LANE=<lane> REVIEW_DATE=<yyyy-mm-dd> FINAL_OUTCOME=<auto_supported|human_reviewed_supported|candidate_context_only|still_blocked|skipped|excluded> Record a reviewed or auto-gated batch outcome",
        "make auto-refresh-plan       Print scheduler-ready source-backed auto-refresh lanes and auto gates",
        "make reviewed-batch-compare PROFILE=<default|demo|local> [BATCH_ID=<id>] [LANE=prices] [REVIEW_DATE=<yyyy-mm-dd>] Compare a profile-bound prior snapshot; current readiness is composed in memory and no current report is written",
        "make reviewed-batch-preflight [LANE=prices] [TOP_N=100] [MAX_CANDIDATES=3500] Check snapshot, dry-run, compare, proof, and artifact gates",
        "make price-reviewed-run [MAX_CANDIDATES=3500] [TOP_N=100] [PROVIDER=auto] Print reviewed capped price-run execution, diff, and rollback plan",
        "make public-demo-readiness-pack Print the small shareable public demo proof set",
        "make linkedin-share-check",
        "Print the final LinkedIn Featured-card checklist",
        "make pilot-share-brief",
        "Write the concise public/demo share brief without refreshing or applying data",
        "make readiness-ops-center Print lane-level ready/partial/blocked/excluded operations without refreshing data",
        "make coverage-frontier [TOP_N=10] Rank broad batch opportunities by unlock impact and safe command",
        "make data-coverage-planner [TOP_N=10] Print repeatable coverage expansion lanes with dry-run, proof, stop, and churn gates",
        "make coverage-expansion-loop [LANE=auto] [TOP_N=10] Print one copy-only planner -> preflight -> packet -> proof loop",
        "make readiness-ops-evidence [TOP_N=10] Print proof, churn, locked-lane, and exclusion evidence for readiness operations",
        "make reviewed-batch [DRY_RUN=1] [LANE=prices|fundamentals|share_count|peers|metrics|optional_context] [TOP_N=10] [TICKERS=NVDA,MSFT] Preview or write outputs/reviewed_batch_packet.md and .csv",
        "make decision-proof-queue [DRY_RUN=1] [TOP_N=12] [OUTPUT=outputs/decision_proof_queue.csv] [MD_OUTPUT=outputs/decision_proof_queue.md] Preview or write a copy-only proof queue from current decision/readiness outputs",
        "make diff-hygiene",
        "Print a read-only staging guide that separates product files from local data changes",
        "make diff-hygiene-summary",
        "Print a short read-only staging summary for public checks",
        "make diff-hygiene-files",
        "Write local pathspec files under outputs/staging for safer reviewed staging",
        "make data-release-decision",
        "Print read-only post-batch keep-local, reviewed-data-release, and cleanup guidance",
        "make public-release-package",
        "Print read-only product staging, generated exclusion, final checks, commit, and push guidance",
        "make public-release-handoff",
        "Print the copy-ready terminal handoff for verify, stage, commit, and push",
        "make session-source-preflight [SEC_USER_AGENT='Name email@example.com']",
        "Check one session's SEC/yfinance/local-fundamentals path before retrying source-backed coverage work",
        "make universe-scope [TICKERS=NVDA,META] [SECTOR=Technology] [THEME=AI] [TOP_N=10]",
        "Print active, ticker-list, sector/theme, ready-only, and missing-data scope commands without broad analysis",
        "make yfinance-stage TICKERS=NVDA",
        "make staged-hygiene-check",
        "Fail if staged files include unreviewed local data/report changes",
        "make public-wording-check",
        "Scan public docs, dashboard copy, and sample reports for unsupported advice/execution wording",
        "make public-check",
        "Run share-safe checks before posting the repo link; does not refresh broad local data",
        "Public share check: LinkedIn visual checklist",
        "@$(MAKE) --silent linkedin-share-check",
        "Run these from the repository root so make can find the project targets.",
        "make status [TOP_N=5]",
        "make status-check [TICKERS=NVDA,MSFT] [TOP_N=5]",
        "make verify",
        "make validate-all",
        "make daily",
        "make dashboard-smoke",
        "make data-sources-check [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make data-sources",
        "make research-health-check [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make risk-context",
        "make project-status",
        "make action-queue-check [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make stock-report-md TICKER=NVDA [MD_OUTPUT=outputs/stock_reports/nvda.md]",
        "make stock-report TICKER=NVDA [OUTPUT=outputs/nvda_stock_report.json] [MD_OUTPUT=outputs/stock_reports/nvda.md]",
        "Generate a readable Markdown report for demos and review",
        "Generate the report plus optional report data for inspection",
        "make local-tickers",
        "make coverage [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make data-wizard [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make unlock-ladder [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make unlock-summary [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make command-bundles [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make command-bundle-details [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make command-bundle-runbook [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "Show ordered steps for the current guided data batches",
        "make bundle-prices [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make bundle-fundamentals [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make bundle-peers [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make bundle-prices-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make bundle-fundamentals-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make bundle-peers-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make detail-prices [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make detail-fundamentals [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make detail-peers [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make detail-prices-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make detail-fundamentals-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make detail-peers-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make runbook-prices [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make runbook-fundamentals [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make runbook-peers [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make runbook-prices-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make runbook-fundamentals-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make runbook-peers-broader [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make focus-price TICKER=AMD",
        "make focus-fundamentals TICKER=NVDA",
        "make focus-peers TICKER=NVDA",
        "Show step-by-step price checks for the broader queue",
        "Show one ticker's peer detail and next local checks",
        "make price-status [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make price-worklist [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make price-refresh [TOP_N=25] [PROVIDER=auto|yahoo|stooq|ibkr|fmp|alpha_vantage|finnhub]",
        "make price-refresh TICKERS=NVDA,MSFT [PROVIDER=auto]",
        "make price-refresh-loop [MAX_CANDIDATES=3500] [TOP_N=100] [PROVIDER=auto] [SLEEP_SECONDS=30]",
        "make price-refresh-loop DRY_RUN=1",
        "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100",
        "avoids repeating 25-ticker refreshes manually",
        "make fundamentals-peer-worklist [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make optional-context-worklist [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make sec-stage-queue [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "make peer-mapping-queue [TICKERS=NVDA,MSFT] [TOP_N=10]",
        "Most read-only onboarding views also accept TOP_N=10 for a shorter local summary",
        "make import-staging",
        "make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual",
        "export SEC_USER_AGENT='Name email@example.com'",
        "make sec-stage TICKERS=NVDA,MSFT",
        "make imports-validate IMPORT_TICKERS=NVDA && make imports-preview IMPORT_TICKERS=NVDA",
        "make imports-apply IMPORT_TICKERS=NVDA only after validation passes, preview scope is intended, rejected rows are zero",
        "Use IMPORT_TICKERS for narrow reviewed slices; broad imports-apply requires ALLOW_BROAD_IMPORT_APPLY=1 after full staged-scope review",
        "make universe-preview",
        "make universe-preview-summary",
        "Preview-first fundamentals and universe imports",
    ):
        assert phrase in makefile

    for old_phrase in (
        "Generate one local stock report JSON plus a readable Markdown report",
        "Generate one local structured stock report plus a readable Markdown report",
        "Generate the report plus optional structured data for inspection",
        "Generate a readable Markdown report without printing the structured report data",
        "structured report data",
        "full JSON payload",
        "shorter terminal summary",
        "Fundamentals and universe import drafts:",
        "top bundle/runbook shortcut",
        "printed focus/runbook path",
        "Show only the price bundle runbook",
        "Show only the peer-mapping bundle",
        "Show one ticker's price detail row and runbook",
        "generated data churn",
    ):
        assert old_phrase not in makefile

    assert makefile.index("make stock-report-md TICKER=NVDA") < makefile.index("make stock-report TICKER=NVDA")
    assert makefile.index("First-time path:") < makefile.index("Core:")
    assert makefile.index("make price-refresh-loop DRY_RUN=1 Preview") < makefile.index(
        "make price-refresh [TOP_N=25]"
    )
    assert makefile.index("make price-refresh-loop [MAX_CANDIDATES=3500]") < makefile.index(
        "make price-refresh TICKERS=NVDA,MSFT"
    )


def test_linkedin_share_check_prints_read_only_final_checklist():
    result = subprocess.run(
        ["make", "linkedin-share-check"],
        check=True,
        capture_output=True,
        text=True,
    )

    output = result.stdout
    assert "LinkedIn Share Check" in output
    assert "Read-only: this target prints the final LinkedIn visual checklist only." in output
    assert "Stock Research Command Center | Evidence-First Company Research" in output
    assert "Research Desk -> Discover -> Company Workbench -> Monitor" in output
    assert "stable GitHub repository link only after this reviewed feature reaches the default branch" in output
    assert "Draft engineering preview" in output
    assert "docs/assets/linkedin-public-dashboard.png" in output
    assert "GitHub's generated OpenGraph card" in output
    assert "hosting" in output
    assert "screenshots prove current data freshness" in output
    assert "provider-key activation" in output
    assert "make public-check" in output


def test_make_help_output_stays_visitor_friendly():
    result = subprocess.run(["make", "help"], check=True, capture_output=True, text=True)
    output = result.stdout
    visitor_lines = [
        line
        for line in output.splitlines()
        if not (
            line.startswith("make[")
            and ("Entering directory" in line or "Leaving directory" in line)
        )
    ]

    assert "Stock Research Command Center" in output
    assert "Start here:" in output
    assert "make next-stage" in output
    assert "make demo" in output
    assert "make project-status-check" in output
    assert "make provider-setup-checklist" in output
    assert "make hosted-demo-readiness" in output
    assert "make stock-report-md TICKER=NVDA" in output
    assert "public-release-handoff" in output
    assert "For the full local command catalog, run: make help-full" in output
    assert "make trusted-data-pilot-candidates TOP_N=10" not in output
    assert "fundamentals-source-ladder-queue" not in output
    assert "Data onboarding:" not in output
    assert "Preview-first fundamentals and universe imports:" not in output
    assert len(visitor_lines) <= 25


def test_make_next_stage_prints_current_stage_ladder_without_running_broad_work():
    result = subprocess.run(["make", "next-stage"], check=True, capture_output=True, text=True)
    output = result.stdout

    assert "Stock Research Command Center next-stage ladder" in output
    assert "Read-only: this target prints the current next-stage decision ladder only." in output
    assert "Current package answer:" in output
    assert "Next executable repo-side item:" in output
    executable = output.split("Next executable repo-side item:\n", 1)[1].split(
        "\n\nExternal unblock conditions (not executable now):", 1
    )[0]
    assert executable.strip() == "- Readiness inspection: make readiness-preview TOP_N=20"
    assert "Hosted demo status:" in output
    assert "Provider key status:" in output
    assert "Source-proof queue status:" in output
    assert "External unblock conditions (not executable now):" in output
    assert "remote synchronization and public sharing require separate authorization" in output
    assert "hosted operation, credentials, source rights, reviewers, and supplied evidence" in output
    assert "Do not run broad proof queues while the continuation gate suppresses execution." in output
    assert "Generated churn stays excluded unless one exact artifact is reviewed evidence." in output
    assert "trusted-data-pilot-candidates" not in output
    assert "data-coverage-proof-queues" not in output


def test_metric_readiness_board_make_target_preserves_comma_default():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "DEFAULT_METRIC_BENCHMARKS := SPY,QQQ" in makefile
    assert '--benchmarks "$(if $(BENCHMARKS),$(BENCHMARKS),$(DEFAULT_METRIC_BENCHMARKS))"' in makefile
    assert "--output \"$(OUTPUT)\"" in makefile


def test_price_refresh_defaults_to_capped_broad_universe_batch():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "STOCK_RESEARCH_DATA_PROFILE=local python3 -m src.data_update --universe-file data/local/universe.csv --missing-only --max-tickers $(or $(TOP_N),25)" in makefile


def test_price_refresh_loop_uses_capped_defaults_and_ends_with_read_only_inspection():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    script = Path("scripts/price_refresh_loop.sh").read_text(encoding="utf-8")

    assert "price-refresh-loop:" in makefile
    assert 'MAX_CANDIDATES="$(MAX_CANDIDATES)" BATCHES=$(or $(BATCHES),5) TOP_N=$(or $(TOP_N),100) PROVIDER=$(or $(PROVIDER),auto) SLEEP_SECONDS=$(or $(SLEEP_SECONDS),30) DRY_RUN=$(or $(DRY_RUN),0) CONTINUE_ON_PROVIDER_FAILURE=$(or $(CONTINUE_ON_PROVIDER_FAILURE),1)' in makefile
    assert 'BATCHES="${BATCHES:-5}"' in script
    assert 'TOP_N="${TOP_N:-100}"' in script
    assert 'PROVIDER="${PROVIDER:-auto}"' in script
    assert 'DRY_RUN="${DRY_RUN:-0}"' in script
    assert 'MAX_CANDIDATES="${MAX_CANDIDATES:-}"' in script
    assert 'CONTINUE_ON_PROVIDER_FAILURE="${CONTINUE_ON_PROVIDER_FAILURE:-1}"' in script
    assert "MAX_CANDIDATES must be a positive integer when provided. Example: make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto" in script
    assert "BATCHES must be a positive integer. For broad coverage, prefer DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 so the loop calculates batches for you." in script
    assert "TOP_N must be a positive integer. Use TOP_N=100 for a capped broad dry run before changing local CSV files." in script
    assert 'BATCHES=$(((MAX_CANDIDATES + TOP_N - 1) / TOP_N))' in script
    assert "TOTAL_CANDIDATES=$((BATCHES * TOP_N))" in script
    assert "MANUAL_25_BATCHES=$(((TOTAL_CANDIDATES + 24) / 25))" in script
    assert "env_file_has_key()" in script
    assert "provider_key_present()" in script
    assert "for env_file in .env config/provider_keys.env .env.local" in script
    assert "Coverage target: $TARGET_NOTE. The final batch may have unused capacity if fewer missing tickers remain." in script
    assert "Provider boundary: this can add research-grade price rows only; it does not create fundamentals, peers, earnings, estimates, DCF inputs, or conclusions." in script
    assert "PROVIDER=auto tries Stooq, Yahoo, optional IBKR read-only, then configured FMP/Alpha Vantage/Finnhub before classifying the ticker as still missing." in script
    assert "Non-blocking behavior: if a provider batch fails" in script
    assert "Provider credential visibility:" in script
    assert "STOOQ_API_KEY=$STOOQ_KEY_STATUS" in script
    assert "FMP_API_KEY=$FMP_KEY_STATUS" in script
    assert "ALPHA_VANTAGE_API_KEY=$ALPHA_KEY_STATUS" in script
    assert "FINNHUB_API_KEY=$FINNHUB_KEY_STATUS" in script
    assert "Use this loop for broad coverage work instead of repeating 25-ticker refreshes manually." in script
    assert "Manual equivalent avoided: about $MANUAL_25_BATCHES separate 25-ticker refresh command(s)." in script
    assert "Estimated wait between batches: about $WAIT_SECONDS second(s), plus provider response time." in script
    assert "Resume behavior: each batch uses the missing-price worklist" in script
    assert "Before a real run, use make readiness-preview TOP_N=20" in script
    assert "What changes on a real run: local price CSVs may update." in script
    assert "The post-refresh readiness preview and status check do not persist derived artifacts." in script
    assert "What stays manual: staging, validation, commit selection, and any generated CSV review remain under your control." in script
    assert "Plain planning knob: set MAX_CANDIDATES=3500" in script
    assert "Use MAX_CANDIDATES first when you know the approximate missing-price count; use BATCHES only as an advanced override." in script
    assert "for a 3000+ ticker universe, set MAX_CANDIDATES and dry-run again" in script
    assert "do not babysit hundreds of tiny commands" in script
    assert "Review summary: one dry run gives a copyable capped plan; one reviewed loop command replaces many manual refresh commands." in script
    assert "Review summary: MAX_CANDIDATES is the approximate missing-price target; TOP_N is the per-batch safety cap." in script
    assert "Dry run only. No local CSV files were changed." in script
    assert "Requested target: up to $REQUESTED_TARGET missing-price candidate(s)." in script
    assert "Rounded batch capacity: up to $TOTAL_CANDIDATES ticker slot(s) across $BATCHES capped batch(es)." in script
    assert "Unused capacity is expected when the last batch has fewer missing tickers than TOP_N." in script
    assert "Manual 25-ticker commands avoided: about $MANUAL_25_BATCHES." in script
    assert "If interrupted or provider-limited, rerun the dry run" in script
    assert "No provider call, import, validation apply, or external account action runs during this dry run." in script
    assert "CONTINUE_ON_PROVIDER_FAILURE=$CONTINUE_ON_PROVIDER_FAILURE" in script
    assert "Planned loop command: make price-refresh-loop MAX_CANDIDATES=$MAX_CANDIDATES TOP_N=$TOP_N PROVIDER=$PROVIDER SLEEP_SECONDS=$SLEEP_SECONDS" in script
    assert "Planned loop command: make price-refresh-loop BATCHES=$BATCHES TOP_N=$TOP_N PROVIDER=$PROVIDER SLEEP_SECONDS=$SLEEP_SECONDS" in script
    assert "Each capped batch would run: make price-refresh TOP_N=$TOP_N PROVIDER=$PROVIDER" in script
    assert "Baseline inspection command before a real run: make readiness-preview TOP_N=20" in script
    assert "Hygiene command after a real run: make diff-hygiene" in script
    assert "Recommended next sequence:" in script
    assert "1. make readiness-preview TOP_N=20" in script
    assert "2. make price-refresh-loop MAX_CANDIDATES=$MAX_CANDIDATES TOP_N=$TOP_N PROVIDER=$PROVIDER SLEEP_SECONDS=$SLEEP_SECONDS" in script
    assert "2. make price-refresh-loop BATCHES=$BATCHES TOP_N=$TOP_N PROVIDER=$PROVIDER SLEEP_SECONDS=$SLEEP_SECONDS" in script
    assert "3. make status-check TOP_N=5" in script
    assert "4. make diff-hygiene" in script
    assert "If you want broader coverage, set MAX_CANDIDATES first while keeping TOP_N capped, then dry-run again." in script
    assert "Example broad dry run: make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=$PROVIDER" in script
    assert "Advanced alternative: make price-refresh-loop DRY_RUN=1 BATCHES=30 TOP_N=100 PROVIDER=$PROVIDER" in script
    assert "copy the one planned loop command instead of running many 25-ticker commands by hand" in script
    assert "Dry-run result: no data changed; review the planned command, then run exactly one capped loop when ready." in script
    assert "Recalculate anytime: rerun DRY_RUN=1 after interruptions, provider limits, or local CSV changes." in script
    assert "Safe fallback: use make runbook-prices-broader or make focus-price TICKER=... to switch to the local import file workflow." in script
    assert "Manual CSV path: normalize downloaded OHLCV rows with make price-normalize" in script
    assert "Resume note: after fixing the source issue, rerun make price-refresh-loop DRY_RUN=1" in script
    assert 'make price-refresh TOP_N="$TOP_N" PROVIDER="$PROVIDER"' in script
    assert "Price refresh batch $i failed." in script
    assert "Non-blocking provider failure recorded for price batch $i." in script
    assert "Source path outcome: price provider ladder still_blocked for this session after batch $FAILED_BATCH failed." in script
    assert "This replaces repeating 25-ticker refreshes manually" in script
    real_branch = script.split('if [ "$DRY_RUN" = "1" ] || [ "$DRY_RUN" = "true" ]; then', 1)[1].split("fi\n\ni=1", 1)[1]
    assert "make price-coverage" not in real_branch
    assert "make readiness\n" not in real_branch
    assert "make project-status" not in real_branch
    real_make_commands = [line.strip() for line in real_branch.splitlines() if line.startswith("make ")]
    assert real_make_commands[-2:] == ["make readiness-preview TOP_N=20", "make status-check TOP_N=5"]
    assert "run make diff-hygiene before staging" in script


def test_operator_guide_documents_local_provider_env_loading():
    guide = Path("docs/OPERATOR_GUIDE.md").read_text(encoding="utf-8")
    example = Path("config/provider_keys.env.example").read_text(encoding="utf-8")

    assert "copy `config/provider_keys.env.example` to `config/provider_keys.env` or create `.env`" in guide
    assert "load those local files automatically" in guide
    assert "Exported terminal variables still win" in guide
    assert "make optional-context-source-ladder-queue TOP_N=10" in guide
    assert "reviewed provider-assisted rows pass the import gates" in guide
    assert "FMP_API_KEY=" in example
    assert "ALPHA_VANTAGE_API_KEY=" in example
    assert "FINNHUB_API_KEY=" in example
    assert "IBKR is optional read-only daily OHLCV and disabled by default" in example
    assert "IBKR_HOST=" in example
    assert "IBKR_PORT=" in example
    assert "IBKR_CLIENT_ID=" in example
    assert "No broker trading, account actions, order routing, or auto-trading" in example


def test_source_activation_guide_documents_provider_setup_without_real_keys():
    guide = Path("docs/SOURCE_ACTIVATION_GUIDE.md").read_text(encoding="utf-8")

    assert "Source Activation Guide" in guide
    assert "FMP_API_KEY" in guide
    assert "ALPHA_VANTAGE_API_KEY" in guide
    assert "FINNHUB_API_KEY" in guide
    assert "STOOQ_API_KEY" in guide
    assert "IBKR_HOST" in guide
    assert "IBKR_PORT" in guide
    assert "IBKR_CLIENT_ID" in guide
    assert "read-only daily OHLCV" in guide
    assert "disabled by default" in guide
    assert "Do not commit" in guide
    assert "make provider-setup-checklist" in guide
    assert "whether its variable names are stale" in guide
    assert "It inspects names only; it never prints" in guide
    assert "price" in guide
    assert "fundamentals" in guide
    assert "share count" in guide
    assert "metadata only" in guide
    assert "| Source | Setup | Can help cover | Batch policy | Smoke command | Cannot unlock by itself |" in guide
    assert "broad unlimited refresh" not in guide.lower()
    assert "unlimited batch coverage" not in guide.lower()
    assert "full-universe refresh without caps" in guide
    assert "FMP free tier" in guide and "small batch" in guide
    assert "When all keyed providers are missing, start with FMP" in guide
    assert "| FMP free tier | `FMP_API_KEY` | price, fundamentals, share count fallback | <=250 requests/day; <=25 tickers/run | `make fmp-smoke TICKER=<ticker>` | full-universe refresh without caps |" in guide
    assert "| Alpha Vantage free tier | `ALPHA_VANTAGE_API_KEY` | price, fundamentals, share count fallback | <=25 requests/day; <=5 tickers/run | `make alpha-vantage-smoke TICKER=<ticker>` | full-universe refresh without caps |" in guide
    assert "| Finnhub free tier | `FINNHUB_API_KEY` | price, fundamentals, share count fallback | <=60 requests/day; <=10 tickers/run | `make finnhub-smoke TICKER=<ticker>` | full-universe refresh without caps |" in guide
    assert "`make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=1 TOP_N=1 PROVIDER=stooq`" in guide
    assert "Keyed-provider smoke commands stage one ticker, validate, and preview only; they do not apply rows." in guide
    assert "Alpha Vantage free tier" in guide and "25 requests/day" in guide
    assert "Finnhub free tier" in guide and "60 requests/day" in guide
    assert "not investment advice" in guide
    assert "REPLACE_WITH" in guide
    assert "Operator Summary" in guide
    assert "`can_run_now`" in guide
    assert "`needs_setup`" in guide
    assert "`avoid_repeating`" in guide
    assert "`next_step`" in guide
    assert "## One-Ticker Smoke Handoff" in guide
    assert "| Step | Command | Inspect | Stop rule |" in guide
    assert "| 1. Pick reviewed ticker | `make project-status-check` | Choose one ticker from the current status/proof packet; do not use a broad ticker list. | Stop if no source-proof queue, proof packet, or reviewed ticker scope exists. |" in guide
    assert "| 2. Configure one provider | Set `FMP_API_KEY` outside the repo | Use `config/provider_keys.env` or hosting secrets; never commit real keys. | Stop if the key is missing; classify FMP as `external_key_required` and keep GitHub/demo flow unchanged. |" in guide
    assert "| 3. Run one smoke | `make fmp-smoke TICKER=<ticker>` | Confirm staged rows have source provenance and belong only to the reviewed ticker. | Stop if no source-backed rows are staged or the provider returns only unsupported fields. |" in guide
    assert "| 4. Validate and preview | `make imports-validate IMPORT_TICKERS=<ticker>` then `make imports-preview IMPORT_TICKERS=<ticker>` | Validation must pass, rejected rows must be zero, and preview scope must be narrow and intended. | Stop before apply if validation fails, rejected rows appear, scope widens, or provenance is missing. |" in guide
    assert "| 5. Decide apply or classify | `make imports-apply IMPORT_TICKERS=<ticker>` only after gate passes | After apply, rebuild readiness and record proof; otherwise record `still_blocked`, `skipped`, `excluded`, or `candidate_context_only`. | Never use provider setup alone as readiness proof. |" in guide
    assert "One-ticker smoke handoff is only for a reviewed ticker after the status/proof packet identifies a source-backed path." in guide


def test_provider_setup_checklist_launcher_is_available():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "provider-setup-checklist" in makefile
    assert "provider-setup-checklist:\n\t@python3 -m src.source_activation_guide --checklist" in makefile
    assert "make provider-setup-checklist" in makefile
    assert "Print checklist-style provider setup states without exposing keys" in makefile


def test_universe_stage_launcher_splits_stage_from_apply():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "universe-stage" in makefile
    assert "universe-stage:\n\tpython3 -m src.universe_builder --write-import --preset sp500_smh --max-tickers 50" in makefile
    apply_target = makefile.split("universe-apply:", 1)[1].split("\nuniverse-refresh:", 1)[0]
    assert "--write-import" not in apply_target
    assert "python3 -m src.universe_builder --apply-import" in apply_target


def test_makefile_exposes_optional_context_source_ladder_targets():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "optional-context-source-ladder:\nifndef TICKERS" in makefile
    assert "python3 -m src.stock_report --optional-context-source-ladder --tickers $(TICKERS)" in makefile
    assert (
        "optional-context-source-ladder-queue:\n\tpython3 -m src.stock_report --optional-context-source-ladder "
        "--optional-context-dry-run --from-optional-context-queue --top-n $(or $(TOP_N),10)"
    ) in makefile
    assert "make optional-context-source-ladder-queue TOP_N=10" in makefile


def test_makefile_exposes_validate_preview_only_provider_smoke_targets():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "provider-smoke:" in makefile
    assert "fmp-smoke:" in makefile
    assert "alpha-vantage-smoke:" in makefile
    assert "finnhub-smoke:" in makefile
    provider_target = makefile.split("provider-smoke:", 1)[1].split("\nfmp-smoke:", 1)[0]
    assert "$(MAKE) fmp-stage TICKERS=$(TICKER)" in provider_target
    assert "$(MAKE) alpha-vantage-stage TICKERS=$(TICKER)" in provider_target
    assert "$(MAKE) finnhub-stage TICKERS=$(TICKER)" in provider_target
    assert "$(MAKE) imports-validate IMPORT_TICKERS=$(TICKER)" in provider_target
    assert "$(MAKE) imports-preview IMPORT_TICKERS=$(TICKER)" in provider_target
    assert "imports-apply" not in provider_target
    assert "make provider-smoke PROVIDER=fmp TICKER=NVDA" in makefile
    assert "Validate/preview one keyed provider ticker without applying rows" in makefile


def test_price_refresh_loop_dry_run_reads_local_provider_env_files(tmp_path):
    project_root = Path.cwd()
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "provider_keys.env").write_text(
        "STOOQ_API_KEY=stooq-from-file\n"
        "FMP_API_KEY=fmp-from-file\n"
        "ALPHA_VANTAGE_API_KEY=alpha-from-file\n"
        "FINNHUB_API_KEY=finnhub-from-file\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    for key in ("STOOQ_API_KEY", "STOQ_API_KEY", "FMP_API_KEY", "ALPHA_VANTAGE_API_KEY", "FINNHUB_API_KEY"):
        env.pop(key, None)
    env.update(
        {
            "DRY_RUN": "1",
            "MAX_CANDIDATES": "1",
            "TOP_N": "1",
            "PROVIDER": "auto",
            "SLEEP_SECONDS": "0",
        }
    )

    result = subprocess.run(
        ["sh", str(project_root / "scripts" / "price_refresh_loop.sh")],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert (
        "Provider credential visibility: STOOQ_API_KEY=present; FMP_API_KEY=present; "
        "ALPHA_VANTAGE_API_KEY=present; FINNHUB_API_KEY=present."
    ) in result.stdout
    assert "stooq-from-file" not in result.stdout
    assert "fmp-from-file" not in result.stdout


def test_price_refresh_loop_dry_run_calculates_broad_universe_plan_without_writes(
    tmp_path: Path,
):
    script = Path(__file__).resolve().parents[1] / "scripts" / "price_refresh_loop.sh"
    result = subprocess.run(
        ["sh", str(script)],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env={
            "BATCHES": "5",
            "TOP_N": "100",
            "PROVIDER": "auto",
            "SLEEP_SECONDS": "30",
            "DRY_RUN": "1",
            "MAX_CANDIDATES": "3538",
        },
    )
    output = result.stdout.lower()

    assert "dry run only. no local csv files were changed." in output
    assert "requested coverage target: up to 3538 missing-price candidates; calculated 36 capped batch(es)." in output
    assert "requested target: up to 3538 missing-price candidate(s)." in output
    assert "rounded batch capacity: up to 3600 ticker slot(s) across 36 capped batch(es)." in output
    assert "unused capacity is expected when the last batch has fewer missing tickers than top_n." in output
    assert "manual 25-ticker commands avoided: about 144." in output
    assert "review summary: one dry run gives a copyable capped plan; one reviewed loop command replaces many manual refresh commands." in output
    assert "review summary: max_candidates is the approximate missing-price target; top_n is the per-batch safety cap." in output
    assert "no provider call, import, validation apply, or external account action runs during this dry run." in output
    assert "provider boundary: this can add research-grade price rows only; it does not create fundamentals, peers, earnings, estimates, dcf inputs, or conclusions." in output
    assert "provider credential visibility:" in output
    assert "stooq_api_key=missing" in output
    assert "fmp_api_key=missing" in output
    assert "alpha_vantage_api_key=missing" in output
    assert "planned loop command: make price-refresh-loop max_candidates=3538 top_n=100 provider=auto sleep_seconds=30" in output
    assert "copy the one planned loop command instead of running many 25-ticker commands by hand" in output
    assert "dry-run result: no data changed; review the planned command, then run exactly one capped loop when ready." in output
    assert "recalculate anytime: rerun dry_run=1 after interruptions, provider limits, or local csv changes." in output
    assert "does not connect to brokers, place orders, or make recommendations" in output
    assert "buy" not in output
    assert "sell" not in output


def test_price_refresh_loop_can_record_provider_failure_without_blocking(tmp_path: Path):
    fake_make = tmp_path / "make"
    calls = tmp_path / "calls.log"
    fake_make.write_text(
        "#!/usr/bin/env sh\n"
        "echo \"$*\" >> \"$CALLS_LOG\"\n"
        "case \"$1\" in\n"
        "  price-refresh) exit 1 ;;\n"
        "  readiness-preview|status-check) exit 0 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    fake_make.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "CALLS_LOG": str(calls),
        "BATCHES": "3",
        "TOP_N": "2",
        "PROVIDER": "auto",
        "SLEEP_SECONDS": "0",
        "DRY_RUN": "0",
        "CONTINUE_ON_PROVIDER_FAILURE": "1",
    }

    result = subprocess.run(
        ["sh", "scripts/price_refresh_loop.sh"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    output = result.stdout.lower()
    recorded_calls = calls.read_text(encoding="utf-8").splitlines()

    assert "non-blocking provider failure recorded for price batch 1." in output
    assert "skipping remaining price batches in this session" in output
    assert "source path outcome: price provider ladder still_blocked for this session" in output
    assert recorded_calls.count("price-refresh TOP_N=2 PROVIDER=auto") == 1
    assert recorded_calls[-2:] == ["readiness-preview TOP_N=20", "status-check TOP_N=5"]


def test_readme_public_landing_page_is_short_visual_and_command_focused():
    readme = Path("README.md").read_text(encoding="utf-8")
    preview = Path("docs/assets/dashboard-preview.svg").read_text(encoding="utf-8")
    public_demo = Path("docs/PUBLIC_DEMO_WALKTHROUGH.md").read_text(encoding="utf-8")

    assert len(readme.splitlines()) < 180
    assert "![Company Workbench answer preview](docs/assets/linkedin-public-dashboard.png)" in readme
    assert "make readiness-ops-center` for lane truth" in readme
    for preview_phrase in (
        "plain-language stock analysis modes",
        "At A Glance single-stock status",
        "Evaluation Snapshot",
        "Best Review Path",
        "At A Glance + Proof Checklist before tables",
        "Proof History: evidence for changed states",
        "Mode + decision",
        "DCF + peers",
        "What not to infer",
        "Next local step",
        "DCF-ready review",
        "Standalone DCF review",
        "Price/setup review",
        "Monitor-only context",
        "Data needed before analysis",
        "Data-confidence cue",
        "Public Demo",
        "MU peer-input and CRDO fundamentals-gated proof paths",
        "Pilot outcomes: Supported, Still blocked, or Skip after proof",
        "QQQ excluded",
        "project DCF method notes",
        "DCF path: cash flows, terminal value, cash/debt, fair value/share",
        "copy-only proof commands",
    ):
        assert preview_phrase in preview
    for stale_preview_phrase in ("Analysis modes before tables", "Standalone DCF</text>", "Price/setup only", "Monitor-only</text>", "Explore ready names: Home filters and sample reports"):
        assert stale_preview_phrase not in preview
    assert "## Quick Start" in readme
    assert "flowchart LR" in readme
    assert 'Desk["Research Desk: changed evidence"] --> Discover["Discover: strict eligibility or saved evidence"]' in readme
    assert 'Discover --> Workbench["Company Workbench: Company Brief first"]' in readme
    assert 'Workbench --> Monitor["Monitor: unresolved research changes"]' in readme
    assert 'Workbench -. advanced evidence .-> Health["Data Health and Proof History"]' in readme
    assert "Open the product before proof packets or report commands" in readme
    quick_start = readme[readme.index("## Quick Start") : readme.index("## Try This Visitor Workflow")]
    assert quick_start.index("make demo-dashboard") < quick_start.index("make status-check TOP_N=5")
    assert quick_start.index("make demo-dashboard") < quick_start.index("make pilot-readiness-check TOP_N=10")
    assert quick_start.index("make demo-dashboard") < quick_start.index("make stock-report-md TICKER=NVDA")
    assert "Optional saved generated-snapshot inspection after the app flow is clear" in quick_start
    assert "When you want to rebuild local outputs after changing data, use the deeper [Local Workflow Guide](docs/OPERATOR_GUIDE.md) for rebuild, import, refresh, and proof steps." in readme
    assert "## What You Can Analyze" in readme
    assert "## How Analysis Works" in readme
    assert "Read the counts in three layers:" in readme
    assert "master universe for broad coverage planning" in readme
    assert "active universe for the demo/research workflow" in readme
    assert "analysis-ready subsets for DCF, peer context, or candidate review" in readme
    assert "A tracked ticker is not automatically ready for every analysis family" in readme
    assert "## What Works Today" in readme
    assert "## Try This Visitor Workflow" in readme
    assert "Open the product first and follow the five-page path." in readme
    assert "Stock Selector filters readiness-backed candidates without framing the queue as advice." in readme
    assert "Use terminal commands only when you want to inspect the same proof artifacts locally." in readme
    assert "Optional local proof checks:" in readme
    assert "| Home | You want the workflow question, next safe action, stop rule, and then readiness context before choosing a route. | `Home` |" in readme
    assert "| Stock Selector | You want to filter readiness-backed candidates before opening a one-ticker report. | `Stock Selector` |" in readme
    assert "| Single-Stock Report | You want a ticker-level research note with ready, blocked, excluded, and data-confidence states. | `Single-Stock Report` |" in readme
    assert "| Proof History | You want one evidence answer before opening raw proof ledger details. | `Proof History` |" in readme
    assert "| Proof History | You want to see the proof ledger" not in readme
    assert "`Home`, then focused review pages" not in readme
    assert "The shortest public walkthrough uses NVDA, ACIC, AACI, QQQ, and MU only as optional state examples." in readme
    assert "[Visitor Workflow Walkthrough](docs/PUBLIC_DEMO_WALKTHROUGH.md)" in readme
    assert "validate/apply step, rejected-row report, and rebuild-proof packet" not in readme
    local_commands = public_demo[public_demo.index("## Local Commands") : public_demo.index("The dashboard defaults")]
    assert local_commands.index("make demo-dashboard") < local_commands.index("make status-check TOP_N=5")
    assert local_commands.index("make demo-dashboard") < local_commands.index("make stock-report-md TICKER=NVDA")
    assert "Optional read-only proof after the app flow is clear" in local_commands
    assert "make project-status-check" in public_demo
    assert "make data-coverage-proof-queues TOP_N=10" not in local_commands
    assert "make trusted-data-pilot-candidates TOP_N=10" not in local_commands
    public_demo_commands = public_demo.split("## Local Commands", 1)[1].split("The dashboard defaults", 1)[0]
    assert public_demo_commands.index("make project-status-check") < public_demo_commands.index(
        "make provider-setup-checklist"
    )
    assert "Do not open broad proof queues from the public walkthrough" in public_demo
    assert "Use the operator guide only after project-status-check shows executable source-backed candidates" in public_demo
    assert "use when project-status-check says source-proof queues are exhausted" in public_demo_commands
    assert "open source-proof queues only when project-status-check shows executable proof candidates" not in public_demo
    assert "make project-status && make data-coverage-proof-queues TOP_N=10" not in readme
    assert "make project-status-check && make provider-setup-checklist" in readme
    assert "make trusted-data-pilot-packet TICKER=MU" not in local_commands
    assert "make trusted-data-pilot-packet TICKER=AACI" not in local_commands
    assert "Local file presence, row counts, staged files, and rejected-row reports are inspection cues, not proof" in public_demo
    assert "Peer context is distinct from optional earnings and estimate lanes" in public_demo
    assert "Missing data is not a product failure here" in public_demo
    assert "snapshot the baseline, review source proof, validate/preview and check rejected rows, rebuild readiness and the stock report, then compare the after report" not in readme
    assert "snapshot the baseline, review source proof, validate/preview and check rejected rows, rebuild readiness and the stock report, then compare the after report" in public_demo
    assert "Read the outcome in three states: `Supported` means rebuilt readiness and the regenerated report show the lane is ready" not in readme
    assert "Read the outcome in three states: `Supported` means rebuilt readiness and the regenerated report show the lane is ready" in public_demo
    assert "`Still blocked` means validation failed, rejected rows appeared, or the report stayed locked" not in readme
    assert "`Still blocked` means validation failed, rejected rows appeared, or the report stayed locked" in public_demo
    assert "`Skip` means source proof is unavailable, so no placeholder rows are applied" not in readme
    assert "`Skip` means source proof is unavailable, so no placeholder rows are applied" in public_demo
    assert readme.index("make stock-report-md TICKER=NVDA") < readme.index("make stock-report-md TICKER=ACIC")
    assert readme.index("make stock-report-md TICKER=ACIC") < readme.index("make stock-report-md TICKER=QQQ")
    main_path = readme.split("## Try This Visitor Workflow", 1)[1].split("Optional local proof checks:", 1)[0]
    proof_checks = readme.split("Optional local proof checks:", 1)[1].split("The shortest public walkthrough", 1)[0]
    assert "make trusted-data-pilot-candidates TOP_N=10" not in main_path
    assert proof_checks.index("make project-status-check") < proof_checks.index("make trusted-data-pilot-candidates TOP_N=10")
    assert proof_checks.index("make trusted-data-pilot-candidates TOP_N=10") < proof_checks.index("make trusted-data-pilot-packet TICKER=MU")
    assert proof_checks.index("make trusted-data-pilot-packet TICKER=MU") < proof_checks.index("make trusted-data-pilot-packet TICKER=AACI")
    assert "## Local Data Hygiene" in readme
    assert "## License" in readme
    assert "## Analysis Methodology" in readme
    assert "docs/METHODOLOGY.md" in readme
    assert "docs/analysis_capability_audit.md" in readme
    assert "[Local Workflow Guide](docs/OPERATOR_GUIDE.md)" in readme
    assert "[Data Strategy](docs/DATA_STRATEGY.md)" in readme
    assert "pip install -e '.[dev]'" in readme
    assert "pip install -e .[dev]" not in readme
    for phrase in (
        "make demo",
        "make trusted-data-pilot TOP_N=10",
        "make trusted-data-pilot-packet TICKER=MU",
        "make trusted-data-pilot-packet TICKER=AACI",
        "make public-check",
        "make stock-report-md TICKER=NVDA",
        "make stock-report-md TICKER=ACIC",
        "make stock-report-md TICKER=AACI",
        "make stock-report-md TICKER=QQQ",
        "make stock-report-md TICKER=SMH",
        "price context with DCF still gated",
        "make stock-report TICKER=NVDA",
        "make dashboard",
        "make status-check TOP_N=5",
        "not investment advice",
        "review states",
        "Example map",
        "operating-company DCF is excluded, not failed",
        "fundamentals-blocked company",
        "ranked pilot packet first when a peer-input lane leads",
        "guessed peers or file row counts do not become valuation",
        "The pilot candidate command may rank a peer-input example such as `MU` first and also name a fundamentals/DCF example such as `CRDO`",
        "both remain read-only proof packets until source review and rebuilt readiness prove a lane changed",
        "At A Glance status, a plain-English Reader Guide, an Evaluation Snapshot, a Proof Checklist, Best Review Path, data-confidence cues, source readiness notes, and read-only proof steps",
            "single-stock reports with reader guidance, proof checklists, blockers, read-only proof steps, and source readiness notes",
        "The report is not a black box",
        "project rules decide what can be analyzed",
        "Price-ready rows can support setup/risk context",
        "DCF-ready rows can support assumptions and sensitivity",
        "peer-ready rows can support source-backed relative context",
        "Missing fundamentals, peer inputs, earnings, or estimates stay locked",
        "company valuation is excluded for ETF/index/fund monitor rows, not failed",
        "Markdown reports start with a visitor scan cue, then `At A Glance`, a `Reader Guide`, an `Evaluation Snapshot`, a `Proof Checklist`, and `Best Review Path`",
        "what evidence proves the current mode",
        "what valuation is supported or blocked",
        "what to read first",
        "Copyable Proof Commands",
        "readiness-state output, not an action list",
        "Review them before committing",
            "Before sharing or committing, run `make public-check`, then `make public-release-package`",
            "compact branch status, package status, staging, generated-exclusion, final-check, commit, and push checklist",
            "staged-file inspection, commit, branch-status check, and push",
            "Use `make diff-hygiene` when you need the full file list",
        "For a large dirty tree, run `make diff-hygiene-files`",
        "product-pending, generated-churn-only, or clean before staging",
        "make staged-hygiene-check",
        "git diff --cached --check",
        "git diff --cached --name-only",
        "outputs/staging/",
        "internal development notes, and stale repo links",
        "safe staging suggestion for product files and reviewed Markdown reports",
        "large generated CSV/JSON changes",
        "controlled portfolio-demo license",
        "copying, redistribution, sublicensing, hosted reuse",
        "[License Decision Guide](docs/LICENSE_DECISION_GUIDE.md)",
        "where the method lives",
        "analysis rules, valuation gates, decision buckets",
        "Strongest today",
        "Main modes",
        "DCF-ready review",
        "Standalone DCF review",
        "Price/setup review only",
        "Monitor-only context",
        "Data needed before analysis",
        "DCF-ready company review with source-backed peer context",
        "price context with the DCF path still gated",
        "fundamentals-blocked company",
        "[NVDA](outputs/stock_reports/nvda.md)",
        "[QQQ](outputs/stock_reports/qqq.md)",
        "[SMH](outputs/stock_reports/smh.md)",
        "Useful with limits",
        "Intentionally locked",
        "Not built to be",
        "Visitor status: the product workflow, dashboard, single-stock reports, readiness gates, visitor path, and public checks are working",
        "remain visibly blocked by missing trusted data until trusted rows exist",
        "source-proof work rather than broken analysis",
        "`undervalued_candidates.csv` is a legacy filename for valuation-readiness and re-rating context",
        "not automatic undervalued calls",
    ):
        assert phrase in readme
    quick_start = readme.split("## Quick Start", 1)[1].split("## Try This Visitor Workflow", 1)[0]
    assert "make pipeline" not in quick_start
    assert "\nmake readiness\n" not in quick_start
    assert quick_start.index("make demo") < quick_start.index("make demo-dashboard")
    assert quick_start.index("make demo-dashboard") < quick_start.index("make status-check TOP_N=5")
    assert quick_start.index("make status-check TOP_N=5") < quick_start.index("make stock-report-md TICKER=NVDA")
    operator_guide = Path("docs/OPERATOR_GUIDE.md").read_text(encoding="utf-8")
    for phrase in (
        "make price-history-proof-queue TOP_N=10",
        "make price-refresh-loop DRY_RUN=1",
        "make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto",
        "make readiness-snapshot",
        "make diff-hygiene",
        "make focus-fundamentals TICKER=NVDA",
        "make peer-mapping-queue TOP_N=10",
        "make optional-context-worklist TOP_N=10",
        "make templates",
        "make imports-validate",
            "make imports-preview",
            "make imports-apply",
            "Large refreshed CSVs are local working data",
            "Provider boundary: price refreshes can improve research-grade local price rows",
            "they do not create fundamentals, source-backed peers, optional context, DCF inputs, or research conclusions",
            "Optional earnings and analyst-estimate rows can be staged through the optional-context source ladder",
        ):
            assert phrase in operator_guide
    for visitor_clutter in (
        "http://localhost:8501/?page=single-stock-report",
        "make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto SLEEP_SECONDS=30",
        "Targeted missing-data examples",
        "Preview-first import flow",
    ):
        assert visitor_clutter not in readme
    for old_phrase in (
        "operator console",
        "deeper local runbook",
        "refreshed generated CSV churn",
        "generated data churn",
        "generated CSV/JSON churn",
        "broad refresh churn",
        "generated report CSVs",
        "operator workflow",
        "source/freshness auditability",
    ):
        assert old_phrase not in readme


def test_public_markdown_links_resolve_to_tracked_local_files():
    public_docs = [
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("PRODUCT_SPEC.md"),
        Path("READINESS_MODEL.md"),
        Path("DECISION_OUTPUT_MODEL.md"),
        *Path("docs").glob("*.md"),
        *Path("outputs/stock_reports").glob("*.md"),
    ]
    missing: list[tuple[str, str]] = []

    for path in public_docs:
        text = path.read_text(encoding="utf-8")
        image_targets = [match.group(1) for match in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", text)]
        link_targets = [match.group(1) for match in re.finditer(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text)]
        for target in image_targets + link_targets:
            local_target = target.split("#", 1)[0].strip()
            if (
                not local_target
                or re.match(r"^[a-z][a-z0-9+.-]*:", local_target)
                or local_target.startswith("/")
            ):
                continue
            resolved = (path.parent / local_target).resolve()
            if not resolved.exists():
                missing.append((str(path), target))

    assert missing == []


def test_public_docs_only_reference_existing_make_targets():
    targets = _makefile_targets()
    docs = [Path("README.md"), Path("ROADMAP.md"), Path("PRODUCT_SPEC.md"), *Path("docs").glob("*.md")]
    missing: list[tuple[str, str]] = []

    for path in docs:
        text = path.read_text(encoding="utf-8")
        command_surfaces = re.findall(r"`([^`]*\bmake\s+[^`]*)`", text)
        command_surfaces.extend(match.group(1) for match in re.finditer(r"```(?:bash|text)?\n(.*?)```", text, flags=re.DOTALL))
        for surface in command_surfaces:
            for match in re.finditer(r"\bmake\s+([A-Za-z0-9_.-]+)", surface):
                target = match.group(1).rstrip(".,;:)")
                if target not in targets:
                    missing.append((str(path), target))

    assert missing == []


def test_public_docs_prose_does_not_accidentally_look_like_make_commands():
    docs = [Path("README.md"), Path("ROADMAP.md"), Path("PRODUCT_SPEC.md"), *Path("docs").glob("*.md")]
    suspicious: list[tuple[str, str]] = []

    for path in docs:
        text = path.read_text(encoding="utf-8")
        code_ranges = [(match.start(), match.end()) for match in re.finditer(r"`[^`]*`|```.*?```", text, flags=re.DOTALL)]
        for match in re.finditer(r"\bmake\s+([a-z][a-z-]+)", text):
            if any(start <= match.start() < end for start, end in code_ranges):
                continue
            target = match.group(1)
            if target not in {"the", "clear", "decisions", "risk", "unsupported"}:
                continue
            suspicious.append((str(path), match.group(0)))

    assert suspicious == []


def test_sample_stock_reports_explain_methodology_and_use_current_research_boundary():
    for report_name in ("a.md", "meta.md", "nvda.md", "qqq.md", "smh.md", "apld.md"):
        report = Path("outputs/stock_reports", report_name).read_text(encoding="utf-8")
        assert "Single-Stock Research Report" in report
        assert "## At A Glance" in report
        assert "## Evaluation Snapshot" in report
        assert "## Best Review Path" in report
        assert report.index("## At A Glance") < report.index("## How To Read This Report")
        assert (
            report.index("## At A Glance")
            < report.index("## Evaluation Snapshot")
            < report.index("## Best Review Path")
            < report.index("## How To Read This Report")
        )
        assert "- Mode:" in report
        assert "- Decision view:" in report
        assert "- DCF:" in report
        assert "- Peer context:" in report
        assert "- Optional context:" in report
        assert "- Method: project readiness gates decide what can appear" in report
        assert any(
            method_boundary in report
            for method_boundary in (
                "discounted terminal value, cash/debt adjustment, and fair value per share when ready",
                "DCF formula output is withheld until trusted price, fundamentals, cash-flow or margin, share-count, and DCF fields pass readiness",
                "monitor reports use local price, market, liquidity, correlation, or theme context and exclude operating-company valuation methods",
            )
        )
        assert "- Next local step:" in report
        assert "## Analysis Quality" in report
        assert "## Methodology" in report
        assert "## Evaluation Function Check" in report
        assert "## Copyable Proof Commands" in report
        assert "Copy-only: these are local research commands to copy when you choose" in report
        assert "the report does not run imports or refreshes and does not connect to external accounts" in report
        assert "## Copyable Proof Commands" in report.split("## Source Readiness Check")[0]
        assert "readiness gate first, supported analysis second, valuation math third, explanation last" in report
        assert "Input boundary: local or provider-assisted rows supply data; project rules decide readiness, calculations, blockers, and report wording" in report
        assert "DCF formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value" in report
        assert "Score boundary: setup, watchlist, confidence, and monthly scores are triage aids" in report
        assert "not price targets, expected returns, or allocation instructions" in report
        assert "missing fields are not inferred" in report
        assert "copyable command only" in report
        assert "Local CSV-backed research data" not in report
        assert "T00:00:00" not in report
        if report_name != "apld.md":
            assert "Saved local research data" in report
        assert "Broken" not in report
        assert "Avoid" not in report
        assert "not_ready" not in report
        assert "monitor_context" not in report
        assert "peer_data_unavailable" not in report
        assert "insufficient_data" not in report
        assert "method=fcf_direct" not in report
        assert "DCF assumptions and sensitivity; DCF assumptions and sensitivity" not in report
        assert "method=revenue_fcf_margin" not in report
        assert "Price ready: True" not in report
        assert "Price ready: False" not in report
        assert "Earnings ready: False" not in report
        assert "Analyst estimates ready: False" not in report
        assert re.search(r"(?<!`)Run make\s+[A-Za-z0-9_.-]+", report) is None
        assert re.search(r"(?<!`)run make\s+[A-Za-z0-9_.-]+", report) is None
        assert "final state: Ignore" not in report
        assert "current state is Ignore" not in report
        for raw_field in (
            "EPSGrowth",
            "GrossMargin",
            "DebtToEquity",
            "ForwardPE",
            "EVToSales",
            "EVToEBITDA",
            "PriceToFCF",
            "FCFYield",
            "shares_outstanding",
            "free_cash_flow",
            "fcf_margin",
            "market_cap_or_price_and_shares",
            "reason_not_ready",
            "missing_dcf_fields",
            "market_direction",
        ):
            assert raw_field not in report
        assert "transaction execution" not in report.lower()
        assert "trade instruction" not in report.lower()
        assert "preview-first local import workflows" in report
        assert "staged import workflows" not in report


def test_methodology_doc_explains_formulas_limits_and_code_paths():
    methodology = Path("docs/METHODOLOGY.md").read_text(encoding="utf-8")

    for phrase in (
        "Base FCF = free_cash_flow",
        "Terminal value = Terminal FCF / (WACC - terminal growth)",
        "Fair value per share = Equity value / shares outstanding",
        "Valuation status is a gate, not a recommendation",
        "Scores And Ranking Context",
        "setup scores, watchlist scores, data-confidence scores, and monthly",
        "Scores are not:",
        "Price targets",
        "Expected returns",
        "Portfolio weights",
        "Buy/sell/hold recommendations",
        "converted into a weak score-based conclusion",
        "outputs/undervalued_candidates.csv",
        "valuation-readiness and",
        "not an automatic undervalued-stock list",
        "not_ready",
        "meaning not enough trusted data exists for valuation",
        "`insufficient_data`, meaning the valuation is intentionally blocked until trusted inputs exist",
        "What Is Data Versus App Method",
        "The product separates source inputs from analysis rules so the report is not a black box",
        "Third-party or optional provider data can supply rows, but it does not decide the research conclusion",
        "How This Compares To Standard Research Workflows",
        "The product follows a familiar equity-research sequence, but keeps each step visible and gated",
        "Standard research step",
        "Intrinsic valuation",
        "Relative valuation",
        "A free-cash-flow DCF with visible scenario assumptions, WACC, terminal growth, and sensitivity",
        "Peer valuation from guessed relationships, sector fallback, or incomplete peer metrics",
        "Compared with a professional research terminal or analyst model, this project is intentionally narrower",
        "the same project code checks data readiness, runs DCF math only when inputs exist",
        "Fundamental review is therefore a validation-and-interpretation layer",
        "DCF output is treated as scenario math, not a price target",
        "Conservative DCF Normalization",
        "It is a transparent guardrail inside `src/valuation.py`",
        "Observed revenue growth above the conservative start-growth cap is capped before projection",
        "Projected early-year FCF growth can be capped even after the revenue-growth path is built",
        "Observed FCF margin above the conservative margin cap is capped before projection",
        "Normalized long-term growth is kept below WACC, and terminal growth must remain below WACC",
        "These warnings are part of the model audit trail",
        "not that the product guessed missing data or changed source inputs",
        "Data confidence follows the same principle",
        "Data Confidence And Decision Scores",
        "Data confidence is a data-quality and review-routing signal, not investment conviction",
        "Data readiness score =",
        "(ready features + 0.45 * partial features) / ready-or-partial-or-blocked features",
        "0.80 or higher",
        "0.55 to below 0.80",
        "0.25 to below 0.55",
        "Data confidence is capped by decision bucket",
        "Blocked by Data",
        "Stays low even if some partial context exists",
        "an ETF/index monitor row can have low or medium data confidence for monitoring while DCF stays excluded",
        "When a company ticker has the full trusted local input stack",
        "At A Glance status: mode, decision view, DCF state, peer context, optional context, method cue, and next local step",
        "Best Review Path: tells the reader whether to review DCF and peers",
        "Evaluation Snapshot: summarizes supported evaluation, valuation boundary, data-confidence cue, next proof step, and stop rule before the detailed sections",
        "The report should be read top-down: visitor scan cue first, At A Glance second, Reader Guide third, Evaluation Snapshot fourth, Proof Checklist fifth",
        "copyable local proof commands next",
        "the report does not run imports or refreshes and does not connect to external accounts",
        "At A Glance mode, method cue, and next local step",
        "Evaluation Snapshot for supported evaluation, valuation boundary, data-confidence cue, next proof, and stop rule",
        "Best Review Path for the safest reading order and proof step",
        "Price, momentum, liquidity, and market-context review",
        "Standalone DCF assumptions, bear/base/bull scenario values, and sensitivity context",
        "Peer trend or peer valuation context only when source-backed peer inputs are ready",
        "Copyable local commands for optional context, peer review, or source-readiness checks",
        "When any part of that stack is missing, only the supported sections appear",
        "local command path for inspecting or proving that input",
        "Readiness Proof Ladder",
        "The product uses the same readiness proof ladder in the dashboard, single-stock reports, and Data Health review lists",
        "Price-ready does not mean fundamentals-ready",
        "Fundamentals-ready does not mean DCF-ready unless all required DCF fields pass",
        "DCF-ready does not mean peer-ready",
        "Peer-ready does not mean earnings or analyst estimates are available",
        "blocked rows must not be labeled undervalued, overvalued, DCF-ready, peer-ready, or optional-context-ready",
        "operating-company DCF and peer valuation are excluded, not failed",
        "`make focus-fundamentals TICKER=NVDA`",
        "`make focus-peers TICKER=A`",
        "`data/imports/fundamentals.csv`",
        "`data/imports/peers.csv`",
        "`make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch>`, then `make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch>`; apply only after validation passes, preview scope is intended, and rejected rows are zero",
        "they show the first trustworthy proof step instead of hiding the gap behind a weak conclusion",
        "Where This Lives In Code",
        "`src/readiness_engine.py`",
        "`src/dcf_readiness.py`",
        "`src/valuation.py`",
        "`src/stock_report.py`",
        "not hidden in a model prompt",
    ):
        assert phrase in methodology


def test_roadmap_keeps_active_plan_separate_from_completed_product_history():
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    completed = Path("docs/COMPLETED_MILESTONES.md").read_text(encoding="utf-8")

    for phrase in (
        "Single-stock report mode with readiness, methodology, source readiness check",
        "Public-facing methodology documentation",
        "Public README/dashboard polish",
        "`make stock-report-md TICKER=...` generates clean Markdown reports for visitor demos",
        "`make stock-report TICKER=...` remains available when optional report data is useful for inspection",
        "Reports show readiness, Evaluation Snapshot, Proof Checklist, Best Review Path, analysis quality, methodology, evaluation function checks",
        "ETF/index/fund reports show operating-company DCF as excluded, not failed",
        "`Blocked by Data - Missing Peer Mapping`",
    ):
        assert phrase in completed

    for phrase in (
        "## Now",
        "## Next",
        "## Externally blocked",
        "## Later",
        "## Completed with evidence",
        "### P0: Performance Release Candidate",
        "### P1 local prerequisite: Hosted operating contracts",
        "### P1 local prerequisite: Independent beta protocol",
        "`hosted_account_and_controls_required`",
        "`independent_reviewers_required`",
    ):
        assert phrase in roadmap

    completed = roadmap.index("## Completed with evidence")
    assert completed < roadmap.index("### P0: Performance Release Candidate")
    assert roadmap.index("## Externally blocked") < completed


def test_roadmap_routes_exhausted_proof_queues_to_provider_setup_before_candidate_loops():
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")

    assert "Provider setup/source-boundary review" in roadmap
    assert "`make provider-setup-checklist`" in roadmap
    assert "current source-proof queues have no unreviewed executable company candidates" in roadmap
    assert "`make trusted-data-pilot-candidates TOP_N=10` only after" in roadmap
    assert roadmap.index("Provider setup/source-boundary review") < roadmap.index(
        "`make trusted-data-pilot-candidates TOP_N=10` only after"
    )

    assert "### B. Single Stock Research Mode\n\nGoal: produce a data-honest single-ticker research report" not in roadmap
    assert "- Add ticker search in the dashboard." not in roadmap
    assert "`make price-refresh-loop BATCHES=... TOP_N=... PROVIDER=auto`" not in roadmap


def test_completed_milestones_record_latest_command_visibility_simplification():
    completed = Path("docs/COMPLETED_MILESTONES.md").read_text(encoding="utf-8")

    assert "Data Health Command Visibility Sweep V1" in completed
    assert "Proof History, Operator context, and Pilot Share Gate detail summaries" in completed
    assert "hide command snippets by default" in completed
    assert "explicit packet command table remains available" in completed


def test_product_spec_keeps_execution_features_permanently_out_of_scope():
    spec = Path("PRODUCT_SPEC.md").read_text(encoding="utf-8")

    for phrase in (
        "## Current Product Surfaces",
        "`Home`: workflow question, one primary next action, stop rule, and then readiness context before deeper counts or examples",
        "`Stock Selector`: readiness-backed queue with the next reading path before filters, plus selected-ticker handoff into one report or Data Health proof",
        "`Single-Stock Report`: ticker-level visitor scan cue, At A Glance status, Reader Guide, Evaluation Snapshot, Proof Checklist, Best Review Path, data-confidence cue, methodology cue, analysis quality, valuation state, source readiness check, and read-only proof steps",
        "`Data Health`: one lane answer first, then trusted local data paths, import validation, rejected-row reports, and proof review paths behind public/advanced or operator detail",
        "`Proof History`: evidence-only page for reviewed outcomes; it does not refresh data, apply imports, or unlock blocked inputs",
        "Markdown reports under `outputs/stock_reports/`",
        "richer company, standalone DCF, price/setup gated, monitor-only, and blocked-data modes",
        "Home workflow start -> Stock Selector -> Single-Stock Report -> Data Health lane answer -> Proof History evidence",
        "Broad-universe tables, command blocks, route maps, and proof ledgers should stay filtered, row-limited, collapsed, or operator-scoped by default",
        "## Public Share Definition",
        "the README has a short demo path and dashboard preview",
        "sample reports show a visitor scan cue, `At A Glance`, `Reader Guide`, `Evaluation Snapshot`, `Proof Checklist`, `Best Review Path`, data-confidence cues, methodology, evaluation function checks, source readiness, and read-only proof steps",
        "project code provides readiness gates, DCF math, peer boundaries, and report wording",
        "`make public-check` passes",
        "generated CSV/JSON churn is reviewed before staging and is not committed by default",
        "## Future Research Enhancements Not Implemented Yet",
        "Paid or licensed data-provider integrations for trusted research inputs",
        "Full SEC financial-statement modeling beyond preview-first fundamentals imports",
        "Full market-scale background job scheduling for local refresh/import workflows",
        "Automated peer suggestions only when clearly labeled as fallback",
        "## Permanently Out Of Scope",
        "Broker connections",
        "Automated order routing",
        "Auto-trading",
        "Direct buy/sell/hold recommendations",
        "Options trade recommendations",
        "Fabricated prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or research conclusions",
    ):
        assert phrase in spec

    future_section = spec.split("## Future Research Enhancements Not Implemented Yet", 1)[1].split("## Permanently Out Of Scope", 1)[0]
    for forbidden in (
        "Broker connections",
        "Automated order routing",
        "Auto-trading",
        "Direct buy/sell/hold recommendations",
        "Options trade recommendations",
    ):
        assert forbidden not in future_section


def test_operator_guide_is_command_focused_and_research_only():
    guide = Path("docs/OPERATOR_GUIDE.md").read_text(encoding="utf-8")

    for phrase in (
        "Data readiness first",
        "Analysis second",
        "Research decision last",
        "does not connect to brokers",
        "make pipeline",
        "make readiness",
        "make project-status",
        "make stock-report-md TICKER=NVDA",
        "make stock-report-md TICKER=A",
        "make stock-report-md TICKER=META",
        "make stock-report-md TICKER=QQQ",
        "make stock-report-md TICKER=SMH",
        "make stock-report-md TICKER=APLD",
        "For public demos, prefer `make stock-report-md TICKER=NVDA`.",
        "Use `make stock-report TICKER=NVDA` only when you want the optional local report data for inspection.",
        "make dashboard",
        "make dashboard-smoke",
        "Open the Home page `Example reports` section to compare richer company, standalone DCF, price/setup gated, monitor-only, and blocked-data examples",
        "make price-history-proof-queue TOP_N=10",
        "make focus-fundamentals TICKER=NVDA",
        "make peer-mapping-queue TOP_N=10",
        "make optional-context-worklist TOP_N=10",
        "make imports-validate",
        "make imports-preview",
        "make imports-apply",
        "make price-refresh-loop DRY_RUN=1",
        "make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto SLEEP_SECONDS=30",
        "make readiness-snapshot",
        "make diff-hygiene",
        "snapshot readiness, then run one capped loop",
        "Read the visitor scan cue first, then `At A Glance`",
        "At A Glance",
        "Best Review Path",
        "method cue",
        "Analysis Quality",
        "Methodology",
        "DCF formula path",
        "The At A Glance method cue and the `Methodology` section show the DCF formula path",
        "For local import files, use preview before apply",
        "Evaluation Function Check",
        "Copyable Proof Commands",
        "does not run imports or refreshes and does not connect to external accounts",
        "ready, blocked, excluded, or optional",
        "Analysis Modes",
        "DCF-ready review",
        "Standalone DCF review",
        "Price/setup review only",
        "Monitor-only context",
        "Data needed before analysis",
        "Large refreshed CSVs are local working data",
        "set `MAX_CANDIDATES` to the approximate number of missing-price rows you want to cover",
        "docs/analysis_capability_audit.md",
        "What Powers The Analysis",
        "shipped analysis comes from project code under `src/`",
        "Support tools and libraries are not the stock-analysis rules",
        "shipped readiness gates, valuation gates",
    ):
        assert phrase in guide
    assert "META` demonstrates company-level analysis where peer context is still locked" not in guide
    assert "For local import draft workflows" not in guide
    assert "For local import drafts, use preview before apply" not in guide
    assert "make price-refresh-loop BATCHES=5 TOP_N=100 PROVIDER=auto SLEEP_SECONDS=30" not in guide
    first_run = guide.split("## First Local Run", 1)[1].split("## What To Open First", 1)[0]
    assert "Open the guided product first" in first_run
    assert first_run.index("make demo") < first_run.index("make dashboard")
    assert first_run.index("make dashboard") < first_run.index("make status-check TOP_N=5")
    assert first_run.index("make status-check TOP_N=5") < first_run.index("make project-status")
    assert first_run.index("make project-status") < first_run.index("make stock-report-md TICKER=NVDA")
    assert "Inspect readiness impact after changing reviewed source data or imports" in first_run
    rebuild_section = first_run.split(
        "Inspect readiness impact after changing reviewed source data or imports; do not regenerate tracked release artifacts through a composite command:", 1
    )[1]
    assert rebuild_section.index("make pipeline") < rebuild_section.index("make readiness-preview")
    assert rebuild_section.index("make readiness-preview") < rebuild_section.index("make project-status-check")
    assert "make readiness\n" not in rebuild_section

    for forbidden in (
        "buy recommendation",
        "sell recommendation",
        "auto-trading system",
        "hidden investing engine",
    ):
        assert forbidden not in guide.lower()


def test_public_release_docs_point_to_operator_guide_without_stale_future_copy():
    checklist = Path("docs/PUBLIC_RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    audit = Path("docs/public_cleanup_audit.md").read_text(encoding="utf-8")
    diff_audit = Path("docs/DIFF_HYGIENE_AUDIT.md").read_text(encoding="utf-8")

    assert "docs/OPERATOR_GUIDE.md" in checklist
    assert "docs/DATA_STRATEGY.md" in checklist
    assert "docs/LICENSE_DECISION_GUIDE.md" in checklist
    assert "docs/DIFF_HYGIENE_AUDIT.md" in checklist
    assert "portfolio/demo project" in checklist
    assert "deeper local workflow guide" in checklist
    assert "dashboard `Data Health` page visible as the safe freshness guide" in checklist
    assert "read-only routine first, capped price dry-run before real refreshes" in checklist
    assert "review-required lanes for fundamentals, peers, earnings, and analyst estimates" in checklist
    assert "not told to manually refresh the full universe every day" in checklist
    assert "lane-specific freshness and generated-data hygiene" in checklist
    assert "Keep the primary product flow near the top" in checklist
    assert "then Research Desk -> Discover -> Company Workbench -> Monitor" in checklist
    assert "Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History as the secondary controlled Public demo" in checklist
    assert "Keep terminal proof commands secondary" in checklist
    assert "make stock-report-md TICKER=NVDA" in checklist
    assert "make trusted-data-pilot-candidates TOP_N=10" in checklist
    assert "make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1" in checklist
    assert "make provider-setup-checklist" in checklist
    checklist_commands = checklist.split("make public-release-handoff", 1)[1].split("make stock-report-md TICKER=NVDA", 1)[0]
    assert checklist_commands.index("make project-status-check") < checklist_commands.index("make provider-setup-checklist")
    assert checklist_commands.index("make provider-setup-checklist") < checklist_commands.index(
        "make trusted-data-pilot-candidates TOP_N=10"
    )
    assert "default candidate output stays compact for visitors" in checklist
    assert "make trusted-data-pilot-packet TICKER=CRDO" in checklist
    assert "make trusted-data-pilot TICKERS=<chosen names> TOP_N=10" in checklist
    assert "only after `make project-status-check` shows executable company candidates" in checklist
    assert "If project-status-check says current source-proof queues are exhausted" in checklist
    assert "start with `make provider-setup-checklist` instead" in checklist
    assert "choose 5-10 operating companies only when source proof exists" in checklist
    assert "file presence, row counts, staged-folder counts, or rejected-row report existence are not proof" in checklist
    assert "source review, validation, preview, apply boundary, readiness rebuild, and the regenerated report prove the lane changed" in checklist
    assert "define a useful pilot win as before report, lane review, trusted source row" in checklist
    assert "Suggested starter set: `NVDA,AVGO,AMD,MU,CRDO,COHR,LITE,HOOD,TSLA,META`" in checklist
    assert "Treat `QQQ` and `SMH` as ETF/index monitor demos" in checklist
    assert "Keep the pilot evidence packet visible" in checklist
    assert "before report, review path, validate/preview gate, apply boundary, rejected-row, and rebuild-proof packet" in checklist
    assert "baseline readiness, before report, focused blocker check, lane review path" in checklist
    assert "validate/preview gate, apply boundary, rejected-row check, rebuild proof" in checklist
    assert "prefer `make stock-report-md` for LinkedIn/GitHub visitors" in checklist
    assert "`At A Glance`, `Reader Guide`, `Evaluation Snapshot`, `Proof Checklist`, `Best Review Path`, `Analysis Quality`, `Methodology`, `Evaluation Function Check`, and `Copyable Proof Commands`" in checklist
    assert "small pilot" in checklist
    assert "After it passes, run `make public-release-package`" in checklist
    assert "compact package" in checklist
    assert "branch status" in checklist
    assert "staged inspection commands" in checklist
    assert "exact terminal" in checklist
    assert "make browser-qa-capture-plan" in checklist
    assert "make public-release-handoff" in checklist
    assert "make diff-hygiene-files" in checklist
    assert "make staged-hygiene-check" in checklist
    assert "git diff --cached --check" in checklist
    assert "git diff --cached --name-only" in checklist
    assert "outputs/staging/" in checklist
    assert "git add --pathspec-from-file=..." in checklist
    assert "local review next steps" in diff_audit
    assert "operator next steps" not in diff_audit
    assert "safe staging" in checklist
    assert "generated CSV/JSON churn" in checklist
    assert "new `docs/`, `scripts/`, and `tests/` files" in checklist
    assert "changed and new file counts" in diff_audit
    assert "make diff-hygiene-files" in diff_audit
    assert "make staged-hygiene-check" in diff_audit
    assert "outputs/staging/product_files.txt" in diff_audit
    assert "outputs/staging/product_plus_reports.txt" in diff_audit
    assert "outputs/staging/README.txt" in diff_audit
    assert "package status" in diff_audit
    assert "New files under `docs/`" in diff_audit
    assert "`scripts/`, and `tests/` are treated as product candidates" in diff_audit
    for demo_command in (
        "make demo",
        "make stock-report-md TICKER=APLD",
        "make stock-report-md TICKER=NVDA",
        "make stock-report-md TICKER=A",
        "make stock-report-md TICKER=META",
        "make stock-report-md TICKER=QQQ",
        "make stock-report-md TICKER=SMH",
    ):
        assert demo_command in checklist

    for phrase in (
        "Public Release Hygiene",
        "Visitor Experience",
        "Data Hygiene",
        "License Decision",
        "Methodology And Trust",
        "Public Wording",
        "Verification Before Sharing",
        "docs/OPERATOR_GUIDE.md",
        "docs/METHODOLOGY.md",
        "docs/LICENSE_DECISION_GUIDE.md",
            "public reuse rights are intentionally restricted",
        "timestamp-only churn",
        "Research-only; no broker integration or order execution.",
        "make dashboard-smoke",
            "make demo",
            "make public-check",
            "make stock-report-md TICKER=NVDA",
            "git diff --check",
    ):
        assert phrase in audit

    assert "AGENTS.md" not in audit
    assert ".agents" not in audit
    assert "internal agent" not in audit.lower()
    assert "may benefit from a separate `docs/OPERATOR_GUIDE.md` later" not in audit
    assert "Whether to create a separate `docs/OPERATOR_GUIDE.md`" not in audit

    for phrase in (
        "Do not stage broad refreshed local data",
        "data/prices.csv",
        "outputs/*.csv",
        "small Markdown sample reports only",
        "make dashboard-smoke",
        "make demo",
        "make public-check",
    ):
        assert phrase in diff_audit


def test_public_docs_avoid_machine_readable_first_read_copy():
    public_docs = {
        "README.md": Path("README.md").read_text(encoding="utf-8"),
        "docs/OPERATOR_GUIDE.md": Path("docs/OPERATOR_GUIDE.md").read_text(encoding="utf-8"),
        "docs/PUBLIC_RELEASE_CHECKLIST.md": Path("docs/PUBLIC_RELEASE_CHECKLIST.md").read_text(encoding="utf-8"),
    }

    for path, text in public_docs.items():
        assert "machine-readable" not in text, path


def test_readme_points_to_pilot_share_brief_for_concise_public_handoff():
    readme = Path("README.md").read_text(encoding="utf-8")
    data_strategy = Path("docs/DATA_STRATEGY.md").read_text(encoding="utf-8")
    public_release = Path("docs/PUBLIC_RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    assert "make pilot-share-brief" in readme
    assert "concise public/demo share brief" in readme
    assert "does not refresh data or unlock blocked inputs" in readme
    for doc in (data_strategy, public_release):
        assert "make pilot-share-brief" in doc
        assert "outputs/pilot_share_brief.md" in doc
        assert "does not refresh data" in doc
    assert "advanced evidence details" in data_strategy
    assert "without stitching together raw tables" not in data_strategy
    assert "without scanning raw tables first" not in data_strategy


def test_license_decision_guide_names_current_controlled_demo_license():
    guide = Path("docs/LICENSE_DECISION_GUIDE.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    release_checklist = Path("docs/PUBLIC_RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    assert Path("LICENSE").exists()
    assert "Controlled Portfolio Demo License" in Path("LICENSE").read_text(encoding="utf-8")
    for phrase in (
        "root `LICENSE` with controlled portfolio-demo terms",
        "Current path: controlled portfolio/demo evaluation",
        "Controlled portfolio showcase",
        "Do not claim the project is open source unless `LICENSE` is replaced",
    ):
        assert phrase in guide
    assert "controlled portfolio-demo license" in readme
    assert "copying, redistribution, sublicensing, hosted reuse" in readme
    assert "make license-status" in readme
    assert "make license-status" in release_checklist
    assert "MIT License" not in readme
    assert "Apache License" not in readme


def test_license_status_launcher_prints_current_share_boundary():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "license-status" in makefile
    assert "license-status:\n\t@python3 -m src.license_status --root ." in makefile
    assert "make license-status" in makefile
    assert "Print the read-only license/reuse gate before public sharing" in makefile

    result = subprocess.run(
        ["make", "license-status"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "License Status" in result.stdout
    assert "share_status: controlled_demo_license" in result.stdout
    assert "next_decision: confirm_readme_license_wording" in result.stdout
    assert "next_safe_command: docs/LICENSE_DECISION_GUIDE.md" in result.stdout
    assert "do not describe as open source or reusable software" in result.stdout


def test_public_check_runs_license_status_before_sharing():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    public_check = makefile.split("public-check:", 1)[1].split("\ntest:", 1)[0]

    assert 'Public share check: license boundary' in public_check
    assert "$(MAKE) --silent license-status" in public_check


def test_stock_report_cli_data_unlock_fallback_uses_product_language():
    source = Path("src/stock_report.py").read_text(encoding="utf-8")

    assert "Data-needed Markdown report:" in source
    assert "First blocker to resolve:" in source
    assert "Readiness-only Markdown report:" not in source
    assert "Full stock report blocked:" not in source


def test_linkedin_project_brief_uses_current_demo_path_and_analysis_quality():
    brief = Path("docs/LINKEDIN_PROJECT_BRIEF.md").read_text(encoding="utf-8")

    for phrase in (
        "Stock Research Command Center | Evidence-First Company Research",
        "local Python and Streamlit portfolio beta for evidence-first company research",
        "Research Desk -> Discover -> Company Workbench -> Monitor",
        "Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History",
        "what evidence can be used now",
        "keep unsupported conclusions withheld",
        "Data Health and Proof History remain available",
        "real Workbench answer-first screenshot",
        "screenshots are product evidence only",
        "stable GitHub repository link only after this reviewed feature reaches the default branch",
        "Draft engineering preview",
        "Operator details stay collapsed until someone intentionally leaves the public path.",
        "The first story is company research, not operator automation.",
        "reviewed batch packets, provider setup, validate / preview / apply mechanics",
        "Use the reviewed `docs/assets/linkedin-public-dashboard.png` Workbench thumbnail",
        "no broker integration, no order routing, no auto-trading, and no direct buy/sell instructions",
        "local portfolio beta, not a hosted product or market-validated service",
        "Run `make project-status-check` first and use `make provider-setup-checklist` when source-proof queues are exhausted.",
        "Do not run trusted-data pilot queues as a LinkedIn demo talking point unless project-status-check shows executable source-backed candidates.",
        "Keep lane-level operator views, coverage frontier details, reviewed batch packets, and validate / preview / apply guidance as follow-up context after the public workflow is clear.",
        "one-company evidence packet",
        "source evidence, and a rebuilt report",
        "leave the rest visibly blocked by missing data until trusted rows exist",
        "docs/DATA_STRATEGY.md",
        "docs/analysis_capability_audit.md",
        "outputs/stock_reports/nvda.md",
        "outputs/stock_reports/a.md",
        "outputs/stock_reports/meta.md",
        "outputs/stock_reports/qqq.md",
        "outputs/stock_reports/smh.md",
        "outputs/stock_reports/apld.md",
        "research-only",
        "does not connect to a broker or place trades",
        "README example map",
        "click the tracked sample reports under `outputs/stock_reports/`",
        "make status-check TOP_N=5",
        "read-only command-center summary without refreshing local artifacts",
        "exact copyable local commands for the next proof step",
        "Readiness-first local stock research dashboard for source-gated analysis workflows",
        "`python`, `research-tool`, `streamlit`, `data-readiness`, `equity-research`, `stock-research`",
    ):
        assert phrase in brief

    assert "readiness counts" not in brief.lower()
    assert "CSV-first staged import workflows" not in brief
    assert "staged import validation" not in brief
    linkedin_demo_talking_points = brief.split("## Demo Talking Points", 1)[1]
    assert "make trusted-data-pilot-candidates TOP_N=10" not in linkedin_demo_talking_points
    assert "make trusted-data-pilot-packet TICKER=CRDO" not in linkedin_demo_talking_points
    assert "make trusted-data-pilot TICKERS=<chosen names> TOP_N=10" not in linkedin_demo_talking_points
    assert "investment advice" in brief


def test_dashboard_qa_records_latest_public_flow_browser_check():
    qa = Path("docs/DASHBOARD_QA.md").read_text(encoding="utf-8")

    for phrase in (
        "Current Screenshot Evidence Status",
        "`docs/assets/linkedin-public-dashboard.png`",
        "`docs/assets/public-demo-home-real.jpg`",
        "`docs/assets/operator-data-health-metrics-real.jpg`",
        "`docs/assets/single-stock-workflow-fit-real.jpg`",
        "`docs/assets/operator-data-health-proof-real.jpg`",
        "`docs/assets/operator-data-health-queue-routing-real.jpg`",
        "Screenshot evidence is product evidence only",
        "2026-06-07 Public Product Flow Pass",
        "`Stock Selector`, `Single-Stock Report`, `Data Health`, and `Proof History`",
        "trusted-data pilot path for improving 5-10 companies first",
        "`At A Glance`, `Reader Guide`, `Evaluation Snapshot`, `Proof Checklist`, then `Best Review Path`",
        "routes the DCF/peer-ready `NVDA` example to review DCF, peers, and source readiness",
        "2026-06-07 Follow-Up Product Copy Pass",
        "2026-06-10 Public Navigation And Data Strategy Pass",
        "2026-06-10 Trusted Pilot Candidate UX Pass",
        "2026-06-11 Public Route Alignment Pass",
        "main navigation control reads `Choose your path`",
        "`Stock Selector`, `Single-Stock Report`, `Data Health`, and `Proof History`",
        "detailed pages remain available under `Optional research views`",
        "Automation Boundary table separates repeatable checks from human-reviewed source judgment",
        "demo walkthrough points visitors to `make project-status-check` first",
        "`make provider-setup-checklist` when source-proof queues are exhausted",
        "candidate list available only when executable company candidates exist",
        "Portfolio Review: confirmed the page renders plain-language capability and limit cards",
        "checklist/review-path language before advanced command detail",
        "broad valuation input count is labeled separately from exact company DCF-ready counts",
        "`next-step context` instead of internal-tool operational wording",
        "prints a company starter set and separates `QQQ` / `SMH` as ETF/index monitor examples",
        "standalone DCF peer wording no longer repeats `DCF assumptions and sensitivity`",
        "Product Tour routes `Proof History` to the Proof History route",
        "Proof History: evidence for changed states",
        "generated Monthly Picks CSV remains local working output",
        "2026-06-11 Visitor Guide Browser Pass",
        "Monthly Picks: confirmed the page renders the new `Reader Guide`",
        "`Open a one-stock report next`, `No automatic conclusion`",
        "Single-Stock Report: confirmed the page renders the demo ticker guide",
        "`NVDA`, `META`, `QQQ`, `MU`, `CRDO`, plus optional `A`, `SMH`, and `APLD`",
        "Trusted Data Pilot CLI: confirmed candidate output no longer repeats the `Decision gate` label",
        "Monthly candidate guidance stays a research queue, not a recommendation list.",
        "2026-06-11 Data Health Freshness Routine Pass",
        "Data Health: confirmed the `Freshness Routine` section explains a read-only daily/opening routine",
        "quick read`, `fix first`, and `trusted-data pilot",
        "Refresh and command details",
        "price freshness guidance starts with a capped dry-run command",
        "fundamentals, peer mappings, earnings, and analyst estimates remain review-required lanes",
        "does not claim new fundamentals, peer, earnings, or analyst-estimate coverage",
        "Commands remain copy-only",
        "No generated CSV/JSON churn was published with the UI copy pass",
        "2026-06-11 Trusted Pilot Compact Output Pass",
        "`make trusted-data-pilot-candidates TOP_N=10` prints a compact visitor-friendly shortlist",
        "`make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1` remains available for local proof detail",
        "file status, decision gates, rejected-row paths, and evidence expectations",
        "README, Data Strategy, Public Release Checklist, LinkedIn brief, and `make demo`",
        "compact default points to one-company evidence packets before validate/preview gate, apply boundary, and rebuild proof",
        "The compact candidate command is read-only",
        "`VERBOSE=1` exposes local proof detail only",
    ):
        assert phrase in qa


def test_analysis_capability_audit_is_public_and_data_honest():
    audit = Path("docs/analysis_capability_audit.md").read_text(encoding="utf-8")

    for phrase in (
        "What Is Strong Today",
        "Plain Answer",
        "Function Quality Matrix",
        "What Is Intentionally Limited",
        "Methodology And Provenance",
        "Support Tooling Boundary",
        "Input-To-Output Contract",
        "At A Glance status",
        "Reader Guide near the top",
        "Evaluation Snapshot",
        "Best Review Path",
        "read-only proof steps",
        "Reader Guide near the top, Evaluation Snapshot near the top, Proof Checklist next",
        "read-only missing-data proof steps",
        "Supported-Today Assessment",
        "Methodology visibility",
        "Methodology and explanation",
        "docs/METHODOLOGY.md",
        "base FCF, projected FCF, discounted cash flows plus discounted terminal value",
        "filling the gap with an inferred value",
        "Analysis Modes",
        "DCF-ready review",
        "Standalone DCF review",
        "Price/setup review only",
        "Monitor-only context",
        "Data needed before analysis",
        "Standard Python packages support data handling, UI, tests, and optional provider access",
        "Readiness gates",
        "Fundamentals and DCF",
        "Peer comparison",
        "ETF/index monitor context",
        "Single-stock report",
        "Quality verdict",
        "Best use today",
        "Strong today",
        "Good for DCF-ready companies only",
        "Ready when peer data exists",
        "Support layer, not analysis rules",
        "What it refuses to do",
        "src/valuation.py",
        "src/readiness_engine.py",
        "pyproject.toml",
        "`numpy`",
        "`pandas`",
        "`PyYAML`",
        "`streamlit`",
        "`yfinance`",
        "`pytest`",
        "Optional unofficial research-grade data adapter",
        "not a wrapper around external investing services",
        "dependencies support the workflow",
        "they are not the analysis rules",
        "Support Tooling Boundary",
        "Support tools and libraries are outside the stock-analysis rules",
        "not embedded valuation rules",
        "recommendation rules",
        "public product should be judged by the files in this repository",
        "local or provider-assisted data supplies rows",
        "does not import a third-party analyst opinion",
        "Validate whether each feature is `ready`, `partial`, `blocked`, or `excluded`",
        "Reduce data confidence or withhold sections when required inputs are missing",
        "full-data company can show fundamentals, DCF assumptions, sensitivity, and peer context",
        "not yet a full-market data platform",
    ):
        assert phrase in audit
    for forbidden in ("place orders", "connect to brokers", "auto-trade", "direct buy/sell"):
        assert forbidden not in audit.lower()
    assert "Open-source Python packages support data handling" not in audit


def test_package_metadata_matches_public_research_only_positioning():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    for phrase in (
        'name = "stock-research-command-center"',
        "CSV-first, research-only stock command center",
        "readiness gates",
        "single-stock reports",
        "transparent valuation blockers",
        'keywords = ["stocks", "research", "streamlit", "readiness", "valuation", "csv"]',
        "[project.urls]",
        'Repository = "https://github.com/YuzeJ21/Stock-Analysis"',
    ):
        assert phrase in pyproject

    assert "license =" not in pyproject
    assert "github.com/davidjiang8888" not in pyproject
    assert "broker" not in pyproject.lower()
    assert "trading" not in pyproject.lower()


def test_legacy_stock_analysis_scaffold_is_not_published():
    publishable_legacy_files = [
        path
        for path in Path("stock_analysis").rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and not path.name.endswith((".pyc", ".pyo"))
    ]
    assert publishable_legacy_files == []

    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'packages = ["src", "src.providers"]' in pyproject
    assert "stock_analysis" not in pyproject


def test_decision_output_model_matches_current_evaluation_contract():
    model = Path("DECISION_OUTPUT_MODEL.md").read_text(encoding="utf-8")

    for phrase in (
        "decision_subtype",
        "primary_blocker",
        "next_best_action",
        "readiness_score",
        "data_confidence",
        "evaluation_status",
        "purpose_fit",
        "setup_quality",
        "valuation_view",
        "risk_view",
        "missing_data_summary",
        "next_research_step",
        "source_freshness_summary",
        "feature_summary",
        "Current Review Details",
        "Research Candidate - DCF Ready But Peer Blocked",
        "Research Candidate - Optional Context Locked",
        "Monitor - ETF Market Proxy",
        "Monitor - Price/Momentum Ready",
        "Blocked by Data - Missing Price",
        "Blocked by Data - Missing Fundamentals",
        "Blocked by Data - Missing Peer Mapping",
        "Excluded - DCF Not Applicable",
        "Confidence And Scores",
        "Scores must not be displayed as price targets, expected returns, or direct",
        "Base score",
        "CompositeScore",
        "review-order or confidence aid only",
        "ETF/index/fund rows must show DCF as excluded",
    ):
        assert phrase in model


def test_readiness_model_documents_peer_layers_and_snapshot_history():
    model = Path("READINESS_MODEL.md").read_text(encoding="utf-8")

    for phrase in (
        "Peer Readiness Layers",
        "peer_price_ready",
        "peer_momentum_ready",
        "peer_fundamentals_ready",
        "peer_valuation_ready",
        "peer_trend_comparison_ready",
        "peer_valuation_comparison_ready",
        "peer_dcf_comparison_ready",
        "Peer trend comparison may appear before peer valuation",
        "Peer valuation must stay blocked when peer fundamentals or valuation inputs are missing",
        "Sector or industry fallback context must be labeled as fallback",
        "Readiness Snapshot History",
        "make readiness-snapshot",
        "data/reports/ticker_readiness_report.previous.csv",
        "current-only baseline instead of fake deltas",
        "valuation-readiness context in legacy `undervalued_candidates.csv`",
    ):
        assert phrase in model


def test_dashboard_advanced_commands_recommend_dry_run_before_refresh():
    dashboard = Path("src/dashboard.py").read_text(encoding="utf-8")
    dry_run_index = dashboard.index("make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto")

    assert dry_run_index >= 0
    assert "make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto SLEEP_SECONDS=30" not in dashboard
    assert "Inspect broad refresh changes before committing or sharing them publicly" in dashboard
    assert "broad refresh churn should be inspected before it is committed or shared publicly" not in dashboard
    assert "Open Review" in dashboard
    assert "Build Local Report Preview" not in dashboard
    assert "Show Report Preview" not in dashboard
    assert "Generate Local Stock Report" not in dashboard
    assert "Online lookup (off by default)" in dashboard
    assert "Online data check (optional)" not in dashboard
    assert "Use research-grade online data" not in dashboard
    assert "Show data source details" in dashboard
    assert "Show source readiness details" not in dashboard
    assert "Show report source details" not in dashboard
    assert "Download Audit Data" in dashboard
    assert "Download Structured Report" not in dashboard
    assert "Download Report Data" not in dashboard
    assert "Download Report Data (JSON)" not in dashboard
    assert "technical context" not in dashboard.lower()
    assert "trend and risk context" in dashboard
    assert "Analysis mode guide." in dashboard
    assert "At A Glance" in dashboard
    assert "stock_report_at_a_glance_cards(" in dashboard
    assert "stock_report_mode_guide_cards(report_payload)" in dashboard
    assert "Project calculations in src/indicators.py and src/momentum_engine.py." in dashboard
    assert "Project calculations in src/report_generator.py and dashboard helpers." not in dashboard
    assert "Developer detail: raw report JSON" not in dashboard
    assert "Show advanced report data (JSON)" not in dashboard
    assert "Use optional online data" not in dashboard
    assert "Current local readiness for the next research review." in dashboard
    assert "Local stock research dashboard" not in dashboard
    assert "names checked" in dashboard
    assert "CSV-first research cockpit" not in dashboard
    assert "stocks checked" not in dashboard
    assert "Current operator focus" in dashboard
    assert "One supported local path before opening secondary status and route details." in dashboard
    assert "operator path" not in dashboard
    assert "Local file checklist" in dashboard
    assert "Local generated file checklist" not in dashboard
    assert "Next Steps" in dashboard
    assert "Next Action Console" not in dashboard
    assert "local file changes" in dashboard
    assert "generated-data churn" not in dashboard


def test_stock_report_cli_help_uses_readable_report_language():
    source = Path("src/stock_report.py").read_text(encoding="utf-8")

    assert "Generate a readable local single-stock research report." in source
    assert "optional report data" in source
    assert "structured stock report" not in source
    assert "structured report data" not in source
    assert "full JSON payload" not in source

def test_readme_preserves_research_only_guardrails_and_preview_first_imports():
    readme = Path("README.md").read_text(encoding="utf-8")
    operator_guide = Path("docs/OPERATOR_GUIDE.md").read_text(encoding="utf-8")
    data_strategy = Path("docs/DATA_STRATEGY.md").read_text(encoding="utf-8")

    assert "Research-Only Guardrails" in readme
    assert "not a trading system" in readme
    assert "docs/DATA_STRATEGY.md" in operator_guide
    assert "Public Visitor FAQ" in data_strategy
    assert "The product analysis comes from this repository's readiness gates, DCF calculations, peer gates, decision buckets, and report wording." in data_strategy
    assert "Local or provider-assisted rows supply inputs; they do not decide valuation status, data confidence, peer readiness, or research state." in data_strategy
    assert "Prices are the safest lane to refresh at scale because they are repeatable time-series rows" in data_strategy
    assert "Fundamentals, peer mappings, earnings, and analyst estimates are judgment-required lanes" in data_strategy
    assert "Missing trusted rows are a product signal." in data_strategy
    assert "Do not try to turn the full universe into analysis-ready rows at once" in data_strategy
    assert "make trusted-data-pilot-candidates TOP_N=10" in data_strategy
    assert "run `make project-status-check` first" in data_strategy
    assert "Only run `make trusted-data-pilot-candidates TOP_N=10` when project-status-check shows executable company candidates" in data_strategy
    assert "run `make provider-setup-checklist` instead" in data_strategy
    assert "make universe-scope TICKERS=NVDA,ACIC TOP_N=10" in readme
    assert "make risk-context" in readme
    assert "make universe-scope TICKERS=NVDA,META TOP_N=10" in data_strategy
    assert "make risk-context" in data_strategy
    assert "active, ticker-list, sector/theme, ready-only, and missing-data scopes" in data_strategy
    assert "liquidity, correlation, and proxy-risk readiness" in data_strategy
    assert "make trusted-data-pilot-candidates TOP_N=10 VERBOSE=1" in data_strategy
    assert "default candidate output is compact" in data_strategy
    assert "row-level proof detail" in data_strategy
    assert "one plain-language lane answer first" in data_strategy
    assert "review one stock, improve data coverage, and inspect proof" not in data_strategy
    assert "review one stock, check data coverage, and inspect proof" not in data_strategy
    assert "three simple paths" not in data_strategy
    assert "row-level diagnostic" not in data_strategy
    assert "make trusted-data-pilot-packet TICKER=CRDO" in data_strategy
    assert "make trusted-data-pilot TOP_N=10" in data_strategy
    assert "rejected-row report path, rebuild proof, and evidence row to record" in data_strategy
    assert "Suggested company pilot: `NVDA,AVGO,AMD,MU,CRDO,COHR,LITE,HOOD,TSLA,META`" in data_strategy
    assert "ETF/index examples such as `QQQ` and `SMH` are useful monitor-context demos" in data_strategy
    assert "One-company evidence packet:" in data_strategy
    assert "make trusted-data-pilot-packet TICKER=<ticker>" in data_strategy
    assert "make stock-report-md TICKER=<ticker>" in data_strategy
    assert "Run the lane-specific review command printed by the packet:" in data_strategy
    assert "fundamentals lane: make focus-fundamentals TICKER=<ticker>" in data_strategy
    assert "peer lane: make focus-peers TICKER=<ticker>" in data_strategy
    assert "make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>" in data_strategy
    assert "make imports-apply IMPORT_TICKERS=<ticker> only after validation passes, preview scope is intended, rejected rows are zero" in data_strategy
    assert "Check the rejected-row report printed by the packet before treating the lane as available." in data_strategy
    assert "Run the matching in-memory readiness comparison after the reviewed source step:" in data_strategy
    assert "readiness impact: make readiness-preview TOP_N=20" in data_strategy
    assert "batch comparison: make reviewed-batch-compare PROFILE=<default|demo|local>" in data_strategy
    assert "fundamentals lane: make dcf-readiness" in data_strategy
    assert "peer lane: make peer-mapping-queue TOP_N=25" in data_strategy
    assert "lane review path, validate/preview gate, apply boundary, rejected-row report path, rebuild proof, and evidence row to record" in data_strategy
    assert "The candidate list and one-company packet also print local file status" in data_strategy
    assert "A file with rows is not automatically trusted coverage" in data_strategy
    assert "Every pilot packet follows the same proof loop" in data_strategy
    assert "snapshot the baseline, generate the before report, review the source proof for the missing lane" in data_strategy
    assert "Only the rebuilt report can prove a lane changed" in data_strategy
    assert "keep the blocker visible and move to the next candidate" in data_strategy
    assert "Read each pilot outcome in durable states:" in data_strategy
    assert "`supported`, `still_blocked`, `skipped`, or `excluded`" in data_strategy
    assert "| Supported | Rebuilt readiness and the regenerated report show the lane is ready. |" in data_strategy
    assert "| Still blocked | Validation failed, rejected rows appeared, or the report stayed locked; keep the named blocker visible. |" in data_strategy
    assert "| Skip | Source proof is unavailable or not reviewable; do not apply placeholder rows, and move to the next shortlisted company. |" in data_strategy
    assert "rejected-row report path, then the relevant readiness proof command" in data_strategy
    assert "does not refresh, import, or edit local CSV files" in data_strategy
    assert "provider-assisted rows are optional inputs" in data_strategy
    assert "Provider-assisted does not mean provider-decided" in data_strategy
    assert "Automation Boundary" in data_strategy
    assert "The product can automate repeatable checks, but it should not automate source judgment." in data_strategy
    assert "Dry-run planning, capped refresh loops, import normalization, validation, readiness rebuilds." in data_strategy
    assert "Freshness Without Daily Manual Work" in data_strategy
    assert "You do not need to hand-refresh every ticker every day for the product to stay useful." in data_strategy
    assert "Treat freshness as a lane-specific review workflow" in data_strategy
    assert "Run status/readiness checks whenever you open the project" in data_strategy
    assert "use capped refresh loops only when coverage is stale or too short for the next research page" in data_strategy
    assert "Only run a real capped price loop after reviewing the dry-run plan." in data_strategy
    assert "Do not schedule unattended fundamentals, peer, earnings, estimate imports, or public commits." in data_strategy
    assert "Whether a source row is trusted, which fiscal period is appropriate, and whether manual fundamentals should be applied." in data_strategy
    assert "Which companies are real peers and whether any fallback sector/industry context is acceptable as context only." in data_strategy
    assert "If a workflow depends on source credibility, issuer judgment, fiscal-period choice, peer selection, or optional provider licensing" in data_strategy
    assert "Safe Overnight Automation" in data_strategy
    assert "keep the job in review mode by default" in data_strategy
    assert "Run `make price-refresh-loop DRY_RUN=1` to produce a capped price-refresh plan without changing local files." in data_strategy
    assert "Do not run unattended jobs that apply fundamentals, peer mappings, earnings, analyst estimates, or public commits." in data_strategy
    assert "make price-history-proof-queue TOP_N=10" in data_strategy
    assert "then preview any broader update with `make price-refresh-loop DRY_RUN=1`" in data_strategy
    assert "Pilot Evidence Checklist" in data_strategy
    assert "A company is a useful pilot win only when the evidence is reviewable, not just when a CSV row exists." in data_strategy
    assert "Keep a before/after readiness count from `make readiness-snapshot PROFILE=<default|demo|local>` and `make reviewed-batch-compare PROFILE=<default|demo|local> ...`" in data_strategy
    assert "Keep one regenerated Markdown report per pilot company" in data_strategy
    assert "Keep the exact review and validation path that changed the state" in data_strategy
    assert "Record local file status from the pilot output, but do not treat row counts or file existence as proof by themselves." in data_strategy
    assert "Peer-limited companies show the mapped peer blocker and the exact source-backed peer input needed next." in data_strategy
    assert "The final proof is a regenerated report plus refreshed readiness counts, recorded alongside any still-blocked reason" in data_strategy
    assert "Reviewed Data Proof V1" in data_strategy
    assert "Use `make reviewed-data-proof` to show the durable lane-level proof ledger" in data_strategy
    assert "source proof status, reviewer outcome, validate/preview/apply result, rejected-row status, readiness before/after" in data_strategy
    assert "Use `make lane-outcome-history` to summarize lane outcomes over time from the reviewed proof ledger." in data_strategy
    assert "Use `make reviewed-data-proof-record` only after the source proof, validation, preview, rejected-row review, apply step, and readiness proof have been reviewed." in data_strategy
    assert "Use `make price-reviewed-run` after a dry-run plan has been reviewed." in data_strategy
    assert "Use `make public-demo-readiness-pack` or open `docs/PUBLIC_DEMO_READINESS_PACK.md`" in data_strategy
    assert "scope selection, risk context, Data Health lane board, one ready report, one blocked report, and one excluded/monitor example" in data_strategy
    assert "Data Health also surfaces the latest reviewed proof timeline" in data_strategy
    assert "Reviewed Batch Execution V1" in data_strategy
    assert "Use `DRY_RUN=1 make reviewed-batch LANE=prices TOP_N=10` to preview a frontier lane as a reviewed run packet without writing packet artifacts." in data_strategy
    assert "The packet includes the pre-run readiness snapshot command, dry-run command, capped execution command, validate/preview/apply gates" in data_strategy
    assert "the packet must stop at `make readiness-preview TOP_N=20`" in data_strategy
    assert "creates an optional ignored local package only" in data_strategy
    assert "does not update the tracked 18-file release candidate" in data_strategy
    assert "Use `make data-release-decision` after any reviewed batch or local refresh creates dirty CSV/report artifacts." in data_strategy
    assert "It separates three choices: keep generated artifacts local for working evidence, publish a reviewed data snapshot only when those exact artifacts are the deliverable, or clean back to a public code/docs release state." in data_strategy
    assert "Keep the public branch clean with `make diff-hygiene`" in data_strategy
    assert "Applying SEC/manual fundamentals rows without validation and preview" in data_strategy
    assert "Peer relationships inferred only from sector labels" in data_strategy
    for phrase in (
        "place orders",
        "connect to brokers",
        "auto-trade",
        "recommend option trades",
        "provide direct buy/sell instructions",
        "fabricate prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or recommendations",
    ):
        assert phrase in readme
    for phrase in (
        "make templates",
        "make imports-validate",
        "make imports-preview",
        "make imports-apply",
    ):
        assert phrase in operator_guide


def test_public_demo_readiness_pack_uses_live_proof_commands_not_stale_snapshot():
    pack = Path("docs/PUBLIC_DEMO_READINESS_PACK.md").read_text(encoding="utf-8")

    assert "Start with the product flow before opening operator proof commands" in pack
    assert "Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History" in pack
    assert "Visitor workflow | `make dashboard` then follow Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History" in pack
    assert "operator evidence; they do not refresh data, unlock blocked inputs, or replace the public workflow" in pack
    assert "Current proof timeline" in pack
    assert "Use `make reviewed-data-proof`" in pack
    assert "Use `make reviewed-batch-proof`" in pack
    assert "does not refresh data" in pack
    assert "Latest reviewed proof: `RDP-" not in pack


def test_product_facing_status_labels_avoid_action_language():
    public_paths = [
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("PRODUCT_SPEC.md"),
        Path("READINESS_MODEL.md"),
        Path("DECISION_OUTPUT_MODEL.md"),
        *Path("docs").glob("*.md"),
        *Path("outputs/stock_reports").glob("*.md"),
        Path("src/momentum_engine.py"),
        Path("src/monthly_picks.py"),
        Path("src/portfolio_review.py"),
        Path("src/state_machine.py"),
        Path("src/dashboard.py"),
    ]
    forbidden_labels = ("Buyable Area", "Pullback Add Candidate", "Add Candidate", "Hold but Do Not Add")

    for path in public_paths:
        text = path.read_text(encoding="utf-8")
        for label in forbidden_labels:
            assert label not in text, f"{path} still exposes action-sounding label {label!r}"

    dashboard = Path("src/dashboard.py").read_text(encoding="utf-8")
    assert "Research Ready" in dashboard
    for retired_action_label in ("Pullback Review Candidate", "Constructive Review", "Hold Review Only"):
        assert retired_action_label not in dashboard


def test_generated_product_outputs_use_current_import_draft_language():
    committed_generated_paths = [
        Path("outputs/research_decisions.csv"),
        Path("outputs/peer_unlock_worklist.csv"),
        Path("data/outputs/research_decisions.csv"),
        *Path("outputs/stock_reports").glob("*.md"),
    ]
    local_generated_paths = [
        Path("outputs/command_bundle_runbook.csv"),
        Path("outputs/project_status_next_steps.csv"),
        Path("outputs/project_status_top_actions.csv"),
    ]
    generated_paths = committed_generated_paths + [path for path in local_generated_paths if path.exists()]
    stale_phrases = (
        "Import staged price rows",
        "staged price rows",
        "staged imports",
        "staged local workflow",
        "staged local data",
        "staged price import",
        "Advance staged",
        "live staged",
        "full JSON payload",
        "technical context",
    )

    for path in committed_generated_paths:
        assert path.exists(), f"{path} is missing"

    for path in generated_paths:
        text = path.read_text(encoding="utf-8")
        for phrase in stale_phrases:
            assert phrase not in text, f"{path} still contains stale generated wording {phrase!r}"


def test_public_docs_do_not_reference_stale_github_or_internal_thread_links():
    public_paths = [
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("PRODUCT_SPEC.md"),
        Path("READINESS_MODEL.md"),
        Path("DECISION_OUTPUT_MODEL.md"),
        *Path("docs").glob("*.md"),
        *Path("outputs/stock_reports").glob("*.md"),
    ]
    forbidden = (
        "github.com/davidjiang8888",
        "davidjiang8888/Stock-Analysis",
        "pull/1",
        "Draft PR",
        "codex/market-command-center-roadmap-sync",
        "/Users/",
        "Documents/New project",
        "yjian070",
        "AGENTS.md",
        ".agents",
        "docs/CODEX_SKILLS_OVERVIEW.md",
        "Codex thread",
        "goal prompt",
    )

    for path in public_paths:
        text = path.read_text(encoding="utf-8")
        for phrase in forbidden:
            assert phrase not in text, f"{path} still references stale/internal link text {phrase!r}"

    linkedin_brief = Path("docs/LINKEDIN_PROJECT_BRIEF.md").read_text(encoding="utf-8")
    assert "https://github.com/YuzeJ21/Stock-Analysis" in linkedin_brief
    assert "Run `make project-status-check` first and use `make provider-setup-checklist` when source-proof queues are exhausted." in linkedin_brief
    assert "Do not run trusted-data pilot queues as a LinkedIn demo talking point unless project-status-check shows executable source-backed candidates." in linkedin_brief
    linkedin_demo_talking_points = linkedin_brief.split("## Demo Talking Points", 1)[1]
    assert "make trusted-data-pilot-candidates TOP_N=10" not in linkedin_demo_talking_points
    assert "make trusted-data-pilot-packet TICKER=CRDO" not in linkedin_demo_talking_points
    assert "make trusted-data-pilot TICKERS=<chosen names> TOP_N=10" not in linkedin_demo_talking_points


def test_shell_launchers_anchor_to_repo_root():
    for script_name in ("daily.sh", "dashboard.sh", "validate_all.sh", "smoke_dashboard.sh"):
        script = (Path("scripts") / script_name).read_text(encoding="utf-8")
        assert "set -euo pipefail" in script
        assert "REPO_ROOT" in script
        assert 'cd "${REPO_ROOT}"' in script
        assert 'echo "Repo root: ${REPO_ROOT}"' in script


def test_dashboard_smoke_launcher_checks_streamlit_health_safely():
    script = Path("scripts/smoke_dashboard.sh").read_text(encoding="utf-8")

    assert "_stcore/health" in script
    assert "SERVER_PID" in script
    assert "trap cleanup EXIT" in script
    assert "Operation not permitted" in script
    assert "Couldn't connect to server" in script
    assert "Uvicorn server started" in script
    assert "_bind_socket" in script
    assert "environment-limited pass" in script


def test_validate_all_reuses_current_verification_targets():
    script = Path("scripts/validate_all.sh").read_text(encoding="utf-8")

    assert "make verify" in script
    assert "make data-sources-check" in script
    assert "make dashboard-smoke" in script
    assert "make monthly" not in script
    assert "make track-record" not in script
    assert "--write-output" not in script
    assert "price-refresh" not in script
    assert "python3 -m pytest tests -q" not in script
    assert "python3 -m src.data_sources --check" not in script


def test_daily_launcher_reuses_current_make_targets():
    script = Path("scripts/daily.sh").read_text(encoding="utf-8")

    make_commands = [line.strip() for line in script.splitlines() if line.startswith("make ")]
    assert make_commands == ["make daily"]
    assert "python3 -m src.data_update --universe-file data/universe.csv" not in script
    assert "python3 -m src.report_generator" not in script


def test_makefile_verify_and_daily_targets_reuse_shared_make_workflows():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "profile-context:\n\t@python3 -m src.profile_context --root ." in makefile
    assert "research-change-snapshot:" in makefile
    assert "research-change-monitor:" in makefile
    assert "research-review-queue:" in makefile
    assert "research-event-review-record:" in makefile
    assert "thesis-journal:" in makefile
    assert "thesis-journal-preview:" in makefile
    assert "thesis-journal-record:" in makefile
    journal = makefile.split("thesis-journal:", 1)[1].split("help-full:", 1)[0]
    assert "src.research_thesis_journal" in journal
    assert "--confirm-reviewed" in journal
    assert "git add" not in journal
    assert "git commit" not in journal
    assert "git push" not in journal
    monitor = makefile.split("research-change-monitor:", 1)[1].split("research-review-queue:", 1)[0]
    assert "imports-apply" not in monitor
    assert "git add" not in monitor
    assert "git push" not in monitor

    assert "status:\n\t$(NO_WRITE_GUARD) python3 -m src.project_status --check --top-n $(or $(TOP_N),5)" in makefile
    assert "status-check:\n\tpython3 -m src.project_status --check --top-n $(or $(TOP_N),5) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "coverage:\n\tpython3 -m src.data_onboarding --coverage $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "data-wizard:\n\tpython3 -m src.data_onboarding --wizard $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "unlock-ladder:\n\tpython3 -m src.data_onboarding --unlock-ladder $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "unlock-summary:\n\tpython3 -m src.data_onboarding --unlock-summary $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "command-bundles:\n\tpython3 -m src.data_onboarding --command-bundles $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "command-bundle-details:\n\tpython3 -m src.data_onboarding --command-bundle-details $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "command-bundle-runbook:\n\tpython3 -m src.data_onboarding --command-bundle-runbook $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "bundle-fundamentals:\n\tpython3 -m src.data_onboarding --command-bundles --lane fundamentals --holdings-only $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "detail-peers:\n\tpython3 -m src.data_onboarding --command-bundle-details --lane peers --holdings-only $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "runbook-prices-broader:\n\tpython3 -m src.data_onboarding --command-bundle-runbook --lane prices --scope broader_queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "focus-price:\nifndef TICKER\n\t$(error TICKER is required, for example: make focus-price TICKER=AMD)\nendif\n\tpython3 -m src.price_history_proof_queue --top-n 1 --tickers $(TICKER)\n\nfocus-fundamentals:" in makefile
    focus_price_block = makefile[makefile.index("focus-price:"):makefile.index("focus-fundamentals:")]
    assert "--command-bundle-details --lane prices" not in focus_price_block
    assert "--command-bundle-runbook --lane prices" not in focus_price_block
    focus_fundamentals_block = makefile[
        makefile.index("focus-fundamentals:"):makefile.index("focus-peers:")
    ]
    assert "python3 -m src.dcf_input_proof_queue --top-n 1 --tickers $(TICKER)" in focus_fundamentals_block
    assert "--command-bundle-details --lane fundamentals" not in focus_fundamentals_block
    assert "--command-bundle-runbook --lane fundamentals" not in focus_fundamentals_block
    focus_peers_block = makefile[makefile.index("focus-peers:"):makefile.index("\nonboarding:")]
    assert "python3 -m src.data_onboarding --peer-mapping-queue --top-n 1 --tickers $(TICKER)" in focus_peers_block
    assert "--command-bundle-details --lane peers" not in focus_peers_block
    assert "--command-bundle-runbook --lane peers" not in focus_peers_block
    assert "price-worklist:\n\tpython3 -m src.data_onboarding --price-worklist $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "fundamentals-peer-worklist:\n\tpython3 -m src.data_onboarding --fundamentals-peer-worklist $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "optional-context-worklist:\n\tpython3 -m src.data_onboarding --optional-context-worklist $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "sec-stage-queue:\n\tpython3 -m src.data_onboarding --sec-stage-queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "peer-mapping-queue:\n\tpython3 -m src.data_onboarding --peer-mapping-queue $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    trusted_data_pilot = _make_target_block(makefile, "trusted-data-pilot")
    assert 'case "$(PROFILE)" in default|demo|local)' in trusted_data_pilot
    assert '@echo "Trusted Data Pilot"' in trusted_data_pilot
    assert "trusted-data-pilot-candidates:\n\t@python3 -m src.trusted_data_pilot --top-n $(or $(TOP_N),10) $(if $(TICKERS),--tickers $(TICKERS),) $(if $(filter 1 true TRUE yes YES,$(VERBOSE)),--verbose,)" in makefile
    assert "pilot-share-brief:\n\t@python3 -m src.pilot_readiness --profile \"$(or $(PROFILE),default)\" --share-brief --top-n $(or $(TOP_N),10) $(if $(OUTPUT),--output \"$(OUTPUT)\",)" in makefile
    assert "trusted-data-pilot-packet:\nifndef TICKER\n\t$(error TICKER is required, for example: make trusted-data-pilot-packet TICKER=CRDO)\nendif\n\t@python3 -m src.trusted_data_pilot --packet $(TICKER)" in makefile
    assert "DEFAULT_TRUSTED_PILOT_TICKERS := MU,CRDO,HOOD,TSLA,META,A,APLD" in makefile
    assert "DEFAULT_TRUSTED_PILOT_EVIDENCE_TICKERS := MU,CRDO" in makefile
    assert "trusted-data-pilot-lane:\nifndef LANE\n\t$(error LANE is required, for example: make trusted-data-pilot-lane LANE=fundamentals_dcf)\nendif\n\t@python3 -m src.trusted_data_pilot --lane $(LANE) --tickers $(if $(TICKERS),$(TICKERS),$(DEFAULT_TRUSTED_PILOT_TICKERS)) --top-n $(or $(TOP_N),10)" in makefile
    assert "trusted-data-pilot-board:\n\t@python3 -m src.trusted_data_pilot --tickers $(if $(TICKERS),$(TICKERS),$(DEFAULT_TRUSTED_PILOT_TICKERS)) --top-n $(or $(TOP_N),10) --board" in makefile
    assert "trusted-data-pilot-evidence:\n\t@python3 -m src.trusted_data_pilot --tickers $(if $(TICKERS),$(TICKERS),$(DEFAULT_TRUSTED_PILOT_EVIDENCE_TICKERS)) --top-n $(or $(TOP_N),10) --write-evidence $(or $(OUTPUT),outputs/trusted_data_pilot_evidence.csv)" in makefile
    assert "reviewed-data-proof:\n\t@python3 -m src.reviewed_data_proof --ledger $(or $(LEDGER),data/reviewed_data_proofs.csv)" in makefile
    assert "lane-outcome-history:\n\t@python3 -m src.reviewed_data_proof --ledger $(or $(LEDGER),data/reviewed_data_proofs.csv) --history" in makefile
    assert "price-reviewed-run:\n\t@python3 -m src.reviewed_data_proof --price-reviewed-run --max-candidates $(or $(MAX_CANDIDATES),3500) --top-n $(or $(TOP_N),100) --provider $(or $(PROVIDER),auto) --sleep-seconds $(or $(SLEEP_SECONDS),30)" in makefile
    assert "public-demo-readiness-pack:\n\t@python3 -m src.reviewed_data_proof --ledger $(or $(LEDGER),data/reviewed_data_proofs.csv) --public-demo-pack" in makefile
    assert "readiness-ops-center:\n\t@python3 -m src.readiness_ops --root ." in makefile
    assert "coverage-frontier:\n\t@python3 -m src.readiness_ops --root . --coverage-frontier --top-n $(or $(TOP_N),10)" in makefile
    assert "data-coverage-planner:\n\t@python3 -m src.readiness_ops --root . --expansion-plan --top-n $(or $(TOP_N),10)" in makefile
    assert "coverage-expansion-loop:\n\t@python3 -m src.coverage_expansion_loop --root . --lane $(or $(LANE),auto) --top-n $(or $(TOP_N),10)" in makefile
    assert "readiness-ops-evidence:\n\t@python3 -m src.readiness_ops --root . --evidence --top-n $(or $(TOP_N),10)" in makefile
    assert "reviewed-batch:\n\t@python3 -m src.reviewed_batch --root . --profile $(or $(PROFILE),default) --lane $(or $(LANE),prices) --top-n $(or $(TOP_N),10)" in makefile
    assert "reviewed-batch-proof:\n\t@python3 -m src.reviewed_batch_proof --ledger $(or $(LEDGER),data/reviewed_batch_proofs.csv)" in makefile
    assert "reviewed-batch-compare:\nifndef PROFILE\n\t$(error PROFILE is required: default, demo, or local)\nendif" in makefile
    assert 'src.readiness_comparison --root . --profile "$(PROFILE)"' in makefile
    assert "reviewed-batch-preflight:\n\t@python3 -m src.reviewed_batch_preflight --root ." in makefile
    assert "reviewed-batch-proof-record:\nifndef BATCH_ID" in makefile
    assert "$(error FINAL_OUTCOME is required: supported, auto_supported, human_reviewed_supported, candidate_context_only, still_blocked, skipped, or excluded)" in makefile
    assert "auto-refresh-plan:\n\t@python3 -m src.auto_refresh_orchestrator --root . --schedule all" in makefile
    assert "auto-refresh-runbook:\n\t@python3 -m src.auto_refresh_orchestrator --root . --schedule $(or $(SCHEDULE),daily) --runbook" in makefile
    assert "auto-refresh-status:\n\t@python3 -m src.auto_refresh_orchestrator --root . --schedule $(or $(SCHEDULE),daily) --status" in makefile
    assert "auto-apply-gate:\n\t@python3 -m src.auto_refresh_orchestrator --root ." in makefile
    assert "reviewed-data-proof-record:\nifndef LANE" in makefile
    assert "Read-only guide: this target prints commands only. It does not refresh prices, import rows, edit CSVs, or change readiness outputs." in makefile
    assert "Check whether price coverage can be improved safely" in makefile
    assert "Suggested company pilot: $(if $(TICKERS),$(TICKERS),NVDA,AVGO,AMD,MU,CRDO,COHR,LITE,HOOD,TSLA,META)" in makefile
    assert "ETF/index examples such as QQQ and SMH are monitor-context demos, not operating-company DCF targets." in makefile
    assert "Ticker-scoped example: make trusted-data-pilot TICKERS=NVDA,AVGO,AMD,MU,CRDO TOP_N=10" in makefile
    assert "Candidate list: make trusted-data-pilot-candidates TOP_N=10" in makefile
    assert "Status gate: make project-status-check before choosing candidate tickers" in makefile
    assert "Candidate list: make trusted-data-pilot-candidates TOP_N=10 only when project-status-check shows executable company candidates" in makefile
    assert "Company-by-company loop: open one report, choose the matching lane, then validate trusted rows before reading any new valuation." in makefile
    assert "Starter loop example: make stock-report-md TICKER=CRDO -> make trusted-data-pilot-packet TICKER=CRDO -> run the packet's lane-specific review command" in makefile
    assert "Pilot proof target: each company should end with a regenerated report showing ready, locked, or excluded sections from current local evidence." in makefile
    assert "Evidence bundle: keep the before/after readiness count, one regenerated Markdown report, the exact review, validate/preview gate, apply boundary, rejected-row report, and proof commands that changed the state." in makefile
    assert "SEC credential state: SEC_USER_AGENT is configured for local staging checks." in makefile
    assert "SEC credential state: SEC_USER_AGENT is not configured; use manual trusted fundamentals or stop at diagnostics." in makefile
    assert "Evidence table columns to record: ticker | before_mode | after_mode | outcome_state | changed_inputs | validation_commands | report_path | still_blocked_reason." in makefile
    assert "Stop condition: if trusted source rows are unavailable, do not fill placeholders; leave the ticker visibly blocked by missing data and record the missing input." in makefile
    assert "Pilot evidence packet: baseline readiness, before report, focused blocker check, lane review path, validate/preview gate, apply boundary, rejected-row check, rebuild proof, and still-blocked evidence row." in makefile
    assert "One-company packet example:" in makefile
    assert "make trusted-data-pilot-candidates TOP_N=10" in makefile
    trusted_pilot_target = makefile.split("trusted-data-pilot:", 1)[1].split("trusted-data-pilot-candidates:", 1)[0]
    assert trusted_pilot_target.index("make project-status-check") < trusted_pilot_target.index(
        "make trusted-data-pilot-candidates TOP_N=10"
    )
    assert "make trusted-data-pilot-packet TICKER=<ticker>" in makefile
    assert "make stock-report-md TICKER=<ticker>" in makefile
    assert "Run the lane-specific review command printed by the packet:" in makefile
    assert "fundamentals lane: make focus-fundamentals TICKER=<ticker>" in makefile
    assert "peer lane: make focus-peers TICKER=<ticker>" in makefile
    assert "make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>" in makefile
    assert "make imports-apply IMPORT_TICKERS=<ticker> only after validation passes, preview scope is intended, rejected rows are zero" in makefile
    assert "Use the broad imports-apply sequence only after every staged row is source-reviewed and intended." in makefile
    assert "ifndef IMPORT_TICKERS\nifndef ALLOW_BROAD_IMPORT_APPLY" in makefile
    assert "$(error IMPORT_TICKERS is required for imports-apply; use ALLOW_BROAD_IMPORT_APPLY=1 only after full staged-scope review)" in makefile
    assert "Check the rejected-row report printed by the packet before treating the lane as available." in makefile
    assert "Run the matching in-memory comparison proof:" in makefile
    assert "fundamentals lane: make dcf-readiness && make reviewed-batch-compare PROFILE=$(PROFILE) LANE=fundamentals" in makefile
    assert "peer lane: make reviewed-batch-compare PROFILE=$(PROFILE) LANE=peers" in makefile
    assert "If SEC staging is not configured or source rows are not ready, stop at diagnostics and keep the ticker visibly blocked by missing data." in makefile
    assert "Add peers only when you have source-backed relationships; sector/industry fallback is context, not trusted peer valuation." in makefile
    assert "Stage only intentional docs/code/tests or reviewed sample Markdown reports; keep broad CSV/JSON refresh churn local unless it is the reviewed artifact." in makefile
    assert "make price-worklist $(if $(TICKERS),TICKERS=$(TICKERS) )TOP_N=$(or $(TOP_N),10)" in makefile
    assert "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=$(or $(TOP_N),10) TOP_N=$(or $(TOP_N),10) PROVIDER=auto" in makefile
    assert "Use a real capped price loop only after reviewing the dry run and saving a readiness snapshot." in makefile
    assert "Use trusted fundamentals, peer, earnings, or estimate rows only, then validate before apply" in makefile
    assert "make trusted-data-pilot [TICKERS=NVDA,AVGO,AMD,MU,CRDO] [TOP_N=10] Print a read-only company-focused trusted-data pilot plan" in makefile
    assert "make trusted-data-pilot-candidates [TICKERS=NVDA,CRDO,META] [TOP_N=10] Rank read-only company candidates for the next trusted-data pilot" in makefile
    assert "make trusted-data-pilot-lane LANE=fundamentals_dcf [TICKERS=MU,CRDO,HOOD] [TOP_N=10] Print a read-only lane-group runbook and evidence summary" in makefile
    assert "price-normalize:\nifndef INPUT\n\t$(error INPUT is required, for example: make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=yahoo_manual)\nendif" in makefile
    price_normalize_target = makefile.split("price-normalize:", 1)[1].split("daily:", 1)[0]
    assert '$(if $(SOURCE_REF),--source-ref "$(SOURCE_REF)",)' in price_normalize_target
    assert '$(if $(RETRIEVED_AT),--retrieved-at "$(RETRIEVED_AT)",)' in price_normalize_target
    assert (
        "make price-normalize INPUT=data/raw/prices/NVDA.csv TICKER=NVDA SOURCE=<source_id> "
        "SOURCE_REF=<durable_reference> RETRIEVED_AT=<timezone-aware-timestamp> "
        "AS_OF=<review-cutoff>"
    ) in makefile
    assert "stock-report:\nifndef TICKER\n\t$(error TICKER is required, for example: make stock-report TICKER=NVDA)\nendif\n\tpython3 -m src.stock_report --ticker $(TICKER) --provider $(if $(PROVIDER),$(PROVIDER),local) $(if $(OUTPUT),--output $(OUTPUT),) $(if $(MD_OUTPUT),--markdown-output $(MD_OUTPUT),)" in makefile
    assert "stock-report-md:\nifndef TICKER\n\t$(error TICKER is required, for example: make stock-report-md TICKER=NVDA)\nendif\n\t@python3 -m src.stock_report --ticker $(TICKER) --provider $(if $(PROVIDER),$(PROVIDER),local) --quiet $(if $(MD_OUTPUT),--markdown-output $(MD_OUTPUT),)" in makefile
    assert "local-tickers:\n\tpython3 -m src.stock_report --list-local-tickers" in makefile
    assert "import-staging:\n\tpython3 -m src.stock_report --write-import-staging" in makefile
    assert "data-sources-check:\n\tpython3 -m src.data_sources --check --top-n $(or $(TOP_N),20) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "data-sources:\n\tpython3 -m src.data_sources --write-output" in makefile
    assert "research-health-check:\n\tpython3 -m src.research_health --check --top-n $(or $(TOP_N),20) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert "action-queue-check:\n\tpython3 -m src.action_queue --check --top-n $(or $(TOP_N),20) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert 'session-source-preflight:\n\t@python3 -m src.session_source_preflight --root . --write-output $(if $(SEC_USER_AGENT),--sec-user-agent "$(SEC_USER_AGENT)",)' in makefile
    assert "yfinance-stage:\nifndef TICKERS\n\t$(error TICKERS is required, for example: make yfinance-stage TICKERS=NVDA)\nendif\n\tpython3 -m src.stock_report --yfinance-stage-fundamentals --tickers $(TICKERS)" in makefile
    assert "sec-filing-share-stage:\nifndef TICKERS\n\t$(error TICKERS is required, for example: make sec-filing-share-stage TICKERS=HOOD)\nendif\n\tpython3 -m src.stock_report --sec-filing-share-stage --tickers $(TICKERS)" in makefile
    assert "price-status:\n\tpython3 -m src.data_update --price-status $(if $(TOP_N),--top-n $(TOP_N),) $(if $(TICKERS),--tickers $(TICKERS),)" in makefile
    assert '@echo "Read-only guide: this target prints the external reviewer path only. It does not refresh data, import rows, or rewrite reports."' in makefile
    assert "@echo \"External Reviewer Start Here\"" in makefile
    assert "@echo \"Visitor workflow path:\"" in makefile
    assert "@echo \"   Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History\"" in makefile
    assert "@echo \"   Optional state examples: NVDA DCF/peer ready, ACIC DCF-gated, AACI fundamentals-blocked, QQQ excluded, MU peer-ready\"" in makefile
    assert "@echo \"What this proves: readiness-backed selection comes first, ready data is analyzed, blocked data stays visible, and non-applicable methods are excluded instead of forced.\"" in makefile
    assert "@echo \"Data-confidence note: data confidence describes readiness and review routing, not investment conviction.\"" in makefile
    assert "@echo \"1. Open the README preview and public walkthrough:\"" in makefile
    assert "@echo \"   docs/PUBLIC_DEMO_WALKTHROUGH.md\"" in makefile
    assert "@echo \"2. Open the clean dashboard path:\"" in makefile
    assert "@echo \"   make demo-dashboard\"" in makefile
    assert "@echo \"3. Follow one ticker in the app before using terminal proof:\"" in makefile
    assert "@echo \"   Start with Stock Selector, open NVDA or another readiness-backed row, then use Data Health only if an input is blocked.\"" in makefile
    assert "@echo \"4. Optional current selected-profile readiness and lane truth:\"" in makefile
    assert "@echo \"   make readiness-ops-center\"" in makefile
    assert "@echo \"   Proves: current selected-profile readiness and lane truth without changing local files.\"" in makefile
    assert "@echo \"   make status-check TOP_N=5\"" in makefile
    assert "@echo \"   Saved generated-snapshot counts and blockers only; this context can be stale.\"" in makefile
    assert "@echo \"5. Optional sample reports after the app flow is clear:\"" in makefile
    assert "@echo \"   make stock-report-md TICKER=NVDA  # DCF-ready company example\"" in makefile
    assert "@echo \"   make stock-report-md TICKER=ACIC  # price context with DCF gated\"" in makefile
    assert "@echo \"   make stock-report-md TICKER=QQQ   # ETF/index monitor context\"" in makefile
    assert "@echo \"6. Smoke-test the dashboard:\"" in makefile
    assert "@echo \"   Proves: the Streamlit app can boot and answer its local health check.\"" in makefile
    assert "@echo \"7. If you are asking what to do next:\"" in makefile
    assert "@echo \"   make next-stage\"" in makefile
    assert "@echo \"   Proves: the current package answer, hosted-demo state, provider-key state, source-proof queue status, and decision ladder without refreshing data, importing rows, staging files, pushing, deploying, or exposing secrets.\"" in makefile
    assert "@echo \"Advanced source-proof follow-up, only after project-status says it is executable:\"" in makefile
    assert "@echo \"   make project-status-check\"" in makefile
    assert "@echo \"   make provider-setup-checklist  # use when project-status-check says source-proof queues are exhausted\"" in makefile
    assert "@echo \"   Do not open broad proof queues unless project-status-check shows executable source-backed candidates.\"" in makefile
    demo_block = makefile.split("\ndemo:\n", 1)[1].split("\nbrowser-qa-evidence:", 1)[0]
    assert '@echo "   make provider-setup-checklist  # use when project-status-check says source-proof queues are exhausted"' in demo_block
    assert '@echo "   make trusted-data-pilot-candidates TOP_N=10' not in demo_block
    assert '@echo "   make data-coverage-proof-queues TOP_N=10"' not in demo_block
    assert '@echo "   make universe-scope TICKERS=NVDA,META TOP_N=10"' not in demo_block
    assert '@echo "   make risk-context"' not in demo_block
    assert demo_block.index('@echo "   make project-status-check"') < demo_block.index('@echo "   make provider-setup-checklist  # use when project-status-check says source-proof queues are exhausted"')
    assert "@echo \"Before sharing or committing:\"" in makefile
    assert "@echo \"   make public-check\"" in makefile
    assert "@echo \"   make browser-qa-evidence\"" in makefile
    assert "@echo \"   make diff-hygiene-summary\"" in makefile
    assert "@echo \"   make staged-hygiene-check # after staging, before commit\"" in makefile
    assert 'This target only prints a visitor path. Optional stock-report-md commands write local Markdown reports under outputs/stock_reports/.' in makefile
    assert "Share-safe story: start with the connected workflow, then use NVDA, ACIC, AACI, QQQ, and MU only as optional state examples." in makefile
    assert "diff-hygiene-files:\n\t@python3 scripts/diff_hygiene.py --write-files" in makefile
    assert "data-release-decision:\n\t@python3 scripts/diff_hygiene.py --data-release-decision" in makefile
    assert "public-release-package:\n\t@python3 scripts/diff_hygiene.py --public-release-package" in makefile
    assert "public-release-handoff:\n\t@python3 scripts/diff_hygiene.py --public-release-handoff" in makefile
    assert "staged-hygiene-check:\n\t@python3 scripts/diff_hygiene.py --staged-check" in makefile
    assert "public-check:" in makefile
    for phrase in (
        'Public share check: GitHub sync boundary',
        'Public share check: diff hygiene',
        'Public share check: staged hygiene',
        'Public share check: whitespace',
        'Public share check: tests',
            'Public share check: demo dashboard smoke',
        'Public share check: browser QA evidence',
        'Public share check: visitor demo',
        "@$(MAKE) --silent diff-hygiene-summary",
        "@$(MAKE) --silent staged-hygiene-check",
        "@git diff --check",
        "@$(MAKE) --silent test",
            "@$(MAKE) --silent demo-dashboard-smoke",
        "@$(MAKE) --silent browser-qa-evidence",
        "@$(MAKE) --silent demo",
    ):
        assert phrase in makefile
    assert "@git status --short --branch --untracked-files=no | sed -n '1p'" in makefile
    assert "verify:\n\t$(NO_WRITE_GUARD) $(MAKE) test pipeline validate-data onboarding" in makefile
    assert "daily:\n\t$(NO_WRITE_GUARD) $(MAKE) pipeline validate-data onboarding status-check TOP_N=$(or $(TOP_N),5)" in makefile
    public_check_body = makefile.split("public-check:", 1)[1].split("\n\ntest:", 1)[0]
    assert "price-refresh" not in public_check_body
    assert "imports-apply" not in public_check_body
    assert "pipeline" not in public_check_body
    assert "verify:\n\tpython3 -m pytest tests -q" not in makefile
    assert "daily:\n\tpython3 -m src.data_update --universe-file data/universe.csv" not in makefile


def test_earnings_nowcast_pilot_launcher_is_read_only_and_fixture_explicit():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    section = makefile[makefile.index("earnings-nowcast-pilot:") :]

    assert "python3 -m src.earnings_nowcast_report" in section
    assert "$(if $(FIXTURE),--fixture,)" in section
    assert "imports-apply" not in section


def test_earnings_nowcast_onboarding_launchers_have_no_apply_path():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    for target in (
        "earnings-nowcast-templates",
        "earnings-nowcast-validate",
        "earnings-nowcast-preview",
        "earnings-nowcast-readiness",
        "earnings-nowcast-prospective-plan",
    ):
        assert f"{target}:" in makefile
    section = makefile[makefile.index("earnings-nowcast-templates:") :]
    assert "src.earnings_nowcast_onboarding" in section
    assert "earnings-nowcast-apply" not in section
    assert "imports-apply" not in section


def test_earnings_nowcast_readiness_launcher_has_explicit_fixture_onboarding_path():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    section = makefile[makefile.index("earnings-nowcast-readiness:") :]

    assert "$(if $(FIXTURE),tests/fixtures/earnings_nowcast_onboarding,$(or $(INPUT_DIR),data/imports/earnings_nowcast))" in section
    assert "tests/fixtures/earnings_nowcast)" not in section
    assert "imports-apply" not in section


def test_earnings_nowcast_sec_actuals_stage_launcher_requires_scoped_output_and_cutoff():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "earnings-nowcast-sec-actuals-stage" in _makefile_targets()
    target = makefile.split("earnings-nowcast-sec-actuals-stage:", 1)[1].split("\n\n", 1)[0]
    assert "TICKERS is required" in target
    assert "OUTPUT_DIR is required" in target
    assert "AS_OF is required" in target
    assert "--cutoff \"$(AS_OF)\"" in target
    assert "--output-dir \"$(OUTPUT_DIR)\"" in target
    assert "--max-runtime-seconds \"$(or $(SEC_STAGE_MAX_RUNTIME_SECONDS),300)\"" in target
    assert "generated temporary/review directory" in target
    assert "data/earnings_nowcast" not in target
    assert "data/imports" not in target
    assert "imports-apply" not in target
    assert "--apply" not in target


def test_makefile_exposes_read_only_commercial_beta_check():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "commercial-beta-check" in _makefile_targets()
    target = makefile.split("commercial-beta-check:", 1)[1].split("\n\n", 1)[0]
    assert "$(MAKE) --silent commercial-source-rights" in target
    assert "$(MAKE) --silent refresh-operations-status" in target
    assert "$(MAKE) --silent private-beta-readiness" in target
    for forbidden in ("price-refresh", "imports-apply", "git add", "git push"):
        assert forbidden not in target


def test_makefile_exposes_read_only_commercial_beta_release_check():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "commercial-beta-release-check" in _makefile_targets()
    target = makefile.split("commercial-beta-release-check:", 1)[1].split("\n\n", 1)[0]
    for required in (
        "$(MAKE) --silent commercial-beta-check",
        "$(MAKE) --silent research-dashboard-render-smoke",
        "$(MAKE) --silent commercial-beta-performance-contract",
        "$(MAKE) --silent browser-qa-evidence",
        "$(MAKE) --silent public-check",
        "$(MAKE) --silent pilot-readiness-check TOP_N=10",
        "$(MAKE) --silent diff-hygiene-summary",
        "git diff --check",
        "Safe claims:",
        "Unsafe claims:",
    ):
        assert required in target
    for forbidden in (
        "price-refresh",
        "imports-apply",
        "git add",
        "git commit",
        "git push",
        "deploy",
    ):
        assert forbidden not in target


def test_makefile_exposes_bytecode_free_consensus_source_review_target():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "earnings-consensus-source-review:" in makefile
    assert "PYTHONDONTWRITEBYTECODE=1 python3 -m src.earnings_consensus_sources" in makefile
    assert '--review-csv "$(INPUT)"' in makefile
    assert '--provider "$(PROVIDER)"' in makefile
    assert '--as-of "$(AS_OF)"' in makefile


def test_consensus_record_requires_the_exact_reviewed_preview_receipt():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    match = re.search(
        r"^earnings-consensus-collection-record:\n(?P<body>(?:\t.*\n)+)",
        makefile,
        flags=re.MULTILINE,
    )
    assert match is not None
    target = match.group("body")

    assert 'test -n "$(AS_OF)"' in target
    assert 'test -n "$(PREVIEW_RECEIPT)"' in target
    assert 'test "$(CONFIRM_REVIEWED)" = "1"' in target
    assert '--as-of "$(AS_OF)"' in target
    assert '--preview-receipt "$(PREVIEW_RECEIPT)"' in target
    assert target.count("--confirm-reviewed") == 1
    assert "$(if $(JSON),--json,)" in makefile


def test_makefile_exposes_direct_html_research_brief_browser_gate():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "company-workbench-html-browser-check" in _makefile_targets()
    assert (
        "make company-workbench-html-browser-check Verify offline research-brief bytes in a real browser"
        in makefile
    )
    target = makefile.split("company-workbench-html-browser-check:", 1)[1].split(
        "\n\n", 1
    )[0]
    assert "mktemp -d /tmp/stock-company-workbench-html-browser.XXXXXX" in target
    assert "export HTML_BRIEF_BROWSER_OUTPUT_DIR" not in target
    assert (
        'HTML_BRIEF_BROWSER_OUTPUT_DIR="$$packet_dir" '
        "PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider "
        "tests/test_company_workbench_html_browser_gate.py"
    ) in target
    assert "PYTHONDONTWRITEBYTECODE=1" in target
    assert "tests/test_company_workbench_html_browser_gate.py" in target
    assert 'test -s "$$packet_dir/results.json"' in target
    assert 'test -s "$$packet_dir/source-hashes.json"' in target
    assert 'shasum -a 256 "$$packet"' in target
    assert "rm " not in target


def test_accessibility_browser_gate_allows_the_exact_current_maturity_paths():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    target = makefile.split("research-accessibility-browser-check:", 1)[1].split(
        "\n\n", 1
    )[0]
    allowed = {
        line.split("--allow-dirty-path ", 1)[1].strip().rstrip(" \\")
        for line in target.splitlines()
        if "--allow-dirty-path " in line
    }

    assert allowed == {
        "src/browser_qa_evidence.py",
        "src/dashboard.py",
        "src/dashboard_navigation.py",
        "src/dashboard_render_smoke.py",
        "src/dashboard_visual_system.py",
        "src/project_status.py",
        "src/public_performance_gate.py",
        "src/readiness_ops.py",
        "src/research_accessibility_browser_gate.py",
        "src/research_loop.py",
        "src/research_workspace.py",
        "src/workspace_visual_browser_gate.py",
        "tests/test_browser_qa_evidence.py",
        "tests/test_dashboard_helpers.py",
        "tests/test_dashboard_navigation.py",
        "tests/test_dashboard_render_smoke.py",
        "tests/test_dashboard_visual_system.py",
        "tests/test_project_status.py",
        "tests/test_public_performance_gate.py",
        "tests/test_public_v1_release_docs.py",
        "tests/test_readiness_ops.py",
        "tests/test_research_accessibility_browser_gate.py",
        "tests/test_research_loop.py",
        "tests/test_research_mode_dashboard_contract.py",
        "tests/test_research_workspace.py",
        "tests/test_workspace_visual_browser_gate.py",
        "tests/test_launchers.py",
        "README.md",
        "ROADMAP.md",
        "docs/DASHBOARD_QA.md",
        "docs/PERSONAL_RESEARCH_MODE.md",
        "docs/PUBLIC_RELEASE_CHECKLIST.md",
        "docs/superpowers/specs/2026-08-12-hypothetical-paper-position-laboratory-design.md",
        "docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md",
        "Makefile",
    }
