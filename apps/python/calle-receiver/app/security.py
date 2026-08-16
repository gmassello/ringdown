from urllib.parse import urljoin

from fastapi import HTTPException, Request
from starlette.datastructures import FormData
from twilio.request_validator import RequestValidator

from app.config import settings

_validator = RequestValidator(settings.twilio_auth_token)


async def twilio_form(request: Request) -> FormData:
    form = await request.form()
    if settings.validate_twilio_signature:
        url = urljoin(settings.public_base_url, request.url.path)
        signature = request.headers.get("X-Twilio-Signature", "")
        if not _validator.validate(url, dict(form), signature):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    return form
