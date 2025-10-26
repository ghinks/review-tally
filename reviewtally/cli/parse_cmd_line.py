# import argparse and create a function to parse command line arguments
# and return the parsed arguments, which will be used by the main function
# to get the start and end dates for the pull requests and the organization
# name
from __future__ import annotations

import argparse
import importlib.metadata
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypedDict

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib  # type: ignore[import-not-found]

from reviewtally.exceptions.local_exceptions import MalformedDateError


class CommandLineArgs(TypedDict):
    """Type definition for cli arguments returned by parse_cmd_line."""

    org_name: str | None
    repositories: list[str] | None
    start_date: datetime
    end_date: datetime
    languages: list[str]
    metrics: list[str]
    sprint_analysis: bool
    output_path: str | None
    plot_sprint: bool
    chart_type: str
    chart_metrics: list[str]
    save_plot: str | None
    plot_individual: bool
    individual_chart_metric: str
    use_cache: bool
    clear_cache: bool
    clear_expired_cache: bool
    show_cache_stats: bool


class ConfigError(Exception):
    """Raised when configuration file cannot be processed."""


def print_toml_version() -> None:
    version = importlib.metadata.version("review-tally")
    print(f"Current version is {version}")  # noqa: T201


def _load_config(path: str) -> dict[str, Any]:
    config_path = Path(path).expanduser()
    if not config_path.is_file():
        msg = f"Error: Configuration file '{path}' not found"
        raise ConfigError(msg)
    try:
        with config_path.open("rb") as file:
            data = tomllib.load(file)
    except tomllib.TOMLDecodeError as exc:  # pragma: no cover
        msg = f"Error parsing configuration file '{path}': {exc}"
        raise ConfigError(msg) from exc
    if not isinstance(data, dict):
        msg = "Configuration file must contain a TOML table"
        raise ConfigError(msg)
    return data


def _collect_argv() -> list[str]:
    """Return CLI arguments even when sys.argv is patched in tests."""
    raw_argv = sys.argv
    if isinstance(raw_argv, (list, tuple)):
        return list(raw_argv)

    get_item = getattr(raw_argv, "__getitem__", None)
    get_length = getattr(raw_argv, "__len__", None)
    if get_item is None or get_length is None:
        return []

    try:
        length = int(get_length())
    except (TypeError, ValueError):
        return []

    collected: list[str] = []
    try:
        collected.extend(get_item(index) for index in range(length))
    except (IndexError, KeyError, TypeError):
        return collected
    return collected


def _argument_supplied(*option_strings: str) -> bool:
    """Return True if any of the provided option strings were used."""
    argv = _collect_argv()
    if len(argv) <= 1:
        return False

    for token in argv[1:]:
        for option in option_strings:
            if token == option:
                return True
            if option.startswith("--") and token.startswith(f"{option}="):
                return True
            if (
                option.startswith("-")
                and not option.startswith("--")
                and token.startswith(option)
                and token != option
            ):
                return True
    return False


def _split_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if not isinstance(item, str):
                msg = "Configuration list values must be strings"
                raise ConfigError(msg)
            if item.strip():
                result.append(item.strip())
        return result
    msg = "Configuration values must be strings or lists of strings"
    raise ConfigError(msg)


def _coerce_date(value: object, *, field: str) -> str:
    """Return a YYYY-MM-DD string from TOML or CLI supplied values."""
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    msg = (
        "Configuration value "
        f"'{field}' must be a date string in the format YYYY-MM-DD"
    )
    raise ConfigError(msg)


def _parse_repositories(value: str | list[str] | None) -> list[str]:
    repositories = _split_list(value)
    if not repositories:
        msg = "Configuration must define at least one repository"
        raise ConfigError(msg)
    for repository in repositories:
        if "/" not in repository:
            msg = (
                "Repository entries must be in the format 'owner/repository'"
            )
            raise ConfigError(msg)
    return repositories


def parse_cmd_line() -> CommandLineArgs:  # noqa: C901, PLR0912, PLR0915
    description = """Get pull requests for the organization between dates
    and the reviewers for each pull request. The environment must declare
    a GTIHUB_TOKEN variable with a valid GitHub token.
    """
    org_help = "Organization name"
    start_date_help = "Start date in the format YYYY-MM-DD"
    end_date_help = "End date in the format YYYY-MM-DD"
    language_selection = "Select the language to filter the pull requests"
    parser = argparse.ArgumentParser(description=description)
    mut_exc_plot_group = parser.add_mutually_exclusive_group()
    # these arguments are required
    parser.add_argument("-o", "--org", required=False, help=org_help)
    parser.add_argument(
        "-c",
        "--config",
        required=False,
        help="Path to TOML configuration file",
    )
    date_format = "%Y-%m-%d"
    two_weeks_ago = datetime.now(tz=timezone.utc) - timedelta(days=14)
    today = datetime.now(tz=timezone.utc)
    parser.add_argument(
        "-s",
        "--start_date",
        required=False,
        help=start_date_help,
        default=two_weeks_ago.strftime(date_format),
    )
    parser.add_argument(
        "-e",
        "--end_date",
        required=False,
        help=end_date_help,
        default=today.strftime(date_format),
    )
    # add the language selection argument
    parser.add_argument(
        "-l",
        "--language",
        required=False,
        help=language_selection,
    )
    # add the metrics selection argument
    metrics_help = (
        "Comma-separated list of metrics to display "
        "(reviews,comments,avg-comments,engagement,thoroughness,"
        "response-time,completion-time,active-days)"
    )
    parser.add_argument(
        "-m",
        "--metrics",
        required=False,
        default="reviews,comments,avg-comments",
        help=metrics_help,
    )
    version_help = """
    Print version and exit
    """
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help=version_help,
    )
    # add sprint analysis arguments
    parser.add_argument(
        "--sprint-analysis",
        action="store_true",
        help="Generate sprint-based team aggregation as CSV",
    )
    parser.add_argument(
        "--output-path",
        help="Output CSV file path for sprint data",
    )

    # plotting options for sprint analysis
    mut_exc_plot_group.add_argument(
        "--plot-sprint",
        action="store_true",
        help=("Plot sprint metrics as an interactive chart (opens browser)"),
    )
    parser.add_argument(
        "--chart-type",
        choices=["bar", "line"],
        default="bar",
        help="Chart type for sprint metrics (bar or line)",
    )
    parser.add_argument(
        "--chart-metrics",
        default="total_reviews,total_comments",
        help=(
            "Comma-separated sprint metrics to plot. "
            "Supported: total_reviews,total_comments,unique_reviewers,"
            "avg_comments_per_review,reviews_per_reviewer,"
            "avg_response_time_hours,avg_completion_time_hours,"
            "active_review_days"
        ),
    )
    parser.add_argument(
        "--save-plot",
        help="Optional path to save the interactive HTML chart",
    )

    # plotting options for individual analysis
    mut_exc_plot_group.add_argument(
        "--plot-individual",
        action="store_true",
        help=(
            "Plot individual reviewer metrics as a pie chart (opens browser)"
        ),
    )
    parser.add_argument(
        "--individual-chart-metric",
        choices=[
            "reviews",
            "comments",
            "engagement_level",
            "thoroughness_score",
            "avg_response_time_hours",
            "avg_completion_time_hours",
            "active_review_days",
        ],
        default="reviews",
        help="Metric to visualize in individual pie chart",
    )

    # caching options
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable PR review caching (always fetch fresh data from API)",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all cached data and exit",
    )
    parser.add_argument(
        "--clear-expired-cache",
        action="store_true",
        help="Clear only expired cached data and exit",
    )
    parser.add_argument(
        "--cache-stats",
        action="store_true",
        help="Show cache statistics and exit",
    )

    args = parser.parse_args()

    config_data: dict[str, Any] = {}
    if args.config:
        try:
            config_data = _load_config(args.config)
        except ConfigError as exc:
            print(exc)  # noqa: T201
            sys.exit(1)
    parser_defaults = {
        "metrics": parser.get_default("metrics"),
        "chart_metrics": parser.get_default("chart_metrics"),
        "chart_type": parser.get_default("chart_type"),
        "language": parser.get_default("language"),
        "start_date": parser.get_default("start_date"),
        "end_date": parser.get_default("end_date"),
    }
    # catch ValueError if the date format is not correct
    if _argument_supplied("-s", "--start_date", "--start-date"):
        start_date_source: Any = args.start_date
    else:
        start_date_source = config_data.get("start_date", args.start_date)
    try:
        start_date_str = _coerce_date(start_date_source, field="start_date")
    except ConfigError as exc:
        print(exc)  # noqa: T201
        sys.exit(1)
    try:
        start_date = (datetime.strptime(start_date_str, "%Y-%m-%d")).replace(
            tzinfo=timezone.utc,
        )
    except ValueError:
        print(MalformedDateError(start_date_str))  # noqa: T201
        sys.exit(1)
    if _argument_supplied("-e", "--end_date", "--end-date"):
        end_date_source: Any = args.end_date
    else:
        end_date_source = config_data.get("end_date", args.end_date)
    try:
        end_date_str = _coerce_date(end_date_source, field="end_date")
    except ConfigError as exc:
        print(exc)  # noqa: T201
        sys.exit(1)
    try:
        end_date = (datetime.strptime(end_date_str, "%Y-%m-%d")).replace(
            tzinfo=timezone.utc,
        )
    except ValueError:
        print(MalformedDateError(end_date_str))  # noqa: T201
        sys.exit(1)
    if args.version:
        print_toml_version()
        sys.exit(0)
    if start_date > end_date:
        print("Error: Start date must be before end date")  # noqa: T201
        sys.exit(1)
    # if the language arg has comma separated values, split them
    language_source: str | list[str] | None
    if args.language is not None:
        language_source = args.language
    else:
        language_source = config_data.get("languages")
        if language_source is None:
            language_source = config_data.get("language")
        if language_source is None:
            language_source = parser_defaults["language"]
    try:
        languages = _split_list(language_source)
    except ConfigError as exc:
        print(exc)  # noqa: T201
        sys.exit(1)

    # parse metrics argument
    metrics_source: str | list[str] | None
    if _argument_supplied("-m", "--metrics"):
        metrics_source = args.metrics
    else:
        metrics_source = config_data.get("metrics", parser_defaults["metrics"])
    try:
        metrics = _split_list(metrics_source)
    except ConfigError as exc:
        print(exc)  # noqa: T201
        sys.exit(1)

    # parse chart metrics argument
    chart_metrics_source: str | list[str] | None
    if _argument_supplied("--chart-metrics"):
        chart_metrics_source = args.chart_metrics
    else:
        chart_metrics_source = config_data.get(
            "chart_metrics",
            parser_defaults["chart_metrics"],
        )
    try:
        chart_metrics = _split_list(chart_metrics_source)
    except ConfigError as exc:
        print(exc)  # noqa: T201
        sys.exit(1)

    plot_sprint = bool(
        args.plot_sprint or config_data.get("plot_sprint", False),
    )
    plot_individual = bool(
        args.plot_individual or config_data.get("plot_individual", False),
    )
    if _argument_supplied("--chart-type"):
        chart_type = args.chart_type
    else:
        chart_type = config_data.get("chart_type", args.chart_type)

    if _argument_supplied("--individual-chart-metric"):
        individual_chart_metric = args.individual_chart_metric
    else:
        individual_chart_metric = config_data.get(
            "individual_chart_metric",
            args.individual_chart_metric,
        )

    if plot_sprint and plot_individual:
        print(  # noqa: T201
            "Error: plot sprint and plot individual options are mutually "
            "exclusive.",
        )
        sys.exit(1)

    config_repositories: list[str] | None = None
    if "repositories" in config_data:
        try:
            config_repositories = _parse_repositories(
                config_data.get("repositories"),
            )
        except ConfigError as exc:
            print(exc)  # noqa: T201
            sys.exit(1)

    org_name = args.org if args.org is not None else config_data.get("org")
    if not org_name and not config_repositories:
        print("Error: Provide an organization or repositories to analyze")  # noqa: T201
        sys.exit(1)

    use_cache_config = config_data.get("use_cache")
    if args.no_cache:
        use_cache = False
    elif use_cache_config is None:
        use_cache = True
    elif isinstance(use_cache_config, bool):
        use_cache = use_cache_config
    else:
        print("Configuration value 'use_cache' must be a boolean")  # noqa: T201
        sys.exit(1)

    return CommandLineArgs(
        org_name=org_name,
        repositories=config_repositories,
        start_date=start_date,
        end_date=end_date,
        languages=languages,
        metrics=metrics,
        sprint_analysis=bool(
            args.sprint_analysis
            or config_data.get("sprint_analysis", False),
        ),
        output_path=(
            args.output_path
            if args.output_path is not None
            else config_data.get("output_path")
        ),
        plot_sprint=plot_sprint,
        chart_type=chart_type,
        chart_metrics=chart_metrics,
        save_plot=(
            args.save_plot
            if args.save_plot is not None
            else config_data.get("save_plot")
        ),
        plot_individual=plot_individual,
        individual_chart_metric=individual_chart_metric,
        use_cache=use_cache,
        clear_cache=bool(
            args.clear_cache or config_data.get("clear_cache", False),
        ),
        clear_expired_cache=bool(
            args.clear_expired_cache
            or config_data.get("clear_expired_cache", False),
        ),
        show_cache_stats=bool(
            args.cache_stats or config_data.get("show_cache_stats", False),
        ),
    )
