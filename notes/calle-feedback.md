# Feedback for the CALL-E team

Eleven findings from building Ringdown, an on-call escalation agent that places calls over REST and
audits them over MCP. Every item below was observed against the live API and the live MCP endpoint
with a real account, and they come from **nine real calls**: six placed on 2026-08-20 to a US
number that bridges to an unsupported region, and three more placed to the same number on
2026-09-13 to see what had changed. Nothing here is speculative, and none of it was found
by reading the docs alone.

Findings 1 to 8 are ordered by how much they cost us. Findings 9 to 11 come from the September
session and are kept together at the end rather than renumbered into that order, so the evidence
links above keep pointing at what they always pointed at.

Six findings carry a stored response, so the shape can be read rather than taken on trust. Each one
lives in [`tests/fixtures/`](https://github.com/gmassello/ringdown/blob/main/apps/python/ringdown/tests/fixtures) with its own `what` / `source` / `unobserved` / `why_it_matters`,
and every value in them was rewritten for the repository: no real number, identifier, recording or
transcript is stored. The shape is what is evidentiary.

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
**Evidence:** [`rest-call-declined-without-dialling.json`](https://github.com/gmassello/ringdown/blob/main/apps/python/ringdown/tests/fixtures/rest-call-declined-without-dialling.json) — the whole body of the second of the two attempts that failed this way. No carrier reason is exposed anywhere in it; the zero-second duration and the empty `transcript_turns` are the only signals that separate this from a real rejection.


Two problems, and the second is worse than the first. A ~60% drop rate is an availability problem
you may already know about. But reporting it as `Hangup by: user` is a **correctness** problem for
anyone building on top: an escalation agent cannot distinguish infrastructure dropping the call
from an engineer who saw the number and rejected it, and those two demand opposite responses — retry
one, never retry the other. The zero-second duration and the empty transcript are the only signals
that separate them, and neither is a documented contract. A distinct `failure_code` for "never
connected" would fix it.

We have since built the workaround, which is how we know how thin it is. Ringdown derives the signal
itself — an attempt whose `started_at` and `completed_at` are the same second, with no transcript —
and records that call under its own reason rather than folding it into a generic failure. It is
enough to stop reporting your outage as the engineer's refusal, and it is not enough to be right: a
recipient who answers and hangs up within the same second is indistinguishable, and we are reading
two timestamps whose equality you have never documented as meaning anything. One field from you
replaces all of it.

**Re-tested on 2026-09-13: three calls, none of them dropped.** All three rang, were answered, and
ran 45 to 67 seconds end to end. We are not claiming the problem is fixed from a sample of three —
at August's rate the odds of three clean calls are about one in twenty-eight — but we are not going
to claim it is still happening when we did not see it. What the re-test does not change is the
correctness half: the payload still exposes no way to tell an infrastructure drop from a refusal, so
the ask for a distinct `failure_code` stands on the shape of the data, not on how often it fires.

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
**Evidence:** [`mcp-get-call-run-rejects-a-call-id.json`](https://github.com/gmassello/ringdown/blob/main/apps/python/ringdown/tests/fixtures/mcp-get-call-run-rejects-a-call-id.json), [`mcp-get-call-run-missing.json`](https://github.com/gmassello/ringdown/blob/main/apps/python/ringdown/tests/fixtures/mcp-get-call-run-missing.json) — the first is the whole JSON-RPC envelope of the rejection, down to the identifier quoted back inside the validation error; the second is the `run_id not found` shape, which also arrives as an HTTP 200 with no error key.


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
**Evidence:** [`mcp-get-call-run-completed.json`](https://github.com/gmassello/ringdown/blob/main/apps/python/ringdown/tests/fixtures/mcp-get-call-run-completed.json) — the first successful `get_call_run` we ever saw. It is the fixture that proves our own client wrong as well: the call id lives at `result.call_id`, not where we read it, and a known ceiling of ours records that rather than quietly correcting it.


## 4. Creating a call takes longer than any client will wait

All five of our `POST /v1/calls` requests timed out at a 15-second client socket timeout before
answering. Every one of them had in fact created the call. The event log shows why — one create sat
between `botlab create bot.` and `calling resolve robot id.` for **four minutes and twenty-seven
seconds** before doing anything.

This is survivable only because `Idempotency-Key` works (see below), but it means the documented
happy path — send a create, read the id from the response — is not the path integrators will
actually take. Either the create should return promptly with a queued id, or the expected latency
belongs in the docs next to a recommended timeout.

**Re-tested on 2026-09-13: three creates, three timeouts.** That is **eight of eight** across two
sessions three weeks apart. This is not a bad afternoon, it is the behaviour. Every one of the eight
had in fact created the call, and every one was recovered by replaying the idempotency key.

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
**Evidence:** [`mcp-authorization-server.json`](https://github.com/gmassello/ringdown/blob/main/apps/python/ringdown/tests/fixtures/mcp-authorization-server.json) — the authorization server metadata, transcribed in full. It is public discovery metadata and carries no call content.


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

## 9. The agent does not wait for an answer it was told to wait for

Step 2 of the task we send says, in these words: *"Ask, in these words: 'Am I speaking with {name}?'
Do not describe the incident until they have answered that question."* On the third call of
2026-09-13 the agent asked the question and read the incident straight through it, without a pause,
before the recipient had said anything:

```
bot   This is an automated on-call page from Ringdown,
user  Hi.
bot   and this call is recorded. Am I speaking with German Massello?
bot   There is a sev2 incident on checkout-api: checkout p99 latency above 3s.
```

The recipient reported afterwards that the opening never reached him — the first audio he heard was
the incident description. So two things went wrong at once, and only one of them is visible in the
transcript: the agent did not honour an explicit ordering constraint, and the first seconds of
outbound audio did not arrive.

For a paging agent that is the difference between a confidential incident read to the right person
and one read to whoever picked up the phone. An instruction to wait for an answer before continuing
is the whole of an identity check, and a task language that accepts such an instruction without
enforcing it is worse than one that refuses it, because the integrator believes they have a gate.
Either enforce ordering constraints in the task, or document that they are advisory so we can build
the gate ourselves.

## 10. Non-English speech comes back as English phonetics, and the call language is not selectable

On that same call the recipient answered in Spanish. This is what the transcript recorded:

| Spoken | Transcribed |
| --- | --- |
| "Sí, soy German" | `C is not a` |
| "Sí, lo tomo yo" | `C, the Thomas` |

Not a low-confidence guess and not an empty turn — confident English words, on a call your own
`completion_confidence` labelled `high` at 0.9. The agent asked twice for clarification and the
recipient gave up and switched to English, which is the only reason the call produced anything.

`CreateCallRequest` exposes no language or locale parameter, so there is no way to tell you the
recipient speaks Spanish even when the rotation says so in advance. Meanwhile `plan_call` refuses
destinations by *region and language pair* — "The recognized destination is Argentina in English,
which is not currently supported" (finding 8) — so the concept exists on your side and simply is not
reachable from create. A language on the create request, or transcript turns marked when they could
not be confidently placed in the expected language, would both work. Today the failure is silent and
reads as the recipient talking nonsense.

## 11. The agent told the recipient it recorded an acknowledgement, and the API told us it had not

The close of that same call:

```
bot   I'll record that you acknowledged taking the incident and have 16 minutes until you're working it.
bot   Bye.
```

The call came back `status: completed` with **`task_completed: false`**. We fail closed on that flag,
which is the right thing for us to do and meant the incident was correctly reported as having no
owner. But the person on the phone had been told the opposite, in your agent's own voice, and hung
up believing they were on the hook.

Whatever decides `task_completed` should also decide what the agent says at the close, or the agent
should not make claims about what was recorded. An engineer who believes they acknowledged and a
system that believes nobody did is the precise failure an escalation tool exists to prevent.

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
for a summary to err.
**Evidence:** [`rest-call-completed-without-an-acknowledgement.json`](https://github.com/gmassello/ringdown/blob/main/apps/python/ringdown/tests/fixtures/rest-call-completed-without-an-acknowledgement.json) — the body of that call, and the one place where the provider's verdict and ours are both visible side by side.
 We mention it only because any consumer that grounds its own fields in the
transcript, as we do, will disagree with your summary on calls like that one, and should.
