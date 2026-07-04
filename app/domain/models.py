from dataclasses import dataclass, field, asdict
from typing import Any

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
    matchers: list
    start_time_ns: int | None = None
    end_time_ns: int | None = None
    limit: int = 100
    direction: Direction = Direction.BACKWARD


@dataclass
class LokiStream:
    stream: dict[str, str]
    values: list[list[str]]


@dataclass
class LokiQueryResponse:
    status: str = "success"
    data: dict[str, Any] = field(default_factory=lambda: {"resultType": "streams", "result": []})

    @classmethod
    def create(cls, streams: list[LokiStream]) -> "LokiQueryResponse":
        return cls(
            status="success",
            data={
                "resultType": "streams",
                "result": [
                    {"stream": s.stream, "values": s.values} for s in streams
                ]
            }
        )
    

@dataclass
class SpanEventModel:
    name: str
    timestamp_ns: int
    attributes: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def to_dict(ev: "SpanEventModel") -> dict:
        return asdict(ev)


@dataclass
class SpanModel:
    trace_id: str
    span_id: str
    operation_name: str
    service_name: str
    start_time_ns: int
    end_time_ns: int
    status: str
    attributes: dict[str, str] = field(default_factory=dict)
    events: list[SpanEventModel] = field(default_factory=list)
    parent_span_id: str | None = None
