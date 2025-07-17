import time
from typing import Any, cast

from tabulate import tabulate
from tqdm import tqdm

from reviewtally.queries.local_exceptions import (
    GitHubTokenNotDefinedError,
    LoginNotFoundError,
    NoGitHubOrgError,
)

from .cli.parse_cmd_line import parse_cmd_line
from .queries.get_prs import get_pull_requests_between_dates
from .queries.get_repos_gql import get_repos_by_language
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


def main() -> None:
    # map containing the reviewer name and the number of pull requests reviewed
    start_time = time.time()
    timestamped_print("Starting process")
    reviewer_stats: dict[str, dict[str, Any]] = {}
    org_name, start_date, end_date, languages, metrics = parse_cmd_line()
    try:
        timestamped_print(
            f"Calling get_repos_by_language {time.time() - start_time:.2f} "
            "seconds",
        )
        repo_names = tqdm(get_repos_by_language(org_name, languages))
    except GitHubTokenNotDefinedError as e:
        print("Error:", e)  # noqa: T201
        return
    except NoGitHubOrgError as e:
        print("Error:", e)  # noqa: T201
        return
    timestamped_print(
        f"Finished get_repos_by_language {time.time() - start_time:.2f} "
        f"seconds for {len(repo_names)} repositories",
    )
    timestamped_print(
        "Calling get_pull_requests_between_dates "
        f"{time.time() - start_time:.2f} seconds",
    )
    # it is possible to take these asynchronous requests and
    # batch them to improve performance.
    # get all the repo names

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
        pr_numbers = [pr["number"] for pr in pull_requests]
        repo_names.set_description(f"Processing {org_name}/{repo}")
        # create batches of 5 pr_numbers
        pr_numbers_batched = [
            pr_numbers[i: i + BATCH_SIZE]
                for i in range(0, len(pr_numbers), BATCH_SIZE)
        ]
        for pr_numbers in pr_numbers_batched:
            reviewer_data = get_reviewers_with_comments_for_pull_requests(
                org_name, repo, pr_numbers,
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
        timestamped_print(
            "Finished processing "
            f"{repo} {time.time() - start_time:.2f} seconds",
        )

    # Calculate Phase 1 metrics
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

    # convert the dictionary to a list of lists and print out with tabulate
    timestamped_print(
        f"Printing results {time.time() - start_time:.2f} seconds")

    # Define available metrics and their display info
    def get_avg_comments(stats: dict[str, Any]) -> str:
        return (
            f"{stats['comments'] / stats['reviews']:.1f}"
            if stats["reviews"] > 0
            else "0.0"
        )

    metric_info = {
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

    # Build headers and table data based on selected metrics
    headers = ["User"]
    headers.extend([
        str(metric_info[metric]["header"])
        for metric in metrics
        if metric in metric_info
    ])

    table = []
    for login, stats in reviewer_stats.items():
        row = [login]
        row.extend([
            str(cast(Any, metric_info[metric]["getter"])(stats))
            for metric in metrics
            if metric in metric_info
        ])
        table.append(row)

    # convert the dictionary to a list of lists and
    #   sort by the number of PRs reviewed
    def sort_key(x: list) -> tuple[int, int]:
        reviews = x[1] if len(x) > 1 else 0
        comments = x[2] if len(x) > 2 else 0  # noqa: PLR2004
        return (reviews, comments)

    table = sorted(table, key=sort_key, reverse=True)
    print(tabulate(table, headers))  # noqa: T201


if __name__ == "__main__":
    main()
