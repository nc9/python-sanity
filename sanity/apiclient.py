import json
import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from sanity import exceptions
from sanity.config import RetryConfig, TimeoutConfig
from sanity.retry import RetryHandler


def clean_params(params: dict):
    return {k: v for k, v in params.items() if v}


def merge_url(url: str, params: dict):
    if params and len(params) > 0:
        return url + "?" + urlencode(clean_params(params))
    return url


class ApiClient:
    def __init__(
        self,
        logger: logging.Logger,
        base_uri: str,
        token: str | None = None,
        timeout: TimeoutConfig | None = None,
        retry_config: RetryConfig | None = None,
        max_connections: int = 100,
        http2: bool = False,
        **kwargs,
    ):
        """
        Initialize API client.

        :param logger: Logger instance
        :param base_uri: The base URI to the API
        :param token: API token (optional for read-only operations)
        :param timeout: Timeout configuration
        :param retry_config: Retry configuration
        :param max_connections: Maximum number of HTTP connections
        :param http2: Enable HTTP/2 support
        """
        self.logger = logger
        self.base_uri = base_uri
        self.token = token

        for k, v in kwargs.items():
            setattr(self, k, v)

        # Use provided configs or defaults
        self.timeout_config = timeout or TimeoutConfig()
        self.retry_config = retry_config or RetryConfig()

        # Create retry handler
        self.retry_handler = RetryHandler(self.retry_config, self.logger)

        # Create httpx client with configuration
        timeout = httpx.Timeout(
            connect=self.timeout_config.connect,
            read=self.timeout_config.read,
            write=self.timeout_config.write,
            pool=self.timeout_config.pool,
        )
        limits = httpx.Limits(max_connections=max_connections)

        self.session = httpx.Client(
            timeout=timeout,
            limits=limits,
            http2=http2,
            follow_redirects=True,
        )

    @property
    def base_uri(self):
        return self._base_uri

    @base_uri.setter
    def base_uri(self, value):
        """The default base_uri"""
        if value and value.endswith("/"):
            value = value[:-1]
        self._base_uri = value

    def headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def request(
        self,
        method: str,
        url: str,
        data: Any = None,
        params: dict[str, Any] | None = None,
        content_type: str | None = None,
        load_json: bool = True,
        parse_ndjson: bool = False,
    ) -> Any:
        """
        Execute HTTP request with retry logic.

        :param method: HTTP method (GET, POST, etc.)
        :param url: URL path (will be appended to base_uri)
        :param data: Request data
        :param params: Query parameters
        :param content_type: Content-Type header
        :param load_json: Parse response as JSON
        :param parse_ndjson: Parse response as NDJSON
        :return: Response data
        :raises: SanityError subclasses on failure
        """

        def make_request():
            # Prepare data
            request_data = data
            if isinstance(data, dict):
                request_data = json.dumps(data)

            # Build full URL
            full_url = merge_url(self.base_uri + url, params)
            self.logger.info(f"{method} {full_url}")

            # Prepare headers
            h = self.headers()
            if content_type:
                h["Content-Type"] = content_type
            elif isinstance(data, dict):
                h["Content-Type"] = "application/json"

            # Make request
            try:
                response = self.session.request(
                    method=method, url=full_url, content=request_data, headers=h
                )
                response.raise_for_status()
            except httpx.TimeoutException as e:
                raise exceptions.SanityTimeoutError(
                    message=f"Request to {full_url} timed out",
                    request_details={"method": method, "url": full_url},
                ) from e
            except httpx.ConnectError as e:
                raise exceptions.SanityConnectionError(
                    message=f"Failed to connect to {full_url}",
                    request_details={"method": method, "url": full_url},
                ) from e
            except httpx.HTTPStatusError as e:
                self._handle_http_error(e, method, full_url)

            # Process response
            if response.status_code == 200:
                if load_json:
                    return response.json()
                elif parse_ndjson:
                    results = []
                    for ndjson_line in response.text.splitlines():
                        if not ndjson_line.strip():
                            continue  # ignore empty lines
                        json_line = json.loads(ndjson_line)
                        results.append(json_line)
                    return results
                else:
                    return response.text

            return response.text

        # Execute with retry logic
        return self.retry_handler.execute_with_retry(make_request, f"{method} {url}")

    def _handle_http_error(
        self, error: httpx.HTTPStatusError, method: str, url: str
    ) -> None:
        """
        Convert httpx HTTPStatusError to appropriate Sanity exception.

        :param error: HTTPStatusError from httpx
        :param method: HTTP method
        :param url: Request URL
        :raises: Appropriate SanityError subclass
        """
        status_code = error.response.status_code
        response_body = error.response.text
        request_details = {"method": method, "url": url}

        self.logger.error(f"HTTP {status_code}: {response_body}")

        if status_code == 401 or status_code == 403:
            raise exceptions.SanityAuthError(
                message=f"Authentication failed: {response_body}",
                status_code=status_code,
                response_body=response_body,
                request_details=request_details,
            ) from error
        elif status_code == 404:
            raise exceptions.SanityNotFoundError(
                message=f"Resource not found: {response_body}",
                status_code=status_code,
                response_body=response_body,
                request_details=request_details,
            ) from error
        elif status_code == 400:
            raise exceptions.SanityValidationError(
                message=f"Validation error: {response_body}",
                status_code=status_code,
                response_body=response_body,
                request_details=request_details,
            ) from error
        elif status_code == 429:
            retry_after = None
            retry_after_header = error.response.headers.get("Retry-After")
            if retry_after_header:
                try:
                    retry_after = int(retry_after_header)
                except ValueError:
                    pass

            raise exceptions.SanityRateLimitError(
                message=f"Rate limit exceeded: {response_body}",
                status_code=status_code,
                response_body=response_body,
                request_details=request_details,
                retry_after=retry_after,
            ) from error
        elif status_code >= 500:
            raise exceptions.SanityServerError(
                message=f"Server error: {response_body}",
                status_code=status_code,
                response_body=response_body,
                request_details=request_details,
            ) from error
        else:
            raise exceptions.SanityError(
                message=f"HTTP {status_code}: {response_body}",
                status_code=status_code,
                response_body=response_body,
                request_details=request_details,
            ) from error

    def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
