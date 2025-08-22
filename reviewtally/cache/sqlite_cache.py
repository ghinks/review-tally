"""SQLite-based cache implementation for GitHub API responses."""

from __future__ import annotations

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

        self._init_database()

    def _init_database(self) -> None:
        """Initialize the cache database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    cache_key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    cached_at INTEGER NOT NULL,
                    expires_at INTEGER,
                    content_hash TEXT,
                    metadata TEXT
                )
            """)

            # Index for efficient TTL cleanup
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON api_cache(expires_at)
            """)

            conn.commit()

    def get(self, key: str) -> dict[str, Any] | None:
        """
        Retrieve cached data if it exists and hasn't expired.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached data dict or None if not found/expired

        """
        current_time = int(time.time())

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT data, expires_at FROM api_cache
                WHERE cache_key = ? AND (expires_at IS NULL OR expires_at > ?)
            """, (key, current_time))

            result = cursor.fetchone()
            if result:
                data_json, expires_at = result
                return json.loads(data_json)

        return None

    def set(
        self,
        key: str,
        data: dict[str, Any],
        ttl_hours: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Store data in cache with optional TTL.

        Args:
            key: Cache key
            data: Data to cache
            ttl_hours: Time to live in hours. None means never expire
            metadata: Optional metadata to store with the cache entry

        """
        current_time = int(time.time())
        expires_at = None
        if ttl_hours is not None:
            expires_at = current_time + (ttl_hours * 3600)

        data_json = json.dumps(data, sort_keys=True)
        content_hash = str(hash(data_json))
        metadata_json = json.dumps(metadata) if metadata else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO api_cache
                (cache_key, data, cached_at, expires_at, content_hash,
                 metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                key, data_json, current_time, expires_at,
                content_hash, metadata_json,
            ))

            conn.commit()

    def delete(self, key: str) -> bool:
        """
        Delete a specific cache entry.

        Args:
            key: Cache key to delete

        Returns:
            True if entry was deleted, False if not found

        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM api_cache WHERE cache_key = ?", (key,),
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

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM api_cache
                WHERE expires_at IS NOT NULL AND expires_at <= ?
            """, (current_time,))
            conn.commit()
            return cursor.rowcount

    def clear_all(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries removed

        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM api_cache")
            conn.commit()
            return cursor.rowcount

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics

        """
        current_time = int(time.time())

        with sqlite3.connect(self.db_path) as conn:
            # Total entries
            total_cursor = conn.execute("SELECT COUNT(*) FROM api_cache")
            total_entries = total_cursor.fetchone()[0]

            # Expired entries
            expired_cursor = conn.execute("""
                SELECT COUNT(*) FROM api_cache
                WHERE expires_at IS NOT NULL AND expires_at <= ?
            """, (current_time,))
            expired_entries = expired_cursor.fetchone()[0]

            # Cache size
            size_cursor = conn.execute(
                "SELECT SUM(LENGTH(data)) FROM api_cache",
            )
            cache_size_bytes = size_cursor.fetchone()[0] or 0

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
        }

    def list_keys(self, pattern: str | None = None) -> list[str]:
        """
        List cache keys, optionally filtered by pattern.

        Args:
            pattern: SQL LIKE pattern to filter keys

        Returns:
            List of matching cache keys

        """
        with sqlite3.connect(self.db_path) as conn:
            if pattern:
                cursor = conn.execute(
                    "SELECT cache_key FROM api_cache WHERE cache_key LIKE ?",
                    (pattern,),
                )
            else:
                cursor = conn.execute("SELECT cache_key FROM api_cache")

            return [row[0] for row in cursor.fetchall()]

