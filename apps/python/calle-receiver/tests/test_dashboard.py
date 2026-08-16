from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db import engine
from app.main import app
from app.models import Call

client = TestClient(app)
AUTH = ("dashboard", "testpass")


def test_dashboard_lists_call_with_transcript(create_call):
    create_call("CAdash1", from_number="+15550000009")
    client.post(
        "/voice/transcription",
        data={
            "CallSid": "CAdash1",
            "TranscriptionEvent": "transcription-content",
            "Track": "inbound_track",
            "TranscriptionData": '{"transcript": "dashboard test segment", "confidence": 0.9}',
        },
    )
    resp = client.get("/calls", auth=AUTH)
    assert resp.status_code == 200
    assert "+15550000009" in resp.text
    assert "dashboard test segment" in resp.text
    assert "<details>" in resp.text


def test_dashboard_requires_auth():
    assert client.get("/calls").status_code == 401
    assert client.get("/calls", auth=("dashboard", "wrong")).status_code == 401
    assert client.get("/calls/CAnope/recording.mp3").status_code == 401


def test_recording_proxy_404_without_recording(create_call):
    create_call("CAdash2")
    assert client.get("/calls/CAdash2/recording.mp3", auth=AUTH).status_code == 404
    assert client.get("/calls/CAnope/recording.mp3", auth=AUTH).status_code == 404


def test_recording_callback_ignores_non_twilio_url(create_call):
    create_call("CAdash3")
    client.post(
        "/voice/recording",
        data={"CallSid": "CAdash3", "RecordingUrl": "https://evil.example/steal-creds"},
    )
    with Session(engine) as session:
        assert session.get(Call, "CAdash3").recording_url is None
    assert client.get("/calls/CAdash3/recording.mp3", auth=AUTH).status_code == 404


def test_recording_proxy_rejects_non_twilio_url(create_call):
    create_call("CAdash4")
    with Session(engine) as session:
        call = session.get(Call, "CAdash4")
        call.recording_url = "https://evil.example/steal-creds"
        session.add(call)
        session.commit()
    assert client.get("/calls/CAdash4/recording.mp3", auth=AUTH).status_code == 404
