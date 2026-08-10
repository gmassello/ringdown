from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Sequence

from ringdown.calle import CalleError, CallSnapshot, RestClient
from ringdown.dispositions import Grounded, Verdict, classify, ground
from ringdown.extract import Extraction, extract
from ringdown.incident import Incident, Rung
from ringdown.script import call_payload, idempotency_key

LadderVerdict = Literal["acknowledged", "declined", "unacknowledged", "unknown"]


@dataclass(frozen=True)
class Attempt:
    rung: Rung
    key: str
    verdict: Verdict
    reason: str
    call_id: str | None = None
    snapshot: CallSnapshot | None = None
    extraction: Extraction | None = None
    grounded: Grounded | None = None


@dataclass(frozen=True)
class LadderResult:
    verdict: LadderVerdict
    attempts: tuple[Attempt, ...]


def place_and_settle(
    rest: RestClient,
    incident: Incident,
    rung: Rung,
    attempt: int = 1,
    log: Callable[[str], None] = print,
) -> Attempt:
    payload = call_payload(incident, rung, attempt)
    key = idempotency_key(payload)
    log(f"idempotency key {key}")
    try:
        created = rest.create_call(payload, key)
    except CalleError as error:
        if not error.ambiguous:
            return Attempt(rung=rung, key=key, verdict="not_acknowledged", reason=error.code)
        log(f"CALL-E returned {error.code} without saying whether the call exists.")
        if not error.retriable:
            log("A call may be live for this person.")
            return Attempt(rung=rung, key=key, verdict="unknown", reason=error.code)
        log(f"Reconciling {key}.")
        try:
            created = rest.create_call(payload, key)
        except CalleError as replay:
            log(f"Reconciling {key} failed with {replay.code}.")
            log("A call may be live for this person.")
            return Attempt(rung=rung, key=key, verdict="unknown", reason=replay.code)
        log(f"Reconciled to call {created.id}.")
    policy = incident.policy
    try:
        snapshot = rest.wait_for_result(
            created.id, policy.per_call_timeout_seconds, policy.poll_interval_seconds
        )
    except CalleError as error:
        return Attempt(
            rung=rung, key=key, verdict="unknown", reason=error.code, call_id=created.id
        )
    extraction = extract(snapshot.turns)
    grounded = ground(extraction, snapshot.turns)
    judged = classify(snapshot, extraction, grounded, rung.contact, policy)
    return Attempt(
        rung=rung,
        key=key,
        verdict=judged.verdict,
        reason=judged.reason,
        call_id=created.id,
        snapshot=snapshot,
        extraction=extraction,
        grounded=grounded,
    )


def run_ladder(
    rest: RestClient,
    incident: Incident,
    rungs: Sequence[Rung],
    log: Callable[[str], None] = print,
) -> LadderResult:
    attempts: list[Attempt] = []
    for rung in rungs:
        placed = place_and_settle(rest, incident, rung, log=log)
        attempts.append(placed)
        if placed.verdict != "not_acknowledged":
            return LadderResult(placed.verdict, tuple(attempts))
    return LadderResult("unacknowledged", tuple(attempts))
