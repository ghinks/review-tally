import os
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

import requests

from reviewtally.exceptions.local_exceptions import PaginationError
from reviewtally.queries import GENERAL_TIMEOUT

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
MAX_NUM_PAGES = 100
ITEMS_PER_PAGE = 100
RATE_LIMIT_REMAINING_THRESHOLD = 10  # arbitrary threshold
RATE_LIMIT_SLEEP_SECONDS = 60  # seconds to sleep if rate limit is hit

def backoff_if_ratelimited(headers: Mapping[str, str]) -> None:
    """
    Sleep until GitHub's rate limit reset if `X-RateLimit-Remaining` is 0.

    Uses only `X-RateLimit-Remaining` and `X-RateLimit-Reset`.
    """
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
) -> list[dict]:
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

    return pull_requests


def get_pull_request_file_changes(
    owner: str,
    repo: str,
    pull_number: int,
) -> dict[str, int]:
    """Get file changes for a PR (additions, deletions, changed files)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/files"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=GENERAL_TIMEOUT)
        backoff_if_ratelimited(response.headers)
        response.raise_for_status()
        files = response.json()

        total_additions = 0
        total_deletions = 0
        changed_files = len(files)

        for file in files:
            total_additions += file.get("additions", 0)
            total_deletions += file.get("deletions", 0)

    except requests.RequestException:
        # Return zeros if API call fails to avoid breaking the flow
        pass
    else:
        return {
            "additions": total_additions,
            "deletions": total_deletions,
            "changed_files": changed_files,
        }

    return {
        "additions": 0,
        "deletions": 0,
        "changed_files": 0,
    }
