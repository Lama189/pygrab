import time


def is_logql_selector(query: str) -> bool:
    start = query.find("{")
    end = query.find("}", start + 1) if start != -1 else -1
    return start != -1 and end != -1


def handle_vector_query() -> dict:
    return {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {},
                    "value": [
                        int(time.time()),
                        "2"
                    ]
                }
            ]
        }
    }
