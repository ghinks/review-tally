import unittest
from typing import Any

from reviewtally.main import generate_results_table


class TestGenerateResultsTable(unittest.TestCase):
    """Test the generate_results_table function's sorting behavior."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Sample reviewer stats with different metrics values
        self.reviewer_stats: dict[str, dict[str, Any]] = {
            "user_high_reviews": {
                "reviews": 10,
                "comments": 5,
                "engagement_level": "Low",
                "thoroughness_score": 25,
                "avg_response_time_hours": 2.5,
                "avg_completion_time_hours": 8.0,
                "active_review_days": 5,
            },
            "user_medium_reviews": {
                "reviews": 5,
                "comments": 20,
                "engagement_level": "High",
                "thoroughness_score": 75,
                "avg_response_time_hours": 1.0,
                "avg_completion_time_hours": 4.0,
                "active_review_days": 3,
            },
            "user_low_reviews": {
                "reviews": 2,
                "comments": 1,
                "engagement_level": "Low",
                "thoroughness_score": 10,
                "avg_response_time_hours": 0.5,
                "avg_completion_time_hours": 2.0,
                "active_review_days": 1,
            },
        }

    def test_default_metrics_sorting(self) -> None:
        """Test sorting with default metrics."""
        metrics = ["reviews", "comments", "avg-comments"]
        result = generate_results_table(self.reviewer_stats, metrics)

        # Split result into lines and extract user column
        lines = result.split("\n")
        # Skip header and separator lines, get actual data rows
        data_lines = [
            line
            for line in lines
            if line and not line.startswith("-") and "User" not in line
        ]

        # Extract usernames from the first column
        users = []
        for line in data_lines:
            parts = line.split()
            if parts:
                users.append(parts[0])

        # Should be sorted by reviews (descending), then comments (descending)
        # user_high_reviews: 10 reviews, 5 comments
        # user_medium_reviews: 5 reviews, 20 comments
        # user_low_reviews: 2 reviews, 1 comment
        expected_order = [
            "user_high_reviews",
            "user_medium_reviews",
            "user_low_reviews",
        ]
        self.assertEqual(users, expected_order)

    def test_custom_metrics_with_formatted_values(self) -> None:
        """Test that sorting works correctly with formatted metrics."""
        # This test demonstrates potential fragility with different orders
        metrics = ["thoroughness", "engagement", "reviews", "comments"]
        result = generate_results_table(self.reviewer_stats, metrics)

        # The current implementation assumes reviews is at index 1 and
        # comments at index 2. But with this metric order, thoroughness
        # is at index 1, engagement at index 2. This test should work
        # with the fixed implementation but may fail with the current one

        lines = result.split("\n")
        data_lines = [
            line
            for line in lines
            if line and not line.startswith("-") and "User" not in line
        ]

        users = []
        for line in data_lines:
            parts = line.split()
            if parts:
                users.append(parts[0])

        # Should still be sorted by reviews (descending), then comments
        expected_order = [
            "user_high_reviews",
            "user_medium_reviews",
            "user_low_reviews",
        ]
        self.assertEqual(users, expected_order)

    def test_metrics_with_only_formatted_values(self) -> None:
        """Test with metrics that don't include raw numeric values."""
        # This will likely expose the bug in the current implementation
        metrics = ["engagement", "thoroughness", "response-time"]

        # This should not raise an exception and should sort by raw
        # reviews/comments even though those columns are not displayed
        try:
            result = generate_results_table(self.reviewer_stats, metrics)

            lines = result.split("\n")
            data_lines = [
                line
                for line in lines
                if line and not line.startswith("-") and "User" not in line
            ]

            users = []
            for line in data_lines:
                parts = line.split()
                if parts:
                    users.append(parts[0])

            # Should still be sorted by underlying reviews/comments values
            expected_order = [
                "user_high_reviews",
                "user_medium_reviews",
                "user_low_reviews",
            ]
            self.assertEqual(users, expected_order)

        except (IndexError, ValueError) as e:
            # This is the bug we're trying to fix - the current implementation
            # fails when the expected columns aren't at the expected positions
            self.fail(f"generate_results_table raised {type(e).__name__}: {e}")

    def test_edge_case_empty_stats(self) -> None:
        """Test with empty reviewer stats."""
        result = generate_results_table({}, ["reviews", "comments"])

        # Should return table with just headers
        lines = result.split("\n")
        # Filter out empty lines
        non_empty_lines = [line for line in lines if line.strip()]

        # Should have header line and separator line only
        self.assertTrue(len(non_empty_lines) >= 1)
        self.assertIn("User", non_empty_lines[0])

    def test_single_user_stats(self) -> None:
        """Test with single user to ensure no sorting issues."""
        single_user_stats = {
            "single_user": {
                "reviews": 3,
                "comments": 6,
                "engagement_level": "Medium",
                "thoroughness_score": 50,
            },
        }

        result = generate_results_table(
            single_user_stats, ["reviews", "comments"],
        )

        lines = result.split("\n")
        data_lines = [
            line
            for line in lines
            if line and not line.startswith("-") and "User" not in line
        ]

        self.assertEqual(len(data_lines), 1)
        self.assertIn("single_user", data_lines[0])


if __name__ == "__main__":
    unittest.main()
