import asyncio
import os
import random
from typing import Any

import aiohttp

from reviewtally.queries import (
    AIOHTTP_TIMEOUT,
    BACKOFF_MULTIPLIER,
    CONNECTION_ENABLE_CLEANUP,
    CONNECTION_KEEP_ALIVE,
    CONNECTION_POOL_SIZE,
    CONNECTION_POOL_SIZE_PER_HOST,
    INITIAL_BACKOFF,
    MAX_BACKOFF,
    MAX_RETRIES,
    RETRYABLE_STATUS_CODES,
    SSL_CONTEXT,
)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# get proxy settings from environment variables
HTTPS_PROXY = os.getenv("HTTPS_PROXY")
# check for lowercase https_proxy
if not HTTPS_PROXY:
    HTTPS_PROXY = os.getenv("https_proxy")


async def fetch(client: aiohttp.ClientSession, url: str) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            if HTTPS_PROXY:
                async with client.get(url,
                                      headers=headers,
                                      proxy=HTTPS_PROXY) as response:
                    if response.status in RETRYABLE_STATUS_CODES:
                        if attempt < MAX_RETRIES:
                            await _backoff_delay(attempt)
                            continue
                        # Final attempt failed
                        response.raise_for_status()
                    response.raise_for_status()  # Raise for other HTTP errors
                    return await response.json()
            else:
                async with client.get(url, headers=headers) as response:
                    if response.status in RETRYABLE_STATUS_CODES:
                        if attempt < MAX_RETRIES:
                            await _backoff_delay(attempt)
                            continue
                        # Final attempt failed
                        response.raise_for_status()
                    response.raise_for_status()  # Raise for other HTTP errors
                    return await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt < MAX_RETRIES:
                await _backoff_delay(attempt)
                continue
            # Final attempt failed, re-raise the exception
            raise

    # This should never be reached due to the loop structure
    msg = (
        f"Unexpected error: Failed to fetch {url} "
        f"after {MAX_RETRIES} retries"
    )
    raise RuntimeError(msg)


async def _backoff_delay(attempt: int) -> None:
    """Calculate exponential backoff delay with jitter."""
    delay = min(
        INITIAL_BACKOFF * (BACKOFF_MULTIPLIER ** attempt),
        MAX_BACKOFF,
    )
    # Add jitter to prevent thundering herd
    jitter = random.uniform(0.1, 0.5) * delay  # noqa: S311
    await asyncio.sleep(delay + jitter)


async def fetch_batch(urls: list[str]) -> tuple[Any]:
    connector = aiohttp.TCPConnector(
        ssl=SSL_CONTEXT,
        limit=CONNECTION_POOL_SIZE,
        limit_per_host=CONNECTION_POOL_SIZE_PER_HOST,
        keepalive_timeout=CONNECTION_KEEP_ALIVE,
        enable_cleanup_closed=CONNECTION_ENABLE_CLEANUP,
    )
    async with aiohttp.ClientSession(
        timeout=AIOHTTP_TIMEOUT,
        connector=connector,
    ) as session:
        tasks = [fetch(session, url) for url in urls]
        return await asyncio.gather(*tasks)  # type: ignore[return-value]



def get_reviewers_for_pull_requests(
    owner: str, repo: str, pull_numbers: list[int],
) -> list[dict]:
    urls = [
        f"https://api.github.com/repos/{owner}/{repo}"
        f"/pulls/{pull_number}/reviews"
        for pull_number in pull_numbers
    ]
    reviewers = asyncio.run(fetch_batch(urls))
    return [item["user"] for sublist in reviewers for item in sublist]


def get_reviewers_with_comments_for_pull_requests(
    owner: str, repo: str, pull_numbers: list[int],
) -> list[dict]:
    # First, get all reviews for the pull requests
    review_urls = [
        f"https://api.github.com/repos/{owner}/{repo}"
        f"/pulls/{pull_number}/reviews"
        for pull_number in pull_numbers
    ]
    reviews_response = asyncio.run(fetch_batch(review_urls))

    # Collect all comment URLs for batch fetching
    comment_urls = []
    review_metadata = []

    for i, sublist in enumerate(reviews_response):
        pull_number = pull_numbers[i]
        for review in sublist:
            user = review["user"]
            review_id = review["id"]

            comment_url = (
                f"https://api.github.com/repos/{owner}/{repo}"
                f"/pulls/{pull_number}/reviews/{review_id}/comments"
            )
            comment_urls.append(comment_url)
            review_metadata.append({
                "user": user,
                "review_id": review_id,
                "pull_number": pull_number,
            })

    # Fetch all comments in batches
    if comment_urls:
        comments_response = asyncio.run(
            fetch_batch(comment_urls),
        )

        # Combine the data
        reviewer_data = []
        for i, comments in enumerate(comments_response):
            metadata = review_metadata[i]
            comment_count = len(comments) if comments else 0

            reviewer_data.append({
                "user": metadata["user"],
                "review_id": metadata["review_id"],
                "pull_number": metadata["pull_number"],
                "comment_count": comment_count,
            })

        return reviewer_data

    return []
