from __future__ import annotations

from typing import Any, cast

from tabulate import tabulate

MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24


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


def generate_results_table(  # noqa: C901
    reviewer_stats: dict[str, dict[str, Any]],
    metrics: list[str],
) -> str:
    # Build headers and table data based on selected metrics
    headers = ["User"]
    headers.extend(
        [
            str(METRIC_INFO[metric]["header"])
            for metric in metrics
            if metric in METRIC_INFO
        ],
    )

    # Resolve indices for robust sorting (may be absent depending on metrics)
    try:
        reviews_idx = headers.index("Reviews")
    except ValueError:
        reviews_idx = -1
    try:
        comments_idx = headers.index("Comments")
    except ValueError:
        comments_idx = -1

    def _safe_int(value: float | str) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            s = value.strip()
            try:
                return int(s)
            except ValueError:
                try:
                    return int(float(s))
                except ValueError:
                    return 0
        return 0

    table: list[list[Any]] = []
    for login, stats in reviewer_stats.items():
        row = [login]
        row.extend(
            [
                str(cast("Any", METRIC_INFO[metric]["getter"])(stats))
                for metric in metrics
                if metric in METRIC_INFO
            ],
        )
        table.append(row)

    # Sort primarily by Reviews, then by Comments; missing or non-numeric -> 0
    def sort_key(row: list[Any]) -> tuple[int, int]:
        reviews = (
            _safe_int(row[reviews_idx])
            if 0 <= reviews_idx < len(row)
            else 0
        )
        comments = (
            _safe_int(row[comments_idx])
            if 0 <= comments_idx < len(row)
            else 0
        )
        return (reviews, comments)

    table = sorted(table, key=sort_key, reverse=True)
    return tabulate(table, headers)
