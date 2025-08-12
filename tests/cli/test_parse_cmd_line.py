import unittest
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

from reviewtally.cli.parse_cmd_line import parse_cmd_line
from reviewtally.exceptions.local_exceptions import MalformedDateError


class TestParseCmdLineMalformedDates(unittest.TestCase):
    """Test malformed date handling in parse_cmd_line function."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Mock successful version metadata to avoid import issues
        self.version_patcher = patch(
            "reviewtally.cli.parse_cmd_line.importlib.metadata.version",
        )
        self.mock_version = self.version_patcher.start()
        self.mock_version.return_value = "0.2.6"

    def tearDown(self) -> None:
        """Clean up after tests."""
        self.version_patcher.stop()

    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv")
    def test_malformed_start_date_exits(
        self,
        mock_argv: Any,
        mock_print: Any,
        mock_exit: Any,
    ) -> None:
        """Test that malformed start date triggers sys.exit(1)."""
        # Arrange
        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "-o",
            "test-org",
            "-s",
            "invalid-date",
            "-e",
            "2023-12-31",
        ][x]
        mock_argv.__len__.return_value = 7
        # Make sys.exit actually raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit

        # Act & Assert
        with self.assertRaises(SystemExit):
            parse_cmd_line()

        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once()
        printed_error = str(mock_print.call_args[0][0])
        self.assertIn("Malformed date: invalid-date", printed_error)
        self.assertIn("Please use the format YYYY-MM-DD", printed_error)

    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv")
    def test_malformed_end_date_exits(
        self,
        mock_argv: Any,
        mock_print: Any,
        mock_exit: Any,
    ) -> None:
        """Test that malformed end date triggers sys.exit(1)."""
        # Arrange
        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "-o",
            "test-org",
            "-s",
            "2023-01-01",
            "-e",
            "not-a-date",
        ][x]
        mock_argv.__len__.return_value = 7
        # Make sys.exit actually raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit

        # Act & Assert
        with self.assertRaises(SystemExit):
            parse_cmd_line()

        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once()
        printed_error = str(mock_print.call_args[0][0])
        self.assertIn("Malformed date: not-a-date", printed_error)
        self.assertIn("Please use the format YYYY-MM-DD", printed_error)

    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv")
    def test_invalid_month_date_exits(
        self,
        mock_argv: Any,
        mock_print: Any,
        mock_exit: Any,
    ) -> None:
        """Test that invalid month in date triggers sys.exit(1)."""
        # Arrange
        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "-o",
            "test-org",
            "-s",
            "2023-13-01",  # Invalid month
            "-e",
            "2023-12-31",
        ][x]
        mock_argv.__len__.return_value = 7
        # Make sys.exit actually raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit

        # Act & Assert
        with self.assertRaises(SystemExit):
            parse_cmd_line()

        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once()
        printed_error = str(mock_print.call_args[0][0])
        self.assertIn("Malformed date: 2023-13-01", printed_error)

    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv")
    def test_invalid_day_date_exits(
        self,
        mock_argv: Any,
        mock_print: Any,
        mock_exit: Any,
    ) -> None:
        """Test that invalid day in date triggers sys.exit(1)."""
        # Arrange
        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "-o",
            "test-org",
            "-s",
            "2023-01-01",
            "-e",
            "2023-02-30",  # Invalid day for February
        ][x]
        mock_argv.__len__.return_value = 7
        # Make sys.exit actually raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit

        # Act & Assert
        with self.assertRaises(SystemExit):
            parse_cmd_line()

        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once()
        printed_error = str(mock_print.call_args[0][0])
        self.assertIn("Malformed date: 2023-02-30", printed_error)

    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv")
    def test_wrong_date_format_exits(
        self,
        mock_argv: Any,
        mock_print: Any,
        mock_exit: Any,
    ) -> None:
        """Test that wrong date format triggers sys.exit(1)."""
        # Arrange
        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "-o",
            "test-org",
            "-s",
            "01/01/2023",  # Wrong format (MM/DD/YYYY instead of YYYY-MM-DD)
            "-e",
            "2023-12-31",
        ][x]
        mock_argv.__len__.return_value = 7
        # Make sys.exit actually raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit

        # Act & Assert
        with self.assertRaises(SystemExit):
            parse_cmd_line()

        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once()
        printed_error = str(mock_print.call_args[0][0])
        self.assertIn("Malformed date: 01/01/2023", printed_error)

    @patch("sys.exit")
    @patch("sys.argv")
    def test_valid_dates_no_exit(self, mock_argv: Any, mock_exit: Any) -> None:
        """Test that valid dates don't trigger sys.exit."""
        # Arrange
        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "-o",
            "test-org",
            "-s",
            "2023-01-01",
            "-e",
            "2023-01-15",
        ][x]
        mock_argv.__len__.return_value = 7

        # Act
        result = parse_cmd_line()

        # Assert
        mock_exit.assert_not_called()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 7)

        # Verify the parsed dates
        (
            org_name,
            start_date,
            end_date,
            languages,
            metrics,
            sprint_analysis,
            output_path,
        ) = result
        self.assertEqual(org_name, "test-org")
        self.assertEqual(start_date, datetime(2023, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(end_date, datetime(2023, 1, 15, tzinfo=timezone.utc))

    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv")
    def test_both_dates_malformed_start_fails_first(
        self,
        mock_argv: Any,
        mock_print: Any,
        mock_exit: Any,
    ) -> None:
        """Test when both dates are malformed, start date fails first."""
        # Arrange - both dates malformed but start date should be checked first
        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "-o",
            "test-org",
            "-s",
            "bad-start-date",
            "-e",
            "bad-end-date",
        ][x]
        mock_argv.__len__.return_value = 7
        # Make sys.exit actually raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit

        # Act & Assert
        with self.assertRaises(SystemExit):
            parse_cmd_line()

        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once()
        printed_error = str(mock_print.call_args[0][0])
        # Should fail on start date first
        self.assertIn("Malformed date: bad-start-date", printed_error)

    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv")
    def test_malformed_date_error_message_format(
        self,
        mock_argv: Any,
        mock_print: Any,
        mock_exit: Any,
    ) -> None:
        """Test MalformedDateError produces correctly formatted message."""
        # Arrange
        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "-o",
            "test-org",
            "-s",
            "test-bad-date",
            "-e",
            "2023-12-31",
        ][x]
        mock_argv.__len__.return_value = 7
        # Make sys.exit actually raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit

        # Act & Assert
        with self.assertRaises(SystemExit):
            parse_cmd_line()

        mock_print.assert_called_once()
        printed_error = str(mock_print.call_args[0][0])

        # Verify the error matches MalformedDateError format
        expected_error = MalformedDateError("test-bad-date")
        self.assertEqual(printed_error, str(expected_error))
        self.assertIn("Malformed date: test-bad-date", printed_error)
        self.assertIn("Please use the format YYYY-MM-DD", printed_error)


if __name__ == "__main__":
    unittest.main()
