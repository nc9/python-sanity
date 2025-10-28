"""
Python wrapper around the Sanity.io HTTP API

Homepage: https://github.com/nc9/python-sanity
PyPI: https://pypi.org/project/python-sanity/
Documentation: https://python-sanity.readthedocs.io/

MIT License

Copyright (c) 2025 Nik Cubrilovic, OmniPro-Group

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
"""

from sanity.async_client import AsyncClient
from sanity.client import Client, SanityClient
from sanity.config import ClientConfig, RetryConfig, TimeoutConfig
from sanity.exceptions import (
    SanityAuthError,
    SanityConnectionError,
    SanityError,
    SanityIOError,
    SanityNotFoundError,
    SanityRateLimitError,
    SanityServerError,
    SanityTimeoutError,
    SanityValidationError,
)
from sanity.logger import get_logger
from sanity.models import (
    AssetDocument,
    AssetResponse,
    HistoryResponse,
    HistoryRevision,
    MutationResponse,
    MutationResult,
    QueryResponse,
    TransactionHistoryItem,
    TransactionHistoryResponse,
)

__version__ = "0.2.0"

__all__ = [
    # Clients
    "Client",
    "SanityClient",
    "AsyncClient",
    # Configuration
    "ClientConfig",
    "TimeoutConfig",
    "RetryConfig",
    # Exceptions
    "SanityError",
    "SanityIOError",
    "SanityAuthError",
    "SanityNotFoundError",
    "SanityValidationError",
    "SanityRateLimitError",
    "SanityTimeoutError",
    "SanityServerError",
    "SanityConnectionError",
    # Models
    "QueryResponse",
    "MutationResponse",
    "MutationResult",
    "AssetResponse",
    "AssetDocument",
    "HistoryResponse",
    "HistoryRevision",
    "TransactionHistoryItem",
    "TransactionHistoryResponse",
    # Logger
    "get_logger",
]
