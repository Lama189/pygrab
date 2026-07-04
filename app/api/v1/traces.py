from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.application.schemas.otlp import ExportTraceServiceRequest
from app.domain.models import SpanModel
from app.application.traces.converter import convert_otlp_to_domain
from app.application.traces.service import TraceService
from app.api.dependencies import get_trace_service


router = APIRouter(prefix="/pygrab/api/v1")


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
    response_model=list[SpanModel],
    status_code=status.HTTP_200_OK
)
async def get_traces(
    service: Annotated[TraceService, Depends(get_trace_service)],
    trace_id: str = Query(None),
    limit: int = Query(100)
):
    try:
        return await service.get_traces(trace_id=trace_id, limit=limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch traces: {str(e)}"
        )