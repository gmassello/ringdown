from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dashboard_lists_call_with_transcript():
    client.post(
        "/voice",
        data={"CallSid": "CAdash1", "From": "+15550000009", "To": "+15550000002"},
    )
    client.post(
        "/voice/transcription",
        data={
            "CallSid": "CAdash1",
            "TranscriptionEvent": "transcription-content",
            "Track": "inbound_track",
            "TranscriptionData": '{"transcript": "dashboard test segment", "confidence": 0.9}',
        },
    )
    resp = client.get("/calls")
    assert resp.status_code == 200
    assert "+15550000009" in resp.text
    assert "dashboard test segment" in resp.text
    assert "<details>" in resp.text


def test_recording_proxy_404_without_recording():
    client.post(
        "/voice",
        data={"CallSid": "CAdash2", "From": "+15550000008", "To": "+15550000002"},
    )
    assert client.get("/calls/CAdash2/recording.mp3").status_code == 404
    assert client.get("/calls/CAnope/recording.mp3").status_code == 404
