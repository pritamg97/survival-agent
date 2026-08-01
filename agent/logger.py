import logging
import os
import sys

from pythonjsonlogger import jsonlogger

from agent.config import CONFIG


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("survival-agent")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if logger.handlers:
        return logger

    os.makedirs(os.path.dirname(CONFIG.LOG_FILE) or ".", exist_ok=True)

    file_handler = logging.FileHandler(CONFIG.LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(pathname)s %(lineno)d %(message)s"
        )
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, CONFIG.LOG_LEVEL.upper(), logging.INFO))
    console_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)-7s %(message)s", "%H:%M:%S")
    )

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


LOGGER = setup_logger()
