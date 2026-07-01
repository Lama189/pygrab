-- migrate:up
CREATE TABLE IF NOT EXISTS pygrab_db.logs (
    timestamp DateTime64(9, 'UTC'),
    level Enum8('TRACE'=1, 'DEBUG'=2, 'INFO'=3, 'WARN'=4, 'ERROR'=5, 'FATAL'=6),
    message String,
    labels Map(String, String),
    trace_id String DEFAULT '',
    span_id String DEFAULT ''
)

-- migrate:down
DROP TABLE IF EXISTS pygrab_db.logs;
