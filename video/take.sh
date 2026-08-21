#!/usr/bin/env bash
# The shot list. Everything on screen is real output of a real run.
# Enter advances, or set DWELL=<seconds> to advance on its own.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/video/demo.log"
PREVIEW='python -m ringdown preview --incident examples/incident.example.json --rotation examples/rotation.example.json'
cd "$ROOT/apps/python/ringdown"

dwell() { [ -n "${DWELL:-}" ] && sleep "$DWELL" || read -r; }
gate() { dwell; clear; }
cmd()  { printf '\033[1;36m$ %s\033[0m\n\n' "$1"; }
show()  { awk -v want="$1" '/^(Scenario |The ledger check)/ { cur = $0 } cur ~ want' "$LOG"; }
scene() { show "$1" | awk 'NR<=2; /^\[[0-9]+\// { on=1; print "" } on'; }

clear
cmd "$PREVIEW"
uv run $PREVIEW
gate

cmd 'python -m demo.run_local'
scene '^Scenario 1 '
gate

scene '^Scenario 2 '
gate

scene '^Scenario 4 '
gate

scene '^Scenario 6 '
gate

show '^The ledger check' | sed '/tampered/,$d'
gate

show '^The ledger check' | sed -n '/tampered/,$p'
dwell
