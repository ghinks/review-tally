import unittest
from datetime import datetime, timezone

from reviewtally.analysis.sprint_periods import (
    calculate_sprint_periods,
    get_sprint_for_date,
)


class TestCalculateSprintPeriods(unittest.TestCase):
    def setUp(self) -> None:
        # Test dates in UTC timezone
        self.start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2025, 2, 1, tzinfo=timezone.utc)  # 31 days

    def test_calculate_sprint_periods_basic(self) -> None:
        """Test basic sprint period calculation with 31-day range."""
        periods = calculate_sprint_periods(self.start_date, self.end_date)

        # Should create 3 periods: 14 days + 14 days + 3 days
        self.assertEqual(len(periods), 3)

        # Check first period
        start1, end1, label1 = periods[0]
        self.assertEqual(start1, self.start_date)
        self.assertEqual(end1, datetime(2025, 1, 15, tzinfo=timezone.utc))
        self.assertEqual(label1, "2025-01-01")

        # Check second period
        start2, end2, label2 = periods[1]
        self.assertEqual(start2, datetime(2025, 1, 15, tzinfo=timezone.utc))
        self.assertEqual(end2, datetime(2025, 1, 29, tzinfo=timezone.utc))
        self.assertEqual(label2, "2025-01-15")

        # Check third period (partial)
        start3, end3, label3 = periods[2]
        self.assertEqual(start3, datetime(2025, 1, 29, tzinfo=timezone.utc))
        self.assertEqual(end3, self.end_date)
        self.assertEqual(label3, "2025-01-29")

    def test_calculate_sprint_periods_exact_14_days(self) -> None:
        """Test sprint calculation with exactly 14 days."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 15, tzinfo=timezone.utc)  # Exactly 14 days

        periods = calculate_sprint_periods(start, end)

        # Should create exactly 1 period
        self.assertEqual(len(periods), 1)
        start_period, end_period, label = periods[0]
        self.assertEqual(start_period, start)
        self.assertEqual(end_period, end)
        self.assertEqual(label, "2025-01-01")

    def test_calculate_sprint_periods_less_than_14_days(self) -> None:
        """Test sprint calculation with less than 14 days."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 5, tzinfo=timezone.utc)  # 4 days

        periods = calculate_sprint_periods(start, end)

        # Should create 1 partial period
        self.assertEqual(len(periods), 1)
        start_period, end_period, label = periods[0]
        self.assertEqual(start_period, start)
        self.assertEqual(end_period, end)
        self.assertEqual(label, "2025-01-01")

    def test_calculate_sprint_periods_empty_range(self) -> None:
        """Test sprint calculation with start date >= end date."""
        start = datetime(2025, 1, 15, tzinfo=timezone.utc)
        end = datetime(2025, 1, 15, tzinfo=timezone.utc)  # Same date

        periods = calculate_sprint_periods(start, end)

        # Should return empty list
        self.assertEqual(len(periods), 0)

    def test_calculate_sprint_periods_start_after_end(self) -> None:
        """Test sprint calculation with start date after end date."""
        start = datetime(2025, 1, 15, tzinfo=timezone.utc)
        end = datetime(2025, 1, 10, tzinfo=timezone.utc)  # Start after end

        periods = calculate_sprint_periods(start, end)

        # Should return empty list
        self.assertEqual(len(periods), 0)

    def test_calculate_sprint_periods_multiple_months(self) -> None:
        """Test sprint calculation spanning multiple months."""
        start = datetime(2024, 12, 20, tzinfo=timezone.utc)
        end = datetime(2025, 1, 20, tzinfo=timezone.utc)  # 31 days

        periods = calculate_sprint_periods(start, end)

        # Should create 3 periods
        self.assertEqual(len(periods), 3)

        # Check labels include year-month transitions
        labels = [period[2] for period in periods]
        self.assertEqual(labels[0], "2024-12-20")
        self.assertEqual(labels[1], "2025-01-03")
        self.assertEqual(labels[2], "2025-01-17")


class TestGetSprintForDate(unittest.TestCase):
    def setUp(self) -> None:
        # Create test sprint periods with non-overlapping boundaries
        self.sprint_periods = [
            (
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                datetime(2025, 1, 14, 23, 59, 59, tzinfo=timezone.utc),
                "Sprint-1",
            ),
            (
                datetime(2025, 1, 15, tzinfo=timezone.utc),
                datetime(2025, 1, 28, 23, 59, 59, tzinfo=timezone.utc),
                "Sprint-2",
            ),
            (
                datetime(2025, 1, 29, tzinfo=timezone.utc),
                datetime(2025, 2, 12, tzinfo=timezone.utc),
                "Sprint-3",
            ),
        ]

    def test_get_sprint_for_date_first_sprint(self) -> None:
        """Test date falls in first sprint period."""
        test_date = datetime(2025, 1, 5, tzinfo=timezone.utc)
        sprint = get_sprint_for_date(test_date, self.sprint_periods)
        self.assertEqual(sprint, "Sprint-1")

    def test_get_sprint_for_date_middle_sprint(self) -> None:
        """Test date falls in middle sprint period."""
        test_date = datetime(2025, 1, 20, tzinfo=timezone.utc)
        sprint = get_sprint_for_date(test_date, self.sprint_periods)
        self.assertEqual(sprint, "Sprint-2")

    def test_get_sprint_for_date_last_sprint(self) -> None:
        """Test date falls in last sprint period."""
        test_date = datetime(2025, 2, 5, tzinfo=timezone.utc)
        sprint = get_sprint_for_date(test_date, self.sprint_periods)
        self.assertEqual(sprint, "Sprint-3")

    def test_get_sprint_for_date_boundary_start(self) -> None:
        """Test date exactly at sprint period start boundary."""
        # Start of Sprint-2
        test_date = datetime(2025, 1, 15, tzinfo=timezone.utc)
        sprint = get_sprint_for_date(test_date, self.sprint_periods)
        self.assertEqual(sprint, "Sprint-2")

    def test_get_sprint_for_date_boundary_end(self) -> None:
        """Test date exactly at sprint period end boundary."""
        # End of Sprint-2
        test_date = datetime(2025, 1, 28, 23, 59, 59, tzinfo=timezone.utc)
        sprint = get_sprint_for_date(test_date, self.sprint_periods)
        self.assertEqual(sprint, "Sprint-2")

    def test_get_sprint_for_date_boundary_transition(self) -> None:
        """Test date exactly at transition between sprint periods."""
        # Test start of Sprint-3
        test_date = datetime(2025, 1, 29, tzinfo=timezone.utc)
        sprint = get_sprint_for_date(test_date, self.sprint_periods)
        self.assertEqual(sprint, "Sprint-3")

    def test_get_sprint_for_date_before_all_periods(self) -> None:
        """Test date before any sprint period."""
        test_date = datetime(2024, 12, 25, tzinfo=timezone.utc)
        sprint = get_sprint_for_date(test_date, self.sprint_periods)
        self.assertEqual(sprint, "Unknown")

    def test_get_sprint_for_date_after_all_periods(self) -> None:
        """Test date after all sprint periods."""
        test_date = datetime(2025, 3, 1, tzinfo=timezone.utc)
        sprint = get_sprint_for_date(test_date, self.sprint_periods)
        self.assertEqual(sprint, "Unknown")

    def test_get_sprint_for_date_empty_periods(self) -> None:
        """Test with empty sprint periods list."""
        test_date = datetime(2025, 1, 15, tzinfo=timezone.utc)
        sprint = get_sprint_for_date(test_date, [])
        self.assertEqual(sprint, "Unknown")

    def test_get_sprint_for_date_microseconds(self) -> None:
        """Test date matching works with microseconds."""
        # Date with microseconds within a sprint period
        test_date = datetime(
            2025, 1, 10, 14, 30, 45, 123456, tzinfo=timezone.utc,
        )
        sprint = get_sprint_for_date(test_date, self.sprint_periods)
        self.assertEqual(sprint, "Sprint-1")

    def test_get_sprint_for_date_different_timezones(self) -> None:
        """Test that timezone differences don't affect matching (both UTC)."""
        test_date = datetime(2025, 1, 10, tzinfo=timezone.utc)
        sprint = get_sprint_for_date(test_date, self.sprint_periods)
        self.assertEqual(sprint, "Sprint-1")


if __name__ == "__main__":
    unittest.main()
