import json
import asyncio
from datetime import datetime, timezone

from app.domain.models import SpanModel, SpanEventModel
from app.application.interfaces import ITracerepository
from app.infrastructure.clickhouse.pool import ClickHousePool


class ClickHouseTraceRepository(ITracerepository):
    def __init__(self, pool: ClickHousePool) -> None:
        self._pool = pool

    async def insert_spans(self, spans: list[SpanModel]) -> None:
        if not spans:
            return
        
        data = []
        for span in spans:
            start_dt = datetime.fromtimestamp(
                span.start_time_ns / 1_000_000_000, 
                tz=timezone.utc
            ).replace(tzinfo=None)

            end_dt = datetime.fromtimestamp(
                span.end_time_ns / 1_000_000_000, 
                tz=timezone.utc
            ).replace(tzinfo=None)

            events_json = json.dumps([SpanEventModel.to_dict(ev) for ev in span.events])

            data.append([
                span.trace_id,
                span.span_id,
                span.parent_span_id,
                span.operation_name,
                span.service_name,
                start_dt,
                end_dt,
                span.status,
                span.attributes,
                events_json
            ])

        column_names = [
            "trace_id", "span_id", "parent_span_id", "operation_name", 
            "service_name", "start_time", "end_time", "status", 
            "attributes", "events"
        ]

        def run():
            with self._pool.client() as client:
                client.insert(
                    table="pygrab_db.spans",
                    data=data,
                    column_names=column_names
                )
        
        await asyncio.to_thread(run)
    
    async def fetch_traces(self, trace_id: str | None = None, limit: int = 100) -> list[SpanModel]:
        query_parts = ["SELECT * FROM pygrab_db.spans WHERE 1=1"]
        query_params = {}

        if trace_id:
            query_parts.append("AND trace_id = {trace_id:String}")
            query_params["trace_id"] = trace_id
            query_parts.append("ORDER BY start_time ASC")
        else:
            query_parts.append(f"ORDER BY start_time DESC LIMIT {limit}")

        query_str = " ".join(query_parts)

        def run():
            with self._pool.client() as client:
                return client.query(query_str, settings=query_params)

        result = await asyncio.to_thread(run)

        spans = []
        for row in result.result_rows:
            start_dt = row[5].replace(tzinfo=timezone.utc) if row[5].tzinfo is None else row[5]
            end_dt = row[6].replace(tzinfo=timezone.utc) if row[6].tzinfo is None else row[6]
            
            start_ns = int(start_dt.timestamp() * 1_000_000_000)
            end_ns = int(end_dt.timestamp() * 1_000_000_000)
            
            try:
                events_list = json.loads(row[9])
                events_models = [
                    SpanEventModel(
                        name=ev["name"],
                        timestamp_ns=ev["timestamp_ns"],
                        attributes=ev.get("attributes", {})
                    )
                    for ev in events_list
                ]
            except Exception:
                events_models = []

            spans.append(
                SpanModel(
                    trace_id=row[0],
                    span_id=row[1],
                    parent_span_id=row[2],
                    operation_name=row[3],
                    service_name=row[4],
                    start_time_ns=start_ns,
                    end_time_ns=end_ns,
                    status=row[7],
                    attributes=row[8],
                    events=events_models
                )
            )

        return spans