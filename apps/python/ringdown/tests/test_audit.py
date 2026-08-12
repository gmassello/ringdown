from __future__ import annotations

import json

from fake import scenarios
from ringdown.audit import (
    GENESIS,
    append_record,
    attempt_record,
    chain_checks,
    sealed,
    verdict_record,
    verification_record,
)
from ringdown.calle import parse_turns
from ringdown.canonical import canonical_json
from ringdown.escalate import Attempt, LadderResult
from ringdown.extract import extract
from ringdown.verify import all_ok
from tests.data import ALICE, LADDER

EXTRACTION = extract(parse_turns(scenarios.answer_ack(ALICE.name, "alice").turns))


def an_attempt(**overrides) -> Attempt:
    fields = {
        "rung": LADDER[0],
        "key": "rd-inc-1-primary-1-abc123def456",
        "attempt_id": "inc-1/primary/1",
        "verdict": "not_acknowledged",
        "reason": "no_answer",
        "call_id": "call_fake1",
    }
    return Attempt(**{**fields, **overrides})


def write_run(path, verdict="unacknowledged", attempt=None):
    attempt = attempt or an_attempt()
    append_record(path, attempt_record(attempt, "inc-1"))
    append_record(path, verdict_record("inc-1", LadderResult(verdict, (attempt,))))
    append_record(
        path,
        verification_record("inc-1", [(True, "run for Alice Okafor reports no acknowledgement")]),
    )


def read_lines(path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def write_back(path, records) -> None:
    path.write_text("".join(canonical_json(record) + "\n" for record in records))


def test_a_run_writes_one_attempt_record_a_verdict_and_a_verification(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    write_run(ledger)

    records = read_lines(ledger)

    assert [record["type"] for record in records] == ["attempt", "verdict", "verification"]
    assert records[0]["prev"] == GENESIS
    assert records[1]["prev"] == records[0]["hash"]


def test_the_ledger_chain_verifies_end_to_end(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    write_run(ledger)

    checks = chain_checks(ledger)

    assert len(checks) == 7
    assert all_ok(checks)
    assert checks[0][1] == "record 1 links to the genesis hash"
    assert checks[6][1] == "record 2 verdict unacknowledged follows from the recorded attempts"


def test_a_rewritten_record_with_a_recomputed_hash_still_breaks_the_chain(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    write_run(ledger)
    records = read_lines(ledger)
    records[1]["verdict"] = "acknowledged"
    records[1] = sealed(records[1])
    write_back(ledger, records)

    checks = dict((label, ok) for ok, label in chain_checks(ledger))

    assert checks["record 2 hash matches its content"]
    assert not checks["record 3 links to record 2"]


def test_a_rewritten_verdict_with_the_whole_chain_relinked_is_still_detected(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    write_run(ledger)
    records = read_lines(ledger)
    records[1]["verdict"] = "acknowledged"
    records[1] = sealed(records[1])
    records[2]["prev"] = records[1]["hash"]
    records[2] = sealed(records[2])
    write_back(ledger, records)

    checks = chain_checks(ledger)

    links_and_hashes = checks[:6]
    assert all(ok for ok, _ in links_and_hashes)
    assert checks[6] == (
        False,
        "record 2 verdict acknowledged does not follow from the recorded attempts (unacknowledged)",
    )


def test_a_fabricated_verdict_with_no_attempts_underneath_does_not_follow(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    result = LadderResult("acknowledged", (an_attempt(verdict="acknowledged", extraction=EXTRACTION),))
    append_record(ledger, verdict_record("inc-1", result))

    checks = chain_checks(ledger)

    assert (
        False,
        "record 1 verdict acknowledged does not follow from the recorded attempts (unacknowledged)",
    ) in checks


def test_two_incidents_interleaved_in_one_ledger_each_derive_their_own_verdict(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    one = an_attempt(attempt_id="inc-1/primary/1")
    two = an_attempt(attempt_id="inc-2/primary/1", verdict="declined")
    append_record(ledger, attempt_record(one, "inc-1"))
    append_record(ledger, attempt_record(two, "inc-2"))
    append_record(ledger, verdict_record("inc-1", LadderResult("unacknowledged", (one,))))
    append_record(ledger, verdict_record("inc-2", LadderResult("declined", (two,))))

    checks = chain_checks(ledger)

    assert all_ok(checks)
    assert checks[-2][1] == "record 3 verdict unacknowledged follows from the recorded attempts"
    assert checks[-1][1] == "record 4 verdict declined follows from the recorded attempts"


def test_an_attempt_written_before_the_incident_field_existed_still_verifies(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    attempt = an_attempt()
    older = {name: value for name, value in attempt_record(attempt, "inc-1").items()
             if name != "incident"}
    append_record(ledger, older)
    append_record(ledger, verdict_record("inc-1", LadderResult("unacknowledged", (attempt,))))

    assert all_ok(chain_checks(ledger))


def test_the_ledger_masks_phones_and_keeps_only_the_quoted_spans(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    write_run(ledger, verdict="acknowledged", attempt=an_attempt(verdict="acknowledged", extraction=EXTRACTION))

    raw = ledger.read_text()

    assert ALICE.phone not in raw
    assert "+1********00" in raw
    assert "give me fifteen minutes" in raw
    assert "automated on-call page" not in raw


def test_the_ledger_file_is_created_private(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    write_run(ledger)

    assert ledger.stat().st_mode & 0o777 == 0o600


def test_an_unreadable_ledger_line_is_a_failed_check_not_a_crash(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    write_run(ledger)
    with ledger.open("a") as handle:
        handle.write("{not json\n")

    checks = chain_checks(ledger)

    assert checks == [(False, "record 4 is not readable JSON")]
