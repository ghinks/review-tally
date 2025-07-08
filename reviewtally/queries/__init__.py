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
