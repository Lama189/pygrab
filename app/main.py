from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import get_settings, Settings
from app.infrastructure.clickhouse.client import ClickHouseClient
from app.infrastructure.clickhouse.repository import ClickHouseLogRepository
from app.application.logs.buffer import LogBuffer
from app.application.logs.worker import LogFlushWorker

from app.api.v1.injest import router as injest_router


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    deps = AppDependencies(settings)
    app.state.deps = deps

    await deps.flush_worker.start()

    yield

    await app.state.deps.flush_worker.stop()


app = FastAPI(title="pygrab", lifespan=lifespan)

app.include_router(injest_router)

@app.get("/ping")
def ping():
    return {"status": "pong"}
