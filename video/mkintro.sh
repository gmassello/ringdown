#!/usr/bin/env bash
# Builds the opening 18.7 s: out/intro.mov (561 frames) and the ringback mixed under the
# voice. narration.voice.wav is the original take and narration.wav becomes derived, so this
# is safe to re-run. How the shots line up with the narration: "The opening" in video/README.md.
set -e
cd "$(dirname "$0")/.."
[ -d /opt/homebrew/opt/ffmpeg@7/bin ] && PATH="/opt/homebrew/opt/ffmpeg@7/bin:$PATH"

OUT=video/out
STAGE=$OUT/intro
PHONE=video/phone.mov
F=/System/Library/Fonts/HelveticaNeue.ttc
BG=0x0e131f
INK=0xf2f5fa
DIM=0x9fb3c8
FAINT=0x5b7085
GO=0x4ade80
BAD=0xf87171

SCREEN=crop=638:1384:68:128
ENC="-c:v libx264 -preset medium -crf 18 -profile:v high -level 4.0 -pix_fmt yuv420p -fps_mode cfr -r 30 -an"
BED=${BED:-0.11}
RING=${RING:-0.26}

mkdir -p "$STAGE"

line() { printf "drawtext=fontfile=$F:text='%s':fontcolor=%s:fontsize=%s:x=(w-tw)/2:y=%s" "$1" "$2" "$3" "$4"; }

phone_shot() { # name frames seek filter
  ffmpeg -y -loglevel error -ss "$3" -i "$PHONE" -frames:v "$2" \
    -vf "$4,setsar=1,fps=30,format=yuv420p" $ENC "$STAGE/$1.mp4"
}

card_shot() { # name frames filter
  ffmpeg -y -loglevel error -f lavfi -i "color=$BG:s=1920x1080:r=30" -frames:v "$2" \
    -vf "$3,setsar=1,format=yuv420p" $ENC "$STAGE/$1.mp4"
}

BAND="scale=1600:-2:flags=lanczos,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:$BG"

phone_shot 1 119 30 "crop=580:190:118:1300,$BAND,\
$(line 'notification sent' $GO 46 168),\
$(line 'delivered' $FAINT 30 232)"

card_shot 2 72 "$(line 'That proves nothing' $DIM 56 500)"

phone_shot 3 112 40 "crop=300:170:165:1290,$BAND"

card_shot 4 126 "$(line '3 AM' $INK 150 380),\
$(line 'read' $FAINT 40 590),\
$(line 'and forgotten' $FAINT 40 650)"

phone_shot 5 60 62 "crop=600:121:88:155,delogo=x=125:y=21:w=255:h=87,$BAND"

phone_shot 6 72 84 "crop=638:85:68:288,$BAND"

: > "$STAGE/concat.txt"
for n in 1 2 3 4 5 6; do echo "file '$n.mp4'" >> "$STAGE/concat.txt"; done
ffmpeg -y -loglevel error -f concat -safe 0 -i "$STAGE/concat.txt" -c copy "$OUT/intro.mov"

EXPR="0.5*(sin(2*PI*440*t)+sin(2*PI*480*t))*if(lt(t,14.3),$BED*lt(mod(t,6),2),if(lt(t,16.3),$RING,0))"
ffmpeg -y -loglevel error -f lavfi -i "aevalsrc='$EXPR':s=48000:d=18.7" \
  -c:a pcm_s16le -ar 48000 -ac 1 "$OUT/ring.wav"

[ -f "$OUT/narration.voice.wav" ] || cp "$OUT/narration.wav" "$OUT/narration.voice.wav"
ffmpeg -y -loglevel error -i "$OUT/narration.voice.wav" -i "$OUT/ring.wav" \
  -filter_complex "[0:a][1:a]amix=inputs=2:duration=longest:normalize=0[a]" \
  -map "[a]" -c:a pcm_s16le -ar 48000 -ac 1 "$OUT/narration.wav"

count() { ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames \
  -of default=nw=1:nk=1 "$1"; }
samples() { ffprobe -v error -show_entries stream=duration_ts -of default=nw=1:nk=1 "$1"; }

FRAMES=$(count "$OUT/intro.mov")
[ "$FRAMES" = 561 ] || { echo "intro.mov has $FRAMES frames, expected 561"; exit 1; }
RINGLEN=$(samples "$OUT/ring.wav")
[ "$RINGLEN" = 897600 ] || { echo "ring.wav has $RINGLEN samples, expected 897600"; exit 1; }
VOICELEN=$(samples "$OUT/narration.wav")
[ "$VOICELEN" = "$(samples "$OUT/narration.voice.wav")" ] || {
  echo "narration.wav changed length: $VOICELEN"; exit 1; }

echo "wrote $OUT/intro.mov  561 frames  18.700 s"
echo "wrote $OUT/narration.wav  voice + ring  ($VOICELEN samples)"
