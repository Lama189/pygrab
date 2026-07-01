import asyncio

from app.domain.models import LogEntry

class LogBuffer:
    def __init__(self, batch_size: int) -> None:
        self._batch_size = batch_size
        self._queue: asyncio.Queue = asyncio.Queue()

    @property
    def batch_size(self) -> int:
        return self._batch_size
    
    async def add(self, item: LogEntry) -> None:
        await self._queue.put(item) 

    async def drain(self) -> list[LogEntry]:
        batch = []
        while not self._queue.empty() and len(batch) < self._batch_size:
            batch.append(self._queue.get_nowait())
            self._queue.task_done()

        return batch
    
    def is_empty(self) -> bool:
        return self._queue.empty()
