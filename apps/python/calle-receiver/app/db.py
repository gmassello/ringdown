from functools import lru_cache

from sqlalchemy import event
from sqlmodel import create_engine

from app.config import get_settings


def _build_engine(url: str):
    if not url.startswith("sqlite"):
        return create_engine(url)
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 10})

    @event.listens_for(engine, "connect")
    def _enable_wal(connection, _record):
        connection.execute("PRAGMA journal_mode=WAL")

    return engine


@lru_cache
def get_engine():
    return _build_engine(get_settings().database_url)
