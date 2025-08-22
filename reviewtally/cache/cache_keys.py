"""Cache key generation utilities for GitHub API responses."""

from __future__ import annotations

import hashlib
from typing import Any


def generate_pr_reviews_cache_key(
    owner: str,
    repo: str,
    pull_numbers: list[int],
) -> str:
    """
    Generate cache key for PR reviews data.

    Args:
        owner: Repository owner/organization
        repo: Repository name
        pull_numbers: List of PR numbers

    Returns:
        Cache key string

    """
    # Sort PR numbers for consistent key generation
    sorted_prs = sorted(pull_numbers)
    pr_list = ",".join(map(str, sorted_prs))

    # Create base key
    base_key = f"pr_reviews:{owner}:{repo}:{pr_list}"

    # Hash if too long (SQLite key limit considerations)
    max_key_length = 200
    if len(base_key) > max_key_length:
        key_hash = hashlib.sha256(base_key.encode()).hexdigest()[:16]
        return f"pr_reviews:{owner}:{repo}:hash_{key_hash}"

    return base_key


def generate_pr_comments_cache_key(
    owner: str,
    repo: str,
    pull_number: int,
    review_id: int,
) -> str:
    """
    Generate cache key for PR review comments.

    Args:
        owner: Repository owner/organization
        repo: Repository name
        pull_number: PR number
        review_id: Review ID

    Returns:
        Cache key string

    """
    return f"pr_comments:{owner}:{repo}:{pull_number}:{review_id}"


def generate_repos_cache_key(org_name: str, languages: list[str]) -> str:
    """
    Generate cache key for repository lists.

    Args:
        org_name: Organization name
        languages: List of programming languages

    Returns:
        Cache key string

    """
    # Sort languages for consistent key generation
    sorted_langs = sorted(languages) if languages else ["all"]
    lang_str = ",".join(sorted_langs)

    return f"repos:{org_name}:{lang_str}"


def generate_prs_cache_key(
    owner: str,
    repo: str,
    start_date: str,
    end_date: str,
) -> str:
    """
    Generate cache key for PR lists within date range.

    Args:
        owner: Repository owner/organization
        repo: Repository name
        start_date: Start date string (ISO format)
        end_date: End date string (ISO format)

    Returns:
        Cache key string

    """
    return f"prs:{owner}:{repo}:{start_date}:{end_date}"


def parse_cache_key(cache_key: str) -> dict[str, Any]:
    """
    Parse cache key to extract components.

    Args:
        cache_key: Cache key to parse

    Returns:
        Dictionary with parsed components

    """
    parts = cache_key.split(":")
    min_parts = 2
    if len(parts) < min_parts:
        return {"type": "unknown", "key": cache_key}

    cache_type = parts[0]

    if cache_type == "pr_reviews":
        min_pr_review_parts = 4
        if len(parts) >= min_pr_review_parts:
            return {
                "type": "pr_reviews",
                "owner": parts[1],
                "repo": parts[2],
                "pull_numbers": parts[3],
                "key": cache_key,
            }
    elif cache_type == "pr_comments":
        min_pr_comment_parts = 5
        if len(parts) >= min_pr_comment_parts:
            return {
                "type": "pr_comments",
                "owner": parts[1],
                "repo": parts[2],
                "pull_number": parts[3],
                "review_id": parts[4],
                "key": cache_key,
            }
    elif cache_type == "repos":
        min_repos_parts = 3
        if len(parts) >= min_repos_parts:
            return {
                "type": "repos",
                "org_name": parts[1],
                "languages": parts[2],
                "key": cache_key,
            }
    elif cache_type == "prs":
        min_prs_parts = 5
        if len(parts) >= min_prs_parts:
            return {
                "type": "prs",
                "owner": parts[1],
                "repo": parts[2],
                "start_date": parts[3],
                "end_date": parts[4],
                "key": cache_key,
            }

    return {"type": cache_type, "key": cache_key}


def is_pr_closed_cache_key(
    cache_key: str, pr_state_lookup: dict[int, str] | None = None,
) -> bool:
    """
    Determine if a cache key is for closed PR data (never expires).

    Args:
        cache_key: Cache key to check
        pr_state_lookup: Optional lookup dict for PR states

    Returns:
        True if this is closed PR data that should never expire

    """
    parsed = parse_cache_key(cache_key)

    # PR reviews and comments for closed PRs never change
    if parsed["type"] in ("pr_reviews", "pr_comments"):
        # If we have state lookup, use it
        if pr_state_lookup and parsed["type"] == "pr_comments":
            pr_number = int(parsed.get("pull_number", 0))
            return pr_state_lookup.get(pr_number) == "closed"

        # Otherwise, assume we should check when caching
        return True  # Conservative approach - cache forever for now

    return False
