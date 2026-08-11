from __future__ import annotations

from datetime import datetime
from typing import Sequence

from ringdown.calle import STATUS_MAP, CalleError, McpClient
from ringdown.dispositions import ground
from ringdown.escalate import Attempt, LadderResult
from ringdown.extract import extract, minutes_in, normalise
from ringdown.incident import first_name, mask_phone

Check = tuple[bool, str]
Block = tuple[str, list[Check]]


def inside(completed_at: str | None, window: tuple[datetime, datetime]) -> bool:
    if not completed_at:
        return False
    try:
        moment = datetime.fromisoformat(completed_at)
    except ValueError:
        return False
    if moment.tzinfo is None:
        return False
    return window[0] <= moment <= window[1]


def ack_checks(
    mcp: McpClient, attempt: Attempt, window: tuple[datetime, datetime]
) -> list[Check]:
    contact = attempt.rung.contact
    returned = f"second channel returned a run for call {attempt.call_id}"
    try:
        run = mcp.get_call_run(attempt.call_id)
    except CalleError:
        return [(False, returned)]
    extraction = attempt.extraction
    grounded = ground(extraction, run.turns)
    return [
        (True, returned),
        (run.call_id == attempt.call_id, f"run reports call id {attempt.call_id}"),
        (
            run.metadata.get("ringdown_attempt_id") == attempt.attempt_id,
            f"run echoes attempt id {attempt.attempt_id}",
        ),
        (
            run.recipient_phone == contact.phone,
            f"run reached {contact.name} at {mask_phone(contact.phone)}",
        ),
        (
            STATUS_MAP.get(run.status) == attempt.snapshot.status,
            f"run status {run.status} maps to the recorded {attempt.snapshot.status}",
        ),
        (
            extract(run.turns).disposition == "acknowledged",
            "re-extracting the second channel transcript gives disposition acknowledged",
        ),
        (
            grounded.disposition.grounded,
            "the recorded disposition span is spoken by the recipient",
        ),
        (
            grounded.owner.grounded and first_name(contact) in normalise(extraction.owner_span),
            f"the recorded owner {contact.name} is spoken by the recipient",
        ),
        (
            grounded.eta.grounded and minutes_in(extraction.eta_span) == extraction.eta_minutes,
            f"the recorded ETA of {extraction.eta_minutes} minutes is spoken by the recipient",
        ),
        (inside(run.completed_at, window), "the run finished inside the escalation window"),
    ]


def no_ack_checks(mcp: McpClient, attempt: Attempt) -> list[Check]:
    label = f"run for {attempt.rung.contact.name} reports no acknowledgement"
    try:
        run = mcp.get_call_run(attempt.call_id)
    except CalleError:
        return [(False, label)]
    re_extracted = extract(run.turns)
    committed = re_extracted.disposition == "acknowledged" and re_extracted.eta_minutes is not None
    return [(not committed, label)]


def verify_ladder(
    mcp: McpClient,
    incident_id: str,
    result: LadderResult,
    window: tuple[datetime, datetime],
) -> list[Block]:
    blocks: list[Block] = []
    for position, attempt in enumerate(result.attempts, 1):
        if attempt.verdict == "unknown" or attempt.call_id is None:
            continue
        title = (
            f"Verification of {incident_id} attempt {position} "
            f"({attempt.rung.contact.id}) on the second channel"
        )
        checks = (
            ack_checks(mcp, attempt, window)
            if attempt.verdict == "acknowledged"
            else no_ack_checks(mcp, attempt)
        )
        blocks.append((title, checks))
    return blocks


def all_checks(blocks: Sequence[Block]) -> list[Check]:
    return [check for _, checks in blocks for check in checks]


def passed(checks: Sequence[Check]) -> int:
    return sum(ok for ok, _ in checks)


def all_ok(checks: Sequence[Check]) -> bool:
    return bool(checks) and passed(checks) == len(checks)


def tally(checks: Sequence[Check]) -> str:
    return f"verified {passed(checks)}/{len(checks)}"


def render_blocks(blocks: Sequence[Block]) -> str:
    lines: list[str] = []
    for title, checks in blocks:
        if lines:
            lines.append("")
        lines.append(f"# {title}")
        lines.extend(f"- [{'x' if ok else ' '}] {label}" for ok, label in checks)
    lines.extend(["", tally(all_checks(blocks))])
    return "\n".join(lines) + "\n"
