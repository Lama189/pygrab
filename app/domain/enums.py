from enum import Enum


class LogLevel(str, Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class MatchOp(Enum):
    EQ = "eq"
    NEQ = "neq"
    RE = "re"
    NRE = "nre"


class Direction(Enum):
    FORWARD = "forward"
    BACKWARD = "backward"