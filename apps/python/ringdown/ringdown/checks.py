from __future__ import annotations

from typing import Sequence

Check = tuple[bool | None, str]
Block = tuple[str, list[Check]]

MARKS = {True: "x", False: " ", None: "?"}


def all_checks(blocks: Sequence[Block]) -> list[Check]:
    return [check for _, checks in blocks for check in checks]


def passed(checks: Sequence[Check]) -> int:
    return sum(1 for ok, _ in checks if ok is True)


def unresolved(checks: Sequence[Check]) -> int:
    return sum(1 for ok, _ in checks if ok is None)


def contradicted(checks: Sequence[Check]) -> int:
    return sum(1 for ok, _ in checks if ok is False)


def all_ok(checks: Sequence[Check]) -> bool:
    return bool(checks) and passed(checks) == len(checks)


def tally(checks: Sequence[Check]) -> str:
    unknown = unresolved(checks)
    tail = f", {unknown} unresolved" if unknown else ""
    return f"verified {passed(checks)}/{len(checks)}{tail}"


def render_blocks(blocks: Sequence[Block]) -> str:
    lines: list[str] = []
    for title, checks in blocks:
        if lines:
            lines.append("")
        lines.append(f"# {title}")
        lines.extend(f"- [{MARKS[ok]}] {label}" for ok, label in checks)
    lines.extend(["", tally(all_checks(blocks))])
    return "\n".join(lines)
