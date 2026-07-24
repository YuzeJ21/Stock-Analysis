from __future__ import annotations


def is_control_free(value: object) -> bool:
    return isinstance(value, str) and not any(
        ord(character) < 0x20 or 0x7F <= ord(character) <= 0x9F
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
            if ord(character) < 0x20
            or 0x7F <= ord(character) <= 0x9F
            else character
        )
        for character in value
    )
