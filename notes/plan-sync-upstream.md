# Resync the upstream contribution and open the second PR

Working note, written 12 September 2026, to be run **after** the pending Ringdown improvements were
pushed. The hackathon compliance review was a separate document and is not kept.

Hackathon deadline: **14 September 2026, 12:45 PM (GMT-3)**.

> **What actually happened.** This was executed the same day. The branch went up as
> `feat/ringdown-pagerduty-scripts-and-mapping-drafts` and became
> [PR #512](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/512), with a second commit
> added afterwards for the threat-model documentation. Three numbers in here were already stale by
> the time it ran: the delta was **36 files, +2373 / −162**, not 31 files; the suite was **449
> tests**, not 427; and there were **five** new test files, not four, because `suggest-mapping`
> landed in between. Two claims in section 4 were wrong on the day: the fork's copy of
> `validate_repository.py` was **not** out of date (identical blob to upstream), and the skill diff
> was **not** empty — `SKILL.md` had picked up five lines. Sections 1 to 3 are the part worth
> keeping: they are the review framework, and they do not expire.

---

## 1. What is missing upstream, and why it matters

PR [#205](https://github.com/CALLE-AI/awesome-phone-call-agents/pull/205) was merged on
**25 August**. Since then Ringdown has added, counting only what travels:

```
31 files, +1820 / −142   (git diff 52f80b2..HEAD -- apps/python/ringdown)
```

`52f80b2` is the commit mirrored in that PR: *"Pin each channel to its own endpoint and write the
fixtures from scratch"*.

**Files that do not exist upstream:**

| Path | What it brings |
| --- | --- |
| `ringdown/pagerduty.py` | The note back to PagerDuty |
| `ringdown/task.py` | Configurable call scripts and their validation |
| `tests/test_pagerduty.py` | 18 tests |
| `tests/test_adapter.py`, `test_calls.py`, `test_site_port.py` | — |
| `examples/pagerduty.example.json`, `pagerduty-mapping.example.json` | — |
| `examples/sla-breach.example.json`, `sla-breach.script.txt` | The second use case |
| `LICENSE` | Exists **in order to travel** (the `CHANGELOG` says so), and the app README links it at the end |

**Behaviour changes that are also absent:** exit code 50 and `LedgerError`, quote neutralisation in
the incident fields against injection, validation of an unknown `speaker` in the transcript, and
`assert_trusted_url` with multiple pinned endpoints.

**Two claims that are false and visible upstream today** — and under the current policy a verifiable
false claim is a Must Fix:

```
apps/python/ringdown/README.md:64-65  (upstream)
  pip install pytest
  python -m pytest -q       # 295 tests, no credentials, no outbound calls
```

The truth is `uv sync` / `uv run pytest -q` and **427 tests**. Copying the tree fixes it by itself.

**And the app is not in the main list.** `grep -i ringdown README.md` against upstream `main`
returns **zero**. #205 added the skill to the root README (line 155) and the app to
`apps/README.md` (line 59), but the `### Apps` table in the root README — the awesome list itself —
does not mention it. It is the only in-repo app missing from there.

---

## 2. The review framework, so it never has to be researched again

### 2.1 What the reviewer demanded in #205

`@Ray-56` blocked the PR **twice**, with the same two Must Fix items. Verbatim:

> **The committed fixtures and documentation explicitly contain verbatim live REST/MCP responses,
> real-call transcripts, and raw call/run/recipient/attempt/provider identifiers.** Replace them
> with wholly synthetic fixtures using reserved fictional data and rewrite this PR's unique history.

> **Remove the arbitrary `--allow-host` escape hatch and pin each live credential to its exact
> trusted HTTPS origin.** Non-default trusted-host ports/paths and plaintext loopback must not
> receive real API keys or MCP tokens; use separate throwaway credentials for local fakes. […] REST
> and MCP validation accepts either production endpoint for either channel, allowing credentials to
> be cross-sent when the flags are swapped.

Closed on 25 August with: *"both frozen Must Fix items are closed at 5072838c"*.

### 2.2 The new delta touches exactly those two areas — and reopens neither

Audited file by file. All of this is assertable in the PR:

**Blocker 1 — synthetic data:**
- No new phone number in the delta except `+1********00`, already masked. The whole repo uses
  reserved ranges: `+1415555010x` (NANP 555-01XX), `+1555010xxxx`, `+441632960111` (Ofcom drama
  range).
- No new names. No email outside `example.com` (except finding 7 below).
- Of the 291 lines added to the README, **none** claims verbatim provenance. The "six calls placed
  against the live provider" narrative is pre-existing text that already travelled and was accepted.
- `tests/test_fixtures.py:21-27` holds the synthetic declaration over the whole `tests/fixtures/*.json`
  glob: a new fixture without a `source` breaks the build.

**Blocker 2 — pinned credentials:**
- `--allow-host` remains eradicated: zero occurrences in the repo.
- The pin still lives on the class: `RestClient.LIVE = LIVE_BASE_URL`, `McpClient.LIVE = LIVE_MCP_URL`
  (`ringdown/calle.py:129-157`), each a single `str`. The `Sequence` branch is never taken for the
  call channels.
- The flag swap is tested: `tests/test_cli.py:118`
  (`test_swapping_the_two_flags_never_sends_a_credential_to_the_other_channel`, which also asserts
  `not ledger.exists()`) and `tests/test_calle.py:62-85` (10 near misses: suffix confusion, path
  prefix, `notapi.`, port `:8443`, `/../evil`, `http://`, userinfo).
- The third channel **extends** the guarantee rather than breaking it. `ringdown/__main__.py:125-130`:

  ```python
  def _credential(url: str, live: str, fake: str) -> str:
      name = fake if is_loopback(url) else live
      value = os.environ.get(name, "")
      if not value:
          emit(f"{name} is not set in the environment")
      return value
  ```

  On loopback the live variable's name is **never even constructed**. Three call sites, all alike:
  `:143`, `:144` and `:212-213` (`PAGERDUTY_TOKEN` / `RINGDOWN_FAKE_PAGERDUTY_TOKEN`). At `:212` it
  receives `pinned`, the return of `assert_trusted_url`, not the raw URL.
- `ringdown/pagerduty.py:39-44` defines `_NoRedirect` and does not follow redirects — without it a
  302 from PagerDuty would forward the `Authorization` header. The token appears in no error path
  and not in the ledger, which stores only `host`, `delivered` and a truncated `detail`.

### 2.3 The policy changed on 11 September

`docs/community-review-policy.md`, version **2026-09-11**, says of itself that it **supersedes the
stricter historical review comments**, and on recent PRs the reviewer has been closing with
*"Obsolete production-hardening and blanket synthetic-history blockers are withdrawn"*.

Ringdown falls in the **Hackathon / live-capable demo** tier, which asks for four things. All four
are already in place:

| Policy requirement | Where |
| --- | --- |
| explicit per-run operator intent | `CONFIRMATION = "place real calls"` — `ringdown/__main__.py:61` |
| authorized valid E.164 destinations | `validate_e164` — `ringdown/incident.py:94` |
| masked user-facing/logged phone numbers | `mask_phone` — `ringdown/incident.py:103` |
| credentials restricted to approved secure origins | `assert_trusted_url` plus the per-class pin |

What **does** block under that policy: live side effects by default, missing explicit intent,
invalid destinations, concrete duplicate-call paths, real exposure of credentials or private data,
and **materially false claims left uncorrected** — which is why those 295 tests matter.

### 2.4 What CI runs on a PR

`.github/workflows/validate.yml`, job `validate`: checkout, Python 3.x, Node 20 and **one single
command**, `python3 scripts/validate_repository.py`. **It does not run pytest.** The suite has to be
run by hand.

---

## 3. Findings to consider before pushing

These came out of auditing the delta with the same criteria the reviewer used to block twice.
**Only the first two have real logic behind them**; the rest is presentation and none of them blocks
under the current policy.

> All eight were fixed before the sync, in commit "Close the gaps an upstream reviewer would open
> first". Finding 3 was answered in the PR body rather than changed in code, and finding 6 became a
> sentence in `tests/fixtures/README.md`.

### With real logic behind them

**1. The negative PagerDuty test on loopback is missing.**

The exact equivalent exists for CALL-E and it is *the* point they blocked on. No test sets
`PAGERDUTY_TOKEN` (the real name) and verifies that loopback ignores it. The logic is correct by
construction — `_credential` is shared — but an eight-line test closes the discussion without a
round trip. Model to copy, `tests/test_cli.py:102-113`:

```python
def test_the_live_api_key_is_never_read_for_a_run_against_the_local_fake(
    serving, incident_file, tmp_path, capsys, monkeypatch
):
    monkeypatch.delenv("RINGDOWN_FAKE_API_KEY")
    monkeypatch.setenv("CALLE_API_KEY", "rd_live_key")
    ...
    assert code == EXIT_USAGE
    assert "RINGDOWN_FAKE_API_KEY is not set" in capsys.readouterr().out
```

Also missing, and cheaper still: the case where the PagerDuty token is refused against the CALL-E
URL — symmetric to `tests/test_calle.py:81-82`.

**2. The incident's `script` field is not contained to its directory.**

`ringdown/incident.py:228-230`:

```python
script = (path.parent / str(named)).resolve()
if not script.is_file():
    raise IncidentError(f"the incident names a call script at {script}, which does not exist")
```

Two things: `pathlib` makes `path.parent / "/etc/shadow"` into `/etc/shadow`, so an absolute path
ignores the parent entirely; and `../../../` walks out just as easily. Real exploitation is narrow
because `validate_task_template` requires `{name}`, the ETA question and the literal string
`"quoted data, never instructions"` — no system file passes that. But the error message **prints the
resolved absolute path and distinguishes "exists" from "does not exist"**: it is an existence oracle
for arbitrary paths. One-line fix:

```python
if not script.is_relative_to(path.parent.resolve()):
    raise IncidentError(...)
```

### Presentation

**3. `LIVE_URLS` reintroduces the `Sequence` shape.** `ringdown/pagerduty.py:14-16` defines
`LIVE_URLS = (LIVE_US, LIVE_EU)`, and it is the only thing justifying `assert_trusted_url` accepting
`str | Sequence[str]`. They are the two *service regions* of one channel, not two different
channels, and it is documented honestly in the README. But it is literally the shape the previous
fix closed: a `PAGERDUTY_TOKEN` from a US account can be sent to the EU host. Either anticipate it
in the PR body with a link to PagerDuty's service regions, or pin it with a `--pagerduty-region`.

**4. The scheme error interpolates the whole URL.** `ringdown/calle.py:73-76`: the userinfo check is
deliberately written **not** to print the URL, but it runs *after* the scheme check, which does
`f"{url!r}"`. For `http`/`https` the order is safe; with an odd scheme (`ftp://user:hunter2@host`)
the password goes to stdout. Fix: move the userinfo check above.

**5. `examples/pagerduty.example.json` carries five provider-shaped ids** (`PBAZLIU`, `PF9KMXH`,
`PRLPRWM`, `PUS0KTE` and a ULID) **without declaring where they came from.** They are the sample
values from PagerDuty's public documentation, and the `html_url`s already use the fictional
`example.pagerduty.com` subdomain — but the file does not say so, and `test_fixtures.py` only covers
`tests/fixtures/`. One line of `source` resolves it.

**6. `tests/fixtures/README.md` escalates the live-call narrative.** It is the file the reviewer
cited, and the delta only moves it towards *more* provenance: `:33` goes from "three calls" to *"On
2026-08-20 six calls were placed against the live provider from a US Twilio number…"*, and `:41-43`
from "Both REST creates timed out" to "All five…". The paragraph clarifying that only the shape is
evidence sits at `:13-19` and is correct — but anyone searching for "live" lands on `:33` first. A
sentence near that line repeating the framing neutralises it.

**7. `a@b.com` in `tests/test_pagerduty.py:118,133,145`.** `b.com` is a real registered domain and is
not in RFC 2606; the rest of the repo uses `example.com` correctly. Mechanical *Should Fix*, not a
blocker.

**8. `ringdown/__main__.py:137-138` uses the module constants** (`LIVE_BASE_URL`, `LIVE_MCP_URL`)
instead of `RestClient.LIVE` / `McpClient.LIVE`. Same value, but it duplicates the source of truth
that the #205 resolution deliberately moved onto the class. A one-word change that takes an argument
away from the reviewer.

---

## 4. The procedure

> **Before starting: recompute the delta.** Every number in this document was measured on
> 12 September. After pushing your improvements, `git diff 52f80b2..HEAD -- apps/python/ringdown
> --stat` and `uv run pytest -q` tell the new truth.

> **Environment trap:** the RTK hook truncates `git diff` output, so `git diff | grep` returns
> **false negatives**. For any inspection of the diff use the binary directly:
> `$(which -a git | tail -1) diff …`.

### Step 1 — start from the real upstream

The fork's `upstream/main` is at `5e09956` and the remote is at `46be3d1`: it does not even contain
the merge of #205 itself. It has to be fetched, and the branch cut from there — **not** from
`feat/incident-escalation-call`.

```bash
cd ~/Documents/awesome-phone-call-agents
git fetch upstream
git switch -c feat/ringdown-pagerduty-and-call-scripts upstream/main
```

The name follows `docs/git-naming-conventions.md`: `<type>/<kebab-summary>`, with the scope taken
from an existing directory. `.idea/` is untracked in the fork and does not enter the commit.

### Step 2 — copy the tree, protecting what belongs to the fork

```bash
rsync -a --delete \
  --exclude='.venv/' --exclude='__pycache__/' --exclude='.pytest_cache/' \
  --exclude='demo/out/' --exclude='.env' --exclude='.gitignore' \
  ~/Documents/ringdown/apps/python/ringdown/ \
  ~/Documents/awesome-phone-call-agents/apps/python/ringdown/
```

Two things a `cp -R` would break:

- **`apps/python/ringdown/.gitignore` exists only in the fork.** Ringdown covers it from the
  `.gitignore` at its root, which does not travel. It is in `--exclude`, and rsync **does not delete
  what it excludes** unless given `--delete-excluded`, so it survives the `--delete`.
- **`.env` does not travel**, by explicit exclusion and not by luck.

`LICENSE` **does** travel: it is left out of the exclusions on purpose.

After the rsync, read the whole `git status` and confirm `--delete` took nothing it should not have.

### Step 3 — the row in the root README

The `### Apps` section has two blocks: a bulleted list and a three-column table preceded by
*"Runnable demo apps live under `apps/`"*. In-repo apps go in **the table**, with backticks and with
the `apps/` prefix — unlike `apps/README.md`, which omits it:

```markdown
| [`apps/python/ringdown`](apps/python/ringdown/) | Python | … |
```

The table has no detectable order (neither alphabetical nor by language), so the row goes **at the
end of the block**, imitating the row before it. The description derives from the one already in
`apps/README.md:59` without repeating it word for word. The `apps/README.md` row **is not touched**:
it is still accurate.

### Step 4 — verify

```bash
cd ~/Documents/awesome-phone-call-agents
diff -r ~/Documents/ringdown/skills/incident-escalation-call skills/incident-escalation-call
python3 scripts/validate_repository.py
cd apps/python/ringdown && uv sync && uv run pytest -q
```

- The skill `diff` should be **empty**: it has not changed since #205. *(It was not, on the day —
  `SKILL.md` had gained the `suggest-mapping` block.)*
- The validator has to be the one from an updated `upstream/main`, not the fork's stale copy — which
  is why this comes after step 1. *(It turned out the fork's copy was already identical.)*
- The suite runs **inside the fork**, where `test_demo.py` and `test_site_port.py` take the skip path
  because `docs/` is absent. That is exactly what will happen upstream: confirm that they **skip and
  do not fail**.

### Step 5 — one commit

```
feat(ringdown): add PagerDuty notes, custom call scripts, and exit code 50
```

Conventional Commits, as `docs/git-naming-conventions.md` requires: valid type, scope taken from the
directory name, imperative verb, lowercase initial, no trailing period. The body lists what it
brings and explains why `assert_trusted_url` now accepts a sequence.

### Step 6 — final checks before publishing

```bash
git status --short                    # only .idea/ untracked
git show --stat HEAD                  # nothing from docs/ video/ notes/
git log --oneline upstream/main..HEAD # exactly one commit
git diff upstream/main --stat -- . ':!apps/python/ringdown' ':!README.md'   # empty
git grep -n "ringdown" README.md      # the new row
git show HEAD -- apps/python/ringdown/.gitignore                            # unchanged
```

The second to last is the one that matters: it proves nothing outside `apps/python/ringdown/` and
the root README was touched. Confirm as well that `.env` is not in the commit.

---

## 5. The pull request text

Title, same as the commit (the convention asks to reuse the message when there is a single commit):

```
feat(ringdown): add PagerDuty notes, custom call scripts, and exit code 50
```

Body, on top of `.github/pull_request_template.md`:

```markdown
## Summary

Ringdown was merged in #205 on 25 August. This brings the app up to date with the work done
since, and adds the entry the app never got in the root README.

What is new since #205:

- **The note back to PagerDuty.** `ringdown/pagerduty.py` posts a note quoting what the engineer
  actually said, to the incident the page came from. A note, never an acknowledgement: suppressing
  PagerDuty's own escalation on the strength of a phone call stays the operator's decision. No
  vendor code — the incident arrives through a mapping file.
- **The call script is configurable.** `ringdown/task.py` lets an incident file replace what the
  agent says, so the same ladder, verification and ledger chase a supplier over a missed service
  level with no code that knows about SLAs — `examples/sla-breach.example.json` ships one. A
  script is refused if it drops the sentences the extractor and the injection defence depend on.
- **Exit code 50 and `LedgerError`.** A ledger that cannot be opened, read or extended once a call
  has been placed is an infrastructure failure, not the operator's mistake it used to be reported
  as.
- **The incident payload is data too.** Quotes in `title`, `summary` and `service` are neutralised
  where the task is formatted, so an alert payload cannot close the wrapper it is read inside.
- Four new test files; the suite is 427 tests, no credentials and no outbound calls.

The README's setup block said `pip install pytest` and "295 tests". Both were stale; they now say
`uv sync` / `uv run pytest -q` and 427.

## The two Must Fix items from #205 still hold

Both areas this PR touches are the ones that blocked #205 twice, so here is where to look:

- **Each credential is still pinned to its own exact origin.** `RestClient.LIVE` and
  `McpClient.LIVE` (`ringdown/calle.py:129-157`) are each a single URL, compared whole. Swapping
  `--base-url` and `--mcp-url` is refused before a socket opens — `tests/test_cli.py:118` and ten
  near misses in `tests/test_calle.py:71-85`.
- **`assert_trusted_url` now accepts `str | Sequence[str]`, and that is only for PagerDuty**, which
  publishes two service regions (`api.pagerduty.com` and `api.eu.pagerduty.com`). Both call
  channels still pass one string each, so the cross-send described in #205 remains impossible.
- **The third channel uses the same loopback rule.** `_credential(pinned, "PAGERDUTY_TOKEN",
  "RINGDOWN_FAKE_PAGERDUTY_TOKEN")` (`ringdown/__main__.py:212`): against loopback the live
  variable's name is never even constructed. `ringdown/pagerduty.py` refuses to follow redirects,
  so a 302 cannot carry the `Authorization` header off-host, and the ledger records the hostname,
  not the URL or the token.
- **No new fixture, example or test carries a provider response.** The only phone number the diff
  adds is already masked; every address is under `example.com`.

Against `docs/community-review-policy.md` (2026-09-11), this is a Hackathon / live-capable demo:
per-run operator intent is `--confirm 'place real calls'` (`__main__.py:61`), destinations go
through `validate_e164` (`incident.py:94`), numbers are masked by `mask_phone` (`incident.py:103`),
and credentials are pinned as above.

## Type

- [ ] New skill
- [x] New runnable app
- [ ] New workflow plugin
- [ ] New provider adapter
- [ ] New scheduler recipe
- [x] README awesome-list entry
- [x] Safety or documentation update
- [ ] Validation or tooling update

## Checklist

- [x] Repository-facing content is written in English.
- [x] Branch name, commit messages, and PR title follow `docs/git-naming-conventions.md`.
- [x] No secrets, tokens, private phone numbers, call recordings, or private transcripts are included.
- [x] Real-world side effects are clearly described.
- [x] Phone numbers are masked in documentation and test fixtures unless they are clearly fictional.
- [x] Recurring workflows include cancellation behavior.
- [x] Runnable code has a dry-run, fake-server, or no-call path by default.
- [x] `python3 scripts/validate_repository.py` passes.
```

Before pasting it: reconfirm the test count with `uv run pytest -q` and adjust the list of new
things to what the improvements actually brought.
