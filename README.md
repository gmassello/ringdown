# Ringdown

An on-call escalation agent that phones the person holding the pager, and **proves** the
acknowledgement happened.

Every on-call system reports "notification sent" and treats the incident as escalated. That
proves nothing: the push arrived at a phone on silent, the email landed in a folder, the SMS was
half-read at 03:00 and the engineer went back to sleep. The acknowledgement is the only part that
matters and it is exactly the part nobody verifies.

Ringdown walks the escalation ladder one call at a time until somebody commits with an owner and
an ETA — then **places the call over the REST API and verifies it over MCP**, because an agent
that audits itself through the channel it wrote with has proved nothing.

## Sixty seconds

```bash
cd apps/python/ringdown && python -m demo.run_local
```

Seven scenarios against a fake CALL-E on `127.0.0.1`. No credentials, no network beyond loopback,
nothing rings. This is the second one:

```text
[1/3] primary  Alice Okafor  +1********00
      idempotency key rd-inc-2026-08-09-0113-primary-1-1ebde0bc3ec9
      call call_fake1  status completed  confidence 0.91 high
      not acknowledged (no_eta)  the call completed and the provider was confident,
                                 and no number of minutes was ever spoken
        disposition  unclear
        eta          absent
```

The call completed, `task_completed` is true, confidence is `high` at 0.91. A system that branches
on those three signals reports this incident as escalated and goes back to sleep. Alice said
"yeah, sure, I'll take a look at some point" — no owner, no clock, no acknowledgement. Ringdown
drops to the next rung, and the backup commits.

That one case is the whole product.

## What it proves

The provider's two surfaces are not two views of one JSON document. REST reports lowercase
statuses and exposes `task_completed` and `completion_confidence`. MCP reports uppercase statuses
and accepts no extraction schema at all. So verifying over MCP forces Ringdown to re-derive the
acknowledgement from the raw transcript, over a different transport, using none of the fields it
recorded. Ten checks on the attempt that acknowledged, one more on every attempt it escalated
past — that last one catches the opposite error, walking over somebody who did say yes.

Every recorded field has to be quoted by a span the recipient actually spoke. A span that appears
only in the agent's own turns is rejected: quoting the question is not evidence of the answer.

The verdict and its verification are appended to a hash-chained ledger, and `verify --ledger`
does something a flat append-only log cannot: it **re-derives the verdict from the recorded
attempts**. Rewrite the verdict, reseal the record and relink every record after it, and the
chain closes cleanly — and the check still fails.

## What is in here

| Path | What it is |
| --- | --- |
| [`apps/python/ringdown/`](apps/python/ringdown/) | The app. Python 3.11+, standard library only, 157 tests. Its [README](apps/python/ringdown/README.md) is the operational manual: setup, exit codes, file formats, threat model, all the ceilings. |
| [`apps/python/ringdown/demo/EXPECTED.md`](apps/python/ringdown/demo/EXPECTED.md) | The seven demo scenarios, narrated, written before the code that produces them. |
| [`docs/plan.md`](docs/plan.md) | How this was built, stage by stage, including the findings that corrected the original brief. |
| [`docs/ringdown-brief.md`](docs/ringdown-brief.md) | The original brief. |

Only the app and its skill are meant to travel to
[`CALLE-AI/awesome-phone-call-agents`](https://github.com/CALLE-AI/awesome-phone-call-agents).
This README stays here.

## The defence

**Against `deployment-approval-call`**, the nearest neighbour: it asks *before* acting — "may I do
X?" — of a known approver, and its failure is safe, because nothing happens. Ringdown asks *after*
something already broke — "will you take it?" — of a rotation that has to be resolved first, and
its failure is unsafe: nobody answers and the incident keeps running. Success is not permission,
it is a commitment with an owner and an ETA.

**Against the Zapier recipe** for the same scenario: it argues its position well — a missed page
costs far more than a duplicate one — but it pays for that insurance by waking two people whenever
the state is unknown, because it cannot reconcile. Ringdown gets the same guarantee for one phone
call by replaying a content-derived idempotency key. And it never verifies that the
acknowledgement existed, which is the point here.

**Against `verify-by-phone`**, which shares the span grounding: it makes one call to verify one
published fact, and abstains when it cannot. Ringdown runs a ladder looking for a commitment and
audits its own call over a second transport. Same technique, different product.

## Known ceilings

- Grounding compares text, not meaning. An engineer who paraphrases honestly produces a
  verification failure over a real acknowledgement. That is the acceptable direction of error —
  it costs a human review, not an unowned incident — but it is a real cost.
- A verdict of `unknown` is never verified. There may be a live call, and checks against a call
  that has not finished produce failures that are not contradictions.
- There is no way to cancel a call already in flight. What is cancellable is the ladder.
- The ladder never re-calls the same person. Adding retries would need another idempotency key
  and another record, never a silent redial.

The [app README](apps/python/ringdown/README.md#known-ceilings) has all ten, unvarnished.

This is a demo app for a workflow pattern, not a CALL-E SDK and not a supported
product API.
