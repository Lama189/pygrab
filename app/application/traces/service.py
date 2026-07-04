from app.domain.models import SpanModel
from app.application.interfaces import ITracerepository


class TraceService:
    def __init__(self, repository: ITracerepository) -> None:
        self._repo = repository

    async def insert_spans(self, spans: list[SpanModel]) -> None:
        await self._repo.insert_spans(spans)

    async def get_traces(self, trace_id: str | None = None, limit: int = 100) -> list[SpanModel]:
        return await self._repo.fetch_traces(trace_id=trace_id, limit=limit)