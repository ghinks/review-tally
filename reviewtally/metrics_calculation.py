from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Constants for engagement level thresholds
HIGH_ENGAGEMENT_THRESHOLD = 2.0
MEDIUM_ENGAGEMENT_THRESHOLD = 0.5
THOROUGHNESS_MULTIPLIER = 25
MAX_THOROUGHNESS_SCORE = 100
HOURS_PER_DAY = 24
SECONDS_PER_HOUR = 3600
MINUTES_PER_HOUR = 60


def calculate_time_metrics(
    review_times: list[str],
    pr_created_times: list[str],
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
        pr_created_datetimes,
        review_datetimes,
    ):
        if review_time >= created_time:
            response_times.append(
                (review_time - created_time).total_seconds()
                / SECONDS_PER_HOUR,
            )

    avg_response_time = (
        sum(response_times) / len(response_times) if response_times else 0.0
    )

    # Calculate completion time (first to last review)
    if len(review_datetimes) > 1:
        sorted_reviews = sorted(review_datetimes)
        completion_time = (
            sorted_reviews[-1] - sorted_reviews[0]
        ).total_seconds() / SECONDS_PER_HOUR
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
            stats["comments"] / stats["reviews"] if stats["reviews"] > 0 else 0
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
