from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Sequence

from ringdown.calle import CalleError, CallSnapshot, RestClient
from ringdown.dispositions import Verdict, classify, ground
from ringdown.extract import Extraction, extract
from ringdown.incident import Incident, Rung
from ringdown.script import attempt_id, call_payload, idempotency_key

LadderVerdict = Literal["acknowledged", "declined", "unacknowledged", "unknown"]


@dataclass(frozen=True)
class Attempt:
    rung: Rung
    key: str
    attempt_id: str
    verdict: Verdict
    reason: str
    call_id: str | None = None
    snapshot: CallSnapshot | None = None
    extraction: Extraction | None = None


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
    aid = attempt_id(incident, rung, attempt)
    log(f"idempotency key {key}")
    try:
        created = rest.create_call(payload, key)
    except CalleError as error:
        if not error.ambiguous:
            return Attempt(
                rung=rung, key=key, attempt_id=aid, verdict="not_acknowledged", reason=error.code
            )
        log(f"CALL-E returned {error.code} without saying whether the call exists.")
        if not error.retriable:
            log("A call may be live for this person.")
            return Attempt(rung=rung, key=key, attempt_id=aid, verdict="unknown", reason=error.code)
        log(f"Reconciling {key}.")
        try:
            created = rest.create_call(payload, key)
        except CalleError as replay:
            log(f"Reconciling {key} failed with {replay.code}.")
            log("A call may be live for this person.")
            return Attempt(
                rung=rung, key=key, attempt_id=aid, verdict="unknown", reason=replay.code
            )
        log(f"Reconciled to call {created.id}.")
    policy = incident.policy
    try:
        snapshot = rest.wait_for_result(
            created.id, policy.per_call_timeout_seconds, policy.poll_interval_seconds
        )
    except CalleError as error:
        return Attempt(
            rung=rung,
            key=key,
            attempt_id=aid,
            verdict="unknown",
            reason=error.code,
            call_id=created.id,
        )
    extraction = extract(snapshot.turns)
    judged = classify(
        snapshot, extraction, ground(extraction, snapshot.turns), rung.contact, policy
    )
    return Attempt(
        rung=rung,
        key=key,
        attempt_id=aid,
        verdict=judged.verdict,
        reason=judged.reason,
        call_id=created.id,
        snapshot=snapshot,
        extraction=extraction,
    )


def ladder_verdict(verdicts: Sequence[str]) -> LadderVerdict:
    return next((v for v in verdicts if v != "not_acknowledged"), "unacknowledged")


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
            break
    return LadderResult(ladder_verdict([a.verdict for a in attempts]), tuple(attempts))
