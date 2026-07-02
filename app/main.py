import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from aiodocker import Docker

from app.core.config import get_app_config, get_docker_config, AppConfig, DockerConfig
from app.infrastructure.clickhouse.client import ClickHouseClient
from app.infrastructure.clickhouse.repository import ClickHouseLogRepository
from app.application.logs.buffer import LogBuffer
from app.application.logs.worker import LogFlushWorker
from app.application.collector.parser import LogParser
from app.application.collector.worker import DockerLogsCollector

from app.api.v1.injest import router as injest_router

logger = logging.getLogger(__name__)


class AppDependencies:
    def __init__(self, config: AppConfig):
        self.ch_client_wrapper = ClickHouseClient(settings=config)
        self.log_repository = ClickHouseLogRepository(client=self.ch_client_wrapper.get())
        self.log_buffer = LogBuffer(batch_size=config.batch_size)
        self.flush_worker = LogFlushWorker(
            buffer=self.log_buffer,
            repository=self.log_repository,
            interval=config.flush_interval_secs
        )
        self.flush_task: asyncio.Task | None = None


class DockerDependencies:
    def __init__(self, config: DockerConfig, app_deps: AppDependencies):
        self.docker_client = Docker(url=config.docker_socket)
        self.log_parser = LogParser()
        self.docker_collector: DockerLogsCollector | None = None
        self.collector_task: asyncio.Task | None = None
        self.config = config
        self.app_deps = app_deps


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_config = get_app_config()
    docker_config = get_docker_config()

    app_deps = AppDependencies(app_config)
    docker_deps = DockerDependencies(docker_config, app_deps)

    app.state.deps = app_deps
    app.state.docker_deps = docker_deps

    app_deps.flush_task = asyncio.create_task(app_deps.flush_worker.start())

    if docker_config.docker_enabled:
        docker_deps.docker_collector = DockerLogsCollector(
            buffer=app_deps.log_buffer,
            docker=docker_deps.docker_client,
            parser=docker_deps.log_parser,
            allowed_containers=docker_config.docker_containers
        )

        docker_deps.collector_task = asyncio.create_task(docker_deps.docker_collector.start())

    yield

    if docker_deps.collector_task:
        docker_deps.collector_task.cancel()

    if docker_deps.docker_collector:
        await docker_deps.docker_collector.stop()

    if app_deps.flush_task:
        app_deps.flush_task.cancel()

    await app_deps.flush_worker.stop()


app = FastAPI(title="pygrab", lifespan=lifespan)

app.include_router(injest_router)


@app.get("/ping")
def ping():
    return {"status": "pong"}