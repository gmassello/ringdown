import requests
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


def _with_recording(
    sid: str, url: str = "https://api.twilio.com/2010-04-01/Recordings/RE1"
) -> None:
    with Session(engine) as session:
        call = session.get(Call, sid)
        call.recording_url = url
        session.add(call)
        session.commit()


def test_recording_proxy_rejects_non_twilio_url(create_call):
    create_call("CAdash4")
    _with_recording("CAdash4", url="https://evil.example/steal-creds")
    assert client.get("/calls/CAdash4/recording.mp3", auth=AUTH).status_code == 404


def test_recording_proxy_streams_the_upstream_audio(create_call, monkeypatch):
    create_call("CAdash5")
    _with_recording("CAdash5")

    class FakeUpstream:
        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            yield b"mp3-bytes"

        def close(self):
            pass

    seen = {}

    def fake_get(url, **kwargs):
        seen.update(url=url, **kwargs)
        return FakeUpstream()

    monkeypatch.setattr("app.routes.dashboard.requests.get", fake_get)
    resp = client.get("/calls/CAdash5/recording.mp3", auth=AUTH)

    assert resp.status_code == 200
    assert resp.content == b"mp3-bytes"
    assert resp.headers["content-type"] == "audio/mpeg"
    assert seen["url"].endswith(".mp3")
    assert seen["stream"] is True


def test_recording_proxy_reports_upstream_failure_as_502(create_call, monkeypatch):
    create_call("CAdash6")
    _with_recording("CAdash6")

    def fake_get(url, **kwargs):
        raise requests.Timeout("upstream timed out")

    monkeypatch.setattr("app.routes.dashboard.requests.get", fake_get)
    resp = client.get("/calls/CAdash6/recording.mp3", auth=AUTH)

    assert resp.status_code == 502
    assert "Twilio recording fetch failed" in resp.text
