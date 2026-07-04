-- migrate:up
CREATE TABLE IF NOT EXISTS pygrab_db.spans (
    trace_id String,
    span_id String,
    parent_span_id Nullable(String),
    operation_name String,
    service_name String,
    start_time DateTime64(9, 'UTC'),
    end_time DateTime64(9, 'UTC'),
    status LowCardinality(String),
    attributes Map(String, String),
    events String
) ENGINE = MergeTree()
ORDER BY (service_name, start_time, trace_id);

-- migrate:down
DROP TABLE IF EXISTS spans;
