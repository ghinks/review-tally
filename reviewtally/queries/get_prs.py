from __future__ import annotations

import os
import random
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

import requests

if TYPE_CHECKING:
    from collections.abc import Mapping

    from reviewtally.cache.cache_manager import CacheManager

from reviewtally.cache.cache_manager import get_cache_manager
from reviewtally.exceptions.local_exceptions import PaginationError
from reviewtally.queries import (
    BACKOFF_MULTIPLIER,
    GENERAL_TIMEOUT,
    INITIAL_BACKOFF,
    MAX_BACKOFF,
    MAX_RETRIES,
    RETRYABLE_STATUS_CODES,
)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
MAX_NUM_PAGES = 100
ITEMS_PER_PAGE = 100
RATE_LIMIT_REMAINING_THRESHOLD = 10  # arbitrary threshold
RATE_LIMIT_SLEEP_SECONDS = 60  # seconds to sleep if rate limit is hit


def backoff_if_ratelimited(headers: Mapping[str, str]) -> None:
    remaining = headers.get("X-RateLimit-Remaining")
    if remaining is None:
        return
    try:
        remaining_int = int(remaining)
    except (ValueError, TypeError):
        return
    if remaining_int > RATE_LIMIT_REMAINING_THRESHOLD:
        return

    reset = headers.get("X-RateLimit-Reset")
    sleep_for = float(RATE_LIMIT_SLEEP_SECONDS)
    if reset is not None:
        try:
            reset_epoch = int(reset)
            sleep_for = max(0.0, reset_epoch - time.time()) + 5.0  # buffer
        except (ValueError, TypeError):
            pass

    if sleep_for > 0:
        time.sleep(sleep_for)


def _backoff_delay(attempt: int) -> None:
    """Calculate exponential backoff delay with jitter (sync version)."""
    delay = min(
        INITIAL_BACKOFF * (BACKOFF_MULTIPLIER**attempt),
        MAX_BACKOFF,
    )
    # Add jitter to prevent thundering herd
    jitter = random.uniform(0.1, 0.5) * delay  # noqa: S311
    time.sleep(delay + jitter)


def _make_pr_request_with_retry(
    url: str,
    headers: dict[str, str],
    params: dict[str, Any],
) -> dict[str, Any] | list[dict]:
    """
    Make a single PR request with retry logic.

    Returns dict for search API responses, list for direct PR endpoints.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=GENERAL_TIMEOUT,
            )

            # Check for retryable status codes
            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt < MAX_RETRIES:
                    _backoff_delay(attempt)
                    continue
                # Final attempt failed
                response.raise_for_status()

            # Handle rate limiting (existing logic)
            backoff_if_ratelimited(response.headers)
            response.raise_for_status()

            return response.json()

        except (
            requests.exceptions.RequestException,
            requests.exceptions.Timeout,
        ):
            if attempt < MAX_RETRIES:
                _backoff_delay(attempt)
                continue
            # Final attempt failed, re-raise the exception
            raise

    # This should never be reached due to the loop structure
    msg = "Failed to fetch pull requests after all retry attempts"
    raise RuntimeError(msg)


def fetch_pull_requests_from_github(
    owner: str,
    repo: str,
    start_date: datetime,
    end_date: datetime,
) -> tuple[list[dict], bool]:
    # Use GitHub Search Issues API for native date filtering
    url = "https://api.github.com/search/issues"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Build search query with date range
    # Format: repo:owner/repo is:pr created:YYYY-MM-DD..YYYY-MM-DD
    query = (
        f"repo:{owner}/{repo} is:pr "
        f"created:{start_date.strftime('%Y-%m-%d')}.."
        f"{end_date.strftime('%Y-%m-%d')}"
    )

    pull_requests = []
    page = 1
    reached_boundary = True  # Search API always returns complete results

    while True:
        params: dict[str, Any] = {
            "q": query,
            "sort": "created",
            "order": "desc",
            "per_page": ITEMS_PER_PAGE,
            "page": page,
        }

        response_data = _make_pr_request_with_retry(url, headers, params)
        # Search API returns {"items": [...]} instead of direct array
        if isinstance(response_data, dict):
            prs = response_data.get("items", [])
        else:
            prs = []  # Unexpected format, skip this page

        if not prs:
            break

        # No need for client-side date filtering - API handles it
        pull_requests.extend(prs)

        page += 1
        if page > MAX_NUM_PAGES:
            raise PaginationError(str(page))

    return pull_requests, reached_boundary


def get_pull_requests_between_dates(
    owner: str,
    repo: str,
    start_date: datetime,
    end_date: datetime,
    *,
    use_cache: bool = True,
) -> list[dict]:
    cache_manager = get_cache_manager()

    if not use_cache:
        print(  # noqa: T201
            f"Cache DISABLED: Fetching PR list for {owner}/{repo} "
            f"({start_date.strftime('%Y-%m-%d')} to "
            f"{end_date.strftime('%Y-%m-%d')})",
        )
        prs, _ = fetch_pull_requests_from_github(
            owner,
            repo,
            start_date,
            end_date,
        )
        return prs

    # Get cached PRs and cache stats from pr_metadata table
    cached_prs, pr_stats = cache_manager.get_cached_prs_for_date_range(
        owner,
        repo,
        start_date,
        end_date,
    )

    # Get cached date range information from pr_metadata table
    cached_date_range = cache_manager.get_cached_date_range(owner, repo)

    # Determine what additional data we need to fetch
    needs_backward = cache_manager.needs_backward_fetch(pr_stats, start_date)
    needs_forward = cache_manager.needs_forward_fetch(pr_stats)

    newly_fetched_prs: list[dict] = []
    reached_boundary = False

    if needs_backward or needs_forward or not pr_stats:
        # Optimize: Use cached date range to fetch only gaps
        if cached_date_range and cached_prs:
            # We have cached data - fetch only what's missing
            cached_min = datetime.fromisoformat(
                cached_date_range["min_date"].replace("Z", "+00:00"),
            )
            cached_max = datetime.fromisoformat(
                cached_date_range["max_date"].replace("Z", "+00:00"),
            )

            # Fetch backward if requested start is before cached data
            if needs_backward and start_date < cached_min:
                print(  # noqa: T201
                    f"Backward fetch: {start_date.date()} to "
                    f"{cached_min.date()}",
                )
                backward_prs, boundary = fetch_pull_requests_from_github(
                    owner,
                    repo,
                    start_date,
                    cached_min,
                )
                newly_fetched_prs.extend(backward_prs)
                reached_boundary = reached_boundary or boundary

            # Fetch forward if needed and end is after cached data
            if needs_forward and end_date > cached_max:
                print(  # noqa: T201
                    f"Forward fetch: {cached_max.date()} to "
                    f"{end_date.date()}",
                )
                forward_prs, boundary = fetch_pull_requests_from_github(
                    owner,
                    repo,
                    cached_max,
                    end_date,
                )
                newly_fetched_prs.extend(forward_prs)
                reached_boundary = reached_boundary or boundary
        else:
            # No cached data - do full fetch
            (
                newly_fetched_prs,
                reached_boundary,
            ) = fetch_pull_requests_from_github(
                owner,
                repo,
                start_date,
                end_date,
            )

        # Cache individual PRs
        if newly_fetched_prs:
            _cache_pr_metadata(
                cache_manager,
                owner,
                repo,
                newly_fetched_prs,
            )

    # Combine cached and newly fetched PRs
    return _combine_pr_results(cached_prs, newly_fetched_prs)


def _cache_pr_metadata(
    cache_manager: CacheManager,
    owner: str,
    repo: str,
    new_prs: list[dict],
) -> None:
    """Cache individual PR metadata entries."""
    for pr in new_prs:
        cache_manager.cache_pr(owner, repo, pr)


def _combine_pr_results(
    cached_prs: list[dict],
    new_prs: list[dict],
) -> list[dict]:
    seen_pr_numbers = set()
    combined_prs = []

    # Add new PRs first (maintain API order)
    for pr in new_prs:
        if pr["number"] not in seen_pr_numbers:
            combined_prs.append(pr)
            seen_pr_numbers.add(pr["number"])

    # Add cached PRs that weren't in new results
    for pr in cached_prs:
        if pr["number"] not in seen_pr_numbers:
            combined_prs.append(pr)
            seen_pr_numbers.add(pr["number"])

    return combined_prs
