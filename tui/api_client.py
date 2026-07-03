import httpx
from typing import Any


class ApiClient:
    def __init__(self, base_url: str = "httpx://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")
        self.limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        self.timeout = httpx.Timeout(3.0, connect=2.0)

    async def fetch_logs(self, query: str, limit: int = 100) -> dict[str, Any]:
        url = f"{self.base_url}/pygrab/api/v1/query_range"
        params = {"query": query, "limit": limit}

        async with httpx.AsyncClient(limits=self.limits, timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        
    async def fetch_labels(self) -> list[str]:
        url = f"{self.base_url}/pygrab/api/v1/labels"

        async with httpx.AsyncClient(limits=self.limits, timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json().get("data", [])
        
    async def fetch_label_values(self, name: str) -> list[str]:
        url = f"{self.base_url}/pygrab/api/v1/label/{name}/values"
        
        async with httpx.AsyncClient(limits=self.limits, timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json().get("data", [])
        
    async def fetch_traces(self, limit: int = 100) -> list[dict[str, Any]]:
        return []