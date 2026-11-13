"""日志配置：统一格式，避免重复添加 handler。"""

from __future__ import annotations

import logging
import sys

from app.core.config import Settings

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level, logging.INFO)
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.database_echo else logging.WARNING
    )
    logging.getLogger("uvicorn.access").setLevel(logging.INFO if settings.debug else level)
