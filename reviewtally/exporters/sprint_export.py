import csv
from pathlib import Path
from typing import Any


def export_sprint_csv(
    team_metrics: dict[str, dict[str, Any]],
    output_path: str,
) -> None:
    """Export sprint team metrics as CSV."""
    if not team_metrics:
        return

    fieldnames = list(next(iter(team_metrics.values())).keys())
    with Path(output_path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for sprint_data in team_metrics.values():
            writer.writerow(sprint_data)
