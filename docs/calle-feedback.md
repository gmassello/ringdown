# Feedback for the CALL-E team

Five findings from building Ringdown, an on-call escalation agent that places calls over REST and
audits them over MCP. Every item below was observed in August 2026 against the live API and the
live MCP endpoint, with a real account. Nothing here is speculative, and none of it was found by
reading the docs alone.

Ordered by how much they cost us.

---

# Feedback for the CALL-E team

Eight findings from building Ringdown, an on-call escalation agent that places calls over REST and
audits them over MCP. Every item below was observed against the live API and the live MCP endpoint
with a real account, and the first four come from **six real calls placed on 2026-08-20** to a US
number that bridges to an unsupported region. Nothing here is speculative, and none of it was found
by reading the docs alone.

Ordered by how much they cost us.

---

## 1. Four calls in six were dropped, and reported as the recipient hanging up

Six calls, same destination, same task, same account, inside two hours. Four of them ended three
seconds after your own event log said `calling task status=calling`:

```
01:49:53  calling task status=calling
01:49:56  Call ended; syncing final Calling result.
01:50:08  calling task status=DECLINED
```

The attempt that comes back has `started_at` and `completed_at` in the same second, an empty
`transcript_turns`, and:

```json
{"failure_code": "call_failed",
 "failure_message": "calling task status=DECLINED (Hangup by: user)"}
```

Nobody hung up. We own the destination number on Twilio, and **Twilio has no record of any of the
four** — no inbound leg, no error code, nothing. The call never reached the destination network,
and the recipient's phone never rang.

It is not tied to a surface: a call placed over `run_call` connected between two REST failures, and
a REST call connected between two others. It is not the destination either, since the same number
answered twice in the same window.

Two problems, and the second is worse than the first. A ~60% drop rate is an availability problem
you may already know about. But reporting it as `Hangup by: user` is a **correctness** problem for
anyone building on top: an escalation agent cannot distinguish infrastructure dropping the call
from an engineer who saw the number and rejected it, and those two demand opposite responses — retry
one, never retry the other. The zero-second duration and the empty transcript are the only signals
that separate them, and neither is a documented contract. A distinct `failure_code` for "never
connected" would fix it.

## 2. MCP cannot read a call that REST placed, and now we have proof

This was in our earlier draft as a reading of the docs. It is now reproduced.

`get_call_run` documents one required argument, `run_id`, "returned by `run_call`". We had been
sending `call_id`. That is rejected — but not as a JSON-RPC error:

```json
{"result": {"content": [{"type": "text", "text":
  "2 validation errors for call[get_call_run]\nrun_id\n  Missing required argument ...\ncall_id\n  Unexpected keyword argument ..."}],
  "isError": true}}
```

HTTP 200, no `error` key, the failure inside `result.content[0].text` with `isError: true`. Any
client that checks for a JSON-RPC error envelope reads this as a successful call and gets an empty
run. That shape alone is worth fixing.

We then tried every identifier a REST-placed call exposes, as `run_id`:

| Sent as `run_id` | Answer |
| --- | --- |
| the `call_...` id from `POST /v1/calls` | `run_id not found.` |
| the attempt's `provider_call_id` | `run_id not found.` |
| the attempt id (`att_...`) | `run_id not found.` |
| the recipient id (`rcp_...`) | `run_id not found.` |

So the mapping runs from run to call and nothing runs the other way. A call placed over REST has no
run, and there is no way to obtain one. This closes off the entire category of applications that
place over one surface and verify over the other — which is exactly what an auditable agent wants,
because a result confirmed through the transport that did not write it is worth far more than one
confirmed through the transport that did.

**What would fix it:** have `get_call_run` accept a call id as well as a run id, or expose the run
id on the `CallTask` that REST already returns. Either one is small.

## 3. A run you do serve still cannot be verified against

We finally saw a successful `get_call_run`, by placing over `run_call`. It is not usable for
verification, for reasons independent of finding 2:

- `transcript` is one newline-joined string (`"[00:00:11] USER: ..."`), not structured turns. Every
  consumer has to re-parse speaker labels and timestamps out of prose, and any consumer that
  compares what was said against what was recorded has to trust that parse.
- `recipient_phone`, `completed_at` and **`metadata` are absent from the run entirely**, although
  REST echoes all three. So a run cannot answer "did this reach the person I dialled", "did it
  finish inside my escalation window", or "is this the attempt I sent" — the three questions
  verification exists to ask.

Serving on the run the same identity fields REST already returns would make the surface auditable
without changing anything else.

## 4. Creating a call takes longer than any client will wait

All five of our `POST /v1/calls` requests timed out at a 15-second client socket timeout before
answering. Every one of them had in fact created the call. The event log shows why — one create sat
between `botlab create bot.` and `calling resolve robot id.` for **four minutes and twenty-seven
seconds** before doing anything.

This is survivable only because `Idempotency-Key` works (see below), but it means the documented
happy path — send a create, read the id from the response — is not the path integrators will
actually take. Either the create should return promptly with a queued id, or the expected latency
belongs in the docs next to a recommended timeout.

## 5. The OpenAPI spec and the live API disagree about `result_schema`

`CreateCallRequest` in `calle.openapi.yaml` v0.6.0 documents `result_schema` and
`recipient_result_schema` at length, including which JSON Schema features are supported. The live
API rejects both with *"... is not supported"* — a limitation already recorded from live testing in
`skills/verify-by-phone/references/api-notes.md` in your own repository, and the Python SDK exposes
both parameters regardless.

Three sources, three different answers, and the only way to find out which one is true is to send
a call. Whichever behaviour is the intended one, the other two should say so.

## 6. Webhook deliveries are unsigned

No shared secret, no timestamp header, no signature header, and the SDK's `verify` and `unwrap`
helpers are deprecated as of 0.6.0. An unsigned delivery proves nothing about its sender, so any
application that cares about the integrity of its records has to ignore webhooks and poll — which
is what Ringdown does, at the cost of latency and request volume that the webhooks exist to avoid.

An HMAC over the raw body with a timestamp, in the shape every other provider uses, would let
integrators trust deliveries.

## 7. MCP offers no machine-to-machine grant

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

## 8. Which regions you serve is undiscoverable

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

`Idempotency-Key` behaves exactly as documented, and we can now say so from evidence rather than
from the spec. Five REST creates, five client timeouts, five replays of the same key — and five
times the original call came back instead of a second one being placed. **Nobody was dialled
twice.** That single guarantee is what turns finding 4 from a disaster into an inconvenience, and
it is why the honest failure mode of this project is "we do not know" rather than "we called your
backup at three in the morning". Very few voice APIs get this right.

`completion_confidence` returning both a score and a label, rather than a label alone, is the
other one. The labels are coarse enough that we treat the score as the primary check — a `high`
carrying `0.05` is a real shape — and having both meant we could fail closed without guessing.

One more, discovered while working around the region restriction above: **CALL-E dials VoIP
numbers.** Since Argentina is not an accepted recipient region, we bridged through a Twilio US
local number that forwards to an Argentine cell (`apps/python/calle-receiver/`), assuming a real
risk that the agent would refuse VoIP destinations for fraud prevention, as several voice platforms
do. It did not: the calls that connected completed normally, `task_completed: true`, full
conversation both ways, 82 seconds bridged end to end. This is worth a line in the docs — "are
VoIP/virtual numbers dialable?" decides whether a bridge like ours is viable at all, and today the
only way to find out is to spend a call trying.

And a last one that is a compliment in a strange shape. On one connected call your agent reported
`task_completed: true` at `0.86` `high`, with evidence reading *"The engineer acknowledged taking
the incident and gave a 15-minute working estimate."* The recipient's turn behind that reads
*"Yes. I'm banking this incident right now"* — speech recognition heard "banking" for "taking". The
summary was right about what happened and the transcript was not, which is the correct direction
for a summary to err. We mention it only because any consumer that grounds its own fields in the
transcript, as we do, will disagree with your summary on calls like that one, and should.
