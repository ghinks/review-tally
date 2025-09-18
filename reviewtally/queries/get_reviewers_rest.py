import asyncio
import os
import random
import time
from typing import Any

import aiohttp

from reviewtally.cache.cache_manager import CacheManager, get_cache_manager
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

# Rate limiting constants
RATE_LIMIT_BUFFER = 500  # Keep this many requests in reserve
RATE_LIMIT_MIN_SLEEP = 60  # Minimum sleep time when rate limited (seconds)


async def check_rate_limit_and_sleep(response: aiohttp.ClientResponse) -> None:
    """
    Check GitHub API rate limit headers and sleep if necessary.

    Args:
        response: The aiohttp response object containing rate limit headers

    """
    # GitHub API rate limit headers (case-insensitive)
    remaining_header = None
    reset_header = None

    # Check for rate limit headers (GitHub uses different variations)
    for header_name, header_value in response.headers.items():
        header_lower = header_name.lower()
        if header_lower in ("x-ratelimit-remaining", "x-rate-limit-remaining"):
            remaining_header = header_value
        elif header_lower in ("x-ratelimit-reset", "x-rate-limit-reset"):
            reset_header = header_value

    if remaining_header is None or reset_header is None:
        # No rate limit headers found, continue normally
        return

    try:
        remaining = int(remaining_header)
        reset_timestamp = int(reset_header)

        # If we're getting close to the rate limit, sleep until reset
        if remaining <= RATE_LIMIT_BUFFER:
            current_time = int(time.time())
            sleep_time = max(
                reset_timestamp - current_time,
                RATE_LIMIT_MIN_SLEEP,
            )

            print(  # noqa: T201
                f"GitHub API rate limit approaching. "
                f"Remaining: {remaining}, sleeping for {sleep_time} seconds.",
            )

            await asyncio.sleep(sleep_time)

    except (ValueError, TypeError) as e:
        # Handle case where header values aren't valid integers
        print(f"Warning: Could not parse rate limit headers: {e}")  # noqa: T201


async def fetch(client: aiohttp.ClientSession, url: str) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            if HTTPS_PROXY:
                async with client.get(
                    url,
                    headers=headers,
                    proxy=HTTPS_PROXY,
                ) as response:
                    if response.status in RETRYABLE_STATUS_CODES:
                        if attempt < MAX_RETRIES:
                            await _backoff_delay(attempt)
                            continue
                        # Final attempt failed
                        response.raise_for_status()
                    response.raise_for_status()  # Raise for other HTTP errors

                    # Check rate limit before proceeding
                    await check_rate_limit_and_sleep(response)

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

                    # Check rate limit before proceeding
                    await check_rate_limit_and_sleep(response)

                    return await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt < MAX_RETRIES:
                await _backoff_delay(attempt)
                continue
            # Final attempt failed, re-raise the exception
            raise

    # This should never be reached due to the loop structure
    msg = (
        f"Unexpected error: Failed to fetch {url} after {MAX_RETRIES} retries"
    )
    raise RuntimeError(msg)


async def _backoff_delay(attempt: int) -> None:
    """Calculate exponential backoff delay with jitter."""
    delay = min(
        INITIAL_BACKOFF * (BACKOFF_MULTIPLIER**attempt),
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
    owner: str,
    repo: str,
    pull_numbers: list[int],
) -> list[dict]:
    urls = [
        f"https://api.github.com/repos/{owner}/{repo}"
        f"/pulls/{pull_number}/reviews"
        for pull_number in pull_numbers
    ]
    reviewers = asyncio.run(fetch_batch(urls))
    return [item["user"] for sublist in reviewers for item in sublist]


def _check_pr_cache(
    cache_manager: CacheManager,
    owner: str,
    repo: str,
    pull_numbers: list[int],
) -> tuple[list[dict], list[int]]:
    """Check cache for each PR individually and return cached/uncached data."""
    cached_results = []
    uncached_prs = []

    for pull_number in pull_numbers:
        cached_pr_data = cache_manager.get_cached_pr_review(
            owner, repo, pull_number,
        )
        if cached_pr_data is not None:
            cached_results.extend(cached_pr_data)
        else:
            uncached_prs.append(pull_number)

    return cached_results, uncached_prs


def _fetch_review_metadata(
    owner: str,
    repo: str,
    uncached_prs: list[int],
) -> list[dict]:
    """Fetch reviews and collect metadata with comment URLs."""
    review_urls = [
        f"https://api.github.com/repos/{owner}/{repo}"
        f"/pulls/{pull_number}/reviews"
        for pull_number in uncached_prs
    ]
    reviews_response = asyncio.run(fetch_batch(review_urls))

    review_data = []

    for i, sublist in enumerate(reviews_response):
        pull_number = uncached_prs[i]
        for review in sublist:
            user = review["user"]
            review_id = review["id"]

            comment_url = (
                f"https://api.github.com/repos/{owner}/{repo}"
                f"/pulls/{pull_number}/reviews/{review_id}/comments"
            )

            submitted_at = review.get("submitted_at")
            if submitted_at is None:
                print(  # noqa: T201
                    f"Warning: Review {review_id} for PR {pull_number} "
                    f"missing submitted_at",
                )

            review_data.append(
                {
                    "user": user,
                    "review_id": review_id,
                    "pull_number": pull_number,
                    "submitted_at": submitted_at,
                    "comment_url": comment_url,
                },
            )

    return review_data


def _process_and_cache_reviews(
    cache_manager: CacheManager,
    owner: str,
    repo: str,
    review_data: list[dict],
    *,
    use_cache: bool = True,
) -> list[dict]:
    """Process comments and cache individual PR reviews."""
    if not review_data:
        return []

    # Extract comment URLs from review data
    comment_urls = [review["comment_url"] for review in review_data]
    comments_response = asyncio.run(fetch_batch(comment_urls))

    # Combine the data and group by PR for individual caching
    pr_review_data: dict[int, list[dict[str, Any]]] = {}
    uncached_results = []

    for i, comments in enumerate(comments_response):
        review_info = review_data[i]
        comment_count = len(comments) if comments else 0
        pull_number = review_info["pull_number"]

        review_entry = {
            "user": review_info["user"],
            "review_id": review_info["review_id"],
            "pull_number": pull_number,
            "comment_count": comment_count,
            "submitted_at": review_info["submitted_at"],
        }

        if pull_number not in pr_review_data:
            pr_review_data[pull_number] = []
        pr_review_data[pull_number].append(review_entry)
        uncached_results.append(review_entry)

    # Cache each PR individually (only if caching enabled)
    if use_cache:
        for pull_number, reviews in pr_review_data.items():
            cache_manager.cache_per_review(
                owner, repo, pull_number, reviews,
            )

    return uncached_results


def get_reviewers_with_comments_for_pull_requests(
    owner: str,
    repo: str,
    pull_numbers: list[int],
    *,
    use_cache: bool = True,
) -> list[dict]:
    cache_manager = get_cache_manager()

    if use_cache:
        # Check cache for each PR individually
        cached_results, uncached_prs = _check_pr_cache(
            cache_manager, owner, repo, pull_numbers,
        )

        # If all PRs are cached, return early
        if not uncached_prs:
            return cached_results
    else:
        # Skip cache entirely - treat all PRs as uncached
        cached_results = []
        uncached_prs = pull_numbers

    # Fetch reviews and collect metadata
    review_data = _fetch_review_metadata(
        owner, repo, uncached_prs,
    )

    # Process comments and cache results
    uncached_results = _process_and_cache_reviews(
        cache_manager, owner, repo, review_data, use_cache=use_cache,
    )

    # Cache empty results for PRs with no reviews (only if caching enabled)
    if not review_data and use_cache:
        for pull_number in uncached_prs:
            cache_manager.cache_per_review(
                owner, repo, pull_number, [],
            )

    # Combine cached and newly fetched results
    return cached_results + uncached_results
