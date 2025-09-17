from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tqdm import tqdm

from reviewtally.analysis.sprint_periods import get_sprint_for_date
from reviewtally.exceptions.local_exceptions import LoginNotFoundError
from reviewtally.queries.get_prs import get_pull_requests_between_dates
from reviewtally.queries.get_reviewers_rest import (
    get_reviewers_with_comments_for_pull_requests,
)

DEBUG_FLAG = False
BATCH_SIZE = 5


def timestamped_print(message: str) -> None:
    if DEBUG_FLAG:
        print(  # noqa: T201
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}",
            flush=True,
        )


@dataclass
class ReviewDataContext:
    """Context object for review data collection."""

    org_name: str
    repo: str
    pull_requests: list
    reviewer_stats: dict[str, dict[str, Any]]
    sprint_stats: dict[str, dict[str, Any]] | None = None
    sprint_periods: list[tuple[datetime, datetime, str]] | None = None
    use_cache: bool = True


@dataclass
class ProcessRepositoriesContext:
    """Context object for repository processing."""

    org_name: str
    repo_names: tqdm
    start_date: datetime
    end_date: datetime
    start_time: float
    sprint_stats: dict[str, dict[str, Any]] | None = None
    sprint_periods: list[tuple[datetime, datetime, str]] | None = None
    use_cache: bool = True


@dataclass
class SprintPlottingContext:
    """Context object for sprint plotting functionality."""

    team_metrics: dict[str, dict[str, Any]]
    org_name: str
    start_date: datetime
    end_date: datetime
    chart_type: str
    chart_metrics: list[str]
    save_plot: str | None


def collect_review_data(context: ReviewDataContext) -> None:
    # Create PR lookup for temporal data
    pr_lookup = {pr["number"]: pr for pr in context.pull_requests}

    pr_numbers = [pr["number"] for pr in context.pull_requests]
    pr_numbers_batched = [
        pr_numbers[i : i + BATCH_SIZE]
        for i in range(0, len(pr_numbers), BATCH_SIZE)
    ]
    for pr_numbers_batch in pr_numbers_batched:
        reviewer_data = get_reviewers_with_comments_for_pull_requests(
            context.org_name,
            context.repo,
            pr_numbers_batch,
            use_cache=context.use_cache,
        )
        for review in reviewer_data:
            user = review["user"]
            if "login" not in user:
                raise LoginNotFoundError

            login: str = user["login"]
            comment_count = review["comment_count"]
            pr_number = review["pull_number"]
            review_submitted_at = review.get("submitted_at")

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

            # Store temporal data for time metrics only if submitted_at exists
            if review_submitted_at is not None:
                context.reviewer_stats[login]["review_times"].append(
                    review_submitted_at,
                )
                context.reviewer_stats[login]["pr_created_times"].append(
                    pr_lookup[pr_number]["created_at"],
                )
            else:
                # Log when we skip time-based metrics due to missing timestamp
                print(  # noqa: T201
                    f"Warning: Skipping time metrics for review by {login} "
                    f"on PR {pr_number} (missing submitted_at)",
                )

            # Sprint-based aggregation (if enabled and submitted_at exists)
            if (
                context.sprint_stats is not None
                and context.sprint_periods is not None
                and review_submitted_at is not None
            ):
                review_date = datetime.strptime(
                    review_submitted_at,
                    "%Y-%m-%dT%H:%M:%SZ",
                ).replace(tzinfo=timezone.utc)
                sprint_label = get_sprint_for_date(
                    review_date,
                    context.sprint_periods,
                )

                if sprint_label not in context.sprint_stats:
                    context.sprint_stats[sprint_label] = {
                        "total_reviews": 0,
                        "total_comments": 0,
                        "unique_reviewers": set(),
                        "review_times": [],
                        "pr_created_times": [],
                    }

                context.sprint_stats[sprint_label]["total_reviews"] += 1
                context.sprint_stats[sprint_label]["total_comments"] += (
                    comment_count
                )
                context.sprint_stats[sprint_label]["unique_reviewers"].add(
                    login,
                )
                context.sprint_stats[sprint_label]["review_times"].append(
                    review_submitted_at,
                )
                context.sprint_stats[sprint_label]["pr_created_times"].append(
                    pr_lookup[pr_number]["created_at"],
                )
            elif (
                context.sprint_stats is not None
                and review_submitted_at is None
            ):
                # Log when we skip sprint aggregation due to missing timestamp
                print(  # noqa: T201
                    f"Warning: Skipping sprint "
                    f"aggregation for review by {login} "
                    f"on PR {pr_number} (missing submitted_at)",
                )


def process_repositories(
    context: ProcessRepositoriesContext,
) -> dict[str, dict[str, Any]]:
    reviewer_stats: dict[str, dict[str, Any]] = {}

    for repo in context.repo_names:
        timestamped_print(f"Processing {repo}")
        pull_requests = get_pull_requests_between_dates(
            context.org_name,
            repo,
            context.start_date,
            context.end_date,
            use_cache=context.use_cache,
        )
        timestamped_print(
            "Finished get_pull_requests_between_dates "
            f"{time.time() - context.start_time:.2f} seconds for "
            f"{len(pull_requests)} pull requests",
        )
        context.repo_names.set_description(
            f"Processing {context.org_name}/{repo}",
        )
        review_context = ReviewDataContext(
            org_name=context.org_name,
            repo=repo,
            pull_requests=pull_requests,
            reviewer_stats=reviewer_stats,
            sprint_stats=context.sprint_stats,
            sprint_periods=context.sprint_periods,
            use_cache=context.use_cache,
        )
        collect_review_data(review_context)
        timestamped_print(
            "Finished processing "
            f"{repo} {time.time() - context.start_time:.2f} seconds",
        )

    return reviewer_stats
