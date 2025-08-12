from datetime import datetime, timezone
from typing import Any

SECONDS_PER_HOUR = 3600
HIGH_ENGAGEMENT_THRESHOLD = 2.0
MEDIUM_ENGAGEMENT_THRESHOLD = 0.5


def calculate_team_time_metrics(
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


def classify_team_engagement(avg_comments: float) -> str:
    """Classify team engagement level."""
    if avg_comments >= HIGH_ENGAGEMENT_THRESHOLD:
        return "High"
    if avg_comments >= MEDIUM_ENGAGEMENT_THRESHOLD:
        return "Medium"
    return "Low"


def calculate_sprint_team_metrics(
    sprint_stats: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Calculate aggregated team metrics per sprint."""
    team_metrics = {}

    for sprint, data in sprint_stats.items():
        # Convert set to count for JSON serialization
        unique_reviewer_count = len(data["unique_reviewers"])

        team_metrics[sprint] = {
            "sprint_period": sprint,
            "total_reviews": data["total_reviews"],
            "total_comments": data["total_comments"],
            "unique_reviewers": unique_reviewer_count,
            "avg_comments_per_review": (
                data["total_comments"] / data["total_reviews"]
                if data["total_reviews"] > 0
                else 0
            ),
            "reviews_per_reviewer": (
                data["total_reviews"] / unique_reviewer_count
                if unique_reviewer_count > 0
                else 0
            ),
            "team_engagement": classify_team_engagement(
                data["total_comments"] / data["total_reviews"]
                if data["total_reviews"] > 0
                else 0,
            ),
        }

        # Add time-based team metrics
        time_metrics = calculate_team_time_metrics(
            data["review_times"],
            data["pr_created_times"],
        )
        team_metrics[sprint].update(time_metrics)

    return team_metrics
