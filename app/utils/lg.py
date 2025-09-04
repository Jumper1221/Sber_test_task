from .logging_utils import ColoredFormatter

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": ColoredFormatter,
            "format": "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "uvicorn.access": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "alembic.runtime.migration": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "app": {"level": "INFO", "handlers": ["console"], "propagate": False},
    },
}
