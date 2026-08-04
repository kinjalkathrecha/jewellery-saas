import logging
import json
from django.utils import timezone
from core.middleware import get_current_request_id

class JSONFormatter(logging.Formatter):
    """
    Custom log formatter that outputs logs as structured JSON strings.
    Automatically captures the active request's correlation ID from thread-local storage,
    exception stack traces, and any extra dictionary fields.
    """
    def format(self, record):
        log_data = {
            "timestamp": timezone.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_current_request_id(),
        }

        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Merge in any extra attributes provided in logger calls (e.g. extra={"shop_id": X, "latency": Y})
        # Ignoring standard Python LogRecord parameters
        standard_attributes = {
            "args", "asctime", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "module",
            "msecs", "msg", "name", "pathname", "process", "processName",
            "relativeCreated", "stack_info", "thread", "threadName", "request"
        }

        for key, value in record.__dict__.items():
            if key not in standard_attributes:
                # Ensure the value is JSON serializable, otherwise cast to string
                try:
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, OverflowError):
                    log_data[key] = str(value)

        return json.dumps(log_data)
