#!/usr/bin/env bash
# Rebuilds out/raw-fitted.mov: the seven terminal stills, then the dashboard as the closing
# evidence. s6 comes straight out of raw-terminal.mov because the fit picked the wrong frame
# for it. Frame counts are asserted at the end — a drift of one slides the whole video
# against the voice and nothing else would catch it. See "The body" in video/README.md.
set -e
cd "$(dirname "$0")/.."
[ -d /opt/homebrew/opt/ffmpeg@7/bin ] && PATH="/opt/homebrew/opt/ffmpeg@7/bin:$PATH"

OUT=video/out
FRAMES=$OUT/frames
BG=0x0e131f
LEDGER_AT=${LEDGER_AT:-36}
TERMINAL_FRAMES=4002
BODY_FRAMES=277
ENC="-c:v libx264 -preset medium -crf 20 -profile:v high -level 4.0 -pix_fmt yuv420p -fps_mode cfr -r 30 -an"

ffmpeg -y -loglevel error -ss "$LEDGER_AT" -i video/raw-terminal.mov -frames:v 1 \
  -vf "crop=1782:1315:111:136,scale=1464:1080:flags=lanczos,pad=1920:1080:259:0:$BG,setsar=1" \
  "$FRAMES/s6.png"

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

echo "wrote $FRAMES/s6.png  the committed ledger, verified 26/26"
echo "wrote $OUT/raw-fitted.mov  $R frames  $(echo "scale=3; $R/30" | bc) s"
