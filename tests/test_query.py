import time
import pytest
from httpx import AsyncClient

from app.domain.enums import LogLevel
from app.domain.models import LogEntry


@pytest.mark.asyncio
async def test_get_logs_empty(client: AsyncClient):
    response = await client.get("/api/logs")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_logs_with_data(client: AsyncClient, log_repo):
    now_ns = time.time_ns()
    log_repo.logs.append(
        LogEntry(
            timestamp=now_ns,
            level=LogLevel.INFO,
            message="Test message",
            labels={"service": "api"},
        )
    )

    response = await client.get("/api/logs?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["message"] == "Test message"
    assert data[0]["level"] == "INFO"
    assert data[0]["labels"]["service"] == "api"


@pytest.mark.asyncio
async def test_get_logs_pagination(client: AsyncClient, log_repo):
    now_ns = time.time_ns()
    for i in range(5):
        log_repo.logs.append(
            LogEntry(
                timestamp=now_ns - i * 1_000_000_000,
                level=LogLevel.INFO,
                message=f"Message {i}",
            )
        )

    response = await client.get("/api/logs?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_logs_with_labels(client: AsyncClient, log_repo):
    now_ns = time.time_ns()
    log_repo.logs.append(
        LogEntry(
            timestamp=now_ns,
            level=LogLevel.INFO,
            message="Labeled log",
            labels={"env": "prod", "region": "us-east"},
        )
    )

    response = await client.get("/api/logs")
    data = response.json()
    assert data[0]["labels"]["env"] == "prod"
    assert data[0]["labels"]["region"] == "us-east"


@pytest.mark.asyncio
async def test_query_instant(client: AsyncClient, log_repo):
    now_ns = time.time_ns()
    log_repo.logs.append(
        LogEntry(
            timestamp=now_ns,
            level=LogLevel.ERROR,
            message="Something failed",
            labels={"service": "worker"},
        )
    )

    response = await client.get(
        '/loki/api/v1/query?query={service="worker"}&limit=10'
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    results = data["data"]["result"]
    assert len(results) == 1
    assert results[0]["stream"]["service"] == "worker"


@pytest.mark.asyncio
async def test_query_instant_with_level_filter(client: AsyncClient, log_repo):
    now_ns = time.time_ns()
    log_repo.logs.append(
        LogEntry(timestamp=now_ns, level=LogLevel.INFO, message="info msg")
    )
    log_repo.logs.append(
        LogEntry(timestamp=now_ns + 1, level=LogLevel.ERROR, message="error msg")
    )

    response = await client.get(
        '/loki/api/v1/query?query={level="ERROR"}&limit=10'
    )
    data = response.json()
    results = data["data"]["result"]
    assert len(results) == 1
    assert results[0]["values"][0][1] == "error msg"


@pytest.mark.asyncio
async def test_query_range(client: AsyncClient, log_repo):
    now_ns = time.time_ns()
    six_hours_ns = 6 * 60 * 60 * 1_000_000_000
    for i in range(3):
        log_repo.logs.append(
            LogEntry(
                timestamp=now_ns - i * 1_000_000_000,
                level=LogLevel.INFO,
                message=f"Range log {i}",
                labels={"app": "test"},
            )
        )

    start = str(now_ns - six_hours_ns)
    end = str(now_ns + 1_000_000_000)
    response = await client.get(
        f'/loki/api/v1/query_range?query={{app="test"}}&start={start}&end={end}&limit=10'
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]["result"]) >= 1


@pytest.mark.asyncio
async def test_query_invalid_format(client: AsyncClient):
    response = await client.get(
        '/loki/api/v1/query?query=invalid&limit=10'
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["result"] == []


@pytest.mark.asyncio
async def test_get_labels(client: AsyncClient, log_repo):
    now_ns = time.time_ns()
    log_repo.logs.append(
        LogEntry(
            timestamp=now_ns,
            level=LogLevel.INFO,
            message="msg1",
            labels={"service": "api", "env": "prod"},
        )
    )
    log_repo.logs.append(
        LogEntry(
            timestamp=now_ns,
            level=LogLevel.INFO,
            message="msg2",
            labels={"service": "worker"},
        )
    )

    response = await client.get("/loki/api/v1/labels")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert sorted(data["data"]) == ["env", "service"]


@pytest.mark.asyncio
async def test_get_label_values(client: AsyncClient, log_repo):
    now_ns = time.time_ns()
    log_repo.logs.append(
        LogEntry(
            timestamp=now_ns,
            level=LogLevel.INFO,
            message="msg1",
            labels={"service": "api"},
        )
    )
    log_repo.logs.append(
        LogEntry(
            timestamp=now_ns,
            level=LogLevel.INFO,
            message="msg2",
            labels={"service": "worker"},
        )
    )
    log_repo.logs.append(
        LogEntry(
            timestamp=now_ns,
            level=LogLevel.INFO,
            message="msg3",
            labels={"service": "api"},
        )
    )

    response = await client.get("/loki/api/v1/label/service/values")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert sorted(data["data"]) == ["api", "worker"]


@pytest.mark.asyncio
async def test_get_labels_empty(client: AsyncClient):
    response = await client.get("/loki/api/v1/labels")
    assert response.status_code == 200
    assert response.json()["data"] == []
