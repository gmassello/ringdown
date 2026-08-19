# The demo video

Everything except pressing record. Built with the `personal-record-video` skill; the scripts
live in `~/.claude/skills/personal-record-video/scripts/`.

| File | What |
| --- | --- |
| `narration.tsv` | The script. Edit this and nothing downstream survives |
| `reset.sh` | Demo state. `--check` reports without changing anything |
| `take.sh` | The shot list. Enter advances, one screen per beat after the slide |
| `slide.png` | Beat 1, the title card |
| `dashboard.png` | Beat 8, the real CALL-E call bridged to an Argentine phone |
| `out/` | Generated. `build-audio.sh` wipes it on every run |

## Before recording

```bash
bash video/reset.sh          # runs the demo and reports; --check to report only
```

All green or do not record. Run it in the same shell session, right before the take: it
warms `uv`, so the live `preview` in the first screen answers in ~80 ms instead of stalling
on camera while the venv is re-resolved.

## The take

Terminal window at 1280x800, `Cmd+Shift+5` in **window mode**, mic off.

```bash
bash video/take.sh
```

Seven screens, Enter between each: `preview` · scenario 1 · scenario 2 · scenario 4 ·
scenario 6 · the committed ledger · the tampered ledger. Hold ~4 s on each — the fit
compresses the waiting afterwards, so only the ORDER matters, not the pace. Scenario 2 is
the money shot: it has to be readable.

Save the recording as `video/raw.mov`.

## Assembling

The audio is already built and under the cap — `out/timing.txt` has the verdict and the
per-beat lengths, and it is the only source for the numbers below. Re-run `build-audio.sh`
only if the narration changes, and then redo `timing-noslide.txt`, the marks and the fit,
because it wipes `out/`. Every number in the command below moves with it.

Find the seven marks (the timestamp in `raw.mov` where each screen appears) from a
timestamped contact sheet, then:

```bash
VIDEO_DIR=$PWD/video python3 ~/.claude/skills/personal-record-video/scripts/fit-to-audio.py \
  video/raw.mov --beats <m1,m2,m3,m4,m5,m6,m7> --timing video/out/timing-noslide.txt

VIDEO_DIR=$PWD/video END=133.6 \
  SLIDE=video/slide.png SLIDE_DUR=18.7 \
  OUTRO="video/dashboard.png:17.2" OUTRO_REPLACE=17.2 \
  bash ~/.claude/skills/personal-record-video/scripts/build-video.sh video/out/raw-fitted.mov
```

Where those come from, all of them out of `out/timing.txt`: `SLIDE_DUR` is beat 1's length,
`OUTRO_REPLACE` is the last beat's, and `END` is what is left of the total for the recording
to cover — 18.7 + 133.6 + 17.2 = 169.5, the length of the track.

Out comes `video/out/demo.mp4` and `video/out/demo.en.srt`. Upload public or unlisted,
never private, with the SRT as the caption track.

## The dashboard still

Regenerating it needs the receiver running locally against its own `calls.db` — the Render
free tier wipes the database on every deploy, so production is empty. Basic Auth opens a
native dialog that blocks browser automation, so the shot was taken from a static copy
fetched with `curl -u`.
