import asyncio
from aiodocker import Docker

from app.core.config import AppConfig, DockerConfig
from app.infrastructure.clickhouse.factory import ClickHouseClientFactory
from app.infrastructure.clickhouse.pool import ClickHousePool
from app.infrastructure.clickhouse.repos.logs import ClickHouseLogRepository
from app.infrastructure.clickhouse.repos.traces import ClickHouseTraceRepository

from app.application.logs.buffer import LogBuffer
from app.application.logs.worker import LogFlushWorker
from app.application.collector.parser import LogParser
from app.application.collector.worker import DockerLogsCollector
from app.application.query.parser import LogQLParser
from app.application.query.service import LokiQueryService
from app.application.logs.service import LogsService
from app.application.traces.service import TraceService


class AppDependencies:
    def __init__(self, config: AppConfig):
        self._ch_client_factory = ClickHouseClientFactory(config)
        self._ch_pool = ClickHousePool(self._ch_client_factory)
        self.log_repository = ClickHouseLogRepository(self._ch_pool)
        self.trace_repository = ClickHouseTraceRepository(self._ch_pool)

        self.log_parser = LogParser()
        self.logql_parser = LogQLParser()
        self.log_buffer = LogBuffer(batch_size=config.batch_size)
        self.flush_worker = LogFlushWorker(
            buffer=self.log_buffer,
            repository=self.log_repository,
            interval=config.flush_interval_secs
        )
        self.flush_task: asyncio.Task | None = None
        self.query_service = LokiQueryService(
            repository=self.log_repository,
            parser=self.logql_parser,
            log_buffer=self.log_buffer,
            log_parser=self.log_parser
        )
        self.log_service = LogsService(buffer=self.log_buffer)
        self.trace_service = TraceService(self.trace_repository)


class DockerDependencies:
    def __init__(self, config: DockerConfig, app_deps: AppDependencies):
        self.docker_client = Docker(url=config.docker_socket)
        self.docker_collector: DockerLogsCollector | None = None
        self.collector_task: asyncio.Task | None = None
        self.config = config
        self.app_deps = app_deps
