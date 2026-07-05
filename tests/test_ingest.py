import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ingest_logs_success(client: AsyncClient, log_repo):
    payload = [
        {
            "message": "Test log message",
            "level": "INFO",
            "labels": {"service": "test-service"},
        }
    ]

    response = await client.post("/v1/logs", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["processed"] == 1


@pytest.mark.asyncio
async def test_ingest_logs_multiple_entries(client: AsyncClient):
    payload = [
        {"message": "Log 1", "level": "INFO"},
        {"message": "Log 2", "level": "ERROR"},
        {"message": "Log 3", "level": "DEBUG"},
    ]

    response = await client.post("/v1/logs", json=payload)
    assert response.status_code == 202
    assert response.json()["processed"] == 3


@pytest.mark.asyncio
async def test_ingest_logs_with_labels(client: AsyncClient):
    payload = [
        {
            "message": "Request processed",
            "level": "INFO",
            "labels": {"service": "api", "environment": "production"},
            "trace_id": "abc123",
            "span_id": "def456",
        }
    ]

    response = await client.post("/v1/logs", json=payload)
    assert response.status_code == 202


@pytest.mark.asyncio
async def test_ingest_logs_empty_list(client: AsyncClient):
    response = await client.post("/v1/logs", json=[])
    assert response.status_code == 202
    assert response.json()["processed"] == 0


@pytest.mark.asyncio
async def test_ingest_logs_missing_message(client: AsyncClient):
    payload = [{"level": "INFO"}]

    response = await client.post("/v1/logs", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ingest_traces_native(client: AsyncClient):
    payload = [
        {
            "trace_id": "trace-001",
            "span_id": "span-001",
            "operation_name": "http.request",
            "service_name": "api-gateway",
            "start_time_ns": 1700000000000000000,
            "end_time_ns": 1700000001000000000,
            "status": "OK",
            "attributes": {"method": "GET"},
            "events": [],
        }
    ]

    response = await client.post("/api/traces", json=payload)
    assert response.status_code == 201
    assert response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_ingest_traces_multiple_spans(client: AsyncClient):
    payload = [
        {
            "trace_id": "trace-001",
            "span_id": "span-001",
            "operation_name": "http.request",
            "service_name": "api-gateway",
            "start_time_ns": 1700000000000000000,
            "end_time_ns": 1700000001000000000,
            "status": "OK",
        },
        {
            "trace_id": "trace-001",
            "span_id": "span-002",
            "parent_span_id": "span-001",
            "operation_name": "db.query",
            "service_name": "database",
            "start_time_ns": 1700000000100000000,
            "end_time_ns": 1700000000900000000,
            "status": "OK",
        },
    ]

    response = await client.post("/api/traces", json=payload)
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_ingest_otlp_traces(client: AsyncClient):
    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "payment-service"}}
                    ]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "abc123def456",
                                "spanId": "span001",
                                "name": "process-payment",
                                "kind": 1,
                                "startTimeUnixNano": "1700000000000000000",
                                "endTimeUnixNano": "1700000001000000000",
                                "status": {"code": 1},
                                "attributes": [
                                    {"key": "amount", "value": {"stringValue": "99.99"}}
                                ],
                            }
                        ]
                    }
                ],
            }
        ]
    }

    response = await client.post("/api/otlp/v1/traces", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_ingest_otlp_traces_with_events(client: AsyncClient):
    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "web-app"}}
                    ]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "trace123",
                                "spanId": "span456",
                                "name": "handle-request",
                                "kind": 1,
                                "startTimeUnixNano": "1700000000000000000",
                                "endTimeUnixNano": "1700000002000000000",
                                "status": {"code": 2, "message": "timeout"},
                                "events": [
                                    {
                                        "timeUnixNano": "1700000001000000000",
                                        "name": "retry",
                                        "attributes": [
                                            {"key": "attempt", "value": {"intValue": 1}}
                                        ],
                                    }
                                ],
                            }
                        ]
                    }
                ],
            }
        ]
    }

    response = await client.post("/api/otlp/v1/traces", json=payload)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ingest_otlp_traces_empty(client: AsyncClient):
    payload = {"resourceSpans": []}

    response = await client.post("/api/otlp/v1/traces", json=payload)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ping(client: AsyncClient):
    response = await client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "pong"}
