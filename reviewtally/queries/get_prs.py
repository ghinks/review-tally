from __future__ import annotations

import os
import random
import time
from datetime import datetime, timezone
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
) -> list[dict]:
    """Make a single PR request with retry logic."""
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
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    params: dict[str, Any] = {
        "state": "all",
        "sort": "created_at",
        "direction": "desc",
        "per_page": ITEMS_PER_PAGE,
    }
    pull_requests = []
    page = 1
    reached_boundary = False

    while True:
        params = {**params, "page": page}
        prs = _make_pr_request_with_retry(url, headers, params)
        if not prs:
            break

        latest_created_at = None
        for pr in prs:
            created_at = (
                datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            ).replace(tzinfo=timezone.utc)
            if start_date <= created_at <= end_date:
                pull_requests.append(pr)
            latest_created_at = created_at

        page += 1
        if latest_created_at and latest_created_at < start_date:
            reached_boundary = True
            break
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
            owner, repo, start_date, end_date,
        )
        return prs

    # Get cached PRs and PR index
    cached_prs, pr_index = cache_manager.get_cached_prs_for_date_range(
        owner, repo, start_date, end_date,
    )


    # Determine what additional data we need to fetch
    needs_backward = cache_manager.needs_backward_fetch(pr_index, start_date)
    needs_forward = cache_manager.needs_forward_fetch(pr_index)

    newly_fetched_prs: list[dict] = []
    reached_boundary = False

    if needs_backward or needs_forward or not pr_index:
        # For now, do a full fetch - optimize later with incremental fetching
        newly_fetched_prs, reached_boundary = fetch_pull_requests_from_github(
            owner, repo, start_date, end_date,
        )

        # Update PR index and cache individual PRs
        _update_pr_cache(
            cache_manager, owner, repo, newly_fetched_prs, pr_index,
            start_date=start_date, reached_boundary=reached_boundary,
        )

    # Combine cached and newly fetched PRs
    return _combine_pr_results(cached_prs, newly_fetched_prs)


def _update_pr_cache(  # noqa: PLR0913
    cache_manager: CacheManager,
    owner: str,
    repo: str,
    new_prs: list[dict],
    existing_index: dict[str, Any] | None,
    *,
    start_date: datetime,
    reached_boundary: bool,
) -> None:
    # Cache individual PR details
    for pr in new_prs:
        cache_manager.cache_pr(owner, repo, pr)

    # Build or update PR index
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    earliest_pr: str | None

    if existing_index:
        # Merge with existing index
        existing_prs = existing_index.get("prs", [])
        existing_pr_numbers = {pr["number"] for pr in existing_prs}

        # Add new PRs to index
        for pr in new_prs:
            if pr["number"] not in existing_pr_numbers:
                existing_prs.append({
                    "number": pr["number"],
                    "created_at": pr["created_at"],
                    "state": pr.get("state", "unknown"),
                })

        # Update timestamps
        # Determine earliest_pr based on boundary information
        if reached_boundary and existing_prs:
            # We've reached the boundary - set earliest to start_date
            earliest_pr = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            # Use existing or first PR's date
            earliest_pr = existing_index.get("earliest_pr") or (
                existing_prs[0]["created_at"] if existing_prs else None
            )

        pr_index_data = {
            "prs": existing_prs,
            "last_updated": now,
            "earliest_pr": earliest_pr,
            "coverage_complete": existing_index.get(
                "coverage_complete", False,
            ),
        }
    else:
        # Create new index
        # Determine earliest_pr based on boundary information
        if reached_boundary and new_prs:
            # We've reached the boundary - set earliest to start_date
            earliest_pr = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            # Use actual earliest PR date or None if no PRs
            earliest_pr = (
                min(pr["created_at"] for pr in new_prs)
                if new_prs else None
            )

        pr_index_data = {
            "prs": [
                {
                    "number": pr["number"],
                    "created_at": pr["created_at"],
                    "state": pr.get("state", "unknown"),
                }
                for pr in new_prs
            ],
            "last_updated": now,
            "earliest_pr": earliest_pr,
            "coverage_complete": False,  # Future: detect when we have all PRs
        }

    cache_manager.set_pr_list(owner, repo, pr_index_data)


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
