#!/usr/bin/env bash
# Cuts docs/demo.gif out of the finished cut. Defaults to the whole real call: the phone
# ringing, the answer, the name it gets wrong, the two questions, and "Call ended". Knobs are
# environment variables; the size it prints is the number that decides whether it ships.
set -e
cd "$(dirname "$0")/.."
[ -d /opt/homebrew/opt/ffmpeg@7/bin ] && PATH="/opt/homebrew/opt/ffmpeg@7/bin:$PATH"

SRC=${SRC:-video/out/demo.mp4}
START=${START:-114.9}
DUR=${DUR:-52.7}
WIDTH=${WIDTH:-900}
FPS=${FPS:-15}
STATS=${STATS:-diff}
OUT=${OUT:-docs/demo.gif}

[ -f "$SRC" ] || { echo "$SRC is gone. build-audio.sh wipes video/out/ — rebuild before cutting."; exit 1; }

# The outro replaces the last 7.7s, so anything past 167.76 is closing.png, not the phone.
PALETTE=$(mktemp -t rdgif).png
CHAIN="fps=$FPS,scale=$WIDTH:-1:flags=lanczos"

ffmpeg -y -loglevel error -ss "$START" -t "$DUR" -i "$SRC" \
  -vf "$CHAIN,palettegen=stats_mode=$STATS" "$PALETTE"

ffmpeg -y -loglevel error -ss "$START" -t "$DUR" -i "$SRC" -i "$PALETTE" \
  -lavfi "$CHAIN[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" \
  -loop 0 "$OUT"

rm -f "$PALETTE"
ffprobe -v error -show_entries stream=width,height,nb_frames -show_entries format=duration,size \
  -of default=noprint_wrappers=1 "$OUT"
