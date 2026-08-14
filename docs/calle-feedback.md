# Feedback for the CALL-E team

Five findings from building Ringdown, an on-call escalation agent that places calls over REST and
audits them over MCP. Every item below was observed in August 2026 against the live API and the
live MCP endpoint, with a real account. Nothing here is speculative, and none of it was found by
reading the docs alone.

Ordered by how much they cost us.

---

## 1. MCP cannot read a call that REST placed

`get_call_run` takes a single required argument, `run_id`, documented as *"Run identifier returned
by `run_call`."* Its response carries the call identity inside the run:

```json
{"run_id": "...", "status": "FAILED", "message": "run_id not found.",
 "result": {"call_id": null, "call_ids": [], "transcript": null, ...}}
```

The mapping runs from run to call. Nothing runs the other way: `tools/list` exposes `plan_call`,
`run_call`, `get_call_run` and `track_ui_events`, and none of them resolves a call id to a run.

So a call created with `POST /v1/calls` — which returns `call_...` and never a run id — appears to
have no run to read. That closes off the whole category of applications that place over one
surface and verify over the other, which is exactly what an auditable agent wants: a result
confirmed through the transport that did not write it is worth much more than one confirmed
through the transport that did.

**What would fix it:** have `get_call_run` accept a call id as well as a run id, or expose the run
id on the `CallTask` object that REST already returns. Either one is small and unlocks
cross-surface verification.

## 2. The OpenAPI spec and the live API disagree about `result_schema`

`CreateCallRequest` in `calle.openapi.yaml` v0.6.0 documents `result_schema` and
`recipient_result_schema` at length, including which JSON Schema features are supported. The live
API rejects both with *"... is not supported"* — a limitation already recorded from live testing in
`skills/verify-by-phone/references/api-notes.md` in your own repository, and the Python SDK exposes
both parameters regardless.

Three sources, three different answers, and the only way to find out which one is true is to send
a call. Whichever behaviour is the intended one, the other two should say so.

## 3. Webhook deliveries are unsigned

No shared secret, no timestamp header, no signature header, and the SDK's `verify` and `unwrap`
helpers are deprecated as of 0.6.0. An unsigned delivery proves nothing about its sender, so any
application that cares about the integrity of its records has to ignore webhooks and poll — which
is what Ringdown does, at the cost of latency and request volume that the webhooks exist to avoid.

An HMAC over the raw body with a timestamp, in the shape every other provider uses, would let
integrators trust deliveries.

## 4. MCP offers no machine-to-machine grant

`https://seleven-mcp-sg.airudder.com/mcp/openagent_oauth` is an OAuth protected resource. Its
authorization server metadata advertises exactly one grant:

```json
{"issuer": "https://dashboard.heycall-e.com/mcp-auth",
 "grant_types_supported": ["authorization_code"],
 "code_challenge_methods_supported": ["S256"]}
```

`authorization_code` with PKCE means a human at a browser. There is no `client_credentials`, and
the API key that authenticates REST is refused with `invalid_token`. Any unattended
integration — a cron job, a CI check, an escalation agent that runs at 03:00 precisely because
nobody is awake — cannot use MCP at all once its interactively obtained token expires.

Accepting the existing API key as a bearer token, or adding `client_credentials`, would fix this
without changing anything else.

## 5. Which regions you serve is undiscoverable

There is no endpoint that lists supported region and language pairs. The only way to learn that a
number cannot be called is to plan a call to it and read the refusal:

> The recognized destination is Argentina in English, which is not currently supported for
> outbound calls.

Probed through `plan_call` in August 2026, which is free and does not dial:

| Accepted | Refused |
| --- | --- |
| United States, Canada, Mexico, Brazil, Singapore, Philippines, India, Australia | Argentina, Chile, Spain, United Kingdom |

The refusal is correct and the message is clear once you see it. The problem is when you see it.
An on-call rotation is loaded and validated long before anyone gets paged; a scheduling tool wants
to reject an unreachable engineer at configuration time, not at 03:00 when the incident is already
running. A `GET /v1/regions` returning the supported pairs would let integrators validate up
front.

Two smaller notes on the same surface: the refusal arrives twice, once as a useful sentence and
once as the bare string `Region is not allowed for this channel`, and it arrives as a
`clarifying_question` — a shape that invites the caller to answer, when the correct handling is to
stop.

---

## What worked well, and is worth saying

`Idempotency-Key` behaves exactly as documented: resubmitting with the same key returns the
original call instead of dialing twice. That single guarantee is what let us build reconciliation
of an ambiguous create — a 503 after the provider already accepted the call — into a design where
nobody gets woken twice. Very few voice APIs get this right, and it is the reason the honest
failure mode of this project is "we do not know", not "we called your backup at three in the
morning".

`completion_confidence` returning both a score and a label, rather than a label alone, is the
other one. The labels are coarse enough that we treat the score as the primary check — a `high`
carrying `0.05` is a real shape — and having both meant we could fail closed without guessing.
