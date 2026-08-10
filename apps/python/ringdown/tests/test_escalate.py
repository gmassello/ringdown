from __future__ import annotations

from fake import scenarios
from ringdown.escalate import place_and_settle, run_ladder
from ringdown.incident import Policy
from tests.data import ALICE, BEN, CARLA, LADDER, an_incident

FAST = Policy(per_call_timeout_seconds=0.05, poll_interval_seconds=0.005)


def test_the_on_call_engineer_picks_up_and_the_ladder_stops_at_the_first_rung(
    serving, rest_client
):
    server = serving({ALICE.phone: scenarios.answer_ack(ALICE.name, "alice")})

    result = run_ladder(rest_client(server), an_incident(policy=FAST), LADDER)

    assert result.verdict == "acknowledged"
    assert len(result.attempts) == 1
    assert result.attempts[0].extraction.eta_minutes == 15
    assert len(server.created) == 1


def test_an_ambiguous_yes_without_an_eta_does_not_acknowledge(serving, rest_client):
    server = serving(
        {
            ALICE.phone: scenarios.ambiguous_yes(ALICE.name, "alice"),
            BEN.phone: scenarios.answer_ack(BEN.name, "ben", "i can be on it in twenty minutes"),
        }
    )

    result = run_ladder(rest_client(server), an_incident(policy=FAST), LADDER)

    assert result.verdict == "acknowledged"
    assert [a.verdict for a in result.attempts] == ["not_acknowledged", "acknowledged"]
    assert result.attempts[0].reason == "no_eta"
    assert result.attempts[1].extraction.eta_minutes == 20


def test_a_reconciled_attempt_places_exactly_one_call_and_never_wakes_the_backup(
    serving, rest_client
):
    server = serving(
        {
            ALICE.phone: scenarios.error_after_create(ALICE.name, "alice"),
            BEN.phone: scenarios.answer_ack(BEN.name, "ben"),
        }
    )
    messages: list[str] = []

    result = run_ladder(rest_client(server), an_incident(policy=FAST), LADDER, log=messages.append)

    assert result.verdict == "acknowledged"
    assert len(result.attempts) == 1
    assert len(server.created) == 1
    assert all(record.recipient_phone == ALICE.phone for record in server.created)
    assert any(message.startswith("Reconciled to call") for message in messages)


def test_an_explicit_decline_cuts_the_ladder(serving, rest_client):
    server = serving(
        {
            ALICE.phone: scenarios.declined(ALICE.name, "alice"),
            BEN.phone: scenarios.answer_ack(BEN.name, "ben"),
        }
    )

    result = run_ladder(rest_client(server), an_incident(policy=FAST), LADDER)

    assert result.verdict == "declined"
    assert len(result.attempts) == 1
    assert len(server.created) == 1


def test_a_create_that_stays_ambiguous_after_one_replay_cuts_the_whole_ladder(
    serving, rest_client
):
    server = serving(
        {
            ALICE.phone: scenarios.error_before_create(ALICE.name, "alice"),
            BEN.phone: scenarios.answer_ack(BEN.name, "ben"),
        }
    )
    messages: list[str] = []

    result = run_ladder(rest_client(server), an_incident(policy=FAST), LADDER, log=messages.append)

    assert result.verdict == "unknown"
    assert len(result.attempts) == 1
    assert len(server.created) == 0
    assert "A call may be live for this person." in messages


def test_a_call_that_never_settles_is_unknown_not_a_failure(serving, rest_client):
    server = serving({ALICE.phone: scenarios.queued_forever()})

    result = run_ladder(rest_client(server), an_incident(policy=FAST), LADDER)

    assert result.verdict == "unknown"
    assert result.attempts[0].reason == "poll_timeout"
    assert result.attempts[0].call_id is not None


def test_an_injected_voicemail_transcript_changes_nothing_on_the_ladder(serving, rest_client):
    server = serving(
        {
            ALICE.phone: scenarios.injected_voicemail(ALICE.name),
            BEN.phone: scenarios.answer_ack(BEN.name, "ben"),
        }
    )

    result = run_ladder(rest_client(server), an_incident(policy=FAST), LADDER)

    assert result.verdict == "acknowledged"
    assert result.attempts[0].verdict == "not_acknowledged"
    assert result.attempts[0].reason == "voicemail"
    assert result.attempts[1].rung.contact == BEN


def test_a_provider_refusal_moves_down_the_ladder_without_a_replay(serving, rest_client):
    server = serving(
        {
            ALICE.phone: scenarios.refused(),
            BEN.phone: scenarios.answer_ack(BEN.name, "ben"),
        }
    )

    result = run_ladder(rest_client(server), an_incident(policy=FAST), LADDER)

    assert result.verdict == "acknowledged"
    assert result.attempts[0].verdict == "not_acknowledged"
    assert result.attempts[0].reason == "call_not_ready"
    assert result.attempts[0].call_id is None
    assert len(server.created) == 1


def test_the_ladder_runs_out_unacknowledged_when_nobody_commits(serving, rest_client):
    server = serving(
        {
            ALICE.phone: scenarios.no_answer(),
            BEN.phone: scenarios.voicemail(BEN.name),
            CARLA.phone: scenarios.low_confidence(CARLA.name),
        }
    )

    result = run_ladder(rest_client(server), an_incident(policy=FAST), LADDER)

    assert result.verdict == "unacknowledged"
    assert [a.reason for a in result.attempts] == ["no_answer", "voicemail", "low_confidence"]
    assert len(server.created) == 3


def test_the_idempotency_key_is_printed_before_the_request_is_sent(serving, rest_client):
    server = serving({ALICE.phone: scenarios.error_before_create(ALICE.name, "alice")})
    messages: list[str] = []

    attempt = place_and_settle(
        rest_client(server), an_incident(policy=FAST), LADDER[0], log=messages.append
    )

    assert attempt.verdict == "unknown"
    assert messages[0] == f"idempotency key {attempt.key}"
    assert server.requests == 2
