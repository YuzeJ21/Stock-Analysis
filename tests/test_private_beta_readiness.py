import subprocess
import sys

from src.private_beta_readiness import build_private_beta_readiness


def test_clean_local_contract_is_ready_but_account_capabilities_stay_external():
    readiness = build_private_beta_readiness()
    checks = {check.area: check for check in readiness.checks}

    assert readiness.classification == "local_ready"
    assert checks["authentication"].status == "external_account_required"
    assert checks["workspaces"].status == "external_account_required"
    assert checks["incident_response"].status == "external_operations_required"
    assert checks["rollback"].status == "external_operations_required"
    assert checks["owner_capacity"].status == "external_operations_required"
    assert checks["secrets"].status == "local_ready"
    assert "do not claim runtime authentication or hosting" in readiness.boundary
    assert set(checks) == {
        "authentication",
        "workspaces",
        "user_data_separation",
        "secrets",
        "audit",
        "retention",
        "entitlements",
        "monitoring",
        "health_checks",
        "incident_response",
        "rollback",
        "owner_capacity",
    }


def test_declared_external_setup_still_requires_manual_verification():
    readiness = build_private_beta_readiness(external_setup_declared=True)
    checks = {check.area: check for check in readiness.checks}

    assert readiness.classification == "manual_verification_required"
    assert checks["authentication"].status == "manual_verification_required"
    assert checks["health_checks"].status == "manual_verification_required"
    assert checks["incident_response"].status == "manual_verification_required"
    assert checks["rollback"].status == "manual_verification_required"
    assert checks["owner_capacity"].status == "manual_verification_required"
    assert "does not prove runtime authentication or hosting" in readiness.boundary


def test_unsafe_secret_condition_blocks_private_beta_readiness_without_echoing_value():
    readiness = build_private_beta_readiness(unsafe_secret_detected=True)
    checks = {check.area: check for check in readiness.checks}

    assert readiness.classification == "unsafe_secret_blocked"
    assert checks["secrets"].status == "unsafe_secret_blocked"
    assert "remove the secret from tracked files" in checks["secrets"].next_step.lower()
    assert "secret value" not in checks["secrets"].detail.lower()


def test_private_beta_cli_and_make_target_are_read_only_and_truthful():
    cli = subprocess.run(
        [sys.executable, "-m", "src.private_beta_readiness"],
        check=False,
        capture_output=True,
        text=True,
    )
    make = subprocess.run(
        ["make", "--no-print-directory", "private-beta-readiness"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert cli.returncode == 0
    assert make.returncode == 0
    for output in (cli.stdout, make.stdout):
        assert "classification: local_ready" in output
        assert "authentication: external_account_required" in output
        assert "health_checks: external_account_required" in output
        assert "incident_response: external_operations_required" in output
        assert "rollback: external_operations_required" in output
        assert "owner_capacity: external_operations_required" in output
        assert "does not prove runtime authentication or hosting" in output
        assert "token=" not in output.lower()
