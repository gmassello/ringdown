from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.models import Call, TranscriptSegment
from app.routes.dashboard import HEADER, _call_card

router = APIRouter()

BANNER = (
    '<div class="call"><div class="empty">'
    "This is the sample call, not the inbound log. It is written into the page rather than the "
    "database, so it survives a redeploy and carries no recording, no real number and nothing "
    "anybody said. The live dashboard is at <span class=\"mono\">/calls</span> and stays behind a "
    "password, because that one prints what the caller actually dialled and what they actually said."
    "</div></div>"
)

STARTED = datetime(2026, 8, 20, 1, 13, 44, tzinfo=UTC)

CALL = Call(
    call_sid="CAdemo0000000000000000000000000001",
    from_number="+1********00",
    to_number="+54*********44",
    started_at=STARTED,
    ended_at=datetime(2026, 8, 20, 1, 14, 27, tzinfo=UTC),
    duration_seconds=43,
    status="completed",
    recording_url=None,
)

SPOKEN = [
    ("inbound_track", "This is an automated on-call page from Ringdown, and this call is recorded."),
    ("outbound_track", "Yes, this is German Massello."),
    ("inbound_track", "There is a p2 incident on checkout-api: checkout p99 latency above 3s."),
    ("inbound_track", "Are you taking this incident right now?"),
    ("outbound_track", "Yes, I am taking this incident right now."),
    ("inbound_track", "How many minutes until you are working the incident?"),
    ("outbound_track", "Give me fifteen minutes."),
]

SEGMENTS = [
    TranscriptSegment(
        id=index,
        call_sid=CALL.call_sid,
        track=track,
        text=text,
        confidence=0.94,
        created_at=STARTED,
    )
    for index, (track, text) in enumerate(SPOKEN, start=1)
]


@router.get("/demo", response_class=HTMLResponse)
def demo() -> str:
    return HEADER + BANNER + _call_card(CALL, SEGMENTS) + "</div></body></html>"
