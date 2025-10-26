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
from collections.abc import Iterable
from typing import NoReturn, TypedDict

import tomllib

from reviewtally.exceptions.local_exceptions import MalformedDateError


class CommandLineArgs(TypedDict):
    """Type definition for cli arguments returned by parse_cmd_line."""

    org_name: str | None
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
    repositories: list[str]


DATE_FORMAT = "%Y-%m-%d"
DEFAULT_METRICS = ["reviews", "comments", "avg-comments"]
DEFAULT_CHART_METRICS = ["total_reviews", "total_comments"]
DEFAULT_CHART_TYPE = "bar"
DEFAULT_INDIVIDUAL_CHART_METRIC = "reviews"
ALLOWED_CHART_TYPES = {"bar", "line"}
ALLOWED_INDIVIDUAL_METRICS = {
    "reviews",
    "comments",
    "engagement_level",
    "thoroughness_score",
    "avg_response_time_hours",
    "avg_completion_time_hours",
    "active_review_days",
}


def print_toml_version() -> None:
    version = importlib.metadata.version("review-tally")
    print(f"Current version is {version}")  # noqa: T201


def _config_error(message: str) -> NoReturn:
    print(f"Error: {message}")  # noqa: T201
    sys.exit(1)


def _load_config(path: str) -> dict[str, object]:
    config_path = Path(path).expanduser()
    try:
        with config_path.open("rb") as config_file:
            return tomllib.load(config_file)
    except FileNotFoundError:
        _config_error(f"Configuration file not found: {config_path}")
    except tomllib.TOMLDecodeError as exc:
        _config_error(f"Failed to parse configuration file: {exc}")
    except OSError as exc:
        _config_error(f"Unable to read configuration file: {exc}")


def _parse_date_value(
    value: object | None,
    *,
    fallback: datetime,
    field_name: str,
) -> datetime:
    if value is None:
        return fallback
    if isinstance(value, datetime):
        parsed_value = value
    elif isinstance(value, date):
        parsed_value = datetime.combine(value, datetime.min.time())
    elif isinstance(value, str):
        try:
            parsed_value = datetime.strptime(value, DATE_FORMAT)  # noqa: DTZ007
        except ValueError:
            print(MalformedDateError(value))  # noqa: T201
            sys.exit(1)
    else:
        _config_error(
            f"{field_name} must be a YYYY-MM-DD string "
            "or date in the configuration file",
        )
    return parsed_value.replace(tzinfo=timezone.utc)


def _parse_sequence(value: object | None, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items: Iterable[object] = value.split(",")
    elif isinstance(value, (list, tuple)):
        raw_items = value
    else:
        _config_error(
            f"{field_name} must be provided as a string "
            "or array in the configuration file",
        )

    items: list[str] = []
    for item in raw_items:
        if not isinstance(item, str):
            _config_error(
                f"All values for {field_name} must be strings "
                "in the configuration file",
            )
        stripped = item.strip()
        if stripped:
            items.append(stripped)
    return items


def _parse_repositories(value: object | None) -> list[str]:
    repositories = _parse_sequence(value, "repositories")
    for repo in repositories:
        owner, separator, name = repo.partition("/")
        if separator == "" or not owner or not name:
            _config_error(
                f"Invalid repository entry '{repo}'. "
                "Expected format 'owner/repository-name'.",
            )
    return repositories


def _get_optional_str(config: dict[str, object], key: str) -> str | None:
    value = config.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    _config_error(f"{key} must be a string in the configuration file")
    return None


def _get_config_bool(config: dict[str, object], key: str) -> bool:
    value = config.get(key)
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    _config_error(f"{key} must be a boolean in the configuration file")
    return False


def parse_cmd_line() -> CommandLineArgs:  # noqa: C901, PLR0912, PLR0915
    description = """Get pull requests for the organization between dates
    and the reviewers for each pull request. The environment must declare
    a GTIHUB_TOKEN variable with a valid GitHub token.
    """
    org_help = "Organization name"
    start_date_help = "Start date in the format YYYY-MM-DD"
    end_date_help = "End date in the format YYYY-MM-DD"
    language_selection = "Select the languages to filter the pull requests"
    parser = argparse.ArgumentParser(description=description)
    mut_exc_plot_group = parser.add_mutually_exclusive_group()
    parser.add_argument(
        "-c",
        "--config",
        dest="config",
        help="Path to a TOML configuration file",
    )
    parser.add_argument(
        "-o",
        "--org",
        dest="org",
        required=False,
        help=org_help,
    )
    parser.add_argument(
        "-s",
        "--start-date",
        dest="start_date",
        help=start_date_help,
    )
    parser.add_argument(
        "-e",
        "--end-date",
        dest="end_date",
        help=end_date_help,
    )
    parser.add_argument(
        "-l",
        "--languages",
        dest="languages",
        help=language_selection,
    )
    metrics_help = (
        "Comma-separated list of metrics to display "
        "(reviews,comments,avg-comments,engagement,thoroughness,"
        "response-time,completion-time,active-days)"
    )
    parser.add_argument(
        "-m",
        "--metrics",
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
        choices=sorted(ALLOWED_CHART_TYPES),
        help="Chart type for sprint metrics (bar or line)",
    )
    parser.add_argument(
        "--chart-metrics",
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
        choices=sorted(ALLOWED_INDIVIDUAL_METRICS),
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
    if args.version:
        print_toml_version()
        sys.exit(0)
    config: dict[str, object] = {}
    if args.config:
        config = _load_config(args.config)

    two_weeks_ago = datetime.now(tz=timezone.utc) - timedelta(days=14)
    today = datetime.now(tz=timezone.utc)

    org_input = args.org
    if org_input is None:
        org_input = _get_optional_str(config, "org")
    if org_input is not None:
        org_input = org_input.strip()
    org_name = org_input or None

    if args.start_date is not None:
        start_date_source = args.start_date
    else:
        start_date_source = config.get("start_date")
    start_date = _parse_date_value(
        start_date_source,
        fallback=two_weeks_ago,
        field_name="start_date",
    )
    if args.end_date is not None:
        end_date_source = args.end_date
    else:
        end_date_source = config.get("end_date")
    end_date = _parse_date_value(
        end_date_source,
        fallback=today,
        field_name="end_date",
    )

    if start_date > end_date:
        print("Error: Start date must be before end date")  # noqa: T201
        sys.exit(1)

    if args.languages is not None:
        languages_input = args.languages
    else:
        languages_input = config.get("languages")
    raw_languages = _parse_sequence(languages_input, "languages")
    languages = [language.lower() for language in raw_languages]

    metrics_input = (
        args.metrics if args.metrics is not None else config.get("metrics")
    )
    metrics = (
        _parse_sequence(metrics_input, "metrics")
        if metrics_input is not None
        else []
    )
    if not metrics:
        metrics = list(DEFAULT_METRICS)

    chart_metrics_input = (
        args.chart_metrics
        if args.chart_metrics is not None
        else config.get("chart_metrics")
    )
    chart_metrics_specified = chart_metrics_input is not None
    chart_metrics = (
        _parse_sequence(chart_metrics_input, "chart_metrics")
        if chart_metrics_input is not None
        else []
    )
    if not chart_metrics:
        chart_metrics = list(DEFAULT_CHART_METRICS)

    chart_type_input = args.chart_type
    if chart_type_input is None:
        chart_type_input = _get_optional_str(config, "chart_type")
    if (
        chart_type_input is not None
        and chart_type_input not in ALLOWED_CHART_TYPES
    ):
        _config_error("chart_type must be one of: bar, line")
    chart_type = chart_type_input or DEFAULT_CHART_TYPE

    individual_chart_metric_input = (
        args.individual_chart_metric
        if args.individual_chart_metric is not None
        else _get_optional_str(config, "individual_chart_metric")
    )
    individual_metric_specified = individual_chart_metric_input is not None
    if (
        individual_chart_metric_input is not None
        and individual_chart_metric_input not in ALLOWED_INDIVIDUAL_METRICS
    ):
        allowed_metrics = ", ".join(sorted(ALLOWED_INDIVIDUAL_METRICS))
        _config_error(
            "individual_chart_metric must be one of: "
            f"{allowed_metrics}",
        )
    individual_chart_metric = (
        individual_chart_metric_input or DEFAULT_INDIVIDUAL_CHART_METRIC
    )

    sprint_analysis = bool(args.sprint_analysis) or _get_config_bool(
        config,
        "sprint_analysis",
    )
    plot_sprint = bool(args.plot_sprint) or _get_config_bool(
        config,
        "plot_sprint",
    )
    plot_individual = bool(args.plot_individual) or _get_config_bool(
        config,
        "plot_individual",
    )

    if plot_sprint and plot_individual:
        print("Error: plot sprint and plot individual are mutually exclusive.")  # noqa: T201
        sys.exit(1)
    if plot_sprint and individual_metric_specified:
        print(  # noqa: T201
            "Error: chart metrics and individual chart metric "
            "are mutually exclusive.",
        )
        sys.exit(1)
    if plot_individual and chart_metrics_specified:
        print(  # noqa: T201
            "Error: plot individual and chart metrics are mutually exclusive.",
        )
        sys.exit(1)

    save_plot = args.save_plot
    if save_plot is None:
        save_plot = _get_optional_str(config, "save_plot")

    output_path = args.output_path
    if output_path is None:
        output_path = _get_optional_str(config, "output_path")

    use_cache = not (
        args.no_cache
        or _get_config_bool(
            config,
            "no_cache",
        )
    )
    clear_cache = bool(args.clear_cache) or _get_config_bool(
        config,
        "clear_cache",
    )
    clear_expired_cache = bool(args.clear_expired_cache) or _get_config_bool(
        config,
        "clear_expired_cache",
    )
    show_cache_stats = bool(args.cache_stats) or _get_config_bool(
        config,
        "cache_stats",
    )

    repositories = _parse_repositories(config.get("repositories"))

    if org_name is None and not repositories:
        error_msg = (
            "Error: Provide an organization (--org) "
            "or configure repositories."
        )
        print(error_msg)  # noqa: T201
        sys.exit(1)

    return CommandLineArgs(
        org_name=org_name,
        start_date=start_date,
        end_date=end_date,
        languages=languages,
        metrics=metrics,
        sprint_analysis=sprint_analysis,
        output_path=output_path,
        plot_sprint=plot_sprint,
        chart_type=chart_type,
        chart_metrics=chart_metrics,
        save_plot=save_plot,
        plot_individual=plot_individual,
        individual_chart_metric=individual_chart_metric,
        use_cache=use_cache,
        clear_cache=clear_cache,
        clear_expired_cache=clear_expired_cache,
        show_cache_stats=show_cache_stats,
        repositories=repositories,
    )
