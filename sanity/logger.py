"""Built-in logger for Sanity Python client."""

import logging
import os
from typing import Any


class SanityLogger:
    """Default logger for Sanity client that honors SANITY_LOG_LEVEL environment variable."""

    _default_logger: logging.Logger | None = None

    @classmethod
    def get_logger(cls, name: str = "sanity") -> logging.Logger:
        """
        Get or create the default Sanity logger.

        The logger honors the SANITY_LOG_LEVEL environment variable.
        Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
        Default level: INFO

        :param name: Logger name
        :return: Configured logger instance
        """
        if cls._default_logger is not None:
            return cls._default_logger

        logger = logging.getLogger(name)

        # Only configure if no handlers exist (avoid duplicate handlers)
        if not logger.handlers:
            # Get log level from environment variable
            log_level_str = os.getenv("SANITY_LOG_LEVEL", "INFO").upper()

            # Map string to logging level
            log_level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL,
            }

            log_level = log_level_map.get(log_level_str, logging.INFO)
            logger.setLevel(log_level)

            # Create console handler with custom format
            handler = logging.StreamHandler()
            handler.setLevel(log_level)

            # Format: [SANITY] 2025-01-15 10:30:45 - INFO - message
            formatter = logging.Formatter(
                "[SANITY] %(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)

            logger.addHandler(handler)

            # Prevent propagation to root logger
            logger.propagate = False

        cls._default_logger = logger
        return logger

    @classmethod
    def reset(cls) -> None:
        """Reset the default logger (useful for testing)."""
        if cls._default_logger:
            cls._default_logger.handlers.clear()
            cls._default_logger = None


def get_logger(name: str = "sanity") -> logging.Logger:
    """
    Convenience function to get the default Sanity logger.

    :param name: Logger name
    :return: Configured logger instance
    """
    return SanityLogger.get_logger(name)
