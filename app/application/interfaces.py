from abc import ABC, abstractmethod

from app.domain.models import LogEntry, LogQueryParams, SpanModel


class ILogRepository(ABC):

    @abstractmethod
    async def flush(self, batch: list[LogEntry]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, params: LogQueryParams) -> list[LogEntry]:
        raise NotImplementedError

    @abstractmethod
    async def get_label_names(self) -> list[str]:
        raise NotImplementedError
    
    @abstractmethod
    async def get_label_values(self, label_name: str) -> list[str]:
        raise NotImplementedError
    

class ITracerepository(ABC):

    @abstractmethod
    async def insert_spans(self, spans: list[SpanModel]) -> None:
        raise NotImplementedError
    
    @abstractmethod
    async def fetch_traces(self, trace_id: str | None = None, limit: int = 100) -> list[SpanModel]:
        raise NotImplementedError