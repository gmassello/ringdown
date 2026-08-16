import html

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlmodel import Session, col, select

from app.config import TWILIO_API_BASE, settings
from app.db import engine
from app.models import Call, TranscriptSegment
from app.security import dashboard_auth

router = APIRouter(dependencies=[Depends(dashboard_auth)])

HEADER = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>CALL-E Receiver</title>
<style>
body{font-family:-apple-system,system-ui,sans-serif;margin:2rem auto;max-width:1000px;padding:0 1rem;background:#0f1420;color:#e8ecf4}
h1{font-size:1.4rem}
h1 span{color:#8fa1c0;font-weight:400}
table{width:100%;border-collapse:collapse}
th,td{padding:.6rem .8rem;text-align:left;border-bottom:1px solid #2a3448;vertical-align:top}
th{color:#8fa1c0;font-weight:600;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em}
.ok{color:#4ade80}
.bad{color:#f87171}
details summary{cursor:pointer;color:#8fa1c0}
.seg{margin:.35rem 0;font-size:.9rem}
.track{display:inline-block;min-width:4.5rem;color:#8fa1c0;font-size:.72rem;text-transform:uppercase}
audio{width:230px;height:32px;vertical-align:middle}
.muted{color:#5b6b88}
</style>
<script>
setInterval(() => {
  if ([...document.querySelectorAll("audio")].every(a => a.paused)) location.reload();
}, 5000);
</script>
</head>
<body>
<h1>CALL-E Receiver <span>&mdash; inbound calls</span></h1>
<table>
<tr><th>Started (UTC)</th><th>From &rarr; To</th><th>Status</th><th>Duration</th><th>Recording</th><th>Transcript</th></tr>
"""

EMPTY_ROW = '<tr><td colspan="6" class="muted">No calls yet.</td></tr>'
STATUS_CLASS = {"completed": "ok", "failed": "bad"}


def _row(call: Call, segments: list[TranscriptSegment]) -> str:
    duration = f"{call.duration_seconds}s" if call.duration_seconds is not None else "&mdash;"
    audio = (
        f'<audio controls preload="none" src="/calls/{html.escape(call.call_sid)}/recording.mp3"></audio>'
        if call.recording_url
        else '<span class="muted">&mdash;</span>'
    )
    if segments:
        lines = "".join(
            f'<div class="seg"><span class="track">{html.escape(seg.track.removesuffix("_track"))}</span>'
            f"{html.escape(seg.text)}</div>"
            for seg in segments
        )
        transcript = f"<details><summary>{len(segments)} segments</summary>{lines}</details>"
    else:
        transcript = '<span class="muted">&mdash;</span>'
    return (
        "<tr>"
        f"<td>{call.started_at.isoformat(sep=' ', timespec='seconds')}</td>"
        f"<td>{html.escape(call.from_number)} &rarr; {html.escape(call.to_number)}</td>"
        f'<td class="{STATUS_CLASS.get(call.status, "")}">{html.escape(call.status)}</td>'
        f"<td>{duration}</td>"
        f"<td>{audio}</td>"
        f"<td>{transcript}</td>"
        "</tr>"
    )


@router.get("/calls", response_class=HTMLResponse)
def dashboard() -> str:
    with Session(engine) as session:
        calls = session.exec(select(Call).order_by(col(Call.started_at).desc()).limit(50)).all()
        segments = session.exec(
            select(TranscriptSegment)
            .where(col(TranscriptSegment.call_sid).in_([call.call_sid for call in calls]))
            .order_by(col(TranscriptSegment.created_at))
        ).all()
    by_call: dict[str, list[TranscriptSegment]] = {}
    for seg in segments:
        by_call.setdefault(seg.call_sid, []).append(seg)
    rows = "".join(_row(call, by_call.get(call.call_sid, [])) for call in calls) or EMPTY_ROW
    return HEADER + rows + "</table></body></html>"


@router.get("/calls/{call_sid}/recording.mp3")
def recording(call_sid: str) -> Response:
    with Session(engine) as session:
        call = session.get(Call, call_sid)
    if call is None or not (call.recording_url or "").startswith(TWILIO_API_BASE):
        raise HTTPException(status_code=404, detail="No recording for this call")
    upstream = requests.get(
        f"{call.recording_url}.mp3",
        auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        timeout=30,
    )
    upstream.raise_for_status()
    return Response(
        upstream.content,
        media_type="audio/mpeg",
        headers={"Cache-Control": "private, max-age=3600"},
    )
