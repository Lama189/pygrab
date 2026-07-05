import json
from typing import Any

from app.application.schemas.otlp import ExportTraceServiceRequest, OtlpKeyValue, OtlpSpan
from app.domain.models import SpanModel, SpanEventModel


def parse_otlp_attributes(attributes: list[OtlpKeyValue]) -> dict[str, str]:
    result = {}
    if not attributes:
        return result
    
    for attr in attributes:
        key = attr.key
        val_obj = attr.value

        if "stringValue" in val_obj:
            result[key] = str(val_obj["stringValue"])
        elif "intValue" in val_obj:
            result[key] = str(val_obj["intValue"])
        elif "boolValue" in val_obj:
            result[key] = str(val_obj["boolValue"]).lower()
        elif "doubleValue" in val_obj:
            result[key] = str(val_obj["doubleValue"])
        else:
            result[key] = json.dumps(val_obj)
    
    return result


def convert_otlp_to_domain(request: ExportTraceServiceRequest) -> list[SpanModel]:
    domain_spans: list[SpanModel] = []

    for resource_span in request.resourceSpans:
        resource_attrs = parse_otlp_attributes(resource_span.resource.attributes)
        service_name = resource_attrs.get("service.name", "unknown_service")

        for scope_span in resource_span.scopeSpans:
            for span in scope_span.spans:
                span_attrs = parse_otlp_attributes(span.attributes)
                full_attrs = {**resource_attrs, **span_attrs}
                parent_id = span.parentSpanId if span.parentSpanId else None
                
                status_str = "UNSET"
                if span.status:
                    if span.status.code == 1:
                        status_str = "OK"
                    elif span.status.code == 2:
                        status_str = "ERROR"
                
                if full_attrs.get("error") == "true":
                    status_str = "ERROR"

                domain_events: list[SpanEventModel] = []
                if span.events:
                    for ev in span.events:
                        event_attrs = parse_otlp_attributes(ev.attributes)
                        domain_events.append(
                            SpanEventModel(
                                name=ev.name,
                                timestamp_ns=int(ev.timeUnixNano),
                                attributes=event_attrs
                            )
                        )

                domain_spans.append(
                    SpanModel(
                        trace_id=span.traceId,
                        span_id=span.spanId,
                        parent_span_id=parent_id,
                        operation_name=span.name,
                        service_name=service_name,
                        start_time_ns=int(span.startTimeUnixNano),
                        end_time_ns=int(span.endTimeUnixNano),
                        status=status_str,
                        attributes=full_attrs,
                        events=domain_events
                    )
                )
                
    return domain_spans