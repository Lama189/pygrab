import time
from typing import Any

from app.domain.enums import Direction
from app.domain.models import LogQueryParams, LokiStream, LokiQueryResponse, LogEntry
from app.application.query.parser import LogQLParser
from app.application.interfaces import ILogRepository
from app.application.logs.buffer import LogBuffer
from app.application.collector.parser import LogParser


class LokiQueryService:
    def __init__(
        self, 
        repository: ILogRepository, 
        parser: LogQLParser,
        log_buffer: LogBuffer,
        log_parser: LogParser
    ) -> None:
        self._repository = repository
        self._parser = parser
        self._log_buffer = log_buffer
        self._log_parser = log_parser

    async def execute_query(
        self, 
        query: str, 
        start_time_ns: int | None = None,
        end_time_ns: int | None = None,
        limit: int = 100,
        direction: Direction = Direction.BACKWARD
    ) -> LokiQueryResponse:
        matchers = self._parser.parse(query)
        
        params = LogQueryParams(
            matchers=matchers, 
            start_time_ns=start_time_ns,
            end_time_ns=end_time_ns,
            limit=limit,
            direction=direction
        )
        
        entries: list[LogEntry] = await self._repository.fetch(params)
        
        streams_map: dict[frozenset, list[list[str]]] = {}
        labels_cache: dict[frozenset, dict[str, str]] = {}

        for entry in entries:
            stream_key = frozenset(entry.labels.items())
            if stream_key not in streams_map:
                streams_map[stream_key] = []
                labels_cache[stream_key] = entry.labels
            
            streams_map[stream_key].append([str(entry.timestamp), entry.message])

        loki_streams = [
            LokiStream(stream=labels_cache[key], values=values)
            for key, values in streams_map.items()
        ]

        return LokiQueryResponse.create(streams=loki_streams)

    async def get_label_names(self) -> list[str]:
        return await self._repository.get_label_names()

    async def get_label_values(self, label_name: str) -> list[str]:
        return await self._repository.get_label_values(label_name)
    
    async def push_external_logs(self, payload: dict[str, Any]) -> None:
        streams = payload.get("streams", "")
        if not streams:
            return
        
        for stream_data in streams:
            labels = stream_data.get("stream", {})
            values = stream_data.get("values", [])

            for val in values:
                if len(val) < 2:
                    continue

                ts_ns_str, message = val[0], val[1]

                try:
                    timestamp_ns = int(ts_ns_str)
                except ValueError:
                    timestamp_ns = time.time_ns()

                trace_id = val[2] if len(val) > 2 else None
                span_id = val[3] if len(val) > 3 else None

                level = self._log_parser.parse_level(message)
                entry = LogEntry(
                    timestamp=timestamp_ns,
                    level=level,
                    message=message,
                    labels=labels,
                    trace_id=trace_id,
                    span_id=span_id
                )

                await self._log_buffer.add(entry)