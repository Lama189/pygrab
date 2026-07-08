import time
import pytest
from httpx import AsyncClient

from app.domain.enums import LogLevel
from app.domain.models import LogEntry, SpanModel


@pytest.mark.asyncio
async def test_loki_push(client: AsyncClient):
    now_ns = time.time_ns()
    payload = {
        "streams": [
            {
                "stream": {"service": "loki-client", "env": "staging"},
                "values": [
                    [str(now_ns), "Log from Loki push"],
                    [str(now_ns + 1_000_000_000), "Second log entry"],
                ],
            }
        ]
    }

    response = await client.post("/loki/api/v1/push", json=payload)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_loki_push_empty(client: AsyncClient):
    payload = {"streams": []}

    response = await client.post("/loki/api/v1/push", json=payload)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_loki_push_multiple_streams(client: AsyncClient):
    now_ns = time.time_ns()
    payload = {
        "streams": [
            {
                "stream": {"service": "app-a"},
                "values": [[str(now_ns), "Stream A log"]],
            },
            {
                "stream": {"service": "app-b"},
                "values": [[str(now_ns), "Stream B log"]],
            },
        ]
    }

    response = await client.post("/loki/api/v1/push", json=payload)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_loki_push_with_trace_id(client: AsyncClient):
    now_ns = time.time_ns()
    payload = {
        "streams": [
            {
                "stream": {"service": "traced-app"},
                "values": [
                    [str(now_ns), "Traced log", "trace-id-123", "span-id-456"]
                ],
            }
        ]
    }

    response = await client.post("/loki/api/v1/push", json=payload)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_traces_empty(client: AsyncClient):
    response = await client.get("/api/traces")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_traces_with_data(client: AsyncClient, trace_repo):
    now_ns = time.time_ns()
    trace_repo.spans.append(
        SpanModel(
            trace_id="trace-001",
            span_id="span-001",
            operation_name="http.get",
            service_name="api",
            start_time_ns=now_ns,
            end_time_ns=now_ns + 100_000_000,
            status="OK",
        )
    )

    response = await client.get("/api/traces?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["trace_id"] == "trace-001"
    assert data[0]["operation_name"] == "http.get"


@pytest.mark.asyncio
async def test_get_traces_by_trace_id(client: AsyncClient, trace_repo):
    now_ns = time.time_ns()
    trace_repo.spans.extend(
        [
            SpanModel(
                trace_id="trace-001",
                span_id="span-001",
                operation_name="http.get",
                service_name="api",
                start_time_ns=now_ns,
                end_time_ns=now_ns + 100_000_000,
                status="OK",
            ),
            SpanModel(
                trace_id="trace-002",
                span_id="span-002",
                operation_name="db.query",
                service_name="db",
                start_time_ns=now_ns,
                end_time_ns=now_ns + 50_000_000,
                status="OK",
            ),
        ]
    )

    response = await client.get("/api/traces?trace_id=trace-001")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["trace_id"] == "trace-001"
