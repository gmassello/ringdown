import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session
from starlette.datastructures import FormData
from twilio.twiml.voice_response import Dial, Start, VoiceResponse

from app.config import TWILIO_API_BASE, settings
from app.db import engine
from app.models import Call, TranscriptSegment
from app.security import twilio_form

router = APIRouter()


def _twiml(vr: VoiceResponse) -> Response:
    return Response(content=str(vr), media_type="application/xml")


@router.post("/voice")
async def incoming_call(form: FormData = Depends(twilio_form)) -> Response:
    with Session(engine) as session:
        if session.get(Call, form["CallSid"]) is None:
            session.add(
                Call(
                    call_sid=form["CallSid"],
                    from_number=form.get("From", ""),
                    to_number=form.get("To", ""),
                    status=form.get("CallStatus", "ringing"),
                )
            )
            session.commit()

    vr = VoiceResponse()

    if settings.enable_transcription:
        start = Start()
        start.transcription(
            status_callback_url=f"{settings.public_base_url}/voice/transcription",
            language_code=settings.transcription_language,
            track="both_tracks",
            partial_results=False,
            transcription_engine="google",
        )
        vr.append(start)

    dial_kwargs = {
        "answer_on_bridge": True,
        "caller_id": settings.twilio_number,
        "action": f"{settings.public_base_url}/voice/status",
    }
    if settings.enable_recording:
        dial_kwargs.update(
            record="record-from-answer-dual",
            recording_status_callback=f"{settings.public_base_url}/voice/recording",
            recording_status_callback_event="completed",
        )

    dial = Dial(**dial_kwargs)
    dial.number(settings.forward_to)
    vr.append(dial)

    return _twiml(vr)


@router.post("/voice/status")
async def call_status(form: FormData = Depends(twilio_form)) -> Response:
    with Session(engine) as session:
        call = session.get(Call, form.get("CallSid", ""))
        if call is not None:
            call.status = form.get("DialCallStatus") or form.get("CallStatus") or call.status
            call.ended_at = datetime.now(UTC)
            duration = form.get("DialCallDuration") or form.get("CallDuration")
            if duration is not None:
                call.duration_seconds = int(duration)
            session.commit()
    return _twiml(VoiceResponse())


@router.post("/voice/recording")
async def recording_completed(form: FormData = Depends(twilio_form)) -> Response:
    url = form.get("RecordingUrl", "")
    with Session(engine) as session:
        call = session.get(Call, form.get("CallSid", ""))
        if call is not None and url.startswith(TWILIO_API_BASE):
            call.recording_url = url
            session.commit()
    return Response(status_code=204)


@router.post("/voice/transcription")
async def transcription_event(form: FormData = Depends(twilio_form)) -> Response:
    if form.get("TranscriptionEvent") != "transcription-content":
        return Response(status_code=204)
    data = json.loads(form.get("TranscriptionData", "{}"))
    with Session(engine) as session:
        session.add(
            TranscriptSegment(
                call_sid=form.get("CallSid", ""),
                track=form.get("Track", ""),
                text=data.get("transcript", ""),
                confidence=data.get("confidence"),
            )
        )
        session.commit()
    return Response(status_code=204)
