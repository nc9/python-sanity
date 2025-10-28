"""Tests for Pydantic response models."""

import pytest
from pydantic import ValidationError

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


class TestQueryResponse:
    """Test QueryResponse model."""

    def test_valid_query_response(self):
        """Test valid query response parsing."""
        data = {
            "ms": 150,
            "query": "*[_type == 'post']",
            "result": [{"_id": "post-1", "title": "Hello"}],
            "syncTags": ["tag1", "tag2"],
        }

        response = QueryResponse(**data)

        assert response.ms == 150
        assert response.query == "*[_type == 'post']"
        assert len(response.result) == 1
        assert response.sync_tags == ["tag1", "tag2"]

    def test_query_response_without_optional_fields(self):
        """Test query response without optional fields."""
        data = {
            "ms": 100,
            "result": {"count": 5},
        }

        response = QueryResponse(**data)

        assert response.ms == 100
        assert response.result == {"count": 5}
        assert response.query is None
        assert response.sync_tags is None

    def test_query_response_dict_method(self):
        """Test dict() method for backward compatibility."""
        data = {"ms": 100, "result": []}

        response = QueryResponse(**data)
        result_dict = response.dict()

        assert isinstance(result_dict, dict)
        assert result_dict["ms"] == 100

    def test_query_response_missing_required_field(self):
        """Test validation error on missing required field."""
        data = {"result": []}  # Missing 'ms' field

        with pytest.raises(ValidationError):
            QueryResponse(**data)


class TestMutationResponse:
    """Test MutationResponse model."""

    def test_valid_mutation_response(self):
        """Test valid mutation response parsing."""
        data = {
            "transactionId": "tx-12345",
            "results": [
                {"id": "doc-1", "operation": "create"},
                {"id": "doc-2", "operation": "update"},
            ],
            "documentIds": ["doc-1", "doc-2"],
            "documents": [
                {"_id": "doc-1", "_type": "post"},
                {"_id": "doc-2", "_type": "author"},
            ],
        }

        response = MutationResponse(**data)

        assert response.transaction_id == "tx-12345"
        assert len(response.results) == 2
        assert response.document_ids == ["doc-1", "doc-2"]
        assert len(response.documents) == 2

    def test_mutation_response_without_optional_fields(self):
        """Test mutation response without optional fields."""
        data = {
            "transactionId": "tx-67890",
            "results": [{"id": "doc-3", "operation": "delete"}],
        }

        response = MutationResponse(**data)

        assert response.transaction_id == "tx-67890"
        assert response.document_ids is None
        assert response.documents is None

    def test_mutation_response_dict_method(self):
        """Test dict() method."""
        data = {"transactionId": "tx-test", "results": []}

        response = MutationResponse(**data)
        result_dict = response.dict()

        assert isinstance(result_dict, dict)
        assert result_dict["transaction_id"] == "tx-test"


class TestAssetResponse:
    """Test AssetResponse and AssetDocument models."""

    def test_valid_asset_response(self):
        """Test valid asset response parsing."""
        data = {
            "document": {
                "_id": "image-abc123",
                "_type": "sanity.imageAsset",
                "url": "https://cdn.sanity.io/images/proj/dataset/abc123.png",
                "path": "images/proj/dataset/abc123.png",
                "size": 54321,
                "sha1hash": "abc123def",
                "extension": "png",
                "mimeType": "image/png",
                "originalFilename": "test.png",
                "metadata": {"dimensions": {"width": 800, "height": 600}},
            }
        }

        response = AssetResponse(**data)

        assert response.document.id == "image-abc123"
        assert response.document.type == "sanity.imageAsset"
        assert response.document.url.startswith("https://")
        assert response.document.size == 54321
        assert response.document.mime_type == "image/png"
        assert response.document.metadata["dimensions"]["width"] == 800

    def test_asset_response_without_metadata(self):
        """Test asset response without metadata."""
        data = {
            "document": {
                "_id": "file-xyz",
                "_type": "sanity.fileAsset",
                "url": "https://cdn.sanity.io/files/proj/dataset/xyz.pdf",
                "path": "files/proj/dataset/xyz.pdf",
                "size": 12345,
                "sha1hash": "xyz789",
                "extension": "pdf",
                "mimeType": "application/pdf",
            }
        }

        response = AssetResponse(**data)

        assert response.document.id == "file-xyz"
        assert response.document.original_filename is None
        assert response.document.metadata is None


class TestHistoryResponse:
    """Test HistoryResponse and HistoryRevision models."""

    def test_valid_history_response(self):
        """Test valid history response parsing."""
        data = {
            "documents": [
                {
                    "_id": "doc-1",
                    "_rev": "rev-abc",
                    "_type": "post",
                    "_createdAt": "2025-01-01T00:00:00Z",
                    "_updatedAt": "2025-01-02T00:00:00Z",
                },
                {
                    "_id": "doc-2",
                    "_rev": "rev-def",
                    "_type": "author",
                    "_createdAt": "2025-01-03T00:00:00Z",
                    "_updatedAt": "2025-01-04T00:00:00Z",
                },
            ]
        }

        response = HistoryResponse(**data)

        assert len(response.documents) == 2
        assert response.documents[0].id == "doc-1"
        assert response.documents[0].rev == "rev-abc"
        assert response.documents[0].type == "post"
        assert response.documents[1].id == "doc-2"


class TestTransactionHistoryResponse:
    """Test TransactionHistoryResponse and TransactionHistoryItem models."""

    def test_valid_transaction_history_response(self):
        """Test valid transaction history response parsing."""
        data = {
            "transactions": [
                {
                    "id": "tx-1",
                    "timestamp": "2025-01-01T00:00:00Z",
                    "author": "user-123",
                    "documentIDs": ["doc-1", "doc-2"],
                    "mutations": [{"create": {"_type": "post"}}],
                },
                {
                    "id": "tx-2",
                    "timestamp": "2025-01-02T00:00:00Z",
                    "author": "user-456",
                },
            ]
        }

        response = TransactionHistoryResponse(**data)

        assert len(response.transactions) == 2
        assert response.transactions[0].id == "tx-1"
        assert response.transactions[0].author == "user-123"
        assert response.transactions[0].document_ids == ["doc-1", "doc-2"]
        assert len(response.transactions[0].mutations) == 1
        assert response.transactions[1].document_ids is None


class TestExtraFieldsHandling:
    """Test that models allow extra fields from Sanity API."""

    def test_query_response_with_extra_fields(self):
        """Test that extra fields are preserved."""
        data = {
            "ms": 100,
            "result": [],
            "extra_field": "extra_value",
            "another_field": 123,
        }

        response = QueryResponse(**data)

        assert response.ms == 100
        # Extra fields should be allowed due to model_config

    def test_asset_document_with_extra_metadata(self):
        """Test asset with extra metadata fields."""
        data = {
            "document": {
                "_id": "image-1",
                "_type": "sanity.imageAsset",
                "url": "https://example.com/image.png",
                "path": "images/image.png",
                "size": 1000,
                "sha1hash": "hash",
                "extension": "png",
                "mimeType": "image/png",
                "customField": "custom value",
                "metadata": {
                    "dimensions": {"width": 100, "height": 100},
                    "custom_metadata": "value",
                },
            }
        }

        response = AssetResponse(**data)

        assert response.document.id == "image-1"
        assert response.document.metadata["custom_metadata"] == "value"
