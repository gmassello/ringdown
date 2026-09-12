import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session
from starlette.datastructures import FormData
from twilio.twiml.voice_response import Dial, Start, VoiceResponse

from app.config import get_settings, is_twilio_recording
from app.db import get_engine
from app.models import Call, TranscriptSegment
from app.security import twilio_form

router = APIRouter()
logger = logging.getLogger(__name__)


def _twiml(vr: VoiceResponse) -> Response:
    return Response(content=str(vr), media_type="application/xml")


@router.post("/voice")
def incoming_call(form: FormData = Depends(twilio_form)) -> Response:
    settings = get_settings()
    sid = form.get("CallSid", "")
    if not sid:
        logger.warning("a voice webhook arrived with no CallSid; the call is bridged but not stored")
    with Session(get_engine()) as session:
        if sid and session.get(Call, sid) is None:
            session.add(
                Call(
                    call_sid=sid,
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
            status_callback_url=settings.url_for("/voice/transcription"),
            language_code=settings.transcription_language,
            track="both_tracks",
            partial_results=False,
            transcription_engine="google",
        )
        vr.append(start)

    dial_kwargs = {
        "answer_on_bridge": True,
        "caller_id": settings.twilio_number,
        "action": settings.url_for("/voice/status"),
    }
    if settings.enable_recording:
        dial_kwargs.update(
            record="record-from-answer-dual",
            recording_status_callback=settings.url_for("/voice/recording"),
            recording_status_callback_event="completed",
        )

    dial = Dial(**dial_kwargs)
    dial.number(settings.forward_to)
    vr.append(dial)

    return _twiml(vr)


@router.post("/voice/status")
def call_status(form: FormData = Depends(twilio_form)) -> Response:
    with Session(get_engine()) as session:
        sid = form.get("CallSid", "")
        call = session.get(Call, sid)
        if call is None:
            logger.warning("status callback for %s, which this database does not know", sid)
        else:
            call.status = form.get("DialCallStatus") or form.get("CallStatus") or call.status
            call.ended_at = datetime.now(UTC)
            duration = form.get("DialCallDuration") or form.get("CallDuration")
            if duration and duration.isdigit():
                call.duration_seconds = int(duration)
            session.commit()
    return _twiml(VoiceResponse())


@router.post("/voice/recording")
def recording_completed(form: FormData = Depends(twilio_form)) -> Response:
    url = form.get("RecordingUrl", "")
    with Session(get_engine()) as session:
        sid = form.get("CallSid", "")
        call = session.get(Call, sid)
        if call is None:
            logger.warning("recording callback for %s, which this database does not know", sid)
        elif not is_twilio_recording(url):
            logger.warning("recording for %s is not hosted by Twilio; the url is dropped", sid)
        else:
            call.recording_url = url
            session.commit()
    return Response(status_code=204)


@router.post("/voice/transcription")
def transcription_event(form: FormData = Depends(twilio_form)) -> Response:
    if form.get("TranscriptionEvent") != "transcription-content":
        return Response(status_code=204)
    try:
        data = json.loads(form.get("TranscriptionData", "{}"))
    except json.JSONDecodeError:
        data = None
    if not isinstance(data, dict):
        logger.warning(
            "transcription for %s carried data this app cannot read; the segment is dropped",
            form.get("CallSid", ""),
        )
        return Response(status_code=204)
    text = data.get("transcript")
    confidence = data.get("confidence")
    with Session(get_engine()) as session:
        session.add(
            TranscriptSegment(
                call_sid=form.get("CallSid", ""),
                track=form.get("Track", ""),
                text=text if isinstance(text, str) else "",
                confidence=confidence if isinstance(confidence, (int, float)) else None,
            )
        )
        session.commit()
    return Response(status_code=204)
