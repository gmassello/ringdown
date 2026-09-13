#!/usr/bin/env bash
# Shoots the stills that come off the published site instead of the terminal: the run view in
# its two scenarios, and the ledger widget clean and tampered. Everything on them is the real
# page — the ledger widget runs the same examples/ledger.example.jsonl through a port of
# audit.chain_checks, so it counts the 26 checks the narration counts. See "The site stills"
# in video/README.md.
set -e
cd "$(dirname "$0")/.."
[ -d /opt/homebrew/opt/ffmpeg@7/bin ] && PATH="/opt/homebrew/opt/ffmpeg@7/bin:$PATH"

CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
[ -x "$CHROME" ] || { echo "Google Chrome not found at $CHROME"; exit 1; }

BG=0x161826                 # the site's own --color-bg, so the still has no frame around it
PORT=${PORT:-8127}
VIEW=${VIEW:-1800,960}      # wide enough for the two columns side by side
SCALE=${SCALE:-2}
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"; [ -n "${SERVER:-}" ] && kill "$SERVER" 2>/dev/null' EXIT

cp -R docs/. "$WORK/"

# The page defaults to light, routes by hash and fills its widgets asynchronously. This forces
# the dark palette the rest of the video is cut in, strips the prose the stills do not need, and
# waits for the page to settle before the shot. ?click= presses one control first, ?hide= takes
# out whatever this particular shot should not carry.
cat >> "$WORK/index.html" <<'JS'
<script type="module">
const wanted = new URLSearchParams(location.search);
document.documentElement.dataset.rdTheme = "dark";
const css = document.createElement("style");
css.textContent = `
  #primer, [data-view] .shell > .card:first-child, footer, nav { display: none !important; }
  :focus, :focus-visible { outline: none !important; }
  [data-view] .shell { max-width: 1720px !important; padding-block: 36px 36px !important; }
  [data-view] p, [data-view] .src:not(.legend) { display: none !important; }
  [data-view] .legend { display: block !important; }
  ${(wanted.get("hide") || "").split("|").filter(Boolean).map((s) => `${s} { display: none !important; }`).join("\n")}
`;
document.head.append(css);
const settled = () => {
  const ledger = document.getElementById("ledger-body");
  return location.hash !== "#ledger" || !ledger.hidden;
};
while (!settled()) await new Promise((wake) => setTimeout(wake, 50));
for (const selector of (wanted.get("click") || "").split("|").filter(Boolean)) {
  document.querySelector(selector).click();
  await new Promise((wake) => setTimeout(wake, 2000));
}
document.title = "shot ready";
</script>
JS

python3 -m http.server "$PORT" --directory "$WORK" --bind 127.0.0.1 >/dev/null 2>&1 &
SERVER=$!
until curl -sf "http://127.0.0.1:$PORT/index.html" >/dev/null; do
  kill -0 "$SERVER" 2>/dev/null || { echo "the server on $PORT died — is the port taken?"; exit 1; }
  sleep 0.2
done
# a server that was already on this port would answer too, and the stills would be silently wrong
curl -s "http://127.0.0.1:$PORT/index.html" | grep -q 'shot ready' \
  || { echo "port $PORT is answering somebody else's page — set PORT"; exit 1; }

shoot() { # name view [click] [hide]
  local query="click=${3:-}&hide=${4:-}"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor="$SCALE" \
    --window-size="$VIEW" --virtual-time-budget=20000 --screenshot="$WORK/$1.png" \
    "http://127.0.0.1:$PORT/?$query#$2" >/dev/null 2>&1
  ffmpeg -y -loglevel error -i "$WORK/$1.png" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:$BG,setsar=1" \
    "video/$1.png"
  echo "wrote video/$1.png"
}

# The run view stacks the ladder, the spoken turns and the verification panels down one page;
# each still takes the one band its beat is about and hides the rest. Dropping every direct
# child of the ladder column that carries data-step-min takes the attempt panel out of any
# scenario without knowing its step numbers, and leaves the rung badges alone: those are
# .rung-state, one level deeper.
LADDER='%23call|[data-scenario-panel]>.grid>div:last-child|[data-scenario-panel]>.grid>div:first-child>[data-step-min]|[data-scenario-panel]>.grid>div:first-child>.legend'
TURNS='%23call-audio|[data-scenario-panel]'

shoot run-ladder     run     ''                        "$LADDER"
shoot run-turns      run     ''                        "$TURNS"
shoot run-noclock    run     '[data-scenario="case"]'  "$LADDER"
shoot ledger-clean   ledger
shoot ledger-tampered ledger '%23tamper-btn'
