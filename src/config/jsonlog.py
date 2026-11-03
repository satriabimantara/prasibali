"""Structured logging: one JSON object per line on stdout (production, Gunicorn and Django share it).

No extra dependency. Only metadata is logged; satua texts are never passed to the logger.
"""

import json
import logging
from datetime import UTC, datetime

# Attributes every LogRecord has; anything else passed through `extra=` is added to the JSON object.
_RESERVED = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "request", "server_time"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # django.request / django.server pass the request and status code.
        status = getattr(record, "status_code", None)
        if status is not None:
            payload["status_code"] = status
        request = getattr(record, "request", None)
        if request is not None and hasattr(request, "method"):
            payload["method"] = request.method
            payload["path"] = getattr(request, "path", "")
        for key, value in vars(record).items():
            if key not in _RESERVED and key not in payload and not key.startswith("_"):
                payload[key] = value if isinstance(value, (str, int, float, bool, type(None))) else repr(value)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def logging_config(level: str = "INFO") -> dict:
    """dictConfig for Django (LOGGING) and Gunicorn (logconfig_dict)."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"json": {"()": "config.jsonlog.JsonFormatter"}},
        "handlers": {"stdout": {"class": "logging.StreamHandler", "formatter": "json", "stream": "ext://sys.stdout"}},
        "root": {"handlers": ["stdout"], "level": level},
        "loggers": {
            "django": {"handlers": ["stdout"], "level": level, "propagate": False},
            "gunicorn.error": {"handlers": ["stdout"], "level": level, "propagate": False},
            "gunicorn.access": {"handlers": ["stdout"], "level": "INFO", "propagate": False},
        },
    }
