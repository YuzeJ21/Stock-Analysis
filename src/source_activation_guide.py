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
) -> dict[str, Any]:
    return {
        "provider": provider,
        "category": category,
        "env_vars": env_vars,
        "can_cover": can_cover,
        "usage": usage,
        "cannot_unlock": cannot_unlock,
        "setup": setup,
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
                cannot_unlock="Unlimited batch coverage, recommendations, order routing, or unreviewed valuation inputs.",
                setup=f"Set {env_name} in config/provider_keys.env, then rerun make session-source-preflight.",
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
    args = parser.parse_args(argv)

    guide = build_source_activation_guide()
    if args.json:
        print(json.dumps(guide, indent=2, sort_keys=True))
    else:
        print(render_source_activation_guide(guide))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
