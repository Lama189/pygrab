from typing import Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, status

from app.application.dto.logs import LogEntryDTO
from app.application.logs.service import LogsService
from app.application.query.service import LokiQueryService
from app.api.dependencies import get_logs_service, get_query_service
from app.application.utils.tui_formatter import format_logs_for_tui


router = APIRouter(prefix="", tags=["Logs Ingestion"])


@router.post(
    path="/v1/logs",
    status_code=status.HTTP_202_ACCEPTED
)
async def injest_logs(
    payload: list[LogEntryDTO],
    logs_service: LogsService = Depends(get_logs_service)
):
    logs_data = [log.model_dump() for log in payload]
    await logs_service.execute(logs_data)
    return {"status": "accepted", "processed": len(payload)}


@router.get(
    path="/api/logs",
    status_code=status.HTTP_200_OK
)
async def get_logs(
    service: Annotated[LokiQueryService, Depends(get_query_service)],
    limit: int = Query(200),
    offset: int = Query(0)
):
    try:
        logs = await service.get_logs(limit, offset)
        return format_logs_for_tui(logs)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=str(e)
        )
