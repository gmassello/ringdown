# The demo video

Everything except pressing record. Built with the `personal-record-video` skill; the scripts
live in `~/.claude/skills/personal-record-video/scripts/`.

| File | What |
| --- | --- |
| `narration.tsv` | The script. Edit this and nothing downstream survives |
| `mkstills.sh` | Regenerates the three stills. The closing line lives in the script |
| `mkintro.sh` | Regenerates the opening 18.7 s and mixes the ringback under the voice |
| `mkbody.sh` | Rebuilds the body: the seven terminal stills plus the dashboard as closing evidence |
| `reset.sh` | Demo state for the terminal take. `--check` reports without changing anything |
| `take.sh` | The shot list. Enter advances, one screen per beat after the opening |
| `slide.png` | The opening card. No longer in the video — `mkintro.sh` replaced it. Poster and thumbnail |
| `dashboard.png` | First closing still: the real call, recorded and transcribed |
| `closing.png` | Last still: the thesis, what the live provider answered, the repo |
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

## 5. The body

`mkbody.sh` rebuilds `out/raw-fitted.mov` — the 142.6 s between the opening and the outro:

```bash
bash video/mkbody.sh          # -> out/frames/s6.png, out/terminal.mp4, out/evidence.mp4, out/raw-fitted.mov
```

Two things it fixes.

**`s6.png` is regenerated from the recording, not taken from the fit.** The mark handed to
`fit-to-audio.py` landed inside the previous screen's hold, so `s6` came out a duplicate of `s5`:
ten seconds of `verified 6/10 · exit 40` while the voice says *"Every verdict is sealed into a
hash-chained ledger / Twenty-six checks pass"*. The right screen is in `raw-terminal.mov` at
`LEDGER_AT=36`; the crop lands the text where the other six stills put it.

**The dashboard replaces the phone clip as the closing evidence.** It now runs from 2:32 to 2:45
— 13.2 s instead of 4, because the body and the outro show the same image and the seam does not
read. That puts all three spoken lines on top of it: *"CALL-E does not dial Argentina"*,
*"lands on a US Twilio number"*, *"bridged to a real phone, recorded and transcribed"*. The clip it
replaces showed the caller ID unmasked and the phone's home screen, and repeated what the opening
already shows better.

Frame counts are asserted, and they are the whole point: `terminal.mp4` must be 4002 and
`evidence.mp4` 277, because a drift of one frame slides the entire video against the voice and
`build-video.sh` absorbs it into `RATIO` without complaining.

## 6. Assembling

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

printf "file 'intro.mov'\nfile 'raw-fitted.mov'\n" > video/out/intro-concat.txt
ffmpeg -y -f concat -safe 0 -i video/out/intro-concat.txt -c copy video/out/raw-with-intro.mov

VIDEO_DIR=$PWD/video END=161.3 \
  OUTRO="video/dashboard.png:4,video/closing.png:4.2" OUTRO_REPLACE=8.2 \
  bash ~/.claude/skills/personal-record-video/scripts/build-video.sh video/out/raw-with-intro.mov
```

**No `SLIDE`.** The intro is concatenated onto the front of the screencast instead, so the whole
161.3 s goes through the fit as one clip: `RATIO = 161.3 / (169.5 - 8.2) = 1.000`.

The arithmetic, all of it out of `out/timing.txt`: the track is 169.5 s and beat 1 is 18.7 s,
so the recording covers beats 2 to 8 = 150.8 s. The two closing stills cover the tail, so
`OUTRO_REPLACE = 4 + 4.2` and `END = 18.7 + 150.8 - 8.2 = 161.3`. Beat 8 is 17.2 s, so the phone
keeps `17.2 - 8.2 = 9` of them.

`TOTAL = A + max(0, OUTRO_TOTAL - OUTRO_REPLACE)` does not depend on `END`, so the video is pinned
to the length of `narration.wav` and nothing else. What `END` does control is the fit — and if
`intro.mov` is not exactly 561 frames the whole screencast slides against the voice, silently.
`mkintro.sh` asserts that count and refuses to finish without it. Under ~3.5 s a still cannot be read; adjust the split once the
footage exists.

Out comes `video/out/demo.mp4` and `video/out/demo.en.srt`. Upload public or unlisted, never
private, with the SRT as the caption track.
