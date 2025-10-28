"""Pydantic models for Sanity API responses."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class QueryResponse(BaseModel):
    """Response model for GROQ query endpoint."""

    model_config = ConfigDict(extra="allow")

    ms: int = Field(..., description="Server-side processing time in milliseconds")
    query: str | None = Field(
        None, description="The submitted GROQ query (if returnQuery=true)"
    )
    result: Any = Field(..., description="Query result (can be any valid JSON value)")
    sync_tags: List[str] | None = Field(
        None,
        alias="syncTags",
        description="Array of tags for request filtering and aggregation",
    )

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Return dict representation for backward compatibility."""
        return super().model_dump(*args, **kwargs)


class MutationResult(BaseModel):
    """Individual mutation result within a transaction."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Document ID affected by this mutation")
    operation: str = Field(
        ..., description="Operation type (create, update, delete, etc.)"
    )
    document: Dict[str, Any] | None = Field(
        None, description="Full document (if returnDocuments=true)"
    )


class MutationResponse(BaseModel):
    """Response model for mutation endpoint."""

    model_config = ConfigDict(extra="allow")

    transaction_id: str = Field(
        ..., alias="transactionId", description="Unique transaction identifier"
    )
    results: List[Dict[str, Any]] = Field(..., description="Array of mutation results")
    document_ids: List[str] | None = Field(
        None, alias="documentIds", description="IDs of affected documents"
    )
    documents: List[Dict[str, Any]] | None = Field(
        None, description="Full documents (if returnDocuments=true)"
    )

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Return dict representation for backward compatibility."""
        return super().model_dump(*args, **kwargs)


class AssetDocument(BaseModel):
    """Asset document structure."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., alias="_id", description="Asset ID")
    type: str = Field(..., alias="_type", description="Asset type (sanity.imageAsset)")
    url: str = Field(..., description="Asset URL")
    path: str = Field(..., description="Asset path")
    size: int = Field(..., description="File size in bytes")
    sha1hash: str = Field(..., description="SHA1 hash of the file")
    extension: str = Field(..., description="File extension")
    mime_type: str = Field(..., alias="mimeType", description="MIME type")
    original_filename: str | None = Field(
        None, alias="originalFilename", description="Original filename"
    )
    metadata: Dict[str, Any] | None = Field(
        None, description="Asset metadata (dimensions, etc.)"
    )


class AssetResponse(BaseModel):
    """Response model for asset upload endpoint."""

    model_config = ConfigDict(extra="allow")

    document: AssetDocument = Field(..., description="Uploaded asset document")

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Return dict representation for backward compatibility."""
        return super().model_dump(*args, **kwargs)


class HistoryRevision(BaseModel):
    """Document revision in history."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., alias="_id", description="Document ID")
    rev: str = Field(..., alias="_rev", description="Revision ID")
    type: str = Field(..., alias="_type", description="Document type")
    created_at: str = Field(..., alias="_createdAt", description="Creation timestamp")
    updated_at: str = Field(..., alias="_updatedAt", description="Update timestamp")


class HistoryResponse(BaseModel):
    """Response model for document history endpoint."""

    model_config = ConfigDict(extra="allow")

    documents: List[HistoryRevision] = Field(
        ..., description="Array of document revisions"
    )

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Return dict representation for backward compatibility."""
        return super().model_dump(*args, **kwargs)


class TransactionHistoryItem(BaseModel):
    """Single transaction in document history."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Transaction ID")
    timestamp: str = Field(..., description="Transaction timestamp")
    author: str | None = Field(None, description="Author of the transaction")
    document_ids: List[str] | None = Field(
        None, alias="documentIDs", description="Affected document IDs"
    )
    mutations: List[Dict[str, Any]] | None = Field(
        None, description="Mutations in this transaction"
    )


class TransactionHistoryResponse(BaseModel):
    """Response model for transaction history (typically NDJSON)."""

    model_config = ConfigDict(extra="allow")

    transactions: List[TransactionHistoryItem] = Field(
        ..., description="Array of transactions"
    )

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Return dict representation for backward compatibility."""
        return super().model_dump(*args, **kwargs)
