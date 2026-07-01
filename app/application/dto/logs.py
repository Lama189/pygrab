from pydantic import BaseModel, Field


class LogEntryDTO(BaseModel):
    message: str
    level: str = "INFO"
    timestamp: int | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    trace_id: str | None = None
    span_id: str | None = None