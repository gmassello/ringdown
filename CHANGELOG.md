# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Both packages are versioned together at `0.1.0`.

## [Unreleased]

### Added

- **Exit code 50**, and a `LedgerError` to carry it: a ledger that cannot be opened, read or
  extended once a call has been placed is an infrastructure failure, not the operator's mistake it
  used to be reported as. Before the first call it is still 30. The run prints the verdict and the
  attempts it reached before exiting, because that output is the only surviving evidence.
- A test that runs `docs/ledger.js` and `audit.chain_checks` over the same six ledgers and compares
  every check, so the browser port cannot drift from Python unnoticed. The seals only ever caught a
  drift in the digest, never a missing family of checks. Skipped where `docs/` or `node` is absent.
- `logging` in the receiver: every path that drops a Twilio callback — an absent `CallSid`, a call
  this database does not know, a recording Twilio does not host, transcription data that will not
  parse, a signature that does not match — now says so.
- Ceiling 20, on what the browser port of the ledger checks can and cannot promise.
- `CONTRIBUTING.md` and this changelog.
- A `LICENSE` inside `apps/python/ringdown/`, so the package that travels upstream carries one.
- A table of contents, a `## License` section, and `git clone` / `cd` instructions in the app
  README, whose Setup section now comes before the demo rather than after it.

### Fixed

- A PagerDuty note whose failure text ran past 200 characters turned a verified run into exit 30
  and lost the `notified` record entirely. The limit now belongs to `post_note`, which produces the
  detail, and the note is wrapped so that no failure in it can change the exit code of a run that
  already settled — which is what ceiling 18 always said happened.
- `verify` left the exit-code contract by traceback on four shapes of ledger: a byte that is not
  UTF-8, a path that is a directory, a `verification` record whose counts are not numbers, and a
  `seq` that is not an integer. There is now one door for reading a ledger, and an unreadable file
  is a failed check and exit 40. Corrupting a record is at least as visible as rewriting one.
- The receiver derived its public URL two incompatible ways — `urljoin` for the signature,
  concatenation for the three callbacks — so a trailing slash in `PUBLIC_BASE_URL` silently lost
  recording, transcription and status, and a webhook configured with a query string failed every
  signature. One `Settings.url_for` now feeds all four, `public_base_url` is normalised and refused
  at startup if it carries a path, and the signature is checked against the path **and** the query
  Twilio signed. The validator is handed the form itself, so a repeated key no longer collapses
  into a false 403.
- `parse_turns` read any speaker label that was not literally `user` as the agent's own turn, so a
  transcript labelled `USER` or `recipient` settled the call `unreachable` — a diagnosis nobody had
  observed, written into the ledger as the reason to call back. `user` and `bot` are now read in
  any case and anything else is an `unreadable_response`.
- The browser port was missing the `notified` family of checks, disagreed with Python on a
  `verification` whose counts are not numbers, and grouped verdicts under a different key for an
  `attempt_id` of fewer than three segments.
- The site's verdict gloss claimed "Somebody acknowledged, with an owner and an ETA" over the
  published ledger, in which nobody acknowledged, and blamed the second channel for any failed
  check — including the one the tamper button is there to demonstrate. Both now describe what the
  chain actually proves.
- The site hung on "Fetching the ledger…" with its body hidden and an inert tamper button wherever
  `crypto.subtle` is unavailable — `file://`, or any origin that is not secure — because the
  `try` covered only the fetch. It now covers everything that recomputes a hash, and the hero foot
  tolerates an empty ledger and a record with no hash, which is exactly the ledger the checks exist
  to paint red.
- The app README claimed 378 tests; there are 393 (plus 19 in the receiver).
- `tests/fixtures/README.md` described the 2026-08-20 live run as three calls with two REST
  creates. It was six calls — five over REST, one over MCP — with five creates and five replays,
  which is what the root README and ceilings 12 and 16 already said.

### Changed

- The demo command is spelled the same way in the root README, the app README and `CLAUDE.md`.
- The root README's *Repository* table lists `skills/`, `video/` and `notes/`.
- The root README summarises the comparison against the three neighbouring projects and links to
  the app README instead of repeating it word for word.

## [0.1.0] — 2026-08-20

First working version, exercised against the live provider.

### Added

- **Escalation ladder.** `resolve_ladder` reads an incident and a rotation, resolves who is on
  call per scope at the current moment, and walks the rungs one at a time. A bounded shift
  relieves an open-ended one; an empty scope is skipped with a note; a person in two scopes is
  called once.
- **One call per rung, ever.** The idempotency key is derived from the call payload, so an
  ambiguous create is replayed with the same key rather than waking a second person.
- **Two transports, one verdict.** The call is placed over REST and verified over MCP. Ten checks
  run on the attempt that acknowledged, split between establishing that both surfaces describe one
  call and re-deriving the acknowledgement from the second channel's transcript.
- **Span grounding.** Every recorded field — disposition, owner, ETA — must be quoted by a span
  the recipient actually spoke. A span appearing only in the agent's turns is rejected.
- **Injection defence.** The transcript is data, never instruction: an attempt to instruct the
  agent is stored, flagged `instructed`, and changes no field. Incident fields arrive as quoted
  data and their quotes are neutralised where the task is formatted.
- **Hash-chained ledger.** `intent` before the POST, `attempt` after it settles, plus `verdict`,
  `verification` and `notified` records. `verify --ledger` relinks the chain, recomputes every
  hash, and re-derives the verdict from the recorded attempts under the schema version that wrote
  it.
- **Seven exit codes** with explicit precedence: 25 skips verification, 40 overrides 0/10/20/45,
  and 45 only lands when nothing was contradicted.
- **Trust-boundary URL pinning.** Each channel is pinned to its own exact live URL by string
  comparison, or to loopback, which is served throwaway credentials.
- **`adapt`** turns an alert payload into an incident file through a mapping, with a worked
  PagerDuty example and no vendor code.
- **`run --pagerduty-note`** writes a note — never an acknowledgement — on the PagerDuty incident.
- **Configurable call script**, refused if it drops the sentences the extractor and the injection
  defence depend on. `examples/sla-breach.example.json` runs a second use case on the same engine.
- **`calle-receiver`**, the Twilio relay that bridges CALL-E's US number to an Argentine phone,
  with recording, live transcription and a password-protected dashboard.

### Known limitations

Nineteen of them, kept deliberately in
[the app README](apps/python/ringdown/README.md#known-ceilings). The load-bearing one: cross-surface
verification does not work against the live provider, so **every live verdict settles at exit 45**.
