"""Configuration dataclasses for Sanity client."""

from dataclasses import dataclass, field


@dataclass
class TimeoutConfig:
    """Timeout configuration for HTTP requests."""

    connect: float = 5.0  # Connection timeout in seconds
    read: float = 30.0  # Read timeout in seconds
    write: float = 30.0  # Write timeout in seconds
    pool: float = 5.0  # Connection pool timeout in seconds

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Return as tuple for httpx.Timeout."""
        return (self.connect, self.read, self.write, self.pool)


@dataclass
class RetryConfig:
    """Retry configuration for failed requests."""

    max_retries: int = 3  # Maximum number of retry attempts
    backoff_factor: float = 0.5  # Exponential backoff factor (0.5s, 1s, 2s, ...)
    retry_on_status: list[int] = field(
        default_factory=lambda: [429, 500, 502, 503, 504]
    )  # HTTP status codes to retry on
    retry_on_timeout: bool = True  # Retry on timeout errors
    retry_on_connection_error: bool = True  # Retry on connection errors


@dataclass
class ClientConfig:
    """Configuration for Sanity client."""

    project_id: str | None = None  # Sanity project ID
    dataset: str = "production"  # Dataset name
    api_version: str = "2025-02-19"  # API version (YYYY-MM-DD format)
    token: str | None = None  # API token for authentication
    use_cdn: bool = True  # Use CDN endpoint for queries
    api_host: str | None = None  # Custom API host (overrides use_cdn)

    # HTTP configuration
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    max_connections: int = 100  # Maximum number of HTTP connections in pool
    http2: bool = True  # Enable HTTP/2 support

    # Retry configuration
    retry: RetryConfig = field(default_factory=RetryConfig)

    # Response configuration
    return_pydantic: bool = True  # Return Pydantic models instead of dicts

    def get_api_host(self) -> str:
        """
        Get the appropriate API host based on configuration.

        :return: Full API host URL
        :raises ValueError: If project_id is not set
        """
        if not self.project_id:
            raise ValueError("project_id is required")

        if self.api_host:
            return self.api_host

        subdomain = "apicdn" if self.use_cdn else "api"
        return f"https://{self.project_id}.{subdomain}.sanity.io/v{self.api_version}"
