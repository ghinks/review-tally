"""Cache key generation utilities for GitHub API responses."""

from __future__ import annotations


def generate_single_pr_reviews_cache_key(
    owner: str,
    repo: str,
    pull_number: int,
) -> str:
    return f"pr_reviews:{owner}:{repo}:{pull_number}"


def generate_pr_list_cache_key(
    owner: str,
    repo: str,
    start_date: str,
    end_date: str,
) -> str:
    return f"pr_list:{owner}:{repo}:{start_date}:{end_date}"
