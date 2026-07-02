from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from src.paths import resolve_project_root
from src.provider_env import load_provider_environment
from src.session_source_preflight import load_session_source_preflight


KEYED_PROVIDER_ENVS = {
    "FMP free tier": "FMP_API_KEY",
    "Alpha Vantage free tier": "ALPHA_VANTAGE_API_KEY",
    "Finnhub free tier": "FINNHUB_API_KEY",
}
KEYED_PROVIDER_BATCH_POLICIES = {
    "FMP free tier": "small_batch_only; recommended <=250 requests/day and <=25 tickers/run",
    "Alpha Vantage free tier": "small_batch_only; recommended <=25 requests/day and <=5 tickers/run",
    "Finnhub free tier": "small_batch_only; recommended <=60 requests/day and <=10 tickers/run",
}
KEYED_PROVIDER_SETUP_PRIORITY = [
    (
        "FMP free tier",
        "Broadest keyed fallback here: price, fundamentals, share count, and the largest stated free-tier daily cap.",
    ),
    (
        "Finnhub free tier",
        "Second fallback after FMP; use only if FMP is unavailable or insufficient for the reviewed ticker.",
    ),
    (
        "Alpha Vantage free tier",
        "Smallest stated free-tier cap; keep as a final small-batch fallback.",
    ),
]
IBKR_ENVS = ["IBKR_HOST", "IBKR_PORT", "IBKR_CLIENT_ID"]
ACTIVATION_PLAN = [
    "Run make project-status first; if it says queues are exhausted, do not reopen broad proof loops.",
    "Configure at most one missing keyed free-tier provider locally, then rerun make session-source-preflight.",
    "Run that provider's reviewed one-ticker smoke command only; do not start a broad batch from setup.",
    "Continue only through validate, preview, rejected-row review, and source-provenance checks.",
    "If no source-backed row is staged, record still_blocked/skipped/excluded and pivot.",
]
WORKFLOW_PIVOT = [
    {
        "command": "make project-status",
        "purpose": "Confirm whether proof queues have executable company candidates before opening broad proof tables.",
        "boundary": "Read-only status; does not refresh, stage, apply, or unlock blocked inputs.",
    },
    {
        "command": "make provider-setup-checklist",
        "purpose": "Review missing keyed providers and reviewed one-ticker smoke commands when proof queues are exhausted.",
        "boundary": "Setup evidence only; do not apply data directly from provider setup.",
    },
    {
        "command": "make universe-scope TOP_N=10",
        "purpose": "Choose active-universe, ticker-list, sector/theme, ready-only, or missing-data scope before deeper review.",
        "boundary": "Scope selection only; does not infer missing fundamentals, peers, earnings, or estimates.",
    },
    {
        "command": "make risk-context",
        "purpose": "Review liquidity, correlation, and proxy-risk readiness after scope is chosen.",
        "boundary": "Historical context only; not a recommendation or source-proof unlock.",
    },
]


def _configured(env_name: str) -> bool:
    return bool(os.environ.get(env_name, "").strip())


def _provider_row(
    provider: str,
    *,
    category: str,
    env_vars: list[str],
    can_cover: list[str],
    usage: str,
    cannot_unlock: str,
    setup: str,
    batch_policy: str = "",
    post_setup_smoke_command: str = "",
) -> dict[str, Any]:
    return {
        "provider": provider,
        "category": category,
        "env_vars": env_vars,
        "can_cover": can_cover,
        "usage": usage,
        "cannot_unlock": cannot_unlock,
        "setup": setup,
        "batch_policy": batch_policy,
        "post_setup_smoke_command": post_setup_smoke_command,
    }


def build_source_activation_guide() -> dict[str, Any]:
    keyed_rows = []
    for provider, env_name in KEYED_PROVIDER_ENVS.items():
        keyed_rows.append(
            _provider_row(
                provider,
                category="keyed_free_tier_available" if _configured(env_name) else "keyed_free_tier_missing",
                env_vars=[env_name],
                can_cover=["price", "fundamentals", "share_count"],
                usage="keyed_free_tier_fallback",
                cannot_unlock="Full-universe refresh without caps, recommendations, order routing, or unreviewed valuation inputs.",
                setup=f"Set {env_name} in config/provider_keys.env, then rerun make session-source-preflight.",
                batch_policy=KEYED_PROVIDER_BATCH_POLICIES[provider],
                post_setup_smoke_command={
                    "FMP free tier": (
                        "make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> "
                        "&& make imports-preview IMPORT_TICKERS=<ticker>"
                    ),
                    "Alpha Vantage free tier": (
                        "make alpha-vantage-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> "
                        "&& make imports-preview IMPORT_TICKERS=<ticker>"
                    ),
                    "Finnhub free tier": (
                        "make finnhub-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> "
                        "&& make imports-preview IMPORT_TICKERS=<ticker>"
                    ),
                }[provider],
            )
        )

    ibkr_configured = all(_configured(env_name) for env_name in IBKR_ENVS)
    providers = [
        _provider_row(
            "SEC Companyfacts",
            category="free_public_available",
            env_vars=["SEC_USER_AGENT"],
            can_cover=["fundamentals", "share_count"],
            usage="source_backed_companyfacts",
            cannot_unlock="Peers, earnings estimates, recommendations, or inferred missing values.",
            setup="Set SEC_USER_AGENT in config/provider_keys.env or the shell.",
        ),
        _provider_row(
            "SEC submissions",
            category="free_public_available",
            env_vars=["SEC_USER_AGENT"],
            can_cover=["metadata"],
            usage="metadata_evidence_only",
            cannot_unlock="DCF, valuation, earnings, analyst estimates, or share count unless a filing document has an explicit fact.",
            setup="Set SEC_USER_AGENT, then run make session-source-preflight.",
        ),
        _provider_row(
            "SEC filing documents",
            category="free_public_available",
            env_vars=["SEC_USER_AGENT"],
            can_cover=["share_count"],
            usage="explicit_filing_document_evidence",
            cannot_unlock="Inferred shares, market cap-derived shares, or missing fundamentals.",
            setup="Use make sec-filing-share-stage TICKERS=<ticker> after source preflight confirms SEC access.",
        ),
        _provider_row(
            "Stooq",
            category="free_public_available",
            env_vars=["STOOQ_API_KEY"],
            can_cover=["price"],
            usage="free_public_daily_ohlcv",
            cannot_unlock="Fundamentals, shares, peers, earnings, estimates, or valuation inputs.",
            setup="Use PROVIDER=auto; set STOOQ_API_KEY only if unauthenticated Stooq access is unavailable.",
            post_setup_smoke_command="make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=1 TOP_N=1 PROVIDER=stooq",
        ),
        _provider_row(
            "Yahoo/yfinance",
            category="free_public_available",
            env_vars=[],
            can_cover=["price", "fundamentals", "optional_context"],
            usage="provider_assisted_research_data",
            cannot_unlock="Trusted proof without validate, preview, rejected-row review, and apply gates.",
            setup="Install the research extra if needed, then rerun make session-source-preflight.",
        ),
        *keyed_rows,
        _provider_row(
            "IBKR read-only",
            category="optional_broker_configured" if ibkr_configured else "optional_broker_disabled",
            env_vars=IBKR_ENVS,
            can_cover=["price"],
            usage="read_only_daily_ohlcv",
            cannot_unlock="Broker actions, order routing, auto-trading, fundamentals, shares, peers, earnings, or estimates.",
            setup="Leave disabled unless IBKR Gateway/TWS is intentionally running for read-only daily bars.",
            post_setup_smoke_command="make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=1 TOP_N=1 PROVIDER=ibkr",
        ),
    ]

    return {
        "title": "Source Activation Guide",
        "research_boundary": "Research-only source setup. No investment advice, broker trading, order routing, auto-trading, or direct buy/sell instructions.",
        "secret_policy": "No provider key values are printed or stored by this guide.",
        "setup_commands": [
            "cp config/provider_keys.env.example config/provider_keys.env",
            "chmod 600 config/provider_keys.env",
            "edit config/provider_keys.env locally; do not commit real keys",
        ],
        "activation_plan": ACTIVATION_PLAN,
        "providers": providers,
        "apply_gate": [
            "make imports-validate IMPORT_TICKERS=<ticker>",
            "make imports-preview IMPORT_TICKERS=<ticker>",
            "make imports-apply IMPORT_TICKERS=<ticker> only when validation passes, preview scope is intended, rejected rows are zero, and source provenance exists",
            "make readiness",
        ],
        "next_commands": [
            "make session-source-preflight",
            "make coverage-frontier TOP_N=10",
            "make project-status",
        ],
        "non_retry_rule": "Record unavailable source paths once, then pivot to the next executable lane in this session.",
        "no_direct_apply_rule": "Do not apply data directly from source setup.",
    }


def _setup_state_for_provider(row: dict[str, Any]) -> str:
    category = str(row.get("category") or "").strip()
    if category == "keyed_free_tier_available":
        return "configured"
    if category == "keyed_free_tier_missing":
        return "needs_key"
    if category == "optional_broker_configured":
        return "optional_configured"
    if category == "optional_broker_disabled":
        return "optional_disabled"
    if category == "free_public_available":
        return "available"
    return "unknown"


def _safe_next_step_for_provider(row: dict[str, Any]) -> str:
    state = _setup_state_for_provider(row)
    if state == "needs_key":
        return str(row.get("setup") or "Set the provider key locally, then rerun make session-source-preflight.")
    if state == "optional_disabled":
        return "Leave disabled unless intentionally using read-only daily OHLCV."
    if state == "optional_configured":
        return "Run make session-source-preflight, then use read-only daily OHLCV only."
    if state == "configured":
        return "Run make session-source-preflight, then dry-run the matching source ladder."
    return "Run make session-source-preflight before using this source path."


def _current_gate_from_preflight(preflight: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(preflight, dict):
        return {}
    activation = preflight.get("source_activation", {})
    activation = activation if isinstance(activation, dict) else {}
    console = preflight.get("source_activation_console_v2", {})
    if not isinstance(console, dict):
        return {}
    operator_summary = console.get("operator_summary", {})
    operator_summary = operator_summary if isinstance(operator_summary, dict) else {}

    def _join(value: object) -> str:
        if isinstance(value, (list, tuple)):
            return ", ".join(str(item) for item in value if str(item).strip()) or "-"
        return str(value or "").strip() or "-"

    return {
        "can_run_now": _join(operator_summary.get("can_run_now") or console.get("next_executable_lane")),
        "needs_setup": _join(operator_summary.get("needs_setup")),
        "avoid_repeating": _join(operator_summary.get("avoid_repeating")),
        "next_step": _join(operator_summary.get("next_step") or console.get("next_executable_command")),
        "next_step_reason": _join(operator_summary.get("next_step_reason")),
        "source_activation_reason": _join(activation.get("reason_code")),
        "source_activation_detail": _join(activation.get("detail")),
        "source_activation_next_action": _join(activation.get("next_action")),
    }


def _provider_names_for_state(rows: list[dict[str, Any]], states: set[str]) -> str:
    names = [
        str(row.get("provider") or "").strip()
        for row in rows
        if str(row.get("setup_state") or "").strip() in states and str(row.get("provider") or "").strip()
    ]
    return ", ".join(names) if names else "-"


def _optional_broker_summary(rows: list[dict[str, Any]]) -> str:
    names: list[str] = []
    for row in rows:
        provider = str(row.get("provider") or "").strip()
        setup_state = str(row.get("setup_state") or "").strip()
        if not provider or setup_state not in {"optional_disabled", "optional_configured"}:
            continue
        if setup_state == "optional_disabled":
            names.append(f"{provider} (disabled unless explicitly configured)")
        else:
            names.append(f"{provider} (configured for read-only daily OHLCV)")
    return ", ".join(names) if names else "-"


def _provider_source_answer(rows: list[dict[str, Any]]) -> dict[str, str]:
    return {
        "free_public_now": _provider_names_for_state(rows, {"available"}),
        "needs_key": _provider_names_for_state(rows, {"needs_key"}),
        "configured_keyed": _provider_names_for_state(rows, {"configured"}),
        "optional_broker": _optional_broker_summary(rows),
        "answer": (
            "Use the free/public baseline first; configure at most one keyed free-tier fallback only when "
            "project-status says source-proof queues are exhausted. Optional broker data remains disabled unless "
            "explicitly configured for read-only daily OHLCV."
        ),
    }


def _one_provider_setup_order(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows_by_provider = {
        str(row.get("provider") or "").strip(): row
        for row in rows
        if str(row.get("setup_state") or "").strip() == "needs_key"
    }
    setup_order: list[dict[str, str]] = []
    for provider, reason in KEYED_PROVIDER_SETUP_PRIORITY:
        row = rows_by_provider.get(provider)
        if not row:
            continue
        setup_order.append(
            {
                "provider": provider,
                "why_first": reason,
                "setup_env": str(row.get("env_vars") or ""),
                "smoke_command": str(row.get("post_setup_smoke_command") or ""),
            }
        )
    return setup_order


def _coverage_unlock_decision(rows: list[dict[str, Any]], current_gate: dict[str, str]) -> dict[str, str]:
    setup_order = _one_provider_setup_order(rows)
    first_setup = setup_order[0] if setup_order else {}
    provider = str(first_setup.get("provider") or "one keyed free-tier provider").strip()
    avoid_repeating = str(current_gate.get("avoid_repeating") or "-").strip()
    can_run_now = str(current_gate.get("can_run_now") or "-").strip()
    do_not_retry = (
        f"Do not retry {avoid_repeating} until new source-backed rows, keyed provider data, reviewed manual rows, "
        "or changed blockers exist."
        if avoid_repeating and avoid_repeating != "-"
        else "Do not retry exhausted proof queues until new source-backed rows, keyed provider data, reviewed manual rows, or changed blockers exist."
    )
    return {
        "answer": "No broad coverage batch should run from setup alone.",
        "can_use_now": f"Use free/public sources for already executable proof paths; current gate says {can_run_now}.",
        "configure_first": f"Configure {provider} first only if you want a keyed fallback, then run one reviewed one-ticker smoke command.",
        "do_not_retry": do_not_retry,
        "proof_boundary": (
            "Provider setup only makes a source executable; readiness changes still require validate, preview, "
            "rejected-row review, source provenance, apply/skip decision, rebuilt readiness, and proof ledger evidence."
        ),
    }


def _first_provider_answer(rows: list[dict[str, Any]], current_gate: dict[str, str]) -> dict[str, str]:
    source_answer = _provider_source_answer(rows)
    unlock_decision = _coverage_unlock_decision(rows, current_gate)
    smoke_row = next(
        (
            row
            for row in rows
            if str(row.get("setup_state") or "").strip() == "configured"
            and str(row.get("post_setup_smoke_command") or "").strip()
        ),
        None,
    )
    if smoke_row is None:
        setup_order = _one_provider_setup_order(rows)
        first_setup = setup_order[0] if setup_order else {}
        smoke_command = str(first_setup.get("smoke_command") or "").strip()
        setup_prerequisite = (
            f"Configure {first_setup.get('provider')} with {first_setup.get('setup_env')} before running its reviewed one-ticker smoke command."
            if first_setup
            else "Run make session-source-preflight before any reviewed one-ticker smoke command."
        )
    else:
        smoke_command = str(smoke_row.get("post_setup_smoke_command") or "").strip()
        setup_prerequisite = (
            f"{smoke_row.get('provider')} is configured; choose one reviewed ticker before running the reviewed one-ticker smoke command."
        )
    if not smoke_command:
        smoke_command = "make session-source-preflight"
    return {
        "question": "What source can I use next?",
        "free_source_now": source_answer.get("free_public_now", "-"),
        "missing_key": source_answer.get("needs_key", "-"),
        "do_not_retry": unlock_decision.get(
            "do_not_retry",
            "Do not retry exhausted proof queues until new source-backed rows, keyed provider data, reviewed manual rows, or changed blockers exist.",
        ),
        "setup_prerequisite": setup_prerequisite,
        "ticker_scope_rule": (
            "Choose one reviewed ticker from make project-status or a current proof packet before replacing <ticker>; "
            "do not run the reviewed one-ticker smoke command across a broad list."
        ),
        "reviewed_one_ticker_smoke": smoke_command,
        "one_safe_smoke": smoke_command,
        "boundary": "Provider setup only makes a source executable; readiness changes still require validate/preview/apply gates.",
    }


def build_provider_setup_checklist(current_preflight: dict[str, Any] | None = None) -> dict[str, Any]:
    guide = build_source_activation_guide()
    rows = []
    for row in guide["providers"]:
        rows.append(
            {
                "provider": row["provider"],
                "category": row["category"],
                "setup_state": _setup_state_for_provider(row),
                "env_vars": ", ".join(row["env_vars"]) if row["env_vars"] else "none",
                "unlock_lanes": ", ".join(row["can_cover"]),
                "usage": row["usage"],
                "batch_policy": row.get("batch_policy", ""),
                "cannot_unlock": row["cannot_unlock"],
                "safe_next_step": _safe_next_step_for_provider(row),
                "post_setup_smoke_command": row.get("post_setup_smoke_command", ""),
            }
        )
    current_gate = _current_gate_from_preflight(current_preflight)
    return {
        "title": "Provider Setup Checklist",
        "research_boundary": guide["research_boundary"],
        "secret_policy": "Real key values are never printed.",
        "setup_commands": guide["setup_commands"],
        "activation_plan": guide["activation_plan"],
        "rows": rows,
        "source_answer": _provider_source_answer(rows),
        "first_answer": _first_provider_answer(rows, current_gate),
        "coverage_unlock_decision": _coverage_unlock_decision(rows, current_gate),
        "one_provider_setup_order": _one_provider_setup_order(rows),
        "workflow_pivot": WORKFLOW_PIVOT,
        "apply_gate": guide["apply_gate"],
        "non_retry_rule": guide["non_retry_rule"],
        "current_gate": current_gate,
    }


def render_provider_setup_checklist(checklist: dict[str, Any]) -> str:
    lines = [
        str(checklist["title"]),
        str(checklist["research_boundary"]),
        str(checklist["secret_policy"]),
        "",
        "First provider answer:",
    ]
    first_answer = checklist.get("first_answer", {})
    if isinstance(first_answer, dict) and first_answer:
        lines.extend(
            [
                f"- question: {first_answer.get('question', '-')}",
                f"- free_source_now: {first_answer.get('free_source_now', '-')}",
                f"- missing_key: {first_answer.get('missing_key', '-')}",
                f"- do_not_retry: {first_answer.get('do_not_retry', '-')}",
                f"- setup_prerequisite: {first_answer.get('setup_prerequisite', '-')}",
                f"- ticker_scope_rule: {first_answer.get('ticker_scope_rule', '-')}",
                f"- reviewed_one_ticker_smoke: {first_answer.get('reviewed_one_ticker_smoke', first_answer.get('one_safe_smoke', '-'))}",
                f"- boundary: {first_answer.get('boundary', '-')}",
                "",
            ]
        )
    lines.extend([
        "What can run now?",
    ])
    source_answer = checklist.get("source_answer", {})
    if isinstance(source_answer, dict) and source_answer:
        configured_keyed = source_answer.get("configured_keyed", "-")
        needs_key = source_answer.get("needs_key", "-")
        lines.extend(
            [
                f"- Free public sources: {source_answer.get('free_public_now', '-')}",
                f"- Keyed free-tier fallbacks: configured {configured_keyed}; needs key {needs_key}",
                f"- Optional broker boundary: {source_answer.get('optional_broker', '-')}",
                "- Apply gate: validate, preview, rejected-row review, source provenance, and explicit apply/skip decision are still required.",
                f"- free_public_now: {source_answer.get('free_public_now', '-')}",
                f"- configured_keyed: {configured_keyed}",
                f"- needs_key: {needs_key}",
                f"- optional_broker: {source_answer.get('optional_broker', '-')}",
                f"- answer: {source_answer.get('answer', '-')}",
                "",
            ]
        )
    coverage_unlock_decision = checklist.get("coverage_unlock_decision", {})
    if isinstance(coverage_unlock_decision, dict) and coverage_unlock_decision:
        lines.extend(
            [
                "Coverage unlock decision:",
                f"- answer: {coverage_unlock_decision.get('answer', '-')}",
                f"- can_use_now: {coverage_unlock_decision.get('can_use_now', '-')}",
                f"- configure_first: {coverage_unlock_decision.get('configure_first', '-')}",
                f"- do_not_retry: {coverage_unlock_decision.get('do_not_retry', '-')}",
                f"- proof_boundary: {coverage_unlock_decision.get('proof_boundary', '-')}",
                "",
            ]
        )
    lines.extend([
        "Local setup commands:",
    ])
    lines.extend(f"- {command}" for command in checklist.get("setup_commands", []))
    lines.extend(["", "Activation plan:"])
    lines.extend(f"- {step}" for step in checklist.get("activation_plan", []))
    workflow_pivot = checklist.get("workflow_pivot", [])
    if isinstance(workflow_pivot, list) and workflow_pivot:
        lines.extend(
            [
                "",
                "Workflow pivot when proof queues are exhausted:",
                "Command | Purpose | Boundary",
                "--- | --- | ---",
            ]
        )
        for row in workflow_pivot:
            if not isinstance(row, dict):
                continue
            lines.append(
                " | ".join(
                    [
                        str(row.get("command") or ""),
                        str(row.get("purpose") or ""),
                        str(row.get("boundary") or ""),
                    ]
                )
            )
    current_gate = checklist.get("current_gate", {})
    if isinstance(current_gate, dict) and current_gate:
        lines.extend(
            [
                "",
                "Current source gate:",
                f"- source_activation_reason: {current_gate.get('source_activation_reason', '-')}",
                f"- source_activation_detail: {current_gate.get('source_activation_detail', '-')}",
                f"- can_run_now: {current_gate.get('can_run_now', '-')}",
                f"- needs_setup: {current_gate.get('needs_setup', '-')}",
                f"- avoid_repeating: {current_gate.get('avoid_repeating', '-')}",
                f"- next_step: {current_gate.get('next_step', '-')}",
                f"- next_step_reason: {current_gate.get('next_step_reason', '-')}",
            ]
        )
    setup_order = checklist.get("one_provider_setup_order", [])
    if isinstance(setup_order, list) and setup_order:
        first = next((row for row in setup_order if isinstance(row, dict)), None)
        if first:
            lines.extend(
                [
                    "",
                    f"Configure first: {first.get('provider', '-')}",
                    f"- why: {first.get('why_first', '-')}",
                    f"- setup_env: {first.get('setup_env', '-')}",
                    f"- reviewed_smoke_command: {first.get('smoke_command', '-')}",
                    "- Do not configure all missing providers at once; configure one, rerun preflight, run one reviewed one-ticker smoke command, then validate/preview before any apply.",
                ]
            )
    lines.extend(
        [
            "",
            "Provider setup and boundaries:",
        ]
    )
    lines.extend(
        [
        "Provider | Setup state | Unlock lanes | Usage | Batch policy | Smoke command | Cannot unlock | Safe next step",
        "--- | --- | --- | --- | --- | --- | --- | ---",
        ]
    )
    for row in checklist["rows"]:
        lines.append(
            " | ".join(
                [
                    str(row["provider"]),
                    str(row["setup_state"]),
                    str(row["unlock_lanes"]),
                    str(row["usage"]),
                    str(row.get("batch_policy") or "not_applicable"),
                    str(row.get("post_setup_smoke_command") or "not_applicable"),
                    str(row["cannot_unlock"]),
                    str(row["safe_next_step"]),
                ]
            )
        )
    lines.append("")
    lines.append("Validate / preview / apply gate:")
    lines.extend(f"- {command}" for command in checklist["apply_gate"])
    lines.append("")
    lines.append(f"Non-retry rule: {checklist['non_retry_rule']}")
    return "\n".join(lines)


def render_source_activation_guide(guide: dict[str, Any]) -> str:
    lines = [
        str(guide["title"]),
        str(guide["research_boundary"]),
        str(guide["secret_policy"]),
        str(guide["no_direct_apply_rule"]),
        "",
        "Setup commands:",
    ]
    lines.extend(f"- {command}" for command in guide["setup_commands"])
    lines.append("")
    lines.append("Activation plan:")
    lines.extend(f"- {step}" for step in guide["activation_plan"])
    lines.append("")
    lines.append("Provider setup and boundaries:")
    for row in guide["providers"]:
        env_vars = ", ".join(row["env_vars"]) if row["env_vars"] else "none"
        can_cover = ", ".join(row["can_cover"])
        lines.append(
            f"- {row['provider']} | {row['category']} | env={env_vars} | can_cover={can_cover} | "
            f"usage={row['usage']}"
        )
        lines.append(f"  setup: {row['setup']}")
        if row.get("batch_policy"):
            lines.append(f"  batch_policy: {row['batch_policy']}")
        if row.get("post_setup_smoke_command"):
            lines.append(f"  post_setup_smoke_command: {row['post_setup_smoke_command']}")
        lines.append(f"  cannot_unlock: {row['cannot_unlock']}")
    lines.append("")
    lines.append("Validate / preview / apply gate:")
    lines.extend(f"- {command}" for command in guide["apply_gate"])
    lines.append("")
    lines.append("Next commands:")
    lines.extend(f"- {command}" for command in guide["next_commands"])
    lines.append("")
    lines.append(f"Non-retry rule: {guide['non_retry_rule']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print read-only source activation setup guidance.")
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--checklist", action="store_true", help="Print checklist-style provider setup states.")
    args = parser.parse_args(argv)

    root = resolve_project_root(Path(args.root))
    load_provider_environment(root)
    if args.checklist:
        checklist = build_provider_setup_checklist(load_session_source_preflight(root))
        if args.json:
            print(json.dumps(checklist, indent=2, sort_keys=True))
        else:
            print(render_provider_setup_checklist(checklist))
        return 0

    guide = build_source_activation_guide()
    if args.json:
        print(json.dumps(guide, indent=2, sort_keys=True))
    else:
        print(render_source_activation_guide(guide))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
