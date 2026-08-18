from sqlalchemy import event
from sqlmodel import create_engine

from app.config import settings

engine = create_engine(
    settings.database_url, connect_args={"check_same_thread": False, "timeout": 10}
)


@event.listens_for(engine, "connect")
def _enable_wal(connection, _record):
    connection.execute("PRAGMA journal_mode=WAL")
