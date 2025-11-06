from __future__ import annotations

from typing import Any

import plotly.graph_objects as go  # type: ignore[import]
import plotly.io as pio  # type: ignore[import]

SUPPORTED_INDIVIDUAL_METRICS = {
    "reviews": "Reviews",
    "comments": "Comments",
    "engagement_level": "Engagement Level",
    "thoroughness_score": "Thoroughness Score",
    "avg_response_time_hours": "Avg Response Time (hrs)",
    "avg_completion_time_hours": "Avg Completion Time (hrs)",
    "active_review_days": "Active Review Days",
}


def _validate_individual_metric(metric: str) -> str:
    """Validate and return a supported metric, with fallback to 'reviews'."""
    if metric in SUPPORTED_INDIVIDUAL_METRICS:
        return metric
    # Fallback to reviews if invalid metric provided
    return "reviews"


def _extract_metric_values(
    reviewer_stats: dict[str, dict[str, Any]],
    metric: str,
) -> tuple[list[str], list[float]]:
    """Extract labels (reviewer names) and values for the specified metric."""
    labels = []
    values = []

    for reviewer, stats in reviewer_stats.items():
        # Skip reviewers with zero values to avoid empty pie slices
        value = stats.get(metric, 0)
        if isinstance(value, str):
            # Handle percentage strings like "85%"
            try:
                value = float(value.rstrip("%"))
            except (ValueError, AttributeError):
                value = 0.0
        elif not isinstance(value, (int, float)):
            value = 0.0

        if value > 0:
            labels.append(reviewer)
            values.append(float(value))

    return labels, values


def plot_individual_pie_chart(
    reviewer_stats: dict[str, dict[str, Any]],
    metric: str = "reviews",
    title: str = "",
    save_path: str | None = None,
) -> None:
    """
    Create a pie chart showing distribution of a metric across reviewers.

    Args:
        reviewer_stats: Dict of reviewer stats from individual analysis
        metric: The metric to visualize (reviews, comments, etc.)
        title: Chart title
        save_path: Optional HTML output path

    """
    if not reviewer_stats:
        print("No individual reviewer data available to plot.")  # noqa: T201
        return

    metric = _validate_individual_metric(metric)
    labels, values = _extract_metric_values(reviewer_stats, metric)

    if not values:
        print(f"No data available for metric '{metric}' to plot.")  # noqa: T201
        return

    metric_display_name = SUPPORTED_INDIVIDUAL_METRICS.get(metric, metric)
    # using a custom text value here to only
    # show labels for slices > threshold percentage
    total = sum(values)
    threshold = 3  # percent
    custom_text = [
        f"{label}: {value}" if (value / total * 100) > threshold else ""
        for label, value in zip(labels, values, strict=False)
    ]
    # Create pie chart
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                name=metric_display_name,
                hoverinfo="label+value+percent",
                text=custom_text,
                textinfo="text",
                direction="clockwise",
                hovertemplate="<b>%{label}</b><br>"
                f"{metric_display_name}: %{{value}}<br>"
                "Percentage: %{percent}<br>"
                "<extra></extra>",
            ),
        ],
    )

    # Update layout
    fig.update_layout(
        title=title or f"{metric_display_name} Distribution Across Reviewers",
        font={"size": 12},
        margin={"l": 60, "r": 60, "t": 80, "b": 60},
        template="plotly_white",
        showlegend=True,
        legend={
            "orientation": "v",
            "x": 1.05,
            "y": 0.5,
        },
    )

    # Ensure we open in browser
    try:
        pio.renderers.default = "browser"
    except Exception as e:  # noqa: BLE001 pragma: no cover - fallback harmless
        print(f"Failed to set default renderer: {e}")  # noqa: T201

    if save_path:
        pio.write_html(
            fig,
            file=save_path,
            auto_open=False,
            include_plotlyjs="cdn",
        )
        print(f"Saved individual pie chart to {save_path}")  # noqa: T201

    fig.show()
