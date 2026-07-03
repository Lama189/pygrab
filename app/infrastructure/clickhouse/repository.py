import asyncio
from datetime import datetime
from typing import cast

from app.domain.models import LogEntry, LogQueryParams
from app.domain.enums import MatchOp, LogLevel, Direction
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
    
    async def fetch(self, params: LogQueryParams) -> list[LogEntry]:
        query_parts = ["SELECT timestamp, level, message, labels, trace_id, span_id FROM logs WHERE 1=1"]
        query_params = {}

        if params.start_time_ns:
            query_parts.append("AND timestamp >= {start_time:DateTime64(9)}")
            query_params["start_time"] = datetime.fromtimestamp(params.start_time_ns / 1_000_000_000)
        
        if params.end_time_ns:
            query_parts.append("AND timestamp <= {end_time:DateTime64(9)}")
            query_params["end_time"] = datetime.fromtimestamp(params.end_time_ns / 1_000_000_000)

        for i, matcher in enumerate(params.matchers):
            param_key = f"val_{i}"  
            db_field = f"labels['{matcher.name}']"

            if matcher.op == MatchOp.EQ:
                query_parts.append(f"AND {db_field} = {{{param_key}:String}}")
                query_params[param_key] = matcher.value
                
            elif matcher.op == MatchOp.NEQ:
                query_parts.append(f"AND {db_field} != {{{param_key}:String}}")
                query_params[param_key] = matcher.value
                
            elif matcher.op == MatchOp.RE:
                query_parts.append(f"AND match({db_field}, {{{param_key}:String}})")
                query_params[param_key] = matcher.value
                
            elif matcher.op == MatchOp.NRE:
                query_parts.append(f"AND NOT match({db_field}, {{{param_key}:String}})")
                query_params[param_key] = matcher.value

        order = "ASC" if params.direction == Direction.FORWARD else "DESC"
        query_parts.append(f"ORDER BY timestamp {order}")
        query_parts.append(f"LIMIT {int(params.limit)}")

        final_query = "\n".join(query_parts)
        
        result = await asyncio.to_thread(
            self._client.query,
            final_query,
            parameters=query_params
        )

        entries = []
        for row in result.result_rows:
            ts_ns = int(row[0].timestamp() * 1_000_000_000) + row[0].microsecond * 1000
            
            entries.append(
                LogEntry(
                    timestamp=ts_ns,
                    level=LogLevel(row[1]),
                    message=row[2],
                    labels=row[3], 
                    trace_id=row[4] if row[4] else None,
                    span_id=row[5] if row[5] else None,
                )
            )
            
        return entries