# import argparse and create a function to parse command line arguments
# and return the parsed arguments, which will be used by the main function
# to get the start and end dates for the pull requests and the organization
# name
from __future__ import annotations

import argparse
import importlib.metadata
import sys
from datetime import datetime, timedelta, timezone
from typing import TypedDict

from reviewtally.exceptions.local_exceptions import MalformedDateError


class CommandLineArgs(TypedDict):
    """Type definition for cli arguments returned by parse_cmd_line."""

    org_name: str
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
    use_cache: bool


def print_toml_version() -> None:
    version = importlib.metadata.version("review-tally")
    print(f"Current version is {version}")  # noqa: T201


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
    # these arguments are required
    parser.add_argument("-o", "--org", required=False, help=org_help)
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
    parser.add_argument(
        "--plot-sprint",
        action="store_true",
        help=(
            "Plot sprint metrics as an interactive chart (opens browser)"
        ),
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

    # caching options
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable PR review caching (always fetch fresh data from API)",
    )

    args = parser.parse_args()
    # catch ValueError if the date format is not correct
    try:
        if args.start_date:
            start_date = (
                datetime.strptime(args.start_date, "%Y-%m-%d")
            ).replace(tzinfo=timezone.utc)
    except ValueError:
        print(MalformedDateError(args.start_date))  # noqa: T201
        sys.exit(1)
    try:
        if args.end_date:
            end_date = (datetime.strptime(args.end_date, "%Y-%m-%d")).replace(
                tzinfo=timezone.utc,
            )
    except ValueError:
        print(MalformedDateError(args.end_date))  # noqa: T201
        sys.exit(1)
    if args.version:
        print_toml_version()
        sys.exit(0)
    if start_date > end_date:
        print("Error: Start date must be before end date")  # noqa: T201
        sys.exit(1)
    # if the language arg has comma separated values, split them
    if args.language is None:
        languages = []
    elif args.language and "," in args.language:
        languages = args.language.split(",")
    else:
        languages = [args.language]

    # parse metrics argument
    if args.metrics and "," in args.metrics:
        metrics = args.metrics.split(",")
    else:
        metrics = [args.metrics]

    # parse chart metrics argument
    if args.chart_metrics and "," in args.chart_metrics:
        chart_metrics = args.chart_metrics.split(",")
    else:
        chart_metrics = [args.chart_metrics]

    return CommandLineArgs(
        org_name=args.org,
        start_date=start_date,
        end_date=end_date,
        languages=languages,
        metrics=metrics,
        sprint_analysis=args.sprint_analysis,
        output_path=args.output_path,
        plot_sprint=args.plot_sprint,
        chart_type=args.chart_type,
        chart_metrics=chart_metrics,
        save_plot=args.save_plot,
        use_cache=not args.no_cache,
    )
