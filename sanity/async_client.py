"""Async Sanity.io HTTP API Python Client"""

import json
import logging
import mimetypes
import os
from typing import Any

import httpx

from sanity import exceptions
from sanity.config import RetryConfig, TimeoutConfig
from sanity.logger import get_logger
from sanity.retry import RetryHandler


class AsyncApiClient:
    """Async base API client for HTTP operations."""

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
        Initialize async API client.

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

        # Create httpx async client with configuration
        timeout = httpx.Timeout(
            connect=self.timeout_config.connect,
            read=self.timeout_config.read,
            write=self.timeout_config.write,
            pool=self.timeout_config.pool,
        )
        limits = httpx.Limits(max_connections=max_connections)

        self.session = httpx.AsyncClient(
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

    async def request(
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
        Execute async HTTP request with retry logic.

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

        async def make_request():
            # Prepare data
            request_data = data
            if isinstance(data, dict):
                request_data = json.dumps(data)

            # Build full URL
            full_url = self._merge_url(self.base_uri + url, params)
            self.logger.info(f"{method} {full_url}")

            # Prepare headers
            h = self.headers()
            if content_type:
                h["Content-Type"] = content_type
            elif isinstance(data, dict):
                h["Content-Type"] = "application/json"

            # Make request
            try:
                response = await self.session.request(
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
        return await self.retry_handler.execute_with_retry_async(
            make_request, f"{method} {url}"
        )

    def _merge_url(self, url: str, params: dict[str, Any] | None) -> str:
        """Build URL with query parameters."""
        if params and len(params) > 0:
            from urllib.parse import urlencode

            cleaned = {k: v for k, v in params.items() if v}
            return url + "?" + urlencode(cleaned)
        return url

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

    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            await self.session.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


class SanityAsyncClient(AsyncApiClient):
    """Async Sanity.io HTTP API client."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        project_id: str | None = None,
        dataset: str | None = None,
        api_host: str | None = None,
        api_version: str = "2025-02-19",
        use_cdn: bool = True,
        token: str | None = None,
        timeout: TimeoutConfig | None = None,
        retry_config: RetryConfig | None = None,
        max_connections: int = 100,
        http2: bool = False,
    ):
        """
        Async client wrapper for Sanity.io HTTP API.

        :param logger: Logger instance (optional, will use default if not provided)
        :param project_id: Sanity Project ID
        :param dataset: Sanity project dataset to use
        :param api_host: The base URI to the API
        :param api_version: API Version to use (format YYYY-MM-DD, default: 2025-02-19)
        :param use_cdn: Use CDN endpoints for quicker responses
        :param token: API token (optional for read-only operations)
        :param timeout: Timeout configuration
        :param retry_config: Retry configuration
        :param max_connections: Maximum number of HTTP connections
        :param http2: Enable HTTP/2 support
        """
        # Use default logger if not provided
        if logger is None:
            logger = get_logger()

        # Get config from environment variables
        if not project_id:
            project_id = os.getenv("SANITY_PROJECT_ID")
        if not dataset:
            dataset = os.getenv("SANITY_DATASET")
        if not token:
            token = os.getenv("SANITY_API_TOKEN")

        # dataset defaults to production
        if not dataset:
            dataset = "production"

        # raise error on missing project_id
        if not project_id:
            raise ValueError(
                "SANITY_PROJECT_ID is required. Set via parameter or environment variable."
            )

        self.project_id = project_id
        self.dataset = dataset
        self.api_version = api_version
        self.token = token

        # API: https://<projectId>.api.sanity.io/v<YYYY-MM-DD>/<path>
        # API CDN: https://<projectId>.apicdn.sanity.io/v<YYYY-MM-DD>/<path>

        if use_cdn is True and api_host is None:
            api_host = f"https://{project_id}.apicdn.sanity.io/v{self.api_version}"
        elif use_cdn is False and api_host is None:
            api_host = f"https://{project_id}.api.sanity.io/v{self.api_version}"

        logger.debug(f"API Host: {api_host}")
        super().__init__(
            logger=logger,
            base_uri=api_host,
            token=token,
            timeout=timeout,
            retry_config=retry_config,
            max_connections=max_connections,
            http2=http2,
        )

    async def query(
        self,
        groq: str,
        variables: dict[str, Any] | None = None,
        explain: bool = False,
        perspective: str | None = None,
        result_source_map: bool = False,
        tag: str | None = None,
        return_query: bool = True,
        method: str = "GET",
    ):
        """
        Execute a GROQ query against the Sanity API (async).

        https://www.sanity.io/docs/http-query

        :param groq: Sanity GROQ Query
        :param variables: Substitutions for the groq query
        :param explain: Return the query execution plan
        :param perspective: Query perspective (raw, published, drafts, or release name)
        :param result_source_map: Include content source map metadata in results
        :param tag: Request tag for filtering log data
        :param return_query: Include submitted query in response (default: True)
        :param method: Use the GET or POST method

        :return: Query response (dict)
        :rtype: dict
        """
        url = f"/data/query/{self.dataset}"
        if method.upper() == "GET":
            params = {
                "query": groq,
                "explain": "true" if explain else "false",
                "returnQuery": "true" if return_query else "false",
            }
            if perspective:
                params["perspective"] = perspective
            if result_source_map:
                params["resultSourceMap"] = "true"
            if tag:
                params["tag"] = tag
            if variables:
                for k, v in variables.items():
                    if type(v) == str:
                        params[f"${k}"] = f'"{v}"'
                    else:
                        params[f"${k}"] = v
            return await self.request(method="GET", url=url, data=None, params=params)
        elif method.upper() == "POST":
            payload = {"query": groq}
            if variables:
                payload["params"] = variables

            # POST method uses query parameters for options
            params = {}
            if perspective:
                params["perspective"] = perspective
            if result_source_map:
                params["resultSourceMap"] = "true"
            if tag:
                params["tag"] = tag
            if explain:
                params["explain"] = "true"
            if not return_query:
                params["returnQuery"] = "false"

            return await self.request(
                method="POST", url=url, data=payload, params=params if params else None
            )

    async def mutate(
        self,
        transactions: list,
        return_ids: bool = False,
        return_documents: bool = False,
        visibility: str = "sync",
        dry_run: bool = False,
        auto_generate_array_keys: bool = False,
        skip_cross_dataset_references_validation: bool = False,
        transaction_id: str | None = None,
    ):
        """
        Execute mutations against the Sanity API (async).

        https://www.sanity.io/docs/http-mutations

        :param transactions: List of Sanity formatted transactions
        :param return_ids: Return IDs of affected documents
        :param return_documents: Return full documents after mutation
        :param visibility: sync (default), async, or deferred. Controls when response is sent.
        :param dry_run: Run mutation in test mode without committing
        :param auto_generate_array_keys: Add unique _key attributes to array items
        :param skip_cross_dataset_references_validation: Skip validation for cross-dataset references
        :param transaction_id: Custom transaction identifier

        :return: Mutation response (dict)
        :rtype: dict
        :raises SanityAuthError: If token is not set
        """
        if not self.token:
            raise exceptions.SanityAuthError(
                message="API token is required for mutations. "
                "Set via 'token' parameter or SANITY_API_TOKEN environment variable."
            )

        url = f"/data/mutate/{self.dataset}"

        parameters = {
            "returnIds": "true" if return_ids else "false",
            "returnDocuments": "true" if return_documents else "false",
            "visibility": visibility,
            "dryRun": "true" if dry_run else "false",
        }

        if auto_generate_array_keys:
            parameters["autoGenerateArrayKeys"] = "true"
        if skip_cross_dataset_references_validation:
            parameters["skipCrossDatasetReferencesValidation"] = "true"
        if transaction_id:
            parameters["transactionId"] = transaction_id

        payload = {"mutations": transactions}

        return await self.request(
            method="POST", url=url, data=payload, params=parameters
        )

    async def assets(self, file_path: str, mime_type: str = ""):
        """
        Upload an asset (image) to Sanity (async).

        POST assets/images/:dataset

        :param file_path: Image file location or web address
        :param mime_type: Force the mime type (will be guessed if not provided)

        :return: Asset response (dict)
        :rtype: dict
        :raises SanityAuthError: If token is not set
        :raises SanityError: If file download/upload fails
        """
        if not self.token:
            raise exceptions.SanityAuthError(
                message="API token is required for asset uploads. "
                "Set via 'token' parameter or SANITY_API_TOKEN environment variable."
            )

        url = f"/assets/images/{self.dataset}"

        data = None

        # Guess mime type if not provided
        if not mime_type:
            mt = mimetypes.guess_type(file_path)
            if mt and mt[0]:
                mime_type = mt[0]

        # Download from URL or read from file
        if "http" in file_path:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(file_path)
                    response.raise_for_status()
                    data = response.content
            except httpx.HTTPError as e:
                raise exceptions.SanityError(
                    message=f"Failed to download file from {file_path}: {str(e)}"
                ) from e
        else:
            try:
                # Read file asynchronously using aiofiles would be ideal,
                # but for now we'll use sync read since it's simple
                with open(file_path, "rb") as f:
                    data = f.read()
            except OSError as e:
                raise exceptions.SanityError(
                    message=f"Failed to read file {file_path}: {str(e)}"
                ) from e

        return await self.request(
            method="POST", url=url, data=data, content_type=mime_type
        )

    async def history_document_revision(self, document_id, revision=None, dt=None):
        """
        Get document revision history (async).

        GET /v2021-06-07/data/history/:dataset/documents/:documentId

        :param document_id: Document ID
        :param revision: Specific revision ID
        :param dt: Timestamp format 2019-05-28T17:18:39Z
        :return: History response (dict)
        :rtype: dict
        """
        url = f"/data/history/{self.dataset}/documents/{document_id}"

        params = {
            "revision": revision,
            "time": dt,
        }
        try:
            return await self.request(method="GET", url=url, data=None, params=params)
        except exceptions.SanityIOError as e:
            raise e

    async def history_document_transactions(
        self,
        document_ids: list,
        exclude_content=True,
        from_time=None,
        to_time=None,
        from_transaction=None,
        to_transaction=None,
        authors=None,
        reverse=False,
        limit=100,
    ):
        """
        Get document transaction history (async).

        GET /v2021-06-07/data/history/:dataset/transactions/:document_ids

        :param document_ids: comma separated list
        :param exclude_content: Exclude content from response
        :param from_time: format 2019-05-28T17:18:39Z
        :param to_time: format 2019-05-28T17:18:39Z
        :param from_transaction: Transaction ID to start from
        :param to_transaction: Transaction ID to end at
        :param authors: Filter by authors
        :param reverse: Reverse chronological order
        :param limit: Limit number of results
        :return: Transaction history (list)
        :rtype: list
        """
        doc_ids = ",".join(document_ids)
        url = f"/data/history/{self.dataset}/transactions/{doc_ids}"

        params = {
            "excludeContent": exclude_content,
            "fromTime": from_time,
            "toTime": to_time,
            "fromTransaction": from_transaction,
            "toTransaction": to_transaction,
            "authors": authors,
            "reverse": reverse,
            "limit": limit,
        }
        try:
            data = await self.request(
                method="GET",
                url=url,
                data=None,
                params=params,
                load_json=False,
                parse_ndjson=True,
            )
            return data
        except exceptions.SanityIOError as e:
            raise e
