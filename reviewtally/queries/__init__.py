import os
import ssl
from typing import Optional

import aiohttp
from urllib.parse import urljoin

from reviewtally.exceptions.local_exceptions import GitHubTokenNotDefinedError

GENERAL_TIMEOUT = 60
GRAPHQL_TIMEOUT = 60
REVIEWERS_TIMEOUT = 900

# More granular timeout configuration for aiohttp to fix SSL handshake issues
AIOHTTP_TIMEOUT = aiohttp.ClientTimeout(
    total=900,           # Total request timeout (15 min)
    connect=120,         # Connection timeout (2 min) 
    sock_connect=120,    # Socket connection timeout (2 min)
    sock_read=60         # Socket read timeout (1 min)
)

# SSL context configuration for secure GitHub API connections
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = True          # Verify hostname matches certificate
SSL_CONTEXT.verify_mode = ssl.CERT_REQUIRED # Require valid certificate
SSL_CONTEXT.minimum_version = ssl.TLSVersion.TLSv1_2  # Minimum TLS version
SSL_CONTEXT.maximum_version = ssl.TLSVersion.TLSv1_3  # Maximum TLS version

# Retry configuration for handling transient failures
MAX_RETRIES = 10                  # Maximum number of retry attempts
INITIAL_BACKOFF = 1.0             # Initial backoff delay in seconds
BACKOFF_MULTIPLIER = 2.0          # Exponential backoff multiplier
MAX_BACKOFF = 600.0               # Maximum backoff delay in seconds

# HTTP status codes that should trigger retries
RETRYABLE_STATUS_CODES = {
    429,  # Too Many Requests (rate limiting)
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
}

# Connection pool configuration for optimized GitHub API connections
CONNECTION_POOL_SIZE = 100        # Maximum connections in pool
CONNECTION_POOL_SIZE_PER_HOST = 10  # Max connections per host (api.github.com)
CONNECTION_KEEP_ALIVE = 300       # Keep connections alive for 5 minutes
CONNECTION_ENABLE_CLEANUP = True  # Enable automatic connection cleanup

# Repository filtering configuration
MAX_PR_COUNT = 100000  # Skip repositories with more PRs than this threshold

# Base GitHub host configuration
DEFAULT_GITHUB_HOST = "https://api.github.com"
_github_host = DEFAULT_GITHUB_HOST


def _normalize_github_host(host: Optional[str]) -> str:
    """Normalise a user-provided GitHub host value."""

    if host is None:
        return DEFAULT_GITHUB_HOST

    trimmed = host.strip()
    if not trimmed:
        return DEFAULT_GITHUB_HOST

    if not trimmed.startswith(("http://", "https://")):
        trimmed = f"https://{trimmed}"

    # Avoid double slashes when joining paths later
    return trimmed.rstrip("/")


def set_github_host(host: Optional[str]) -> None:
    """Update the base host used for GitHub API requests."""

    global _github_host
    _github_host = _normalize_github_host(host)


def get_github_host() -> str:
    """Return the currently configured GitHub API host."""

    return _github_host


def build_github_api_url(path: str) -> str:
    """Build a GitHub API URL using the configured host."""

    base = f"{get_github_host()}/"
    normalized_path = path.lstrip("/")
    return urljoin(base, normalized_path)


def require_github_token() -> str:
    """Return the GitHub token or raise if it is undefined."""
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token is None:
        raise GitHubTokenNotDefinedError
    return github_token
