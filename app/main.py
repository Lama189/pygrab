import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from aiodocker import Docker

from app.core.config import get_settings, Settings
from app.infrastructure.clickhouse.client import ClickHouseClient
from app.infrastructure.clickhouse.repository import ClickHouseLogRepository
from app.application.logs.buffer import LogBuffer
from app.application.logs.worker import LogFlushWorker
from app.application.collector.parser import LogParser
from app.application.collector.worker import DockerLogsCollector

from app.api.v1.injest import router as injest_router

logger = logging.getLogger(__name__)


class AppDependencies:
    def __init__(self, settings: Settings):
        self.ch_client_wrapper = ClickHouseClient(settings=settings)
        self.log_repository = ClickHouseLogRepository(client=self.ch_client_wrapper.get())
        self.log_buffer = LogBuffer(batch_size=settings.batch_size)
        self.flush_worker = LogFlushWorker(
            buffer=self.log_buffer,
            repository=self.log_repository,
            interval=settings.flush_interval_secs
        )
        self.docker_client = Docker(url=settings.docker_socket)
        self.log_parser = LogParser()
        self.docker_collector: DockerLogsCollector | None = None

        self.flush_task: asyncio.Task | None = None
        self.collector_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    deps = AppDependencies(settings)
    app.state.deps = deps

    deps.flush_task = asyncio.create_task(deps.flush_worker.start())

    if settings.docker_enabled:
        deps.docker_collector = DockerLogsCollector(
            buffer=deps.log_buffer,
            docker=deps.docker_client,
            parser=deps.log_parser,
            allowed_containers=settings.docker_containers
        )

        deps.collector_task = asyncio.create_task(deps.docker_collector.start())

    yield

    if deps.collector_task:
        deps.collector_task.cancel()

    if deps.docker_collector:
        await deps.docker_collector.stop()

    if deps.flush_task:
        deps.flush_task.cancel()

    await deps.flush_worker.stop()


app = FastAPI(title="pygrab", lifespan=lifespan)

app.include_router(injest_router)


@app.get("/ping")
def ping():
    return {"status": "pong"}