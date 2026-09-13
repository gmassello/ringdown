#!/usr/bin/env bash
# Builds out/call.mp4: the real call of 2026-08-20, the phone that rang beside the words that
# were actually said. The footage is phone.mov and the turns come from the provider's own
# transcript, placed at their own offset_seconds — so the spacing between lines is the spacing
# that happened. Two clocks, and they are not the same one: see "The real call" in
# video/README.md. Frame counts are asserted; a drift of one slides the video against the voice.
set -e
cd "$(dirname "$0")/.."
[ -d /opt/homebrew/opt/ffmpeg@7/bin ] && PATH="/opt/homebrew/opt/ffmpeg@7/bin:$PATH"

OUT=video/out
STAGE=$OUT/call
PHONE=video/phone.mov
F=/System/Library/Fonts/HelveticaNeue.ttc
BG=0x0e131f
INK=0xf2f5fa
DIM=0x9fb3c8
FAINT=0x5b7085
GO=0x4ade80

# The call is answered at second 66 of the footage: the phone's own timer reads 00:37 at 103.
# Every offset below is the transcript's, and ANSWER + offset is where it lands in the footage.
ANSWER=66

# The phone's screen inside the 774x1692 recording, and the band the caller ID scrolls through.
SCREEN="crop=620:1370:77:135,delogo=x=1:y=222:w=618:h=138"
MASK="drawtext=fontfile=$F:text='+1********44':fontcolor=$DIM:fontsize=52:x=(w-tw)/2:y=252"
# The Dynamic Island on its own — the home screen underneath it never enters the frame.
ISLAND="crop=600:121:88:155,delogo=x=125:y=21:w=255:h=87"
# Once answered the island shrinks to a pill and the tops of the home screen icons come up
# under it, so this band is shorter. The pill carries the timer, not the number.
PILL="crop=600:98:88:155"

ENC="-c:v libx264 -preset medium -crf 19 -profile:v high -level 4.0 -pix_fmt yuv420p -fps_mode cfr -r 30 -an"

RING_FRAMES=120     # it rings
ANSWERED_FRAMES=90  # answered: the pill counts 0:01 to 0:04, before the call screen comes up
FIRST_FRAMES=660    # offsets 5 to 27: the greeting, the wrong name, and the right one
LAST_FRAMES=540     # offsets 45 to 63: takes the incident, and names a number of minutes
ENDED_FRAMES=180    # Call ended — a held frame, because the home screen returns 1.7 s later
TOTAL_FRAMES=$((RING_FRAMES + ANSWERED_FRAMES + FIRST_FRAMES + LAST_FRAMES + ENDED_FRAMES))

mkdir -p "$STAGE"

# offset | who | line 1 | line 2 | aside
FIRST_TURNS=(
  "2|agent|and this call is recorded.|Am I speaking with German Massello?"
  "11|german|Yes. This is Sharma.|"
  "12|agent|The identity doesn't match German Massello.|"
  "14|agent|I need to check if Sharma|can get German Massello."
  "17|agent|May I speak with German Massello?|"
  "22|german|Yes. I am.|"
  "24|agent|I apologize for the mix-up.|"
)
LAST_TURNS=(
  "46|german|Yes. I'm banking this incident right now.||he said taking. the provider heard banking"
  "47|agent|Let me confirm your acknowledgment.|How many minutes until you are working it?"
  "58|german|K. Give me 15 minutes, please.|"
)

# drawtext text lives inside single quotes, where every other character is literal, but a
# straight apostrophe would close them. The curly one is the same word, rendered the way
# the site already renders it.
esc() { printf '%s' "${1//\'/’}"; }

text() { # x y size colour content [enable]
  printf "drawtext=fontfile=%s:text='%s':fontcolor=%s:fontsize=%s:x=%s:y=%s%s" \
    "$F" "$(esc "$5")" "$4" "$3" "$1" "$2" \
    "${6:+:enable='gte(t,$6)'}"
}

# The panel: a header, then one turn after another, each appearing at its own offset and staying.
panel() { # start_offset label turns...
  local start="$1" label="$2"; shift 2
  local y=140 chain
  chain="$(text 660 64 30 "$FAINT" '20 August 2026 · the call, as it was transcribed')"
  chain="$chain,$(text 660 104 28 "$FAINT" "$label")"
  local turn
  for turn in "$@"; do
    IFS='|' read -r offset who one two aside <<< "$turn"
    local at=$(python3 -c "print(max(0.0, $offset - $start))")
    local colour=$DIM size=34
    [ "$who" = german ] && colour=$INK
    chain="$chain,$(text 660 "$y" 24 "$FAINT" "$who" "$at")"
    chain="$chain,$(text 800 "$y" "$size" "$colour" "$one" "$at")"
    y=$((y + 46))
    if [ -n "$two" ]; then
      chain="$chain,$(text 800 "$y" "$size" "$colour" "$two" "$at")"
      y=$((y + 46))
    fi
    if [ -n "$aside" ]; then
      chain="$chain,$(text 800 "$y" 26 "$FAINT" "$aside" "$at")"
      y=$((y + 38))
    fi
    y=$((y + 26))
  done
  printf '%s' "$chain"
}

compose() { # name frames input... phone_filter overlay_xy [panel_chain]
  local name="$1" frames="$2"; shift 2
  local inputs=() ; while [ "$1" != "--" ]; do inputs+=("$1"); shift; done; shift
  ffmpeg -y -loglevel error -f lavfi -i "color=$BG:s=1920x1080:r=30" "${inputs[@]}" \
    -frames:v "$frames" -filter_complex \
    "[1:v]$1,setsar=1[ph];[0:v][ph]overlay=$2:shortest=0[base];[base]${3:-null},format=yuv420p[v]" \
    -map "[v]" $ENC "$STAGE/$name.mp4"
}

shot() { # name frames seek phone_filter overlay_xy [panel_chain]
  compose "$1" "$2" -ss "$3" -i "$PHONE" -- "$4" "$5" "${6:-}"
}

# "Call ended" is on screen for 1.7 s before the home screen comes back, and the home screen
# never enters this video. So the last shot is one frame of it, held.
frozen() { # name frames seek phone_filter overlay_xy [panel_chain]
  ffmpeg -y -loglevel error -ss "$3" -i "$PHONE" -frames:v 1 "$STAGE/$1.png"
  compose "$1" "$2" -loop 1 -framerate 30 -i "$STAGE/$1.png" -- "$4" "$5" "${6:-}"
}

shot ring "$RING_FRAMES" 62 \
  "$ISLAND,scale=1740:-2:flags=lanczos" "(W-w)/2:(H-h)/2"

shot answered "$ANSWERED_FRAMES" 66.4 \
  "$PILL,scale=1740:-2:flags=lanczos" "(W-w)/2:(H-h)/2"

# The call screen is only up from footage 71, which is offset 5. Both the seek and the panel's
# base move together, so a turn still lands at the same second of the finished video.
shot first "$FIRST_FRAMES" "$((ANSWER + 5))" \
  "$SCREEN,$MASK,scale=-2:1000:flags=lanczos" "90:40" \
  "$(panel 5 'from the first ring' "${FIRST_TURNS[@]}")"

shot last "$LAST_FRAMES" "$((ANSWER + 45))" \
  "$SCREEN,$MASK,scale=-2:1000:flags=lanczos" "90:40" \
  "$(panel 45 'twenty seconds later' "${LAST_TURNS[@]}")"

frozen ended "$ENDED_FRAMES" 150.6 \
  "$SCREEN,$MASK,scale=-2:1000:flags=lanczos" "90:40" \
  "$(text 660 140 44 "$GO" 'Eighty-two seconds.'),$(text 660 200 34 "$DIM" 'One incident, and somebody who said they had it.')"

: > "$STAGE/concat.txt"
for n in ring answered first last ended; do echo "file '$n.mp4'" >> "$STAGE/concat.txt"; done
ffmpeg -y -loglevel error -f concat -safe 0 -i "$STAGE/concat.txt" -c copy "$OUT/call.mp4"

count() { ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames \
  -of default=nw=1:nk=1 "$1"; }
C=$(count "$OUT/call.mp4")
[ "$C" = "$TOTAL_FRAMES" ] || { echo "call.mp4 has $C frames, expected $TOTAL_FRAMES"; exit 1; }

echo "wrote $OUT/call.mp4  $C frames  $(echo "scale=3; $C/30" | bc) s"
