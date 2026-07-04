
class ClickHouseClient:
    def __init__(self, client):
        self._client = client

    def query(self, *args, **kwargs):
        return self._client.query(*args, **kwargs)

    def insert(self, *args, **kwargs):
        return self._client.insert(*args, **kwargs)