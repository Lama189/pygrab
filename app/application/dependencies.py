from fastapi import Request
from app.application.logs.services import LogsService
from app.application.logs.buffer import LogBuffer
from app.infrastructure.clickhouse.repository import ClickHouseLogRepository


def get_log_buffer(request: Request) -> LogBuffer:
    return request.app.state.deps.lo0g_buffer

def get_log_repository(request: Request) -> ClickHouseLogRepository:
    return request.app.state.deps.log_repository

def get_logs_service(request: Request) -> LogsService:
    return LogsService(buffer=request.app.state.deps.log_buffer)