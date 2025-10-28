"""Sanity.io HTTP API Python Client"""

import logging
import mimetypes
import os
from typing import Any

import httpx

from sanity import apiclient, exceptions
from sanity.config import RetryConfig, TimeoutConfig
from sanity.logger import get_logger
from sanity.webhook import (
    contains_valid_signature,
    get_json_payload,
    parse_signature,
    timestamp_is_valid,
)


class Client(apiclient.ApiClient):
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
        Client wrapper for Sanity.io HTTP API.

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

        # Token is now optional (only required for mutations and authenticated operations)

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

    def query(
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
        Execute a GROQ query against the Sanity API.

        https://www.sanity.io/docs/http-query

        GET /data/query/<dataset>?query=<GROQ-query>
        POST /data/query/<dataset>
            {
              "query": "<the GROQ query>",
              "params": {
                "language": "es"
              }
            }

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
            return self.request(method="GET", url=url, data=None, params=params)
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

            return self.request(
                method="POST", url=url, data=payload, params=params if params else None
            )

    def mutate(
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
        Execute mutations against the Sanity API.

        https://www.sanity.io/docs/http-mutations

        POST /data/mutate/:dataset

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

        return self.request(method="POST", url=url, data=payload, params=parameters)

    def assets(self, file_path: str, mime_type: str = ""):
        """
        Upload an asset (image) to Sanity.

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
                with httpx.Client() as client:
                    response = client.get(file_path)
                    response.raise_for_status()
                    data = response.content
            except httpx.HTTPError as e:
                raise exceptions.SanityError(
                    message=f"Failed to download file from {file_path}: {str(e)}"
                ) from e
        else:
            try:
                with open(file_path, "rb") as f:
                    data = f.read()
            except OSError as e:
                raise exceptions.SanityError(
                    message=f"Failed to read file {file_path}: {str(e)}"
                ) from e

        return self.request(method="POST", url=url, data=data, content_type=mime_type)

    def history_document_revision(self, document_id, revision=None, dt=None):
        """

        GET /v2021-06-07/data/history/:dataset/documents/:documentId

        :param document_id:
        :param revision:
        :param dt: format 2019-05-28T17:18:39Z
        :return:
        :rtype: json
        """
        url = f"/data/history/{self.dataset}/documents/{document_id}"

        params = {
            "revision": revision,
            "time": dt,
        }
        try:
            return self.request(method="GET", url=url, data=None, params=params)
        except exceptions.SanityIOError as e:
            raise e

    def history_document_transactions(
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

        GET /v2021-06-07/data/history/:dataset/transactions/:document_ids

        :param document_ids: comma separated list
        :param exclude_content:
        :param from_time: format 2019-05-28T17:18:39Z
        :param to_time: format 2019-05-28T17:18:39Z
        :param from_transaction:
        :param to_transaction:
        :param authors:
        :param reverse:
        :param limit:
        :return:
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
            data = self.request(
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


# Alias for backwards compatibility
SanityClient = Client


def validate_webhook(event: dict, secret: str):
    headers = event.get("headers", {})

    timestamp, signatures = parse_signature(
        signature_header=headers.get("sanity-webhook-signature")
    )

    if not timestamp or not timestamp_is_valid(timestamp):
        return False

    return contains_valid_signature(
        payload=event["body"], timestamp=timestamp, signatures=signatures, secret=secret
    )


def parse_webhook(event: dict):
    try:
        return get_json_payload(event)
    except ValueError as err:
        raise err
