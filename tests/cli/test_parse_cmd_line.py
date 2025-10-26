import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
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
        self.assertIsInstance(result, dict)
        # Check it's the right type (added repositories config key)
        self.assertEqual(len(result), 18)

        # Verify the parsed dates
        self.assertEqual(result["org_name"], "test-org")
        self.assertIsNone(result["repositories"])
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


class TestParseCmdLineConfig(unittest.TestCase):
    """Tests for TOML configuration loading."""

    def _create_config_file(self, contents: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".toml")
        path_obj = Path(path)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(contents)

        def cleanup() -> None:
            if path_obj.exists():
                path_obj.unlink()

        self.addCleanup(cleanup)
        return str(path_obj)

    @patch("sys.exit")
    @patch("sys.argv")
    def test_config_without_org_uses_repositories(
        self,
        mock_argv: Any,
        mock_exit: Any,
    ) -> None:
        """Configuration file can define repositories without CLI org."""
        config_path = self._create_config_file(
            """
repositories = ["octocat/hello-world", "octocat/test-repo"]
start_date = "2023-01-01"
end_date = "2023-01-15"
metrics = ["reviews", "comments"]
""",
        )

        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "--config",
            config_path,
        ][x]
        mock_argv.__len__.return_value = 3

        result = parse_cmd_line()

        mock_exit.assert_not_called()
        self.assertIsNone(result["org_name"])
        self.assertEqual(
            result["repositories"],
            ["octocat/hello-world", "octocat/test-repo"],
        )
        self.assertEqual(
            result["start_date"],
            datetime(2023, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(
            result["metrics"],
            ["reviews", "comments"],
        )

    @patch("sys.exit")
    @patch("sys.argv")
    def test_config_supports_toml_dates(
        self,
        mock_argv: Any,
        mock_exit: Any,
    ) -> None:
        """Configuration can use TOML local-date values."""
        config_path = self._create_config_file(
            """
repositories = ["octocat/hello-world"]
start_date = 2024-01-01
end_date = 2024-01-31
""",
        )

        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "--config",
            config_path,
        ][x]
        mock_argv.__len__.return_value = 3

        result = parse_cmd_line()

        mock_exit.assert_not_called()
        self.assertEqual(
            result["start_date"],
            datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(
            result["end_date"],
            datetime(2024, 1, 31, tzinfo=timezone.utc),
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
        """Invalid repository entries produce a clear error message."""
        config_path = self._create_config_file(
            """
repositories = ["invalidrepo"]
""",
        )

        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "--config",
            config_path,
        ][x]
        mock_argv.__len__.return_value = 3
        mock_exit.side_effect = SystemExit

        with self.assertRaises(SystemExit):
            parse_cmd_line()

        mock_print.assert_called_once()
        error_message = str(mock_print.call_args[0][0])
        self.assertIn("owner/repository", error_message)

    @patch("sys.exit")
    @patch("sys.argv")
    def test_plot_sprint_flag_does_not_conflict(
        self,
        mock_argv: Any,
        mock_exit: Any,
    ) -> None:
        """Sprint plotting flag should not trigger spurious conflicts."""
        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "-o",
            "test-org",
            "--plot-sprint",
        ][x]
        mock_argv.__len__.return_value = 4

        result = parse_cmd_line()

        mock_exit.assert_not_called()
        self.assertTrue(result["plot_sprint"])
        self.assertFalse(result["plot_individual"])

    @patch("sys.exit")
    @patch("sys.argv")
    def test_plot_individual_flag_does_not_conflict(
        self,
        mock_argv: Any,
        mock_exit: Any,
    ) -> None:
        """Individual plotting flag should not trigger spurious conflicts."""
        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "-o",
            "test-org",
            "--plot-individual",
        ][x]
        mock_argv.__len__.return_value = 4

        result = parse_cmd_line()

        mock_exit.assert_not_called()
        self.assertTrue(result["plot_individual"])
        self.assertFalse(result["plot_sprint"])

    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv")
    def test_config_cannot_enable_both_plot_modes(
        self,
        mock_argv: Any,
        mock_print: Any,
        mock_exit: Any,
    ) -> None:
        """Configuration enabling both plot modes should exit with error."""
        config_path = self._create_config_file(
            """
plot_sprint = true
plot_individual = true
repositories = ["octocat/hello-world"]
start_date = "2023-01-01"
end_date = "2023-01-02"
""",
        )

        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "--config",
            config_path,
        ][x]
        mock_argv.__len__.return_value = 3
        mock_exit.side_effect = SystemExit

        with self.assertRaises(SystemExit):
            parse_cmd_line()

        mock_exit.assert_called_once_with(1)
        mock_print.assert_called_once()
        error_message = str(mock_print.call_args[0][0])
        self.assertIn("mutually exclusive", error_message)

    @patch("sys.exit")
    @patch("sys.argv")
    def test_config_allows_language_key(
        self,
        mock_argv: Any,
        mock_exit: Any,
    ) -> None:
        """Configuration may use singular language key for compatibility."""
        config_path = self._create_config_file(
            """
repositories = ["octocat/hello-world"]
language = "python"
start_date = "2023-01-01"
end_date = "2023-01-02"
""",
        )

        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "--config",
            config_path,
        ][x]
        mock_argv.__len__.return_value = 3

        result = parse_cmd_line()

        mock_exit.assert_not_called()
        self.assertEqual(result["languages"], ["python"])

    @patch("sys.exit")
    @patch("sys.argv")
    def test_cli_can_disable_cache_even_if_config_enables_it(
        self,
        mock_argv: Any,
        mock_exit: Any,
    ) -> None:
        """The --no-cache flag should override a configuration value."""
        config_path = self._create_config_file(
            """
use_cache = true
repositories = ["octocat/hello-world"]
start_date = "2023-01-01"
end_date = "2023-01-02"
""",
        )

        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "--config",
            config_path,
            "--no-cache",
        ][x]
        mock_argv.__len__.return_value = 4

        result = parse_cmd_line()

        mock_exit.assert_not_called()
        self.assertFalse(result["use_cache"])

    @patch("sys.exit")
    @patch("sys.argv")
    def test_cli_can_reset_metrics_to_default_values(
        self,
        mock_argv: Any,
        mock_exit: Any,
    ) -> None:
        """Explicit CLI metrics should override config even if default."""
        config_path = self._create_config_file(
            """
metrics = ["reviews"]
repositories = ["octocat/hello-world"]
start_date = "2023-01-01"
end_date = "2023-01-02"
""",
        )

        default_metrics = "reviews,comments,avg-comments"
        argv_values = [
            "review-tally",
            "--config",
            config_path,
            "--metrics",
            default_metrics,
        ]

        mock_argv.__getitem__.side_effect = lambda index: argv_values[index]
        mock_argv.__len__.return_value = len(argv_values)

        result = parse_cmd_line()

        mock_exit.assert_not_called()
        self.assertEqual(
            result["metrics"],
            default_metrics.split(","),
        )

    @patch("sys.exit")
    @patch("sys.argv")
    def test_cli_chart_type_override_applies_even_with_default_value(
        self,
        mock_argv: Any,
        mock_exit: Any,
    ) -> None:
        """Providing chart-type on CLI should replace config value."""
        config_path = self._create_config_file(
            """
chart_type = "line"
repositories = ["octocat/hello-world"]
start_date = "2023-01-01"
end_date = "2023-01-02"
""",
        )

        argv_values = [
            "review-tally",
            "--config",
            config_path,
            "--chart-type",
            "bar",
        ]

        mock_argv.__getitem__.side_effect = lambda index: argv_values[index]
        mock_argv.__len__.return_value = len(argv_values)

        result = parse_cmd_line()

        mock_exit.assert_not_called()
        self.assertEqual(result["chart_type"], "bar")

    @patch("sys.exit")
    @patch("sys.argv")
    def test_config_path_expands_user_home(
        self,
        mock_argv: Any,
        mock_exit: Any,
    ) -> None:
        """The --config flag should expand '~' to the user home directory."""
        home_dir = Path.home()
        config_dir = home_dir / ".review_tally_tests"
        config_dir.mkdir(exist_ok=True)

        def cleanup_dir() -> None:
            if config_dir.exists():
                config_dir.rmdir()

        self.addCleanup(cleanup_dir)

        config_path = config_dir / "config.toml"
        config_path.write_text(
            """
repositories = ["octocat/hello-world"]
start_date = "2023-01-01"
end_date = "2023-01-02"
""",
            encoding="utf-8",
        )

        def cleanup_file() -> None:
            if config_path.exists():
                config_path.unlink()

        self.addCleanup(cleanup_file)

        tilde_path = f"~/{config_path.relative_to(home_dir).as_posix()}"

        mock_argv.__getitem__.side_effect = lambda x: [
            "review-tally",
            "--config",
            tilde_path,
        ][x]
        mock_argv.__len__.return_value = 3

        result = parse_cmd_line()

        mock_exit.assert_not_called()
        self.assertEqual(result["repositories"], ["octocat/hello-world"])


if __name__ == "__main__":
    unittest.main()
