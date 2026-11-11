import logging
import sys


def configure_logging(level: str = "INFO") -> logging.Logger:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        for h in root_logger.handlers:
            h.setFormatter(formatter)

    # Suppress noisy SQL/library info logs unless debugging
    logging.getLogger("uvicorn.access").setLevel(numeric_level)
    return logging.getLogger("terraqora")
