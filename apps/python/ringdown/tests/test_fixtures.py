from __future__ import annotations

import json
from pathlib import Path

import pytest

from ringdown.calls import run_from

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DOCUMENTED = sorted(FIXTURES.glob("*.json"))


def payload_of(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())["payload"]


@pytest.mark.parametrize("path", DOCUMENTED, ids=lambda path: path.stem)
def test_every_captured_response_says_where_it_came_from_and_what_it_does_not_prove(path):
    fixture = json.loads(path.read_text())

    assert set(fixture) == {"what", "source", "unobserved", "why_it_matters", "payload"}
    assert "observed" in fixture["source"]


def test_the_parser_does_not_mistake_the_providers_missing_run_for_a_run():
    run = run_from(payload_of("mcp-get-call-run-missing.json"))

    assert not run.readable
    assert run.turns == ()


def test_a_run_that_carries_a_call_id_is_readable():
    assert run_from({"call_id": "call_abc", "status": "COMPLETED"}).readable


def test_a_null_the_provider_sent_is_not_read_as_the_word_none():
    run = run_from({"call_id": None, "status": None})

    assert not run.readable
    assert (run.call_id, run.status) == ("", "")
