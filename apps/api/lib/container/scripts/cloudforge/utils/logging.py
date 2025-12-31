# apps/api/sandbox-modules/cloudforge/utils/logging.py
"""
Logging configuration.
"""

import sys
import structlog
from typing import Optional


def setup_logging(level: str = "INFO", json_output: bool = False) -> None:
    """Configure structured logging."""
    
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog, level.upper(), structlog.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class Logger:
    """Simple logger wrapper for convenience."""
    
    def __init__(self, name: str):
        """Initialize logger with name."""
        self._logger = structlog.get_logger(name)
    
    def debug(self, message: str, **kwargs) -> None:
        self._logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        self._logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        self._logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        self._logger.error(message, **kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        self._logger.exception(message, **kwargs)


# Initialize logging on import
setup_logging()
