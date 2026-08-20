# The demo video

Everything except pressing record. Built with the `personal-record-video` skill; the scripts
live in `~/.claude/skills/personal-record-video/scripts/`.

| File | What |
| --- | --- |
| `narration.tsv` | The script. Edit this and nothing downstream survives |
| `mkstills.sh` | Regenerates the three stills. The closing line lives in the script |
| `reset.sh` | Demo state for the terminal take. `--check` reports without changing anything |
| `take.sh` | The shot list. Enter advances, one screen per beat after the slide |
| `slide.png` | Beat 1, the opening card: the problem and the thesis |
| `dashboard.png` | First closing still: the real call, recorded and transcribed |
| `closing.png` | Last still: the thesis, what the live provider answered, the repo |
| `live/` | The live call: run files, pre-flight, evidence capture. Gitignored |
| `out/` | Generated. `build-audio.sh` wipes it on every run |

Two recordings feed one video: `raw-terminal.mov` (the CLI) and `phone.mov` (the phone
ringing). They get concatenated into `raw.mov` before the fit.

## 1. The live call

One call does two jobs: it gives beat 8 real footage instead of a screenshot, and it produces
the first responses ever observed from the live provider — which `tests/fixtures/README.md`
calls the single highest-value thing anyone with a dialable number can do for this repo.

```bash
set -a; . apps/python/ringdown/.env; set +a     # the app reads os.environ, not .env
bash video/live/preflight.sh
```

All green, then place the call **now, not in ten minutes** — Render sleeps after 15 and Twilio
times the webhook out at 15 s, so a cold start loses it. Start recording the Vysor window
first.

```bash
cd apps/python/ringdown
uv run python -m ringdown run \
  --incident ../../../video/live/incident.json \
  --rotation ../../../video/live/rotation.json \
  --ledger   ../../../video/live/ledger.jsonl \
  --confirm 'place real calls'
```

Answer in English, in these words — `extract` is English-only and the grounding needs the
recipient to have said the span:

- *"Yes, this is German Massello"*
- *"Yes, I am taking this incident right now"*
- *"Give me fifteen minutes"*

**Expect exit 45, not 0.** `verify.py` asks MCP for the run by the REST call id, and the live
`get_call_run` indexes by a `run_id` only `run_call` hands out. That is a `[?]`, not a
contradiction. Exit 25 is also possible if the live REST GET does not echo the attempt
metadata. Both outcomes are evidence worth having.

Then capture what the provider said:

```bash
PYTHONPATH=$PWD uv run python ../../../video/live/capture.py <call_id>
```

It writes `video/live/observed-<call_id>.json` — raw bodies, unmasked. Mask the phone before
copying anything into `tests/fixtures/`.

## 2. The terminal take

Terminal window at 1280x800, `Cmd+Shift+5` in **window mode**, mic off.

```bash
bash video/reset.sh && bash video/take.sh
```

`reset.sh` must be green, and running it in the same shell warms `uv` so the live `preview` in
the first screen answers in ~80 ms instead of stalling on camera. Seven screens, Enter between
each: `preview` · scenario 1 · scenario 2 · scenario 4 · scenario 6 · the committed ledger ·
the tampered ledger. Hold ~4 s on each — the fit compresses the waiting afterwards, so only
the ORDER matters. Scenario 2 is the money shot: it has to be readable.

Save as `video/raw-terminal.mov`.

## 3. The stills

```bash
bash video/mkstills.sh <screenshot>
```

The closing line is written **after** the call, because the new fact is whatever the provider
returned. Edit it in `mkstills.sh` and re-run.

`dashboard.png` needs a screenshot of the local dashboard: run the receiver against its own
`calls.db`, fetch the page with `curl -u`, serve that static copy and shoot it. The Render free
tier wipes the database on every deploy, and Basic Auth opens a native dialog that blocks
browser automation — hence the static copy.

## 4. Assembling

The audio is already built and under the cap — `out/timing.txt` has the verdict and the
per-beat lengths, and it is the only source for the numbers below. Re-run `build-audio.sh`
only if the narration changes, and then redo `timing-noslide.txt`, the stills, the marks and
the fit, because it wipes `out/`.

Concatenate first. The phone is vertical, so it gets scaled and pillarboxed onto the same
`0x0e131f` the stills use, and both clips are normalised to 1920x1080 before concat.

```bash
# raw-terminal.mov + phone.mov -> raw.mov
```

Then find the seven marks (the timestamp in `raw.mov` where each screen appears) from a
timestamped contact sheet:

```bash
VIDEO_DIR=$PWD/video python3 ~/.claude/skills/personal-record-video/scripts/fit-to-audio.py \
  video/raw.mov --beats <m1,m2,m3,m4,m5,m6,m7> --timing video/out/timing-noslide.txt

VIDEO_DIR=$PWD/video END=142.6 \
  SLIDE=video/slide.png SLIDE_DUR=18.7 \
  OUTRO="video/dashboard.png:4,video/closing.png:4.2" OUTRO_REPLACE=8.2 \
  bash ~/.claude/skills/personal-record-video/scripts/build-video.sh video/out/raw-fitted.mov
```

The arithmetic, all of it out of `out/timing.txt`: the track is 169.5 s and beat 1 is 18.7 s,
so the recording covers beats 2 to 8 = 150.8 s. The two closing stills cover the tail, so
`OUTRO_REPLACE = 4 + 4.2` and `END = 150.8 - 8.2 = 142.6`. Beat 8 is 17.2 s, so the phone keeps
`17.2 - 8.2 = 9` of them. Under ~3.5 s a still cannot be read; adjust the split once the
footage exists.

Out comes `video/out/demo.mp4` and `video/out/demo.en.srt`. Upload public or unlisted, never
private, with the SRT as the caption track.
