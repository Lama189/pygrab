from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.domain.enums import LogLevel


@dataclass(frozen=True)
class LogEntry:
    timestamp: int
    level: LogLevel
    message: str
    labels: dict[str, str] = field(default_factory=dict)
    trace_id: str | None = None
    span_id: str | None = None