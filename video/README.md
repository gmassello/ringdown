# The demo video

Everything except pressing record. Built with the `personal-record-video` skill; the scripts
live in `~/.claude/skills/personal-record-video/scripts/`.

| File | What |
| --- | --- |
| `narration.tsv` | The script. Edit this and nothing downstream survives |
| `mkstills.sh` | Regenerates the three stills. The closing line lives in the script |
| `mkintro.sh` | Regenerates the opening 18.7 s and mixes the ringback under the voice |
| `mkbody.sh` | Rebuilds the body: one still per beat, then the real call |
| `mksite.sh` | Shoots the four stills that come off the published site. Needs Chrome |
| `mkcall.sh` | Builds the real call: the phone that rang beside the words that were said |
| `reset.sh` | Demo state for the terminal take. `--check` reports without changing anything |
| `take.sh` | The shot list. Enter advances, one screen per beat after the opening |
| `slide.png` | The opening card. No longer in the video — `mkintro.sh` replaced it. Poster and thumbnail |
| `dashboard.png` | The receiver's card for the real call. No longer in the video — the call itself closes it now |
| `closing.png` | The last still: the thesis, what the live provider answered, the repo |
| `run-ladder.png` | `#run` — the incident and who is on call, in order |
| `run-turns.png` | `#run` — the three things she said, each quoted |
| `run-noclock.png` | `#run` scenario 2 — `NO_ETA`, and the next rung acknowledged |
| `ledger-clean.png` | `#ledger` as published. `exit 0`, 26 checks |
| `ledger-tampered.png` | The same widget after `#tamper-btn`. `exit 40`, every seal still green |
| `live/` | The live call: run files, pre-flight, evidence capture. Gitignored |
| `out/` | Generated. `build-audio.sh` wipes it on every run, `narration.voice.wav` included |

`docs/demo.gif`, the animation at the top of the root README, comes from none of this. It is
captured off the published site, not off a terminal take: the `#ledger` section at
<https://gmassello.github.io/ringdown/#ledger>, with `#tamper-btn` and the `verify` card lifted
into a fixed full-bleed container so the screenshot needs no cropping, three states — clean,
button focused, tampered — grabbed with `screencapture` at 2.5x and assembled by `ffmpeg`
(`concat`, then `palettegen` with `stats_mode=full`, which the red of `exit 40` needs).

Two recordings feed one video, and both reach it. `raw-terminal.mov` (the CLI) is down to one
screen: everything it used to carry is now shot off the published site, which is written to be
read rather than parsed. `phone.mov` (the phone ringing) carries the opening **and** the last
fifty-three seconds — see "The real call" below. Wherever it appears the caller ID is masked,
and the home screen underneath it never enters the frame.

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
the first screen answers in ~80 ms instead of stalling on camera. Eight screens, Enter between
each: `preview` · scenario 1 · scenario 2 · the mapping file · scenario 4 · scenario 6 · the
committed ledger · the tampered ledger. Hold ~4 s on each — only the ORDER matters, since every
screen is pulled out as a still at an explicit mark afterwards.

**The current cut uses one of them**, scenario 4 at `mark:29`; the rest of the body comes off the
published site. The whole take is still worth having: the marks in `mkbody.sh` are timestamps
into this file, so any screen can come back into the edit without recording again.

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

## 5. The site stills

Four of the six screens in the body are photographs of <https://gmassello.github.io/ringdown/>.
Everything on them is the real page: `#ledger` runs the committed `examples/ledger.example.jsonl`
through a port of `audit.chain_checks`, so it counts the 26 checks the narration counts, and
`#run` is the same ladder the app resolves.

```bash
bash video/mksite.sh          # -> run-ladder, run-turns, run-noclock, ledger-clean, ledger-tampered
```

It serves a copy of `docs/` on loopback rather than shooting `file://`, because the widgets need
`fetch` and `crypto.subtle`, and appends a module that forces the dark palette (the page ships
`data-rd-theme="light"`), strips the prose a still does not need, waits for the page to settle,
and presses one control — `#tamper-btn`, or a scenario tab — before the shot. Two query
parameters drive it: `click` and `hide`.

The run view stacks the ladder, the spoken turns and the verification panels down one page, so
each still takes the one band its beat is about. Dropping every **direct** child of the ladder
column that carries `data-step-min` removes the attempt panel in any scenario without knowing
that scenario's step numbers, and leaves the rung badges alone — those are `.rung-state`, a level
deeper. `select(tab)` in `docs/app.js` already paints the panel at its last step, so one click is
enough and `paintStep`, which is private to the module, never has to be reached.

`VIEW` and `SCALE` are the knobs. Each new shot is calibrated by looking at **one** capture: the
height comes from seeing it, not from arithmetic, and the bottom ~110 px stays empty because that
is where the burned-in subtitles land. The shot is padded to 1920x1080 on `#161826`, the site's
own background, so the still carries no frame around it.

`docs/demo.gif` is the same widget captured the same way, by hand — see the note at the top.

## 6. The real call

The last fifty-three seconds are the call of **2026-08-20 01:42 UTC**
(`call_zU0ikLWrqToX6vl0cYGfCA`, 80 s by the provider's clock): the phone ringing on the left, and
on the right the turns the provider transcribed, each appearing at its own `offset_seconds`.

```bash
bash video/mkcall.sh          # -> out/call.mp4, 1590 frames
```

**It is that call and no other.** The three calls placed on 2026-09-13 were never filmed, so
their transcripts are not put beside this footage: that would be claiming two different calls are
one.

**Two clocks, and they are not the same one.** The phone's timer counts the Twilio leg; the
transcript offsets count the CALL-E leg, which starts a second or two later. The anchor —
`ANSWER=66` — was read off the phone's own timer, which shows `00:37` at footage second 103. So
the spacing between lines is real and the alignment is within a couple of seconds. It is not
frame-accurate and nothing here depends on it being.

The call runs 67 s of conversation into a 53 s beat, so there is **a cut, and it is visible**:
the first segment ends at offset 27, the next begins at 45, the phone's timer jumps, and the
panel says `twenty seconds later`. The narration talks over it — every line of it names what has
just appeared on the right, and the longest silence anywhere in the video is 3.3 s. An earlier cut
left the voice out of this beat entirely and twenty-five seconds of dead air read as a broken
file, not as a pause. One line carries an aside, because the provider transcribed
*taking* as *banking* and a viewer would otherwise read it as our typo.

**The home screen never enters this video**, and the phone spends five seconds on its way to
making that hard. The block opens on the Dynamic Island alone, at the geometry `mkintro.sh`
already uses. Then the call is answered and the island shrinks to a pill, so from footage 66 to
71 the tops of the app icons and the weather widget come up underneath it — a shorter band,
`PILL`, crops them out while the pill counts `0:01` to `0:04`. Only at footage 71 is the
full-screen call UI up, and that is where the phone-and-transcript layout starts.

That last part is why the seek and the panel's base offset move **together**: `first` seeks to
`ANSWER + 5` and the panel counts from offset 5, so a turn still lands at the same second of the
finished video as it did when the segment began three seconds earlier.

`Call ended` is a **held frame**: it is on screen for 1.7 s before the home screen returns.

Masking: the caller ID scrolls as a marquee across a fixed band, so `delogo` covers the band and
`+1********44` — what `incident.mask_phone` would print — is drawn over it.

## 7. The body

`mkbody.sh` rebuilds `out/raw-fitted.mov` — the 149.1 s between the opening and the outro:

```bash
bash video/mkbody.sh          # -> out/frames/, out/terminal.mp4, out/raw-fitted.mov
```

`SCREENS` is the whole edit: one `source | hold` per beat, in order, where a source is either a
PNG or `mark:N`, a timestamp in `raw-terminal.mov`. The holds are the beat lengths straight out
of `out/timing.txt`; only the ledger beat is split, across its two states. Five of the six are
site stills and one is the terminal, which is the point: the video shows the page because the
page is readable, and shows the terminal once because the thing underneath is a program.

**Why the marks are explicit.** A mark handed to `fit-to-audio.py` once landed inside the
previous screen's hold and a still came out a duplicate of the one before it: ten seconds of the
wrong screen under the voice, and nothing failed. Every screen now names its own timestamp.

Frame counts are asserted, and they are the whole point: `terminal.mp4` must be 2883 and
`call.mp4` 1590, because a drift of one frame slides the entire video against the voice and
`build-video.sh` absorbs it into `RATIO` without complaining.

## 8. Assembling

`out/timing.txt` has the per-beat lengths and it is the only source for the numbers below.

**Re-run `build-audio.sh` only if `narration.tsv` changes** — it wipes `out/`,
`narration.voice.wav` included, and then the holds in `mkbody.sh`, the frame counts in
`mkcall.sh` and every number here have to be redone:

```bash
VIDEO_DIR=$PWD/video bash ~/.claude/skills/personal-record-video/scripts/build-audio.sh
```

The **first five rows of `narration.tsv` are load-bearing**: they are beat 1, `mkintro.sh` cuts
its six phone shots to that beat's 18.7 s, and it asserts 561 frames. Change a word in them and
the opening has to be re-cut by hand. Everything from row six down is free.

`mkbody.sh` already lays each still on its own beat length, so there is no `fit-to-audio.py` step.
Concatenate the opening onto the front and hand `build-video.sh` one clip:

```bash
printf "file 'intro.mov'\nfile 'raw-fitted.mov'\n" > video/out/intro-concat.txt
ffmpeg -y -f concat -safe 0 -i video/out/intro-concat.txt -c copy video/out/raw-with-intro.mov

VIDEO_DIR=$PWD/video END=167.8 OUTRO="video/closing.png:7.7" OUTRO_REPLACE=7.7 \
  bash ~/.claude/skills/personal-record-video/scripts/build-video.sh video/out/raw-with-intro.mov
```

**No `SLIDE`.** The arithmetic, all of it derivable from what is on disk: `narration.wav` is
175.5 s; `intro.mov` is 561 frames and `raw-fitted.mov` 4473, so the clip is 5034 frames =
**167.8 s**, which is `END`. `build-video.sh` fits at `RATIO = END / (A - OUTRO_REPLACE)`, and the
closing still covers the tail, so `OUTRO_REPLACE = 175.5 - 167.8 = 7.7` — the length of the last
beat, and `RATIO = 1.000`. **Read that line in the output.** Anything else and the cut
slides against the voice with nothing to catch it.

`TOTAL = A + max(0, OUTRO_TOTAL - OUTRO_REPLACE)` does not depend on `END`, so the video is pinned
to the length of `narration.wav` and nothing else. `intro.mov` has to be exactly 561 frames for
the same reason; `mkintro.sh` asserts that count and refuses to finish without it.

Out comes `video/out/demo.mp4` (2:55.5) and `video/out/demo.en.srt`. Upload public or unlisted,
never private, with the SRT as the caption track. YouTube does not replace the file of a video
that is already up, so a new cut is a new URL: `README.md`, `docs/index.html` (twice, where the
running time is printed beside it), the pull request and the Devpost submission all carry it.
