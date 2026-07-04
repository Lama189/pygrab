from pydantic import BaseModel, Field
from typing import Any


class OtlpKeyValue(BaseModel):
    key: str
    value: dict[str, Any]


class OtlpEvent(BaseModel):
    timeUnixNano: str
    name: str
    attributes: list["OtlpKeyValue"] = Field(default_factory=list)


class OtlpStatus(BaseModel):
    code: int
    message: str = ""


class OtlpSpan(BaseModel):
    traceId: str
    spanId: str
    parentSpanId: str | None = None
    name: str
    kind: int
    startTimeUnixNano: str
    endTimeUnixNano: str
    attributes: list["OtlpKeyValue"] = Field(default_factory=list)
    events: list["OtlpEvent"] = Field(default_factory=list)
    status: OtlpStatus | None = None


class OtlpScopeSpan(BaseModel):
    scope: dict[str, Any] | None = None
    spans: list[OtlpSpan]


class OtlpResource(BaseModel):
    attributes: list["OtlpKeyValue"] = Field(default_factory=list)


class OtlpResourceSpan(BaseModel):
    resource: OtlpResource
    scopeSpans: list[OtlpScopeSpan]


class ExportTraceServiceRequest(BaseModel):
    resourceSpans: list[OtlpResourceSpan]