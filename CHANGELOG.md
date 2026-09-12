# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Both packages are versioned together at `0.1.0`.

## [Unreleased]

### Fixed

- The app README claimed 378 tests; there are 393 (plus 19 in the receiver).
- `tests/fixtures/README.md` described the 2026-08-20 live run as three calls with two REST
  creates. It was six calls — five over REST, one over MCP — with five creates and five replays,
  which is what the root README and ceilings 12 and 16 already said.

### Added

- `CONTRIBUTING.md` and this changelog.
- A `LICENSE` inside `apps/python/ringdown/`, so the package that travels upstream carries one.
- A table of contents, a `## License` section, and `git clone` / `cd` instructions in the app
  README, whose Setup section now comes before the demo rather than after it.

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
