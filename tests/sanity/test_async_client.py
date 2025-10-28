"""Tests for AsyncClient class."""

import os
import tempfile

import pytest
import pytest_asyncio
import respx
from httpx import Response

from sanity import SanityAsyncClient
from sanity.exceptions import (
    SanityAuthError,
    SanityNotFoundError,
    SanityRateLimitError,
)


@pytest.fixture
def mock_sanity_responses():
    """Fixture with realistic Sanity API mock responses."""
    return {
        "query_success": {
            "ms": 145,
            "query": "*[_type == 'author']",
            "result": [
                {
                    "_id": "author-1",
                    "_type": "author",
                    "name": "John Doe",
                    "bio": "Writer",
                },
                {
                    "_id": "author-2",
                    "_type": "author",
                    "name": "Jane Smith",
                    "bio": "Editor",
                },
            ],
            "syncTags": ["sync1"],
        },
        "mutation_success": {
            "transactionId": "tx-xyz789",
            "results": [{"id": "author-3", "operation": "create"}],
            "documentIds": ["author-3"],
        },
        "asset_success": {
            "document": {
                "_id": "image-xyz789",
                "_type": "sanity.imageAsset",
                "url": "https://cdn.sanity.io/images/test/prod/xyz789.jpg",
                "path": "images/test/prod/xyz789.jpg",
                "size": 54321,
                "sha1hash": "xyz789abc",
                "extension": "jpg",
                "mimeType": "image/jpeg",
                "originalFilename": "photo.jpg",
            }
        },
    }


@pytest_asyncio.fixture
async def async_client():
    """Create test async client."""
    client = SanityAsyncClient(
        project_id="test-project",
        dataset="test-dataset",
        token="test-token",
        use_cdn=False,
    )
    yield client
    await client.close()


class TestAsyncClientInitialization:
    """Test async client initialization."""

    @pytest.mark.asyncio
    async def test_init_with_params(self):
        """Test async client initialization."""
        async with SanityAsyncClient(
            project_id="my-project",
            dataset="staging",
            token="my-token",
            use_cdn=True,
        ) as client:
            assert client.project_id == "my-project"
            assert client.dataset == "staging"
            assert client.token == "my-token"

    @pytest.mark.asyncio
    async def test_init_without_logger(self):
        """Test that logger is optional for async client."""
        async with SanityAsyncClient(project_id="test", dataset="test") as client:
            assert client.logger is not None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async client as context manager."""
        async with SanityAsyncClient(project_id="test", dataset="test") as client:
            assert client is not None
        # Session should be closed after context


class TestAsyncQuery:
    """Test async query method."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_query_get_success(self, async_client, mock_sanity_responses):
        """Test successful async GET query."""
        route = respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset"
        ).mock(return_value=Response(200, json=mock_sanity_responses["query_success"]))

        result = await async_client.query(groq="*[_type == 'author']", method="GET")

        assert result["ms"] == 145
        assert len(result["result"]) == 2
        assert result["result"][0]["name"] == "John Doe"
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_query_post_success(self, async_client, mock_sanity_responses):
        """Test successful async POST query."""
        route = respx.post(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset"
        ).mock(return_value=Response(200, json=mock_sanity_responses["query_success"]))

        result = await async_client.query(
            groq="*[_type == $type]", variables={"type": "author"}, method="POST"
        )

        assert result["ms"] == 145
        assert len(result["result"]) == 2
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_query_with_perspective(self, async_client, mock_sanity_responses):
        """Test async query with perspective parameter."""
        route = respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset",
            params={"perspective": "drafts"},
        ).mock(return_value=Response(200, json=mock_sanity_responses["query_success"]))

        result = await async_client.query(
            groq="*[_type == 'author']", perspective="drafts", method="GET"
        )

        assert result is not None
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_query_with_result_source_map(
        self, async_client, mock_sanity_responses
    ):
        """Test async query with result_source_map parameter."""
        route = respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset",
            params={"resultSourceMap": "true"},
        ).mock(return_value=Response(200, json=mock_sanity_responses["query_success"]))

        result = await async_client.query(
            groq="*[_type == 'author']", result_source_map=True, method="GET"
        )

        assert result is not None
        assert route.called


class TestAsyncMutations:
    """Test async mutation method."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_mutate_success(self, async_client, mock_sanity_responses):
        """Test successful async mutation."""
        route = respx.post(
            "https://test-project.api.sanity.io/v2025-02-19/data/mutate/test-dataset"
        ).mock(
            return_value=Response(200, json=mock_sanity_responses["mutation_success"])
        )

        transactions = [{"create": {"_type": "author", "name": "New Author"}}]

        result = await async_client.mutate(transactions=transactions, return_ids=True)

        assert result["transactionId"] == "tx-xyz789"
        assert len(result["results"]) == 1
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_mutate_with_visibility_deferred(
        self, async_client, mock_sanity_responses
    ):
        """Test async mutation with deferred visibility."""
        route = respx.post(
            "https://test-project.api.sanity.io/v2025-02-19/data/mutate/test-dataset",
            params={"visibility": "deferred"},
        ).mock(
            return_value=Response(200, json=mock_sanity_responses["mutation_success"])
        )

        transactions = [{"create": {"_type": "author", "name": "Deferred Author"}}]

        result = await async_client.mutate(
            transactions=transactions, visibility="deferred"
        )

        assert result is not None
        assert route.called

    @pytest.mark.asyncio
    async def test_mutate_without_token(self):
        """Test that async mutation without token raises error."""
        async with SanityAsyncClient(
            project_id="test", dataset="test", token=None
        ) as client:
            transactions = [{"create": {"_type": "author"}}]

            with pytest.raises(SanityAuthError, match="API token is required"):
                await client.mutate(transactions=transactions)


class TestAsyncAssets:
    """Test async asset upload."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_assets_upload_success(self, async_client, mock_sanity_responses):
        """Test successful async asset upload."""
        route = respx.post(
            "https://test-project.api.sanity.io/v2025-02-19/assets/images/test-dataset"
        ).mock(return_value=Response(200, json=mock_sanity_responses["asset_success"]))

        # Mock file read
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"fake jpeg data")
            temp_path = f.name

        try:
            result = await async_client.assets(file_path=temp_path)
            assert result["document"]["_type"] == "sanity.imageAsset"
            assert result["document"]["mimeType"] == "image/jpeg"
            assert route.called
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_assets_without_token(self):
        """Test that async asset upload without token raises error."""
        async with SanityAsyncClient(
            project_id="test", dataset="test", token=None
        ) as client:
            with pytest.raises(SanityAuthError, match="API token is required"):
                await client.assets(file_path="/path/to/file.jpg")


class TestAsyncErrorHandling:
    """Test async error handling."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_auth_error_403(self, async_client):
        """Test 403 authentication error."""
        respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset"
        ).mock(return_value=Response(403, json={"error": "Forbidden"}))

        with pytest.raises(SanityAuthError) as exc_info:
            await async_client.query(groq="*[_type == 'author']")

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @respx.mock
    async def test_not_found_404(self, async_client):
        """Test 404 not found error."""
        respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset"
        ).mock(return_value=Response(404, json={"error": "Not found"}))

        with pytest.raises(SanityNotFoundError) as exc_info:
            await async_client.query(groq="*[_type == 'author']")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @respx.mock
    async def test_rate_limit_with_retry_after(self, async_client):
        """Test rate limit with Retry-After header."""
        respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset"
        ).mock(
            return_value=Response(
                429, json={"error": "Rate limited"}, headers={"Retry-After": "30"}
            )
        )

        with pytest.raises(SanityRateLimitError) as exc_info:
            await async_client.query(groq="*[_type == 'author']")

        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 30


class TestAsyncHistory:
    """Test async history methods."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_history_document_revision(self, async_client):
        """Test async document revision history."""
        mock_response = {
            "documents": [
                {
                    "_id": "doc-1",
                    "_rev": "rev-1",
                    "_type": "post",
                    "_createdAt": "2025-01-01T00:00:00Z",
                    "_updatedAt": "2025-01-02T00:00:00Z",
                }
            ]
        }

        route = respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/history/test-dataset/documents/doc-1"
        ).mock(return_value=Response(200, json=mock_response))

        result = await async_client.history_document_revision(document_id="doc-1")

        assert result["documents"][0]["_id"] == "doc-1"
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_history_document_transactions(self, async_client):
        """Test async document transaction history."""
        mock_response_lines = [
            '{"id": "tx-1", "timestamp": "2025-01-01T00:00:00Z"}',
            '{"id": "tx-2", "timestamp": "2025-01-02T00:00:00Z"}',
        ]

        route = respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/history/test-dataset/transactions/doc-1"
        ).mock(return_value=Response(200, text="\n".join(mock_response_lines)))

        result = await async_client.history_document_transactions(
            document_ids=["doc-1"]
        )

        assert len(result) == 2
        assert result[0]["id"] == "tx-1"
        assert route.called
