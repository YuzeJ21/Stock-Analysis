from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from streamlit.testing.v1 import AppTest

from src.paths import resolve_project_root


@dataclass(frozen=True)
class DashboardRenderRoute:
    name: str
    query_params: tuple[tuple[str, str], ...]
    required_markers: tuple[str, ...]
    required_regions: tuple[str, ...] = ()


@dataclass(frozen=True)
class DashboardRenderResult:
    name: str
    exceptions: tuple[str, ...]
    missing_markers: tuple[str, ...]
    forbidden_markers: tuple[str, ...] = ()
    expanded_advanced: tuple[str, ...] = ()
    rendered_blocks: tuple[str, ...] = ()
    missing_regions: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not (
            self.exceptions
            or self.missing_markers
            or self.forbidden_markers
            or self.expanded_advanced
            or self.missing_regions
        )


FORBIDDEN_RENDER_MARKERS: tuple[str, ...] = (
    "Traceback (most recent call last)",
    "ArrowInvalid",
    "ModuleNotFoundError",
    "ImportError:",
    "SYN1",
    "SYN2",
    "SYN3",
    "SYN4",
    "SYN5",
)


PUBLIC_RENDER_ROUTES: tuple[DashboardRenderRoute, ...] = (
    DashboardRenderRoute(
        name="Home",
        query_params=(("mode", "public"),),
        required_markers=("What is this product and where do I start?", "Research-only", "No data, no conclusion", "Start with Stock Selector"),
    ),
    DashboardRenderRoute(
        name="Stock Selector",
        query_params=(("mode", "public"), ("page", "stock-selector")),
        required_markers=("Stock Selector", "Which stock can I review?", "Research-only"),
    ),
    DashboardRenderRoute(
        name="Single-Stock Report",
        query_params=(
            ("mode", "public"),
            ("page", "single-stock-report"),
            ("ticker", "NVDA"),
            ("open", "1"),
        ),
        required_markers=("What can I use for this ticker right now?", "NVDA", "Open Data Health"),
    ),
    DashboardRenderRoute(
        name="Data Health",
        query_params=(("mode", "public"), ("page", "data-health")),
        required_markers=("Price / setup", "Fundamentals / DCF", "Peers", "Optional inputs"),
    ),
    DashboardRenderRoute(
        name="Proof History",
        query_params=(("mode", "public"), ("page", "proof-history")),
        required_markers=("Newest reviewed evidence",),
    ),
)


RESEARCH_RENDER_ROUTES: tuple[DashboardRenderRoute, ...] = (
    DashboardRenderRoute(
        name="Research Desk",
        query_params=(("mode", "research"),),
        required_markers=(
            "Research Desk",
            "Today's Research Brief",
            "What needs my attention today?",
            "Open Data Health",
            "market-complete event feed",
            "Research-only",
        ),
        required_regions=(
            "workflow-nav",
            "context",
            "page-title",
            "primary-answer",
            "primary-action",
            "stop-rule",
            "supporting-evidence",
            "advanced-detail",
        ),
    ),
    DashboardRenderRoute(
        name="Discover",
        query_params=(("mode", "research"), ("page", "discover")),
        required_markers=(
            "Discover",
            "Focused cohort",
            "Find a Company",
            "Screen eligibility — when supported",
            "Browse saved companies",
            "Research-only",
        ),
    ),
    DashboardRenderRoute(
        name="Company Workbench",
        query_params=(
            ("mode", "research"),
            ("page", "company-workbench"),
            ("ticker", "NVDA"),
            ("open", "1"),
        ),
        required_markers=(
            "Company Workbench",
            "Company Brief",
            "Use now",
            "Still withheld",
            "What changed",
            "Next research task",
            "Open evidence and analysis modules",
            "Advanced Evidence",
            "Research-only",
        ),
    ),
    DashboardRenderRoute(
        name="Monitor",
        query_params=(("mode", "research"), ("page", "monitor")),
        required_markers=("Monitor", "Follow-up Queue", "Research-only"),
    ),
    DashboardRenderRoute(
        name="Research Data Health",
        query_params=(
            ("mode", "research"),
            ("page", "data-health"),
            ("ticker", "NVDA"),
            ("lane", "peers"),
            ("drawer", "proof"),
        ),
        required_markers=(
            "Data Health",
            "What can I use and what stays unavailable?",
            "Return to Company Workbench",
            "Selected Lane Answer",
            "trusted peer mapping proof",
            "Research-only",
        ),
        required_regions=(
            "workflow-nav",
            "context",
            "page-title",
            "primary-answer",
            "primary-action",
            "stop-rule",
            "supporting-evidence",
            "advanced-detail",
        ),
    ),
    DashboardRenderRoute(
        name="Research Proof History",
        query_params=(("mode", "research"), ("page", "proof-history"), ("ticker", "NVDA")),
        required_markers=(
            "Proof History",
            "What evidence changed a readiness state?",
            "Return to Company Workbench",
            "Newest reviewed evidence",
            "Research-only",
        ),
        required_regions=(
            "workflow-nav",
            "context",
            "page-title",
            "primary-answer",
            "primary-action",
            "stop-rule",
            "supporting-evidence",
            "advanced-detail",
        ),
    ),
)


def _rendered_blocks(app: AppTest) -> tuple[str, ...]:
    collections = (
        "markdown",
        "text",
        "caption",
        "title",
        "header",
        "subheader",
        "error",
        "exception",
    )
    values: list[str] = []
    for collection in collections:
        for item in getattr(app, collection):
            value = getattr(item, "value", "")
            if value:
                values.append(str(value))
    for item in app.button:
        label = getattr(item, "label", "")
        if label:
            values.append(str(label))
    return tuple(values)


def _rendered_markdown(app: AppTest) -> str:
    return "\n".join(_rendered_blocks(app))


def _expanded_advanced_sections(app: AppTest) -> tuple[str, ...]:
    return tuple(
        str(item.label)
        for item in app.expander
        if str(item.label).lower().startswith("advanced") and bool(item.proto.expanded)
    )


def render_public_routes(
    base_dir: Path | str | None = None,
    *,
    routes: Iterable[DashboardRenderRoute] = PUBLIC_RENDER_ROUTES,
    timeout: int = 120,
) -> list[DashboardRenderResult]:
    root = resolve_project_root(base_dir)
    dashboard_path = root / "src" / "dashboard.py"
    results: list[DashboardRenderResult] = []

    for route in routes:
        app = AppTest.from_file(str(dashboard_path), default_timeout=timeout)
        app.query_params.update(dict(route.query_params))
        app.run(timeout=timeout)
        rendered_blocks = _rendered_blocks(app)
        rendered = "\n".join(rendered_blocks)
        exceptions = tuple(str(item.value) for item in app.exception)
        missing_markers = tuple(marker for marker in route.required_markers if marker not in rendered)
        forbidden_markers = tuple(marker for marker in FORBIDDEN_RENDER_MARKERS if marker in rendered)
        missing_regions = tuple(
            region
            for region in route.required_regions
            if rendered.count(f"data-sr-region='{region}'") != 1
        )
        results.append(
            DashboardRenderResult(
                name=route.name,
                exceptions=exceptions,
                missing_markers=missing_markers,
                forbidden_markers=forbidden_markers,
                expanded_advanced=_expanded_advanced_sections(app),
                rendered_blocks=rendered_blocks,
                missing_regions=missing_regions,
            )
        )

    return results


def render_dashboard_smoke(
    results: Iterable[DashboardRenderResult],
    *,
    contract_name: str = "Dashboard render smoke",
) -> str:
    lines = [
        contract_name,
        "Read-only: renders the selected route contract with Streamlit AppTest; it does not refresh data, import rows, apply changes, stage files, commit, or push.",
    ]
    for result in results:
        status = "passed" if result.passed else "failed"
        lines.append(f"- {result.name}: {status}")
        if result.exceptions:
            lines.append(f"  exceptions: {' | '.join(result.exceptions)}")
        if result.missing_markers:
            lines.append(f"  missing markers: {', '.join(result.missing_markers)}")
        if result.forbidden_markers:
            lines.append(f"  forbidden markers: {', '.join(result.forbidden_markers)}")
        if result.expanded_advanced:
            lines.append(f"  expanded advanced sections: {', '.join(result.expanded_advanced)}")
        if result.missing_regions:
            lines.append(f"  missing or duplicated regions: {', '.join(result.missing_regions)}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the public Streamlit routes without starting a long-lived server.")
    parser.add_argument("--root", default=".", help="Project root containing src/dashboard.py")
    parser.add_argument(
        "--routes",
        choices=("public", "research"),
        default="public",
        help="Route contract to render.",
    )
    args = parser.parse_args()

    routes = RESEARCH_RENDER_ROUTES if args.routes == "research" else PUBLIC_RENDER_ROUTES
    contract_name = "Research dashboard render smoke" if args.routes == "research" else "Dashboard render smoke"
    results = render_public_routes(Path(args.root), routes=routes)
    print(render_dashboard_smoke(results, contract_name=contract_name))
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
