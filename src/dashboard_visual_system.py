"""Pure presentation primitives shared by dashboard integrations."""

from __future__ import annotations

import html
import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlsplit


_VISUAL_TOKENS = {
    "--sr-canvas": "#F6F7F4",
    "--sr-surface": "#FFFFFF",
    "--sr-surface-muted": "#F1F4F1",
    "--sr-ink": "#0F172A",
    "--sr-text": "#243244",
    "--sr-muted": "#475569",
    "--sr-border": "#D9E1DC",
    "--sr-nav": "#0B1B2B",
    "--sr-nav-text": "#F8FAFC",
    "--sr-nav-muted": "#CBD5E1",
    "--sr-forest": "#155E4B",
    "--sr-teal": "#0F766E",
    "--sr-amber": "#854D0E",
    "--sr-red": "#B42318",
    "--sr-blue": "#315D8A",
    "--sr-focus": "#0B6BFF",
}

_CANONICAL_ROUTE_KEYS = frozenset(
    {
        "mode",
        "page",
        "ticker",
        "open",
        "cash_preview",
        "lane",
        "drawer",
        "queue_details",
        "batch_details",
        "proof_details",
        "metric_details",
    }
)


_HTML_FRAGMENT_PROVENANCE = object()


@dataclass(frozen=True, init=False)
class HtmlFragment:
    value: str

    def __init__(self, value: str) -> None:
        del value
        raise TypeError(
            "HtmlFragment values are created by module presentation helpers only."
        )


@dataclass(frozen=True)
class SafeRouteAction:
    label: str
    href: str
    aria_label: str | None = None

    def __post_init__(self) -> None:
        _validate_safe_route_href(self.href)


@dataclass(frozen=True)
class EvidenceRow:
    lane: str
    role: str
    state: str
    count_or_cutoff: str
    reason: str
    evidence_action: SafeRouteAction | None = None


@dataclass(frozen=True)
class TimelineRecord:
    record_id: str
    timestamp: str | None
    label: str
    summary: str
    evidence_action: SafeRouteAction | None = None


@dataclass(frozen=True)
class VisualState:
    role: str
    state: str
    semantic: str
    label: str
    foreground: str
    background: str
    border: str


def visual_tokens() -> dict[str, str]:
    """Return a copy of the approved calm institutional token palette."""

    return dict(_VISUAL_TOKENS)


def _normalized_label(state: str, label: str | None) -> str:
    explicit = str(label or "").strip()
    if explicit:
        return explicit
    normalized = str(state or "").strip()
    return normalized if normalized else "Unknown"


def visual_state(role: str, state: str, label: str | None = None) -> VisualState:
    """Map an explicit semantic role and state without inferring investment sentiment."""

    normalized_role = str(role or "").strip().casefold()
    normalized_state = re.sub(
        r"[^a-z0-9]+",
        "_",
        str(state or "").strip().casefold(),
    ).strip("_")
    semantic = "neutral"
    foreground = _VISUAL_TOKENS["--sr-muted"]
    if normalized_role in {"evidence", "readiness"}:
        if normalized_state in {
            "supported",
            "ready",
            "usable_now",
            "research_ready",
            "available",
            "valid",
            "liquid",
            "low_co_movement",
        }:
            semantic, foreground = "supported", _VISUAL_TOKENS["--sr-teal"]
        elif normalized_state in {
            "partial",
            "waiting",
            "candidate_context_only",
            "partial_coverage",
            "valid_with_warnings",
            "moderate_liquidity",
            "moderate_co_movement",
        }:
            semantic, foreground = "partial", _VISUAL_TOKENS["--sr-amber"]
        elif normalized_state in {
            "blocked",
            "missing",
            "unavailable",
            "needs_price_data",
            "needs_enrichment",
            "missing_file",
            "not_available",
            "peer_data_unavailable",
            "insufficient_peer_data",
            "insufficient_price_data",
            "thin_needs_review",
            "high_co_movement",
            "insufficient_overlap",
            "insufficient_data",
        }:
            semantic, foreground = "blocked", _VISUAL_TOKENS["--sr-red"]
        elif normalized_state == "stale":
            semantic, foreground = "stale", _VISUAL_TOKENS["--sr-amber"]
        elif normalized_state == "excluded":
            semantic, foreground = "excluded", _VISUAL_TOKENS["--sr-muted"]
        elif normalized_state == "withheld":
            semantic, foreground = "withheld", _VISUAL_TOKENS["--sr-amber"]
    elif normalized_role == "freshness":
        if normalized_state in {"current", "fresh", "ready"}:
            semantic, foreground = "supported", _VISUAL_TOKENS["--sr-teal"]
        elif normalized_state in {"mixed", "partial", "stale"}:
            semantic, foreground = "partial", _VISUAL_TOKENS["--sr-amber"]
        elif normalized_state in {"missing", "unavailable"}:
            semantic, foreground = "blocked", _VISUAL_TOKENS["--sr-red"]
    elif normalized_role == "workflow" and normalized_state in {
        "current",
        "primary",
        "safe_action",
    }:
        semantic, foreground = "workflow", _VISUAL_TOKENS["--sr-forest"]
    elif normalized_role == "trace" and normalized_state in {
        "source_backed",
        "traceable",
        "changed",
    }:
        semantic, foreground = "trace", _VISUAL_TOKENS["--sr-blue"]
    return VisualState(
        role=normalized_role or "unknown",
        state=normalized_state or "unknown",
        semantic=semantic,
        label=_normalized_label(state, label),
        foreground=foreground,
        background=_VISUAL_TOKENS["--sr-surface-muted"],
        border=foreground,
    )


def _validate_safe_route_href(href: str) -> None:
    value = str(href or "").strip()
    parsed = urlsplit(value)
    if (
        not value
        or not value.startswith("?")
        or value.startswith("//")
        or parsed.scheme
        or parsed.netloc
        or parsed.path
        or parsed.fragment
    ):
        raise ValueError("Safe route actions require a same-app query-only URL.")
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    keys = [key for key, _ in pairs]
    if not pairs or any(not key or key not in _CANONICAL_ROUTE_KEYS for key in keys):
        raise ValueError("Safe route actions may use canonical route keys only.")
    if len(keys) != len(set(keys)):
        raise ValueError("Safe route actions cannot repeat a controlled route key.")
    if any(not str(value).strip() for _, value in pairs):
        raise ValueError("Safe route action values cannot be empty.")
    modes = [value for key, value in pairs if key == "mode"]
    if len(modes) != 1 or modes[0] not in {"public", "research", "operator"}:
        raise ValueError("Safe route actions require one canonical workspace mode.")


def _trusted_fragment(value: str) -> HtmlFragment:
    fragment = object.__new__(HtmlFragment)
    object.__setattr__(fragment, "value", str(value))
    object.__setattr__(fragment, "_html_fragment_provenance", _HTML_FRAGMENT_PROVENANCE)
    return fragment


def _fragment(value: HtmlFragment, *, field: str) -> str:
    if (
        type(value) is not HtmlFragment
        or getattr(value, "_html_fragment_provenance", None)
        is not _HTML_FRAGMENT_PROVENANCE
    ):
        raise TypeError(f"{field} accepts trusted HtmlFragment values only.")
    return value.value


def _action_link(action: SafeRouteAction, *, region: bool) -> str:
    aria = (
        f" aria-label='{escape_attribute(action.aria_label)}'"
        if action.aria_label is not None
        else ""
    )
    region_attribute = " data-sr-region='primary-action'" if region else ""
    return (
        f"<a class='sr-primary-action public-primary-action' href='{escape_attribute(action.href)}'"
        f" target='_self'{aria}{region_attribute}>{escape_text(action.label)}</a>"
    )


def workspace_shell_html(
    *,
    mode: str,
    navigation: HtmlFragment | None,
    content: Sequence[HtmlFragment],
) -> HtmlFragment:
    navigation_html = "" if navigation is None else _fragment(navigation, field="navigation")
    content_html = "".join(_fragment(item, field="content") for item in content)
    return _trusted_fragment(
        f"<div class='sr-workspace-shell' data-sr-mode='{escape_attribute(mode)}'>"
        f"{navigation_html}<div class='sr-workspace-content'>{content_html}</div></div>"
    )


def context_bar_html(items: Sequence[tuple[str, str]]) -> HtmlFragment:
    rendered = "".join(
        "<div class='sr-context-item'>"
        f"<dt>{escape_text(label)}</dt><dd>{escape_text(value)}</dd>"
        "</div>"
        for label, value in items
    )
    return _trusted_fragment(
        "<dl class='sr-context-bar' data-sr-region='context' "
        f"aria-label='Workspace context'>{rendered}</dl>"
    )


def page_title_html(*, title: str, purpose: str) -> HtmlFragment:
    return _trusted_fragment(
        "<header class='sr-page-title' data-sr-region='page-title'>"
        f"<h1>{escape_text(title)}</h1><p>{escape_text(purpose)}</p></header>"
    )


def operator_route_shell_html(*, title: str, kind: str) -> HtmlFragment:
    """Render one neutral Operator or compatibility boundary before route detail."""

    normalized_kind = str(kind or "").strip().casefold()
    if normalized_kind not in {"operator", "compatibility"}:
        raise ValueError("Operator route shells require operator or compatibility kind.")
    if normalized_kind == "compatibility":
        kicker = "Compatibility utility"
        purpose = "Retained operator-only output for deterministic regression review."
        warning_title = "Compatibility boundary"
        warning_body = (
            "This legacy utility is excluded from Personal Research Mode and product "
            "conclusions. Analytic labels stay neutral and do not create a recommendation "
            "or transaction direction."
        )
    else:
        kicker = "Operator workspace"
        purpose = "Saved local readiness, maintenance, and review controls."
        warning_title = "Operator boundary"
        warning_body = (
            "This route preserves local controls and evidence context. It does not create "
            "a recommendation, ranking for action, or account action."
        )
    return _trusted_fragment(
        "<section class='sr-operator-route-shell' data-sr-region='operator-shell' "
        f"data-sr-operator-kind='{escape_attribute(normalized_kind)}'>"
        "<header class='sr-operator-route-title' data-sr-region='page-title'>"
        f"<p>{escape_text(kicker)}</p><h1>{escape_text(title)}</h1>"
        f"<span>{escape_text(purpose)}</span></header>"
        "<div class='sr-operator-warning' data-sr-region='operator-warning' role='note' "
        f"data-sr-operator-kind='{escape_attribute(normalized_kind)}'>"
        f"<strong>{escape_text(warning_title)}</strong>"
        f"<span>{escape_text(warning_body)}</span></div></section>"
    )


def answer_panel_html(
    *,
    question: str,
    answer: str,
    reason: str,
    action: SafeRouteAction | None,
    stop_rule: str | None,
) -> HtmlFragment:
    action_html = _action_link(action, region=True) if action is not None else ""
    stop_html = (
        "<p class='sr-stop-rule research-workspace-boundary' data-sr-region='stop-rule'>"
        f"<strong>Research boundary</strong><span>{escape_text(stop_rule)}</span></p>"
        if stop_rule
        else ""
    )
    return _trusted_fragment(
        "<section class='sr-answer-panel' data-sr-region='primary-answer' "
        "aria-label='Primary research answer'>"
        f"<p class='sr-answer-question'>{escape_text(question)}</p>"
        f"<h2>{escape_text(answer)}</h2>"
        f"<p class='sr-answer-reason'>{escape_text(reason)}</p>"
        f"{action_html}{stop_html}</section>"
    )


def status_chip_html(*, role: str, state: str, label: str | None = None) -> HtmlFragment:
    visual = visual_state(role, state, label)
    return _trusted_fragment(
        f"<span class='sr-status-chip sr-status-{escape_attribute(visual.semantic)}' "
        f"data-sr-semantic='{escape_attribute(visual.semantic)}' "
        f"style='--sr-state-fg:{escape_attribute(visual.foreground)};"
        f"--sr-state-bg:{escape_attribute(visual.background)};"
        f"--sr-state-border:{escape_attribute(visual.border)}'>"
        f"{escape_text(visual.label)}</span>"
    )


def evidence_rows_html(rows: Sequence[EvidenceRow]) -> HtmlFragment:
    rendered: list[str] = []
    for row in rows:
        chip = status_chip_html(role=row.role, state=row.state).value
        action = _action_link(row.evidence_action, region=False) if row.evidence_action else ""
        rendered.append(
            "<li class='sr-evidence-row'>"
            f"<div class='sr-evidence-lane'><strong>{escape_text(row.lane)}</strong>{chip}</div>"
            f"<span class='sr-evidence-count'>{escape_text(row.count_or_cutoff)}</span>"
            f"<p>{escape_text(row.reason)}</p>{action}</li>"
        )
    if not rendered:
        rendered.append(
            "<li class='sr-evidence-row sr-evidence-empty'>"
            "No supporting saved evidence is available.</li>"
        )
    return _trusted_fragment(
        "<section class='sr-supporting-evidence' data-sr-region='supporting-evidence' "
        "aria-label='Supporting evidence'><h2>Supporting evidence</h2>"
        f"<ul>{''.join(rendered)}</ul></section>"
    )


def evidence_timeline_html(
    records: Sequence[TimelineRecord],
    *,
    empty_title: str,
    empty_body: str,
    heading: str = "What changed",
    aria_label: str = "Evidence timeline",
) -> HtmlFragment:
    """Render the supplied authoritative order without deriving a latest record."""

    rendered: list[str] = []
    for record in records:
        if type(record) is not TimelineRecord:
            raise TypeError("records accepts TimelineRecord values only.")
        timestamp = str(record.timestamp or "").strip() or "Timestamp unavailable"
        action = (
            _action_link(record.evidence_action, region=False)
            if record.evidence_action is not None
            else ""
        )
        rendered.append(
            "<li class='sr-timeline-record' "
            f"data-timeline-record-id='{escape_attribute(record.record_id)}'>"
            f"<time>{escape_text(timestamp)}</time>"
            f"<strong>{escape_text(record.label)}</strong>"
            f"<p>{escape_text(record.summary)}</p>{action}</li>"
        )
    if not rendered:
        rendered.append(
            "<li class='sr-timeline-empty'>"
            f"<strong>{escape_text(empty_title)}</strong>"
            f"<p>{escape_text(empty_body)}</p></li>"
        )
    return _trusted_fragment(
        "<section class='sr-evidence-timeline' data-sr-region='supporting-evidence' "
        f"aria-label='{escape_attribute(aria_label)}'><h2>{escape_text(heading)}</h2>"
        f"<ol>{''.join(rendered)}</ol></section>"
    )


def detail_disclosure_html(
    summary: str,
    body: Sequence[HtmlFragment],
    *,
    open_by_default: bool = False,
) -> HtmlFragment:
    """Render sealed pure detail without accepting raw trusted HTML."""

    body_html = "".join(_fragment(item, field="body") for item in body)
    open_attribute = " open" if open_by_default else ""
    return _trusted_fragment(
        f"<details class='sr-detail-disclosure' data-sr-region='advanced-detail'{open_attribute}>"
        f"<summary>{escape_text(summary)}</summary>"
        f"<div class='sr-detail-disclosure-body'>{body_html}</div></details>"
    )


def detail_item_html(*, label: str, body: str) -> HtmlFragment:
    """Build escaped prose for a sealed detail disclosure."""

    return _trusted_fragment(
        "<section class='sr-detail-item'>"
        f"<strong>{escape_text(label)}</strong><p>{escape_text(body)}</p></section>"
    )


def next_action_html(action: SafeRouteAction) -> HtmlFragment:
    return _trusted_fragment(_action_link(action, region=True))


def next_step_prompt_html(*, title: str, body: str) -> HtmlFragment:
    """Label an adjacent native control as the route's single next action."""

    return _trusted_fragment(
        "<section class='sr-next-step-prompt'>"
        f"<strong>{escape_text(title)}</strong><span>{escape_text(body)}</span></section>"
    )


def stop_rule_html(rule: str) -> HtmlFragment:
    return _trusted_fragment(
        "<p class='sr-stop-rule research-workspace-boundary' data-sr-region='stop-rule'>"
        f"<strong>Research boundary</strong><span>{escape_text(rule)}</span></p>"
    )


def supporting_detail_html(*, title: str, body: str) -> HtmlFragment:
    return _trusted_fragment(
        "<section class='sr-supporting-intro' data-sr-region='supporting-evidence'>"
        f"<h2>{escape_text(title)}</h2><p>{escape_text(body)}</p></section>"
    )


def empty_state_html(
    *,
    title: str,
    absence: str,
    not_proven: str,
    action: SafeRouteAction | None,
) -> HtmlFragment:
    action_html = _action_link(action, region=True) if action is not None else ""
    return _trusted_fragment(
        "<section class='sr-empty-state' data-sr-region='primary-answer'>"
        f"<h2>{escape_text(title)}</h2><p>{escape_text(absence)}</p>"
        f"<p><strong>This does not prove:</strong> {escape_text(not_proven)}</p>"
        f"{action_html}</section>"
    )


def advanced_detail_marker_html() -> HtmlFragment:
    return _trusted_fragment(
        "<div class='sr-advanced-detail-marker' data-sr-region='advanced-detail'>"
        "Advanced evidence</div>"
    )


def dashboard_visual_system_css() -> str:
    """Return the dependency-free calm institutional workspace stylesheet."""

    tokens = "\n".join(f"  {name}: {value};" for name, value in _VISUAL_TOKENS.items())
    return f"""
:root {{
{tokens}
}}
html, body, .stApp, [data-testid="stAppViewContainer"] {{
  background: var(--sr-canvas) !important;
  color: var(--sr-text) !important;
  font-family: Inter, "SF Pro Text", "Segoe UI", system-ui, sans-serif;
}}
[data-testid="stMainBlockContainer"] {{
  max-width: 76rem !important;
}}
.sr-workspace-shell, .sr-workspace-shell *, [data-sr-region], [data-sr-region] * {{
  box-sizing: border-box;
}}
.sr-workspace-content {{
  display: grid;
  gap: 16px;
  min-width: 0;
}}
.sr-visually-hidden {{
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}}
.sr-context-bar {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
  margin: 0 0 8px;
  padding: 8px 0 12px;
  border-bottom: 1px solid var(--sr-border);
}}
.sr-context-item {{ display: grid; gap: 4px; min-width: 9rem; }}
.sr-context-item dt {{ color: var(--sr-muted); font-size: .75rem; }}
.sr-context-item dd {{ margin: 0; color: var(--sr-text); font-size: .8125rem; font-weight: 650; }}
.sr-page-title {{ max-width: 65ch; margin: 0 0 16px; }}
.sr-page-title h1 {{ margin: 0; color: var(--sr-ink); font-size: 1.75rem; line-height: 1.2; }}
.sr-page-title p {{ margin: 8px 0 0; color: var(--sr-muted); font-size: .9375rem; line-height: 1.5; }}
.sr-operator-route-shell {{
  display: grid;
  gap: 12px;
  margin: 0 0 16px;
  padding: 20px 24px;
  background: var(--sr-surface);
  border: 1px solid var(--sr-border);
  border-radius: 10px;
}}
.sr-operator-route-title {{ display: grid; gap: 6px; min-width: 0; }}
.sr-operator-route-title p {{
  margin: 0;
  color: var(--sr-muted);
  font-size: .75rem;
  font-weight: 750;
  letter-spacing: .04em;
  text-transform: uppercase;
}}
.sr-operator-route-title h1 {{
  margin: 0;
  color: var(--sr-ink);
  font-size: 1.5rem;
  line-height: 1.2;
}}
.sr-operator-route-title span {{ color: var(--sr-muted); font-size: .875rem; line-height: 1.45; }}
.sr-operator-warning {{
  display: grid;
  grid-template-columns: minmax(9rem, auto) minmax(0, 1fr);
  gap: 8px 16px;
  padding: 10px 12px;
  color: var(--sr-text);
  background: var(--sr-surface-muted);
  border-left: 3px solid var(--sr-blue);
  border-radius: 6px;
  font-size: .8125rem;
  line-height: 1.45;
}}
.sr-operator-warning strong {{ color: var(--sr-ink); }}
.command-topbar .command-top-link,
.command-topbar.compact .command-top-link {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;
  white-space: normal;
}}
.stApp:has(.sr-operator-route-shell) .profile-trust-strip.compact {{
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  margin: 0 0 16px;
  padding: 12px;
  color: var(--sr-text);
  background: var(--sr-surface);
  border: 1px solid var(--sr-border);
  border-radius: 8px;
}}
.stApp:has(.sr-operator-route-shell) .profile-trust-strip > span,
.stApp:has(.sr-operator-route-shell) .profile-trust-primary {{
  display: grid;
  align-content: start;
  gap: 4px;
  min-width: 0;
  padding: 0 8px;
  border-left: 1px solid var(--sr-border);
  font-size: .8125rem;
  line-height: 1.4;
  overflow-wrap: anywhere;
}}
.stApp:has(.sr-operator-route-shell) .profile-trust-primary {{
  padding-left: 0;
  border-left: 0;
}}
.stApp:has(.sr-operator-route-shell) .profile-trust-strip small,
.stApp:has(.sr-operator-route-shell) .profile-trust-label {{
  color: var(--sr-muted);
  font-size: .6875rem;
  font-weight: 700;
  line-height: 1.25;
  text-transform: uppercase;
}}
.sr-answer-panel {{
  display: grid;
  gap: 12px;
  max-width: 65rem;
  margin: 0 0 16px;
  padding: 24px;
  background: var(--sr-surface);
  border: 1px solid var(--sr-border);
  border-left: 4px solid var(--sr-forest);
  border-radius: 12px;
}}
.sr-answer-question {{ margin: 0; color: var(--sr-muted); font-size: .8125rem; font-weight: 700; }}
.sr-answer-panel h2 {{ margin: 0; max-width: 50ch; color: var(--sr-ink); font-size: 1.25rem; line-height: 1.35; }}
.sr-answer-reason {{ margin: 0; max-width: 65ch; color: var(--sr-text); font-size: .9375rem; line-height: 1.5; }}
.sr-primary-action, .public-primary-action {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-width: 44px;
  min-height: 44px;
  padding: 8px 16px;
  color: #FFFFFF !important;
  background: var(--sr-forest);
  border: 1px solid var(--sr-forest);
  border-radius: 6px;
  font-weight: 700;
  line-height: 1.35;
  text-decoration: none !important;
  white-space: normal;
}}
.stApp:has(.research-workflow-navigation) [data-testid="stTextInput"] input {{ min-height: 44px; }}
.stApp:has(.public-app-shell) [data-testid="stTextInput"] input {{ min-height: 44px; }}
.sr-stop-rule {{
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 12px 16px;
  color: var(--sr-text);
  background: var(--sr-surface-muted);
  border-left: 3px solid var(--sr-amber);
  border-radius: 6px;
  font-size: .8125rem;
  line-height: 1.5;
}}
.sr-supporting-evidence {{ max-width: 65rem; margin: 0 0 16px; }}
.sr-supporting-evidence h2 {{ margin: 0 0 8px; color: var(--sr-ink); font-size: 1.125rem; }}
.sr-supporting-evidence ul {{ margin: 0; padding: 0; list-style: none; border-top: 1px solid var(--sr-border); }}
.sr-evidence-row {{
  display: grid;
  grid-template-columns: minmax(10rem, 1fr) minmax(10rem, auto) minmax(0, 2fr);
  gap: 8px 16px;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--sr-border);
}}
.sr-evidence-row > * {{ min-width: 0; }}
.sr-evidence-lane {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; min-width: 0; }}
.sr-evidence-row p {{ margin: 0; color: var(--sr-text); overflow-wrap: anywhere; font-size: .8125rem; line-height: 1.5; }}
.sr-evidence-count {{ color: var(--sr-muted); font: .8125rem ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace; }}
.sr-status-chip {{
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 2px 8px;
  color: var(--sr-state-fg);
  background: var(--sr-state-bg);
  border: 1px solid var(--sr-state-border);
  border-radius: 999px;
  font-size: .75rem;
  font-weight: 700;
  line-height: 1.35;
}}
.sr-next-step-prompt {{
  display: grid;
  gap: 4px;
  min-height: 44px;
  max-width: 65rem;
  padding: 10px 16px;
  color: var(--sr-text);
  background: var(--sr-surface);
  border-left: 4px solid var(--sr-forest);
  border-radius: 6px;
}}
.sr-next-step-prompt strong {{ color: var(--sr-ink); font-size: .8125rem; }}
.sr-next-step-prompt span {{ color: var(--sr-muted); font-size: .8125rem; line-height: 1.5; }}
.sr-supporting-intro {{ max-width: 65rem; padding-top: 4px; }}
.sr-supporting-intro h2 {{ margin: 0 0 4px; color: var(--sr-ink); font-size: 1.125rem; }}
.sr-supporting-intro p {{ margin: 0; color: var(--sr-muted); font-size: .8125rem; line-height: 1.5; }}
.sr-evidence-timeline {{ max-width: 65rem; }}
.sr-evidence-timeline h2 {{ margin: 0 0 8px; color: var(--sr-ink); font-size: 1.125rem; }}
.sr-evidence-timeline ol {{
  display: grid;
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--sr-border);
}}
.sr-timeline-record, .sr-timeline-empty {{
  display: grid;
  grid-template-columns: minmax(9rem, auto) minmax(10rem, .8fr) minmax(0, 2fr);
  gap: 8px 16px;
  align-items: start;
  padding: 12px 0;
  border-bottom: 1px solid var(--sr-border);
  content-visibility: auto;
  contain-intrinsic-size: auto 72px;
}}
.sr-timeline-record time {{ color: var(--sr-muted); font: .8125rem ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace; }}
.sr-timeline-record strong, .sr-timeline-empty strong {{ color: var(--sr-ink); font-size: .8125rem; }}
.sr-timeline-record p, .sr-timeline-empty p {{ margin: 0; color: var(--sr-text); font-size: .8125rem; line-height: 1.5; overflow-wrap: anywhere; }}
.sr-timeline-empty {{ grid-template-columns: 1fr; }}
.sr-detail-disclosure {{ max-width: 65rem; border-top: 1px solid var(--sr-border); }}
.sr-detail-disclosure summary {{ min-height: 44px; padding: 12px 0; color: var(--sr-ink); font-weight: 700; cursor: pointer; }}
.sr-detail-disclosure-body {{ display: grid; gap: 12px; padding: 0 0 16px; }}
.sr-detail-item {{ display: grid; gap: 4px; }}
.sr-detail-item strong {{ color: var(--sr-ink); font-size: .8125rem; }}
.sr-detail-item p {{ margin: 0; color: var(--sr-text); font-size: .8125rem; line-height: 1.5; }}
.sr-advanced-detail-marker {{
  height: 1px;
  overflow: hidden;
  color: transparent;
}}
.research-workflow-navigation {{
  position: fixed !important;
  z-index: 20;
  top: 16px;
  left: 16px;
  display: grid !important;
  align-content: start;
  gap: 8px !important;
  width: clamp(12.5rem, 16vw, 14.5rem) !important;
  max-height: calc(100vh - 32px);
  padding: 16px !important;
  overflow-y: auto;
  background: var(--sr-nav) !important;
  border: 1px solid var(--sr-nav) !important;
  border-radius: 10px !important;
}}
.stApp:has(.research-workflow-navigation) [data-testid="stSidebar"] {{
  display: none !important;
}}
.stApp:has(.research-workflow-navigation) [data-testid="stMain"] {{
  margin-left: 0 !important;
}}
.stApp:has(.research-workflow-navigation) [data-testid="stMainBlockContainer"] {{
  padding-left: calc(clamp(12.5rem, 16vw, 14.5rem) + 40px) !important;
}}
.research-workflow-routes {{ display: grid; gap: 4px; }}
.research-workspace-brand {{
  display: grid;
  align-content: center;
  min-height: 44px;
  color: var(--sr-nav-text) !important;
  text-decoration: none !important;
}}
.research-workspace-brand span {{ color: var(--sr-nav-muted); font-size: .75rem; }}
.research-workspace-brand strong {{ color: var(--sr-nav-text); font-size: .8125rem; line-height: 1.35; }}
.research-workflow-navigation .research-workflow-link, .research-workflow-disabled {{
  display: flex;
  align-items: center;
  min-width: 44px;
  min-height: 44px;
  padding: 8px 12px;
  color: var(--sr-nav-text) !important;
  border: 1px solid transparent;
  border-radius: 6px;
  font-size: .8125rem;
  font-weight: 650;
  line-height: 1.35;
  text-decoration: none !important;
  white-space: normal;
}}
.research-workflow-navigation .research-workflow-link[aria-current="page"] {{
  background: rgba(248, 250, 252, .12) !important;
  border-color: var(--sr-nav-text) !important;
  color: var(--sr-nav-text) !important;
}}
.research-workflow-disabled {{ position: relative; color: var(--sr-nav-muted) !important; opacity: .82; cursor: not-allowed; }}
.research-workspace-mode {{
  display: grid;
  gap: 4px;
  padding-top: 12px;
  border-top: 1px solid rgba(248, 250, 252, .24);
}}
.research-workspace-mode > span {{ color: var(--sr-nav-muted); font-size: .75rem; }}
.research-workspace-mode a {{
  display: flex;
  align-items: center;
  min-width: 44px;
  min-height: 44px;
  color: var(--sr-nav-text) !important;
  font-size: .8125rem;
}}
.public-app-shell, .research-workspace-header, .research-desk-brief {{ box-shadow: none !important; }}
.research-workspace-header {{
  margin-bottom: 16px !important;
  padding: 0 !important;
  background: transparent !important;
  border: 0 !important;
}}
.research-desk-brief[aria-label="Today's Research Brief"] {{
  margin: 0 0 16px !important;
  padding: 0 !important;
  background: transparent !important;
  border: 0 !important;
}}
.public-app-nav a {{ min-width: 44px; min-height: 44px; white-space: normal; }}
.public-app-shell .public-workspace-mode {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  color: var(--sr-muted);
  font-size: .8125rem;
}}
.public-app-shell .public-workspace-mode a {{ color: var(--sr-forest) !important; min-height: 44px; display: inline-flex; align-items: center; }}
.public-skip-link:focus-visible, a:focus-visible, button:focus-visible,
input:focus-visible, select:focus-visible, textarea:focus-visible, summary:focus-visible,
[role="button"]:focus-visible, [data-sr-region]:focus-visible,
.sr-evidence-timeline ol:focus-visible {{
  outline: 3px solid var(--sr-focus) !important;
  outline-offset: 3px !important;
}}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"],
  .stApp:has(.research-workflow-navigation) [data-testid="stMainBlockContainer"] {{
    width: 100% !important;
    max-width: 100% !important;
    padding: 8px 12px 32px !important;
  }}
  .research-workflow-navigation {{
    position: static !important;
    display: flex !important;
    align-items: stretch;
    width: 100% !important;
    max-width: 100% !important;
    min-height: 44px;
    padding: 8px !important;
    overflow-x: auto;
    overflow-y: visible;
    border-radius: 10px;
  }}
  .research-workspace-brand {{ flex: 0 0 10rem; }}
  .research-workflow-routes, .research-workspace-mode {{ display: flex; gap: 4px; flex: 0 0 auto; }}
  .research-workspace-mode {{ padding: 0 0 0 8px; border-top: 0; border-left: 1px solid rgba(248, 250, 252, .24); }}
  .research-workspace-mode > span {{ align-self: center; padding: 0 4px; }}
  .research-workflow-navigation .research-workflow-link, .research-workflow-disabled, .research-workspace-mode a {{ flex: 0 0 auto !important; max-width: 11rem; }}
  .sr-context-bar {{ gap: 8px 16px; }}
  .sr-context-item {{ min-width: min(9rem, 100%); }}
  .sr-page-title h1 {{ font-size: 1.375rem; }}
  .sr-operator-route-shell {{ gap: 10px; padding: 16px; }}
  .sr-operator-route-title h1 {{ font-size: 1.25rem; }}
  .sr-operator-warning {{ grid-template-columns: 1fr; gap: 4px; }}
  .stApp:has(.sr-operator-route-shell) .profile-trust-strip.compact {{
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px 0;
    padding: 10px;
  }}
  .stApp:has(.sr-operator-route-shell) .profile-trust-strip > :nth-child(odd) {{
    padding-left: 0;
    border-left: 0;
  }}
  .sr-answer-panel {{ gap: 12px; padding: 16px; }}
  .sr-answer-panel h2 {{ font-size: 1.0625rem; }}
  .sr-primary-action, .public-primary-action {{ width: 100%; }}
  .sr-evidence-row, .sr-timeline-record {{ grid-template-columns: 1fr; }}
}}
@media (forced-colors: active) {{
  .public-app-nav a[aria-current="page"],
  .research-workflow-link[aria-current="page"],
  [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked),
  .sr-status-chip,
  .sr-stop-rule {{
    border: 2px solid CanvasText;
    outline: 1px solid CanvasText;
    outline-offset: -4px;
  }}
  .public-skip-link:focus-visible, a:focus-visible, button:focus-visible {{
    outline: 3px solid Highlight !important;
  }}
}}
@media (prefers-reduced-motion: reduce) {{
  .stApp, .stApp *, .stApp *::before, .stApp *::after {{
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
    transition-delay: 0ms !important;
    scroll-behavior: auto !important;
  }}
}}
""".strip()


def legacy_research_accessibility_css() -> str:
    """Return the frozen Research-only media preference fallback CSS."""

    return """
@media (forced-colors: active) {
  .stApp a:focus-visible,
  .stApp button:focus-visible,
  .stApp input:focus-visible,
  .stApp select:focus-visible,
  .stApp textarea:focus-visible,
  .stApp [role="button"]:focus-visible,
  .stApp [role="radio"]:focus-visible,
  .stApp [role="tab"]:focus-visible,
  .stApp summary:focus-visible,
  .stApp [tabindex]:not([tabindex="-1"]):focus-visible {
    outline: 3px solid Highlight !important;
    outline-offset: 3px !important;
    box-shadow: none !important;
  }
  .research-workflow-link[aria-current='page'] {
    border: 2px solid Highlight !important;
    outline: 1px solid CanvasText !important;
    outline-offset: -4px !important;
  }
  .research-workspace-boundary,
  .observation-recency-summary,
  .research-state-message,
  .signal-card {
    border-color: CanvasText !important;
  }
  .research-workspace-boundary {
    border-style: solid !important;
    border-width: 1px !important;
    border-radius: 4px;
    padding: 0.2rem 0.35rem;
  }
}
@media (prefers-reduced-motion: reduce) {
  .stApp,
  .stApp *,
  .stApp *::before,
  .stApp *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    transition-delay: 0ms !important;
    scroll-behavior: auto !important;
  }
}
""".strip()


def render_stylesheet(css: str) -> str:
    """Wrap already-composed CSS in the exact stylesheet DOM envelope."""

    return f"<style>{css}</style>"


def escape_text(value: object) -> str:
    """Escape a value at an HTML text boundary."""

    return html.escape(str(value), quote=False)


def escape_attribute(value: object) -> str:
    """Escape a value at a quoted HTML attribute boundary."""

    return html.escape(str(value), quote=True)
