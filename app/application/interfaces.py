from abc import ABC, abstractmethod

from app.domain.models import LogEntry


class ILogRepository(ABC):

    @abstractmethod
    async def flush(self, batch: list[LogEntry]) -> None:
        pass
