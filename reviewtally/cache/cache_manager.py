"""Main cache manager for GitHub API response caching."""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Any

from reviewtally.cache import MODERATE_THRESHOLD_DAYS, RECENT_THRESHOLD_DAYS
from reviewtally.cache.cache_keys import (
    generate_pr_metadata_cache_key,
    generate_single_pr_reviews_cache_key,
)
from reviewtally.cache.sqlite_cache import SQLiteCache

if TYPE_CHECKING:
    from pathlib import Path


class CacheManager:
    """Main interface for caching GitHub API responses."""

    cache: SQLiteCache | None

    def __init__(
        self, cache_dir: Path | None = None, *, enabled: bool = True,
    ) -> None:
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for cache storage
            enabled: Whether caching is enabled

        """
        self.enabled = enabled and not self._is_cache_disabled()

        if self.enabled:
            self.cache = SQLiteCache(cache_dir)
        else:
            self.cache = None

    def _is_cache_disabled(self) -> bool:
        """Check if caching is disabled via environment variable."""
        # Disable cache during testing
        if os.getenv("PYTEST_CURRENT_TEST") is not None:
            return True
        disable_values = ("1", "true", "yes")
        env_value = os.getenv("REVIEW_TALLY_DISABLE_CACHE", "").lower()
        return env_value in disable_values

    def get_cached_pr_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
    ) -> list[dict[str, Any]] | None:
        """
        Get cached reviews data for a single PR.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: PR number

        Returns:
            Cached review data or None if not found

        """
        if not self.enabled or not self.cache:
            return None

        cache_key = generate_single_pr_reviews_cache_key(
            owner, repo, pull_number,
        )
        cached_data = self.cache.get(cache_key)

        if cached_data:
            print(  # noqa: T201
                f"Cache HIT: PR reviews for {owner}/{repo} PR #{pull_number}",
            )
            return cached_data.get("reviews", [])

        return None

    def cache_per_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        reviews_data: list[dict[str, Any]],
        pr_state: str | None = None,
    ) -> None:
        """
        Cache reviews data for a single PR.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: PR number
            reviews_data: Review data to cache
            pr_state: PR state for TTL determination

        """
        if not self.enabled or not self.cache:
            return

        cache_key = generate_single_pr_reviews_cache_key(
            owner, repo, pull_number,
        )

        # Determine TTL based on PR state
        ttl_hours = None  # Never expire by default
        if pr_state == "open":
            ttl_hours = 1  # Short TTL for open PRs

        metadata = {
            "owner": owner,
            "repo": repo,
            "pull_number": pull_number,
            "review_count": len(reviews_data),
            "pr_state": pr_state,
        }

        self.cache.set(
            cache_key,
            {"reviews": reviews_data},
            ttl_hours=ttl_hours,
            metadata=metadata,
        )

        ttl_desc = "forever" if ttl_hours is None else f"{ttl_hours}h"
        print(  # noqa: T201
            f"Cache SET: PR reviews for {owner}/{repo} PR #{pull_number} "
            f"(TTL: {ttl_desc})",
        )

    def _calculate_pr_ttl(self, pr_created_at: str) -> int | None:
        created_date = datetime.fromisoformat(
            pr_created_at.replace("Z", "+00:00"),
        )
        now = datetime.now(created_date.tzinfo)
        days_ago = (now - created_date).days

        if days_ago < RECENT_THRESHOLD_DAYS:
            return 1  # 1 hour for very recent PRs
        if days_ago < MODERATE_THRESHOLD_DAYS:
            return 6  # 6 hours for recent PRs
        return None  # Permanent cache for PRs older than 30 days

    def get_cached_pr_metadata(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> dict[str, Any] | None:
        if not self.enabled or not self.cache:
            return None

        cache_key = generate_pr_metadata_cache_key(owner, repo, pr_number)
        return self.cache.get(cache_key)

    def cache_pr_metadata(
        self,
        owner: str,
        repo: str,
        pr_data: dict[str, Any],
    ) -> None:
        if not self.enabled or not self.cache:
            return

        pr_number = pr_data["number"]
        cache_key = generate_pr_metadata_cache_key(owner, repo, pr_number)

        # Calculate TTL based on PR creation date
        ttl_hours = self._calculate_pr_ttl(pr_data["created_at"])

        metadata = {
            "owner": owner,
            "repo": repo,
            "pr_number": pr_number,
            "pr_state": pr_data.get("state"),
            "created_at": pr_data["created_at"],
        }

        self.cache.set(
            cache_key,
            pr_data,
            ttl_hours=ttl_hours,
            metadata=metadata,
        )

    def get_cached_prs_for_date_range(
        self,
        owner: str,
        repo: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        if not self.enabled or not self.cache:
            return []

        # Get all cached PR keys for this repo
        pattern = f"pr_metadata:{owner}:{repo}:%"
        cached_keys = self.cache.list_keys(pattern)

        cached_prs = []
        for key in cached_keys:
            cached_data = self.cache.get(key)
            if cached_data:
                created_at = datetime.fromisoformat(
                    cached_data["created_at"].replace("Z", "+00:00"),
                )
                if start_date <= created_at <= end_date:
                    cached_prs.append(cached_data)

        return cached_prs

# Global cache manager instance
_cache_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager  # noqa: PLW0603
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
