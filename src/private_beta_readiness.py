"""Read-only readiness classification for the unhosted private-beta boundary."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrivateBetaCheck:
    area: str
    status: str
    detail: str
    next_step: str


@dataclass(frozen=True)
class PrivateBetaReadiness:
    classification: str
    checks: tuple[PrivateBetaCheck, ...]
    boundary: str


_EXTERNAL_ACCOUNT_AREAS = (
    ("authentication", "Configure and verify an external identity provider before admitting users."),
    ("workspaces", "Create private workspaces through the hosted account-backed service."),
    ("user_data_separation", "Verify per-user data isolation in the hosted persistence layer."),
    ("audit", "Configure and review hosted audit logging before relying on audit records."),
    ("retention", "Set and verify retention and deletion behavior with the hosted provider."),
    ("entitlements", "Configure and test account-backed access entitlements."),
    ("monitoring", "Configure hosted usage and error monitoring without recording sensitive user data."),
    ("health_checks", "Configure and verify hosted health checks after deployment."),
)


def build_private_beta_readiness(
    *, external_setup_declared: bool = False, unsafe_secret_detected: bool = False
) -> PrivateBetaReadiness:
    """Describe local contract readiness without inspecting or configuring runtime systems."""
    secret_status = "unsafe_secret_blocked" if unsafe_secret_detected else "local_ready"
    secret_detail = (
        "A tracked or otherwise unsafe secret condition was declared; readiness is blocked."
        if unsafe_secret_detected
        else "Repository guidance keeps real secrets outside Git and limits committed files to templates and names."
    )
    secret_next_step = (
        "Remove the secret from tracked files, rotate it outside the repository, and re-run the review."
        if unsafe_secret_detected
        else "Use the external host's encrypted secret store only after an account exists."
    )
    checks = [
        PrivateBetaCheck(
            area="secrets",
            status=secret_status,
            detail=secret_detail,
            next_step=secret_next_step,
        )
    ]
    external_status = (
        "manual_verification_required"
        if external_setup_declared
        else "external_account_required"
    )
    checks.extend(
        PrivateBetaCheck(
            area=area,
            status=external_status,
            detail="This repository contains a readiness requirement, not an implemented runtime capability.",
            next_step=next_step,
        )
        for area, next_step in _EXTERNAL_ACCOUNT_AREAS
    )
    return PrivateBetaReadiness(
        classification=(
            "unsafe_secret_blocked"
            if unsafe_secret_detected
            else "manual_verification_required"
            if external_setup_declared
            else "local_ready"
        ),
        checks=tuple(checks),
        boundary=(
            "Local readiness only; declared setup does not prove runtime authentication or "
            "hosting; do not claim runtime authentication or hosting."
        ),
    )
