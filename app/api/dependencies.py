from fastapi import Request

from app.application.logs.service import LogsService
from app.application.query.service import LokiQueryService
from app.application.logs.buffer import LogBuffer
from app.infrastructure.clickhouse.repos.logs import ClickHouseLogRepository
from app.application.traces.service import TraceService


def get_log_buffer(request: Request) -> LogBuffer:
    return request.app.state.deps.log_buffer

def get_log_repository(request: Request) -> ClickHouseLogRepository:
    return request.app.state.deps.log_repository

def get_logs_service(request: Request) -> LogsService:
    return request.app.state.deps.log_service

def get_query_service(request: Request) -> LokiQueryService:
    return request.app.state.deps.query_service

def get_trace_service(request: Request) -> TraceService:
    return request.app.state.deps.trace_service
