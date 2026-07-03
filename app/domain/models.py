from dataclasses import dataclass, field
from typing import List, Dict, Any

from app.domain.enums import LogLevel, MatchOp, Direction


@dataclass(frozen=True)
class LogEntry:
    timestamp: int
    level: LogLevel
    message: str
    labels: dict[str, str] = field(default_factory=dict)
    trace_id: str | None = None
    span_id: str | None = None


@dataclass(frozen=True)
class LabelMatcher:
    name: str
    op: MatchOp
    value: str


@dataclass(frozen=True)
class LogQueryParams:
    matchers: List
    start_time_ns: int | None = None
    end_time_ns: int | None = None
    limit: int = 100
    direction: Direction = Direction.BACKWARD


@dataclass
class LokiStream:
    stream: Dict[str, str]
    values: List[List[str]]


@dataclass
class LokiQueryResponse:
    status: str = "success"
    data: Dict[str, Any] = field(default_factory=lambda: {"resultType": "streams", "result": []})

    @classmethod
    def create(cls, streams: List[LokiStream]) -> "LokiQueryResponse":
        return cls(
            status="success",
            data={
                "resultType": "streams",
                "result": [
                    {"stream": s.stream, "values": s.values} for s in streams
                ]
            }
        )