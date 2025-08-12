import unittest

from reviewtally.analysis.team_metrics import (
    calculate_sprint_team_metrics,
    calculate_team_time_metrics,
    classify_team_engagement,
)


class TestCalculateTeamTimeMetrics(unittest.TestCase):
    def test_calculate_team_time_metrics_empty_input(self) -> None:
        """Test with empty review times and PR created times."""
        result = calculate_team_time_metrics([], [])

        expected = {
            "avg_response_time_hours": 0.0,
            "avg_completion_time_hours": 0.0,
            "active_review_days": 0,
        }
        self.assertEqual(result, expected)

    def test_calculate_team_time_metrics_single_review(self) -> None:
        """Test with single review and PR."""
        pr_created = "2025-01-01T10:00:00Z"
        review_time = "2025-01-01T14:00:00Z"  # 4 hours later

        result = calculate_team_time_metrics([review_time], [pr_created])

        # Single review: response time 4 hours, completion time 0, 1 active day
        self.assertEqual(result["avg_response_time_hours"], 4.0)
        self.assertEqual(result["avg_completion_time_hours"], 0.0)
        self.assertEqual(result["active_review_days"], 1)

    def test_calculate_team_time_metrics_multiple_reviews_same_day(
        self,
    ) -> None:
        """Test with multiple reviews on the same day."""
        pr_created_times = [
            "2025-01-01T10:00:00Z",
            "2025-01-01T11:00:00Z",
        ]
        review_times = [
            "2025-01-01T14:00:00Z",  # 4 hours after first PR
            "2025-01-01T15:00:00Z",  # 4 hours after second PR
        ]

        result = calculate_team_time_metrics(review_times, pr_created_times)

        # Average response time: (4 + 4) / 2 = 4 hours
        # Completion time: 15:00 - 14:00 = 1 hour
        # Active days: 1 (same day)
        self.assertEqual(result["avg_response_time_hours"], 4.0)
        self.assertEqual(result["avg_completion_time_hours"], 1.0)
        self.assertEqual(result["active_review_days"], 1)

    def test_calculate_team_time_metrics_multiple_days(self) -> None:
        """Test with reviews spanning multiple days."""
        pr_created_times = [
            "2025-01-01T10:00:00Z",
            "2025-01-02T10:00:00Z",
            "2025-01-03T10:00:00Z",
        ]
        review_times = [
            "2025-01-01T12:00:00Z",  # 2 hours later
            "2025-01-02T16:00:00Z",  # 6 hours later
            "2025-01-04T14:00:00Z",  # 28 hours later
        ]

        result = calculate_team_time_metrics(review_times, pr_created_times)

        # Average response time: (2 + 6 + 28) / 3 = 12 hours
        # Completion time: Jan 4 14:00 - Jan 1 12:00 = 74 hours
        # Active days: 3 (Jan 1, Jan 2, Jan 4)
        self.assertEqual(result["avg_response_time_hours"], 12.0)
        self.assertEqual(result["avg_completion_time_hours"], 74.0)
        self.assertEqual(result["active_review_days"], 3)

    def test_calculate_team_time_metrics_review_before_pr_creation(
        self,
    ) -> None:
        """Test with review time before PR creation (filtered out)."""
        pr_created_times = [
            "2025-01-01T12:00:00Z",
        ]
        review_times = [
            "2025-01-01T10:00:00Z",  # 2 hours BEFORE PR creation
        ]

        result = calculate_team_time_metrics(review_times, pr_created_times)

        # Should filter out negative response times
        self.assertEqual(result["avg_response_time_hours"], 0.0)
        self.assertEqual(result["avg_completion_time_hours"], 0.0)
        # Still counts the day
        self.assertEqual(result["active_review_days"], 1)

    def test_calculate_team_time_metrics_mixed_valid_invalid(self) -> None:
        """Test with mix of valid and invalid response times."""
        pr_created_times = [
            "2025-01-01T10:00:00Z",
            "2025-01-01T12:00:00Z",
        ]
        review_times = [
            "2025-01-01T14:00:00Z",  # Valid: 4 hours after first PR
            "2025-01-01T11:00:00Z",  # Invalid: 1 hour before second PR
        ]

        result = calculate_team_time_metrics(review_times, pr_created_times)

        # Only valid response time (4 hours) should be counted
        self.assertEqual(result["avg_response_time_hours"], 4.0)
        # 14:00 - 11:00
        self.assertEqual(result["avg_completion_time_hours"], 3.0)
        self.assertEqual(result["active_review_days"], 1)

    def test_calculate_team_time_metrics_mismatched_lengths(self) -> None:
        """Test with mismatched lengths of review/PR created times."""
        pr_created_times = [
            "2025-01-01T10:00:00Z",
            "2025-01-01T11:00:00Z",
            "2025-01-01T12:00:00Z",
        ]
        review_times = [
            "2025-01-01T14:00:00Z",
            "2025-01-01T15:00:00Z",
        ]  # Only 2 review times for 3 PRs

        result = calculate_team_time_metrics(review_times, pr_created_times)

        # Should process pairs up to the shorter list length
        # (14:00 - 10:00) = 4 hours, (15:00 - 11:00) = 4 hours
        self.assertEqual(result["avg_response_time_hours"], 4.0)
        # 15:00 - 14:00
        self.assertEqual(result["avg_completion_time_hours"], 1.0)
        self.assertEqual(result["active_review_days"], 1)

    def test_calculate_team_time_metrics_timezone_handling(self) -> None:
        """Test that UTC timezone is handled correctly."""
        pr_created_times = ["2025-01-01T00:00:00Z"]
        review_times = ["2025-01-02T00:00:00Z"]  # Exactly 24 hours later

        result = calculate_team_time_metrics(review_times, pr_created_times)

        self.assertEqual(result["avg_response_time_hours"], 24.0)
        self.assertEqual(result["avg_completion_time_hours"], 0.0)
        self.assertEqual(result["active_review_days"], 1)


class TestClassifyTeamEngagement(unittest.TestCase):
    def test_classify_team_engagement_high(self) -> None:
        """Test high engagement classification."""
        # Test values >= HIGH_ENGAGEMENT_THRESHOLD (2.0)
        self.assertEqual(classify_team_engagement(2.0), "High")
        self.assertEqual(classify_team_engagement(2.5), "High")
        self.assertEqual(classify_team_engagement(10.0), "High")

    def test_classify_team_engagement_medium(self) -> None:
        """Test medium engagement classification."""
        # MEDIUM_ENGAGEMENT_THRESHOLD = 0.5, HIGH_ENGAGEMENT_THRESHOLD = 2.0
        self.assertEqual(classify_team_engagement(0.5), "Medium")
        self.assertEqual(classify_team_engagement(1.0), "Medium")
        self.assertEqual(classify_team_engagement(1.9), "Medium")

    def test_classify_team_engagement_low(self) -> None:
        """Test low engagement classification."""
        # Below MEDIUM_ENGAGEMENT_THRESHOLD = 0.5
        self.assertEqual(classify_team_engagement(0.0), "Low")
        self.assertEqual(classify_team_engagement(0.1), "Low")
        self.assertEqual(classify_team_engagement(0.49), "Low")

    def test_classify_team_engagement_boundary_values(self) -> None:
        """Test boundary values for engagement classification."""
        # Test exact boundary values
        self.assertEqual(classify_team_engagement(0.5), "Medium")
        self.assertEqual(classify_team_engagement(2.0), "High")

        # Test just below boundaries
        self.assertEqual(classify_team_engagement(0.4999), "Low")
        self.assertEqual(classify_team_engagement(1.9999), "Medium")


class TestCalculateSprintTeamMetrics(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test data for sprint team metrics tests."""
        self.sample_sprint_stats = {
            "2025-01-01": {
                "total_reviews": 10,
                "total_comments": 25,
                "unique_reviewers": {"alice", "bob", "charlie"},
                "review_times": [
                    "2025-01-01T10:00:00Z",
                    "2025-01-01T14:00:00Z",
                    "2025-01-02T12:00:00Z",
                ],
                "pr_created_times": [
                    "2025-01-01T08:00:00Z",
                    "2025-01-01T12:00:00Z",
                    "2025-01-02T10:00:00Z",
                ],
            },
            "2025-01-15": {
                "total_reviews": 5,
                "total_comments": 2,
                "unique_reviewers": {"alice", "bob"},
                "review_times": ["2025-01-15T10:00:00Z"],
                "pr_created_times": ["2025-01-15T09:00:00Z"],
            },
        }

    def test_calculate_sprint_team_metrics_basic(self) -> None:
        """Test basic sprint team metrics calculation."""
        result = calculate_sprint_team_metrics(self.sample_sprint_stats)

        # Should have metrics for both sprints
        self.assertEqual(len(result), 2)
        self.assertIn("2025-01-01", result)
        self.assertIn("2025-01-15", result)

        # Check first sprint metrics
        sprint1 = result["2025-01-01"]
        self.assertEqual(sprint1["sprint_period"], "2025-01-01")
        self.assertEqual(sprint1["total_reviews"], 10)
        self.assertEqual(sprint1["total_comments"], 25)
        self.assertEqual(sprint1["unique_reviewers"], 3)  # Converted from set
        self.assertEqual(sprint1["avg_comments_per_review"], 2.5)  # 25/10
        self.assertEqual(
            sprint1["reviews_per_reviewer"],
            10 / 3,
        )  # 10/3 ≈ 3.33
        self.assertEqual(sprint1["team_engagement"], "High")  # 2.5 >= 2.0

        # Check second sprint metrics
        sprint2 = result["2025-01-15"]
        self.assertEqual(sprint2["sprint_period"], "2025-01-15")
        self.assertEqual(sprint2["total_reviews"], 5)
        self.assertEqual(sprint2["total_comments"], 2)
        self.assertEqual(sprint2["unique_reviewers"], 2)
        self.assertEqual(sprint2["avg_comments_per_review"], 0.4)  # 2/5
        self.assertEqual(sprint2["reviews_per_reviewer"], 2.5)  # 5/2
        self.assertEqual(sprint2["team_engagement"], "Low")  # 0.4 < 0.5

    def test_calculate_sprint_team_metrics_zero_reviews(self) -> None:
        """Test sprint with zero reviews."""
        sprint_stats = {
            "2025-01-01": {
                "total_reviews": 0,
                "total_comments": 0,
                "unique_reviewers": set(),
                "review_times": [],
                "pr_created_times": [],
            },
        }

        result = calculate_sprint_team_metrics(sprint_stats)

        sprint = result["2025-01-01"]
        self.assertEqual(sprint["total_reviews"], 0)
        self.assertEqual(sprint["total_comments"], 0)
        self.assertEqual(sprint["unique_reviewers"], 0)
        self.assertEqual(sprint["avg_comments_per_review"], 0)
        self.assertEqual(sprint["reviews_per_reviewer"], 0)
        self.assertEqual(sprint["team_engagement"], "Low")

    def test_calculate_sprint_team_metrics_zero_unique_reviewers(self) -> None:
        """Test sprint with reviews but zero unique reviewers."""
        sprint_stats = {
            "2025-01-01": {
                "total_reviews": 5,
                "total_comments": 10,
                "unique_reviewers": set(),  # Empty set
                "review_times": ["2025-01-01T10:00:00Z"],
                "pr_created_times": ["2025-01-01T09:00:00Z"],
            },
        }

        result = calculate_sprint_team_metrics(sprint_stats)

        sprint = result["2025-01-01"]
        # Division by zero case
        self.assertEqual(sprint["reviews_per_reviewer"], 0)

    def test_calculate_sprint_team_metrics_engagement_levels(self) -> None:
        """Test different engagement level classifications."""
        sprint_stats = {
            "high_engagement": {
                "total_reviews": 10,
                "total_comments": 30,  # 3.0 avg comments per review
                "unique_reviewers": {"alice", "bob"},
                "review_times": ["2025-01-01T10:00:00Z"],
                "pr_created_times": ["2025-01-01T09:00:00Z"],
            },
            "medium_engagement": {
                "total_reviews": 10,
                "total_comments": 10,  # 1.0 avg comments per review
                "unique_reviewers": {"alice", "bob"},
                "review_times": ["2025-01-01T10:00:00Z"],
                "pr_created_times": ["2025-01-01T09:00:00Z"],
            },
            "low_engagement": {
                "total_reviews": 10,
                "total_comments": 2,  # 0.2 avg comments per review
                "unique_reviewers": {"alice", "bob"},
                "review_times": ["2025-01-01T10:00:00Z"],
                "pr_created_times": ["2025-01-01T09:00:00Z"],
            },
        }

        result = calculate_sprint_team_metrics(sprint_stats)

        self.assertEqual(result["high_engagement"]["team_engagement"], "High")
        self.assertEqual(
            result["medium_engagement"]["team_engagement"],
            "Medium",
        )
        self.assertEqual(result["low_engagement"]["team_engagement"], "Low")

    def test_calculate_sprint_team_metrics_includes_time_metrics(self) -> None:
        """Test that sprint metrics include time-based metrics."""
        result = calculate_sprint_team_metrics(self.sample_sprint_stats)

        sprint1 = result["2025-01-01"]

        # Should include time metrics keys
        self.assertIn("avg_response_time_hours", sprint1)
        self.assertIn("avg_completion_time_hours", sprint1)
        self.assertIn("active_review_days", sprint1)

        # Verify time metrics are calculated
        # Response times: (2, 2, 2) hours -> avg 2.0
        self.assertEqual(sprint1["avg_response_time_hours"], 2.0)
        # Completion time: Jan 2 12:00 - Jan 1 10:00 = 26 hours
        self.assertEqual(sprint1["avg_completion_time_hours"], 26.0)
        # Active days: Jan 1, Jan 2 = 2 days
        self.assertEqual(sprint1["active_review_days"], 2)

    def test_calculate_sprint_team_metrics_empty_input(self) -> None:
        """Test with empty sprint stats."""
        result = calculate_sprint_team_metrics({})

        self.assertEqual(result, {})

    def test_calculate_sprint_team_metrics_precision(self) -> None:
        """Test calculation precision for ratios."""
        sprint_stats = {
            "2025-01-01": {
                "total_reviews": 3,
                "total_comments": 7,
                "unique_reviewers": {"alice", "bob"},
                "review_times": ["2025-01-01T10:00:00Z"],
                "pr_created_times": ["2025-01-01T09:00:00Z"],
            },
        }

        result = calculate_sprint_team_metrics(sprint_stats)
        sprint = result["2025-01-01"]

        # 7/3 = 2.333...
        self.assertAlmostEqual(
            sprint["avg_comments_per_review"],
            7 / 3,
            places=10,
        )
        # 3/2 = 1.5
        self.assertEqual(sprint["reviews_per_reviewer"], 1.5)


if __name__ == "__main__":
    unittest.main()
