from __future__ import annotations

import pytest

from fake import scenarios
from fake.calle_server import FakeCalleServer
from ringdown.calle import (
    CalleError,
    McpClient,
    RestClient,
    UntrustedHost,
    assert_trusted_base_url,
)
from ringdown.script import attempt_id, call_payload, idempotency_key
from tests.conftest import ALICE, LADDER

KEY = "rd-test-1"


def clients(server: FakeCalleServer) -> tuple[RestClient, McpClient]:
    return (
        RestClient(server.base_url, "rd_test_key", timeout=5),
        McpClient(server.mcp_url, "rd_test_key", timeout=5),
    )


def serving(scenario) -> FakeCalleServer:
    return FakeCalleServer({ALICE.phone: scenario})


def payload(incident) -> dict:
    return call_payload(incident, LADDER[0], 1)


def test_a_plain_http_host_that_is_not_loopback_never_receives_the_api_key():
    with pytest.raises(UntrustedHost, match="plain http"):
        assert_trusted_base_url("http://calle.example.com")


def test_an_unknown_https_host_is_refused_unless_it_is_named():
    with pytest.raises(UntrustedHost, match="refusing to send an API key"):
        assert_trusted_base_url("https://calle.example.com")

    assert assert_trusted_base_url(
        "https://calle.example.com", frozenset({"calle.example.com"})
    ) == "https://calle.example.com"


def test_the_production_host_and_loopback_are_trusted_without_being_named():
    assert assert_trusted_base_url("https://api.heycall-e.com/") == "https://api.heycall-e.com"
    assert assert_trusted_base_url("http://127.0.0.1:8080") == "http://127.0.0.1:8080"


def test_a_lookalike_host_is_not_matched_as_a_prefix_of_a_trusted_one():
    for lookalike in (
        "https://api.heycall-e.com.evil.test",
        "https://evil.test/api.heycall-e.com",
        "https://notapi.heycall-e.com",
    ):
        with pytest.raises(UntrustedHost):
            assert_trusted_base_url(lookalike)


def test_a_url_that_is_not_http_is_refused():
    for bad in ("ftp://api.heycall-e.com", "file:///etc/passwd", "not a url"):
        with pytest.raises(UntrustedHost):
            assert_trusted_base_url(bad)


def test_a_created_call_is_read_back_from_the_placing_channel(incident):
    with serving(scenarios.answer_ack(ALICE.name, "alice")) as server:
        rest, _ = clients(server)

        created = rest.create_call(payload(incident), KEY)
        settled = rest.wait_for_result(created.id, timeout=5, interval=0)

        assert created.status == "queued"
        assert settled.terminal
        assert settled.task_completed is True
        assert settled.confidence_score == 0.94
        assert settled.recipient_phone == ALICE.phone
        assert settled.metadata["ringdown_attempt_id"] == attempt_id(incident, LADDER[0], 1)
        assert any("taking this incident" in turn.text for turn in settled.turns)


def test_the_verifying_channel_reads_the_same_call_without_the_provider_judgement(incident):
    with serving(scenarios.answer_ack(ALICE.name, "alice")) as server:
        rest, mcp = clients(server)

        created = rest.create_call(payload(incident), KEY)
        rest.wait_for_result(created.id, timeout=5, interval=0)
        run = mcp.get_call_run(created.id)

        assert run.call_id == created.id
        assert run.status == "COMPLETED"
        assert run.recipient_phone == ALICE.phone
        assert run.metadata["ringdown_attempt_id"] == attempt_id(incident, LADDER[0], 1)
        assert not hasattr(run, "confidence_score")


def test_a_voicemail_keeps_its_own_word_on_the_verifying_channel(incident):
    with serving(scenarios.voicemail(ALICE.name)) as server:
        rest, mcp = clients(server)

        created = rest.create_call(payload(incident), KEY)
        settled = rest.wait_for_result(created.id, timeout=5, interval=0)

        assert (settled.status, settled.failure_code) == ("failed", "voicemail")
        assert mcp.get_call_run(created.id).status == "VOICEMAIL"


def test_a_dropped_connection_is_ambiguous_and_can_be_replayed(incident):
    with serving(scenarios.dropped_connection(ALICE.name, "alice")) as server:
        rest, _ = clients(server)

        with pytest.raises(CalleError) as raised:
            rest.create_call(payload(incident), KEY)

        assert raised.value.status is None
        assert raised.value.ambiguous
        assert raised.value.retriable


def test_a_lost_reply_after_the_call_was_created_is_ambiguous(incident):
    with serving(scenarios.error_after_create(ALICE.name, "alice")) as server:
        rest, _ = clients(server)

        with pytest.raises(CalleError) as raised:
            rest.create_call(payload(incident), KEY)

        assert raised.value.status == 503
        assert raised.value.ambiguous and raised.value.retriable
        assert len(server.created) == 1


def test_a_key_replayed_with_a_different_body_is_ambiguous_but_never_retried(incident):
    with serving(scenarios.answer_ack(ALICE.name, "alice")) as server:
        rest, _ = clients(server)
        rest.create_call(payload(incident), KEY)

        edited = {**payload(incident), "task": "something else entirely"}
        with pytest.raises(CalleError) as raised:
            rest.create_call(edited, KEY)

        assert raised.value.code == "idempotency_conflict"
        assert raised.value.ambiguous
        assert not raised.value.retriable


def test_a_provider_refusal_is_neither_ambiguous_nor_retriable(incident):
    with serving(scenarios.refused()) as server:
        rest, _ = clients(server)

        with pytest.raises(CalleError) as raised:
            rest.create_call(payload(incident), KEY)

        assert raised.value.code == "call_not_ready"
        assert not raised.value.ambiguous
        assert raised.value.details["questions"]
        assert len(server.created) == 0


def test_a_call_that_never_settles_times_out_instead_of_reporting_a_failure(incident):
    with serving(scenarios.queued_forever()) as server:
        rest, _ = clients(server)
        created = rest.create_call(payload(incident), KEY)

        with pytest.raises(CalleError) as raised:
            rest.wait_for_result(created.id, timeout=0.05, interval=0)

        assert raised.value.code == "poll_timeout"
        assert raised.value.ambiguous
        assert "queued" in raised.value.message


def test_polling_walks_a_slow_call_through_in_progress_to_completed(incident):
    with serving(scenarios.slow_pickup(ALICE.name, "alice")) as server:
        rest, _ = clients(server)
        created = rest.create_call(payload(incident), KEY)

        assert rest.get_call(created.id).status == "in_progress"
        assert rest.wait_for_result(created.id, timeout=5, interval=0).status == "completed"


def test_a_call_the_verifying_channel_cannot_see_raises_instead_of_returning_empty(incident):
    with serving(scenarios.unseen_on_second_channel(ALICE.name, "alice")) as server:
        rest, mcp = clients(server)
        created = rest.create_call(payload(incident), KEY)

        with pytest.raises(CalleError) as raised:
            mcp.get_call_run(created.id)

        assert raised.value.code == "no_call_run"


def test_a_bad_api_key_is_reported_as_unauthorized(incident):
    with serving(scenarios.answer_ack(ALICE.name, "alice")) as server:
        rest = RestClient(server.base_url, "", timeout=5)

        with pytest.raises(CalleError) as raised:
            rest.create_call(payload(incident), KEY)

        assert raised.value.status == 401
        assert not raised.value.ambiguous
