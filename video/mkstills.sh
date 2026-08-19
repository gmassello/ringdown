#!/usr/bin/env bash
# Regenerates slide.png, and dashboard.png from a screenshot passed as $1.
# How to get that screenshot: see "The dashboard still" in video/README.md.
set -e
cd "$(dirname "$0")/.."
[ -d /opt/homebrew/opt/ffmpeg@7/bin ] && PATH="/opt/homebrew/opt/ffmpeg@7/bin:$PATH"
F=/System/Library/Fonts/HelveticaNeue.ttc

line() { printf "drawtext=fontfile=$F:text='%s':fontcolor=%s:fontsize=%s:x=(w-tw)/2:y=%s" "$1" "$2" "$3" "$4"; }

ffmpeg -y -loglevel error -f lavfi -i color=0x0e131f:s=1920x1080 -frames:v 1 -vf "\
$(line 'Ringdown' 0xf2f5fa 140 300),\
$(line 'An on-call escalation agent that phones the pager holder' 0x9fb3c8 48 520),\
$(line 'and proves the acknowledgement happened' 0x4ade80 48 595),\
$(line 'CALL-E REST + MCP      Python stdlib      zero dependencies' 0x5b7085 34 790)" \
video/slide.png
echo "wrote video/slide.png"

[ -n "${1:-}" ] || { echo "no screenshot given, keeping video/dashboard.png"; exit 0; }

# The crop keeps the header and the CALL-E row only. The second row is a manual test from a
# personal Argentine landline and stays out of the deliverable.
ffmpeg -y -loglevel error -i "$1" -vf "\
crop=1180:322:190:22,scale=1560:-1,pad=1920:1080:180:400:0x0e131f,\
$(line 'The agent called a US Twilio number. It rang a phone in Argentina.' 0x9fb3c8 42 250),\
$(line 'github.com/gmassello/ringdown' 0x4ade80 40 880)" \
video/dashboard.png
echo "wrote video/dashboard.png"
