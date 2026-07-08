import time
import logging
from typing import Any

from app.domain.models import LogEntry
from app.domain.enums import LogLevel
from app.application.logs.buffer import LogBuffer


logger = logging.getLogger(__name__)


class LogsService:
    def __init__(self, buffer: LogBuffer) -> None:
        self._buffer = buffer

    async def execute(self, logs_dto: list[dict[str, Any]]) -> None:
        try:
            for raw_log in logs_dto:
                timestamp = raw_log.get("timestamp")
                if timestamp is None:
                    timestamp = time.time_ns()

                raw_level = str(raw_log.get("level", "INFO")).upper()
                try:
                    level = LogLevel(raw_level)
                except ValueError:
                    logger.warning(f"Unknown log level: {raw_level}")
                    level = LogLevel.INFO

                entry = LogEntry(
                    timestamp=int(timestamp),
                    level=level,
                    message=str(raw_log.get("message", "")),
                    labels=dict(raw_log.get("labels", {})),
                    trace_id=raw_log.get("trace_id"),
                    span_id=raw_log.get("span_id"),
                )

                await self._buffer.add(entry)
        except Exception:
            logger.error(f"Error processing log: {raw_log}")
