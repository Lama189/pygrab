from app.domain.models import LogQueryParams, LokiStream, LokiQueryResponse, LogEntry
from app.domain.enums import Direction
from app.application.query.parser import LogQLParser
from app.application.interfaces import ILogRepository


class LokiQueryService:
    def __init__(self, repository: ILogRepository, parser: LogQLParser) -> None:
        self._repository = repository
        self._parser = parser

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