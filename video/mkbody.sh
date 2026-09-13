#!/usr/bin/env bash
# Rebuilds out/raw-fitted.mov: six terminal stills, the two ledger stills off the published
# site, then the dashboard as the closing evidence. Every terminal still is pulled straight out
# of raw-terminal.mov at an explicit mark, so the class of bug that made s6 a duplicate of s5
# cannot come back. Frame counts are asserted at the end — a drift of one slides the whole video
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

# One mark per still, each landing in that screen's settled state — never on the transition.
# s4 waits for the live model call to come back, which is why it is not 17.
MARKS=(3 7 13 24 29 35)
# s7 and s8 are the ledger beat, and they come off the published site rather than the terminal:
# the widget runs the same file through a port of audit.chain_checks, so it counts the same 26.
STILLS=(video/ledger-clean.png video/ledger-tampered.png)
# Beat lengths from out/timing.txt; the ledger beat (21.9) is split across s7 and s8.
HOLDS=(18.1 17.5 35.5 12.8 12.8 23.2 10.0 11.9)

TERMINAL_FRAMES=4254
BODY_FRAMES=276
ENC="-c:v libx264 -preset medium -crf 20 -profile:v high -level 4.0 -pix_fmt yuv420p -fps_mode cfr -r 30 -an"

mkdir -p "$FRAMES"
for i in "${!MARKS[@]}"; do
  ffmpeg -y -loglevel error -ss "${MARKS[$i]}" -i "$SRC" -frames:v 1 -vf "$CROP" \
    "$FRAMES/s$((i + 1)).png"
done
for i in "${!STILLS[@]}"; do
  [ -f "${STILLS[$i]}" ] || { echo "${STILLS[$i]} is missing — run video/mkledger.sh"; exit 1; }
  cp "${STILLS[$i]}" "$FRAMES/s$((${#MARKS[@]} + i + 1)).png"
done

: > "$OUT/terminal.txt"
for i in "${!HOLDS[@]}"; do
  printf "file 'frames/s%s.png'\nduration %s\n" "$((i + 1))" "${HOLDS[$i]}" >> "$OUT/terminal.txt"
done
printf "file 'frames/s%s.png'\n" "${#HOLDS[@]}" >> "$OUT/terminal.txt"

ffmpeg -y -loglevel error -f concat -safe 0 -i "$OUT/terminal.txt" -frames:v "$TERMINAL_FRAMES" \
  -vf "fps=30,scale=1920:1080,setsar=1,format=yuv420p" $ENC "$OUT/terminal.mp4"

ffmpeg -y -loglevel error -loop 1 -i video/dashboard.png -frames:v "$BODY_FRAMES" \
  -vf "scale=1920:1080,setsar=1,format=yuv420p" $ENC "$OUT/evidence.mp4"

printf "file 'terminal.mp4'\nfile 'evidence.mp4'\n" > "$OUT/parts.txt"
ffmpeg -y -loglevel error -f concat -safe 0 -i "$OUT/parts.txt" -c copy "$OUT/raw-fitted.mov"

count() { ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames \
  -of default=nw=1:nk=1 "$1"; }

T=$(count "$OUT/terminal.mp4")
[ "$T" = "$TERMINAL_FRAMES" ] || { echo "terminal.mp4 has $T frames, expected $TERMINAL_FRAMES"; exit 1; }
B=$(count "$OUT/evidence.mp4")
[ "$B" = "$BODY_FRAMES" ] || { echo "evidence.mp4 has $B frames, expected $BODY_FRAMES"; exit 1; }
R=$(count "$OUT/raw-fitted.mov")
[ "$R" = "$((TERMINAL_FRAMES + BODY_FRAMES))" ] || {
  echo "raw-fitted.mov has $R frames, expected $((TERMINAL_FRAMES + BODY_FRAMES))"; exit 1; }

echo "wrote ${#HOLDS[@]} stills into $FRAMES"
echo "wrote $OUT/raw-fitted.mov  $R frames  $(echo "scale=3; $R/30" | bc) s"
