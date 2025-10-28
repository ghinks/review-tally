import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from typing import Any
from unittest.mock import patch

from reviewtally.cli.parse_cmd_line import parse_cmd_line
from reviewtally.exceptions.local_exceptions import MalformedDateError


class ParseCmdLineTestCase(unittest.TestCase):
    """Base class that patches shared dependencies."""

    def setUp(self) -> None:
        """Set up common patches."""
        self.version_patcher = patch(
            "reviewtally.cli.parse_cmd_line.importlib.metadata.version",
        )
        self.mock_version = self.version_patcher.start()
        self.mock_version.return_value = "0.2.6"

    def tearDown(self) -> None:
        """Stop common patches."""
        self.version_patcher.stop()


class TestParseCmdLineMalformedDates(ParseCmdLineTestCase):
    """Test malformed date handling in parse_cmd_line function."""

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
        self.assertIsInstance(result, dict)
        # Check result includes the expected CommandLineArgs keys
        self.assertEqual(len(result), 18)

        # Verify the parsed dates
        self.assertEqual(result["org_name"], "test-org")
        self.assertEqual(
            result["start_date"],
            datetime(2023, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(
            result["end_date"],
            datetime(2023, 1, 15, tzinfo=timezone.utc),
        )
        # Defaults for new args
        self.assertFalse(result["plot_sprint"])
        self.assertEqual(result["chart_type"], "bar")
        self.assertEqual(
            result["chart_metrics"],
            ["total_reviews", "total_comments"],
        )
        self.assertIsNone(result["save_plot"])
        self.assertEqual(result["repositories"], [])

    @patch("sys.exit")
    @patch("sys.argv")
    def test_long_form_date_flags(
        self,
        mock_argv: Any,
        mock_exit: Any,
    ) -> None:
        """Ensure hyphenated long-form date flags parse correctly."""
        # Arrange
        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "--org",
            "test-org",
            "--start-date",
            "2023-02-01",
            "--end-date",
            "2023-02-15",
        ][x]
        mock_argv.__len__.return_value = 7

        # Act
        result = parse_cmd_line()

        # Assert
        mock_exit.assert_not_called()
        self.assertEqual(result["org_name"], "test-org")
        self.assertEqual(
            result["start_date"],
            datetime(2023, 2, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(
            result["end_date"],
            datetime(2023, 2, 15, tzinfo=timezone.utc),
        )

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


class TestParseCmdLineLanguageArgument(ParseCmdLineTestCase):
    """Tests related to the --languages CLI option."""

    @patch("sys.exit")
    @patch("sys.argv")
    def test_language_argument_trims_and_filters(
        self,
        mock_argv: Any,
        mock_exit: Any,
    ) -> None:
        """Languages argument strips whitespace and ignores empties."""
        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "-o",
            "test-org",
            "-l",
            " python, javascript , ,TypeScript  ",
            "-s",
            "2023-01-01",
            "-e",
            "2023-01-31",
        ][x]
        mock_argv.__len__.return_value = 9

        result = parse_cmd_line()

        mock_exit.assert_not_called()
        self.assertEqual(
            result["languages"],
            ["python", "javascript", "typescript"],
        )


class TestParseCmdLineValidation(ParseCmdLineTestCase):
    """Additional validation scenarios for parse_cmd_line."""

    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv")
    def test_missing_org_or_repositories_exits(
        self,
        mock_argv: Any,
        mock_print: Any,
        mock_exit: Any,
    ) -> None:
        """Ensure we require an org or repositories configuration."""
        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "-s",
            "2023-01-01",
            "-e",
            "2023-01-02",
        ][x]
        mock_argv.__len__.return_value = 5
        mock_exit.side_effect = SystemExit

        with self.assertRaises(SystemExit):
            parse_cmd_line()

        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once()
        self.assertIn(
            "Provide an organization (--org) or configure repositories.",
            str(mock_print.call_args[0][0]),
        )


class TestParseCmdLineConfiguration(ParseCmdLineTestCase):
    """Tests for TOML configuration support."""

    @patch("sys.exit")
    @patch("sys.argv")
    def test_config_file_parses_options(
        self,
        mock_argv: Any,
        mock_exit: Any,
    ) -> None:
        """Configuration file should populate command values."""
        config_contents = dedent(
            """
            start-date = 2023-01-01
            end-date = 2023-01-15
            languages = ["Python", " TypeScript "]
            metrics = ["reviews", "comments"]
            sprint-analysis = true
            output-path = "sprint.csv"
            plot-sprint = true
            chart-type = "line"
            chart-metrics = ["total_reviews"]
            save-plot = "plot.html"
            no-cache = true
            clear-cache = true
            clear-expired-cache = true
            cache-stats = true
            repositories = ["octocat/hello-world", "cli/review-tally"]
            """,
        )

        with tempfile.NamedTemporaryFile(
            "w",
            suffix=".toml",
            delete=False,
        ) as tmp:
            tmp.write(config_contents)
            tmp_path = Path(tmp.name)

        try:
            mock_argv.__getitem__.side_effect = lambda x: [
                "review-tally",
                "--config",
                str(tmp_path),
            ][x]
            mock_argv.__len__.return_value = 3

            result = parse_cmd_line()
        finally:
            tmp_path.unlink(missing_ok=True)

        mock_exit.assert_not_called()
        self.assertIsNone(result["org_name"])
        self.assertEqual(
            result["start_date"],
            datetime(2023, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(
            result["end_date"],
            datetime(2023, 1, 15, tzinfo=timezone.utc),
        )
        self.assertEqual(result["languages"], ["python", "typescript"])
        self.assertEqual(result["metrics"], ["reviews", "comments"])
        self.assertTrue(result["sprint_analysis"])
        self.assertEqual(result["output_path"], "sprint.csv")
        self.assertTrue(result["plot_sprint"])
        self.assertEqual(result["chart_type"], "line")
        self.assertEqual(result["chart_metrics"], ["total_reviews"])
        self.assertEqual(result["save_plot"], "plot.html")
        self.assertFalse(result["plot_individual"])
        self.assertEqual(result["individual_chart_metric"], "reviews")
        self.assertFalse(result["use_cache"])
        self.assertTrue(result["clear_cache"])
        self.assertTrue(result["clear_expired_cache"])
        self.assertTrue(result["show_cache_stats"])
        self.assertEqual(
            result["repositories"],
            ["octocat/hello-world", "cli/review-tally"],
        )

    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv")
    def test_invalid_repository_format_exits(
        self,
        mock_argv: Any,
        mock_print: Any,
        mock_exit: Any,
    ) -> None:
        """Invalid repository definitions should raise an error."""
        with tempfile.NamedTemporaryFile(
            "w",
            suffix=".toml",
            delete=False,
        ) as tmp:
            tmp.write('repositories = ["invalid"]\n')
            tmp_path = Path(tmp.name)

        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "--config",
            str(tmp_path),
        ][x]
        mock_argv.__len__.return_value = 3
        mock_exit.side_effect = SystemExit

        try:
            with self.assertRaises(SystemExit):
                parse_cmd_line()
        finally:
            tmp_path.unlink(missing_ok=True)

        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once()
        self.assertIn(
            "Invalid repository entry",
            str(mock_print.call_args[0][0]),
        )
if __name__ == "__main__":
    unittest.main()
