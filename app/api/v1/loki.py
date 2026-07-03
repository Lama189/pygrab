import time
import logging
from typing import Annotated
from fastapi import (
    APIRouter,
    Request,
    Response,
    HTTPException,
    status,
    Depends,
    Query,
)

from app.domain.enums import Direction
from app.application.query.service import LokiQueryService
from app.application.dependencies import get_query_service
from app.application.utils.time_parser import parse_time_ns


logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/pygrab/api/v1",
)


@router.get(
    path="/query",
    status_code=status.HTTP_200_OK
)
async def query_instant(
    service: Annotated[LokiQueryService, Depends(get_query_service)],
    query: str = Query(..., description="LogQL selector"),
    limit: int = Query(100, description="Logs limit"),
    time_ts: str | None = Query(None, alias="time", description="Evaluation time timestamp")
):
    now_ns = time.time_ns()
    end_ns = parse_time_ns(time_ts, now_ns)

    try:
        return await service.execute_query(
            query=query, 
            end_time_ns=end_ns, 
            limit=limit, 
            direction=Direction.BACKWARD
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@router.get(
    path="/query_range",
    status_code=status.HTTP_200_OK
)
async def query_range(
    service: Annotated[LokiQueryService, Depends(get_query_service)],
    query: str = Query(..., description="LogQL selector"),
    limit: int = Query(100, description="Logs limit"),
    start: str | None = Query(None, description="Start time"),
    end: str | None = Query(None, description="End time"),
    direction: str = Query("backward", description="Sorting direction: forward or backward")
):
    now_ns = time.time_ns()
    six_hours_ns = 6 * 60 * 60 * 1_000_000_000
    start_ns = parse_time_ns(start, now_ns - six_hours_ns)
    end_ns = parse_time_ns(end, now_ns)

    try:
        dir_enum = Direction(direction.lower())
    except ValueError:
        dir_enum = Direction.BACKWARD

    try:
        return await service.execute_query(
            query=query,
            start_time_ns=start_ns,
            end_time_ns=end_ns,
            limit=limit,
            direction=dir_enum
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@router.get(
    path="/labels",
    status_code=status.HTTP_200_OK
)
async def get_labels(
    service: Annotated[LokiQueryService, Depends(get_query_service)],
):
    names = await service.get_label_names()
    return {"status": "success", "data": names}


@router.get(
    path="/label/{name}/values",
    status_code=status.HTTP_200_OK
)
async def get_label_values(
    name: str,
    service: Annotated[LokiQueryService, Depends(get_query_service)],
):
    values = await service.get_label_values(name)
    return {"status": "success", "data": values}


@router.post(
    path="/push",
    status_code=status.HTTP_204_NO_CONTENT
)
async def push_logs(
    request: Request,
    service: Annotated[LokiQueryService, Depends(get_query_service)],
):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    await service.push_external_logs(payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)