import os
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

import requests

from reviewtally.cache.cache_manager import get_cache_manager
from reviewtally.exceptions.local_exceptions import PaginationError
from reviewtally.queries import GENERAL_TIMEOUT

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

def get_pull_requests_between_dates(
    owner: str,
    repo: str,
    start_date: datetime,
    end_date: datetime,
    *,
    use_cache: bool = True,
) -> list[dict]:
    cache_manager = get_cache_manager()
    cached_prs = []

    if use_cache:
        # Get cached PRs for the date range
        cached_prs = cache_manager.get_cached_prs_for_date_range(
            owner, repo, start_date, end_date,
        )
        if cached_prs:
            print(  # noqa: T201
                f"Cache PARTIAL HIT: Found {len(cached_prs)} cached PRs for "
                f"{owner}/{repo} ({start_date.strftime('%Y-%m-%d')} to "
                f"{end_date.strftime('%Y-%m-%d')})",
            )

    cache_status = "DISABLED" if not use_cache else "FETCHING"
    print(  # noqa: T201
        f"Cache {cache_status}: Fetching PR list for {owner}/{repo} "
        f"({start_date.strftime('%Y-%m-%d')} to "
        f"{end_date.strftime('%Y-%m-%d')})",
    )

    # Fetch PR list from GitHub API
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

    while True:
        params = {**params, "page": page}
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=GENERAL_TIMEOUT,
        )
        backoff_if_ratelimited(response.headers)
        response.raise_for_status()
        prs = response.json()
        if not prs:
            break
        for pr in prs:
            created_at = (
                datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            ).replace(tzinfo=timezone.utc)
            if start_date <= created_at <= end_date:
                pull_requests.append(pr)

        page += 1
        if created_at < start_date:
            break
        if page > MAX_NUM_PAGES:
            raise PaginationError(str(page))

    # Cache individual PRs if caching is enabled
    if use_cache:
        for pr in pull_requests:
            cache_manager.cache_pr_metadata(owner, repo, pr)

    # Combine cached PRs with newly fetched PRs, removing duplicates
    seen_pr_numbers = set()
    unique_prs = []

    # First add newly fetched PRs (to maintain original processing order)
    for pr in pull_requests:
        if pr["number"] not in seen_pr_numbers:
            unique_prs.append(pr)
            seen_pr_numbers.add(pr["number"])

    # Then add cached PRs that weren't already fetched
    for pr in cached_prs:
        if pr["number"] not in seen_pr_numbers:
            unique_prs.append(pr)
            seen_pr_numbers.add(pr["number"])

    return unique_prs
