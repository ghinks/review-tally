"""SQLite-based cache implementation for GitHub API responses."""

from __future__ import annotations

import contextlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class SQLiteCache:
    """SQLite-based cache for GitHub API responses with TTL support."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """
        Initialize SQLite cache.

        Args:
            cache_dir: Directory for cache database.
                Defaults to ~/.review-tally-cache

        """
        if cache_dir is None:
            cache_dir = Path.home() / ".review-tally-cache"

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.db_path = self.cache_dir / "api_cache.db"
        self._connection: sqlite3.Connection | None = None

        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a persistent database connection."""
        if self._connection is None or self._connection_needs_refresh():
            # Close existing connection if it exists but needs refresh
            if self._connection:
                with contextlib.suppress(sqlite3.Error):
                    # Ignore errors during close - connection might be bad
                    self._connection.close()

            self._connection = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False,
            )
        return self._connection

    def _connection_needs_refresh(self) -> bool:
        """Check if the connection needs to be refreshed due to staleness."""
        if self._connection is None:
            return False

        try:
            # Test connection health with a simple query
            self._connection.execute("SELECT 1")
        except sqlite3.Error:
            # Connection is stale or broken
            return True
        else:
            return False

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            with contextlib.suppress(sqlite3.Error):
                # Ignore errors during close - connection might be in bad state
                self._connection.close()
            self._connection = None

    def __del__(self) -> None:
        """Ensure connection is closed when object is destroyed."""
        self.close()

    def _init_database(self) -> None:
        """Initialize the cache database with required tables."""
        conn = self._get_connection()

        # Drop old single-table schema if it exists
        conn.execute("DROP TABLE IF EXISTS api_cache")
        conn.execute("DROP INDEX IF EXISTS idx_expires_at")

        # Create PR reviews cache table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pr_reviews_cache (
                owner TEXT NOT NULL,
                repo TEXT NOT NULL,
                pull_number INTEGER NOT NULL,
                data TEXT NOT NULL,
                cached_at INTEGER NOT NULL,
                expires_at INTEGER,
                review_count INTEGER,
                pr_state TEXT,
                PRIMARY KEY (owner, repo, pull_number)
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pr_reviews_expires_at
            ON pr_reviews_cache(expires_at)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pr_reviews_owner_repo
            ON pr_reviews_cache(owner, repo)
        """)

        # Create PR metadata cache table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pr_metadata_cache (
                owner TEXT NOT NULL,
                repo TEXT NOT NULL,
                pr_number INTEGER NOT NULL,
                data TEXT NOT NULL,
                cached_at INTEGER NOT NULL,
                expires_at INTEGER,
                pr_state TEXT,
                created_at TEXT,
                PRIMARY KEY (owner, repo, pr_number)
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pr_metadata_expires_at
            ON pr_metadata_cache(expires_at)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pr_metadata_owner_repo
            ON pr_metadata_cache(owner, repo)
        """)

        # Create PR index cache table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pr_index_cache (
                owner TEXT NOT NULL,
                repo TEXT NOT NULL,
                data TEXT NOT NULL,
                cached_at INTEGER NOT NULL,
                expires_at INTEGER,
                pr_count INTEGER,
                coverage_complete INTEGER,
                PRIMARY KEY (owner, repo)
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pr_index_expires_at
            ON pr_index_cache(expires_at)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pr_index_owner
            ON pr_index_cache(owner)
        """)

        conn.commit()

    # PR Review cache methods

    def get_pr_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
    ) -> dict[str, Any] | None:
        """
        Retrieve cached PR review data if it exists and hasn't expired.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: Pull request number

        Returns:
            Cached PR review data or None if not found/expired

        """
        current_time = int(time.time())
        conn = self._get_connection()

        cursor = conn.execute(
            """
            SELECT data FROM pr_reviews_cache
            WHERE owner = ? AND repo = ? AND pull_number = ?
            AND (expires_at IS NULL OR expires_at > ?)
        """,
            (owner, repo, pull_number, current_time),
        )

        result = cursor.fetchone()
        if result:
            return json.loads(result[0])

        return None

    def set_pr_review(  # noqa: PLR0913
        self,
        owner: str,
        repo: str,
        pull_number: int,
        data: dict[str, Any],
        ttl_hours: int | None = None,
        pr_state: str | None = None,
        review_count: int | None = None,
    ) -> None:
        """
        Store PR review data in cache.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: Pull request number
            data: Review data to cache
            ttl_hours: Time to live in hours. None means never expire
            pr_state: PR state (open/closed)
            review_count: Number of reviews

        """
        current_time = int(time.time())
        expires_at = None
        if ttl_hours is not None:
            expires_at = current_time + (ttl_hours * 3600)

        data_json = json.dumps(data, sort_keys=True)
        conn = self._get_connection()

        conn.execute(
            """
            INSERT OR REPLACE INTO pr_reviews_cache
            (owner, repo, pull_number, data, cached_at, expires_at,
             review_count, pr_state)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                owner,
                repo,
                pull_number,
                data_json,
                current_time,
                expires_at,
                review_count,
                pr_state,
            ),
        )

        conn.commit()

    def delete_pr_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
    ) -> bool:
        """
        Delete a PR review cache entry.

        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: Pull request number

        Returns:
            True if entry was deleted, False if not found

        """
        conn = self._get_connection()

        cursor = conn.execute(
            """
            DELETE FROM pr_reviews_cache
            WHERE owner = ? AND repo = ? AND pull_number = ?
        """,
            (owner, repo, pull_number),
        )
        conn.commit()
        return cursor.rowcount > 0

    # PR Metadata cache methods

    def get_pr_metadata(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> dict[str, Any] | None:
        """
        Retrieve cached PR metadata if it exists and hasn't expired.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            Cached PR metadata or None if not found/expired

        """
        current_time = int(time.time())
        conn = self._get_connection()

        cursor = conn.execute(
            """
            SELECT data FROM pr_metadata_cache
            WHERE owner = ? AND repo = ? AND pr_number = ?
            AND (expires_at IS NULL OR expires_at > ?)
        """,
            (owner, repo, pr_number, current_time),
        )

        result = cursor.fetchone()
        if result:
            return json.loads(result[0])

        return None

    def set_pr_metadata(  # noqa: PLR0913
        self,
        owner: str,
        repo: str,
        pr_number: int,
        data: dict[str, Any],
        ttl_hours: int | None = None,
        pr_state: str | None = None,
        created_at: str | None = None,
    ) -> None:
        """
        Store PR metadata in cache.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            data: PR metadata to cache
            ttl_hours: Time to live in hours. None means never expire
            pr_state: PR state (open/closed)
            created_at: PR creation timestamp

        """
        current_time = int(time.time())
        expires_at = None
        if ttl_hours is not None:
            expires_at = current_time + (ttl_hours * 3600)

        data_json = json.dumps(data, sort_keys=True)
        conn = self._get_connection()

        conn.execute(
            """
            INSERT OR REPLACE INTO pr_metadata_cache
            (owner, repo, pr_number, data, cached_at, expires_at,
             pr_state, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                owner,
                repo,
                pr_number,
                data_json,
                current_time,
                expires_at,
                pr_state,
                created_at,
            ),
        )

        conn.commit()

    def delete_pr_metadata(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> bool:
        """
        Delete a PR metadata cache entry.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            True if entry was deleted, False if not found

        """
        conn = self._get_connection()

        cursor = conn.execute(
            """
            DELETE FROM pr_metadata_cache
            WHERE owner = ? AND repo = ? AND pr_number = ?
        """,
            (owner, repo, pr_number),
        )
        conn.commit()
        return cursor.rowcount > 0

    # PR Index cache methods

    def get_pr_index(
        self,
        owner: str,
        repo: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve cached PR index data if it exists and hasn't expired.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Cached PR index data or None if not found/expired

        """
        current_time = int(time.time())
        conn = self._get_connection()

        cursor = conn.execute(
            """
            SELECT data FROM pr_index_cache
            WHERE owner = ? AND repo = ?
            AND (expires_at IS NULL OR expires_at > ?)
        """,
            (owner, repo, current_time),
        )

        result = cursor.fetchone()
        if result:
            return json.loads(result[0])

        return None

    def set_pr_index(  # noqa: PLR0913
        self,
        owner: str,
        repo: str,
        data: dict[str, Any],
        ttl_hours: int | None = None,
        pr_count: int | None = None,
        *,
        coverage_complete: bool = False,
    ) -> None:
        """
        Store PR index data in cache.

        Args:
            owner: Repository owner
            repo: Repository name
            data: PR index data to cache
            ttl_hours: Time to live in hours. None means never expire
            pr_count: Number of PRs in the index
            coverage_complete: Whether index coverage is complete

        """
        current_time = int(time.time())
        expires_at = None
        if ttl_hours is not None:
            expires_at = current_time + (ttl_hours * 3600)

        data_json = json.dumps(data, sort_keys=True)
        conn = self._get_connection()

        conn.execute(
            """
            INSERT OR REPLACE INTO pr_index_cache
            (owner, repo, data, cached_at, expires_at, pr_count,
             coverage_complete)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                owner,
                repo,
                data_json,
                current_time,
                expires_at,
                pr_count,
                1 if coverage_complete else 0,
            ),
        )

        conn.commit()

    def delete_pr_index(
        self,
        owner: str,
        repo: str,
    ) -> bool:
        """
        Delete a PR index cache entry.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            True if entry was deleted, False if not found

        """
        conn = self._get_connection()

        cursor = conn.execute(
            "DELETE FROM pr_index_cache WHERE owner = ? AND repo = ?",
            (owner, repo),
        )
        conn.commit()
        return cursor.rowcount > 0

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed

        """
        current_time = int(time.time())
        conn = self._get_connection()

        total_removed = 0

        # Clean each table
        for table_name in [
            "pr_reviews_cache",
            "pr_metadata_cache",
            "pr_index_cache",
        ]:
            # Table names are hardcoded constants, safe from injection
            cursor = conn.execute(
                f"""
                DELETE FROM {table_name}
                WHERE expires_at IS NOT NULL AND expires_at <= ?
            """,  # noqa: S608
                (current_time,),
            )
            total_removed += cursor.rowcount

        conn.commit()
        return total_removed

    def clear_all(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries removed

        """
        conn = self._get_connection()

        total_removed = 0

        # Clear each table
        for table_name in [
            "pr_reviews_cache",
            "pr_metadata_cache",
            "pr_index_cache",
        ]:
            # Table names are hardcoded constants, safe from injection
            cursor = conn.execute(f"DELETE FROM {table_name}")  # noqa: S608
            total_removed += cursor.rowcount

        conn.commit()
        return total_removed

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics

        """
        current_time = int(time.time())
        conn = self._get_connection()

        total_entries = 0
        expired_entries = 0
        cache_size_bytes = 0
        stats_by_table = {}

        # Aggregate stats across all tables
        for table_name, key_prefix in [
            ("pr_reviews_cache", "pr_reviews"),
            ("pr_metadata_cache", "pr_metadata"),
            ("pr_index_cache", "pr_index"),
        ]:
            # Total entries per table (table names are hardcoded constants)
            total_cursor = conn.execute(
                f"SELECT COUNT(*) FROM {table_name}",  # noqa: S608
            )
            table_total = total_cursor.fetchone()[0]
            total_entries += table_total

            # Expired entries per table
            expired_cursor = conn.execute(
                f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE expires_at IS NOT NULL AND expires_at <= ?
            """,  # noqa: S608
                (current_time,),
            )
            table_expired = expired_cursor.fetchone()[0]
            expired_entries += table_expired

            # Cache size per table
            size_cursor = conn.execute(
                f"SELECT SUM(LENGTH(data)) FROM {table_name}",  # noqa: S608
            )
            table_size = size_cursor.fetchone()[0] or 0
            cache_size_bytes += table_size

            stats_by_table[key_prefix] = {
                "total": table_total,
                "expired": table_expired,
                "valid": table_total - table_expired,
                "size_bytes": table_size,
            }

        # Database file size
        db_size_bytes = (
            self.db_path.stat().st_size if self.db_path.exists() else 0
        )

        return {
            "total_entries": total_entries,
            "valid_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
            "cache_size_bytes": cache_size_bytes,
            "cache_size_mb": round(cache_size_bytes / (1024 * 1024), 2),
            "db_size_bytes": db_size_bytes,
            "db_size_mb": round(db_size_bytes / (1024 * 1024), 2),
            "db_path": str(self.db_path),
            "by_table": stats_by_table,
        }
