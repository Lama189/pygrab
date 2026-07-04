import queue
import threading
from contextlib import contextmanager

from app.infrastructure.clickhouse.factory import ClickHouseClientFactory
from app.infrastructure.clickhouse.client import ClickHouseClient
from app.core.exceptions import PoolExhaustedError


class ClickHousePool:
    def __init__(self, factory: ClickHouseClientFactory, size: int = 10):
        self._factory = factory
        self._pool = queue.Queue(maxsize=size)

        for _ in range(size):
            client = factory.create_raw()
            self._pool.put(client)
    
    def acquire(self, timeout: float = 5.0):
        try:
            return self._pool.get(timeout=timeout)
        except queue.Empty:
            raise PoolExhaustedError("No ClickHouse clients available")
    
    def realise(self, client) -> None:
        self._pool.put(client)

    @contextmanager
    def client(self):
        client = self.acquire()
        try:
            yield ClickHouseClient(client)
        finally:
            self.realise(client)