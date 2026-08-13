"""Pure policy for identifying non-portable research action language."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass


_REFERENCE_MODIFIER_MAX_CONTEXT_TOKENS = 8
_SECURITY_ACTION_STARTS = frozenset(
    {
        "add", "added", "adding", "adds",
        "acquire", "acquired", "acquires", "acquiring", "bought", "buy", "buying", "buys",
        "build", "building", "builds", "built", "close", "closed", "closes", "closing", "enter", "entered",
        "entering", "enters", "exit", "exited", "exiting", "exits",
        "dispose", "disposed", "disposes", "disposing", "held", "hold", "holding", "holds",
        "increase", "increased", "increases", "increasing",
        "initiate", "initiated", "initiates", "initiating", "liquidate", "liquidated", "liquidates",
        "liquidating", "open", "opened", "opening", "opens", "order", "ordered", "ordering", "orders",
        "purchase", "purchased", "purchases",
        "purchasing", "reduce", "reduced", "reduces", "reducing", "sale", "sales", "sell", "selling",
        "sells", "short", "shorted", "shorting", "shorts", "size", "sized", "sizes", "sizing", "sold",
        "trim", "trimmed", "trimming", "trims",
    }
)
_SECURITY_ACTION_ENDPOINTS = frozenset(
    {"equities", "equity", "securities", "security", "share", "shares", "stock", "stocks"}
)
_EXECUTION_ACTION_STARTS = frozenset(
    {
        "close", "closed", "closes", "closing", "enter", "entered", "entering", "enters", "execute",
        "executed", "executes", "executing", "exit", "exited", "exiting", "exits", "open", "opened",
        "opening", "opens", "order", "ordered", "ordering", "orders", "place", "placed", "places",
        "placing", "route", "routed", "routes", "routing", "submit", "submits", "submitted", "submitting",
    }
)
_EXECUTION_ACTION_ENDPOINTS = frozenset({"order", "orders", "trade", "trades", "transaction", "transactions"})
_POSITION_ACTION_STARTS = frozenset(
    {
        "add", "added", "adding", "adds", "build", "building", "builds", "built", "close", "closed",
        "closes", "closing", "enter", "entered", "entering", "enters", "exit", "exited", "exiting",
        "exits", "held", "hold", "holding", "holds", "increase", "increased", "increases", "increasing",
        "initiate", "initiated", "initiates", "initiating", "liquidate", "liquidated", "liquidates",
        "liquidating", "open", "opened", "opening", "opens", "reduce", "reduced", "reduces", "reducing",
        "size", "sized", "sizes", "sizing", "trim", "trimmed", "trimming", "trims",
    }
) | _SECURITY_ACTION_STARTS
_EXPOSURE_ACTION_ENDPOINTS = frozenset({"exposure", "exposures"})
_POSITION_ACTION_ENDPOINTS = frozenset({"position", "positions"}) | _EXPOSURE_ACTION_ENDPOINTS
_COVERING_ACTION_STARTS = frozenset({"cover", "covered", "covering", "covers"})
_COVERING_ACTION_ENDPOINTS = _SECURITY_ACTION_ENDPOINTS | _POSITION_ACTION_ENDPOINTS | frozenset({"short", "shorts"})
_DIRECTIONAL_ACTION_STARTS = frozenset(
    {
        "close", "closed", "closes", "closing", "enter", "entered", "entering", "enters", "exit",
        "exited", "exiting", "exits", "go", "goes", "going", "open", "opened", "opening", "opens", "went",
    }
)
_DIRECTIONAL_ACTION_ENDPOINTS = frozenset({"long", "short"}) | _EXPOSURE_ACTION_ENDPOINTS
_ACTION_FAMILIES = (
    (_SECURITY_ACTION_STARTS, _SECURITY_ACTION_ENDPOINTS),
    (_EXECUTION_ACTION_STARTS, _EXECUTION_ACTION_ENDPOINTS),
    (_POSITION_ACTION_STARTS, _POSITION_ACTION_ENDPOINTS),
    (_COVERING_ACTION_STARTS, _COVERING_ACTION_ENDPOINTS),
    (_DIRECTIONAL_ACTION_STARTS, _DIRECTIONAL_ACTION_ENDPOINTS),
)
_PASSIVE_MODALS = frozenset(
    {"must", "should", "can", "could", "may", "might", "will", "would", "shall"}
)
_PASSIVE_AUXILIARIES = frozenset(
    {"be", "been", "being", "is", "are", "was", "were", "get", "gets", "got", "getting"}
)
_PASSIVE_NEGATIONS = frozenset({"not", "never"})
_PASSIVE_NEGATED_MODAL_STEMS = {
    "can": "can",
    "couldn": "could",
    "mayn": "may",
    "mightn": "might",
    "mustn": "must",
    "shan": "shall",
    "shouldn": "should",
    "won": "will",
    "wouldn": "would",
}
_PASSIVE_UNSPACED_NEGATED_MODALS = {"cannot": "can"}
_PASSIVE_ACTION_FAMILIES = (
    (_SECURITY_ACTION_ENDPOINTS, _SECURITY_ACTION_STARTS),
    (_EXECUTION_ACTION_ENDPOINTS, _EXECUTION_ACTION_STARTS),
    (_POSITION_ACTION_ENDPOINTS, _POSITION_ACTION_STARTS | _DIRECTIONAL_ACTION_STARTS),
    (_COVERING_ACTION_ENDPOINTS, _COVERING_ACTION_STARTS),
    (_DIRECTIONAL_ACTION_ENDPOINTS, _DIRECTIONAL_ACTION_STARTS | _POSITION_ACTION_STARTS),
)
_PASSIVE_ACTION_TOKENS = frozenset(
    token
    for _, action_starts in _PASSIVE_ACTION_FAMILIES
    for token in action_starts
)
_PASSIVE_ATTRIBUTION_SUBJECTS = frozenset({"evidence", "report", "reports"})
_PASSIVE_ATTRIBUTION_VERBS = frozenset(
    {"documented", "documents", "recorded", "records", "reported", "reports", "showed", "shows"}
)
_PASSIVE_ATTRIBUTION_ACTORS = frozenset({"companies", "company", "issuer", "issuers"})
_PASSIVE_ATTRIBUTION_ARTICLES = frozenset({"a", "an", "the"})
_PASSIVE_ATTRIBUTION_CONTEXTS = frozenset({"historical", "past"})
_PASSIVE_PAST_AUXILIARIES = frozenset({"was", "were"})
_PASSIVE_APPROVED_ATTRIBUTION_TAILS = ((), ("in", "2024"))
_PASSIVE_MODAL_REFERENCE_HEADS = frozenset(
    {("equity", "method"), ("position", "estimate"), ("trade", "record")}
)
_PASSIVE_DIRECT_NOMINAL_TAILS = (
    ("a", "commonly", "purchased", "investment", "class"),
    ("family", "purchased", "investment", "units"),
)
_PASSIVE_REFERENCE_PHRASES = (("ordered", "by", "market", "capitalization"),)
_PASSIVE_DATASET_REFERENCE_HEADS = frozenset({"dataset"})
_PASSIVE_DATASET_REFERENCE_MAX_MODIFIERS = 3
_PASSIVE_DATASET_METHODOLOGY_MAX_CONTEXT_TOKENS = 8
_ACTIVE_DOCUMENTED_RESULT_REFERENCE_HEADS = frozenset(
    {("position", "estimate"), ("share", "count")}
)
_APPROVED_NEGATED_BOUNDARIES = (
    ("no", "recommendation"),
    ("no", "buy", "sell", "instruction"),
    ("no", "broker", "integration"),
    ("not", "investment", "advice"),
)
_NON_ACTION_CLASSIFICATION_PHRASES = (
    ("available", "for", "sale"),
    ("held", "for", "sale"),
    ("held", "to", "maturity"),
)
_STANDALONE_ACTION_TOKENS = frozenset(
    {
        "allocation", "broker", "brokers", "downside", "expectedreturn", "marginofsafety",
        "recommend", "recommendation", "recommendations", "recommended", "recommending", "recommends",
        "rank", "ranking", "stoploss", "takeprofit", "targetprice", "upside",
    }
)
_ACTION_TOKEN_PHRASES = (
    ("position", "size"),
    ("stop", "loss"),
    ("take", "profit"),
    ("target", "price"),
    ("expected", "return"),
    ("margin", "of", "safety"),
)
_REFERENCE_SUBJECT_TOKENS = frozenset(
    {
        "analysis", "analyses", "analyst", "analysts", "brief", "briefs", "calculation", "calculations",
        "chart", "charts",
        "data", "dataset", "datasets", "disclosure", "disclosures", "document", "documents", "estimate",
        "estimates", "evidence", "filing", "filings", "formula", "formulas", "framework", "frameworks",
        "method", "methods", "methodology", "methodologies", "model", "models", "note", "notes", "output",
        "outputs", "packet", "packets", "record", "records", "report", "reports", "research", "schedule",
        "schedules", "section", "sections", "source", "sources", "spreadsheet", "spreadsheets", "study",
        "studies", "table", "tables", "workbook", "workbooks", "worksheet", "worksheets",
    }
)
_COVERAGE_REFERENCE_SUBJECTS = frozenset(
    {
        "analyses", "analysis", "analyst", "analysts", "brief", "briefs", "disclosure", "disclosures", "document",
        "documents", "filing", "filings", "note", "notes", "report", "reports", "research", "section", "sections",
        "study", "studies",
    }
)
_REFERENCE_COVERAGE_ENDPOINTS = frozenset(
    {"equities", "equity", "securities", "security", "share", "shares", "stock", "stocks"}
)
_REFERENCE_ENDPOINT_FOLLOWERS = frozenset(
    {
        "analysis", "analyses", "based", "blotter", "blotters", "bridge", "bridges", "count", "counts", "data",
        "coverage", "date", "dates", "disclosure", "disclosures", "duration", "estimate", "estimates", "evidence", "history",
        "histories", "interest", "ledger", "ledgers", "log", "logs", "method", "methods", "metric", "metrics",
        "model", "models",
        "outstanding", "performance", "reconciliation", "reconciliations", "record", "records", "report", "reports",
        "research", "row", "rows", "schedule", "schedules", "statistic", "statistics", "summary", "summaries", "table", "tables",
        "term", "terms",
    }
)
_BUILD_REFERENCE_STARTS = frozenset({"build", "building", "builds", "built"})
_HOLD_REFERENCE_STARTS = frozenset({"held", "hold", "holding", "holds"})
_OPEN_REFERENCE_STARTS = frozenset({"open", "opened", "opening", "opens"})
_RECORD_REFERENCE_STARTS = frozenset(
    {
        "order", "ordered", "ordering", "orders", "place", "placed", "places", "placing", "route", "routed", "routes",
        "routing",
    }
)
_ACCOUNTING_COMPOUND_STARTS = frozenset(
    {"add", "added", "adding", "adds", "reduce", "reduced", "reduces", "reducing"}
)
_ACCOUNTING_CHANGE_STARTS = _ACCOUNTING_COMPOUND_STARTS | frozenset(
    {"increase", "increased", "increases", "increasing"}
)
_COVERAGE_REFERENCE_STARTS = frozenset({"initiate", "initiated", "initiates", "initiating"})
_ACCOUNTING_REFERENCE_SUBJECTS = frozenset(
    {"bank", "banks", "business", "businesses", "company", "companies", "firm", "firms", "issuer", "issuers"}
)
_OPEN_REFERENCE_FOLLOWERS = frozenset(
    {
        "blotter", "blotters", "data", "duration", "ledger", "ledgers", "model", "models", "report", "reports",
        "research", "schedule", "schedules", "workbook", "workbooks", "worksheet", "worksheets",
    }
)
_RECORD_REFERENCE_FOLLOWERS = frozenset(
    {
        "blotter", "blotters", "data", "date", "dates", "evidence", "histories", "history", "ledger", "ledgers",
        "log", "logs", "record", "records", "row", "rows", "table", "tables",
    }
)
_REFERENCE_FOLLOWER_GROUPS = (
    (_BUILD_REFERENCE_STARTS | _COVERING_ACTION_STARTS, _REFERENCE_ENDPOINT_FOLLOWERS),
    (_HOLD_REFERENCE_STARTS, frozenset({"method", "methods"})),
    (_OPEN_REFERENCE_STARTS, _OPEN_REFERENCE_FOLLOWERS),
    (_RECORD_REFERENCE_STARTS, _RECORD_REFERENCE_FOLLOWERS),
    (_ACCOUNTING_COMPOUND_STARTS, frozenset({"based"})),
    (_COVERAGE_REFERENCE_STARTS, frozenset({"coverage"})),
)
_COVERAGE_ACTION_OBJECTS = (
    _POSITION_ACTION_ENDPOINTS
    | _EXECUTION_ACTION_ENDPOINTS
    | _DIRECTIONAL_ACTION_ENDPOINTS
    | frozenset({"exposure", "exposures", "holding", "holdings"})
)
_ENDPOINT_COORDINATION_TOKENS = frozenset({"alongside", "and", "or", "plus", "then", "with"})
_ENDPOINT_COORDINATION_PHRASES = (("as", "well", "as"),)


@dataclass(frozen=True)
class _ActionToken:
    text: str
    separator_before: str


def _is_numeric_connector(value: str, index: int) -> bool:
    return (
        value[index] in {",", ".", "/", "⁄"}
        and index > 0
        and index + 1 < len(value)
        and value[index - 1].isdecimal()
        and value[index + 1].isdecimal()
    )


def _is_action_clause_boundary(char: str) -> bool:
    name = unicodedata.name(char, "")
    return (
        char in ".!?;\r\n؟।॥。！？；"
        or unicodedata.category(char) in {"Zl", "Zp"}
        or any(label in name for label in ("DANDA", "EXCLAMATION MARK", "FULL STOP", "INTERROBANG", "QUESTION MARK"))
    )


def _is_action_ignorable(char: str) -> bool:
    category = unicodedata.category(char)
    name = unicodedata.name(char, "")
    return category == "Cf" or category.startswith("M") or "FILLER" in name or name.endswith("BLANK")


def _action_token_clauses(value: str) -> tuple[tuple[_ActionToken, ...], ...]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = "".join(char for char in normalized if not _is_action_ignorable(char))
    clauses: list[tuple[_ActionToken, ...]] = []
    clause: list[_ActionToken] = []
    atom: list[str] = []
    pending_separator: list[str] = []
    atom_separator = ""

    def finish_atom() -> None:
        nonlocal atom_separator
        if atom:
            clause.append(_ActionToken("".join(atom), atom_separator))
            atom.clear()
            atom_separator = ""

    def finish_clause() -> None:
        finish_atom()
        if clause:
            clauses.append(tuple(clause))
            clause.clear()
        pending_separator.clear()

    for index, char in enumerate(normalized):
        if char.isalnum():
            if not atom:
                atom_separator = "".join(pending_separator)
                pending_separator.clear()
            atom.append(char)
            continue
        if _is_numeric_connector(normalized, index):
            continue
        finish_atom()
        if _is_action_clause_boundary(char):
            finish_clause()
        else:
            pending_separator.append(char)
    finish_clause()
    return tuple(clauses)


def _token_texts(tokens: tuple[_ActionToken, ...]) -> tuple[str, ...]:
    return tuple(token.text for token in tokens)


def _is_contraction_apostrophe(separator: str) -> bool:
    if len(separator) != 1:
        return False
    name = unicodedata.name(separator, "")
    return "APOSTROPHE" in name or "SINGLE QUOTATION MARK" in name


def _normalize_passive_modal_contractions(
    tokens: tuple[_ActionToken, ...],
) -> tuple[_ActionToken, ...]:
    normalized: list[_ActionToken] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        unspaced_modal = _PASSIVE_UNSPACED_NEGATED_MODALS.get(token.text)
        if unspaced_modal is not None:
            normalized.append(_ActionToken(unspaced_modal, token.separator_before))
            normalized.append(_ActionToken("not", ""))
            index += 1
            continue
        modal = _PASSIVE_NEGATED_MODAL_STEMS.get(token.text)
        if (
            modal is not None
            and index + 1 < len(tokens)
            and tokens[index + 1].text == "t"
            and _is_contraction_apostrophe(tokens[index + 1].separator_before)
        ):
            normalized.append(_ActionToken(modal, token.separator_before))
            normalized.append(_ActionToken("not", tokens[index + 1].separator_before))
            index += 2
            continue
        normalized.append(token)
        index += 1
    return tuple(normalized)


def _without_approved_negated_boundaries(tokens: tuple[_ActionToken, ...]) -> tuple[_ActionToken, ...]:
    ignored: set[int] = set()
    token_texts = _token_texts(tokens)
    for boundary in _APPROVED_NEGATED_BOUNDARIES:
        width = len(boundary)
        for index in range(len(tokens) - width + 1):
            if token_texts[index : index + width] == boundary:
                ignored.update(range(index, index + width))
    return tuple(token for index, token in enumerate(tokens) if index not in ignored)


def _without_non_action_classifications(tokens: tuple[_ActionToken, ...]) -> tuple[_ActionToken, ...]:
    ignored: set[int] = set()
    token_texts = _token_texts(tokens)
    for phrase in _NON_ACTION_CLASSIFICATION_PHRASES:
        width = len(phrase)
        for index in range(len(tokens) - width + 1):
            if token_texts[index : index + width] == phrase:
                ignored.update(range(index, index + width))
    return tuple(token for index, token in enumerate(tokens) if index not in ignored)


def _contains_token_phrase(tokens: tuple[_ActionToken, ...], phrase: tuple[str, ...]) -> bool:
    width = len(phrase)
    token_texts = _token_texts(tokens)
    return any(token_texts[index : index + width] == phrase for index in range(len(tokens) - width + 1))


def _has_immediate_coverage_subject(tokens: tuple[_ActionToken, ...], start_index: int) -> bool:
    return start_index > 0 and tokens[start_index - 1].text in _COVERAGE_REFERENCE_SUBJECTS


def _has_reference_modifier_context(tokens: tuple[_ActionToken, ...], start_index: int) -> bool:
    start = tokens[start_index].text
    if start not in {"buy", "sell", "short"}:
        return False
    expected_modifier = "term" if start == "short" else "side"
    if start_index + 1 >= len(tokens) or tokens[start_index + 1].text != expected_modifier:
        return False
    if start == "short" and not _is_compound_separator(tokens[start_index + 1].separator_before):
        return False
    context_limit = start_index + _REFERENCE_MODIFIER_MAX_CONTEXT_TOKENS + 2
    return any(
        token.text in _REFERENCE_SUBJECT_TOKENS or token.text in _REFERENCE_ENDPOINT_FOLLOWERS
        for token in tokens[start_index + 2 : context_limit]
    )


def _is_compound_separator(separator: str) -> bool:
    if len(separator) != 1:
        return False
    name = unicodedata.name(separator, "")
    return (
        (unicodedata.category(separator) == "Pd" or separator == "−" or "HYPHEN" in name)
        and separator not in {"—", "―"}
    )


def _is_reference_follower(token: _ActionToken) -> bool:
    separator = token.separator_before
    return bool(separator) and (separator.isspace() or _is_compound_separator(separator))


def _has_reference_adjacency(
    tokens: tuple[_ActionToken, ...],
    start_index: int,
    end_index: int,
) -> bool:
    return all(_is_reference_follower(tokens[index]) for index in range(start_index + 1, end_index + 1))


def _has_dataset_reference_modifier_run(
    tokens: tuple[_ActionToken, ...],
    start_index: int,
    end_index: int,
) -> bool:
    return _has_reference_adjacency(tokens, start_index, end_index) and not any(
        token.text in _ENDPOINT_COORDINATION_TOKENS
        for token in tokens[start_index + 1 : end_index]
    )


def _has_endpoint_coordination(
    tokens: tuple[_ActionToken, ...],
    first_endpoint_index: int,
    later_endpoint_index: int,
) -> bool:
    between = tokens[first_endpoint_index + 1 : later_endpoint_index + 1]
    token_texts = _token_texts(between)
    if any(
        token.text in _ENDPOINT_COORDINATION_TOKENS
        or any(char in token.separator_before for char in {"&", "+", ","})
        for token in between
    ):
        return True
    return any(
        token_texts[index : index + len(phrase)] == phrase
        for phrase in _ENDPOINT_COORDINATION_PHRASES
        for index in range(len(token_texts) - len(phrase) + 1)
    )


def _has_reference_coverage_endpoint(tokens: tuple[_ActionToken, ...], start_index: int) -> bool:
    return any(
        token.text in _REFERENCE_COVERAGE_ENDPOINTS
        for token in tokens[start_index + 1 :]
    )


def _has_coverage_action_object(tokens: tuple[_ActionToken, ...], start_index: int) -> bool:
    return any(token.text in _COVERAGE_ACTION_OBJECTS for token in tokens[start_index + 1 :])


def _has_allowed_reference_follower(start: str, follower: str) -> bool:
    return any(start in starts and follower in followers for starts, followers in _REFERENCE_FOLLOWER_GROUPS)


def _has_accounting_subject(tokens: tuple[_ActionToken, ...], start_index: int) -> bool:
    return start_index > 0 and tokens[start_index - 1].text in _ACCOUNTING_REFERENCE_SUBJECTS


def _is_active_reference_endpoint_head(
    tokens: tuple[_ActionToken, ...],
    start_index: int,
    endpoint_index: int,
) -> bool:
    if (
        tokens[start_index].text != "increase"
        or endpoint_index + 1 >= len(tokens)
        or endpoint_index + 2 != len(tokens)
        or (tokens[endpoint_index].text, tokens[endpoint_index + 1].text)
        not in _ACTIVE_DOCUMENTED_RESULT_REFERENCE_HEADS
        or not _has_reference_adjacency(tokens, start_index, endpoint_index + 1)
    ):
        return False
    cursor = start_index + 1
    if tokens[cursor].text in _PASSIVE_ATTRIBUTION_ARTICLES:
        cursor += 1
    for expected in ("model", "detail", "using"):
        if cursor >= endpoint_index or tokens[cursor].text != expected:
            return False
        cursor += 1
    if cursor < endpoint_index and tokens[cursor].text in _PASSIVE_ATTRIBUTION_ARTICLES:
        cursor += 1
    for expected in (
        "reviewed",
        "historical",
        "assumptions",
        "and",
        "document",
    ):
        if cursor >= endpoint_index or tokens[cursor].text != expected:
            return False
        cursor += 1
    if cursor < endpoint_index and tokens[cursor].text in _PASSIVE_ATTRIBUTION_ARTICLES:
        cursor += 1
    return cursor + 1 == endpoint_index and tokens[cursor].text == "resulting"


def _family_has_action_endpoint(
    tokens: tuple[_ActionToken, ...],
    start_index: int,
    endpoints: frozenset[str],
) -> bool:
    endpoint_limit = len(tokens)
    endpoint_index = start_index + 1
    while endpoint_index < endpoint_limit:
        if tokens[endpoint_index].text not in endpoints:
            endpoint_index += 1
            continue
        start = tokens[start_index].text
        reference_follower = (
            endpoint_index + 1 < len(tokens)
            and tokens[endpoint_index + 1].text in _REFERENCE_ENDPOINT_FOLLOWERS
            and _is_reference_follower(tokens[endpoint_index + 1])
            and _has_allowed_reference_follower(start, tokens[endpoint_index + 1].text)
        )
        accounting_equity_context = (
            tokens[endpoint_index].text == "equity"
            and start in _ACCOUNTING_CHANGE_STARTS
            and _has_accounting_subject(tokens, start_index)
        )
        reference_coverage_context = start in (_BUILD_REFERENCE_STARTS | _COVERAGE_REFERENCE_STARTS) and any(
            token.text == "coverage" for token in tokens[start_index + 1 : endpoint_index + 1]
        )
        reference_endpoint_head = _is_active_reference_endpoint_head(tokens, start_index, endpoint_index)
        if (
            not reference_follower
            and not accounting_equity_context
            and not reference_coverage_context
            and not reference_endpoint_head
        ):
            return True
        coordinated_endpoint_index = next(
            (
                index
                for index in range(endpoint_index + 1, endpoint_limit)
                if tokens[index].text in endpoints
                and _has_endpoint_coordination(tokens, endpoint_index, index)
            ),
            None,
        )
        if coordinated_endpoint_index is None:
            return False
        endpoint_index = coordinated_endpoint_index
    return False


def _contains_semantic_action(tokens: tuple[_ActionToken, ...]) -> bool:
    if any(token.text in _STANDALONE_ACTION_TOKENS for token in tokens):
        return True
    if any(_contains_token_phrase(tokens, phrase) for phrase in _ACTION_TOKEN_PHRASES):
        return True
    for starts, endpoints in _ACTION_FAMILIES:
        for start_index, token in enumerate(tokens):
            if token.text not in starts:
                continue
            if (
                token.text in _COVERING_ACTION_STARTS
                and _has_immediate_coverage_subject(tokens, start_index)
                and _has_reference_coverage_endpoint(tokens, start_index)
                and not _has_coverage_action_object(tokens, start_index)
            ):
                continue
            if _has_reference_modifier_context(tokens, start_index):
                continue
            if _family_has_action_endpoint(tokens, start_index, endpoints):
                return True
    return False


def _is_descriptive_direct_passive_attribution(
    tokens: tuple[_ActionToken, ...],
    endpoint_index: int,
    action_index: int,
) -> bool:
    lead_in = tokens[:endpoint_index]
    if tokens[endpoint_index + 1].text not in _PASSIVE_PAST_AUXILIARIES:
        return False
    if not any(token.text in _PASSIVE_ATTRIBUTION_CONTEXTS for token in lead_in):
        return False
    if not any(token.text in _PASSIVE_ATTRIBUTION_SUBJECTS for token in lead_in):
        return False
    if not any(token.text in _PASSIVE_ATTRIBUTION_VERBS for token in lead_in):
        return False
    if action_index + 1 >= len(tokens) or tokens[action_index + 1].text != "by":
        return False
    actor_index = action_index + 2
    if actor_index < len(tokens) and tokens[actor_index].text in _PASSIVE_ATTRIBUTION_ARTICLES:
        actor_index += 1
    if actor_index >= len(tokens) or tokens[actor_index].text not in _PASSIVE_ATTRIBUTION_ACTORS:
        return False
    return _token_texts(tokens[actor_index + 1 :]) in _PASSIVE_APPROVED_ATTRIBUTION_TAILS


def _is_direct_passive_nominal_tail(tokens: tuple[_ActionToken, ...], auxiliary_index: int) -> bool:
    return _token_texts(tokens[auxiliary_index + 1 :]) in _PASSIVE_DIRECT_NOMINAL_TAILS


def _is_passive_modal_reference_head(
    tokens: tuple[_ActionToken, ...],
    endpoint_index: int,
    modal_index: int,
) -> bool:
    if modal_index <= endpoint_index + 1:
        return False
    return (tokens[endpoint_index].text, tokens[endpoint_index + 1].text) in _PASSIVE_MODAL_REFERENCE_HEADS


def _is_bounded_dataset_methodology_reference(
    tokens: tuple[_ActionToken, ...],
    endpoint_index: int,
    action_index: int,
) -> bool:
    if (
        tokens[action_index].text != "purchased"
        or endpoint_index + 1 >= len(tokens)
        or (tokens[endpoint_index].text, tokens[endpoint_index + 1].text) != ("share", "count")
        or not _is_reference_follower(tokens[endpoint_index + 1])
    ):
        return False
    context_start = max(
        endpoint_index + 2,
        action_index - _PASSIVE_DATASET_METHODOLOGY_MAX_CONTEXT_TOKENS,
    )
    using_index = next(
        (
            index
            for index in range(action_index - 1, context_start - 1, -1)
            if tokens[index].text == "using"
        ),
        None,
    )
    if using_index is None:
        return False
    pre_nominal_limit = min(
        len(tokens),
        action_index + _PASSIVE_DATASET_REFERENCE_MAX_MODIFIERS + 2,
    )
    pre_nominal_reference = any(
        tokens[dataset_index].text in _PASSIVE_DATASET_REFERENCE_HEADS
        and _has_dataset_reference_modifier_run(tokens, using_index, dataset_index)
        for dataset_index in range(action_index + 1, pre_nominal_limit)
    )
    post_nominal_start = max(
        using_index + 1,
        action_index - _PASSIVE_DATASET_REFERENCE_MAX_MODIFIERS - 1,
    )
    provider_index = action_index + 2
    if (
        provider_index < len(tokens)
        and tokens[action_index + 1].text == "from"
        and tokens[provider_index].text in _PASSIVE_ATTRIBUTION_ARTICLES
    ):
        provider_index += 1
    post_nominal_reference = (
        provider_index < len(tokens)
        and action_index + 1 < len(tokens)
        and tokens[action_index + 1].text == "from"
        and any(
            tokens[dataset_index].text in _PASSIVE_DATASET_REFERENCE_HEADS
            and _has_dataset_reference_modifier_run(tokens, using_index, action_index)
            for dataset_index in range(post_nominal_start, action_index)
        )
        and _has_reference_adjacency(tokens, using_index, provider_index)
    )
    if not pre_nominal_reference and not post_nominal_reference:
        return False
    return not any(
        token.text in _PASSIVE_ACTION_TOKENS
        for token in tokens[action_index + 1 :]
    )


def _is_passive_reference_phrase(
    tokens: tuple[_ActionToken, ...],
    endpoint_index: int,
    action_index: int,
) -> bool:
    if _is_bounded_dataset_methodology_reference(tokens, endpoint_index, action_index):
        return True
    token_texts = _token_texts(tokens)
    for phrase in _PASSIVE_REFERENCE_PHRASES:
        if token_texts[action_index : action_index + len(phrase)] != phrase:
            continue
        if not all(
            _is_reference_follower(tokens[index])
            for index in range(action_index + 1, action_index + len(phrase))
        ):
            continue
        return not any(token.text in _PASSIVE_ACTION_TOKENS for token in tokens[action_index + len(phrase) :])
    return False


def _contains_modal_passive_action(tokens: tuple[_ActionToken, ...]) -> bool:
    for endpoints, action_starts in _PASSIVE_ACTION_FAMILIES:
        for endpoint_index, endpoint in enumerate(tokens[:-1]):
            if endpoint.text not in endpoints:
                continue
            chain_index = endpoint_index + 1
            chain_limit = len(tokens)
            modal_index = next(
                (
                    index
                    for index in range(chain_index, chain_limit)
                    if tokens[index].text in _PASSIVE_MODALS
                ),
                None,
            )
            if (
                modal_index is not None
                and _is_passive_modal_reference_head(tokens, endpoint_index, modal_index)
            ):
                continue
            if modal_index is not None:
                has_auxiliary = False
                action_range = range(modal_index + 1, chain_limit)
            elif tokens[chain_index].text in _PASSIVE_AUXILIARIES:
                if _is_direct_passive_nominal_tail(tokens, chain_index):
                    continue
                has_auxiliary = True
                action_range = range(chain_index + 1, chain_limit)
            else:
                continue
            for action_index in action_range:
                text = tokens[action_index].text
                if text in action_starts:
                    if not has_auxiliary:
                        break
                    if _is_passive_reference_phrase(tokens, endpoint_index, action_index):
                        break
                    if (
                        modal_index is None
                        and _is_descriptive_direct_passive_attribution(tokens, endpoint_index, action_index)
                    ):
                        break
                    return True
                if text in _PASSIVE_AUXILIARIES:
                    has_auxiliary = True
                    continue
                if text in _PASSIVE_MODALS or text in _PASSIVE_NEGATIONS:
                    continue
                continue
    return False


def contains_portable_action_language(value: str) -> bool:
    for clause in _action_token_clauses(value):
        action_tokens = _without_non_action_classifications(clause)
        action_tokens = _without_approved_negated_boundaries(action_tokens)
        action_tokens = _normalize_passive_modal_contractions(action_tokens)
        if _contains_semantic_action(action_tokens) or _contains_modal_passive_action(action_tokens):
            return True
    return False
