#!/usr/bin/env bash
# Regenerates the three stills: slide.png (opening), dashboard.png (from a screenshot passed as $1)
# and closing.png. How to get that screenshot: see "The dashboard still" in video/README.md.
set -e
cd "$(dirname "$0")/.."
[ -d /opt/homebrew/opt/ffmpeg@7/bin ] && PATH="/opt/homebrew/opt/ffmpeg@7/bin:$PATH"
F=/System/Library/Fonts/HelveticaNeue.ttc
BG=0x0e131f
INK=0xf2f5fa
DIM=0x9fb3c8
FAINT=0x5b7085
GO=0x4ade80

line() { printf "drawtext=fontfile=$F:text='%s':fontcolor=%s:fontsize=%s:x=(w-tw)/2:y=%s" "$1" "$2" "$3" "$4"; }
card() { ffmpeg -y -loglevel error -f lavfi -i color=$BG:s=1920x1080 -frames:v 1 -vf "$2" "$1"; echo "wrote $1"; }

card video/slide.png "\
$(line 'Ringdown' $INK 132 130),\
$(line 'Every on-call system reports it sent the notification' $DIM 46 330),\
$(line 'The push landed on a silenced phone' $FAINT 38 450),\
$(line 'The page was read at 3am and forgotten' $FAINT 38 508),\
$(line 'Nobody checked whether anyone answered' $FAINT 38 566),\
$(line 'An on-call escalation agent that phones the pager holder' $DIM 44 700),\
$(line 'and proves the acknowledgement happened' $GO 44 760),\
$(line 'CALL-E REST + MCP      Python stdlib      zero dependencies' $FAINT 32 910)"

card video/closing.png "\
$(line 'Notification sent proves nothing.' $INK 62 300),\
$(line 'A commitment has an owner and a clock.' $GO 62 385),\
$(line 'Six calls to the live provider — the second channel could never read one back.' $DIM 34 600),\
$(line 'github.com/gmassello/ringdown' $GO 44 830)"

[ -n "${1:-}" ] || { echo "no screenshot given, keeping video/dashboard.png"; exit 0; }

# Crops the header, the row and the transcript down to the acknowledgement. Tuned to a
# 1505x812 window-mode screenshot of /calls with the details expanded.
ffmpeg -y -loglevel error -i "$1" -vf "\
crop=1200:790:150:20,scale=-1:900,pad=1920:1080:(ow-iw)/2:150:$BG,\
$(line 'The agent called a US Twilio number. It rang a phone in Argentina.' $DIM 40 60)" \
video/dashboard.png
echo "wrote video/dashboard.png"
