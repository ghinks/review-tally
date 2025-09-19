"""Cache key generation utilities for GitHub API responses."""

from __future__ import annotations


def gen_pr_review_key(
    owner: str,
    repo: str,
    pull_number: int,
) -> str:
    return f"pr_reviews:{owner}:{repo}:{pull_number}"


def gen_pr_key(
    owner: str,
    repo: str,
    pr_number: int,
) -> str:
    return f"pr_metadata:{owner}:{repo}:{pr_number}"


def gen_pr_list_metadata_key(
    owner: str,
    repo: str,
) -> str:
    """Key for storing PR list metadata (index)."""
    return f"pr_index:{owner}:{repo}"
