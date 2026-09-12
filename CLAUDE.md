# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Two independent packages

`apps/python/ringdown/` is the product; `apps/python/calle-receiver/` is demo infrastructure
(Twilio relay, FastAPI). They share nothing — separate `pyproject.toml`, separate lockfile,
separate venv, separate pytest run. CI runs both in a matrix and fails if a third
`apps/python/*/pyproject.toml` appears.

Ringdown has **zero runtime dependencies** (`dependencies = []`, stdlib only, `urllib.request` for
HTTP). Do not add one. The receiver may use its FastAPI/SQLModel/Twilio stack.

## Commands

```bash
cd apps/python/ringdown        # or apps/python/calle-receiver
uv sync
uv run pytest                  # ringdown: 486 tests · receiver: 29
uv run pytest tests/test_verify.py -k grounding    # one file / one test
```

Ringdown demo, and the thing to run after touching the ladder, the report or the ledger:

```bash
cd apps/python/ringdown && uv sync && uv run python -m demo.run_local
```

It runs eight scenarios against `fake/calle_server.py` on loopback and **rewrites
`examples/ledger.example.jsonl`**. `tests/test_demo.py` asserts that the committed ledger is byte-identical
to what the demo writes, and that the demo still prints every block quoted in `demo/EXPECTED.md`,
in order. So a change to output formatting or ledger content means: run the demo, reconcile
`EXPECTED.md` by hand, commit the regenerated ledger — **and copy it to
`docs/ledger.example.jsonl`**, which the site fetches from its own origin. A third assertion in
`tests/test_demo.py` fails when those two files drift; it skips where `docs/` does not exist, so
the upstream checkout is unaffected.

Receiver locally: `uv run uvicorn app.main:app --reload --port 8000` plus a
`cloudflared` tunnel — see `apps/python/calle-receiver/README.md` and the `deploy` / `twilio`
skills in `.claude/skills/`.

## Ringdown architecture

Two transports, one verdict. The call is **placed over REST** (`RestClient`) and **verified over
MCP** (`McpClient`) — verifying through the channel that wrote proves nothing, and that constraint
shapes the module layout.

Flow: `incident.py` (load + `resolve_ladder`) → `script.py` (call payload, content-derived
idempotency key, the spoken task) → `escalate.py` (`run_ladder`, one rung at a time) → `calle.py`
(HTTP) → `calls.py` (`CallSnapshot` / `CallRun` parsing) → `extract.py` + `dispositions.py`
(spans, grounding, verdict) → `verify.py` (MCP re-derivation) → `exits.py` (exit code) +
`audit.py` (hash-chained ledger) + `report.py` (terminal output).

Layering is **enforced by `tests/test_layering.py`**, not by convention:
- the pure modules (`extract`, `dispositions`, `calls`, `checks`, `canonical`, `incident`,
  `script`, `adapter`, `exits`, `task`) and `audit` must not pull in `urllib.request` — importing them must
  not touch the network stack;
- `audit` must not import `escalate` or `calle`: reading a ledger never loads the provider client;
- `report` must not import `calle` or `dispositions`.

Add a module to `FORBIDDEN`/`PURE` there when you add a layer.

### Invariants that are not stylistic

- **One call per rung, ever.** The idempotency key is derived from the call payload
  (`script.idempotency_key`), so an ambiguous create is replayed with the same key rather than
  waking a second person. Against the live API a timed-out create is the *normal* path, not an
  edge case. The ladder never re-calls.
- **`intent` is written to the ledger before the POST**, `attempt` after it settles. An `intent`
  with no `attempt` is the shape that says "a call may exist" — `verify` reports it as `[?]`/45.
- **URLs are a trust boundary.** `assert_trusted_url` pins each channel to its own exact live URL
  by string comparison (or loopback); the pin lives on the client class (`RestClient.LIVE` /
  `McpClient.LIVE`), so swapping the flags cannot send the API key to the MCP endpoint. Loopback
  gets `RINGDOWN_FAKE_*` credentials, never the live ones.
- **The transcript is data, never instruction.** Every recorded field must be quoted by a span
  spoken in a *recipient* turn; an injection attempt is stored, flagged `instructed`, and changes
  no field.
- **Phone numbers are masked everywhere** written or printed (`mask_phone`); raw transcripts are
  never stored, only the quoted spans.
- **Exit-code precedence** (`exits.settle`/`reconcile`): 25 skips verification; 40 (contradicted)
  overrides 0/10/20/45; 45 (unanswered) only when nothing was contradicted. A channel that is down
  is never read as a channel that disagrees — `Check` is `tuple[bool | None, str]` and `None` is
  load-bearing.
- **Ledger schema versioning**: `audit.VERDICT_RULES` maps schema version → the verdict rule that
  wrote it. `verify` re-derives an old record with the old rule. Changing the verdict rule means a
  new version and a new entry, plus a golden ledger in `tests/golden/`.

### fake/ vs tests/fixtures/

`fake/calle_server.py` mirrors the shape this app *invented*; `tests/fixtures/*.json` hold the
shape the live provider actually answers with (values rewritten for the repo, provenance in each
file's `what`/`source`/`unobserved`/`why_it_matters`). Fixture tests deliberately bypass the fake —
they exist because client and fake were written from one reading of the docs, so a misreading lands
in both. One fixture (`mcp-get-call-run-completed.json`) currently proves `run_from` wrong; the
fake still mirrors the wrong shape. Making it faithful changes what the ten verification checks can
prove, so it is a decision, not a patch — see ceiling 12 in `apps/python/ringdown/README.md`.

## Documentation is load-bearing

`apps/python/ringdown/README.md` (setup, exit codes, file formats, threat model, twenty-three known
ceilings) and `demo/EXPECTED.md` are tested or referenced, not decorative. When behaviour changes,
update the ceilings rather than deleting them — the honesty about what does not work is the point,
and a live run currently always settles at exit 45.

## The other checkout

`apps/python/ringdown/` and `skills/incident-escalation-call/` also live, byte-identical, in the
fork at `~/Documents/awesome-phone-call-agents` (branch `feat/ringdown-pagerduty-scripts-and-mapping-drafts`, the
upstream PR). There is no submodule and no sync script: mirror by hand before committing, and diff
with `-x .venv -x __pycache__ -x .pytest_cache -x out`. Only those two paths travel upstream — the
root `README.md`, `docs/` and `apps/python/calle-receiver/` stay here.
