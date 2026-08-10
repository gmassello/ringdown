from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Literal, Mapping
from urllib.parse import urlparse

TRUSTED_HOSTS = frozenset({"api.heycall-e.com"})
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
AMBIGUOUS_STATUSES = frozenset({408, 409, 425, 429})
TERMINAL_STATUSES = frozenset({"completed", "failed", "canceled"})


class CalleError(Exception):
    def __init__(self, code: str, status: int | None, message: str, details: Any = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.status = status
        self.message = message
        self.details = details

    @property
    def ambiguous(self) -> bool:
        return self.status is None or self.status in AMBIGUOUS_STATUSES or self.status >= 500

    @property
    def retriable(self) -> bool:
        return self.ambiguous and self.status != 409


class UntrustedHost(ValueError):
    pass


@dataclass(frozen=True)
class Turn:
    speaker: Literal["bot", "user"]
    text: str
    offset_seconds: int


@dataclass(frozen=True)
class CallSnapshot:
    id: str
    status: str
    task_completed: bool | None
    confidence_score: float | None
    confidence_label: str | None
    failure_code: str | None
    completed_at: str | None
    recipient_phone: str | None
    metadata: dict[str, str]
    turns: tuple[Turn, ...]

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES


@dataclass(frozen=True)
class CallRun:
    call_id: str
    status: str
    recipient_phone: str | None
    completed_at: str | None
    metadata: dict[str, str]
    turns: tuple[Turn, ...]


def assert_trusted_base_url(url: str, allowed: frozenset[str] = frozenset()) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise UntrustedHost(f"{url!r} is not an http or https URL")
    if parsed.username or parsed.password:
        raise UntrustedHost("refusing a URL that carries credentials in its userinfo")
    if parsed.query or parsed.fragment:
        raise UntrustedHost("refusing a base URL that carries a query string or a fragment")
    host = parsed.hostname
    loopback = host in LOOPBACK_HOSTS
    if parsed.scheme == "http" and not loopback:
        raise UntrustedHost(f"refusing to send an API key over plain http to {host}")
    if not (loopback or host in TRUSTED_HOSTS or host in allowed):
        raise UntrustedHost(
            f"refusing to send an API key to {host}. Name it with --allow-host to permit it."
        )
    return url.rstrip("/")


def parse_turns(raw: Any) -> tuple[Turn, ...]:
    if not isinstance(raw, list):
        return ()
    turns = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        speaker = "user" if entry.get("speaker") == "user" else "bot"
        turns.append(
            Turn(
                speaker=speaker,
                text=str(entry.get("text", "")),
                offset_seconds=int(entry.get("offset_seconds", 0) or 0),
            )
        )
    return tuple(turns)


def snapshot_from(body: Mapping[str, Any]) -> CallSnapshot:
    recipients = body.get("recipients") or [{}]
    first = recipients[0] if isinstance(recipients[0], dict) else {}
    attempts = first.get("attempts") or [{}]
    last = attempts[-1] if isinstance(attempts[-1], dict) else {}
    confidence = body.get("completion_confidence") or {}
    label = confidence.get("label")
    return CallSnapshot(
        id=str(body.get("id", "")),
        status=str(body.get("status", "")),
        task_completed=body.get("task_completed"),
        confidence_score=confidence.get("score"),
        confidence_label=label.lower() if isinstance(label, str) else None,
        failure_code=body.get("failure_code"),
        completed_at=body.get("completed_at"),
        recipient_phone=first.get("phone"),
        metadata=dict(body.get("metadata") or {}),
        turns=parse_turns(last.get("transcript_turns")),
    )


def run_from(body: Mapping[str, Any]) -> CallRun:
    return CallRun(
        call_id=str(body.get("call_id", "")),
        status=str(body.get("status", "")),
        recipient_phone=body.get("recipient_phone"),
        completed_at=body.get("completed_at"),
        metadata=dict(body.get("metadata") or {}),
        turns=parse_turns(body.get("transcript_turns")),
    )


class _Client:
    def __init__(
        self,
        url: str,
        api_key: str,
        timeout: float = 15.0,
        allowed_hosts: frozenset[str] = frozenset(),
    ) -> None:
        self._url = assert_trusted_base_url(url, allowed_hosts)
        self._api_key = api_key
        self._timeout = timeout

    def _send(
        self,
        url: str,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method="POST" if data else "GET")
        request.add_header("Authorization", f"Bearer {self._api_key}")
        request.add_header("Content-Type", "application/json")
        for name, value in (headers or {}).items():
            request.add_header(name, value)
        try:
            with urllib.request.urlopen(request, timeout=timeout or self._timeout) as response:
                return json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            raise _http_error(error) from error
        except OSError as error:
            raise CalleError("transport_failure", None, str(error)) from error
        except json.JSONDecodeError as error:
            raise CalleError("unreadable_response", None, str(error)) from error


def _http_error(error: urllib.error.HTTPError) -> CalleError:
    try:
        body = json.loads(error.read() or b"{}")
        envelope = body.get("error", {}) if isinstance(body, dict) else {}
    except (json.JSONDecodeError, OSError):
        envelope = {}
    return CalleError(
        code=str(envelope.get("code") or f"http_{error.code}"),
        status=error.code,
        message=str(envelope.get("message") or error.reason),
        details=envelope.get("details"),
    )


class RestClient(_Client):
    def create_call(self, payload: Mapping[str, Any], key: str) -> CallSnapshot:
        return snapshot_from(
            self._send(f"{self._url}/v1/calls", payload, {"Idempotency-Key": key})
        )

    def get_call(self, call_id: str, timeout: float | None = None) -> CallSnapshot:
        return snapshot_from(self._send(f"{self._url}/v1/calls/{call_id}", timeout=timeout))

    def wait_for_result(self, call_id: str, timeout: float, interval: float) -> CallSnapshot:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            snapshot = self.get_call(call_id, timeout=max(0.001, min(self._timeout, remaining)))
            if snapshot.terminal:
                return snapshot
            if time.monotonic() >= deadline:
                raise CalleError(
                    "poll_timeout",
                    None,
                    f"call {call_id} was still {snapshot.status} after {timeout:.0f}s",
                )
            time.sleep(min(interval, max(0.0, deadline - time.monotonic())))


class McpClient(_Client):
    def get_call_run(self, call_id: str) -> CallRun:
        body = self._send(
            self._url,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "get_call_run", "arguments": {"call_id": call_id}},
            },
        )
        if not isinstance(body, dict) or "error" in body:
            envelope = body.get("error", {}) if isinstance(body, dict) else {}
            raise CalleError(
                "no_call_run", 404, str(envelope.get("message") or "the run is not readable")
            )
        return run_from(_unwrap_content(body.get("result")))


def _unwrap_content(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise CalleError("unreadable_run", None, "the run payload is not an object")
    content = result.get("content") or []
    if not content or not isinstance(content[0], dict):
        raise CalleError("unreadable_run", None, "the run payload carries no content")
    try:
        parsed = json.loads(content[0].get("text") or "")
    except json.JSONDecodeError as error:
        raise CalleError("unreadable_run", None, f"the run payload is not JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise CalleError("unreadable_run", None, "the run payload is not an object")
    return parsed
