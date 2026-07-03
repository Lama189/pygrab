def parse_time_ns(time_str: str | None, default_ns: int) -> int:
    if not time_str:
        return default_ns
    try:
        if "." in time_str:
            return int(float(time_str) * 1_000_000_000)
        
        val = int(time_str)
        if len(time_str) <= 11:
            return val * 1_000_000_000
        return val
    except ValueError:
        return default_ns