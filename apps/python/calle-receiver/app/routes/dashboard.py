import html

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from sqlmodel import Session, col, select

from app.config import get_settings, is_twilio_recording
from app.db import get_engine
from app.models import Call, TranscriptSegment
from app.security import dashboard_auth

router = APIRouter(dependencies=[Depends(dashboard_auth)])

HEADER = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CALL-E Receiver</title>
<style>
:root{
  color-scheme:dark;
  --bg:#161826;--surface:#232532;--text:#e9e9ed;--accent:#9184d9;
  --divider:color-mix(in srgb,#e9e9ed 16%,transparent);
  --n300:#cfd3e5;--n500:#9397ab;--n600:#75798c;--n900:#292b31;
  --bad:#f87171;--radius:14px;
  --mono:ui-monospace,SFMono-Regular,Menlo,monospace;
}
*,*::before,*::after{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
  font-family:Inter,system-ui,-apple-system,sans-serif;font-size:15px;line-height:1.55}
.shell{max-width:1000px;margin:0 auto;padding:clamp(28px,5vw,56px) clamp(16px,4vw,32px)}
h1{font-weight:500;font-size:clamp(24px,3.4vw,34px);letter-spacing:-0.03em;margin:0}
.kicker{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--n500);margin-bottom:10px}
.head{display:flex;flex-wrap:wrap;align-items:baseline;gap:12px;margin-bottom:clamp(24px,4vw,36px)}
.live{margin-left:auto;font-size:12px;color:var(--n500)}
.call{background:var(--surface);border-radius:var(--radius);
  box-shadow:0 0 0 1px #3f424d;overflow:hidden;margin-bottom:16px}
.meta{padding:clamp(18px,3vw,26px);display:grid;
  grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:18px;
  border-bottom:1px solid var(--divider)}
.label{font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase;
  color:var(--n500);margin-bottom:7px}
.mono{font-family:var(--mono);font-size:14px}
.ok{color:#d2cefd}
.bad{color:var(--bad)}
.muted{color:var(--n600)}
.audio{padding:16px clamp(18px,3vw,26px);border-bottom:1px solid var(--divider)}
audio{width:100%;max-width:340px;height:36px;vertical-align:middle}
.segments{padding:clamp(18px,3vw,26px)}
summary{cursor:pointer;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--n500)}
.seg{display:flex;gap:clamp(10px,2vw,20px);align-items:baseline;margin-top:14px}
.track{flex:none;width:74px;font-family:var(--mono);font-size:11px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--n500)}
.inbound .track{color:#d2cefd}
.text{max-width:60ch}
.outbound .text{color:var(--n300)}
.empty{color:var(--n600);padding:clamp(18px,3vw,26px)}
</style>
<script>
setInterval(() => {
  if ([...document.querySelectorAll("audio")].every(a => a.paused)) location.reload();
}, 5000);
</script>
</head>
<body>
<div class="shell">
<div class="head">
<div>
<div class="kicker">CALL-E receiver &middot; inbound</div>
<h1>Calls</h1>
</div>
<div class="live">refreshing every 5s</div>
</div>
"""

EMPTY_ROW = '<div class="call"><div class="empty">No calls yet.</div></div>'
STATUS_CLASS = {"completed": "ok", "failed": "bad"}


def _meta(call: Call) -> str:
    duration = f"{call.duration_seconds}s" if call.duration_seconds is not None else "&mdash;"
    status_class = STATUS_CLASS.get(call.status, "")
    return (
        '<div class="meta">'
        f'<div><div class="label">started (UTC)</div>'
        f"<div>{call.started_at.isoformat(sep=' ', timespec='seconds')}</div></div>"
        f'<div><div class="label">from &rarr; to</div>'
        f'<div class="mono">{html.escape(call.from_number)} &rarr; '
        f"{html.escape(call.to_number)}</div></div>"
        f'<div><div class="label">status</div>'
        f'<div class="{status_class}">{html.escape(call.status)}</div></div>'
        f'<div><div class="label">duration</div><div>{duration}</div></div>'
        "</div>"
    )


def _audio(call: Call) -> str:
    if not is_twilio_recording(call.recording_url or ""):
        return ""
    return (
        '<div class="audio"><audio controls preload="none" '
        f'src="/calls/{html.escape(call.call_sid)}/recording.mp3"></audio></div>'
    )


def _segments(segments: list[TranscriptSegment]) -> str:
    if not segments:
        return '<div class="segments"><span class="muted">No transcript.</span></div>'
    lines = "".join(
        f'<div class="seg {html.escape(seg.track.removesuffix("_track"))}">'
        f'<span class="track">{html.escape(seg.track.removesuffix("_track"))}</span>'
        f'<span class="text">{html.escape(seg.text)}</span></div>'
        for seg in segments
    )
    return (
        '<div class="segments"><details open>'
        f"<summary>{len(segments)} segments</summary>{lines}"
        "</details></div>"
    )


def _call_card(call: Call, segments: list[TranscriptSegment]) -> str:
    return f'<div class="call">{_meta(call)}{_audio(call)}{_segments(segments)}</div>'


@router.get("/calls", response_class=HTMLResponse)
def dashboard() -> str:
    with Session(get_engine()) as session:
        calls = session.exec(select(Call).order_by(col(Call.started_at).desc()).limit(50)).all()
        segments = session.exec(
            select(TranscriptSegment)
            .where(col(TranscriptSegment.call_sid).in_([call.call_sid for call in calls]))
            .order_by(col(TranscriptSegment.created_at))
        ).all()
    by_call: dict[str, list[TranscriptSegment]] = {}
    for seg in segments:
        by_call.setdefault(seg.call_sid, []).append(seg)
    cards = "".join(_call_card(call, by_call.get(call.call_sid, [])) for call in calls) or EMPTY_ROW
    return HEADER + cards + "</div></body></html>"


@router.get("/calls/{call_sid}/recording.mp3")
def recording(call_sid: str) -> Response:
    with Session(get_engine()) as session:
        call = session.get(Call, call_sid)
    if call is None or not is_twilio_recording(call.recording_url or ""):
        raise HTTPException(status_code=404, detail="No recording for this call")
    settings = get_settings()
    try:
        upstream = requests.get(
            f"{call.recording_url}.mp3",
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            timeout=10,
            stream=True,
        )
        upstream.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="Twilio recording fetch failed") from exc
    return StreamingResponse(
        _stream(upstream),
        media_type="audio/mpeg",
        headers={"Cache-Control": "private, max-age=3600"},
    )


def _stream(upstream: requests.Response):
    try:
        yield from upstream.iter_content(chunk_size=65536)
    finally:
        upstream.close()
