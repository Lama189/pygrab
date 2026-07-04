import httpx


class ApiClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        self.timeout = httpx.Timeout(3.0, connect=2.0)

    async def fetch_logs(
        self,
        query: str,
        limit: int = 200,
        start_ns: int | None = None,
    ) -> dict:
        url = f"{self.base_url}/pygrab/api/v1/query_range"
        params = {"query": query, "limit": limit}

        if start_ns:
            params["end"] = str(start_ns)

        async with httpx.AsyncClient(limits=self.limits, timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def fetch_labels(self) -> list[str]:
        url = f"{self.base_url}/pygrab/api/v1/labels"

        async with httpx.AsyncClient(limits=self.limits, timeout=self.timeout) as client:
            response = await client.get(url)
            return response.json().get("data", [])

    async def fetch_label_values(self, name: str) -> list[str]:
        url = f"{self.base_url}/pygrab/api/v1/label/{name}/values"

        async with httpx.AsyncClient(limits=self.limits, timeout=self.timeout) as client:
            response = await client.get(url)
            return response.json().get("data", [])

    async def fetch_traces(self, limit: int = 200) -> list[dict]:
        return []