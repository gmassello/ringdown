from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

E164 = r"^\+[1-9]\d{7,14}$"
TWILIO_API_BASE = "https://api.twilio.com/"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    twilio_account_sid: str
    twilio_auth_token: str
    twilio_number: str = Field(pattern=E164)
    forward_to: str = Field(pattern=E164)
    public_base_url: str
    dashboard_password: str
    database_url: str = "sqlite:///calls.db"
    enable_recording: bool = True
    enable_transcription: bool = True
    transcription_language: str = "en-US"
    validate_twilio_signature: bool = True

    @field_validator("public_base_url")
    @classmethod
    def _rooted_origin(cls, raw: str) -> str:
        parts = urlsplit(raw.rstrip("/"))
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise ValueError(f"public_base_url must be http(s)://host, got {raw!r}")
        if parts.path or parts.query or parts.fragment:
            raise ValueError(
                f"public_base_url must carry no path, query or fragment, got {raw!r}; "
                "the app is mounted at the root"
            )
        return f"{parts.scheme}://{parts.netloc}"

    def url_for(self, path: str) -> str:
        return f"{self.public_base_url}{path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def is_twilio_recording(url: str) -> bool:
    return url.startswith(TWILIO_API_BASE)
