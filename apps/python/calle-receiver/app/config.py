from pydantic import Field
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


settings = Settings()
