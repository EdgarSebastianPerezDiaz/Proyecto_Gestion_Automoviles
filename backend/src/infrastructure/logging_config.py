"""
Centralized Logging Configuration Module

Configures JSON logging for CloudWatch in production and readable format in development.
Follows AWS CloudWatch JSON schema for structured logging and easy filtering/analysis.

Environment Variables:
    FLASK_ENV: development/staging/production (determines log format)
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) - default: INFO
"""

import os
import logging
import logging.config
import json
from datetime import datetime, timezone
from typing import Dict, Any


def get_logging_config() -> Dict[str, Any]:
    """
    Get logging configuration dictionary based on environment.
    
    Returns:
        Dict with logging.config.dictConfig compatible structure
    """
    flask_env = os.getenv("FLASK_ENV", "development")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    base_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "class": "src.infrastructure.logging_config.JSONFormatter",
            },
            "simple": {
                "format": "[%(levelname)s] %(asctime)s - %(name)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "json" if flask_env == "production" else "simple",
                "stream": "ext://sys.stdout",
            },
            "console_error": {
                "class": "logging.StreamHandler",
                "level": "ERROR",
                "formatter": "json" if flask_env == "production" else "simple",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": {
            "src": {
                "level": log_level,
                "handlers": ["console", "console_error"],
                "propagate": False,
            },
            "flask": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "console_error"],
        },
    }
    
    return base_config


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for CloudWatch compatibility.
    
    Outputs structured JSON logs suitable for AWS CloudWatch Insights queries.
    Includes timestamp, level, logger name, message, and optional extra fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.
        
        Args:
            record: LogRecord from logging framework
            
        Returns:
            JSON string with log data
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Include correlation_id if available in Flask context
        try:
            from flask import g, has_request_context
            if has_request_context() and hasattr(g, 'correlation_id'):
                log_data["correlation_id"] = g.correlation_id
            else:
                # Outside request context (e.g., app startup)
                log_data["correlation_id"] = None
        except RuntimeError:
            # Called outside Flask app context
            log_data["correlation_id"] = None
        
        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "traceback": self.formatException(record.exc_info),
            }
        
        # Include extra fields if provided
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename",
                "funcName", "levelname", "levelno", "lineno",
                "module", "msecs", "message", "pathname", "process",
                "processName", "relativeCreated", "thread", "threadName",
                "exc_info", "exc_text", "asctime", "taskName",
            ]:
                log_data[key] = value
        
        return json.dumps(log_data)


def configure_logging() -> None:
    """
    Initialize logging configuration.
    
    Must be called at application startup before any logging occurs.
    Sets up JSON formatting for production and human-readable for development.
    """
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    logger = logging.getLogger(__name__)
    flask_env = os.getenv("FLASK_ENV", "development")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    logger.info(
        f"Logging configured for {flask_env} environment with level {log_level}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name, typically __name__ from calling module
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
