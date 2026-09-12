from urllib.parse import urlencode

import pytest
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_engine
from app.models import Call, TranscriptSegment


def test_incoming_call_returns_twiml_and_persists(client):
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
    for path in ("/voice/status", "/voice/recording", "/voice/transcription"):
        assert f"https://example.test{path}" in resp.text
    assert "example.test//" not in resp.text
    with Session(get_engine()) as session:
        call = session.get(Call, "CA123")
        assert call is not None
        assert call.status == "ringing"


@pytest.mark.parametrize(("duration", "expected"), [("42", 42), ("unknown", None)])
def test_status_callback_closes_call(client, create_call, duration, expected):
    sid = f"CAstatus{duration}"
    create_call(sid)
    resp = client.post(
        "/voice/status",
        data={"CallSid": sid, "DialCallStatus": "completed", "DialCallDuration": duration},
    )
    assert resp.status_code == 200
    with Session(get_engine()) as session:
        call = session.get(Call, sid)
        assert call.status == "completed"
        assert call.duration_seconds == expected
        assert call.ended_at is not None


def test_recording_callback_saves_url(client, create_call):
    create_call("CArec")
    client.post(
        "/voice/recording",
        data={"CallSid": "CArec", "RecordingUrl": "https://api.twilio.com/rec/RE1"},
    )
    with Session(get_engine()) as session:
        call = session.get(Call, "CArec")
        assert call.recording_url == "https://api.twilio.com/rec/RE1"


def test_transcription_content_saves_segment(client, create_call):
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
    with Session(get_engine()) as session:
        segments = session.exec(
            select(TranscriptSegment).where(TranscriptSegment.call_sid == "CAtrans")
        ).all()
        assert len(segments) == 1
        assert segments[0].text == "hello there"
        assert segments[0].confidence == 0.93


def test_signature_rejected_when_enabled(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "validate_twilio_signature", True)
    resp = client.post("/voice", data={"CallSid": "CA999"})
    assert resp.status_code == 403


def test_signature_accepted_when_valid(client, monkeypatch):
    from twilio.request_validator import RequestValidator

    settings = get_settings()
    monkeypatch.setattr(settings, "validate_twilio_signature", True)
    params = {"CallSid": "CAsigned", "From": "+15550000001", "To": "+15550000002"}
    signature = RequestValidator(settings.twilio_auth_token).compute_signature(
        f"{settings.public_base_url}/voice", params
    )
    resp = client.post("/voice", data=params, headers={"X-Twilio-Signature": signature})
    assert resp.status_code == 200


def test_signature_accepted_when_the_webhook_carries_a_query_string(client, monkeypatch):
    from twilio.request_validator import RequestValidator

    settings = get_settings()
    monkeypatch.setattr(settings, "validate_twilio_signature", True)
    params = {"CallSid": "CAtagged", "From": "+15550000001", "To": "+15550000002"}
    signature = RequestValidator(settings.twilio_auth_token).compute_signature(
        settings.url_for("/voice") + "?env=prod", params
    )
    resp = client.post(
        "/voice", params={"env": "prod"}, data=params, headers={"X-Twilio-Signature": signature}
    )
    assert resp.status_code == 200


def test_signature_accepted_when_twilio_repeats_a_form_key(client, monkeypatch):
    from starlette.datastructures import FormData
    from twilio.request_validator import RequestValidator

    settings = get_settings()
    monkeypatch.setattr(settings, "validate_twilio_signature", True)
    sent = [("CallSid", "CArepeated"), ("From", "+15550000001"), ("To", "+15550000002"),
            ("SpeechResult", "first"), ("SpeechResult", "second")]
    signature = RequestValidator(settings.twilio_auth_token).compute_signature(
        settings.url_for("/voice"), FormData(sent)
    )
    resp = client.post(
        "/voice",
        content=urlencode(sent),
        headers={
            "X-Twilio-Signature": signature,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    assert resp.status_code == 200


def test_transcription_malformed_data_is_ignored(client, create_call):
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
    with Session(get_engine()) as session:
        segments = session.exec(
            select(TranscriptSegment).where(TranscriptSegment.call_sid == "CAbadjson")
        ).all()
        assert segments == []


def test_no_handler_runs_on_the_event_loop():
    import inspect

    from app.routes import dashboard, voice

    handlers = [
        route.endpoint
        for router in (voice.router, dashboard.router)
        for route in router.routes
    ]
    assert handlers
    assert not any(inspect.iscoroutinefunction(handler) for handler in handlers)
