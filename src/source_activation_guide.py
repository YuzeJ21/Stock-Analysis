from __future__ import annotations

import argparse
import json
import os
from typing import Any


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
IBKR_ENVS = ["IBKR_HOST", "IBKR_PORT", "IBKR_CLIENT_ID"]


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


def build_provider_setup_checklist() -> dict[str, Any]:
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
            }
        )
    return {
        "title": "Provider Setup Checklist",
        "research_boundary": guide["research_boundary"],
        "secret_policy": "Real key values are never printed.",
        "rows": rows,
        "apply_gate": guide["apply_gate"],
        "non_retry_rule": guide["non_retry_rule"],
    }


def render_provider_setup_checklist(checklist: dict[str, Any]) -> str:
    lines = [
        str(checklist["title"]),
        str(checklist["research_boundary"]),
        str(checklist["secret_policy"]),
        "",
        "Provider | Setup state | Unlock lanes | Usage | Safe next step",
        "--- | --- | --- | --- | ---",
    ]
    for row in checklist["rows"]:
        lines.append(
            " | ".join(
                [
                    str(row["provider"]),
                    str(row["setup_state"]),
                    str(row["unlock_lanes"]),
                    str(row["usage"]),
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
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--checklist", action="store_true", help="Print checklist-style provider setup states.")
    args = parser.parse_args(argv)

    if args.checklist:
        checklist = build_provider_setup_checklist()
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
