# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Both packages are versioned together.

## [Unreleased]

### Changed

- `docs/demo.gif` is the close of the real call instead of the ledger widget. The old one was three
  screenshots of a web page proving something true but abstract; this one is a telephone, ten
  seconds of it, ending at eighty-two seconds with an owner and a clock. The subtitles were already
  burned into the cut, so the slice carries its own narration — a GIF has no audio. It comes out of
  `video/out/demo.mp4` through the new `video/mkgif.sh`, which replaces a recipe that lived only as
  prose in `video/README.md`. 900x506, 9.9 s, 327 KB.
- The root README's caption and image description follow the GIF. The caption was the only link to
  the live ledger widget anywhere in that file, so the link moved down to the row beside the video
  and the manual rather than disappearing with the text that carried it.

## [0.2.0] — 2026-09-13

Spanish, the calls the provider ends before they ring, and the identity answer that had no
rule. Everything here was found by placing real calls: nine of them, across two sessions.

### Added

- **The identity answer may carry the name without saying "this is".** A live call on 2026-09-13
  asked "Am I speaking with German Massello?" and was answered "Hi. Yes. I am." — the ordinary
  English answer. The recipient then took the incident and gave fifteen minutes, and the attempt
  settled `not_acknowledged` with the reason `owner_not_confirmed`, because the owner table only
  read "this is {name}", "{name} speaking", "soy {name}" and "habla {name}". "I am {name}" and
  "I'm {name}" are now read too: the name comes out of the recipient's own mouth, so the grounding
  is exactly the one the other four already satisfy, and it was missing rather than excluded. The
  new phrasing is read only from the first recipient turn after the identity question, which narrows
  that pattern's reach without closing it: "yes, I'm on it." still yields an owner called `on` when
  it is itself that turn, and a test pins that rather than hiding it. Nothing hangs on the junk
  capture — the token is compared against the roster's first name, so it settles
  `owner_not_confirmed` either way. Assent with no name in it
  ("yes, I am", "speaking") still confirms nobody: the only name spoken on that call is the agent's,
  and a recorded field has to be quoted from the recipient. Ceiling 17 records both halves.

- **`zero_duration`**, a reason for the call the provider ends in the second it starts. Four of the
  six calls placed against the live API on 2026-08-20 ended that way, with nothing transcribed and
  `failure_message` reading `Hangup by: user`, while the carrier that owns the destination number
  had no record of them. `CallSnapshot` was dropping the two signals that show it, so those calls
  reached the verdict as a generic failure, indistinguishable from nobody answering — and a ladder
  exhausted that way reported that the incident had no owner, when no telephone had rung. The
  snapshot now carries the attempt's measured `duration_seconds` — the evidence rather than a
  conclusion drawn from it, and `None` where the provider gives no timestamps to measure — the
  reason is recorded per attempt whatever status the provider puts on the call, and the run says how
  many of its calls ended that way beside the verdict, so a mixed ladder is as legible as one that
  failed all the way down. No verdict, exit code or ledger schema moves. Ceiling 16 rewritten around what the shape does and does not prove.
- **Spanish.** The extractor's phrase tables carry Spanish beside English — commitments, declines,
  qualifiers, callbacks, voicemail greetings, wrong-number answers, the two questions a call script
  has to ask, spoken numbers, and the three injection families. `normalise` now folds accents, so
  `José` and `Muñoz` confirm an owner where they used to be read as `jos` and `mu`. There is no
  language flag: a real call code-switches, and the language is not known until somebody answers.
  The gates do not soften — *"creo que lo tomo yo, si puedo"* is a commitment with a condition and
  settles `not_acknowledged`, exactly as its English twin does. `examples/guardia.script.txt` is a
  call script in Spanish, which `validate_task_template` used to refuse outright, and scenario 8 of
  the demo runs the ladder in Spanish end to end. One collision the fold creates is recorded rather
  than papered over: `sí` and `si` fold to the same string, so a conditional "si puedo" cannot be
  told from an affirmative "sí puedo", and the conditional is accepted rather than risk escalating
  past a firm commitment. Ceilings 10 and 17 rewritten around what two
  languages do and do not buy.
- A ledger whose spans were spoken in Spanish, as the seventh shape `tests/test_site_port.py`
  replays through `docs/ledger.js`. Python escapes non-ASCII to `\uXXXX` and the browser port
  replicates that escape, but nothing proved the two agreed until now.
- `.github/workflows/keepalive.yml`, which rings the receiver's `/health` every five minutes. The
  free tier sleeps after 15 minutes idle and takes ~22s to wake, so a visitor arriving cold could
  not tell the service from a dead one. It covers a visitor, not an incoming call: GitHub delays
  scheduled runs, and Twilio times its webhook out at 15s, so the manual wake before anything that
  dials stays mandatory.
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
- An index on `Call.started_at` in the receiver, which is the only column the dashboard orders by,
  and a per-call cap on the transcript segments a card renders. A card that truncates says so.
- A visible legend under each ladder on the site, explaining every state it uses.
- An *In plain words* section, first thing in the root README, and a *What Ringdown does* card at
  the top of `#ledger`, `#run` and `#receiver` on the site: what the system does, in language that
  assumes no on-call vocabulary. The site shows one view at a time, so a deep link to any of the
  three — `#ledger` is the one this README hands out — used to open on a heading like "The chain
  closes cleanly. The check still fails." with no context at all, and with no way back to the
  overview. The card lives once in the markup and `placePrimer` clones it into the other two, so
  the text has one home; it carries the first link back to `#overview` those views have had.
- `CONTRIBUTING.md` and this changelog.
- A `LICENSE` inside `apps/python/ringdown/`, so the package that travels upstream carries one.
- A table of contents, a `## License` section, and `git clone` / `cd` instructions in the app
  README, whose Setup section now comes before the demo rather than after it.

### Fixed

- The site's receiver page offered exactly one link, the password-gated `/calls`, so a visitor
  waited out a cold start and then met a login box. It now points at the open `/demo` first, the way
  the root README already did, and keeps `/calls` described as what it is. The card's header also
  claimed to refresh every five seconds; it is a static reproduction of one, and now says so.
- The receiver's `/demo` page inherited the dashboard's header, so the sample call was titled
  "Calls", announced that it refreshed every five seconds, and reloaded itself on a timer to
  re-render constants that are hardcoded in Python. The header is now built per page, and only the
  dashboard claims to refresh.
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
- `validate_task_template` accepted a call script that could not be rendered. `Formatter().parse`
  reports a format spec and a conversion alongside each field name, and only the name was being
  read, so `{}` reached `str.format` as an `IndexError`, `{name:{severity}}` as a `ValueError`,
  `{name:{customer_email}}` slipped a field past the allowlist entirely, `{summary!r}` undid the
  quote neutralisation that marks incident text as data, and `{summary:>999999999}` turned a 4 KB
  script into a gigabyte of task. None of those was a `TaskError`, so the CLI left its own exit-code
  contract by traceback. A placeholder now has to be a bare field name.
- The site left the keyboard focus on the nav link when a view changed, and the jump to the
  fragment never happened at all — the browser looks for the target while it is still `hidden`, so
  there is nothing to scroll to and it does not look again. The revealed section now takes the
  focus, except on a plain visit to the front page, which keeps its own.
- The seven explanations of the ladder states lived only in a `title` attribute on elements nobody
  can focus, which means they did not exist for a keyboard, and did not exist at all on a phone.
  They are written under each ladder now. The verdict gloss and the `instructed` chip had the same
  problem and carry an accessible name as well.
- The app README claimed 378 tests; there are 393 (plus 19 in the receiver).
- `tests/fixtures/README.md` described the 2026-08-20 live run as three calls with two REST
  creates. It was six calls — five over REST, one over MCP — with five creates and five replays,
  which is what the root README and ceilings 12 and 16 already said.

### Changed

- The demo command is spelled the same way in the root README, the app README and `CLAUDE.md`.
- The root README's *Repository* table lists `skills/`, `video/` and `notes/`.
- The root README summarises the comparison against the three neighbouring projects and links to
  the app README instead of repeating it word for word.
- `docs/demo.gif` is the ledger check instead of three screens of terminal output. The old one held
  ninety lines of monospace at the width GitHub renders it, and the line that carried the point was
  the twenty-sixth of twenty-six identical ones. The new one is the site's `#ledger` panel, where
  the same checks are grouped into five: the verdict is rewritten, the chain is resealed, every
  link, seal and position still passes, and `exit 0` becomes `exit 40`. A caption under it says so
  and links to the live widget, so the row of links no longer has to. 532 KB became 58 KB.

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
