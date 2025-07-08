import ssl

import aiohttp

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
MAX_RETRIES = 3                    # Maximum number of retry attempts
INITIAL_BACKOFF = 1.0             # Initial backoff delay in seconds
BACKOFF_MULTIPLIER = 2.0          # Exponential backoff multiplier
MAX_BACKOFF = 60.0                # Maximum backoff delay in seconds

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
