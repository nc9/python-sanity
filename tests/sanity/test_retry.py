"""Tests for retry logic."""

import logging
from unittest.mock import Mock

import httpx
import pytest

from sanity.config import RetryConfig
from sanity.retry import RetryHandler


@pytest.fixture
def logger():
    """Create test logger."""
    return logging.getLogger("test")


@pytest.fixture
def retry_config():
    """Create test retry configuration."""
    return RetryConfig(
        max_retries=3, backoff_factor=0.1, retry_on_status=[429, 500, 502, 503]
    )


@pytest.fixture
def retry_handler(logger, retry_config):
    """Create retry handler."""
    return RetryHandler(retry_config, logger)


class TestShouldRetry:
    """Test should_retry logic."""

    def test_should_retry_on_429(self, retry_handler):
        """Test retry on 429 status."""
        assert retry_handler.should_retry(0, status_code=429)
        assert retry_handler.should_retry(1, status_code=429)
        assert retry_handler.should_retry(2, status_code=429)
        assert not retry_handler.should_retry(3, status_code=429)  # Max retries reached

    def test_should_retry_on_500(self, retry_handler):
        """Test retry on 500 status."""
        assert retry_handler.should_retry(0, status_code=500)

    def test_should_not_retry_on_400(self, retry_handler):
        """Test no retry on 400 status."""
        assert not retry_handler.should_retry(0, status_code=400)

    def test_should_not_retry_on_404(self, retry_handler):
        """Test no retry on 404 status."""
        assert not retry_handler.should_retry(0, status_code=404)

    def test_should_retry_on_timeout(self, retry_handler):
        """Test retry on timeout exception."""
        exception = httpx.TimeoutException("Request timed out")
        assert retry_handler.should_retry(0, exception=exception)

    def test_should_retry_on_connection_error(self, retry_handler):
        """Test retry on connection error."""
        exception = httpx.ConnectError("Connection failed")
        assert retry_handler.should_retry(0, exception=exception)

    def test_should_not_retry_when_disabled(self, logger):
        """Test no retry when retry is disabled."""
        config = RetryConfig(retry_on_timeout=False, retry_on_connection_error=False)
        handler = RetryHandler(config, logger)

        timeout_exception = httpx.TimeoutException("Timeout")
        connection_exception = httpx.ConnectError("Connection error")

        assert not handler.should_retry(0, exception=timeout_exception)
        assert not handler.should_retry(0, exception=connection_exception)


class TestBackoffTime:
    """Test backoff time calculation."""

    def test_backoff_with_retry_after(self, retry_handler):
        """Test backoff uses Retry-After when provided."""
        backoff = retry_handler.get_backoff_time(0, retry_after=60)
        assert backoff == 60.0

    def test_exponential_backoff(self, retry_handler):
        """Test exponential backoff calculation."""
        # backoff_factor=0.1, so: 0.1 * 2^attempt
        assert retry_handler.get_backoff_time(0) == 0.1  # 0.1 * 2^0
        assert retry_handler.get_backoff_time(1) == 0.2  # 0.1 * 2^1
        assert retry_handler.get_backoff_time(2) == 0.4  # 0.1 * 2^2
        assert retry_handler.get_backoff_time(3) == 0.8  # 0.1 * 2^3


class TestExecuteWithRetry:
    """Test execute_with_retry for sync operations."""

    def test_success_on_first_try(self, retry_handler):
        """Test successful execution on first attempt."""
        mock_func = Mock(return_value="success")

        result = retry_handler.execute_with_retry(mock_func, "test operation")

        assert result == "success"
        assert mock_func.call_count == 1

    def test_success_after_retries(self, retry_handler):
        """Test successful execution after retries."""
        mock_func = Mock(side_effect=[
            httpx.HTTPStatusError(
                "Rate limited",
                request=Mock(),
                response=Mock(status_code=429, headers={}),
            ),
            httpx.HTTPStatusError(
                "Rate limited",
                request=Mock(),
                response=Mock(status_code=429, headers={}),
            ),
            "success",
        ])

        result = retry_handler.execute_with_retry(mock_func, "test operation")

        assert result == "success"
        assert mock_func.call_count == 3

    def test_failure_after_max_retries(self, retry_handler):
        """Test failure after max retries exhausted."""
        mock_func = Mock(side_effect=httpx.HTTPStatusError(
            "Rate limited",
            request=Mock(),
            response=Mock(status_code=429, headers={}),
        ))

        with pytest.raises(httpx.HTTPStatusError):
            retry_handler.execute_with_retry(mock_func, "test operation")

        # Should try: initial + 3 retries = 4 times
        assert mock_func.call_count == 4

    def test_no_retry_on_non_retryable_error(self, retry_handler):
        """Test no retry on non-retryable error."""
        mock_func = Mock(side_effect=httpx.HTTPStatusError(
            "Bad request",
            request=Mock(),
            response=Mock(status_code=400, headers={}),
        ))

        with pytest.raises(httpx.HTTPStatusError):
            retry_handler.execute_with_retry(mock_func, "test operation")

        # Should only try once (no retries)
        assert mock_func.call_count == 1


class TestExecuteWithRetryAsync:
    """Test execute_with_retry_async for async operations."""

    @pytest.mark.asyncio
    async def test_async_success_on_first_try(self, retry_handler):
        """Test successful async execution on first attempt."""

        async def mock_async_func():
            return "async success"

        result = await retry_handler.execute_with_retry_async(
            mock_async_func, "test async operation"
        )

        assert result == "async success"

    @pytest.mark.asyncio
    async def test_async_success_after_retries(self, retry_handler):
        """Test successful async execution after retries."""
        call_count = 0

        async def mock_async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.HTTPStatusError(
                    "Server error",
                    request=Mock(),
                    response=Mock(status_code=500, headers={}),
                )
            return "async success"

        result = await retry_handler.execute_with_retry_async(
            mock_async_func, "test async operation"
        )

        assert result == "async success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_failure_after_max_retries(self, retry_handler):
        """Test async failure after max retries."""

        async def mock_async_func():
            raise httpx.HTTPStatusError(
                "Server error",
                request=Mock(),
                response=Mock(status_code=500, headers={}),
            )

        with pytest.raises(httpx.HTTPStatusError):
            await retry_handler.execute_with_retry_async(
                mock_async_func, "test async operation"
            )

    @pytest.mark.asyncio
    async def test_async_timeout_retry(self, retry_handler):
        """Test async retry on timeout."""
        call_count = 0

        async def mock_async_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Request timed out")
            return "success after timeout"

        result = await retry_handler.execute_with_retry_async(
            mock_async_func, "test timeout"
        )

        assert result == "success after timeout"
        assert call_count == 2


class TestGetRetryAfter:
    """Test Retry-After header extraction."""

    def test_get_retry_after_with_valid_header(self, retry_handler):
        """Test extraction of valid Retry-After header."""
        response = Mock()
        response.headers = {"Retry-After": "120"}

        retry_after = retry_handler._get_retry_after(response)
        assert retry_after == 120

    def test_get_retry_after_with_invalid_header(self, retry_handler):
        """Test extraction with invalid Retry-After header."""
        response = Mock()
        response.headers = {"Retry-After": "invalid"}

        retry_after = retry_handler._get_retry_after(response)
        assert retry_after is None

    def test_get_retry_after_missing_header(self, retry_handler):
        """Test extraction with missing Retry-After header."""
        response = Mock()
        response.headers = {}

        retry_after = retry_handler._get_retry_after(response)
        assert retry_after is None
