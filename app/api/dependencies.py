from starlette.requests import HTTPConnection

from app.application.logs.service import LogsService
from app.application.query.service import LokiQueryService
from app.application.logs.buffer import LogBuffer
from app.application.query.parser import LogQLParser
from app.infrastructure.clickhouse.repos.logs import ClickHouseLogRepository
from app.application.traces.service import TraceService



def get_log_buffer(connection: HTTPConnection) -> LogBuffer:
    return connection.app.state.deps.log_buffer

def get_log_repository(connection: HTTPConnection) -> ClickHouseLogRepository:
    return connection.app.state.deps.log_repository

def get_logs_service(connection: HTTPConnection) -> LogsService:
    return connection.app.state.deps.log_service

def get_query_service(connection: HTTPConnection) -> LokiQueryService:
    return connection.app.state.deps.query_service

def get_trace_service(connection: HTTPConnection) -> TraceService:
    return connection.app.state.deps.trace_service

def get_logql_parser(connection: HTTPConnection) -> LogQLParser:
    return connection.app.state.deps.logql_parser

