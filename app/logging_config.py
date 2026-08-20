"""One-line JSON logs so they can be shipped to Loki/CloudWatch later."""

import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Anything passed as logger.info("msg", extra={"extra_data": {...}})
        if hasattr(record, "extra_data"):
            data.update(record.extra_data)
        if record.exc_info:
            data["error"] = self.formatException(record.exc_info)
        return json.dumps(data)


def setup_logging(level="INFO"):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # uvicorn is noisy by default
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name):
    return logging.getLogger(name)
