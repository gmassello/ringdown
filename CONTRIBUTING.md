# Contributing

## Two packages, no shared anything

`apps/python/ringdown/` is the product; `apps/python/calle-receiver/` is demo infrastructure.
They share no `pyproject.toml`, no lockfile, no virtualenv and no pytest run, and CI runs them as
a matrix that fails if a third `apps/python/*/pyproject.toml` shows up.

```bash
cd apps/python/ringdown        # or apps/python/calle-receiver
uv sync
uv run pytest                  # ringdown: 502 · receiver: 29
```

**Ringdown has zero runtime dependencies** — `dependencies = []`, standard library only,
`urllib.request` for HTTP. A pull request that adds one will not be merged. The receiver may use
its FastAPI/SQLModel/Twilio stack freely.

## Touching the ladder, the report or the ledger

Output formatting and ledger content are pinned by a test, so a change to either is a four-step
move, not a one-line edit:

```bash
cd apps/python/ringdown && uv run python -m demo.run_local
```

That runs eight scenarios against `fake/calle_server.py` on loopback and **rewrites**
`examples/ledger.example.jsonl`. Then:

1. Reconcile `demo/EXPECTED.md` by hand — `tests/test_demo.py` asserts the demo still prints every
   block quoted there, in order.
2. Commit the regenerated `examples/ledger.example.jsonl`; the test asserts it is byte-identical to
   what the demo wrote.
3. Copy it to `docs/ledger.example.jsonl`, which the project site fetches from its own origin. A
   third assertion fails when the two drift.

## Layering is enforced, not conventional

`tests/test_layering.py` fails if the pure modules (`extract`, `dispositions`, `calls`, `checks`,
`canonical`, `incident`, `script`, `adapter`, `exits`, `task`) or `audit` pull in `urllib.request`; if
`audit` imports `escalate` or `calle`; or if `report` imports `calle` or `dispositions`. Adding a
layer means adding it to `FORBIDDEN`/`PURE` there.

## Changing the verdict rule

`audit.VERDICT_RULES` maps a ledger schema version to the rule that wrote it, so `verify`
re-derives an old record with the old rule. Changing how a verdict is decided therefore means a
new schema version, a new entry in that map, and a golden ledger under `tests/golden/`.

## fake/ vs tests/fixtures/

`fake/calle_server.py` mirrors the shape this app invented. `tests/fixtures/*.json` hold the shape
the live provider actually answers with, and the tests that read them deliberately bypass the fake:
client and fake were written from one reading of the docs, so a misreading lands in both. Every
fixture carries its own `what` / `source` / `unobserved` / `why_it_matters`; fill those in when you
add one.

## Documentation is load-bearing

`apps/python/ringdown/README.md` and `demo/EXPECTED.md` are tested or referenced, not decorative.
When behaviour changes, **update the twenty-three known ceilings rather than deleting them** — the
honesty about what does not work is the point.

## Two checkouts

`apps/python/ringdown/` and `skills/incident-escalation-call/` also live in the fork that carries
the upstream PR. There is no submodule and no sync script: mirror by hand, and diff with
`-x .venv -x __pycache__ -x .pytest_cache -x out`. Only those two paths travel upstream — the root
`README.md`, `docs/` and `apps/python/calle-receiver/` stay here.

## Known papercut

The test count is hardcoded in three places and nothing keeps them honest: the badge in
`README.md`, the Setup block in `apps/python/ringdown/README.md`, and the receiver's test line.
Update all three, or move them to something generated.
