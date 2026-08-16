import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from twilio.rest import Client

from app.config import settings


def main() -> None:
    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    call = client.calls.create(
        to=settings.forward_to,
        from_=settings.twilio_number,
        twiml="<Response><Say>Geographic permissions are working. This is the CALL-E receiver test.</Say></Response>",
    )
    print(f"Llamada creada: {call.sid} -> {settings.forward_to}")


if __name__ == "__main__":
    main()
