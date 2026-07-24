from __future__ import annotations

import unicodedata


UNSAFE_RECORD_SEPARATOR_CATEGORIES = frozenset({"Zl", "Zp"})


def _unsafe_structural_character(character: str) -> bool:
    codepoint = ord(character)
    return (
        codepoint < 0x20
        or 0x7F <= codepoint <= 0x9F
        or unicodedata.category(character)
        in UNSAFE_RECORD_SEPARATOR_CATEGORIES
    )


def is_control_free(value: object) -> bool:
    """Reject controls plus Unicode line and paragraph record separators."""

    return isinstance(value, str) and not any(
        _unsafe_structural_character(character)
        for character in value
    )


def require_control_free(value: object, reason: str) -> str:
    if not is_control_free(value):
        raise ValueError(reason)
    return value


def escape_structural_token(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("render_structural_token_invalid")
    return "".join(
        (
            f"\\u{ord(character):04x}"
            if _unsafe_structural_character(character)
            else character
        )
        for character in value
    )
