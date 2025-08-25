"""Main cache manager for GitHub API response caching."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from reviewtally.cache.cache_keys import (
    generate_pr_reviews_cache_key,
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

    def get_pr_reviews_cache(
        self,
        owner: str,
        repo: str,
        pull_numbers: list[int],
    ) -> list[dict[str, Any]] | None:
        """
        Get cached PR reviews data.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_numbers: List of PR numbers

        Returns:
            Cached review data or None if not found

        """
        if not self.enabled or not self.cache:
            return None

        cache_key = generate_pr_reviews_cache_key(owner, repo, pull_numbers)
        cached_data = self.cache.get(cache_key)

        if cached_data:
            print(  # noqa: T201
                f"Cache HIT: PR reviews for {owner}/{repo} "
                f"({len(pull_numbers)} PRs)",
            )
            return cached_data.get("reviews", [])

        return None

    def get_single_pr_reviews_cache(
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

    def set_single_pr_reviews_cache(
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

    def set_pr_reviews_cache(
        self,
        owner: str,
        repo: str,
        pull_numbers: list[int],
        reviews_data: list[dict[str, Any]],
        pr_states: dict[int, str] | None = None,
    ) -> None:
        """
        Cache PR reviews data.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_numbers: List of PR numbers
            reviews_data: Review data to cache
            pr_states: Optional PR state lookup for TTL determination

        """
        if not self.enabled or not self.cache:
            return

        cache_key = generate_pr_reviews_cache_key(owner, repo, pull_numbers)

        # Determine TTL based on PR states
        ttl_hours = None  # Never expire by default

        # If we have PR states, only cache closed PRs forever
        if pr_states:
            [pr for pr in pull_numbers if pr_states.get(pr) == "closed"]
            open_prs = [
                pr for pr in pull_numbers if pr_states.get(pr) == "open"
            ]

            if open_prs:
                # If any PRs are open, use short TTL
                ttl_hours = 1
            # If all PRs are closed, cache forever (ttl_hours = None)

        metadata = {
            "owner": owner,
            "repo": repo,
            "pull_count": len(pull_numbers),
            "review_count": len(reviews_data),
            "pr_states": pr_states,
        }

        self.cache.set(
            cache_key,
            {"reviews": reviews_data},
            ttl_hours=ttl_hours,
            metadata=metadata,
        )

        ttl_desc = "forever" if ttl_hours is None else f"{ttl_hours}h"
        print(f"Cache SET: PR reviews for {owner}/{repo} (TTL: {ttl_desc})")  # noqa: T201

    def cleanup_expired(self) -> int:
        """
        Clean up expired cache entries.

        Returns:
            Number of entries cleaned up

        """
        if not self.enabled or not self.cache:
            return 0

        return self.cache.cleanup_expired()

    def clear_all(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared

        """
        if not self.enabled or not self.cache:
            return 0

        return self.cache.clear_all()

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Cache statistics dictionary

        """
        if not self.enabled or not self.cache:
            return {"enabled": False, "message": "Cache is disabled"}

        stats = self.cache.get_stats()
        stats["enabled"] = True
        return stats

    def list_keys(self, pattern: str | None = None) -> list[str]:
        """
        List cache keys.

        Args:
            pattern: Optional pattern to filter keys

        Returns:
            List of cache keys

        """
        if not self.enabled or not self.cache:
            return []

        return self.cache.list_keys(pattern)


# Global cache manager instance
_cache_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager  # noqa: PLW0603
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def clear_cache_manager() -> None:
    """Clear the global cache manager instance (for testing)."""
    global _cache_manager  # noqa: PLW0603
    _cache_manager = None

