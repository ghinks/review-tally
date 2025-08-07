from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, cast

from tabulate import tabulate
from tqdm import tqdm

from reviewtally.analysis.team_metrics import calculate_sprint_team_metrics
from reviewtally.cli.parse_cmd_line import parse_cmd_line
from reviewtally.exporters.sprint_export import export_sprint_csv
from reviewtally.queries.get_prs import get_pull_requests_between_dates
from reviewtally.queries.get_repos_gql import (
    get_repos,
)
from reviewtally.queries.get_reviewers_rest import (
    get_reviewers_with_comments_for_pull_requests,
)
from reviewtally.queries.local_exceptions import (
    LoginNotFoundError,
)
from reviewtally.analysis.sprint_periods import (
    calculate_sprint_periods,
    get_sprint_for_date,
)

DEBUG_FLAG = False


@dataclass
class ReviewDataContext:
    """Context object for review data collection."""

    org_name: str
    repo: str
    pull_requests: list
    reviewer_stats: dict[str, dict[str, Any]]
    sprint_stats: dict[str, dict[str, Any]] | None = None
    sprint_periods: list[tuple[dt.datetime, dt.datetime, str]] | None = None


@dataclass
class ProcessRepositoriesContext:
    """Context object for repository processing."""

    org_name: str
    repo_names: tqdm
    start_date: dt.datetime
    end_date: dt.datetime
    start_time: float
    sprint_stats: dict[str, dict[str, Any]] | None = None
    sprint_periods: list[tuple[dt.datetime, dt.datetime, str]] | None = None


def timestamped_print(message: str) -> None:
    if DEBUG_FLAG:
        print(  # noqa: T201
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}", flush=True,
        )


BATCH_SIZE = 5

# Constants for engagement level thresholds
HIGH_ENGAGEMENT_THRESHOLD = 2.0
MEDIUM_ENGAGEMENT_THRESHOLD = 0.5
THOROUGHNESS_MULTIPLIER = 25
MAX_THOROUGHNESS_SCORE = 100
HOURS_PER_DAY = 24
SECONDS_PER_HOUR = 3600
MINUTES_PER_HOUR = 60


def get_avg_comments(stats: dict[str, Any]) -> str:
    return (
        f"{stats['comments'] / stats['reviews']:.1f}"
        if stats["reviews"] > 0
        else "0.0"
    )


def format_hours(hours: float) -> str:
    """Format hours into human-readable time."""
    if hours == 0:
        return "0h"
    if hours < 1:
        return f"{int(hours * MINUTES_PER_HOUR)}m"
    if hours < HOURS_PER_DAY:
        return f"{hours:.1f}h"
    days = hours / HOURS_PER_DAY
    return f"{days:.1f}d"


METRIC_INFO = {
    "reviews": {
        "header": "Reviews",
        "getter": lambda stats: stats["reviews"],
    },
    "comments": {
        "header": "Comments",
        "getter": lambda stats: stats["comments"],
    },
    "avg-comments": {
        "header": "Avg Comments",
        "getter": get_avg_comments,
    },
    "engagement": {
        "header": "Engagement",
        "getter": lambda stats: stats["engagement_level"],
    },
    "thoroughness": {
        "header": "Thoroughness",
        "getter": lambda stats: f"{stats['thoroughness_score']}%",
    },
    "response-time": {
        "header": "Avg Response",
        "getter": lambda stats: format_hours(
            stats.get("avg_response_time_hours", 0),
        ),
    },
    "completion-time": {
        "header": "Review Span",
        "getter": lambda stats: format_hours(
            stats.get("avg_completion_time_hours", 0),
        ),
    },
    "active-days": {
        "header": "Active Days",
        "getter": lambda stats: stats.get("active_review_days", 0),
    },
}

def collect_review_data(context: ReviewDataContext) -> None:
    # Create PR lookup for temporal data
    pr_lookup = {pr["number"]: pr for pr in context.pull_requests}

    pr_numbers = [pr["number"] for pr in context.pull_requests]
    pr_numbers_batched = [
        pr_numbers[i: i + BATCH_SIZE]
        for i in range(0, len(pr_numbers), BATCH_SIZE)
    ]
    for pr_numbers_batch in pr_numbers_batched:
        reviewer_data = get_reviewers_with_comments_for_pull_requests(
            context.org_name, context.repo, pr_numbers_batch,
        )
        for review in reviewer_data:
            user = review["user"]
            if "login" not in user:
                raise LoginNotFoundError

            login: str = user["login"]
            comment_count = review["comment_count"]
            pr_number = review["pull_number"]
            review_submitted_at = review["submitted_at"]

            if login not in context.reviewer_stats:
                context.reviewer_stats[login] = {
                    "reviews": 0,
                    "comments": 0,
                    "engagement_level": "Low",
                    "thoroughness_score": 0,
                    "review_times": [],
                    "pr_created_times": [],
                }

            context.reviewer_stats[login]["reviews"] += 1
            context.reviewer_stats[login]["comments"] += comment_count

            # Store temporal data for time-based metrics
            context.reviewer_stats[login]["review_times"].append(review_submitted_at)
            context.reviewer_stats[login]["pr_created_times"].append(
                pr_lookup[pr_number]["created_at"],
            )

            # Sprint-based aggregation (if enabled)
            if (context.sprint_stats
                    is not None
                    and context.sprint_periods is not None):
                review_date = datetime.strptime(
                    review_submitted_at, "%Y-%m-%dT%H:%M:%SZ",
                ).replace(tzinfo=timezone.utc)
                sprint_label = get_sprint_for_date(review_date,
                                                   context.sprint_periods)

                if sprint_label not in context.sprint_stats:
                    context.sprint_stats[sprint_label] = {
                        "total_reviews": 0,
                        "total_comments": 0,
                        "unique_reviewers": set(),
                        "review_times": [],
                        "pr_created_times": [],
                    }

                context.sprint_stats[sprint_label]["total_reviews"] += 1
                context.sprint_stats[sprint_label]["total_comments"] \
                    += comment_count
                context.sprint_stats[sprint_label]["unique_reviewers"]\
                    .add(login)
                context.sprint_stats[sprint_label]["review_times"].append(
                    review_submitted_at,
                )
                context.sprint_stats[sprint_label]["pr_created_times"].append(
                    pr_lookup[pr_number]["created_at"],
                )


def process_repositories(context: ProcessRepositoriesContext) \
        -> dict[str, dict[str, Any]]:
    reviewer_stats: dict[str, dict[str, Any]] = {}

    for repo in context.repo_names:
        timestamped_print(f"Processing {repo}")
        pull_requests = get_pull_requests_between_dates(
            context.org_name,
            repo,
            context.start_date,
            context.end_date,
        )
        timestamped_print(
            "Finished get_pull_requests_between_dates "
            f"{time.time() - context.start_time:.2f} seconds for "
            f"{len(pull_requests)} pull requests",
        )
        context.repo_names.\
            set_description(f"Processing {context.org_name}/{repo}")
        review_context = ReviewDataContext(
            org_name=context.org_name,
            repo=repo,
            pull_requests=pull_requests,
            reviewer_stats=reviewer_stats,
            sprint_stats=context.sprint_stats,
            sprint_periods=context.sprint_periods,
        )
        collect_review_data(review_context)
        timestamped_print(
            "Finished processing "
            f"{repo} {time.time() - context.start_time:.2f} seconds",
        )

    return reviewer_stats


def calculate_time_metrics(
    review_times: list[str], pr_created_times: list[str],
) -> dict[str, Any]:
    """Calculate time-based metrics from review and PR creation timestamps."""
    if not review_times or not pr_created_times:
        return {
            "avg_response_time_hours": 0.0,
            "avg_completion_time_hours": 0.0,
            "active_review_days": 0,
        }

    # Parse timestamps
    review_datetimes = [
        datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc,
        )
        for ts in review_times
    ]
    pr_created_datetimes = [
        datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc,
        )
        for ts in pr_created_times
    ]

    # Calculate response times (PR creation to review)
    response_times = []
    for created_time, review_time in zip(
        pr_created_datetimes, review_datetimes,
    ):
        if review_time >= created_time:
            response_times.append(
                (review_time - created_time).total_seconds()
                / SECONDS_PER_HOUR,
            )

    avg_response_time = (
        sum(response_times) / len(response_times)
        if response_times
        else 0.0
    )

    # Calculate completion time (first to last review)
    if len(review_datetimes) > 1:
        sorted_reviews = sorted(review_datetimes)
        completion_time = (
            (sorted_reviews[-1] - sorted_reviews[0]).total_seconds()
            / SECONDS_PER_HOUR
        )
    else:
        completion_time = 0.0

    # Calculate active review days
    review_dates = {dt.date() for dt in review_datetimes}
    active_days = len(review_dates)

    return {
        "avg_response_time_hours": avg_response_time,
        "avg_completion_time_hours": completion_time,
        "active_review_days": active_days,
    }


def calculate_reviewer_metrics(
    reviewer_stats: dict[str, dict[str, Any]],
) -> None:
    for stats in reviewer_stats.values():
        avg_comments = (
            stats["comments"] / stats["reviews"]
            if stats["reviews"] > 0
            else 0
        )

        # Review engagement level
        if avg_comments >= HIGH_ENGAGEMENT_THRESHOLD:
            stats["engagement_level"] = "High"
        elif avg_comments >= MEDIUM_ENGAGEMENT_THRESHOLD:
            stats["engagement_level"] = "Medium"
        else:
            stats["engagement_level"] = "Low"

        # Thoroughness score (0-100 scale)
        stats["thoroughness_score"] = min(
            int(avg_comments * THOROUGHNESS_MULTIPLIER),
            MAX_THOROUGHNESS_SCORE,
        )

        # Time-based metrics
        time_metrics = calculate_time_metrics(
            stats.get("review_times", []),
            stats.get("pr_created_times", []),
        )
        stats.update(time_metrics)


def generate_results_table(
    reviewer_stats: dict[str, dict[str, Any]], metrics: list[str],
) -> str:
    # Build headers and table data based on selected metrics
    headers = ["User"]
    headers.extend([
        str(METRIC_INFO[metric]["header"])
        for metric in metrics
        if metric in METRIC_INFO
    ])

    table = []
    for login, stats in reviewer_stats.items():
        row = [login]
        row.extend([
            str(cast("Any", METRIC_INFO[metric]["getter"])(stats))
            for metric in metrics
            if metric in METRIC_INFO
        ])
        table.append(row)

    # Sort by the number of PRs reviewed and comments
    def sort_key(x: list) -> tuple[int, int]:
        reviews = int(x[1]) if len(x) > 1 else 0
        comments = int(x[2]) if len(x) > 2 else 0  # noqa: PLR2004
        return (reviews, comments)

    table = sorted(table, key=sort_key, reverse=True)
    return tabulate(table, headers)


def main() -> None:
    start_time = time.time()
    timestamped_print("Starting process")
    (
        org_name,
        start_date,
        end_date,
        languages,
        metrics,
        sprint_analysis,
        output_path,
    ) = parse_cmd_line()
    timestamped_print(
        f"Calling get_repos_by_language {time.time() - start_time:.2f} "
        "seconds",
    )
    repo_list = get_repos(org_name, languages)
    if repo_list is None:
        return
    repo_names = tqdm(repo_list)
    timestamped_print(
        f"Finished get_repos_by_language {time.time() - start_time:.2f} "
        f"seconds for {len(repo_names)} repositories",
    )
    timestamped_print(
        "Calling get_pull_requests_between_dates "
        f"{time.time() - start_time:.2f} seconds",
    )

    if sprint_analysis:
        # Sprint analysis mode
        sprint_periods = calculate_sprint_periods(start_date, end_date)
        sprint_stats: dict[str, dict[str, Any]] = {}

        process_context = ProcessRepositoriesContext(
            org_name=org_name,
            repo_names=repo_names,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            sprint_stats=sprint_stats,
            sprint_periods=sprint_periods,
        )
        reviewer_stats = process_repositories(process_context)

        team_metrics = calculate_sprint_team_metrics(sprint_stats)
        if output_path:
            export_sprint_csv(team_metrics, output_path)
            print(f"Sprint analysis exported to {output_path}")  # noqa: T201
        else:
            # Print sprint summary to console
            print("Sprint Analysis Summary:")  # noqa: T201
            print("=" * 50)  # noqa: T201
            for sprint, sprint_metrics in team_metrics.items():
                print(f"\n{sprint}:")  # noqa: T201
                print(f"  Total Reviews: {sprint_metrics['total_reviews']}")  # noqa: T201
                print(f"  Total Comments: {sprint_metrics['total_comments']}")  # noqa: T201
                print(  # noqa: T201
                    "  Unique Reviewers: "
                    f"{sprint_metrics['unique_reviewers']}",
                )
                print(  # noqa: T201
                    "  Avg Comments/Review: "
                    f"{sprint_metrics['avg_comments_per_review']:.1f}",
                )
                print(  # noqa: T201
                    "  Reviews/Reviewer: "
                    f"{sprint_metrics['reviews_per_reviewer']:.1f}",
                )
                print(  # noqa: T201
                    f"  Team Engagement: {sprint_metrics['team_engagement']}",
                )
    else:
        # Normal mode - individual reviewer stats
        process_context = ProcessRepositoriesContext(
            org_name=org_name,
            repo_names=repo_names,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
        )
        reviewer_stats = process_repositories(process_context)

        calculate_reviewer_metrics(reviewer_stats)

        timestamped_print(
            f"Printing results {time.time() - start_time:.2f} seconds")

        results_table = generate_results_table(reviewer_stats, metrics)
        print(results_table)  # noqa: T201


if __name__ == "__main__":
    main()
