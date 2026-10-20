# Improvements after CALL-E

CALL-E closed on 14 September 2026 with **4 winners out of 452 entries**. Ringdown was not one of
them. Nothing below is applied: it is the backlog for a next iteration.

Two things we believed on the last day turned out to be wrong, and both are worth recording before
the rest. **PR #512 was merged** — 14 September at 08:26 UTC, about seven hours before the deadline,
and a maintainer pushed two commits of their own onto it. And it would not have mattered either way:
**RingBack won an Honorable Mention with its own PR still open today**. The merge was never the
differentiator.

## What the winners had in common

| Project | What it does | Stack | Prize |
|---|---|---|---|
| [Local atlas with 1st party FAQs](https://devpost.com/software/local-atlas-with-1st-party-faqs) | A local guide that mostly avoids calling: one call's answer is dated, quoted and served to everyone who asks next | express.js, gemini, supabase, redis, PWA | Most Practical — $4,000 |
| [Conversation-Clarify](https://devpost.com/software/conversation-clarify) | Spots the Gmail reply that answers nothing, makes one bounded call, writes the answer back into the thread | python, chrome extension, gmail | Most Innovative — $3,000 |
| [Care Call AI](https://devpost.com/software/care-call-ai) | Charity outreach to people at home with severe illness; the coordinator keeps safety, approval and fulfilment | next.js, react, typescript, python, docker | Honorable Mention — $1,000 |
| [RingBack](https://devpost.com/software/ringback-sumnr6) | Refills a cancelled appointment by calling the waiting list one at a time; the first yes stops the cascade | python, standard library, unittest, sqlite, http.server | Honorable Mention — $1,000 |

Patterns that repeat across the winners:

1. **A screen you can operate, not a page you can read.** 3 of 4 ship an interface — a 3-step
   wizard and a planner (RingBack), a dashboard with an approval screen and printable orders
   (Care Call AI), a PWA with a map and 14 question templates (Local atlas). Ringdown ships a static
   replay site. RingBack's README says wizard/screen/panel 33 times; our root README says it once.
2. **The restraint is the pitch.** 2 of 4 name what they cut and why — RingBack dropped three
   campaign kinds for failing the test that an answer must have somewhere to land; Local atlas
   inverted its own product into "a system for not calling" because a hundred calls to one café is
   "a denial-of-service attack on a small business, delivered politely".
3. **A human presses the button, and they say so.** 3 of 4 state it in the submission text.
   Care Call AI enforces it in the server: four confirmations plus the literal phrase
   `EXECUTE LIVE CALLS`, plus an env flag, with a default batch of 1.
4. **The submission is illustrated.** All four carry 10–14 screenshots. Ringdown carries 4.
5. **Nobody quantified anything.** Not one of the four puts a number on money or time saved —
   no calls placed, no reuse rate, no cost avoided. The criterion with the weakest field.

## Where Ringdown stands

Devpost page against the 4 winners:

| Signal | Ringdown | Winners' median | Percentile |
|---|---|---|---|
| Words in the description | **1899** | 1749 | 75 |
| Screenshots | **2** | 6 | **0** |
| Tags "Built With" | **8** | 11 | 25 |
| Demo video | yes | 4/4 | — |
| Public repo | yes | 3/4 | — |

Coverage of the judging criteria ([`judging.tsv`](judging.tsv) — four criteria, equally weighted at
25 each, from the event's own `/rules`):

| Signal | Ringdown | Winners |
|---|---|---|
| Names a concrete trade or population | yes | 75% |
| Puts a figure on money or time | **no** | 50% |
| Says what comes after the hackathon | **no** | 25% |
| Contribution named as reusable | yes | 100% |
| Says what was cut, and why | **no** | 50% |
| States the non-obvious inversion | yes | 25% |
| Standard library / zero dependencies | **no** | 25% |
| Tests, named | yes | 75% |
| Validation, audit trail, re-derivation | yes | 100% |
| Operable screens | yes | 75% |
| Human approval, masked numbers, never-dial | **no** | 75% |
| A real call, quoted | yes | 100% |

**The pattern in the misses is one thing, and it is not the product.** Ringdown masks every phone
number it writes or prints, runs on the standard library with `dependencies = []`, and has
`test_a_reconciled_attempt_places_exactly_one_call_and_never_wakes_the_backup` and
`test_the_same_person_on_two_rungs_is_only_dialled_once` in the suite. Its Devpost description says
`mask` zero times, `stdlib` zero times and `urllib` zero times. The code earns those criteria and
the submission text never claims them.

Deep review of 3 winners' repos (same probes on both sides, nothing executed):

| Competitor | Competitor score | Ringdown score |
|---|---|---|
| Local atlas | 9/10 | 8/10 |
| RingBack | 8/10 | 7/10 |
| Care Call AI | 8/10 | 8/10 |

What we already had going for us, measured against those three: the hash-chained ledger that
re-derives a verdict offline is unique in the field — Local atlas stores `evidenceQuote`,
`collectedAt` and seven publication checks but no chain and no re-derivation; RingBack's audit is one
masked line per real call with no chain. Ringdown is the only entry whose verification crosses
transports (REST to place, MCP to verify). CI runs green here and RingBack has no CI and no linter
at all. Our largest module is a fraction of RingBack's 11,194-line `serveur.py`.

## Improvements to apply

Ordered by how much each one moves a judging criterion.

| # | Change | Criterion | Effort | Where |
|---|---|---|---|---|
| 1 | **Upload the screenshots that already exist.** The submission has 2 images; every winner has 3–7, and the repo already holds nine finished stills from the video build. Nothing to produce. | Product Experience | low | `video/ledger-clean.png`, `video/ledger-tampered.png`, `video/dashboard.png`, `video/run-ladder.png`, `video/run-noclock.png`, `video/run-turns.png`, `video/slide.png`, `video/closing.png` → Devpost gallery |
| 2 | **Say the three things the code already does.** Add masked numbers, `dependencies = []` / stdlib-only, and the never-re-dials test to the submission text. Three sentences against three criteria, on properties that are already true and already tested. | Technical Implementation · Product Experience | low | Devpost description; `README.md:33` alt text already says it better than the pitch does |
| 3 | **Put a number on the incident.** No entry in the field quantified anything, which makes it cheap to win: minutes from page to acknowledgement, the cost of an unacknowledged page, the measured 82 seconds of the real call. | Real World Impact | low | `README.md`, Devpost description, `CHANGELOG.md:24` already dates real calls |
| 4 | **A "what we cut, and why" section.** The twenty-three known ceilings are honest about what fails but never about what was deliberately refused — one call per rung ever, no retry on the ladder, no ETA enforcement. Two winners made that restraint the pitch. | Quality of the Idea | medium | `apps/python/ringdown/README.md` (next to the ceilings), `CONTRIBUTING.md` |
| 5 | **Make the site operable instead of replayable.** Today `docs/` replays three recorded scenarios. The winners let the judge start something. A button that runs the ladder against the bundled fake, with the approval phrase in front of it, closes the loudest gap. | Product Experience | high | `docs/index.html`, `docs/app.js`, `fake/calle_server.py` |
| 6 | **Close, or stop leading with, the live verification ceiling.** A live run still always settles at exit 45. It is ceiling 12 and it is documented, but it is also the one thing a judge who runs the code would hit first. | Technical Implementation | high | `apps/python/ringdown/ringdown/calls.py`, `tests/fixtures/mcp-get-call-run-completed.json` |

## Caveats

- **The screenshot figures were corrected on 2026-10-19.** `parse_ficha` counted occurrences of
  `software_photos` rather than distinct photos, and each photo appears two or three times
  depending on the page, so the counter inflated by a variable factor. This table first read
  4 against a median of 14. The conclusion is unchanged: last of five, a third of the median.
- The competitor repos were read, never executed. Nothing was run from any third-party repo.
- **Test counts are approximate and method-dependent.** `uv run pytest -q` reports **606 passed**
  here because `parametrize` expands; counting `def test_` gives **376**. The reviewing agents
  counted functions, so RingBack's ~1221 against our 376 is the comparison that is apples to apples
  — treat it as "about three times", not as an exact ratio. One agent reported 404 for our side; 376
  is the number this repo's files give.
- **Conversation-Clarify got no repo review.** It publishes no repository — not in the submission,
  not on its Devpost profile, not under any GitHub search for it. It is assessed from its submission
  text alone.
- RingBack was reviewed through `Ludo321/awesome-phone-call-agents` on branch `feat/ringback-app`,
  the fork carrying PR #297. That PR is still open, so the code was never merged upstream.
- A coverage `no` in this table means the **submission text** does not say it. For masked numbers,
  the standard library and the never-re-dials test, the code does — see the paragraph above.
- Care Call AI lists Kubernetes among its Devpost tags and has no Kubernetes file in its repo; its
  first commit imports 120 files and 20,757 lines from a private repo. Local atlas has 74 commits
  predating the event, and its `calle.js` first appears on 9 August. Dated facts, not accusations.
- The four criteria weights are the event's own ("equally weighted"); the observable signals under
  each one were written here and calibrated against what the winners' pages actually say.
