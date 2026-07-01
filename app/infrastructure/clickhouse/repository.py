import asyncio
from datetime import datetime
from typing import cast

from app.domain.models import LogEntry
from app.application.interfaces import ILogRepository
from app.infrastructure.clickhouse.protocol import ClickHouseClientProtocol

class ClickHouseLogRepository(ILogRepository):
    def __init__(self, client: ClickHouseClientProtocol) -> None:
        self._client = client
    
    async def flush(self, batch: list[LogEntry]) -> None:
        if not batch:
            return
        
        data = [
            [
                datetime.fromtimestamp(e.timestamp / 1_000_000_000),
                e.level.value,
                e.message,
                e.labels,
                e.trace_id or "",
                e.span_id or "",
            ]
            for e in batch
        ]

        await asyncio.to_thread(
            self._client.insert,
            table="pygrab_db.logs",
            data=data,
            column_names=[
                "timestamp",
                "level",
                "message",
                "labels",
                "trace_id",
                "span_id",
            ],
        )
        