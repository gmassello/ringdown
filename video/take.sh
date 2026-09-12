#!/usr/bin/env bash
# The shot list. Everything on screen is real output of a real run.
# Enter advances, or set DWELL=<seconds> to advance on its own.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/video/demo.log"
PREVIEW='python -m ringdown preview --incident examples/incident.example.json --rotation examples/rotation.example.json'
cd "$ROOT/apps/python/ringdown"

# the app reads os.environ, not .env; screen 3 needs GEMINI_API_KEY
[ -f .env ] && { set -a; . ./.env; set +a; }
[ -n "${GEMINI_API_KEY:-}" ] || { echo "GEMINI_API_KEY is not set: screen 3 shows the refusal, not a draft"; sleep 2; }

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

cmd 'cat examples/pagerduty-mapping.example.json'
cat examples/pagerduty-mapping.example.json
echo
cmd 'python -m ringdown adapt --payload examples/pagerduty.example.json --mapping examples/pagerduty-mapping.example.json'
uv run python -m ringdown adapt \
  --payload examples/pagerduty.example.json \
  --mapping examples/pagerduty-mapping.example.json | grep -E '"(id|severity|service|title)"'
echo
cmd 'python -m ringdown suggest-mapping --payload examples/opsgenie.example.json --out /tmp/drafted.json'
uv run python -m ringdown suggest-mapping \
  --payload examples/opsgenie.example.json --out /tmp/drafted.json
gate

scene '^Scenario 4 '
gate

scene '^Scenario 6 '
gate

show '^The ledger check' | sed '/tampered/,$d'
gate

show '^The ledger check' | sed -n '/tampered/,$p'
dwell
