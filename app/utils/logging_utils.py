import logging

# ANSI-цвета по уровням
LOG_COLORS = {
    "DEBUG": "\033[36m",  # голубой
    "INFO": "\033[32m",  # зелёный
    "WARNING": "\033[33m",  # жёлтый
    "ERROR": "\033[31m",  # красный
    "CRITICAL": "\033[41m",  # белый на красном фоне
}
RESET_COLOR = "\033[0m"


class ColoredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_color = LOG_COLORS.get(record.levelname, "")
        record.levelname = f"{log_color}{record.levelname}{RESET_COLOR}"
        return super().format(record)
