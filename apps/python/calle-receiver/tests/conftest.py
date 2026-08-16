import os
import tempfile

os.environ.update(
    {
        "TWILIO_ACCOUNT_SID": "ACtest",
        "TWILIO_AUTH_TOKEN": "testtoken",
        "TWILIO_NUMBER": "+15550000000",
        "FORWARD_TO": "+5491100000000",
        "PUBLIC_BASE_URL": "https://example.test",
        "VALIDATE_TWILIO_SIGNATURE": "false",
        "DATABASE_URL": f"sqlite:///{tempfile.mkdtemp()}/calls.db",
    }
)
