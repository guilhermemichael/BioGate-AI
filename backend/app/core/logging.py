import json
import logging
from datetime import datetime, timezone
from typing import Any


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def log_json(event: str, **payload: Any) -> None:
    logger = logging.getLogger("biogate")
    message = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **payload,
    }
    logger.info(json.dumps(message, default=str))
