import asyncio
import logging
from app.application.logs.buffer import LogBuffer
from app.infrastructure.clickhouse.repository import ClickHouseLogRepository

logger = logging.getLogger(__name__)

class LogFlushWorker:
    def __init__(
        self,
        buffer: LogBuffer,
        repository: ClickHouseLogRepository,
        interval: float
    ) -> None:
        self._buffer = buffer
        self._repo = repository
        self._interval = interval
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Log background worker started successfully")

    async def _flush_once(self) -> None:
        try:
            batch = await self._buffer.drain()
            if batch:
                await self._repo.flush(batch)
        except Exception as e:
            logger.error(f"Error during background log flush: {e}")

    async def _loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self._interval)
                await self._flush_once()
            except asyncio.CancelledError:
                break

    async def stop(self) -> None:
        logger.info("Stopping log worker, flushing remaining buffer...")
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        while not self._buffer.is_empty():
            await self._flush_once()
            
        logger.info("Log worker fully stopped. All data saved.")