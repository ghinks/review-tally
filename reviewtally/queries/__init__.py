import os
import ssl
from typing import Optional, Tuple

import aiohttp
from urllib.parse import urljoin, urlparse, urlunparse

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
DEFAULT_GITHUB_REST_PATH = ""
DEFAULT_GITHUB_GRAPHQL_PATH = "/graphql"

_github_host = DEFAULT_GITHUB_HOST
_github_rest_path = DEFAULT_GITHUB_REST_PATH
_github_graphql_path = DEFAULT_GITHUB_GRAPHQL_PATH


def _normalize_github_host(host: Optional[str]) -> Tuple[str, str]:
    """Normalise a user-provided GitHub host value and extract an embedded path."""

    if host is None:
        return DEFAULT_GITHUB_HOST, ""

    trimmed = host.strip()
    if not trimmed:
        return DEFAULT_GITHUB_HOST, ""

    if not trimmed.startswith(("http://", "https://")):
        trimmed = f"https://{trimmed}"

    parsed = urlparse(trimmed)

    if not parsed.netloc:
        return DEFAULT_GITHUB_HOST, ""

    normalized_host = urlunparse(
        (
            parsed.scheme or "https",
            parsed.netloc,
            "",
            "",
            "",
            "",
        ),
    ).rstrip("/")

    embedded_path = parsed.path.rstrip("/")

    return normalized_host, embedded_path


def _normalize_api_path(path: Optional[str], *, default: str) -> str:
    """Normalise API path segments ensuring a single leading slash."""

    candidate = default if path is None else path.strip()

    if not candidate:
        return ""

    if candidate.startswith(("http://", "https://")):
        candidate = urlparse(candidate).path

    trimmed = candidate.strip().strip("/")

    if not trimmed:
        return ""

    return f"/{trimmed}"


def _compute_graphql_default(rest_path: str, embedded_path: str) -> str:
    if rest_path:
        return f"{rest_path}/graphql"
    if embedded_path:
        return f"{embedded_path}/graphql"
    return DEFAULT_GITHUB_GRAPHQL_PATH


def set_github_host(
    host: Optional[str],
    *,
    rest_path: Optional[str] = None,
    graphql_path: Optional[str] = None,
) -> None:
    """Update the base host and API paths used for GitHub API requests."""

    global _github_host, _github_rest_path, _github_graphql_path

    normalized_host, embedded_path = _normalize_github_host(host)

    rest_default = embedded_path or DEFAULT_GITHUB_REST_PATH
    if rest_path is None:
        normalized_rest_path = _normalize_api_path(
            None,
            default=rest_default,
        )
    else:
        normalized_rest_path = _normalize_api_path(rest_path, default="")

    graphql_default = _compute_graphql_default(
        normalized_rest_path,
        embedded_path,
    )
    if graphql_path is None:
        normalized_graphql_path = _normalize_api_path(
            None,
            default=graphql_default,
        )
    else:
        normalized_graphql_path = _normalize_api_path(graphql_path, default="")

    _github_host = normalized_host
    _github_rest_path = normalized_rest_path
    if graphql_path is None:
        _github_graphql_path = (
            normalized_graphql_path or DEFAULT_GITHUB_GRAPHQL_PATH
        )
    else:
        _github_graphql_path = normalized_graphql_path


def get_github_host() -> str:
    """Return the currently configured GitHub API host."""

    return _github_host


def _get_rest_api_base() -> str:
    if _github_rest_path:
        return f"{_github_host}{_github_rest_path}"
    return _github_host


def _build_github_url(path: str) -> str:
    """Build a GitHub URL relative to the configured host."""

    base = f"{_get_rest_api_base()}/"
    normalized_path = path.lstrip("/")
    return urljoin(base, normalized_path)


def build_github_rest_api_url(path: str) -> str:
    """Build a REST API URL using the configured host."""

    return _build_github_url(path)


def get_github_graphql_url() -> str:
    """Return the configured GitHub GraphQL endpoint URL."""

    base = f"{get_github_host()}/"
    normalized_path = _github_graphql_path.lstrip("/")
    return urljoin(base, normalized_path)


def require_github_token() -> str:
    """Return the GitHub token or raise if it is undefined."""
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token is None:
        raise GitHubTokenNotDefinedError
    return github_token
