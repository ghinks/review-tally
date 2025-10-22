"""Main cache manager for GitHub API response caching."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from reviewtally.cache import MODERATE_THRESHOLD_DAYS, RECENT_THRESHOLD_DAYS
from reviewtally.cache.sqlite_cache import SQLiteCache

if TYPE_CHECKING:
    from pathlib import Path


class CacheManager:
    """Main interface for caching GitHub API responses."""

    cache: SQLiteCache | None

    def __init__(
        self,
        cache_dir: Path | None = None,
        *,
        enabled: bool = True,
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
        if not self.enabled or not self.cache:
            return None

        cached_data = self.cache.get_pr_review(owner, repo, pull_number)

        if cached_data:
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
        if not self.enabled or not self.cache:
            return

        # Determine TTL based on PR state
        ttl_hours = None  # Never expire by default
        if pr_state == "open":
            ttl_hours = 1  # Short TTL for open PRs

        self.cache.set_pr_review(
            owner,
            repo,
            pull_number,
            {"reviews": reviews_data},
            ttl_hours=ttl_hours,
            pr_state=pr_state,
            review_count=len(reviews_data),
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

    def get_pr(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> dict[str, Any] | None:
        if not self.enabled or not self.cache:
            return None

        return self.cache.get_pr_metadata(owner, repo, pr_number)

    def cache_pr(
        self,
        owner: str,
        repo: str,
        pr_data: dict[str, Any],
    ) -> None:
        if not self.enabled or not self.cache:
            return

        pr_number = pr_data["number"]

        # Calculate TTL based on PR creation date
        ttl_hours = self._calculate_pr_ttl(pr_data["created_at"])

        self.cache.set_pr_metadata(
            owner,
            repo,
            pr_number,
            pr_data,
            ttl_hours=ttl_hours,
            pr_state=pr_data.get("state"),
            created_at=pr_data["created_at"],
        )

    def get_pr_stats(
        self,
        owner: str,
        repo: str,
    ) -> dict[str, Any] | None:
        """Get cache statistics from pr_metadata_cache."""
        if not self.enabled or not self.cache:
            return None

        return self.cache.get_pr_metadata_stats(owner, repo)

    def get_cached_prs_for_date_range(
        self,
        owner: str,
        repo: str,
        start_date: datetime,
        end_date: datetime,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        if not self.enabled or not self.cache:
            return [], None

        # Get PR summaries from pr_metadata_cache
        pr_summaries = self.cache.get_pr_summaries(owner, repo)
        if not pr_summaries:
            return [], None

        # Get cache stats for metadata
        pr_stats = self.get_pr_stats(owner, repo)

        # Filter PRs by date range from lightweight summaries
        cached_prs = []
        for pr_summary in pr_summaries:
            created_at = datetime.fromisoformat(
                pr_summary["created_at"].replace("Z", "+00:00"),
            )
            if start_date <= created_at <= end_date:
                # Get full PR details from detail cache
                full_pr = self.get_pr(
                    owner,
                    repo,
                    pr_summary["number"],
                )
                if full_pr:
                    cached_prs.append(full_pr)

        return cached_prs, pr_stats

    def needs_backward_fetch(
        self,
        pr_stats: dict[str, Any] | None,
        start_date: datetime,
    ) -> bool:
        if not pr_stats:
            return True

        earliest_pr = pr_stats.get("earliest_pr")
        if not earliest_pr:
            # No PRs in cache or missing earliest_pr
            return True

        earliest_date = datetime.fromisoformat(
            earliest_pr.replace("Z", "+00:00"),
        )
        print(f" {start_date.date()}: {earliest_date.date()}")  # noqa: T201
        return start_date.date() < earliest_date.date()

    def needs_forward_fetch(
        self,
        pr_stats: dict[str, Any] | None,
    ) -> bool:
        if not pr_stats:
            return True

        # Check if cache is stale (older than TTL threshold)
        last_updated = pr_stats.get("last_updated")
        if not last_updated:
            return True

        # last_updated is a Unix timestamp (integer)
        last_update_time = datetime.fromtimestamp(
            last_updated,
            tz=timezone.utc,
        )
        now = datetime.now(tz=timezone.utc)
        hours_since_update = (now - last_update_time).total_seconds() / 3600

        return hours_since_update > 1  # Refresh if older than 1 hour

    def get_cached_date_range(
        self,
        owner: str,
        repo: str,
    ) -> dict[str, Any] | None:
        """
        Get the date range of currently cached PR metadata for a repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Dict with min_date, max_date, and count or None if no cached data

        """
        if not self.enabled or not self.cache:
            return None

        return self.cache.get_pr_metadata_date_range(owner, repo)


# Global cache manager instance
_cache_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager  # noqa: PLW0603
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
