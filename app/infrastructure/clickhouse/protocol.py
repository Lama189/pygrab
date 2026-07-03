from typing import Protocol, Sequence, Any


class ClickHouseClientProtocol(Protocol):
    def insert(self, table: str, data: Sequence[Sequence[Any]], column_names: Sequence[str]) -> Any:
        ...
    
    def query(self, query: str, parameters: dict[str, Any] | None = None) -> Any: 
        ...