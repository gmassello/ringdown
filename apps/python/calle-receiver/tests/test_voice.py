import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine
from app.main import app
from app.models import Call, TranscriptSegment

client = TestClient(app)


def test_incoming_call_returns_twiml_and_persists():
    resp = client.post(
        "/voice",
        data={"CallSid": "CA123", "From": "+15550000001", "To": "+15550000002"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/xml")
    assert "<Dial" in resp.text
    assert "+5491100000000" in resp.text
    assert "<Transcription" in resp.text
    assert 'record="record-from-answer-dual"' in resp.text
    with Session(engine) as session:
        call = session.get(Call, "CA123")
        assert call is not None
        assert call.status == "ringing"


@pytest.mark.parametrize(("duration", "expected"), [("42", 42), ("unknown", None)])
def test_status_callback_closes_call(create_call, duration, expected):
    sid = f"CAstatus{duration}"
    create_call(sid)
    resp = client.post(
        "/voice/status",
        data={"CallSid": sid, "DialCallStatus": "completed", "DialCallDuration": duration},
    )
    assert resp.status_code == 200
    with Session(engine) as session:
        call = session.get(Call, sid)
        assert call.status == "completed"
        assert call.duration_seconds == expected
        assert call.ended_at is not None


def test_recording_callback_saves_url(create_call):
    create_call("CArec")
    client.post(
        "/voice/recording",
        data={"CallSid": "CArec", "RecordingUrl": "https://api.twilio.com/rec/RE1"},
    )
    with Session(engine) as session:
        call = session.get(Call, "CArec")
        assert call.recording_url == "https://api.twilio.com/rec/RE1"


def test_transcription_content_saves_segment(create_call):
    create_call("CAtrans")
    client.post(
        "/voice/transcription",
        data={
            "CallSid": "CAtrans",
            "TranscriptionEvent": "transcription-content",
            "Track": "inbound_track",
            "TranscriptionData": '{"transcript": "hello there", "confidence": 0.93}',
        },
    )
    client.post(
        "/voice/transcription",
        data={"CallSid": "CAtrans", "TranscriptionEvent": "transcription-stopped"},
    )
    with Session(engine) as session:
        segments = session.exec(
            select(TranscriptSegment).where(TranscriptSegment.call_sid == "CAtrans")
        ).all()
        assert len(segments) == 1
        assert segments[0].text == "hello there"
        assert segments[0].confidence == 0.93


def test_signature_rejected_when_enabled(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "validate_twilio_signature", True)
    resp = client.post("/voice", data={"CallSid": "CA999"})
    assert resp.status_code == 403


def test_signature_accepted_when_valid(monkeypatch):
    from twilio.request_validator import RequestValidator

    from app.config import settings

    monkeypatch.setattr(settings, "validate_twilio_signature", True)
    params = {"CallSid": "CAsigned", "From": "+15550000001", "To": "+15550000002"}
    signature = RequestValidator(settings.twilio_auth_token).compute_signature(
        f"{settings.public_base_url}/voice", params
    )
    resp = client.post("/voice", data=params, headers={"X-Twilio-Signature": signature})
    assert resp.status_code == 200


def test_transcription_malformed_data_is_ignored(create_call):
    create_call("CAbadjson")
    for payload in ("not json", "42"):
        resp = client.post(
            "/voice/transcription",
            data={
                "CallSid": "CAbadjson",
                "TranscriptionEvent": "transcription-content",
                "Track": "inbound_track",
                "TranscriptionData": payload,
            },
        )
        assert resp.status_code == 204
    with Session(engine) as session:
        segments = session.exec(
            select(TranscriptSegment).where(TranscriptSegment.call_sid == "CAbadjson")
        ).all()
        assert segments == []
