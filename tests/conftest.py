from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.application.collector.parser import LogParser
from app.application.interfaces import ILogRepository, ITracerepository
from app.application.logs.buffer import LogBuffer
from app.application.logs.service import LogsService
from app.application.logs.worker import LogFlushWorker
from app.application.query.parser import LogQLParser
from app.application.query.service import LokiQueryService
from app.application.traces.service import TraceService
from app.domain.models import LogEntry, LogQueryParams, SpanModel
from app.main import app


class FakeLogRepository(ILogRepository):
    def __init__(self) -> None:
        self.logs: list[LogEntry] = []

    async def flush(self, batch: list[LogEntry]) -> None:
        self.logs.extend(batch)

    async def fetch(self, params: LogQueryParams) -> list[LogEntry]:
        result = list(self.logs)
        if params.start_time_ns:
            result = [entry for entry in result if entry.timestamp >= params.start_time_ns]
        if params.end_time_ns:
            result = [entry for entry in result if entry.timestamp <= params.end_time_ns]
        if params.matchers:
            for matcher in params.matchers:
                if matcher.name == "level":
                    result = [entry for entry in result if entry.level.value == matcher.value]
                else:
                    result = [entry for entry in result if entry.labels.get(matcher.name) == matcher.value]
        result = result[: params.limit]
        if params.direction.value == "backward":
            result.reverse()
        return result

    async def get_label_names(self) -> list[str]:
        names = set()
        for log in self.logs:
            names.update(log.labels.keys())
        return sorted(names)

    async def get_label_values(self, label_name: str) -> list[str]:
        values = set()
        for log in self.logs:
            if label_name in log.labels:
                values.add(log.labels[label_name])
        return sorted(values)


class FakeTraceRepository(ITracerepository):
    def __init__(self) -> None:
        self.spans: list[SpanModel] = []

    async def insert_spans(self, spans: list[SpanModel]) -> None:
        self.spans.extend(spans)

    async def fetch_traces(self, trace_id: str | None = None, limit: int = 100) -> list[SpanModel]:
        result = list(self.spans)
        if trace_id:
            result = [s for s in result if s.trace_id == trace_id]
        return result[:limit]


@pytest.fixture
def log_repo() -> FakeLogRepository:
    return FakeLogRepository()


@pytest.fixture
def trace_repo() -> FakeTraceRepository:
    return FakeTraceRepository()


@pytest.fixture
def log_buffer() -> LogBuffer:
    return LogBuffer(batch_size=100)


@pytest.fixture
def log_parser() -> LogParser:
    return LogParser()


@pytest.fixture
def logql_parser() -> LogQLParser:
    return LogQLParser()


@pytest.fixture
def loki_query_service(log_repo: FakeLogRepository, logql_parser: LogQLParser, log_buffer: LogBuffer, log_parser: LogParser) -> LokiQueryService:
    return LokiQueryService(
        repository=log_repo,
        parser=logql_parser,
        log_buffer=log_buffer,
        log_parser=log_parser,
    )


@pytest.fixture
def logs_service(log_buffer: LogBuffer) -> LogsService:
    return LogsService(buffer=log_buffer)


@pytest.fixture
def trace_service(trace_repo: FakeTraceRepository) -> TraceService:
    return TraceService(trace_repo)


@pytest.fixture
def flush_worker(log_buffer: LogBuffer, log_repo: FakeLogRepository) -> LogFlushWorker:
    return LogFlushWorker(buffer=log_buffer, repository=log_repo, interval=1)


@pytest.fixture
def mock_deps(log_repo, trace_repo, log_buffer, log_parser, logql_parser, loki_query_service, logs_service, trace_service, flush_worker):
    deps = MagicMock()
    deps.log_repository = log_repo
    deps.trace_repository = trace_repo
    deps.log_buffer = log_buffer
    deps.log_parser = log_parser
    deps.logql_parser = logql_parser
    deps.query_service = loki_query_service
    deps.log_service = logs_service
    deps.trace_service = trace_service
    deps.flush_worker = flush_worker
    deps.flush_task = None
    return deps


@pytest_asyncio.fixture
async def client(mock_deps):
    app.state.deps = mock_deps
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
