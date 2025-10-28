"""Tests for sync Client class."""

import os
import tempfile

import pytest
import respx
from httpx import Response

from sanity import Client
from sanity.exceptions import (
    SanityAuthError,
    SanityNotFoundError,
    SanityRateLimitError,
    SanityValidationError,
)


@pytest.fixture
def mock_sanity_responses():
    """Fixture with realistic Sanity API mock responses."""
    return {
        "query_success": {
            "ms": 123,
            "query": "*[_type == 'post']",
            "result": [
                {
                    "_id": "post-1",
                    "_type": "post",
                    "title": "Hello World",
                    "publishedAt": "2025-01-15T00:00:00Z",
                },
                {
                    "_id": "post-2",
                    "_type": "post",
                    "title": "Second Post",
                    "publishedAt": "2025-01-16T00:00:00Z",
                },
            ],
            "syncTags": ["tag1", "tag2"],
        },
        "mutation_success": {
            "transactionId": "tx-abc123",
            "results": [
                {"id": "post-1", "operation": "create"},
                {"id": "post-2", "operation": "update"},
            ],
            "documentIds": ["post-1", "post-2"],
        },
        "asset_success": {
            "document": {
                "_id": "image-abc123",
                "_type": "sanity.imageAsset",
                "url": "https://cdn.sanity.io/images/project/dataset/abc123.png",
                "path": "images/project/dataset/abc123.png",
                "size": 12345,
                "sha1hash": "abc123def456",
                "extension": "png",
                "mimeType": "image/png",
                "originalFilename": "test.png",
                "metadata": {"dimensions": {"width": 800, "height": 600}},
            }
        },
    }


@pytest.fixture
def client():
    """Create test client."""
    return Client(
        project_id="test-project",
        dataset="test-dataset",
        token="test-token",
        use_cdn=False,
    )


class TestClientInitialization:
    """Test client initialization."""

    def test_init_with_params(self):
        """Test client initialization with explicit parameters."""
        client = Client(
            project_id="my-project",
            dataset="production",
            token="my-token",
            use_cdn=True,
        )
        assert client.project_id == "my-project"
        assert client.dataset == "production"
        assert client.token == "my-token"

    def test_init_without_logger(self):
        """Test that logger is optional."""
        client = Client(project_id="test", dataset="test")
        assert client.logger is not None

    def test_init_missing_project_id(self):
        """Test that missing project_id raises error."""
        with pytest.raises(ValueError, match="SANITY_PROJECT_ID"):
            Client(dataset="test")

    def test_api_host_cdn(self):
        """Test CDN API host construction."""
        client = Client(
            project_id="my-project", dataset="test", use_cdn=True, api_version="2025-02-19"
        )
        assert "apicdn.sanity.io" in client.base_uri
        assert "v2025-02-19" in client.base_uri

    def test_api_host_no_cdn(self):
        """Test non-CDN API host construction."""
        client = Client(
            project_id="my-project",
            dataset="test",
            use_cdn=False,
            api_version="2025-02-19",
        )
        assert ".api.sanity.io" in client.base_uri
        assert "apicdn" not in client.base_uri

    def test_context_manager(self):
        """Test client as context manager."""
        with Client(project_id="test", dataset="test") as client:
            assert client is not None
        # Session should be closed after context


class TestQuery:
    """Test query method."""

    @respx.mock
    def test_query_get_success(self, client, mock_sanity_responses):
        """Test successful GET query."""
        route = respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset"
        ).mock(return_value=Response(200, json=mock_sanity_responses["query_success"]))

        result = client.query(groq="*[_type == 'post']", method="GET")

        assert result["ms"] == 123
        assert len(result["result"]) == 2
        assert result["result"][0]["title"] == "Hello World"
        assert route.called

    @respx.mock
    def test_query_post_success(self, client, mock_sanity_responses):
        """Test successful POST query."""
        route = respx.post(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset"
        ).mock(return_value=Response(200, json=mock_sanity_responses["query_success"]))

        result = client.query(
            groq="*[_type == $type]", variables={"type": "post"}, method="POST"
        )

        assert result["ms"] == 123
        assert len(result["result"]) == 2
        assert route.called

    @respx.mock
    def test_query_with_perspective(self, client, mock_sanity_responses):
        """Test query with perspective parameter."""
        route = respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset",
            params={"perspective": "published"},
        ).mock(return_value=Response(200, json=mock_sanity_responses["query_success"]))

        result = client.query(
            groq="*[_type == 'post']", perspective="published", method="GET"
        )

        assert result is not None
        assert route.called

    @respx.mock
    def test_query_with_tag(self, client, mock_sanity_responses):
        """Test query with tag parameter."""
        route = respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset",
            params={"tag": "my-app"},
        ).mock(return_value=Response(200, json=mock_sanity_responses["query_success"]))

        result = client.query(groq="*[_type == 'post']", tag="my-app", method="GET")

        assert result is not None
        assert route.called

    @respx.mock
    def test_query_variables(self, client, mock_sanity_responses):
        """Test query with variables."""
        route = respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset"
        ).mock(return_value=Response(200, json=mock_sanity_responses["query_success"]))

        result = client.query(
            groq="*[_type == $type]", variables={"type": "post"}, method="GET"
        )

        assert result is not None
        assert route.called


class TestMutations:
    """Test mutation method."""

    @respx.mock
    def test_mutate_success(self, client, mock_sanity_responses):
        """Test successful mutation."""
        route = respx.post(
            "https://test-project.api.sanity.io/v2025-02-19/data/mutate/test-dataset"
        ).mock(
            return_value=Response(200, json=mock_sanity_responses["mutation_success"])
        )

        transactions = [
            {
                "create": {
                    "_type": "post",
                    "title": "New Post",
                }
            }
        ]

        result = client.mutate(transactions=transactions, return_ids=True)

        assert result["transactionId"] == "tx-abc123"
        assert len(result["results"]) == 2
        assert route.called

    @respx.mock
    def test_mutate_with_custom_transaction_id(self, client, mock_sanity_responses):
        """Test mutation with custom transaction ID."""
        route = respx.post(
            "https://test-project.api.sanity.io/v2025-02-19/data/mutate/test-dataset",
            params={"transactionId": "my-custom-id"},
        ).mock(
            return_value=Response(200, json=mock_sanity_responses["mutation_success"])
        )

        transactions = [{"create": {"_type": "post", "title": "New Post"}}]

        result = client.mutate(
            transactions=transactions, transaction_id="my-custom-id"
        )

        assert result is not None
        assert route.called

    @respx.mock
    def test_mutate_with_auto_generate_array_keys(
        self, client, mock_sanity_responses
    ):
        """Test mutation with auto_generate_array_keys."""
        route = respx.post(
            "https://test-project.api.sanity.io/v2025-02-19/data/mutate/test-dataset",
            params={"autoGenerateArrayKeys": "true"},
        ).mock(
            return_value=Response(200, json=mock_sanity_responses["mutation_success"])
        )

        transactions = [{"create": {"_type": "post", "title": "New Post"}}]

        result = client.mutate(
            transactions=transactions, auto_generate_array_keys=True
        )

        assert result is not None
        assert route.called

    def test_mutate_without_token(self):
        """Test that mutation without token raises error."""
        client = Client(project_id="test", dataset="test", token=None)

        transactions = [{"create": {"_type": "post"}}]

        with pytest.raises(SanityAuthError, match="API token is required"):
            client.mutate(transactions=transactions)


class TestAssets:
    """Test asset upload."""

    @respx.mock
    def test_assets_upload_success(self, client, mock_sanity_responses):
        """Test successful asset upload."""
        route = respx.post(
            "https://test-project.api.sanity.io/v2025-02-19/assets/images/test-dataset"
        ).mock(return_value=Response(200, json=mock_sanity_responses["asset_success"]))

        # Mock file read
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name

        try:
            result = client.assets(file_path=temp_path)
            assert result["document"]["_type"] == "sanity.imageAsset"
            assert result["document"]["mimeType"] == "image/png"
            assert route.called
        finally:
            os.unlink(temp_path)

    def test_assets_without_token(self):
        """Test that asset upload without token raises error."""
        client = Client(project_id="test", dataset="test", token=None)

        with pytest.raises(SanityAuthError, match="API token is required"):
            client.assets(file_path="/path/to/file.png")


class TestErrorHandling:
    """Test error handling."""

    @respx.mock
    def test_auth_error_401(self, client):
        """Test 401 authentication error."""
        respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset"
        ).mock(return_value=Response(401, json={"error": "Unauthorized"}))

        with pytest.raises(SanityAuthError) as exc_info:
            client.query(groq="*[_type == 'post']")

        assert exc_info.value.status_code == 401

    @respx.mock
    def test_not_found_404(self, client):
        """Test 404 not found error."""
        respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset"
        ).mock(return_value=Response(404, json={"error": "Not found"}))

        with pytest.raises(SanityNotFoundError) as exc_info:
            client.query(groq="*[_type == 'post']")

        assert exc_info.value.status_code == 404

    @respx.mock
    def test_validation_error_400(self, client):
        """Test 400 validation error."""
        respx.post(
            "https://test-project.api.sanity.io/v2025-02-19/data/mutate/test-dataset"
        ).mock(return_value=Response(400, json={"error": "Invalid mutation"}))

        with pytest.raises(SanityValidationError) as exc_info:
            client.mutate(transactions=[{"invalid": "data"}])

        assert exc_info.value.status_code == 400

    @respx.mock
    def test_rate_limit_429(self, client):
        """Test 429 rate limit error."""
        respx.get(
            "https://test-project.api.sanity.io/v2025-02-19/data/query/test-dataset"
        ).mock(
            return_value=Response(
                429, json={"error": "Rate limited"}, headers={"Retry-After": "60"}
            )
        )

        with pytest.raises(SanityRateLimitError) as exc_info:
            client.query(groq="*[_type == 'post']")

        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 60
