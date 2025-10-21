"""Tests for PR metadata date range functionality."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from reviewtally.cache.sqlite_cache import SQLiteCache

if TYPE_CHECKING:
    from collections.abc import Generator

EXPECTED_PR_COUNT = 3


@pytest.fixture
def temp_cache_dir() -> Generator[Path, None, None]:
    """Create a temporary cache directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache_manager(temp_cache_dir: Path) -> Generator[SQLiteCache, None, None]:
    """Create a SQLiteCache directly to bypass test environment checks."""
    cache = SQLiteCache(cache_dir=temp_cache_dir)
    yield cache
    # Explicitly close the database connection for Windows compatibility
    cache.close()


def test_get_pr_metadata_date_range_empty(
    cache_manager: SQLiteCache,
) -> None:
    """Test getting date range when no PRs are cached."""
    result = cache_manager.get_pr_metadata_date_range(
        "test-owner",
        "test-repo",
    )
    assert result is None


def test_get_pr_metadata_date_range_single_pr(
    cache_manager: SQLiteCache,
) -> None:
    """Test getting date range with a single cached PR."""
    pr_data = {
        "number": 1,
        "state": "open",
        "created_at": "2024-01-15T10:00:00Z",
        "title": "Test PR",
    }

    cache_manager.set_pr_metadata(
        "test-owner",
        "test-repo",
        1,
        pr_data,
        ttl_hours=None,
        pr_state="open",
        created_at="2024-01-15T10:00:00Z",
    )

    result = cache_manager.get_pr_metadata_date_range(
        "test-owner",
        "test-repo",
    )

    assert result is not None
    assert result["min_date"] == "2024-01-15T10:00:00Z"
    assert result["max_date"] == "2024-01-15T10:00:00Z"
    assert result["count"] == 1


def test_get_pr_metadata_date_range_multiple_prs(
    cache_manager: SQLiteCache,
) -> None:
    """Test getting date range with multiple cached PRs."""
    pr_data_1 = {
        "number": 1,
        "state": "closed",
        "created_at": "2024-01-10T10:00:00Z",
        "title": "First PR",
    }
    pr_data_2 = {
        "number": 2,
        "state": "open",
        "created_at": "2024-01-20T10:00:00Z",
        "title": "Second PR",
    }
    pr_data_3 = {
        "number": 3,
        "state": "closed",
        "created_at": "2024-01-15T10:00:00Z",
        "title": "Third PR",
    }

    cache_manager.set_pr_metadata(
        "test-owner",
        "test-repo",
        1,
        pr_data_1,
        ttl_hours=None,
        pr_state="closed",
        created_at="2024-01-10T10:00:00Z",
    )
    cache_manager.set_pr_metadata(
        "test-owner",
        "test-repo",
        2,
        pr_data_2,
        ttl_hours=None,
        pr_state="open",
        created_at="2024-01-20T10:00:00Z",
    )
    cache_manager.set_pr_metadata(
        "test-owner",
        "test-repo",
        3,
        pr_data_3,
        ttl_hours=None,
        pr_state="closed",
        created_at="2024-01-15T10:00:00Z",
    )

    result = cache_manager.get_pr_metadata_date_range(
        "test-owner",
        "test-repo",
    )

    assert result is not None
    assert result["min_date"] == "2024-01-10T10:00:00Z"
    assert result["max_date"] == "2024-01-20T10:00:00Z"
    assert result["count"] == EXPECTED_PR_COUNT


def test_get_pr_metadata_date_range_different_repos(
    cache_manager: SQLiteCache,
) -> None:
    """Test date range is isolated per repository."""
    pr_data_repo1 = {
        "number": 1,
        "state": "open",
        "created_at": "2024-01-10T10:00:00Z",
        "title": "Repo 1 PR",
    }
    pr_data_repo2 = {
        "number": 1,
        "state": "open",
        "created_at": "2024-02-15T10:00:00Z",
        "title": "Repo 2 PR",
    }

    cache_manager.set_pr_metadata(
        "test-owner",
        "repo1",
        1,
        pr_data_repo1,
        ttl_hours=None,
        pr_state="open",
        created_at="2024-01-10T10:00:00Z",
    )
    cache_manager.set_pr_metadata(
        "test-owner",
        "repo2",
        1,
        pr_data_repo2,
        ttl_hours=None,
        pr_state="open",
        created_at="2024-02-15T10:00:00Z",
    )

    result_repo1 = cache_manager.get_pr_metadata_date_range(
        "test-owner",
        "repo1",
    )
    result_repo2 = cache_manager.get_pr_metadata_date_range(
        "test-owner",
        "repo2",
    )

    assert result_repo1 is not None
    assert result_repo1["min_date"] == "2024-01-10T10:00:00Z"
    assert result_repo1["count"] == 1

    assert result_repo2 is not None
    assert result_repo2["min_date"] == "2024-02-15T10:00:00Z"
    assert result_repo2["count"] == 1


def test_get_pr_metadata_date_range_ignores_expired(
    cache_manager: SQLiteCache,
) -> None:
    """Test that expired entries are not included in date range."""
    pr_data = {
        "number": 1,
        "state": "open",
        "created_at": "2024-01-15T10:00:00Z",
        "title": "Test PR",
    }

    # Set with very short TTL (will expire immediately)
    cache_manager.set_pr_metadata(
        "test-owner",
        "test-repo",
        1,
        pr_data,
        ttl_hours=0,  # Expire immediately
        pr_state="open",
        created_at="2024-01-15T10:00:00Z",
    )

    result = cache_manager.get_pr_metadata_date_range(
        "test-owner",
        "test-repo",
    )

    # Should return None because the only entry is expired
    assert result is None
