import os
import tempfile

import pytest

os.environ.update(
    {
        "TWILIO_ACCOUNT_SID": "ACtest",
        "TWILIO_AUTH_TOKEN": "testtoken",
        "TWILIO_NUMBER": "+15550000000",
        "FORWARD_TO": "+5491100000000",
        "PUBLIC_BASE_URL": "https://example.test",
        "DASHBOARD_PASSWORD": "testpass",
        "VALIDATE_TWILIO_SIGNATURE": "false",
        "DATABASE_URL": f"sqlite:///{tempfile.mkdtemp()}/calls.db",
    }
)

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as running:
        yield running


@pytest.fixture
def create_call(client):
    def _create(sid: str, from_number: str = "+15550000001") -> None:
        client.post(
            "/voice",
            data={"CallSid": sid, "From": from_number, "To": "+15550000002"},
        )

    return _create
