from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Call(SQLModel, table=True):
    call_sid: str = Field(primary_key=True)
    from_number: str
    to_number: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    status: str
    recording_url: str | None = None


class TranscriptSegment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    call_sid: str = Field(index=True)
    track: str
    text: str
    confidence: float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
