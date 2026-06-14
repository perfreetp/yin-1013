import sys
from loguru import logger
from app.config import settings


def setup_logger():
    logger.remove()

    format_str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<magenta>{extra[request_id]}</magenta> | "
        "<level>{message}</level>"
    )

    logger.configure(extra={"request_id": "N/A"})

    logger.add(
        sys.stdout,
        level="INFO" if not settings.APP_DEBUG else "DEBUG",
        format=format_str,
        colorize=True,
        enqueue=True
    )

    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        level="INFO",
        format=format_str,
        enqueue=True
    )

    logger.add(
        "logs/error_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        compression="zip",
        level="ERROR",
        format=format_str,
        enqueue=True
    )

    return logger


logger = setup_logger()
