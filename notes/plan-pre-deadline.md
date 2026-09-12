# Ringdown — pre-deadline plan

Hackathon deadline: **14 September 2026, 23:45 SGT** (check the conversion to your own timezone
before starting — SGT is UTC+8).

This document merges two plans that used to live apart: the injection hardening of the core, and the
three-day sprint meant to close the four gaps identified against the competing entries. The
hardening goes first, as **Day 0**: it is the smallest change and it touches the module every other
day builds on.

---

## 0. Context

- **The hackathon submission is already settled.** PR
  [`#205`](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/205) to
  `CALLE-AI/awesome-phone-call-agents` was **merged on 2026-08-25** (commit `257ed6f`), and the
  Devpost rules only ask for that PR's URL — they do not even require it to be merged. Nothing here
  needs to touch that repository again.
- Once a PR is merged, GitHub copies the files exactly as they were that day into the target repo's
  `main`. No live link remains between that copy and this repository (`gmassello/ringdown`).
  Everything done here **cannot break or affect** what landed in PR #205 — it is a frozen snapshot.
  No special care is needed on that account.
- Devpost's "URL to a working demo" field is **optional**, and that is where the link to this
  improved repository goes once it is ready. It does not depend on touching the shared repo again.
- Operational conclusion: all the work below happens in `gmassello/ringdown`, against its own `main`,
  with no further interaction with `CALLE-AI/awesome-phone-call-agents` and no mirroring to the fork
  checkout.

---

## 1. What already exists — read this before executing any day

The sprint below was written against an older reading of the repository. Four features were
proposed; two are already built and a third is largely built. Each day has been rewritten
accordingly, but the underlying facts are worth having in one place:

| What the original plan proposed | What is in the repository today |
|---|---|
| Build an inbound alert adapter | **Already built and tested.** `ringdown/adapter.py` resolves paths like `$.alerts[0].labels.severity` (dotted keys and integer indices, no `eval`, no vendor regex; an unresolved path omits the key rather than inventing a value). Exposed as the `adapt` CLI subcommand, with `examples/alertmanager.example.json` and `examples/field-mapping.example.json`, documented at `apps/python/ringdown/README.md:210-222`. It is **generic on purpose**: `docs/plan.md:397` puts integration with any concrete vendor out of scope precisely because the adapter does not need to know one |
| A `POST /webhooks/pagerduty` endpoint | **Conflicts with known ceiling 3** — *no webhooks, because they are not signed*. That is a written decision, not an oversight |
| Build a dashboard showing the ledger, REST vs. MCP verification and the hash chain | **Two surfaces already do this.** The `docs/` site (`ledger.js` ports `audit.chain_checks` to JS — canonical JSON, SHA-256 via `crypto.subtle`, chain checks and tamper; `app.js` renders the records with truncated hashes, the REST/MCP/LEDGER columns and an interactive tamper button) and the `/calls` dashboard in `calle-receiver`. A third dashboard inside `apps/python/ringdown/` would duplicate the first and break the zero-dependency rule |
| Move the ladder out of hardcoding into a config file | **It has been file-driven from day one.** `ladder` is a required field of the incident file and scopes are free strings (`incident.py:196-200`, `resolve_ladder` at `incident.py:261-279`). What is actually coupled to the on-call domain is narrower: `severity` restricted to `sev1\|sev2\|sev3`, the required `service` / `runbook_url` fields, and the spoken script in `fake/scenarios.py` |
| "313+ tests", and the hardening plan's claim that the badge is wrong | **Both numbers are correct today**: 298 (ringdown) + 19 (receiver) = 317, and the root README badge reads 317. That correction task is dropped |

The only genuinely new surface among the four is the **generative-AI narration**: there is not a
single LLM call anywhere in the repository, and `report.py` produces deterministic template prose,
not generated text.

---

## 2. Non-negotiable constraints

These are exactly what wins against the entries analysed. Any task below that puts them at risk gets
trimmed or postponed — trading a won differentiator for a half-finished new one is not worth it:

1. **Zero external dependencies** in the core (`apps/python/ringdown/`). Anything new goes in a
   separate, optional module that can be left uninstalled without breaking a thing.
2. **The verdict is still decided by REST+MCP cross-verification**, never by an LLM. Any generative
   AI added is *narration*, not *decision*.
3. **Nothing places a real call without `--confirm 'place real calls'`.** Every new demo surface
   starts in preview/dry-run mode by default.
4. **The hash-chained ledger stays the source of truth.** Everything new (dashboard, integrations,
   AI) READS from the ledger; nothing replaces or bypasses it.
5. **The demo output does not change.** `demo/EXPECTED.md` and `examples/ledger.example.jsonl` stay
   byte-identical, because the README video depends on them. `tests/test_demo.py` enforces this on
   its own — if either file shows up modified, the change leaked into the demo output and must be
   fixed, not regenerated.

---

## 3. Git strategy

`gmassello/ringdown` has no branch protection on `main`, and with three days left the formal
circuit (a branch per task, a PR against your own `main`, a merge every morning) buys less than it
costs.

- **Before starting:** tag the current commit as a safe point — `git tag pre-hackathon-sprint` — so
  there is always somewhere to fall back to.
- **Work directly on `main`.** No feature branches, no self-reviewed PRs.
- **Done criteria, applied per commit instead of per merge** — non-negotiable:
  - the full suite green;
  - preview mode still the default on every new surface;
  - `EXPECTED.md` and `examples/ledger.example.jsonl` unchanged;
  - **the README and any affected documentation updated in the same commit as the change.** This is
    what replaces reading the diff in a PR.
- **If something runs late** (the AI narration, lowest priority, is the likely candidate), it is
  simply left undone — a small stable `main` beats a complete broken one.
- **Final cushion:** if you would rather not depend on the last commit of `main`, point the demo
  link (the optional Devpost field) at a specific tag instead of `main` HEAD.

---

## 4. Priorities

| Priority | Gap it closes | Effort | Why it goes first / last |
|---|---|---|---|
| 1 | Injection defence is real but not solid or proven | Low | Best impact-to-effort ratio left. The defence exists and is unique in the field, but one exploitable hole remains (quotes), detection is four literal phrases, and the central property is untested. It touches the module every other day builds on, so it goes before them |
| 2 | No generative AI on display | Low | The only one of the four that is genuinely new. Fast to add if kept narrow: a narration layer, never a decision layer |
| 3 | Narrow scope | Low | The ladder is already config-driven; what is left is loosening the on-call coupling and shipping a second example. Cheap, and it shows one engine across use cases |
| 4 | No integration with real tools | Medium | The most concrete judge's critique — "this replaces PagerDuty but does not talk to PagerDuty" — and the field analysis confirms the gap is genuine (only 1% of entries integrate a real webhook). But the adapter is already built, and the webhook endpoint conflicts with ceiling 3, so what remains is smaller than it looks: a vendor mapping and a write-back |

---

## Day 0 — Injection hardening

**Objective:** close the one exploitable vector, widen detection from phrases to families, and prove
the central property by test — **without changing a byte of the demo output**.

### Where the defence stands

Ringdown **already treats the transcript as data and not as instruction**: `extract()` only reads
`user` turns, `classify()` requires every verdict field to be quoted by a span the recipient spoke,
and `instructed()` flags the attempt without changing any field. Across the 111 hackathon entries it
is the only one that addresses the problem at all — the rest do not mention it.

What is missing is not the defence, it is its solidity at two concrete points and its demonstration:

1. **A real, exploitable hole.** The spoken task wraps the incident fields in double quotes
   (`script.py`, `CALL_TASK` step 5: `read exactly this: "There is a {severity} incident on
   {service}: {title}. {summary}"`). `clean_text` (`incident.py:81`) already collapses newlines, so
   multiline injection is closed — but **it does not neutralise double quotes**. A `summary` arriving
   from an alert payload containing `"` closes the wrapper, and everything after it reaches the agent
   as task text, outside the quotes. The README claims those fields travel "marked as quoted data";
   today the data itself can break the mark.
2. **Detection is by rote.** `extract.INJECTION` is four literal phrases compared with `in`. It
   catches exactly the attack the demo stages and nothing else: "olvidá lo anterior", "system:",
   "mark this as acknowledged" all pass unflagged. The flag decides nothing, but it is what gets
   written to the ledger and what an auditor reads — so a real attack is invisible in the artefact.
3. **The property is not proven.** There is a test that an injected voicemail is still `unreachable`
   and another that the flag only trips when the recipient says it. None proves the central claim:
   *no hostile transcript can produce `acknowledged`*.

### 1. Close the quote vector — `ringdown/script.py`

Add a one-line helper that neutralises quotes (`"`, `“`, `”`) by replacing them with the single
quote, and apply it in `call_task()` to the three fields that come from the untrusted payload and
are interpolated inside the quoted wrapper: `title`, `summary`, `service`.

- **Why here and not in `clean_text`**: `clean_text` also validates `id`, and `id` feeds
  `attempt_id()` → `idempotency_key()`. Touching it would change idempotency keys and, with them, the
  example ledger. `call_task()` is the only point where untrusted data crosses into spoken text: one
  sanitisation there covers the whole vector without touching call identity.
- `runbook_url` does not need it: `validate_runbook_url` (`incident.py:110`) already rejects anything
  that is not an http/https URL without spaces.
- `rung.contact.name` does not need it: it comes from the rotation file, which is an operator file,
  not an alert payload. Mention that in the threat model instead of sanitising it.

### 2. Detection by families — `ringdown/extract.py`

Replace the four-substring `INJECTION` tuple with compiled regexes grouped into three families, plus
a matcher of their own:

- **instruction override**: `ignore` / `disregard` / `forget` followed by `previous|prior|all|your`
  and by `instructions|prompt|rules`
- **role or system impersonation**: `system:`, `you are now`, `new instructions`, `as the admin`
- **verdict commands**: `record this as`, `mark this as`, `log this as`, `set the verdict`,
  `set the eta`

Constraints:

- **Do not touch `_first_matching`**: it is shared by `VOICEMAIL`, `WRONG_PERSON`, `DECLINE` and
  `ACKNOWLEDGE`, which stay substring comparisons. Add a separate matcher for the regexes and have
  `instructed()` use it. SRP: one matcher per kind of pattern.
- The regex must require the **combination** instruction + object, never the bare verb: an engineer
  saying "ignore the previous alert, this is the real one" must not be flagged.
- The fake's scenario (`fake/scenarios.py`) must keep yielding `instructed=True`, or the demo output
  changes and `test_demo.py` fails. It is the canary for this change.

### 3. Property tests

- **`tests/test_dispositions.py`** — the central test, parametrised over a corpus of hostile
  transcripts, asserting `classify(...).verdict != "acknowledged"` for all of them: injection asking
  for the acknowledgement with no owner and no ETA; injection supplying owner and ETA in the
  attacker's turn but with a name that is not the contact's; injection on top of a voicemail;
  injection pretending to declare `task_completed` or to raise confidence (those come from the
  snapshot, not the transcript, and the test makes that explicit).
- **`tests/test_extract.py`** — that each new family is flagged when the recipient says it and not
  when the bot does, and that the control phrase ("ignore the previous alert") is not flagged.
- **`tests/test_script.py`** — that an incident carrying double quotes in `title`, `summary` and
  `service` produces a task whose interpolated fields contribute no quotes, i.e. the quoted-data
  wrapper stays closed.

Reuse the helpers that already exist: `said()` in `tests/test_extract.py`, `an_incident()` in
`tests/data.py`, and the fixtures in `tests/conftest.py`.

### 4. Documentation

- **`apps/python/ringdown/README.md`**, *Threat model*: it currently says the incident fields are
  "length-limited and validated". Add that quotes are neutralised when formatting the task, and why
  — the quoted wrapper is the defence, and data able to close it voids it. Name the rotation file as
  an operator file that does not share that status.
- **`apps/python/ringdown/README.md`**, *Known ceilings*: state plainly that `instructed` is an
  English-language heuristic over known families and not a classifier — the real defence is
  structural (every verdict field comes from deterministic rules over recipient turns), and the flag
  is evidence for the auditor, not a control. This is the answer to "what if the injection is not on
  your list?".
- Root **`README.md`**: the "The transcript is data, never instruction" bullet gains a mention that
  the incoming incident is data too.

No new dependencies: `re` is already imported in both `script.py` and `extract.py`.

### Manual check of the closed vector

Build an incident whose `summary` contains `"` followed by an order, render the task, and confirm
the order stays inside the quotes instead of escaping them. Run it before and after the change.

### Task brief — Day 0

> Work in `apps/python/ringdown/`, committing directly to `main`. Harden the injection defence in
> two places and prove it with tests. First: in `script.py`, neutralise double quotes in the
> `title`, `summary` and `service` fields at the point where `call_task()` interpolates them into
> the quoted wrapper — not in `clean_text`, because that also validates `id` and would move the
> idempotency keys and the example ledger with them. Second: in `extract.py`, replace the four
> literal `INJECTION` substrings with compiled regexes covering three families (instruction
> override, role/system impersonation, verdict commands), matched by a new matcher of their own —
> leave `_first_matching` alone, it is shared with the disposition patterns. Each regex must require
> instruction + object together, so "ignore the previous alert" stays unflagged. Then add the tests
> named in this plan, including the parametrised corpus proving no hostile transcript can reach
> `acknowledged`. The whole change must leave `demo/EXPECTED.md` and `examples/ledger.example.jsonl`
> byte-identical — `git diff --stat` is the completion gate. Update the threat model and known
> ceilings in the same commit.

---

## Day 1 — Alert adapter: vendor mapping and write-back

**Objective:** an incident raised in a real alerting tool can start the Ringdown ladder, and the
result (a verified ack) can be reported back. Scope limited to ingestion + reporting, not full
two-way sync.

**Starting point, corrected:** the adapter is already built (`ringdown/adapter.py`, the `adapt`
subcommand, the Alertmanager example). What is missing is a worked mapping for a named vendor and the
write-back leg.

Tasks:

- [ ] Add a second field-mapping example for a named vendor (PagerDuty `incident.triggered` or
      Opsgenie `alert.create` — the schemas are public) next to
      `examples/field-mapping.example.json`, mapping that payload onto the incident fields Ringdown
      already requires. **No vendor code**: the adapter stays generic, the vendor knowledge lives in
      the mapping file. Cite the official schema doc in the example.
- [ ] Offline tests with a fixture of the real payload taken from public documentation, never
      hitting the network — the same pattern used everywhere else in the project.
- [ ] Write-back: once the verdict settles (cross-channel verified), a simple `POST` to the vendor's
      "add note" / "resolve" endpoint with the result. Optional if time is short — document it as
      roadmap if it does not land.
- [ ] **The `POST /webhooks/...` endpoint is not built.** It contradicts known ceiling 3 (no
      webhooks, because they are not signed). Record the decision in the README next to that ceiling:
      the adapter reads a payload the operator hands it, and accepting one over the network needs
      signature verification that does not exist yet.
- [ ] Update the README's integration section with an end-to-end example in preview mode, in the
      same commit.

### Task brief — Day 1

> Work in `apps/python/ringdown/`, committing directly to `main`. The inbound adapter already exists
> — `ringdown/adapter.py` plus the `adapt` CLI subcommand and the Alertmanager example — so do not
> rebuild it. Add a worked field mapping for one named vendor (PagerDuty or Opsgenie) as a second
> example file, with an offline fixture of the real payload from their public docs, and tests that
> never touch the network. Keep the adapter itself vendor-free: all vendor knowledge belongs in the
> mapping file. Then add the write-back leg: once the verdict has settled, post the result to the
> vendor's note/resolve endpoint, stdlib only. Do not build a webhook endpoint — it conflicts with
> known ceiling 3; instead write down next to that ceiling why an unsigned inbound webhook is still
> out of scope. Read `apps/python/ringdown/README.md` and the current threat model before writing
> code, and update the integration section of that README in the same commit.

---

## Day 2 (morning) — Make the verification visible

**Objective:** the cross-channel verification and the hash chain are the differentiator and they are
already rendered — by the `docs/` site, which replays three scenarios step by step, shows the
REST/MCP/LEDGER columns, prints the truncated chain hashes and offers an interactive tamper button.
The gap is not rendering, it is that a judge may never find it.

**Do not build a third dashboard.** A stdlib HTTP server inside `apps/python/ringdown/` would
duplicate `docs/` and put a web surface inside a package whose whole claim is that it has no runtime
dependencies.

Tasks:

- [ ] Surface the site from the README: a link near the top that says what it shows in one line, so
      the path from "repo opened" to "cross-verification seen" is one click.
- [ ] Review the site against fresh eyes: does the REST vs. MCP comparison read as *two transports,
      one verdict* within ten seconds, or does it need a caption? Fix the wording, not the
      architecture.
- [ ] Check the tamper demo still works against the committed `docs/ledger.example.jsonl`, and that
      that file still matches `examples/ledger.example.jsonl` byte for byte (`tests/test_demo.py`
      asserts it).
- [ ] The receiver dashboard at `/calls` stays as it is — it shows real inbound calls, which is a
      different claim from the ledger and should not be merged into it.

### Task brief — Day 2 (morning)

> Committing directly to `main`. Do not build a new dashboard: the `docs/` site already renders the
> ledger with its chain hashes, the REST vs. MCP comparison and an interactive tamper check, and
> `calle-receiver` serves `/calls` for real inbound calls. The work is to make the first one findable
> and legible — link it from the README with a one-line description of what it proves, and reread the
> site's copy so that "two transports, one verdict" lands in the first ten seconds without prior
> context. Verify the tamper demo still works and that `docs/ledger.example.jsonl` is still
> byte-identical to `examples/ledger.example.jsonl`. No Python changes expected.

---

## Day 2 (afternoon) — Generative-AI narration layer — **DROPPED, 2026-09-11**

**Objective, as originally written:** add a visible generative-AI surface for the judges without
touching the deterministic decision path — an optional `apps/python/ringdown/narration/` module that
turns a settled verdict into a natural-language summary.

**Not built, and not because it ran late.** Two things changed between writing this plan and
reaching this day:

- **Day 1 already produces the artefact this was for.** `pagerduty.note_text` writes prose a human
  reads on the incident: who was called, what they committed to, the exact phrases they spoke, the
  settled exit code and the ledger head. It is deterministic, it quotes only grounded spans, and it
  is testable without a network. A model narrating the same facts would add an API key, a failure
  mode and a source of drift to restate what is already stated.
- **It argues against the product.** The pitch is that the verdict comes from deterministic rules
  over what the recipient actually said, cross-checked on a second transport, and that nothing here
  depends on a model being right. Bolting on a model — even one that decides nothing — invites the
  question the whole design exists to foreclose. The honest answer to "where is the generative AI?"
  is that the agent on the phone is the model, and everything downstream of it is deliberately not.

The decision is recorded in `apps/python/ringdown/README.md` so it reads as a choice rather than an
omission. Nothing else in this plan depended on it.

## Day 3 — Widen the scope without rewriting the core, and final polish

**Objective:** show the Ringdown engine (ladder + cross-verification + ledger) serves more than one
use case, without writing a second application.

**Starting point, corrected:** the ladder is already declared in the incident file and its scopes are
free strings, so a non-on-call ladder runs today by renaming scopes in two files. The actual coupling
to the on-call domain is narrower and that is what this day addresses.

Tasks:

- [ ] Loosen the real coupling: `severity` restricted to `sev1|sev2|sev3`, the required `service` and
      `runbook_url` fields, and the spoken script in `fake/scenarios.py`. Decide per field whether to
      generalise it or to document it as domain-specific — generalising `severity` changes validation
      and therefore needs its own tests.
- [ ] Ship a second configuration example in `examples/` that runs on the same binary — an
      appointment confirmation, or an SLA breach notice to a supplier — so the demo reads as *one
      engine, several use cases* rather than one fixed ladder.
- [ ] **Do not add a scenario to `demo/run_local.py`.** The demo output is frozen (constraint 5): the
      second example is documented and runnable, not wired into the recorded demo.
- [ ] Update the README and *Known ceilings* with whatever actually shipped (vendor mapping,
      narration, second scenario) and remove from the ceilings only what genuinely got solved.
- [ ] Run both suites, confirm preview mode is still the default on every new surface.

### Ceilings this sprint touches

Day 0 **adds** a ceiling (the `instructed` heuristic); Day 3 **removes** whichever ones got solved.
That is not a contradiction — both edits land in the same list. The ceilings the sprint runs into
head-on, and which should be reread before each day rather than quietly contradicted:

- **3** — no webhooks, because they are not signed (Day 1).
- **7** — re-escalation on an expired ETA is documented, not implemented; it belongs to the host
  scheduler (Day 1 write-back).
- **13** — the two channels share no credentials and only one can be automated; MCP is OAuth+PKCE
  with an interactive token that expires (any scheduled integration).
- **10** — disposition and ETA extraction is English-only (Day 0's new regex families inherit this,
  and Day 3's second scenario is bounded by it).

### Task brief — Day 3

> Committing directly to `main`. The ladder is already config-driven — `ladder` is a required field
> of the incident file and scopes are free strings — so do not "extract it from hardcoding". What is
> actually coupled to on-call is `severity` (restricted to sev1/sev2/sev3), the required `service`
> and `runbook_url` fields, and the spoken script in the fake. Decide per field whether to generalise
> or to document as domain-specific, with tests for whatever validation changes. Ship a second
> configuration example under `examples/` that runs on the same binary, such as an appointment
> confirmation with double verification. Do not add a scenario to the recorded demo: `EXPECTED.md`
> and the example ledger must stay byte-identical. Then update the README and the known-ceilings
> list — adding the one about the injection heuristic, removing only what genuinely shipped — and run
> both suites to confirm nothing broke and preview mode is still the default everywhere.

---

## Final checklist

- [ ] Nothing new places a real call without `--confirm 'place real calls'`.
- [ ] `demo/EXPECTED.md` and `examples/ledger.example.jsonl` are byte-identical to what they were
      before the sprint, and `docs/ledger.example.jsonl` still matches the latter.
- [ ] The README mentions what actually shipped: the vendor mapping, the link to the site, the AI
      narration with its informational disclaimer, and the second scenario.
- [ ] Known ceilings updated in both directions — the injection heuristic added, anything genuinely
      solved removed.
- [ ] The pitch makes explicit that the differentiator is still the cross-verification and the
      ledger — the site and the AI exist to SHOW it, not to replace it.
- [ ] `main` runs clean with the full suite green, and every commit carried its own documentation
      update.
- [ ] The optional working-demo field updated at
      `devpost.com/submit-to/30579-call-e-your-code-is-calling` (PR #205 in the shared repo is not
      touched — it is already settled).
