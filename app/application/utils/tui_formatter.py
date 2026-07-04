from datetime import datetime, timezone
from typing import Any

def format_logs_for_tui(logs: list[Any]) -> list[dict[str, Any]]:
    formatted_logs = []
    
    for e in logs:
        dt = datetime.fromtimestamp(e.timestamp / 1_000_000_000, tz=timezone.utc)
        iso_timestamp = dt.isoformat().replace("+00:00", "Z")
        level_formatted = e.level.value if hasattr(e.level, "value") else str(e.level)
        level_formatted = level_formatted.upper()

        clean_msg = e.message
        prefixes = [
            f"{level_formatted}:", 
            f"{level_formatted} ", 
            f"{level_formatted.lower()}:", 
            f"{level_formatted.lower()} |", 
            f"{level_formatted.lower()} "
        ]
        for prefix in prefixes:
            if clean_msg.lstrip().startswith(prefix):
                clean_msg = clean_msg.lstrip()[len(prefix):].lstrip()
                break

        labels = dict(e.labels) if e.labels else {}
        if not any(k in labels for k in ["container_name", "service", "container"]):
            extracted_name = labels.get("app") or labels.get("job") or labels.get("stream") or "pygrab-api"
            labels["container_name"] = extracted_name

        t_id = e.trace_id if e.trace_id and e.trace_id.strip() else None
        s_id = e.span_id if e.span_id and e.span_id.strip() else None

        formatted_logs.append({
            "timestamp": iso_timestamp,
            "level": level_formatted,  
            "message": clean_msg, 
            "labels": labels,    
            "trace_id": t_id,
            "span_id": s_id
        })

    return formatted_logs