from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.application.schemas.otlp import ExportTraceServiceRequest
from app.domain.models import SpanModel
from app.application.traces.converter import convert_otlp_to_domain
from app.application.traces.service import TraceService
from app.api.dependencies import get_trace_service


router = APIRouter(prefix="/api")


@router.post(
    path="/otlp/v1/traces",
    status_code=status.HTTP_200_OK
)
async def ingest_otlp_traces(
    request: ExportTraceServiceRequest,
    service: Annotated[TraceService, Depends(get_trace_service)]
):
    try:
        domain_spans = convert_otlp_to_domain(request)
        await service.insert_spans(domain_spans)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process OTLP traces: {str(e)}"
        )
    

@router.post(
    path="/traces",
    status_code=status.HTTP_201_CREATED
)
async def ingest_native_traces(
    spans: list[SpanModel],
    service: Annotated[TraceService, Depends(get_trace_service)]
):
    try:
        await service.insert_spans(spans)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save native traces: {str(e)}"
        )
    

@router.get(
    path="/traces",
    status_code=status.HTTP_200_OK
)
async def get_traces(
    service: Annotated[TraceService, Depends(get_trace_service)],
    trace_id: str = Query(None),
    limit: int = Query(100)
):
    try:
        spans = await service.get_traces(trace_id=trace_id, limit=limit)
        
        formatted_spans = []
        for s in spans:
            start_dt = datetime.fromtimestamp(s.start_time_ns / 1_000_000_000, tz=timezone.utc)
            end_dt = datetime.fromtimestamp(s.end_time_ns / 1_000_000_000, tz=timezone.utc)

            raw_status = str(s.status).upper()
            if "OK" in raw_status:
                status_formatted = "Ok"
            elif "ERROR" in raw_status or "ERR" in raw_status:
                status_formatted = "Error"
            else:
                status_formatted = "Unset"

            p_id = s.parent_span_id if s.parent_span_id and s.parent_span_id.strip() else None

            formatted_spans.append({
                "trace_id": s.trace_id,
                "span_id": s.span_id,
                "parent_span_id": p_id,
                "operation_name": s.operation_name,
                "service_name": s.service_name,
                "start_time": start_dt.isoformat().replace("+00:00", "Z"), 
                "end_time": end_dt.isoformat().replace("+00:00", "Z"),     
                "status": status_formatted,
                "attributes": s.attributes,
                "events": [
                    {
                        "name": ev.name,
                        "timestamp": datetime.fromtimestamp(ev.timestamp_ns / 1_000_000_000, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                        "attributes": ev.attributes
                    }
                    for ev in s.events
                ]
            })

        return formatted_spans
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch traces: {str(e)}"
        )