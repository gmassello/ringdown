# The demo video

Everything except pressing record. Built with the `personal-record-video` skill; the scripts
live in `~/.claude/skills/personal-record-video/scripts/`.

| File | What |
| --- | --- |
| `narration.tsv` | The script. Edit this and nothing downstream survives |
| `mkstills.sh` | Regenerates the three stills. The closing line lives in the script |
| `mkintro.sh` | Regenerates the opening 18.7 s and mixes the ringback under the voice |
| `mkbody.sh` | Rebuilds the body: six terminal stills, the two ledger stills, the dashboard |
| `mkledger.sh` | Regenerates the two ledger stills off the published site. Needs Chrome |
| `reset.sh` | Demo state for the terminal take. `--check` reports without changing anything |
| `take.sh` | The shot list. Enter advances, one screen per beat after the opening |
| `slide.png` | The opening card. No longer in the video — `mkintro.sh` replaced it. Poster and thumbnail |
| `dashboard.png` | First closing still: the real call, recorded and transcribed |
| `closing.png` | Last still: the thesis, what the live provider answered, the repo |
| `ledger-clean.png` | The `#ledger` widget as published. `exit 0`, 26 checks |
| `ledger-tampered.png` | The same widget after `#tamper-btn`. `exit 40`, every seal still green |
| `live/` | The live call: run files, pre-flight, evidence capture. Gitignored |
| `out/` | Generated. `build-audio.sh` wipes it on every run, `narration.voice.wav` included |

`docs/demo.gif`, the animation at the top of the root README, comes from none of this. It is
captured off the published site, not off a terminal take: the `#ledger` section at
<https://gmassello.github.io/ringdown/#ledger>, with `#tamper-btn` and the `verify` card lifted
into a fixed full-bleed container so the screenshot needs no cropping, three states — clean,
button focused, tampered — grabbed with `screencapture` at 2.5x and assembled by `ffmpeg`
(`concat`, then `palettegen` with `stats_mode=full`, which the red of `exit 40` needs).

Two recordings feed one video: `raw-terminal.mov` (the CLI) and `phone.mov` (the phone
ringing). **`phone.mov` no longer reaches the video directly** — `mkintro.sh` takes tight,
masked bands out of it for the opening, and the closing seconds show the dashboard instead.
The clip that used to sit there printed the caller ID in the clear.

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

The crop is tuned to a **2128x1400** shot — a 1064x700 viewport at device scale 2, which is what
headless Chrome gives you and what keeps the card sharp when it is scaled back up:

```bash
'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' --headless=new --disable-gpu \
  --screenshot=shot.png --window-size=1064,700 --force-device-scale-factor=2 --hide-scrollbars \
  http://localhost:8123/
```

Seed the call **already masked** (`+1********83 → +1********44`) — the dashboard prints whatever is
in the database, and the still is published.

## 4. The opening

Beat 1 used to be `slide.png` held still for 18.7 s. `mkintro.sh` replaces it with six shots cut
out of `phone.mov`, and mixes a ringback tone under the voice that already exists:

```bash
bash video/mkintro.sh          # -> out/intro.mov (561 frames), out/ring.wav, out/narration.wav
```

The cuts land in the silences between the spoken lines (`3.76-4.16`, `6.11-6.61`, `9.96-10.26`,
`13.96-14.66`, from `out/captions.srt`), so no shot changes mid-sentence. The tone is the real US
ringback — 440+480 Hz, 2 s on, 4 s off — synthesised, so there is no licence to clear: a bed at
`BED=0.05` until 14.3 s, then one burst at `RING=0.12` that stops dead at 16.3 s when the shot cuts
to the answered call. Both are env vars; that is the knob to set by ear.

Every shot of the phone is a **tight band**: the Vysor chrome, the home screen and the app names
never make it in, and the caller ID is masked with `delogo`. `crop=638:1384:68:128` is the phone's
own screen inside the 774x1692 source.

`narration.voice.wav` is the take as `build-audio.sh` produced it and `narration.wav` is derived
from it, so the script is safe to re-run. **That backup is now as irreplaceable as
`raw-fitted.mov`** — `build-audio.sh` deletes both.

## 5. The ledger stills

The beat at 2:18 used to be two screenshots of `verify` in the terminal. It is now the published
site, which runs the same `examples/ledger.example.jsonl` through a port of `audit.chain_checks`
and therefore counts the same **26 checks** the narration counts — `#tamper-btn` reseals the whole
chain around a rewritten verdict, so the two states are exactly the two the voice describes.

```bash
bash video/mkledger.sh        # -> video/ledger-clean.png, video/ledger-tampered.png
```

It serves a copy of `docs/` on loopback rather than shooting `file://`, because the widget needs
`fetch` and `crypto.subtle`, and appends a module that forces the dark palette (the page ships
`data-rd-theme="light"`), hides the prose the still does not need, waits for `#ledger-body`, and —
in the second pass only — clicks the button. `VIEW` and `SCALE` are the two knobs; the shot is
padded to 1920x1080 on `#161826`, the site's own background, so the still carries no frame.

The bottom ~110 px of each shot is left empty on purpose: that is where the burned-in subtitles land.

`docs/demo.gif` is the same widget captured the same way, by hand — see the note at the top.

## 6. The body

`mkbody.sh` rebuilds `out/raw-fitted.mov` — the 151.0 s between the opening and the outro:

```bash
bash video/mkbody.sh          # -> out/frames/, out/terminal.mp4, out/evidence.mp4, out/raw-fitted.mov
```

Six of the eight stills come out of `raw-terminal.mov` at an explicit mark; `s7` and `s8` are
copied from `ledger-clean.png` and `ledger-tampered.png`, and the script refuses to run if those
are missing.

**Why `MARKS` exists.** A mark handed to `fit-to-audio.py` once landed inside the previous screen's
hold and `s6` came out a duplicate of `s5`: ten seconds of the wrong screen under the voice, and
nothing failed. Every still now names its own timestamp in `raw-terminal.mov`, so that class of bug
cannot come back silently.

**The dashboard replaces the phone clip as the closing evidence.** `evidence.mp4` is 276 frames,
9.2 s, and the two outro stills cover the remaining 8.2 s of the 17.3 s beat — the body and the
outro show the same image, so the seam does not read. That puts all three spoken lines on top of
it: *"CALL-E does not dial Argentina"*,
*"lands on a US Twilio number"*, *"bridged to a real phone, recorded and transcribed"*. The clip it
replaces showed the caller ID unmasked and the phone's home screen, and repeated what the opening
already shows better.

Frame counts are asserted, and they are the whole point: `terminal.mp4` must be 4254 and
`evidence.mp4` 276, because a drift of one frame slides the entire video against the voice and
`build-video.sh` absorbs it into `RATIO` without complaining.

## 7. Assembling

`out/timing.txt` has the per-beat lengths and it is the only source for the numbers below. Re-run
`build-audio.sh` only if the narration changes: it wipes `out/`, `narration.voice.wav` included, and
then the holds in `mkbody.sh`, the cuts in `mkintro.sh` and every number here have to be redone. The
track sits at 177.9 s against a 180 s cap, so a new line means dropping one.

`mkbody.sh` already lays each still on its own beat length, so there is no `fit-to-audio.py` step
any more. Concatenate the opening onto the front and hand `build-video.sh` one clip:

```bash
printf "file 'intro.mov'\nfile 'raw-fitted.mov'\n" > video/out/intro-concat.txt
ffmpeg -y -f concat -safe 0 -i video/out/intro-concat.txt -c copy video/out/raw-with-intro.mov

VIDEO_DIR=$PWD/video END=169.7 \
  OUTRO="video/dashboard.png:4,video/closing.png:4.2" OUTRO_REPLACE=8.2 \
  bash ~/.claude/skills/personal-record-video/scripts/build-video.sh video/out/raw-with-intro.mov
```

**No `SLIDE`.** The arithmetic, all of it derivable from what is on disk: `narration.wav` is
177.9 s; `intro.mov` is 561 frames and `raw-fitted.mov` 4530, so the clip is 5091 frames =
**169.7 s**, which is `END`. `build-video.sh` fits at `RATIO = END / (A - OUTRO_REPLACE)`, and the
two closing stills cover the tail, so `OUTRO_REPLACE = 177.9 - 169.7 = 8.2` — exactly their combined
length, and `RATIO = 1.000`. **Read that line in the output.** Anything else and the cut slides
against the voice with nothing to catch it.

`TOTAL = A + max(0, OUTRO_TOTAL - OUTRO_REPLACE)` does not depend on `END`, so the video is pinned
to the length of `narration.wav` and nothing else. `intro.mov` has to be exactly 561 frames for the
same reason; `mkintro.sh` asserts that count and refuses to finish without it.

Out comes `video/out/demo.mp4` and `video/out/demo.en.srt`. Upload public or unlisted, never
private, with the SRT as the caption track. YouTube does not replace the file of a video that is
already up, so a new cut is a new URL: `README.md`, `docs/index.html` (twice), the pull request and
the Devpost submission all carry it.
