# What the provider actually sent

Responses observed against the live CALL-E API and MCP endpoint, committed verbatim. They exist
because the client and the fake in `fake/` were both written from the same reading of the same
documentation on the same day, so a mistake in that reading lands in both and the tests cannot
see it. That already happened once: the payload sent `recipient` where the API takes
`recipients: [{phones: []}]`, and the fake accepted both.

These files are the third artefact. `tests/golden/` holds ledgers this app wrote; this directory
holds what somebody else sent us. Tests read them directly, without the fake, so the parser is
checked against evidence rather than against a mirror.

Every fixture carries its own provenance:

- `what` — the request it answers
- `source` — where it was transcribed from, and when it was observed
- `unobserved` — what is **not** evidence: the parts elided, assumed, or never captured
- `why_it_matters` — the failure it pins down
- `payload` — the literal body

Read `unobserved` before trusting a fixture. The evidence is partial and the gaps are the point.

## The gap

**No successful response has ever been observed.** Not from `get_call_run`, not from
`POST /v1/calls`, not from `GET /v1/calls/{id}`. No call has been placed against the live
provider — the account cannot dial the region the on-call engineer is in (ceiling 14), so the
happy path is documented by the provider and reproduced by our fake, and confirmed by neither.

Which means the shape `run_from` and `snapshot_from` parse on the happy path is a reading of the
docs, not a record of a reply. What is defended instead is the degradation: a response the parser
cannot read is reported as unresolved rather than as a contradiction, whatever shape it arrives
in. See ceiling 12.

Adding a fixture from a real call is the single highest-value thing anyone with a dialable number
can do for this repo.
