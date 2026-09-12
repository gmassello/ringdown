import pytest
from pydantic import ValidationError

from app.config import Settings


def test_a_trailing_slash_never_reaches_a_callback_url():
    settings = Settings(public_base_url="https://relay.example.com/")

    assert settings.public_base_url == "https://relay.example.com"
    assert settings.url_for("/voice/status") == "https://relay.example.com/voice/status"


def test_a_base_url_with_a_path_is_refused_at_startup():
    with pytest.raises(ValidationError, match="no path, query or fragment"):
        Settings(public_base_url="https://relay.example.com/api")


def test_a_base_url_without_a_scheme_is_refused_at_startup():
    with pytest.raises(ValidationError, match="must be http"):
        Settings(public_base_url="relay.example.com")
