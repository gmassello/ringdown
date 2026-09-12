# Re-shoot the dashboard still and re-assemble the demo

Plan to run tomorrow. Written down in `docs/plan-still-dashboard.md`, next to
`plan-pre-deadline.md`. Nothing else is executed today.

## Context

`video/dashboard.png` is the first closing still of the demo video (2:50): it shows the receiver
dashboard with the real call received in Argentina. When `/calls` was redesigned from a table to
cards, the still was left showing the old interface. It is flagged as pending in `video/README.md`.

Opening the material surfaces two things that change the work:

**1. The still is not a loose image: it is an OUTRO of the assembly.** `video/README.md:113-118`
leaves the full command, with the numbers already derived from `out/timing.txt`:

```
END=142.6  SLIDE=video/slide.png SLIDE_DUR=18.7
OUTRO="video/dashboard.png:4,video/closing.png:4.2"  OUTRO_REPLACE=8.2
```

Changing the PNG does not touch the published `demo.mp4`. But **the expensive material is still on
disk**: `out/raw-fitted.mov` (the screencast already fitted to the audio), `out/narration.wav`,
`out/captions.srt`, `out/timing.txt` and `out/timing-noslide.txt`. So re-assembling is a single
command and **nothing has to be re-shot — not the terminal, not the phone, not the audio**.

**2. `mkstills.sh` does not reproduce the committed PNG.** For `dashboard.png` it does
`crop=1200:790:150:20`, `scale=-1:900`, `pad=1920:1080:…:150` and draws **a single** line at `y=60`,
which would leave the crop running from `y=150` to `y=1050`. The real PNG has the text at ~`y=267`,
the dashboard in a band of ~420 px and a `github.com/gmassello/ringdown` line in green that the
script does not draw. The artefact and its generator diverged, and the README declares the script to
be the way to regenerate it.

Desired result: the still shows the current dashboard with the numbers masked, `mkstills.sh`
produces it again exactly as committed, and `out/demo.mp4` is regenerated with it.

## Objective

A new `video/dashboard.png` (1920x1080, redesigned dashboard, masked numbers), a `mkstills.sh` that
regenerates it reproducibly, and `out/demo.mp4` re-assembled with the new still — without re-shooting
a single take.

## Assumptions

- **Masked numbers** (`+1********83 → +1********44`), decided in conversation. The dashboard prints
  whatever it has in the database, so the demo call is seeded already masked. The still ends up
  differing from today's published video in that detail.
- **The audio player is kept**, in the empty state as in the old still: the seeded call carries a
  `recording_url` from `api.twilio.com` (like `_with_recording` in
  `apps/python/calle-receiver/tests/test_dashboard.py:51`) so that `_audio()` renders the
  `<audio controls>`.
- Same content as the old still: the 2026-08-16 call, `completed`, `18s`, and the four segments
  (`This is a ring down test call…` / `Okay, is that there?` / `Thank you for your call.` /
  `The bridge.`).
- The composition replicates the current still, not the script's: context line on top
  (`The agent called a US Twilio number. It rang a phone in Argentina.`), dashboard in the middle,
  repo in green at the bottom.
- **Uploading the new video to YouTube is your call**, not part of this. The plan leaves `demo.mp4`
  ready.

## Rules from the `personal-record-video` skill that apply here

The skill (`~/Documents/dotfiles/claude-code/skills/personal-record-video/`) is used for the
assembly. Of its rules, the ones that touch this work:

- **`build-audio.sh` wipes the whole `video/out/`.** It is not run. That would be the expensive
  mistake of the day: it would take `raw-fitted.mov` with it and force redoing the fit against the
  beat marks. Only `build-video.sh` is run.
- **`SLIDE_DUR` must be exactly the length of beat 1** (18.7 s in `out/timing.txt`) and
  `OUTRO_REPLACE` the sum of the outros (8.2). The numbers are already in the README and do not
  change, because the new still occupies the same slot and the same duration.
- **`dashboard.png` is on screen for 4 s.** The skill warns that below ~3.5 s a still cannot be
  read, so 4 s is the floor: the framing has to favour legibility over showing everything. The new
  card helps (less dense than the table), but the crop should be tight.
- **libass**: without it, the subtitle filter fails at the very end of the whole encode. Check
  `ffmpeg -filters | grep " subtitles "` before assembling; if it is missing, `brew install ffmpeg@7`
  (the scripts prefer the keg on their own, and `mkstills.sh` already does).
- **The Chrome debugger banner does not apply here.** That is a problem of window-mode captures with
  `Cmd+Shift+5`; the still is taken with the MCP tool, which photographs only the page content, with
  no browser chrome.
- **Screenshots come back at a scale different from the viewport**, so the crop coordinates are
  derived from `getBoundingClientRect()`, never by measuring on the image.

## Steps

1. **Capture the new dashboard.** The method already documented in `video/README.md:91-94` and used
   when the redesign was implemented: the receiver running locally against its own `calls.db` in the
   scratchpad, seeded via `POST /voice` + four `POST /voice/transcription` + `POST /voice/status`,
   marking the `recording_url`, pulling the page down with `curl -u`, serving that static copy and
   photographing it with Chrome. The static copy exists because Basic Auth opens a native dialog that
   blocks automation. Window at 1280×800 via `resize_window`, as the skill requires.
2. **Derive the crop by measuring.** With `javascript_tool` against the served copy, read the
   `getBoundingClientRect()` of `.call` and of the header and compute `crop=w:h:x:y` from that. The
   old crop (`1200:790:150:20`, tuned to a 1505x812 window) does not work: the layout went from a
   wide table to a narrower, taller card.
3. **`video/mkstills.sh` — fix the `dashboard.png` block.** New `crop`, plus the three layers the
   still actually has: context line on top, scaled and centred crop via `pad`, and
   `github.com/gmassello/ringdown` in `$GO` at the bottom. The `line()` and `card()` helpers and the
   colour variables already in the script are reused. The generation of `slide.png` and
   `closing.png` is not touched.
4. **Regenerate `video/dashboard.png`**: `bash video/mkstills.sh <screenshot>`.
5. **Re-assemble the mp4** with the README command, without changing a single number:
   ```bash
   VIDEO_DIR=$PWD/video END=142.6 \
     SLIDE=video/slide.png SLIDE_DUR=18.7 \
     OUTRO="video/dashboard.png:4,video/closing.png:4.2" OUTRO_REPLACE=8.2 \
     bash ~/Documents/dotfiles/claude-code/skills/personal-record-video/scripts/build-video.sh \
       video/out/raw-fitted.mov
   ```
   `fit-to-audio.py` is not run: `raw-fitted.mov` is already made and the beat marks do not change.
6. **`video/README.md`** — remove the `**Shot before the dashboard was restyled** — re-shoot it
   before the next take` note from the `dashboard.png` row. The *The dashboard still* section
   describes the method correctly and stays as it is.

## Documentation

`video/README.md`, in step 6. Nothing else: no other doc describes the still. No Python code and no
site changes.

## Verification

- **`slide.png` and `closing.png` must not change**: `mkstills.sh` always regenerates them, so
  `git status video/` has to list `dashboard.png` as the only modified PNG.
- `dashboard.png` measures 1920x1080; open it with the image tool and look at it: whole card, the
  four segments legible, nothing cut off.
- **Masked numbers**: visual review, plus a `grep` over the captured HTML confirming no `+1832590`
  or `+1364365` is left.
- Run `mkstills.sh` twice against the same screenshot and compare `shasum` — proof that the script
  now reproduces the artefact.
- `out/demo.mp4` regenerated: duration ~2:49.5 (`out/timing.txt`), and watch the last 10 s to see
  the new still landing where the old one was. `ffprobe` for the duration, and extract a frame from
  the outro stretch to confirm it by eye.
- Legibility at 4 s: look at the extracted frame at phone size; if the segment text cannot be read,
  tighten the crop.
- Both suites stay green (297 + 19), even though no Python is touched.
- Shut down the receiver and the static server left running during the capture.

## Out of scope

- **Re-shooting takes**: terminal, phone and audio are reused as they are. `build-audio.sh` is not
  run (it would wipe `out/`), nor is `fit-to-audio.py`.
- **Uploading the video to YouTube.** The plan leaves `out/demo.mp4` and `out/demo.en.srt` ready.
- `slide.png`, `closing.png` and `thumbnail.png`: their content is still current.
- `narration.tsv` and the timings: the still occupies the same slot and the same duration.
- The live dashboard, the site and the two Python packages.

## Plain-language explanation

The demo video ends by showing a picture of the screen listing the calls received. That picture went
stale: it shows the screen as it used to be, a spreadsheet with rows and columns, and now that screen
has one card per call.

The picture is taken again: the program is started on the computer, the same call that appeared
before is loaded into it — same date, same 18 seconds, the same four sentences — and the new screen
is photographed. This time the phone numbers are masked, as was already done on the web page.

The good part is that **nothing has to be recorded again**: not the voice, not the screen, not the
phone. All that material was kept, so the picture is swapped and the video is rebuilt with a single
command. The result is a new file ready to upload; whether to upload it is up to you.

Along the way something quietly broken gets fixed: there is a file that is supposed to rebuild those
pictures automatically, and today it does not produce the one actually in use (it is missing the
bottom line with the repository address, and it frames things differently). Once fixed, asking it to
rebuild the picture returns exactly the one that goes into the video.

The risk of the day is written down and there is only one: there is a similar command
(`build-audio.sh`) that wipes the whole folder of generated material. If it is run by mistake, the
heavy work of syncing the video to the voice has to be redone. It is not run.
