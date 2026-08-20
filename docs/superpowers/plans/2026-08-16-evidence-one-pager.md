# Evidence One-Pager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an auditable Evidence One-Pager to the front of the existing Company Workbench HTML Research Brief without changing routes, calculations, readiness, persistence, or the complete report.

**Architecture:** Extend the existing pure `CompanyWorkbenchHtmlSnapshot` only with an explicitly scoped, already-computed What changed answer. Add one pure summary projector inside `src/company_workbench_html.py`, compose it before the existing full-report content in both fragment and document renderers, and pass the existing Workbench change object from `src/dashboard.py`. Extend the current offline browser gate rather than creating another report or verification engine.

**Tech Stack:** Python 3.12, frozen dataclasses, deterministic HTML/CSS, Streamlit, pytest, Playwright with local Chrome, repository fingerprint guards.

## Global Constraints

- Work only in `/Users/yjian070/Documents/New project/.worktrees/evidence-one-pager` on `codex/evidence-one-pager`.
- Preserve `data/`, `outputs/`, and `docs/assets/` byte-for-byte and do not stage them.
- Never use `git add -A`; stage only the named files for each task.
- The existing Workbench, module gate, full HTML report, download label, MIME type, filename convention, CSP, session behavior, and every existing research function remain available.
- The one-pager selects and formats already-frozen values only; it performs no file I/O, provider call, refresh, readiness rebuild, calculation, ledger append, or repository write.
- Missing, unsafe, stale, unverified, mismatched, excluded, or rights-blocked evidence remains independently `partial`, `not_recorded`, or `withheld`.
- Do not add `Certified`, ownership language, recommendations, rankings, target prices, spot comparisons, upside/downside, probabilities, confidence-looking precision, sizing, allocation, entry/exit, or transaction language.
- Do not add Blue Sky, capital-allocation metrics, company-specific KPIs, generated claims, generated thesis prose, or generated falsifiers.
- `source_backed` What changed content remains `partial` in this slice because portable publication/retrieval dates, rights, field scope, and cutoff proof are not frozen.
- Reuse the current `per_share_state` display decision and show the existing `share_basis_state`; do not introduce a new readiness rule.
- “One-Pager” means a bounded summary section, not a guaranteed single printed sheet; never clip, truncate, or shrink evidence to force page count.
- Local automation is engineering evidence only, not source-rights, current-market, hosted, human-accessibility, market-fit, or investment-performance proof.

**Pre-execution prerequisite:** this reviewed plan must itself be committed by
named path on `codex/evidence-one-pager` before Task 0 starts. Task 0 must not
waive or ignore an untracked plan file.

---

### Task 0: Re-establish exact branch and protected-artifact truth

**Files:**
- Create only temporary manifests under `/tmp`; modify no repository file.

- [ ] **Step 1: Verify the isolated execution boundary**

Run:

```bash
pwd
git status --short --branch
git rev-parse HEAD
git merge-base --is-ancestor 9147a47c327774e31e5ad76a370561b572d3ccbd HEAD
git rev-list --left-right --count origin/main...HEAD
git diff --check
```

Expected: exact worktree
`/Users/yjian070/Documents/New project/.worktrees/evidence-one-pager`, branch
`codex/evidence-one-pager`, approved design and implementation-plan commits on
top of the named `origin/main` base, no staged/untracked files, and clean diff
hygiene. Stop if another byte is present; classify it before continuing.

- [ ] **Step 2: Capture the before-state for every protected path**

Write a sorted relative-path/type/SHA-256 manifest for every file, directory,
and symlink under `data/`, `outputs/`, and `docs/assets/` to a fresh named
directory under `/tmp`. Record the manifest path and SHA-256 in the execution
log. Do not follow symlinks and do not create any file under those protected
trees.

- [ ] **Step 3: Record the reference image identity without copying it**

```bash
shasum -a 256 /var/folders/cw/xfqgmp_57rn7nn3fq68z_6280000gn/T/codex-clipboard-80b40520-4c8b-493e-89af-a87e159e329b.png
```

Expected:
`d467ce50f7803b3a269b5cfd748a87c1ce4a269345943ca6993d365056c72d59`.
If missing or different, continue code work but mark visual closeout blocked
until the owner reattaches the exact image.

---

### Task 1: Freeze the scoped What changed answer

**Files:**
- Modify: `src/company_workbench_html.py:51-176,567-604`
- Modify: `tests/test_company_workbench_html.py:1-230`

**Interfaces:**
- Consumes: `CompanyWorkbenchHtmlInputs.change_answer`, `.change_ticker`, and `.change_profile_key` supplied by Task 4.
- Produces: a four-item `CompanyWorkbenchHtmlSnapshot.answers` tuple ordered `Use now`, `Still withheld`, `What changed`, `Next research task`; the What changed `HtmlBriefAnswer` carries safe source references and blockers.

- [ ] **Step 1: Add failing snapshot tests for scoped change states**

Add a default change mapping to `_inputs(...)` and tests that prove exact scope, order, state, references, and failure behavior:

```python
def _change(**changes: object) -> dict[str, object]:
    row: dict[str, object] = {
        "state": "review_now",
        "answer": "1 unresolved source-backed change needs review.",
        "next_task": "Review the changed filing evidence.",
        "source_refs": ("https://sec.example/change",),
        "source_backed_eligible": True,
        "change_context_kind": "source_backed",
    }
    row.update(changes)
    return row


def test_snapshot_freezes_four_scoped_answers_without_promoting_source_backed_change():
    snapshot = build_company_workbench_html_snapshot(_inputs())

    assert [answer.label for answer in snapshot.answers] == [
        "Use now",
        "Still withheld",
        "What changed",
        "Next research task",
    ]
    changed = snapshot.answers[2]
    assert changed.state == "partial"
    assert changed.title == "1 unresolved source-backed change needs review."
    assert changed.body == "Review the changed filing evidence."
    assert [reference.href for reference in changed.source_refs] == [
        "https://sec.example/change"
    ]
    assert any("portable publication" in blocker.lower() for blocker in changed.blockers)


@pytest.mark.parametrize(
    ("kind", "eligible", "expected"),
    (
        ("none", False, "not_recorded"),
        ("snapshot_only", False, "partial"),
        ("source_backed", True, "partial"),
        ("unknown", True, "withheld"),
    ),
)
def test_snapshot_maps_change_context_without_inheriting_workflow_state(kind, eligible, expected):
    inputs = _inputs(change_answer=_change(change_context_kind=kind, source_backed_eligible=eligible))
    assert build_company_workbench_html_snapshot(inputs).answers[2].state == expected


@pytest.mark.parametrize("kind", ("none", "unknown"))
def test_snapshot_clears_claim_and_references_for_none_or_unknown_context(kind):
    changed = build_company_workbench_html_snapshot(
        _inputs(change_answer=_change(change_context_kind=kind))
    ).answers[2]
    assert changed.title == "No portable change answer."
    assert changed.body == "No scoped saved change answer is available."
    assert changed.source_refs == ()
    assert "unresolved source-backed" not in repr(changed).lower()


@pytest.mark.parametrize(
    ("ticker", "profile"),
    (("AMD", "demo"), ("NVDA", "other"), ("", "demo")),
)
def test_snapshot_rejects_unscoped_or_mismatched_change_answer(ticker, profile):
    snapshot = build_company_workbench_html_snapshot(
        _inputs(change_ticker=ticker, change_profile_key=profile)
    )
    changed = snapshot.answers[2]
    assert changed.state == "not_recorded"
    assert changed.source_refs == ()
    assert "changed filing" not in repr(changed).lower()


def test_snapshot_sanitizes_change_copy_state_and_references():
    snapshot = build_company_workbench_html_snapshot(
        _inputs(
            change_answer=_change(
                state="invented-state<script>",
                answer="<script>alert(1)</script>",
                next_task="buy this stock now",
                source_refs=(
                    "javascript:alert(1)",
                    "https://sec.example/change",
                ),
            )
        )
    )
    changed = snapshot.answers[2]
    assert changed.state == "withheld"
    assert changed.badges == ()
    assert "<script" not in repr(changed).lower()
    assert "buy this stock" not in repr(changed).lower()
    assert changed.source_refs == ()
    assert changed.title == "No portable change answer."


@pytest.mark.parametrize(
    "source_ref",
    (
        "sec:accession",
        "sec-accession:0001045810-26-000021",
        "consensus://nvda/fy2027-q2/2026-07-15",
        "sec_companyfacts",
        "sec_companyfacts; sec_filing_document",
        "yfinance_research_grade; sec_filing_document",
    ),
)
def test_snapshot_keeps_real_opaque_source_ref_partial_but_does_not_expose_it(
    source_ref,
):
    changed = build_company_workbench_html_snapshot(
        _inputs(change_answer=_change(source_refs=(source_ref,)))
    ).answers[2]
    assert changed.state == "partial"
    assert changed.source_refs == ()
    assert any("reference is incomplete" in blocker.lower() for blocker in changed.blockers)


@pytest.mark.parametrize(
    "unsafe_ref",
    (
        "http://example.com/change",
        "/etc/passwd",
        "src/private-change.txt",
        "file:///tmp/change",
        "consensus://nvda/../../private",
    ),
)
def test_snapshot_withholds_mixed_valid_and_unsafe_change_references(unsafe_ref):
    changed = build_company_workbench_html_snapshot(
        _inputs(
            change_answer=_change(
                source_refs=("https://sec.example/change", unsafe_ref)
            )
        )
    ).answers[2]
    assert changed.state == "withheld"
    assert changed.source_refs == ()
    assert changed.title == "No portable change answer."
```

Update `_inputs(...)` defaults with:

```python
change_answer=_change(),
change_ticker="NVDA",
change_profile_key="demo",
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_company_workbench_html.py \
  -k 'four_scoped_answers or maps_change_context or clears_claim or rejects_unscoped or sanitizes_change or real_opaque_source_ref or withholds_mixed_valid'
```

Expected: collection or assertion failure because `CompanyWorkbenchHtmlInputs` has no change fields and the snapshot still has three answers.

- [ ] **Step 3: Implement the minimal frozen change projection**

Import `field` beside `asdict`, `dataclass`, `is_dataclass`, and `replace`, and
import `urlsplit` beside the existing URL parsing helpers.
Extend the dataclasses. Put the three new inputs at the end with fail-closed
defaults so Tasks 1-3 cannot break the existing dashboard constructor before
Task 4 supplies explicit scope:

```python
@dataclass(frozen=True)
class HtmlBriefAnswer:
    label: str
    title: str
    body: str
    state: str
    badges: tuple[str, ...]
    source_refs: tuple[HtmlBriefSafeReference, ...] = ()
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompanyWorkbenchHtmlInputs:
    report_payload: Mapping[str, object]
    profile_context: ProfileContext
    observation_recency: ObservationRecencySet | None
    selected_answer: Mapping[str, object]
    authoritative_task: Mapping[str, object]
    scenario_lab_result: ScenarioLabResult | None
    nowcast_packet: Mapping[str, object] | None
    decision_lab_state: ResearchDecisionLabState
    quarterly_trend: QuarterlyTrendPacket
    forward_view: ForwardViewPacket
    journal_state: JournalState | None
    valuation_regime: ValuationRegimePacket
    catalyst_timeline: CatalystTimeline
    change_answer: Mapping[str, object] = field(default_factory=dict)
    change_ticker: str = ""
    change_profile_key: str = ""
```

Do not add a profile-key field to `CompanyWorkbenchHtmlSnapshot`. The approved
extension permits only the normalized What changed answer to be added to the
snapshot. Validate the supplied profile key against the selected
`ProfileContext.profile_key` before projection; the resulting normalized,
scoped answer is then included in the existing deterministic snapshot hash.

Add pure fail-closed helpers and use the result between Still withheld and Next
research task. `none`, unknown, unscoped, or unsafe input must never retain the
supplied claim or source reference under a weaker state label:

```python
def _neutral_change_answer(*, state: str, blocker: str) -> HtmlBriefAnswer:
    return HtmlBriefAnswer(
        "What changed",
        "No portable change answer.",
        "No scoped saved change answer is available.",
        state,
        (),
        (),
        (blocker,),
    )


def _portable_change_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    raw = value.strip()
    if not raw or "<" in raw or ">" in raw:
        return ""
    safe = safe_html_brief_text(raw)
    return "" if not safe or safe == _WITHHELD_ACTION else safe


def _benign_incomplete_change_reference(raw: str) -> bool:
    if len(raw) > 512:
        return False
    if re.fullmatch(r"sec:[A-Za-z0-9][A-Za-z0-9._-]{0,127}", raw):
        return True
    if re.fullmatch(
        r"sec-accession:[A-Za-z0-9][A-Za-z0-9._-]{0,127}", raw
    ):
        return True
    source_tokens = tuple(part.strip() for part in raw.split(";"))
    if 1 <= len(source_tokens) <= 8 and all(
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", part)
        for part in source_tokens
    ):
        return True
    try:
        parsed = urlsplit(raw)
        path_parts = tuple(part for part in parsed.path.split("/") if part)
        return bool(
            parsed.scheme == "consensus"
            and parsed.hostname
            and re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9.-]{0,127}", parsed.hostname
            )
            and not parsed.username
            and not parsed.password
            and parsed.port is None
            and not parsed.query
            and not parsed.fragment
            and path_parts
            and all(
                part not in {".", ".."}
                and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", part)
                for part in path_parts
            )
        )
    except ValueError:
        return False


def _change_reference_is_unsafe(value: object) -> bool:
    if not isinstance(value, str):
        return True
    raw = value.strip()
    if not raw or "<" in raw or ">" in raw or "\\" in raw:
        return True
    if any(unicodedata.category(char) == "Cc" for char in raw):
        return True
    if _SECRET_PATTERN.search(raw):
        return True
    if _benign_incomplete_change_reference(raw):
        return False
    return not bool(
        safe_html_brief_reference(
            {"label": "Change source", "href": raw}
        ).href
    )


def _portable_change_answer(
    inputs: CompanyWorkbenchHtmlInputs,
    ticker: str,
) -> HtmlBriefAnswer:
    scoped = _ticker_matches(inputs.change_ticker, ticker) and _profile_matches(
        inputs.change_profile_key,
        inputs.profile_context.profile_key,
    )
    change = _mapping(inputs.change_answer)
    if not scoped or not change:
        return _neutral_change_answer(
            state="not_recorded",
            blocker="Portable change scope is absent or mismatched.",
        )

    raw_context_kind = str(change.get("change_context_kind") or "").strip().lower()
    if raw_context_kind == "none":
        return _neutral_change_answer(
            state="not_recorded",
            blocker="No source-backed or snapshot-only change is recorded.",
        )
    if raw_context_kind not in {"snapshot_only", "source_backed"}:
        return _neutral_change_answer(
            state="withheld",
            blocker="Portable change context is unsupported.",
        )

    raw_workflow_state = str(change.get("state") or "").strip().lower()
    title = _portable_change_text(change.get("answer"))
    body = _portable_change_text(change.get("next_task"))
    refs: list[HtmlBriefSafeReference] = []
    refs_incomplete = False
    raw_refs = change.get("source_refs")
    refs_unsafe = raw_refs is not None and not isinstance(raw_refs, (list, tuple))
    for index, raw in enumerate(raw_refs if isinstance(raw_refs, (list, tuple)) else ()):
        if _change_reference_is_unsafe(raw):
            refs_unsafe = True
            continue
        safe = safe_html_brief_reference(
            {"label": f"Change source {index + 1}", "href": raw}
        )
        if safe.href and safe not in refs:
            refs.append(safe)
        elif not safe.href:
            refs_incomplete = True

    content_safe = (
        raw_workflow_state in {"monitor", "review_now", "wait_for_evidence"}
        and bool(title)
        and bool(body)
        and not refs_unsafe
    )
    if not content_safe:
        return _neutral_change_answer(
            state="withheld",
            blocker="Portable change content, workflow state, or reference is unsafe.",
        )

    if raw_context_kind == "snapshot_only":
        state = "partial"
        refs = []
        blockers = ("Change context is snapshot-only.",)
    else:
        state = "partial"
        blockers = (
            "Portable publication and retrieval dates, rights, field scope, and cutoff proof are not frozen."
            if (
                change.get("source_backed_eligible") is True
                and refs
                and not refs_incomplete
            )
            else "Portable source-backed change eligibility or reference is incomplete."
        ,)

    return HtmlBriefAnswer(
        "What changed",
        title,
        body,
        state,
        tuple(
            safe_html_brief_text(item)
            for item in (raw_workflow_state, raw_context_kind)
            if safe_html_brief_text(item)
        ),
        tuple(refs),
        blockers,
    )
```

Construct `answers` in this exact order:

```python
answers = (
    HtmlBriefAnswer("Use now", "Use now", selected_use_now, normalize_html_brief_state(selected_state), ()),
    HtmlBriefAnswer("Still withheld", "Still withheld", selected_blocked, "withheld", ()),
    _portable_change_answer(inputs, ticker),
    HtmlBriefAnswer(
        "Next research task",
        _clean_text(inputs.authoritative_task.get("title"), "Next research task"),
        _clean_text(inputs.authoritative_task.get("body"), "No portable task."),
        normalize_html_brief_state(inputs.authoritative_task.get("state")),
        tuple(
            safe_html_brief_text(item)
            for item in inputs.authoritative_task.get("badges", ())
            if safe_html_brief_text(item)
        )
        if isinstance(inputs.authoritative_task.get("badges"), (list, tuple))
        else (),
    ),
)
```

- [ ] **Step 4: Run the focused change tests and the complete HTML unit file**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_company_workbench_html.py
```

Expected: all tests pass; existing identity assertions are updated only where the intentional fourth answer changes the frozen payload.

- [ ] **Step 5: Commit the scoped snapshot change**

```bash
git add src/company_workbench_html.py tests/test_company_workbench_html.py
git diff --cached --check
git commit -m "Freeze Workbench change answer for portable summary"
```

---

### Task 2: Render the pure Evidence One-Pager

**Files:**
- Modify: `src/company_workbench_html.py:612-880`
- Modify: `tests/test_company_workbench_html.py:560-1848`

**Interfaces:**
- Consumes: `CompanyWorkbenchHtmlSnapshot` from Task 1 and existing `_html_brief_*` safety/formatting helpers.
- Produces: `_html_evidence_one_pager(snapshot, heading_level) -> str` and `_html_evidence_one_pager_or_unavailable(snapshot, heading_level) -> str`.

- [ ] **Step 1: Add failing renderer tests for order, truth, and prohibited content**

Add `import html` beside the existing standard-library imports in
`tests/test_company_workbench_html.py`. Add tests that parse the actual rendered
markup rather than matching implementation source:

```python
def test_evidence_one_pager_renders_fixed_order_from_frozen_snapshot_only():
    snapshot = build_company_workbench_html_snapshot(_inputs())
    rendered = html_brief._html_evidence_one_pager(snapshot, heading_level=2)

    markers = (
        "Saved evidence snapshot",
        "Company Brief",
        "Scenarios under assumptions",
        "Research case",
        "Operating and valuation evidence",
        "What could break the research case",
        "Questions still requiring evidence",
        "Provenance and boundaries",
        "Continue to the full evidence report below.",
    )
    assert all(marker in rendered for marker in markers)
    assert [rendered.index(marker) for marker in markers] == sorted(
        rendered.index(marker) for marker in markers
    )
    assert rendered.count('data-section="evidence-one-pager"') == 1
    assert rendered.count("Use now") >= 1
    assert rendered.count("What changed") >= 1


@pytest.mark.parametrize(
    "forbidden",
    (
        "Certified",
        "Why own it",
        "Blue Sky",
        "upside",
        "target price",
        "expected return",
        "buy",
        "sell",
        "position size",
    ),
)
def test_evidence_one_pager_never_adds_prohibited_claims(forbidden):
    rendered = html.unescape(
        html_brief._html_evidence_one_pager(
            build_company_workbench_html_snapshot(_inputs()),
            heading_level=2,
        )
    )
    assert forbidden.lower() not in rendered.lower()


def test_evidence_one_pager_keeps_withheld_values_non_numeric():
    snapshot = build_company_workbench_html_snapshot(_inputs())
    sentinels = tuple(101001.1 + index for index in range(12))
    base = next(scenario for scenario in snapshot.scenarios if scenario.name == "Base")
    withheld_bridge = replace(
        base.bridge,
        state="withheld",
        enterprise_state="withheld",
        equity_state="withheld",
        per_share_state="withheld",
        explicit_total_state="withheld",
        projected_fcfs=(sentinels[0],),
        discounted_fcfs=(sentinels[1],),
        discounted_explicit_total=sentinels[2],
        terminal_value=sentinels[3],
        discounted_terminal_value=sentinels[4],
        enterprise_value=sentinels[5],
        cash=sentinels[6],
        debt=sentinels[7],
        net_debt=sentinels[8],
        equity_value=sentinels[9],
        shares_outstanding=sentinels[10],
        scenario_value_per_share=sentinels[11],
        blockers=("The supplied Base bridge is withheld.",),
    )
    withheld = replace(
        snapshot,
        scenarios=tuple(
            replace(scenario, bridge=withheld_bridge)
            if scenario.name == "Base"
            else scenario
            for scenario in snapshot.scenarios
        ),
    )
    rendered = html_brief._html_evidence_one_pager(withheld, heading_level=2)
    assert "Scenario value withheld" in rendered
    assert "The supplied Base bridge is withheld." in html.unescape(rendered)
    assert not [
        value
        for value in sentinels
        if html_brief.format_html_brief_number(value) in html.unescape(rendered)
    ]


def test_evidence_one_pager_preserves_share_basis_state_without_using_it_as_gate():
    snapshot = build_company_workbench_html_snapshot(_inputs())
    scenarios = tuple(
        replace(
            scenario,
            bridge=replace(
                scenario.bridge,
                per_share_state="available",
                share_basis_state="unverified",
                scenario_value_per_share=31415.92,
            ),
        )
        for scenario in snapshot.scenarios
    )
    rendered = html.unescape(
        html_brief._html_evidence_one_pager(
            replace(snapshot, scenarios=scenarios), heading_level=2
        )
    )
    assert html_brief.format_html_brief_number(31415.92) in rendered
    assert rendered.count("Share basis state: unverified") >= 3


def test_share_basis_state_cannot_override_withheld_per_share_gate():
    snapshot = build_company_workbench_html_snapshot(_inputs())
    base = next(item for item in snapshot.scenarios if item.name == "Base")
    changed = replace(
        snapshot,
        scenarios=tuple(
            replace(
                scenario,
                bridge=replace(
                    scenario.bridge,
                    per_share_state="withheld",
                    share_basis_state="available",
                    scenario_value_per_share=27182.81,
                ),
            )
            if scenario.name == "Base"
            else scenario
            for scenario in snapshot.scenarios
        ),
    )
    rendered = html.unescape(
        html_brief._html_evidence_one_pager(changed, heading_level=2)
    )
    assert html_brief.format_html_brief_number(27182.81) not in rendered
    assert "Share basis state: available" in rendered


@pytest.mark.parametrize(
    ("state", "label"),
    (
        ("available", "complete"),
        ("partial", "partial"),
        ("stale", "stale"),
        ("withheld", "withheld"),
    ),
)
def test_evidence_one_pager_keeps_independent_state_text_visible(state, label):
    snapshot = build_company_workbench_html_snapshot(_inputs())
    changed = replace(
        snapshot,
        freshness_state=state,
        answers=tuple(replace(answer, state=state) for answer in snapshot.answers),
    )
    rendered = html.unescape(
        html_brief._html_evidence_one_pager(changed, heading_level=2)
    )
    assert f'data-state="{state}"' in rendered
    assert f"State: {label}" in rendered


def test_evidence_one_pager_formats_only_supplied_scenario_values():
    snapshot = build_company_workbench_html_snapshot(_inputs())
    scenarios = tuple(
        replace(
            scenario,
            revenue_growth=0.123,
            fcf_margin=0.234,
            wacc=0.087,
            terminal_growth=0.031,
            forecast_years=7,
        )
        for scenario in snapshot.scenarios
    )
    rendered = html.unescape(
        html_brief._html_evidence_one_pager(
            replace(snapshot, scenarios=scenarios),
            heading_level=2,
        )
    )
    for supplied in ("12.3%", "23.4%", "8.7%", "3.1%", "7"):
        assert supplied in rendered


def test_evidence_one_pager_has_summary_scoped_semantics_and_dom_order():
    rendered = html_brief._html_evidence_one_pager(
        build_company_workbench_html_snapshot(_inputs()),
        heading_level=2,
    )
    parser = _OnePagerHtmlParser()
    parser.feed(rendered)
    assert parser.tags[0] == "section"
    assert {"header", "section", "ol", "table", "caption", "aside"} <= set(
        parser.tags
    )
    assert not {"main", "footer", "script", "form", "iframe"} & set(parser.tags)
    assert parser.headings[0] == ("h2", "NVDA Evidence One-Pager")
    assert "Portable evidence provenance" in parser.captions
    assert parser.answer_item_count == 4
    assert parser.scenario_item_count == 3
    assert len(parser.state_nodes) == len(parser.state_roles)
    assert len(parser.state_roles) == len(set(parser.state_roles))
    assert all(role and state for role, state in parser.state_role_pairs)
    assert len(parser.share_basis_pairs) == 4
    markers = (
        'data-section="one-pager-header"',
        'data-section="one-pager-answers"',
        'data-section="one-pager-scenarios"',
        'data-section="one-pager-research-case"',
        'data-section="one-pager-operating-valuation"',
        'data-section="one-pager-break-case"',
        'data-section="one-pager-questions"',
        'data-section="one-pager-provenance"',
        'data-section="one-pager-handoff"',
    )
    assert [rendered.index(marker) for marker in markers] == sorted(
        rendered.index(marker) for marker in markers
    )
```

Add a small `_OnePagerHtmlParser(HTMLParser)` beside the existing
`_BriefHtmlParser`. It must begin recording only at the outer element with
`data-section="evidence-one-pager"`, track nested depth, and collect tags,
headings, caption text, answer/scenario list-item counts, every
`data-state`/`data-state-role` pair, and every share-basis role/state pair from
that subtree. This prevents the existing full
report landmarks/tables from creating a false green.

Add an escaping test using a manually replaced answer containing `<script>`, a repository path, and action language; assert none reaches output and no `<script>` element appears.

- [ ] **Step 2: Run renderer tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_company_workbench_html.py \
  -k 'evidence_one_pager or share_basis_state'
```

Expected: failure because `_html_evidence_one_pager` does not exist.

- [ ] **Step 3: Add scoped CSS and the pure summary projector**

Extend the existing f-string returned by `_html_brief_css(root)` with the exact
`.srcc-one-pager` rules below. Keep `{root}` as interpolation and retain the
doubled literal braces exactly so the containing Python f-string remains
valid:

```python
{root} .srcc-one-pager {{
  color: #f8fafc;
  background: #0b1b2b;
  border-top: .35rem solid #f59e0b;
  padding: 1.25rem;
}}
{root} .srcc-one-pager * {{ color: inherit; }}
{root} .srcc-one-pager-grid {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  background: #64748b;
}}
{root} .srcc-one-pager-card {{
  min-width: 0;
  background: #0b1b2b;
  padding: 1rem;
}}
{root} .srcc-one-pager-scenarios {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .75rem;
  list-style: none;
  margin: 0;
  padding: 0;
}}
{root} .srcc-one-pager a {{ color: #67e8f9; }}
{root} .srcc-one-pager .srcc-boundary {{ border-color: #60a5fa; }}
{root} .srcc-one-pager .srcc-state-available {{ border-color: #34d399; }}
{root} .srcc-one-pager .srcc-state-partial {{ border-color: #fbbf24; }}
{root} .srcc-one-pager .srcc-state-withheld {{ border-color: #f87171; }}
{root} .srcc-one-pager .srcc-state-stale {{ border-color: #c4b5fd; }}
{root} .srcc-one-pager .srcc-state-not_recorded {{ border-color: #94a3b8; }}
{root} .srcc-one-pager .srcc-state-excluded {{ border-color: #7dd3fc; }}
{root} .srcc-one-pager .table-scroll {{ overflow: visible; }}
{root} .srcc-one-pager .srcc-table {{
  min-width: 0;
  table-layout: fixed;
  width: 100%;
}}
{root} .srcc-one-pager .srcc-table th,
{root} .srcc-one-pager .srcc-table td {{ overflow-wrap: anywhere; }}
@media (max-width: 640px) {{
  {root} .srcc-one-pager-grid,
  {root} .srcc-one-pager-scenarios {{ grid-template-columns: 1fr; }}
}}
@media (forced-colors: active) {{
  {root} .srcc-one-pager,
  {root} .srcc-one-pager-card {{ border: 1px solid CanvasText; }}
}}
@media print {{
  {root} .srcc-one-pager {{
    color: #000 !important;
    background: #fff !important;
    border-color: #000 !important;
    break-inside: auto;
  }}
  {root} .srcc-one-pager * {{ color: #000 !important; }}
  {root} .srcc-one-pager-grid {{ background: #000 !important; }}
  {root} .srcc-one-pager-card {{ background: #fff !important; }}
  {root} .srcc-one-pager .srcc-state,
  {root} .srcc-one-pager .srcc-boundary,
  {root} .srcc-one-pager [data-section="one-pager-provenance"],
  {root} .srcc-one-pager .srcc-table th,
  {root} .srcc-one-pager .srcc-table td,
  {root} .srcc-one-pager-card {{
    border-color: #000 !important;
  }}
  {root} .srcc-one-pager a {{
    color: #000 !important;
    text-decoration: underline !important;
  }}
}}
```

`#64748b` against `#0b1b2b` is approximately `3.66:1`; do not replace it
with the lower-contrast `#526173`. Normal text remains `#f8fafc`, secondary
text `#cbd5e1`, and links `#67e8f9` on `#0b1b2b`, all above `4.5:1`.
The scoped boundary/state colors above range from approximately `6.3:1` to
`10.4:1` against the one-pager navy; never inherit the lower-contrast light
report state colors onto this dark surface. Print explicitly resets every
summary state, boundary, provenance, and card border to black on white so the
same `3:1` component-boundary floor remains measurable after media emulation.

Add selectors that read only exact existing keys:

```python
def _section_by_key(
    sections: tuple[HtmlBriefSection, ...],
    key: str,
) -> HtmlBriefSection | None:
    return next((section for section in sections if section.key == key), None)


def _answer_by_label(
    answers: tuple[HtmlBriefAnswer, ...],
    label: str,
) -> HtmlBriefAnswer | None:
    return next((answer for answer in answers if answer.label == label), None)
```

Implement `_html_evidence_one_pager(...)` with these exact sources:

- header: exact title `{ticker} Evidence One-Pager`, exact eyebrow `Saved evidence snapshot`, and `ticker`, `review_cutoff`, `source_as_of`, `freshness_state`, `rights_state`, `model_version`, `identity`, `boundary`;
- answers: the four `snapshot.answers` items in stored order, including each answer's safe source references and blockers;
- scenarios: `snapshot.scenarios` in stored Bear/Base/Bull order, reusing `format_html_brief_number`, `scenario.bridge.per_share_state`, and `scenario.bridge.share_basis_state`;
- research case: decision keys `plan`, `evidence`, plus research keys `business-trend`, `key-drivers`;
- operating/value status: research keys `business-trend`, `key-drivers`, and
  `valuation-regime`, plus exactly the existing ten scalar Base `bridge_values`
  fields already used by the full report (discounted explicit total, terminal
  value, discounted terminal value, enterprise value, cash, debt, net debt,
  equity value, supplied shares, and supplied value per share) with their
  existing states/blockers. Keep the projected/discounted FCF schedule in the
  unchanged full report rather than duplicating it in the summary;
- break case: research key `risks` and decision key `invalidation`;
- questions: decision key `review-trigger`, research key `evidence-gaps`, and the `Next research task` answer;
- provenance and boundaries: exact top-level freshness/rights/model/snapshot identity/boundary plus safe source reference, date, rights, field-scope, model-identity, input-identity, and blocker fields from `snapshot.evidence_rows`; render an explicit no-portable-evidence state when the tuple is empty;
- handoff: exact copy `Continue to the full evidence report below.`

Call `format_html_brief_number(...)` for a scenario value/share or Base bridge
numeric only when that exact field's existing independent state is
`available`; otherwise emit visible `withheld` text plus its supplied blocker,
even when a manually constructed/adversarial snapshot still contains a finite
number. Scenario assumptions remain visible when supplied because the approved
contract treats them as assumptions, not targets.
Use the existing bridge-state mapping exactly: discounted explicit total uses
`explicit_total_state`; terminal value, discounted terminal value, and
enterprise value use `enterprise_state`; cash, debt, net debt, and equity value
use `equity_state`; supplied shares and supplied value per share use
`per_share_state`. Display `share_basis_state` separately and never use it as a
new gate.
Render the supplied share-basis value separately as exact escaped text
`Share basis state: <supplied state>` with
`data-share-basis-role="..."` and `data-share-basis-state="..."`. Never
normalize it into a readiness promotion and never use it to gate the per-share
number; only the existing `per_share_state` controls that display. The
share-basis disclosure does not carry `data-state`; its independent token is
audited separately in Task 5.

Every independently gated card or row must carry its normalized
`data-state="..."`, a stable unique `data-state-role="..."`, and visible
`State: ...` text. Roles use the containing summary block plus the exact answer
label, scenario name, stored section key, header field, or provenance row
identity normalized to the bounded role vocabulary described in Task 5. A
provenance role includes the frozen row ordinal, section, and source ID so
repeated source IDs remain unique. The block
namespace makes repeated content such as Business trend and Next research task
unique. Color is supplementary only.
Use one outer labelled `<section data-section="evidence-one-pager">`, one
summary `<header>`, ordered answer-list semantics, an ordered three-item
scenario list, named nested sections in DOM order, and one labelled provenance
`<aside>` with a compact captioned two-column provenance table. The handoff is
a final named block. Do not add a
nested `main` or `footer`; the existing full document already owns those
landmarks and the in-app fragment must remain valid beneath the Workbench H1.

Render absent sections using this explicit card:

```python
HtmlBriefSection(
    key="unavailable",
    title="Not recorded",
    state="not_recorded",
    answer="No portable evidence is recorded for this section.",
    facts=(),
    blockers=("The frozen snapshot does not contain this section.",),
)
```

Do not inspect narrative text to create fields or claims.

- [ ] **Step 4: Run renderer tests and complete HTML unit regression**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_company_workbench_html.py
```

Expected: all tests pass with no warning beyond the repository's known third-party dateutil deprecation.

- [ ] **Step 5: Commit the pure renderer**

```bash
git add src/company_workbench_html.py tests/test_company_workbench_html.py
git diff --cached --check
git commit -m "Render evidence one-pager from frozen research truth"
```

---

### Task 3: Compose the summary without risking the full report

**Files:**
- Modify: `src/company_workbench_html.py:750-922`
- Modify: `tests/test_company_workbench_html.py:1848-2025`

**Interfaces:**
- Consumes: `_html_evidence_one_pager(...)` from Task 2.
- Produces: unchanged public interfaces `render_company_workbench_html_fragment`, `render_company_workbench_html_document`, `company_workbench_html_bytes`, and `company_workbench_html_download_spec`, now with the one-pager before the existing full content.

- [ ] **Step 1: Add failing composition and failure-isolation tests**

```python
def test_fragment_and_document_place_one_pager_before_unchanged_full_report_order():
    snapshot = build_company_workbench_html_snapshot(_inputs())
    fragment = html_brief.render_company_workbench_html_fragment(snapshot)
    document = html_brief.render_company_workbench_html_document(snapshot)

    for rendered in (fragment, document):
        assert rendered.index('data-section="evidence-one-pager"') < rendered.index(
            'data-section="one-pager-provenance"'
        ) < rendered.index('data-section="one-pager-handoff"') < rendered.index(
            'data-section="overview"'
        )
        assert rendered.index('data-section="overview"') < rendered.index(
            'data-section="answers"'
        ) < rendered.index('data-section="scenarios"') < rendered.index(
            'data-section="advanced-evidence"'
        )


def test_one_pager_projection_failure_cannot_suppress_full_report(monkeypatch):
    snapshot = build_company_workbench_html_snapshot(_inputs())

    def fail(*args, **kwargs):
        raise ValueError("summary formatting failed")

    monkeypatch.setattr(html_brief, "_html_evidence_one_pager", fail)
    rendered = html_brief.render_company_workbench_html_document(snapshot)

    assert 'data-section="evidence-one-pager-unavailable"' in rendered
    assert "Evidence One-Pager unavailable" in rendered
    assert 'data-section="overview"' in rendered
    assert 'data-section="advanced-evidence"' in rendered


@pytest.mark.parametrize(
    "changes",
    (
        {"ticker": ""},
        {"ticker": "NVDA<script>"},
        {"profile_label": ""},
        {"profile_label": "not recorded"},
        {"profile_label": "/private/profile"},
        {"profile_label": "Different reviewed profile"},
        {"review_cutoff": "not recorded"},
        {"identity": ""},
        {"identity": "not-a-sha256"},
    ),
)
def test_invalid_summary_scope_fails_closed_without_suppressing_full_report(changes):
    snapshot = replace(build_company_workbench_html_snapshot(_inputs()), **changes)
    rendered = html_brief.render_company_workbench_html_document(snapshot)
    assert 'data-section="evidence-one-pager"' not in rendered
    assert 'data-section="evidence-one-pager-unavailable"' in rendered
    assert 'data-section="overview"' in rendered
    assert 'data-section="advanced-evidence"' in rendered


def test_download_contract_remains_one_deterministic_html_artifact():
    snapshot = build_company_workbench_html_snapshot(_inputs())
    first = html_brief.company_workbench_html_download_spec(snapshot)
    second = html_brief.company_workbench_html_download_spec(snapshot)
    assert first == second
    assert first.file_name == "NVDA-2026-07-30-research-brief.html"
    assert first.mime == "text/html; charset=utf-8"
    assert first.data.count(b'data-section="evidence-one-pager"') == 1
    assert first.data.count(b'data-section="advanced-evidence"') == 1
```

- [ ] **Step 2: Run composition tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_company_workbench_html.py \
  -k 'place_one_pager or projection_failure or invalid_summary_scope or one_deterministic_html_artifact'
```

Expected: failure because the existing fragment and document do not call the one-pager projector and have no unavailable fallback.

- [ ] **Step 3: Add explicit scope preflight, bounded fallback, and compose both renderers**

Add a pure preflight before formatting:

```python
def _evidence_one_pager_scope_valid(
    snapshot: CompanyWorkbenchHtmlSnapshot,
) -> bool:
    profile_label = safe_html_brief_text(
        html.unescape(str(snapshot.profile_label))
    )
    expected_identity = hashlib.sha256(
        json.dumps(
            asdict(replace(snapshot, identity="")),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    return bool(
        _ticker(snapshot.ticker)
        and profile_label
        and profile_label.lower() != "not recorded"
        and profile_label != _WITHHELD_ACTION
        and _iso(snapshot.review_cutoff)
        and str(snapshot.identity or "") == expected_identity
    )
```

This validation is summary-only. It does not change or suppress the existing
full-report renderer.

```python
def _html_evidence_one_pager_or_unavailable(
    snapshot: CompanyWorkbenchHtmlSnapshot,
    *,
    heading_level: int,
) -> str:
    try:
        if not _evidence_one_pager_scope_valid(snapshot):
            raise ValueError("one-pager scope is incomplete or unsafe")
        return _html_evidence_one_pager(snapshot, heading_level=heading_level)
    except (TypeError, ValueError):
        heading = f"h{heading_level}"
        return (
            '<section class="srcc-one-pager" '
            'data-section="evidence-one-pager-unavailable">'
            f"<{heading}>Evidence One-Pager unavailable</{heading}>"
            '<p class="srcc-boundary">The compact summary could not be formatted. '
            "Continue to the full evidence report below.</p></section>"
        )
```

In the fragment:

```python
summary = _html_evidence_one_pager_or_unavailable(snapshot, heading_level=3)
full_report = _html_brief_content(snapshot, heading_level=3)
```

In the full document:

```python
summary = _html_evidence_one_pager_or_unavailable(snapshot, heading_level=2)
full_report = _html_brief_content(snapshot, heading_level=2)
```

Place `summary + full_report` inside the existing shell/main. Do not change the title, CSP, skip link, footer, filename, MIME, or download function signatures.

- [ ] **Step 4: Run the complete HTML unit file**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_company_workbench_html.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit failure-isolated composition**

```bash
git add src/company_workbench_html.py tests/test_company_workbench_html.py
git diff --cached --check
git commit -m "Prepend one-pager without hiding full research brief"
```

---

### Task 4: Wire the existing Workbench change object and preserve the UI

**Files:**
- Modify: `src/dashboard.py:32390-32750`
- Modify: `tests/test_dashboard_helpers.py:36330-36375`
- Modify: `tests/test_dashboard_render_smoke.py:1026-1243`
- Modify: `tests/test_research_mode_dashboard_contract.py:2170-2270`

**Interfaces:**
- Consumes: new `CompanyWorkbenchHtmlInputs` change fields from Task 1.
- Produces: one existing HTML Research Brief expander and one unchanged download button whose fragment/document now begin with the one-pager.

- [ ] **Step 1: Add failing wiring and preservation tests**

Extend
`test_company_workbench_html_brief_uses_the_prepared_session_and_loaded_evidence_only`
in `tests/test_dashboard_helpers.py`. Slice the existing
`CompanyWorkbenchHtmlInputs(...)` call from `render_single_stock_report(...)`
and require these three fields:

```python
brief_start = render_source.index("CompanyWorkbenchHtmlInputs(")
brief_end = render_source.index("\n                )", brief_start)
brief_inputs = render_source[brief_start:brief_end]

assert "change_answer=change_answer or {}" in brief_inputs
assert "change_ticker=ticker" in brief_inputs
assert "change_profile_key=selected_context.profile_key" in brief_inputs
assert render_source.count("company_change_answer(") == 1
```

Extend the existing real Streamlit AppTest
`test_company_workbench_html_brief_is_one_collapsed_research_only_in_memory_surface`
in `tests/test_dashboard_render_smoke.py`. It already uses `_html_brief_app(...)`,
opens `Open evidence and analysis modules`, and verifies the exact Research,
Public, Operator, and closed-state boundaries. Add these assertions to the
current `fragments[0]` checks:

```python
fragment = fragments[0]
assert fragment.count('data-section="evidence-one-pager"') == 1
assert fragment.count('data-section="overview"') == 1
assert fragment.count('data-section="advanced-evidence"') == 1
assert fragment.index('data-section="evidence-one-pager"') < fragment.index(
    'data-section="overview"'
)
```

Keep the existing loop over Public and Operator modes plus the closed Research
state. Strengthen each branch by collecting any HTML bodies containing
`data-section="evidence-one-pager"` and requiring none. Do not create a second
dashboard harness.

Extend
`test_company_workbench_html_brief_is_research_only_and_follows_the_module_gate`
in `tests/test_research_mode_dashboard_contract.py` so source order proves the
one constructor remains after the module gate and before the existing expander;
do not pin private renderer helper names.

- [ ] **Step 2: Run the focused wiring tests and verify RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_helpers.py \
  tests/test_dashboard_render_smoke.py \
  tests/test_research_mode_dashboard_contract.py \
  -k 'CompanyWorkbenchHtmlInputs or one_pager or html_brief'
```

Expected: failure because the dashboard constructor does not supply the new scoped change fields and no one-pager marker exists.

- [ ] **Step 3: Supply the existing computed change without adding a loader**

Modify the sole production constructor:

```python
html_brief_snapshot = build_company_workbench_html_snapshot(
    CompanyWorkbenchHtmlInputs(
        report_payload=report_payload,
        profile_context=selected_context,
        observation_recency=observation_recency,
        selected_answer=selected_answer,
        authoritative_task=authoritative_task,
        change_answer=change_answer or {},
        change_ticker=ticker,
        change_profile_key=selected_context.profile_key,
        scenario_lab_result=scenario_session.result,
        nowcast_packet=nowcast_packet,
        decision_lab_state=decision_lab_state,
        quarterly_trend=trend_packet,
        forward_view=forward_view_packet,
        journal_state=journal_state,
        valuation_regime=valuation_regime,
        catalyst_timeline=catalyst_timeline,
    )
)
```

Do not add a new expander, button, key, report build, or download spec. Keep the current `HTML Research Brief` block otherwise unchanged.

- [ ] **Step 4: Run affected render and contract tests**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_dashboard_helpers.py \
  tests/test_dashboard_render_smoke.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_company_workbench_html.py
```

Expected: all tests pass and the existing closed/open Workbench function contracts remain green.

- [ ] **Step 5: Commit the dashboard wiring**

```bash
git add \
  src/dashboard.py \
  tests/test_dashboard_helpers.py \
  tests/test_dashboard_render_smoke.py \
  tests/test_research_mode_dashboard_contract.py
git diff --cached --check
git commit -m "Wire one-pager to existing Workbench change truth"
```

---

### Task 5: Extend real-browser, zoom, contrast, and in-app evidence

**Files:**
- Modify: `src/company_workbench_html_browser_gate.py:1-1110`
- Modify: `tests/test_company_workbench_html_browser_gate.py:1-890`
- Modify: `src/research_accessibility_browser_gate.py:2523-2699`
- Modify: `tests/test_research_accessibility_browser_gate.py:228-520`
- Modify: `Makefile:529-530`
- Modify: `tests/test_launchers.py` at the existing company-workbench browser target contract

**Interfaces:**
- Consumes: final HTML bytes from Task 3 and the existing Workbench module-open flow from Task 4.
- Produces: typed standalone observations for one-pager visibility/order/contrast/overflow/zoom plus a bounded three-cell in-app Workbench result proving that the summary remains behind the explicit module gate and reflows at the approved zooms.

- [ ] **Step 1: Add failing pure evaluator tests for the new observation fields**

Extend `REQUIRED_OBSERVATION_KEYS` and `_OBSERVATION_TYPES` with:

```python
"requested_zoom",
"actual_browser_zoom",
"one_pager_visible",
"one_pager_before_overview",
"one_pager_heading_count",
"one_pager_section_count",
"page_header_count",
"one_pager_header_count",
"one_pager_answer_item_count",
"one_pager_scenario_item_count",
"one_pager_state_tokens",
"one_pager_share_basis_tokens",
"one_pager_state_node_count",
"one_pager_state_role_count",
"one_pager_unique_state_role_count",
"one_pager_provenance_caption_visible",
"one_pager_min_text_contrast_ratio",
"one_pager_min_boundary_contrast_ratio",
"one_pager_overflow_px",
"one_pager_max_descendant_overflow_px",
"one_pager_provenance_visible",
"one_pager_blockers_visible",
"one_pager_assumptions_visible",
"one_pager_handoff_visible",
"one_pager_forced_colors_non_color_cue",
"one_pager_print_min_text_contrast_ratio",
"one_pager_print_min_boundary_contrast_ratio",
"one_pager_print_provenance_visible",
"one_pager_print_blockers_visible",
"one_pager_print_assumptions_visible",
"one_pager_print_handoff_visible",
```

Types:

```python
"requested_zoom": int,
"actual_browser_zoom": bool,
"one_pager_visible": bool,
"one_pager_before_overview": bool,
"one_pager_heading_count": int,
"one_pager_section_count": int,
"page_header_count": int,
"one_pager_header_count": int,
"one_pager_answer_item_count": int,
"one_pager_scenario_item_count": int,
"one_pager_state_tokens": (tuple, str),
"one_pager_share_basis_tokens": (tuple, str),
"one_pager_state_node_count": int,
"one_pager_state_role_count": int,
"one_pager_unique_state_role_count": int,
"one_pager_provenance_caption_visible": bool,
"one_pager_min_text_contrast_ratio": float,
"one_pager_min_boundary_contrast_ratio": float,
"one_pager_overflow_px": float,
"one_pager_max_descendant_overflow_px": float,
"one_pager_provenance_visible": bool,
"one_pager_blockers_visible": bool,
"one_pager_assumptions_visible": bool,
"one_pager_handoff_visible": bool,
"one_pager_forced_colors_non_color_cue": bool,
"one_pager_print_min_text_contrast_ratio": float,
"one_pager_print_min_boundary_contrast_ratio": float,
"one_pager_print_provenance_visible": bool,
"one_pager_print_blockers_visible": bool,
"one_pager_print_assumptions_visible": bool,
"one_pager_print_handoff_visible": bool,
```

Add evaluator tests proving:

Update `_complete_observation()` and `DEPENDENT_ASSERTIONS` in the same RED so
`header_count` is `2`, `page_header_count` and
`one_pager_header_count` are `1`, and all three fields own the existing
`semantic_landmarks` assertion.

- values are required with exact types;
- zoom must be `1`, `2`, or `4` and `actual_browser_zoom` must be true;
- one-pager must be visible and precede `data-section="overview"`;
- update the existing `semantic_landmarks` contract for the intentional nested
  summary header: the complete document has exactly two header elements,
  exactly one top-level page header and exactly one direct one-pager summary
  header, while `main_count == footer_count == 1`. Add mutations for a missing
  or duplicate page/summary header so the wider count cannot hide drift;
- the summary must own its expected heading/sections, exact four-item answer
  list, exact three-item scenario
  list, and visible captioned provenance table rather than borrowing the downstream report's
  semantics: exactly eight summary headings (one title plus seven named block
  headings) and exactly seven nested section/aside blocks;
- the minimum contrast across every visible summary text/link color must be at
  least `4.5`, and every explicit summary separator/component boundary at
  least `3.0`;
- both outer one-pager horizontal overflow and the maximum overflow of every
  visible descendant/scroll container must be at most `1.0` pixel; and
- `one_pager_state_tokens` must be derived from summary DOM pairs formatted
  `role=normalized_state`, not a caller-supplied pass boolean. Define a literal
  `SYNTHETIC_EXPECTED_STATE_ROLE_TOKENS` mapping from the fixture contract and
  require an exact tuple/count match for the case named by
  `observation["state"]`. The complete mapping explicitly includes
  `answers:still-withheld=withheld` and `answers:what-changed=partial`, while its
  permitted scenario/evidence/process roles are available; partial and stale
  cases preserve their named roles plus those invariant exceptions; the fully
  withheld case uses withheld for every state-bearing role. Relabeling an
  identical document as another case must fail; and
- every summary node with `data-state` must also have exactly one nonempty,
  unique `data-state-role`; state-node, paired-role, and unique-role counts must
  be equal, with no missing, duplicate, or unexpected role; and
- `one_pager_share_basis_tokens` must independently preserve the exact safe
  supplied disclosure for Bear/Base/Bull and the Base bridge (including
  `unverified`) and must not affect the per-share numeric gate; and
- one-pager provenance, blockers, assumptions, and handoff must remain visible
  in both screen and print media with the same text/boundary thresholds; and
- forced colors must preserve visible state text plus a non-color border or
  outline for every summary state and the summary boundary/provenance block;
  downstream full-report cues cannot satisfy this check; and
- generic full-report table scrolling remains allowed.

- [ ] **Step 2: Run the evaluator tests and verify RED**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_company_workbench_html_browser_gate.py \
  -k 'observation or one_pager or contrast or zoom'
```

Expected: failure because the observation contract has no one-pager or zoom fields.

- [ ] **Step 3: Serve injected bytes on loopback and use real Chrome zoom preferences**

Before production edits, add pure/loopback contract tests named with the
prefixes `test_injected_server_contract_`,
`test_synthetic_fixture_contract_`, and
`test_external_origin_policy_contract_`. Cover exact byte serving, explicit
favicon behavior, unknown-state 404, all four scope-valid fixture identities,
the literal role/disclosure maps, and exact-origin allow/other-origin abort.
Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_company_workbench_html_browser_gate.py \
  -k 'injected_server_contract_ or synthetic_fixture_contract_ or external_origin_policy_contract_'
```

Expected RED: the injected server/origin policy does not exist and the current
synthetic fixture is scope-invalid and incomplete. Only then add the server,
fixture, and route-interception implementation below.

Add a temporary loopback server context that serves the exact supplied bytes from memory and writes nothing to the repository:

```python
@contextmanager
def _injected_brief_server(cases: Mapping[str, bytes]) -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = unquote(urlsplit(self.path).path)
            if path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            state = path.strip("/").removesuffix(".html")
            payload = cases.get(state)
            if payload is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
```

Record the same-origin favicon request in the HTTP audit. The explicit `204`
prevents Chrome's implicit favicon lookup from creating a false console error;
it must not mutate the exact injected document bytes.

Use the same Chrome preference contract as `workspace_visual_browser_gate._chromium_zoom_preferences`: a temporary profile under `/tmp`, `partition.per_host_zoom_levels`, and `zoom_level = math.log(float(zoom), 1.2)`. Launch a fresh persistent context per cell and navigate to the exact loopback state URL.

Add a local pure `evaluate_html_brief_browser_zoom(...)` that copies the
workspace evaluator's geometry tolerances but has the summary-specific allowed
set `(1, 2, 4)`. Do not modify the workspace gate's global `ZOOMS == (1, 2)`.
Add pure tests proving 100%, 200%, and 400% pass only with matching screenshot,
inner/visual viewport, DPR, and scale geometry; wrong zoom or fabricated
geometry fails. Add `zoom: int` to `HtmlBriefBrowserResult` and use
`(state, viewport, zoom)` as the unique cell identity.

Use these standalone cells:

```python
HTML_BRIEF_BROWSER_CELLS = (
    (1280, 720, 1),
    (1280, 720, 2),
    (1440, 1024, 1),
    (1440, 1024, 2),
    (1440, 1024, 4),
    (390, 844, 1),
)
```

Add a keyword-only `cells` argument to
`run_company_workbench_html_browser_gate(...)`, defaulting to the exact full
tuple above. The authoritative matrix uses the default. Existing adversarial
mutation tests must pass one explicit `1280x720@100%` cell so each proves its
named failure without repeating the 24-cell acceptance matrix.

Extend the synthetic-state fixture so `stale` maps to the existing normalized
`stale` state. The current manual fixture uses `review_cutoff="not recorded"`
and `identity="synthetic-..."`; those must be replaced because the new scope
preflight correctly rejects them. Give every synthetic state the same safe
zoned ISO review cutoff, then compute its 64-character identity exactly like
the production builder from `json.dumps(asdict(replace(snapshot,
identity="")), sort_keys=True, separators=(",", ":"), ensure_ascii=False)` and
SHA-256.

Make these fixtures substantive rather than label-only:

- every case contains the four exact answer labels `Use now`, `Still
  withheld`, `What changed`, and `Next research task`;
- every case contains the decision keys `plan`, `evidence`, `invalidation`,
  and `review-trigger`, the research keys `business-trend`, `key-drivers`,
  `valuation-regime`, `risks`, and `evidence-gaps`, all three scenarios, and a
  provenance row;
- every synthetic scenario bridge uses `share_basis_state="unverified"`, even
  when `per_share_state="available"`, so the matrix proves disclosure without
  introducing a stricter gate;
- `complete` supplies finite scenario assumptions, per-share values, and Base
  bridge values behind `available` numeric gates, while its What-changed card
  remains `partial` as required by the approved contract;
- `partial` supplies finite values only for fields whose independent state is
  `available`, includes real partial blockers elsewhere, and also supplies at
  least one finite sentinel behind a non-available gate to prove suppression;
- `stale` exercises visible stale state and blockers without promoting stale
  numerics; and
- `withheld` makes every state-bearing summary card truly withheld and gives
  dangerous numeric fields finite sentinels that must not render.

Add a pure fixture test that parses each snapshot/document before Chrome and
proves all four answers, all named keys, three scenarios, provenance, expected
state distribution, finite-value layout where permitted, suppression where
not permitted, and the normal one-pager rather than the unavailable fallback.
Build the expected state-role tuple independently from these literal roles:
`answers:{use-now,still-withheld,what-changed,next-research-task}`;
`scenarios:{bear,base,bull}`;
`research-case:{plan,evidence,business-trend,key-drivers}`;
`operating-value:{business-trend,key-drivers,valuation-regime,base-bridge}`;
`operating-value:base-bridge:{discounted-explicit-total,terminal-value,discounted-terminal-value,enterprise-value,cash,debt,net-debt,equity-value,shares-outstanding,scenario-value-per-share}`;
`scenarios:{bear,base,bull}:per-share`;
`break-case:{risks,invalidation}`;
`questions:{review-trigger,evidence-gaps,next-research-task}`;
`header:{freshness,rights}`; and
`provenance:0:synthetic-provenance:synthetic-test-source`. For complete,
default those roles to
available but override Still-withheld to withheld and What-changed to partial;
for partial, keep the explicitly declared finite numeric-role subset available
and default the other roles to partial with the same two answer overrides; for
stale, default to stale with the same overrides and no promoted numeric role;
for withheld, every role is withheld. Sort this literal tuple once and use it
as `SYNTHETIC_EXPECTED_STATE_ROLE_TOKENS`; never derive it from the rendered
DOM. Assert that the literal role set equals the renderer's documented role
set before any browser runs. Separately define the exact share-basis disclosure
tokens `scenarios:{bear,base,bull}=unverified` and
`operating-value:base-bridge=unverified`; these are not normalized readiness
roles and cannot gate a number.
Run all cells for `complete`, `partial`, `stale`, and `withheld` exact
documents. Intercept every HTTP/HTTPS request before it leaves the page: abort
and record it as a failure unless
its normalized `scheme://host:port` exactly equals the active temporary server
origin. A different loopback port, a lookalike hostname, or a malformed HTTP
URL must fail; `data:`, `blob:`, and `about:` are not HTTP requests. Keep the
existing `remote_request_count` field as this exact external-origin count so
the current fail-closed assertion remains meaningful.

- [ ] **Step 4: Observe summary order, contrast, overflow, and actual zoom**

Before editing `_browser_observation(...)`, add one focused real-Chrome
parameterized test family named
`test_summary_browser_collector_contract_*`. Use only the explicit
`1280x720@100%` cell and cover a correct substantive fixture plus mutations for
borrowed full-report semantics, missing/duplicate state roles, relabeled case,
low-contrast text/link/boundary, hidden/caption/order/list-count drift,
descendant-only overflow, print-only hidden/low-contrast content,
forced-colors-only border loss, wrong zoom geometry, and external-origin
injection. Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_company_workbench_html_browser_gate.py \
  -k 'summary_browser_collector_contract_'
```

Expected RED: the current collector has no summary-scoped observation fields
and cannot identify each named mutation. Preserve this RED transcript, then
implement the collector below. The full 24-cell acceptance matrix remains
reserved for Step 9.

In `_browser_observation(...)`, compute the summary measurements and all zoom
geometry required by `evaluate_html_brief_browser_zoom(...)`:

```javascript
const onePager = document.querySelector('[data-section="evidence-one-pager"]');
const overview = document.querySelector('[data-section="overview"]');
const headings = onePager ? [...onePager.querySelectorAll('h2,h3,h4,h5,h6')] : [];
const sections = onePager ? [...onePager.querySelectorAll(':scope section, :scope aside')] : [];
const stateNodes = onePager ? [...onePager.querySelectorAll('[data-state]')] : [];
const stateRoleNodes = onePager
  ? [...onePager.querySelectorAll('[data-state][data-state-role]')]
  : [];
const stateRoles = stateRoleNodes
  .map((node) => String(node.dataset.stateRole || '').trim().toLowerCase())
  .filter(Boolean);
return {
  one_pager_visible: visible(onePager),
  page_header_count: document.querySelectorAll('body > header').length,
  one_pager_header_count: onePager
    ? onePager.querySelectorAll(':scope > header').length
    : 0,
  one_pager_before_overview: Boolean(
    onePager && overview &&
    (onePager.compareDocumentPosition(overview) & Node.DOCUMENT_POSITION_FOLLOWING)
  ),
  one_pager_heading_count: headings.length,
  one_pager_section_count: sections.length,
  one_pager_answer_item_count: onePager
    ? onePager.querySelectorAll(
        '[data-section="one-pager-answers"] > ol > li'
      ).length
    : 0,
  one_pager_scenario_item_count: onePager
    ? onePager.querySelectorAll(
        '[data-section="one-pager-scenarios"] > ol > li'
      ).length
    : 0,
  one_pager_state_tokens: onePager
    ? stateRoleNodes
        .map((node) => `${String(node.dataset.stateRole || '').trim().toLowerCase()}=${String(node.dataset.state || '').trim().toLowerCase()}`)
        .filter((token) => !token.startsWith('=') && !token.endsWith('='))
        .sort()
    : [],
  one_pager_share_basis_tokens: onePager
    ? [...onePager.querySelectorAll('[data-share-basis-role][data-share-basis-state]')]
        .map((node) => `${String(node.dataset.shareBasisRole || '').trim().toLowerCase()}=${String(node.dataset.shareBasisState || '').trim().toLowerCase()}`)
        .filter((token) => !token.startsWith('=') && !token.endsWith('='))
        .sort()
    : [],
  one_pager_state_node_count: stateNodes.length,
  one_pager_state_role_count: stateRoleNodes.length,
  one_pager_unique_state_role_count: new Set(stateRoles).size,
  one_pager_provenance_caption_visible: visible(
    onePager?.querySelector('[data-section="one-pager-provenance"] caption')
  ),
  one_pager_min_text_contrast_ratio: minimumTextContrast(onePager),
  one_pager_min_boundary_contrast_ratio: minimumBoundaryContrast(onePager),
  one_pager_overflow_px: onePager
    ? Math.max(0, onePager.scrollWidth - onePager.clientWidth)
    : -1,
  one_pager_max_descendant_overflow_px: onePager
    ? Math.max(
        0,
        ...[...onePager.querySelectorAll('*')]
          .filter(visible)
          .map((node) => Math.max(0, node.scrollWidth - node.clientWidth))
      )
    : -1,
  one_pager_provenance_visible: visible(
    onePager?.querySelector('[data-section="one-pager-provenance"]')
  ),
  one_pager_blockers_visible: visible(
    onePager?.querySelector('.srcc-blockers')
  ),
  one_pager_assumptions_visible: visible(
    onePager?.querySelector('[data-section="one-pager-scenarios"]')
  ),
  one_pager_handoff_visible: visible(
    onePager?.querySelector('[data-section="one-pager-handoff"]')
  ),
  inner_width: window.innerWidth,
  inner_height: window.innerHeight,
  device_pixel_ratio: window.devicePixelRatio,
  visual_viewport_width: window.visualViewport?.width || 0,
  visual_viewport_height: window.visualViewport?.height || 0,
  visual_viewport_scale: window.visualViewport?.scale || 0,
};
```

Normalize the returned state-role and share-basis arrays to tuples before the
typed evaluator runs. Add stable, unique `data-state-role` plus `data-state`
attributes to every one-pager answer, scenario, named evidence/process card,
and provenance state row. Role names come from exact answer labels, scenario
names, and stored section keys; do not derive case truth from a caller-supplied
boolean.

Define `one_pager_assumptions_visible` as three visible Bear/Base/Bull list
items with visible state and assumption text, not merely a visible containing section.
Define summary provenance visibility as a visible caption plus at least one
visible row or the explicit visible no-portable-evidence row.

Use a standard sRGB relative-luminance implementation for `contrastRatio`.
Within the summary subtree, find every visible element with non-empty direct or
descendant text, resolve its effective opaque ancestor background, and record
the minimum foreground/background ratio; include links and state labels. For
component boundaries, record the minimum of grid-separator versus card
background and explicit border versus adjacent background. Repeat the same
measurements after settled print emulation; do not use the existing full-report
`.srcc-advanced-evidence` selector as proof of summary print visibility.
During settled forced-colors emulation, scope every selector to the one-pager
and require visible state text plus at least a one-pixel border or outline for
all summary states and the summary boundary/provenance block. Serialize this as
`one_pager_forced_colors_non_color_cue` separately from the existing generic
full-report field.
Take a viewport screenshot with `scale="device"`, require a PNG signature,
and read its width/height from IHDR bytes 16:24, exactly as the workspace gate
does. Feed declared width/height, screenshot width/height, inner width/height,
visual viewport width/height, device pixel ratio, and visual viewport scale to
the dedicated `evaluate_html_brief_browser_zoom(...)` contract; serialize only its pass
result as `actual_browser_zoom` and retain its evidence in the named zoom
assertion.

Add mutation tests that inject low-contrast body text, a low-contrast link, and
a sub-3:1 separator; hide the one-pager; remove a summary caption/landmark;
remove one answer or scenario list item; relabel/duplicate a state document;
move it after Overview; add horizontal overflow to a descendant scroll
container while the outer one-pager remains clipped; and hide or recolor summary
provenance/blockers/assumptions/handoff only in print. Assert the corresponding
summary-scoped named check fails while unrelated full-report checks can remain
green. Include a print-only mutation that restores a low-contrast state or
table-cell border on white. Add a forced-colors-only mutation that removes summary borders while
leaving the existing full-report cues intact; it must fail the new
summary-scoped forced-colors assertion.

Rerun the exact `summary_browser_collector_contract_` command above after the
collector change. Expected GREEN: the baseline passes and every mutation fails
only its corresponding summary-scoped assertion on the single bounded cell.

- [ ] **Step 5: Tighten the in-app accessibility observer after explicit module open**

First add the collector and payload tests, named
`test_one_pager_collector_contract_*` and
`test_one_pager_payload_contract_*`, including every missing/duplicate/hidden,
ordering, zoom, overflow, state-role, share-basis, target-size, runtime, and
external-request negative listed below. Run them before editing the production
observer:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_research_accessibility_browser_gate.py \
  -k 'one_pager_collector_contract_ or one_pager_payload_contract_'
```

Expected RED: the collector and payload have no one-pager fields or bounded
Workbench matrix. Only then implement the observer/payload changes below.

Keep `_company_workbench_primary_brief_assertion(...)` unchanged so the one-pager remains absent before open. After `_open_company_workbench_modules(...)` passes:

1. locate the one existing `details` element whose summary is `HTML Research Brief`;
2. open it through the native summary control;
3. require exactly one visible `[data-section="evidence-one-pager"]` inside its rendered HTML surface;
4. require its marker before `data-section="overview"`;
5. require the existing `data-section="advanced-evidence"` afterward; and
6. require the existing download button label and 44-pixel target.

Add pure negative fixtures for missing, duplicate, hidden, after-overview, or full-report-missing one-pagers.

Add a dedicated in-app Workbench-only zoom slice to the existing Research
accessibility payload; do not multiply every route in `RESEARCH_ROUTES`. Reuse
the same local captured Streamlit server and the same temporary-profile Chrome
zoom preference contract from Step 3 for exactly:

```python
COMPANY_WORKBENCH_ONE_PAGER_CELLS = (
    (1280, 720, 1),
    (1280, 720, 2),
    (390, 844, 1),
)
```

For each cell, navigate to the exact Company Workbench query, prove the
one-pager is absent before module activation, activate modules, open the
existing HTML Research Brief disclosure, and record actual browser zoom,
summary/full-report order, summary/document-shell overflow, summary minimum
text/link and boundary contrast, maximum descendant overflow, exactly four
visible answer items, exactly three visible scenario items, a case-consistent
summary state distribution, the exact visible share-basis disclosures, and a
visible provenance caption,
provenance/blockers/assumptions/handoff visibility, 44-pixel download target,
console/page errors, and exact-origin network evidence. Serialize this
under a new `company_workbench_one_pager` result list in the existing gate
payload. Add payload tests that fail on a missing cell, duplicate cell, false
zoom, overflow, external HTTP request, or failed assertion.

- [ ] **Step 6: Add a guarded `/tmp` result-packet writer for the standalone gate**

First add the writer tests named `test_result_packet_contract_*` for schema,
cell uniqueness, determinism, path containment, and nonempty-directory
rejection, then run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_company_workbench_html_browser_gate.py \
  -k 'result_packet_contract_'
```

Expected RED: no packet builder/writer exists. Only then add the production
builder/writer and Make wiring below.

Add a pure payload builder and a bounded writer to
`src/company_workbench_html_browser_gate.py`. The writer must:

- accept only an existing empty output directory resolving under `/tmp`;
- serialize verdict, all unique `(state, viewport, zoom)` cells, every named
  assertion, exact input-document SHA-256s, and SHA-256s for the explicitly
  supplied renderer/gate/test source paths;
- write exactly `results.json` and `source-hashes.json` with deterministic
  sorted JSON; and
- reject a missing, duplicate, or unexpected cell before writing.

Add focused tests for the schema, `24/24` uniqueness, deterministic bytes,
outside-`/tmp` rejection, and non-empty-directory rejection. In the one actual
matrix test only, when `HTML_BRIEF_BROWSER_OUTPUT_DIR` is set, write the packet
after every cell passes.

Change `company-workbench-html-browser-check` to create a fresh directory with
`mktemp -d /tmp/stock-company-workbench-html-browser.XXXXXX`, export it only to
the `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider`
process, require both packet files after pytest exits zero, print the
two absolute paths and SHA-256s, and never delete or overwrite an existing
packet. Extend the current Makefile launcher contract test; do not add a repo
output path.

- [ ] **Step 7: Run only pure/fake browser and accessibility unit tests**

Name the newly added no-Chrome tests with one of the explicit prefixes
`test_observation_contract_`, `test_zoom_contract_`,
`test_result_packet_contract_`, `test_one_pager_collector_contract_`, or
`test_one_pager_payload_contract_`. Reserve all persistent-context/Chrome tests
for Step 9. Run:

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_company_workbench_html_browser_gate.py \
  tests/test_research_accessibility_browser_gate.py \
  -k 'observation_contract_ or zoom_contract_ or result_packet_contract_ or injected_server_contract_ or synthetic_fixture_contract_ or external_origin_policy_contract_ or one_pager_collector_contract_ or one_pager_payload_contract_'

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_launchers.py::test_makefile_exposes_direct_html_research_brief_browser_gate
```

Expected: all typed/pure/fake-browser checks pass and zero test that launches
Chrome or the 24-cell matrix is selected. Confirm the collected node list
before accepting this step.

- [ ] **Step 8: Commit the reviewed browser-gate implementation**

```bash
git add \
  src/company_workbench_html_browser_gate.py \
  tests/test_company_workbench_html_browser_gate.py \
  src/research_accessibility_browser_gate.py \
  tests/test_research_accessibility_browser_gate.py \
  Makefile \
  tests/test_launchers.py
git diff --cached --check
git commit -m "Verify one-pager truth across browser states"
```

- [ ] **Step 9: Run the authoritative focused browser gates on a clean worktree**

```bash
test -z "$(git status --porcelain)"
make company-workbench-html-browser-check
make research-accessibility-browser-check \
  > /tmp/stock-evidence-one-pager-research-accessibility.json
```

Expected: the standalone matrix produces `24/24` passed cells; Research
accessibility passes its existing desktop and phone routes plus all `3/3`
Workbench one-pager cells, with the summary absent before open and present after
open. Validate and hash the standalone packet paths printed by Make. Validate
the Research accessibility stdout as JSON, hash it, and write a separate sorted
source-hash manifest under `/tmp` for its exact gate/product/test inputs. If either
gate fails, add one focused failing test for the reproduced defect, land a new
minimal fix commit, and rerun only the invalidated gate.

---

### Task 6: Reconcile documentation and complete final verification

**Files:**
- Modify: `README.md:47-49`
- Modify: `ROADMAP.md:63-71`
- Modify: `tests/test_public_v1_release_docs.py:2230-2315`
- Create: `.superpowers/sdd/2026-08-16-evidence-one-pager/design-qa.md`
- Create: `.superpowers/sdd/2026-08-16-evidence-one-pager/final-report.md`

**Interfaces:**
- Consumes: final product/browser behavior from Tasks 1-5.
- Produces: active product truth, final visual comparison, verification manifest, and local implementation commit without push.

- [ ] **Step 1: Add failing active-document contract tests**

Add exact assertions that README and ROADMAP describe:

- the one-pager as the first summary section of the existing HTML Research Brief;
- the complete report following in the same artifact;
- no new route, engine, download, readiness promotion, or recommendation;
- withheld evidence remaining independently visible; and
- the explicit absence of `Certified`, target-price, upside, and probability claims.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_public_v1_release_docs.py \
  -k 'html_research_brief or one_pager'
```

Expected: failure because active docs do not yet name the Evidence One-Pager.

- [ ] **Step 2: Update active documentation with exact bounded truth**

Use this core sentence in both active surfaces:

```text
The existing HTML Research Brief begins with an Evidence One-Pager that projects only the already-frozen saved evidence, scenario assumptions, blockers, process status, and next research task; the complete evidence report follows in the same offline artifact. The summary adds no source, calculation engine, readiness promotion, recommendation, target price, probability, or second download.
```

Do not add current counts, release claims, human-accessibility claims, or external validation claims.

- [ ] **Step 3: Run affected code, render, documentation, and static checks**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_public_v1_release_docs.py

python3 -m ruff check \
  src/company_workbench_html.py \
  src/company_workbench_html_browser_gate.py \
  src/dashboard.py \
  src/research_accessibility_browser_gate.py \
  tests/test_company_workbench_html.py \
  tests/test_company_workbench_html_browser_gate.py \
  tests/test_dashboard_helpers.py \
  tests/test_dashboard_render_smoke.py \
  tests/test_research_mode_dashboard_contract.py \
  tests/test_research_accessibility_browser_gate.py \
  tests/test_launchers.py \
  tests/test_public_v1_release_docs.py

git diff --check
git diff --cached --check
```

Expected: the docs contract and static checks pass. Bridge every Task 1-5
focused result by exact source/test hashes instead of rerunning unchanged unit,
AppTest, launcher, or browser files.

The pytest command intentionally excludes the two real-browser test files.
Task 6 changes only active documentation and its static contract, so the exact
Task 5 browser packets remain authoritative when every renderer, gate, and
browser-test hash still matches. The Ruff command may lint those files without
executing them.

- [ ] **Step 4: Commit the active-document truth before clean-worktree gates**

```bash
git add README.md ROADMAP.md tests/test_public_v1_release_docs.py
git diff --cached --check
git commit -m "Document the Evidence One-Pager boundary"
test -z "$(git status --porcelain)"
```

- [ ] **Step 5: Run remaining changed-byte gates serially and bridge browser evidence**

```bash
make research-dashboard-render-smoke \
  > /tmp/stock-evidence-one-pager-research-render-smoke.log
make commercial-beta-performance-contract \
  > /tmp/stock-evidence-one-pager-performance-contract.log
```

Run serially with no overlapping Streamlit/browser gate. Record exit code,
absolute transcript path, transcript SHA-256, and exact source hash manifest
for each; neither command natively writes a result artifact, so do not claim a
JSON result path. Do not
repeat the two Task 5 browser gates merely because README/ROADMAP/test-doc bytes
changed. Instead, prove every product, renderer, browser-gate, and browser-test
blob bound to the Task 5 results is byte-identical. Rerun only a browser gate
whose bound byte changed or whose evidence cannot be bridged exactly.

- [ ] **Step 6: Capture and compare final visual evidence**

Verify the reference still exists and matches:

```bash
shasum -a 256 /var/folders/cw/xfqgmp_57rn7nn3fq68z_6280000gn/T/codex-clipboard-80b40520-4c8b-493e-89af-a87e159e329b.png
```

Expected: `d467ce50f7803b3a269b5cfd748a87c1ce4a269345943ca6993d365056c72d59`. If unavailable or different, stop visual closeout and request reattachment.

Capture the standalone complete-state one-pager at an exact CSS viewport of
`2310x1504`, browser zoom `100%`, DPR `1`, and screenshot `scale="device"`;
require its PNG IHDR to be exactly `2310x1504`. Use the reference at its native
`2310x1504` pixels with no crop, stretch, or content-aware edit. Build one
side-by-side composite with equal `2310x1504` panels, a fixed neutral gutter,
and explicit `Reference` / `Implementation` labels outside the image content.
Also capture the same implementation document at `390x844`, zoom `100%`, DPR
`1`, with no crop. Save all temporary captures and composites under
`/tmp/stock-evidence-one-pager-design-qa-<HEAD>/`, record viewport/zoom/DPR/IHDR
for each, and inspect every saved image. Write
`.superpowers/sdd/2026-08-16-evidence-one-pager/design-qa.md` with:

- reference and implementation paths and hashes;
- same-viewport state;
- P0/P1/P2/P3 findings;
- intentional differences for certification, target/upside, probability, capital-allocation, and action language;
- phone/zoom/contrast evidence; and
- `final result: passed` only after every P0/P1/P2 is closed.

- [ ] **Step 7: Verify protected paths, draft the report, and request independent final review**

Regenerate the same relative-path/type/SHA-256 manifest for `data/`, `outputs/`,
and `docs/assets/` and compare it byte-for-byte with the Task 0 baseline;
assert zero differences. Record exact intentional changed paths, zero unexpected
staged/untracked paths, and an empty index before final staging.

Request an independent review of:

- complete branch diff;
- preservation contract;
- no-recommendation/no-fabrication boundary;
- browser result/source hashes;
- visual QA; and
- protected artifacts.

Before sending the review, draft
`.superpowers/sdd/2026-08-16-evidence-one-pager/final-report.md` with every
already-known exact HEAD/base, commit, changed-file, RED/GREEN, gate/hash,
visual, protected-path, external-gate, and no-push fact. Mark only the reviewer
verdict as pending.

Do not create the final source manifest yet: the reviewer verdict still changes
the final-report bytes. Do not stage the final slice until the reviewer reports
zero Critical and zero Important findings.

- [ ] **Step 8: Finalize, re-review, and commit exact reviewed paths**

Update only the pending verdict fields in the already-reviewed final report.
Then create a sorted final source manifest under a fresh `/tmp` evidence
directory covering every intended final repository path. Each entry records
relative path, file type, executable mode, working-byte SHA-256, and (where the
path is already committed) Git blob ID; include source, tests, Makefile,
README, ROADMAP, design spec, implementation plan, design-QA, and the now-final
report. Record the manifest's own SHA-256 only in the external execution log,
not inside any file covered by the manifest.

Request one bounded exact-byte follow-up review of that manifest, the final
report, `design-qa.md`, the complete branch diff, and final status. Any
substantive report or code change requires regenerating the manifest and
another review; do not treat prose as exempt.

Stage only reviewed source, test, active-doc, design-QA, and report paths. Then:

```bash
git diff --cached --check
git status --short
git commit -m "Add auditable Evidence One-Pager"
```

After commit, stream each committed path from `git show HEAD:<path>`, verify its
mode and SHA-256 against the final reviewed source manifest, require no omitted
or extra intended path, and rerun the focused no-write unit slice. Recompare
the protected manifest and require a clean worktree. Do not push, open a PR,
mark ready, merge, deploy, or publish without a separate owner request.
