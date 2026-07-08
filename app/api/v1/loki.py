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
    WebSocket
)

from app.domain.enums import Direction
from app.domain.models import LokiQueryResponse
from app.application.query.service import LokiQueryService
from app.application.logs.buffer import LogBuffer
from app.application.query.parser import LogQLParser
from app.application.utils.loki_helpers import is_logql_selector, handle_vector_query
from app.api.dependencies import get_query_service, get_log_buffer, get_logql_parser
from app.application.utils.time_parser import parse_time_ns


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/loki/api/v1")


@router.get(
    path="/ready",
    status_code=status.HTTP_200_OK
)
async def ready():
    return Response(content="ready", media_type="text/plain")


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
    if query.startswith("vector("):
        return handle_vector_query()

    if not is_logql_selector(query):
        return LokiQueryResponse.create(streams=[])

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
    if query.startswith("vector("):
        return handle_vector_query()

    if not is_logql_selector(query):
        return LokiQueryResponse.create(streams=[])

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


@router.websocket(
    path="/tail"
)
async def tail_logs(
    websocket: WebSocket,
    buffer: Annotated[LogBuffer, Depends(get_log_buffer)],
    parser: Annotated[LogQLParser, Depends(get_logql_parser)],
):
    await websocket.accept()

    query = websocket.query_params.get("query", "{}")

    try:
        matchers = parser.parse(query)
    except ValueError:
        await websocket.close(code=1008, reason="Invalid LogQL query")
        return

    subscriber = buffer.subscribe(matchers)

    try:
        while True:
            entry = await subscriber.queue.get()
            ts_str = str(entry.timestamp)
            labels = dict(entry.labels)
            labels["level"] = entry.level.value

            await websocket.send_json({
                "streams": [
                    {
                        "stream": labels,
                        "values": [[ts_str, entry.message]]
                    }
                ]
            })
    except Exception:
        pass
    finally:
        buffer.unsubscribe(subscriber)