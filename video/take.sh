#!/usr/bin/env bash
# The shot list. Enter advances. Everything on screen is real output of a real run.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/video/demo.log"
PREVIEW='python -m ringdown preview --incident examples/incident.example.json --rotation examples/rotation.example.json'
cd "$ROOT/apps/python/ringdown"

gate() { read -r; clear; }
cmd()  { printf '\033[1;36m$ %s\033[0m\n\n' "$1"; }
show() { awk -v want="$1" '/^(Scenario |The ledger check)/ { cur = $0 } cur ~ want' "$LOG"; }

clear
cmd "$PREVIEW"
uv run $PREVIEW
gate

cmd 'python -m demo.run_local'
show '^Scenario 1 '
gate

show '^Scenario 2 '
gate

show '^Scenario 4 '
gate

show '^Scenario 6 '
gate

show '^The ledger check' | sed '/tampered/,$d'
gate

show '^The ledger check' | sed -n '/tampered/,$p'
gate
