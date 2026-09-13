#!/usr/bin/env bash
# Rebuilds out/raw-fitted.mov: one still per beat, then the real call. Most of the stills come
# off the published site, which is written to be read; one comes out of raw-terminal.mov at an
# explicit mark, so there is still a terminal in the video. The holds are the beat lengths in
# out/timing.txt and the frame counts are asserted — a drift of one slides the whole video
# against the voice and nothing else would catch it. See "The body" in video/README.md.
set -e
cd "$(dirname "$0")/.."
[ -d /opt/homebrew/opt/ffmpeg@7/bin ] && PATH="/opt/homebrew/opt/ffmpeg@7/bin:$PATH"

OUT=video/out
FRAMES=$OUT/frames
BG=0x0e131f
SRC=video/raw-terminal.mov

# The terminal content box inside the 3248x1972 recording, and the letterbox that fits it
# to 1080p. Re-measure both if the window geometry of the take ever changes.
CROP="crop=3019:1565:111:218,scale=1920:996:flags=lanczos,pad=1920:1080:0:42:$BG,setsar=1"

# source | hold, in order. mark:N is a timestamp in raw-terminal.mov, landing in that screen's
# settled state and never on a transition. Holds are beat lengths from out/timing.txt; the
# ledger beat (21.4) is the one split across two screens.
SCREENS=(
  "video/run-ladder.png|17.2"       # what    — the incident and who is on call
  "video/run-turns.png|19.6"        # picks   — the three things she said
  "video/run-noclock.png|29.3"      # noclock — a yes with no clock, and the next rung
  "mark:29|8.6"                     # twice   — asked twice, rang once
  "video/ledger-clean.png|10.0"     # ledger  — sealed
  "video/ledger-tampered.png|11.4"  # ledger  — resealed, and still wrong
)

STILL_FRAMES=2883
ENC="-c:v libx264 -preset medium -crf 20 -profile:v high -level 4.0 -pix_fmt yuv420p -fps_mode cfr -r 30 -an"

mkdir -p "$FRAMES"
: > "$OUT/terminal.txt"
n=0
for screen in "${SCREENS[@]}"; do
  n=$((n + 1))
  source="${screen%%|*}"; hold="${screen##*|}"
  if [ "${source%%:*}" = mark ]; then
    ffmpeg -y -loglevel error -ss "${source##*:}" -i "$SRC" -frames:v 1 -vf "$CROP" "$FRAMES/s$n.png"
  else
    [ -f "$source" ] || { echo "$source is missing — run video/mksite.sh"; exit 1; }
    cp "$source" "$FRAMES/s$n.png"
  fi
  printf "file 'frames/s%s.png'\nduration %s\n" "$n" "$hold" >> "$OUT/terminal.txt"
done
printf "file 'frames/s%s.png'\n" "$n" >> "$OUT/terminal.txt"

ffmpeg -y -loglevel error -f concat -safe 0 -i "$OUT/terminal.txt" -frames:v "$STILL_FRAMES" \
  -vf "fps=30,scale=1920:1080,setsar=1,format=yuv420p" $ENC "$OUT/terminal.mp4"

[ -f "$OUT/call.mp4" ] || { echo "$OUT/call.mp4 is missing — run video/mkcall.sh"; exit 1; }

printf "file 'terminal.mp4'\nfile 'call.mp4'\n" > "$OUT/parts.txt"
ffmpeg -y -loglevel error -f concat -safe 0 -i "$OUT/parts.txt" -c copy "$OUT/raw-fitted.mov"

count() { ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames \
  -of default=nw=1:nk=1 "$1"; }

T=$(count "$OUT/terminal.mp4")
[ "$T" = "$STILL_FRAMES" ] || { echo "terminal.mp4 has $T frames, expected $STILL_FRAMES"; exit 1; }
CALL=$(count "$OUT/call.mp4")
R=$(count "$OUT/raw-fitted.mov")
[ "$R" = "$((STILL_FRAMES + CALL))" ] || {
  echo "raw-fitted.mov has $R frames, expected $((STILL_FRAMES + CALL))"; exit 1; }

echo "wrote $n stills into $FRAMES"
echo "wrote $OUT/raw-fitted.mov  $R frames  $(echo "scale=3; $R/30" | bc) s"
