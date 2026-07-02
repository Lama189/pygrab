import re

from app.domain.enums import LogLevel


class LogParser:
    def __init__(self) -> None:
        self._patterns = {
            LogLevel.FATAL: re.compile(r'\b(FATAL|CRITICAL)\b', re.IGNORECASE),
            LogLevel.ERROR: re.compile(r'\bERROR\b', re.IGNORECASE),
            LogLevel.WARN:  re.compile(r'\b(WARN|WARNING)\b', re.IGNORECASE),
            LogLevel.INFO:  re.compile(r'\bINFO\b', re.IGNORECASE),
            LogLevel.DEBUG: re.compile(r'\bDEBUG\b', re.IGNORECASE),
            LogLevel.TRACE: re.compile(r'\bTRACE\b', re.IGNORECASE),
        }

    def parse_level(self, message: str) -> LogLevel:
        for level, pattern in self._patterns.items():
            if pattern.search(message):
                return level
        return level.INFO
    
    