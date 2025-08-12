import unittest
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

from reviewtally.main import ReviewDataContext, collect_review_data


class TestMissingSubmittedAtMain(unittest.TestCase):
    """Test handling of missing submitted_at field in main.py functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Mock PR lookup data
        self.pr_lookup = {
            12: {"number": 12, "created_at": "2019-11-17T16:00:00Z"},
        }

        # Sample reviewer data with mixed submitted_at scenarios
        self.reviewer_data = [
            {
                "user": {"login": "reviewer_with_timestamp"},
                "comment_count": 2,
                "pull_number": 12,
                "submitted_at": "2019-11-17T17:43:43Z",  # Has timestamp
            },
            {
                "user": {"login": "reviewer_missing_timestamp"},
                "comment_count": 1,
                "pull_number": 12,
                "submitted_at": None,  # Missing timestamp
            },
        ]
        self.NUM_COMMENTS = len(self.reviewer_data)
        self.NUM_COMMENTS_WITH_TS = 1

        # Initialize context
        self.context = ReviewDataContext(
            org_name="test-org",
            repo="test-repo",
            pull_requests=[
                {"number": 12, "created_at": "2019-11-17T16:00:00Z"},
            ],
            reviewer_stats={},
        )

    @patch("reviewtally.main.get_reviewers_with_comments_for_pull_requests")
    @patch("builtins.print")
    def test_collect_review_data_handles_missing_submitted_at(
        self,
        mock_print: Any,
        mock_get_reviewers: Any,
    ) -> None:
        """Test missing submitted_at gracefully."""
        # Arrange
        mock_get_reviewers.return_value = self.reviewer_data

        # Act
        collect_review_data(self.context)

        # Assert
        # Both reviewers should be counted for reviews and comments
        assert len(self.context.reviewer_stats) == len(self.reviewer_data)

        # Check reviewer with timestamp
        reviewer_with_ts = self.context.reviewer_stats[
            "reviewer_with_timestamp"
        ]
        assert reviewer_with_ts["reviews"] == self.NUM_COMMENTS_WITH_TS
        assert reviewer_with_ts["comments"] == self.NUM_COMMENTS

        # Check reviewer missing timestamp
        reviewer_missing_ts = self.context.reviewer_stats[
            "reviewer_missing_timestamp"
        ]
        assert reviewer_missing_ts["reviews"] == \
            self.NUM_COMMENTS - self.NUM_COMMENTS_WITH_TS

        # Should have printed warning for missing timestamp
        mock_print.assert_called_with(
            "Warning: Skipping time metrics for review by "
            "reviewer_missing_timestamp on PR 12 (missing submitted_at)",
        )

    @patch("reviewtally.main.get_reviewers_with_comments_for_pull_requests")
    @patch("builtins.print")
    def test_collect_review_data_sprint_aggregation_missing_submitted_at(
        self,
        mock_print: Any,
        mock_get_reviewers: Any,
    ) -> None:
        """Test sprint aggregation skips reviews with missing submitted_at."""
        # Arrange
        mock_get_reviewers.return_value = self.reviewer_data

        # Enable sprint stats
        self.context.sprint_stats = {}
        self.context.sprint_periods = [
            (
                datetime(2019, 11, 17, tzinfo=timezone.utc),
                datetime(2019, 12, 1, tzinfo=timezone.utc),
                "2019-11-17",
            ),
        ]

        # Act
        collect_review_data(self.context)

        # Assert
        # Should have sprint stats only for reviewer with timestamp
        assert "2019-11-17" in self.context.sprint_stats
        sprint_data = self.context.sprint_stats["2019-11-17"]

        # Sprint stats should only include one review (the one with timestamp)
        assert sprint_data["total_reviews"] == self.NUM_COMMENTS_WITH_TS
        assert sprint_data["total_comments"] == self.NUM_COMMENTS
        assert len(sprint_data["unique_reviewers"]) == \
               self.NUM_COMMENTS_WITH_TS
        assert "reviewer_with_timestamp" in sprint_data["unique_reviewers"]
        assert (
            "reviewer_missing_timestamp" not in sprint_data["unique_reviewers"]
        )

        # Should print warning for missing timestamp in sprint aggregation
        expected_calls = [
            unittest.mock.call(
                "Warning: Skipping time metrics for review by "
                "reviewer_missing_timestamp on PR 12 (missing submitted_at)",
            ),
            unittest.mock.call(
                "Warning: Skipping sprint aggregation for review by "
                "reviewer_missing_timestamp on PR 12 (missing submitted_at)",
            ),
        ]
        mock_print.assert_has_calls(expected_calls)

    def test_reviewer_data_with_all_missing_submitted_at(self) -> None:
        """Test behavior when all reviews have missing submitted_at."""
        # Arrange
        reviewer_data_all_missing = [
            {
                "user": {"login": "reviewer1"},
                "comment_count": 1,
                "pull_number": 12,
                "submitted_at": None,
            },
            {
                "user": {"login": "reviewer2"},
                "comment_count": 2,
                "pull_number": 12,
                "submitted_at": None,
            },
        ]

        # Mock the get_reviewers function
        with (
            patch(
                "reviewtally.main.get_reviewers_with_comments_for_pull_requests",
            ) as mock_get_reviewers,
            patch("builtins.print") as mock_print,
        ):
            mock_get_reviewers.return_value = reviewer_data_all_missing

            # Act
            collect_review_data(self.context)

            # Assert
            # Both reviewers should be counted but no time data
            assert len(self.context.reviewer_stats) == \
                   len(reviewer_data_all_missing)

            for reviewer in ["reviewer1", "reviewer2"]:
                stats = self.context.reviewer_stats[reviewer]
                assert stats["reviews"] == 1
                assert len(stats["review_times"]) == 0
                assert len(stats["pr_created_times"]) == 0

            # Should have printed warnings for both reviewers
            assert mock_print.call_count == len(reviewer_data_all_missing)


if __name__ == "__main__":
    unittest.main()
