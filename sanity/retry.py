"""Retry logic with exponential backoff for Sanity API requests."""

import asyncio
import logging
import time
from typing import Any, Callable

import httpx

from sanity.config import RetryConfig
from sanity.exceptions import (
    SanityConnectionError,
    SanityRateLimitError,
    SanityServerError,
    SanityTimeoutError,
)


class RetryHandler:
    """Handle retries with exponential backoff."""

    def __init__(self, config: RetryConfig, logger: logging.Logger):
        """
        Initialize retry handler.

        :param config: Retry configuration
        :param logger: Logger instance
        """
        self.config = config
        self.logger = logger

    def should_retry(
        self, attempt: int, exception: Exception | None = None, status_code: int | None = None
    ) -> bool:
        """
        Determine if a request should be retried.

        :param attempt: Current attempt number (0-indexed)
        :param exception: Exception that occurred, if any
        :param status_code: HTTP status code, if any
        :return: True if should retry, False otherwise
        """
        # Check if we've exceeded max retries
        if attempt >= self.config.max_retries:
            return False

        # Retry on specified status codes
        if status_code and status_code in self.config.retry_on_status:
            return True

        # Retry on timeout errors
        if (
            self.config.retry_on_timeout
            and exception
            and isinstance(exception, (httpx.TimeoutException, SanityTimeoutError))
        ):
            return True

        # Retry on connection errors
        if (
            self.config.retry_on_connection_error
            and exception
            and isinstance(
                exception, (httpx.ConnectError, httpx.NetworkError, SanityConnectionError)
            )
        ):
            return True

        return False

    def get_backoff_time(self, attempt: int, retry_after: int | None = None) -> float:
        """
        Calculate backoff time for next retry using exponential backoff.

        :param attempt: Current attempt number (0-indexed)
        :param retry_after: Suggested retry-after time from Retry-After header
        :return: Seconds to wait before retry
        """
        if retry_after is not None:
            return float(retry_after)

        # Exponential backoff: backoff_factor * (2 ** attempt)
        # e.g., with factor 0.5: 0.5s, 1s, 2s, 4s, ...
        return self.config.backoff_factor * (2**attempt)

    def execute_with_retry(
        self, func: Callable[[], Any], operation_name: str = "request"
    ) -> Any:
        """
        Execute a synchronous function with retry logic.

        :param func: Function to execute
        :param operation_name: Name of the operation (for logging)
        :return: Function result
        :raises: Last exception if all retries fail
        """
        last_exception = None
        last_status_code = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return func()
            except httpx.HTTPStatusError as e:
                last_exception = e
                last_status_code = e.response.status_code

                retry_after = self._get_retry_after(e.response)

                if not self.should_retry(attempt, exception=e, status_code=last_status_code):
                    self.logger.error(
                        f"{operation_name} failed with status {last_status_code}, "
                        f"no more retries"
                    )
                    raise

                backoff = self.get_backoff_time(attempt, retry_after)
                self.logger.warning(
                    f"{operation_name} failed with status {last_status_code}, "
                    f"retrying in {backoff}s (attempt {attempt + 1}/{self.config.max_retries})"
                )
                time.sleep(backoff)

            except (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.NetworkError,
            ) as e:
                last_exception = e

                if not self.should_retry(attempt, exception=e):
                    self.logger.error(
                        f"{operation_name} failed with {type(e).__name__}, no more retries"
                    )
                    raise

                backoff = self.get_backoff_time(attempt)
                self.logger.warning(
                    f"{operation_name} failed with {type(e).__name__}, "
                    f"retrying in {backoff}s (attempt {attempt + 1}/{self.config.max_retries})"
                )
                time.sleep(backoff)

        # If we get here, all retries failed
        if last_exception:
            raise last_exception

    async def execute_with_retry_async(
        self, func: Callable[[], Any], operation_name: str = "request"
    ) -> Any:
        """
        Execute an async function with retry logic.

        :param func: Async function to execute
        :param operation_name: Name of the operation (for logging)
        :return: Function result
        :raises: Last exception if all retries fail
        """
        last_exception = None
        last_status_code = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return await func()
            except httpx.HTTPStatusError as e:
                last_exception = e
                last_status_code = e.response.status_code

                retry_after = self._get_retry_after(e.response)

                if not self.should_retry(attempt, exception=e, status_code=last_status_code):
                    self.logger.error(
                        f"{operation_name} failed with status {last_status_code}, "
                        f"no more retries"
                    )
                    raise

                backoff = self.get_backoff_time(attempt, retry_after)
                self.logger.warning(
                    f"{operation_name} failed with status {last_status_code}, "
                    f"retrying in {backoff}s (attempt {attempt + 1}/{self.config.max_retries})"
                )
                await asyncio.sleep(backoff)

            except (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.NetworkError,
            ) as e:
                last_exception = e

                if not self.should_retry(attempt, exception=e):
                    self.logger.error(
                        f"{operation_name} failed with {type(e).__name__}, no more retries"
                    )
                    raise

                backoff = self.get_backoff_time(attempt)
                self.logger.warning(
                    f"{operation_name} failed with {type(e).__name__}, "
                    f"retrying in {backoff}s (attempt {attempt + 1}/{self.config.max_retries})"
                )
                await asyncio.sleep(backoff)

        # If we get here, all retries failed
        if last_exception:
            raise last_exception

    def _get_retry_after(self, response: httpx.Response) -> int | None:
        """
        Extract Retry-After header from response.

        :param response: HTTP response
        :return: Seconds to wait, or None
        """
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                # Could be HTTP-date format, but we'll just return None
                return None
        return None
