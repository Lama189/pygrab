import asyncio

from app.domain.models import LogEntry, LabelMatcher, TailSubscriber


class LogBuffer:
    def __init__(self, batch_size: int) -> None:
        self._batch_size = batch_size
        self._queue: asyncio.Queue = asyncio.Queue()
        self._subscribers: list[TailSubscriber] = []

    @property
    def batch_size(self) -> int:
        return self._batch_size
    
    async def add(self, item: LogEntry) -> None:
        await self._queue.put(item)
        for sub in list(self._subscribers):
            if sub.matches(item):
                try:
                    sub.queue.put_nowait(item)
                except asyncio.QueueFull:
                    pass

    async def drain(self) -> list[LogEntry]:
        batch = []
        while not self._queue.empty() and len(batch) < self._batch_size:
            batch.append(self._queue.get_nowait())
            self._queue.task_done()

        return batch
    
    def is_empty(self) -> bool:
        return self._queue.empty()

    def subscribe(self, matchers: list[LabelMatcher]) -> TailSubscriber:
        sub = TailSubscriber(queue=asyncio.Queue(maxsize=100), matchers=matchers)
        self._subscribers.append(sub)
        return sub

    def unsubscribe(self, subscriber: TailSubscriber) -> None:
        try:
            self._subscribers.remove(subscriber)
        except ValueError:
            pass
