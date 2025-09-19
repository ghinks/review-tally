"""Main cache manager for GitHub API response caching."""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Any

from reviewtally.cache import MODERATE_THRESHOLD_DAYS, RECENT_THRESHOLD_DAYS
from reviewtally.cache.cache_keys import (
    gen_pr_key,
    gen_pr_list_metadata_key,
    gen_pr_review_key,
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
        if not self.enabled or not self.cache:
            return None

        cache_key = gen_pr_review_key(
            owner, repo, pull_number,
        )
        cached_data = self.cache.get(cache_key)

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

        cache_key = gen_pr_review_key(
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

        cache_key = gen_pr_key(owner, repo, pr_number)
        return self.cache.get(cache_key)

    def cache_pr(
        self,
        owner: str,
        repo: str,
        pr_data: dict[str, Any],
    ) -> None:
        if not self.enabled or not self.cache:
            return

        pr_number = pr_data["number"]
        cache_key = gen_pr_key(owner, repo, pr_number)

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

    def get_pr_list(
        self,
        owner: str,
        repo: str,
    ) -> dict[str, Any] | None:
        if not self.enabled or not self.cache:
            return None

        cache_key = gen_pr_list_metadata_key(owner, repo)
        return self.cache.get(cache_key)

    def set_pr_list(
        self,
        owner: str,
        repo: str,
        pr_index_data: dict[str, Any],
    ) -> None:
        if not self.enabled or not self.cache:
            return

        cache_key = gen_pr_list_metadata_key(owner, repo)

        # PR index has moderate TTL - needs regular updates for active repos
        ttl_hours = 6  # 6 hours for PR index

        metadata = {
            "owner": owner,
            "repo": repo,
            "pr_count": len(pr_index_data.get("prs", [])),
            "coverage_complete": pr_index_data.get("coverage_complete", False),
        }

        self.cache.set(
            cache_key,
            pr_index_data,
            ttl_hours=ttl_hours,
            metadata=metadata,
        )

    def get_cached_prs_for_date_range(
        self,
        owner: str,
        repo: str,
        start_date: datetime,
        end_date: datetime,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        if not self.enabled or not self.cache:
            return [], None

        # Get PR index from cache
        pr_index = self.get_pr_list(owner, repo)
        if not pr_index:
            return [], None

        # Filter PRs by date range from lightweight index
        cached_prs = []
        for pr_summary in pr_index.get("prs", []):
            created_at = datetime.fromisoformat(
                pr_summary["created_at"].replace("Z", "+00:00"),
            )
            if start_date <= created_at <= end_date:
                # Get full PR details from detail cache
                full_pr = self.get_pr(
                    owner, repo, pr_summary["number"],
                )
                if full_pr:
                    cached_prs.append(full_pr)

        return cached_prs, pr_index

    def needs_backward_fetch(
        self,
        pr_index: dict[str, Any] | None,
        start_date: datetime,
    ) -> bool:
        if not pr_index or pr_index.get("coverage_complete", False):
            return False

        earliest_pr = pr_index.get("earliest_pr")
        if earliest_pr is None:
            # No PRs exist in this repo - no backward fetch needed
            return False
        if not earliest_pr:
            print("Warning: PR index missing earliest_pr field")  # noqa: T201
            return True

        earliest_date = datetime.fromisoformat(
            earliest_pr.replace("Z", "+00:00"),
        )
        print(f" {start_date.date()}: {earliest_date.date()}")  # noqa: T201
        return start_date.date() < earliest_date.date()

    def needs_forward_fetch(
        self,
        pr_index: dict[str, Any] | None,
    ) -> bool:
        if not pr_index:
            return True

        # Check if cache is stale (older than TTL threshold)
        last_updated = pr_index.get("last_updated")
        if not last_updated:
            return True

        last_update_time = datetime.fromisoformat(
            last_updated.replace("Z", "+00:00"),
        )
        now = datetime.now(last_update_time.tzinfo)
        hours_since_update = (now - last_update_time).total_seconds() / 3600

        return hours_since_update > 1  # Refresh if older than 1 hour

# Global cache manager instance
_cache_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager  # noqa: PLW0603
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
