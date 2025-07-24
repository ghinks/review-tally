from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import datetime

from tabulate import tabulate
from tqdm import tqdm

from reviewtally.queries.local_exceptions import (
    LoginNotFoundError,
)

from .cli.parse_cmd_line import parse_cmd_line
from .queries.get_prs import get_pull_requests_between_dates
from .queries.get_repos_gql import (
    get_repos,
)
from .queries.get_reviewers_rest import (
    get_reviewers_with_comments_for_pull_requests,
)

DEBUG_FLAG = False


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


def get_avg_comments(stats: dict[str, Any]) -> str:
    return (
        f"{stats['comments'] / stats['reviews']:.1f}"
        if stats["reviews"] > 0
        else "0.0"
    )


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
}



def collect_review_data(
    org_name: str,
    repo: str,
    pull_requests: list,
    reviewer_stats: dict[str, dict[str, Any]],
) -> None:
    pr_numbers = [pr["number"] for pr in pull_requests]
    pr_numbers_batched = [
        pr_numbers[i: i + BATCH_SIZE]
        for i in range(0, len(pr_numbers), BATCH_SIZE)
    ]
    for pr_numbers_batch in pr_numbers_batched:
        reviewer_data = get_reviewers_with_comments_for_pull_requests(
            org_name, repo, pr_numbers_batch,
        )
        for review in reviewer_data:
            user = review["user"]
            if "login" not in user:
                raise LoginNotFoundError

            login: str = user["login"]
            comment_count = review["comment_count"]

            if login not in reviewer_stats:
                reviewer_stats[login] = {
                    "reviews": 0,
                    "comments": 0,
                    "engagement_level": "Low",
                    "thoroughness_score": 0,
                }

            reviewer_stats[login]["reviews"] += 1
            reviewer_stats[login]["comments"] += comment_count


def process_repositories(
    org_name: str,
    repo_names: tqdm,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    start_time: float,
) -> dict[str, dict[str, Any]]:
    reviewer_stats: dict[str, dict[str, Any]] = {}

    for repo in repo_names:
        timestamped_print(f"Processing {repo}")
        pull_requests = get_pull_requests_between_dates(
            org_name,
            repo,
            start_date,
            end_date,
        )
        timestamped_print(
            "Finished get_pull_requests_between_dates "
            f"{time.time() - start_time:.2f} seconds for "
            f"{len(pull_requests)} pull requests",
        )
        repo_names.set_description(f"Processing {org_name}/{repo}")
        collect_review_data(org_name, repo, pull_requests, reviewer_stats)
        timestamped_print(
            "Finished processing "
            f"{repo} {time.time() - start_time:.2f} seconds",
        )

    return reviewer_stats


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
        reviews = x[1] if len(x) > 1 else 0
        comments = x[2] if len(x) > 2 else 0  # noqa: PLR2004
        return (reviews, comments)

    table = sorted(table, key=sort_key, reverse=True)
    return tabulate(table, headers)


def main() -> None:
    start_time = time.time()
    timestamped_print("Starting process")
    org_name, start_date, end_date, languages, metrics = parse_cmd_line()
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

    reviewer_stats = process_repositories(
        org_name, repo_names, start_date, end_date, start_time,
    )

    calculate_reviewer_metrics(reviewer_stats)

    timestamped_print(
        f"Printing results {time.time() - start_time:.2f} seconds")

    results_table = generate_results_table(reviewer_stats, metrics)
    print(results_table)  # noqa: T201


if __name__ == "__main__":
    main()
