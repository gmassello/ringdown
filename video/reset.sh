#!/usr/bin/env bash
# Demo state for the recording. Idempotent. --check reports without changing anything.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/apps/python/ringdown"
RECEIVER="$ROOT/apps/python/calle-receiver"
LOG="$ROOT/video/demo.log"
REAL_CALL="CAdaccf857c1ee7fa6c84de56151bff993"

fail=0
ok()  { printf '  \033[32m[ok]\033[0m   %s\n' "$1"; }
bad() { printf '  \033[31m[BAD]\033[0m  %s\n' "$1"; fail=1; }
hdr() { printf '\n\033[1m%s\033[0m\n' "$1"; }
holds() { grep -q "$1" "$LOG" && ok "$2" || bad "$3"; }

hdr "demo run"
[ "${1:-}" = "--check" ] || ( cd "$APP" && uv run python -m demo.run_local > "$LOG" 2>&1 )
if [ -s "$LOG" ]; then
  for want in "Scenario 1 " "Scenario 2 " "Scenario 4 " "Scenario 6 " "The ledger check"; do
    holds "^$want" "log has ${want% }" "log is missing ${want% }"
  done
  holds '^verified 11/11$' "scenario 2 verifies 11/11" "scenario 2 lost its 11/11"
  holds '^verified 6/10$'  "scenario 6 verifies 6/10"  "scenario 6 lost its 6/10"
  holds '^POST requests sent 2, calls created 1, people woken 1$' \
        "scenario 4 woke one person" "scenario 4 lost its reconciliation line"
  holds '^verified 26/26$' "the committed ledger verifies 26/26" "the committed ledger does not verify"
  holds '^verified 25/26$' "the tampered ledger fails 25/26" "the tampered ledger no longer fails"
else
  bad "no $LOG - run without --check first"
fi

hdr "the real bridged call"
if [ -f "$RECEIVER/calls.db" ]; then
  [ "$(sqlite3 "$RECEIVER/calls.db" \
      "select count(*) from call where call_sid='$REAL_CALL' and recording_url is not null;")" = "1" ] \
    && ok "calls.db holds $REAL_CALL with a recording" || bad "calls.db lost the real CALL-E call"
  seg=$(sqlite3 "$RECEIVER/calls.db" "select count(*) from transcriptsegment where call_sid='$REAL_CALL';")
  [ "${seg:-0}" -ge 3 ] && ok "it has $seg transcript segments" || bad "transcript segments are gone"
else
  bad "$RECEIVER/calls.db is missing - the dashboard shot has no data"
fi

hdr "toolchain"
[ -d /opt/homebrew/opt/ffmpeg@7/bin ] && PATH="/opt/homebrew/opt/ffmpeg@7/bin:$PATH"
[ "$(ffmpeg -filters 2>/dev/null | grep -c ' subtitles ')" -gt 0 ] \
  && ok "ffmpeg can burn in subtitles" || bad "ffmpeg has no libass (brew install ffmpeg@7)"

printf '\n'
[ $fail -eq 0 ] && printf '\033[32mall green - safe to record\033[0m\n' || printf '\033[31mnot ready\033[0m\n'
exit $fail
