from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
from typing import Any

import plotly.graph_objects as go  # type: ignore[import]
import plotly.io as pio  # type: ignore[import]

SUPPORTED_METRICS = {
    "total_reviews": "Total Reviews",
    "total_comments": "Total Comments",
    "unique_reviewers": "Unique Reviewers",
    "avg_comments_per_review": "Avg Comments/Review",
    "reviews_per_reviewer": "Reviews/Reviewer",
    "avg_response_time_hours": "Avg Response (hrs)",
    "avg_completion_time_hours": "Review Span (hrs)",
    "active_review_days": "Active Review Days",
}


def _validate_metrics(metrics: Iterable[str]) -> list[str]:
    valid: list[str] = []
    for m in metrics:
        if m in SUPPORTED_METRICS:
            valid.append(m)
        else:
            # Keep it quiet but skip unknown. Could log/print if desired.
            pass
    return valid or ["total_reviews", "total_comments"]


def _sorted_sprint_labels(team_metrics: dict[str, dict[str, Any]]) -> \
        list[str]:
    # sprint labels are YYYY-MM-DD -> lexical sort is chronological
    return sorted(team_metrics.keys())


def plot_sprint_metrics(
    team_metrics: dict[str, dict[str, Any]],
    chart_type: str,
    metrics: list[str],
    title: str,
    save_path: str | None = None,
) -> None:
    """
    Render sprint metrics in a browser using Plotly.

    Args:
        team_metrics: Output of calculate_sprint_team_metrics.
        chart_type: "bar" or "line".
        metrics: list of metric keys to plot.
        title: chart title.
        save_path: optional HTML output path.

    """
    if not team_metrics:
        print("No sprint data available to plot.")  # noqa: T201
        return

    metrics = _validate_metrics(metrics)

    x = _sorted_sprint_labels(team_metrics)

    # Build traces
    traces: list[Any] = []
    for metric in metrics:
        y = [team_metrics[label].get(metric, 0) for label in x]
        display_name = SUPPORTED_METRICS.get(metric, metric)
        if chart_type == "line":
            traces.append(
                go.Scatter(x=x, y=y, mode="lines+markers", name=display_name),
            )
        else:
            traces.append(go.Bar(x=x, y=y, name=display_name))

    layout = go.Layout(
        title=title,
        barmode="group" if chart_type == "bar" else None,
        xaxis={"title": "Sprint (Start Date)"},
        yaxis={"title":"Value"},
        legend={"orientation":"h", "y":-0.2},
        margin={"l":60, "r":30, "t":60, "b":80},
        template="plotly_white",
    )

    fig = go.Figure(data=traces, layout=layout)

    # Ensure we open in a browser
    try:
        pio.renderers.default = "browser"
    except Exception as e:  # noqa: BLE001 pragma: no cover - fallback harmless
        print(f"Failed to set default renderer: {e}") # noqa: T201

    if save_path:
        pio.write_html(fig, file=save_path,
                       auto_open=False, include_plotlyjs="cdn")
        print(f"Saved sprint chart to {save_path}")  # noqa: T201

    fig.show()
