"""Cache key generation utilities for GitHub API responses."""

from __future__ import annotations


def generate_single_pr_reviews_cache_key(
    owner: str,
    repo: str,
    pull_number: int,
) -> str:
    return f"pr_reviews:{owner}:{repo}:{pull_number}"


def generate_pr_metadata_cache_key(
    owner: str,
    repo: str,
    pr_number: int,
) -> str:
    return f"pr_metadata:{owner}:{repo}:{pr_number}"


def generate_pr_index_cache_key(
    owner: str,
    repo: str,
) -> str:
    return f"pr_index:{owner}:{repo}"
