from fastapi import APIRouter, Depends, status
from typing import List

from app.application.dto.logs import LogEntryDTO
from app.application.logs.services import LogsService
from app.application.dependencies import get_logs_service


router = APIRouter(prefix="/v1/logs", tags=["Logs Ingestion"])


@router.post(
    path="",
    status_code=status.HTTP_202_ACCEPTED
)
async def injest_logs(
    payload: List[LogEntryDTO],
    logs_service: LogsService = Depends(get_logs_service)
):
    logs_data = [log.model_dump() for log in payload]

    await logs_service.execute(logs_data)

    return {"status": "accepted", "processed": len(payload)}
