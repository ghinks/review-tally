"""Main cache manager for GitHub API response caching."""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Any

from reviewtally.cache.cache_keys import (
    generate_pr_list_cache_key,
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

    def _calculate_pr_list_ttl(self, end_date: datetime) -> int | None:
        # TTL constants
        recent_threshold_days = 7
        moderate_threshold_days = 30

        now = datetime.now(end_date.tzinfo or None)
        days_ago = (now - end_date).days

        if days_ago < recent_threshold_days:
            return 1  # 1 hour for very recent data
        if days_ago < moderate_threshold_days:
            return 6  # 6 hours for recent data
        return None  # Permanent cache for data older than 30 days

    def get_cached_pr_list(
        self,
        owner: str,
        repo: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]] | None:
        if not self.enabled or not self.cache:
            return None

        cache_key = generate_pr_list_cache_key(
            owner,
            repo,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )
        cached_data = self.cache.get(cache_key)

        if cached_data:
            pr_count = len(cached_data.get("pr_list", []))
            print(  # noqa: T201
                f"Cache HIT: PR list for {owner}/{repo} "
                f"({start_date.strftime('%Y-%m-%d')} to "
                f"{end_date.strftime('%Y-%m-%d')}) - {pr_count} PRs",
            )
            return cached_data.get("pr_list", [])

        return None

    def cache_pr_list(
        self,
        owner: str,
        repo: str,
        start_date: datetime,
        end_date: datetime,
        pr_list: list[dict[str, Any]],
    ) -> None:
        if not self.enabled or not self.cache:
            return

        cache_key = generate_pr_list_cache_key(
            owner,
            repo,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )

        # Calculate smart TTL based on date range recency
        ttl_hours = self._calculate_pr_list_ttl(end_date)

        metadata = {
            "owner": owner,
            "repo": repo,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "pr_count": len(pr_list),
        }

        self.cache.set(
            cache_key,
            {"pr_list": pr_list},
            ttl_hours=ttl_hours,
            metadata=metadata,
        )

        ttl_desc = "forever" if ttl_hours is None else f"{ttl_hours}h"
        print(  # noqa: T201
            f"Cache SET: PR list for {owner}/{repo} "
            f"({start_date.strftime('%Y-%m-%d')} to "
            f"{end_date.strftime('%Y-%m-%d')}) - {len(pr_list)} PRs "
            f"(TTL: {ttl_desc})",
        )

# Global cache manager instance
_cache_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager  # noqa: PLW0603
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
