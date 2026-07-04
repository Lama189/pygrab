import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import get_app_config, get_docker_config
from app.core.dependencies import AppDependencies, DockerDependencies
from app.application.collector.worker import DockerLogsCollector

from app.api.v1.injest import router as injest_router
from app.api.v1.loki import router as loki_router
from app.api.v1.traces import router as traces_router


logger = logging.getLogger(__name__)


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
            parser=app_deps.log_parser,
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
app.include_router(loki_router)
app.include_router(traces_router)

@app.get("/ping")
def ping():
    return {"status": "pong"}