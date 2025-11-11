from __future__ import annotations

import sys
import time
from typing import Any

import requests
from tqdm import tqdm

from reviewtally.analysis.sprint_periods import calculate_sprint_periods
from reviewtally.analysis.team_metrics import calculate_sprint_team_metrics
from reviewtally.cache.cache_manager import CacheManager
from reviewtally.cli.parse_cmd_line import CommandLineArgs, parse_cmd_line
from reviewtally.data_collection import (
    ProcessRepositoriesContext,
    RepositoryTarget,
    SprintPlottingContext,
    process_repositories,
    timestamped_print,
)
from reviewtally.exporters.sprint_export import export_sprint_csv
from reviewtally.metrics_calculation import calculate_reviewer_metrics
from reviewtally.output_formatting import generate_results_table
from reviewtally.queries import (
    GENERAL_TIMEOUT,
    build_github_rest_api_url,
    require_github_token,
    set_github_host,
)
from reviewtally.queries.get_repos_gql import get_repos
from reviewtally.visualization.individual_plot import (
    SUPPORTED_INDIVIDUAL_METRICS,
    plot_individual_pie_chart,
)
from reviewtally.visualization.sprint_plot import plot_sprint_metrics


def main() -> None:
    start_time = time.time()
    timestamped_print("Starting process")

    # Parse command line arguments
    args = parse_cmd_line()
    set_github_host(
        args["github_host"],
        rest_path=args["github_rest_path"],
        graphql_path=args["github_graphql_path"],
    )

    # Handle cache management operations
    if (
        args["clear_cache"]
        or args["clear_expired_cache"]
        or args["show_cache_stats"]
    ):
        _handle_cache_operations(args)
        sys.exit(0)

    repo_targets: list[RepositoryTarget]
    if args["repositories"]:
        repo_targets = []
        for full_name in args["repositories"]:
            owner, repo_name = full_name.split("/", 1)
            repo_targets.append(RepositoryTarget(owner=owner, name=repo_name))
        configured_message = (
            "Using configured repositories "
            f"{time.time() - start_time:.2f} seconds"
        )
        timestamped_print(configured_message)
        token = require_github_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        for target in repo_targets:
            url = build_github_rest_api_url(
                f"repos/{target.owner}/{target.name}",
            )
            response = requests.get(
                url,
                headers=headers,
                timeout=GENERAL_TIMEOUT,
            )
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                status = (
                    getattr(e.response, "status_code", None)
                    or response.status_code
                )
                print(  # noqa: T201
                    f"Error: repository {target.owner}/{target.name}"
                    " not found ",
                    f"(HTTP {status})",
                )
                sys.exit(1)
    else:
        request_message = (
            "Calling get_repos_by_language "
            f"{time.time() - start_time:.2f} seconds"
        )
        timestamped_print(request_message)
        org_name = args["org_name"] or ""
        repo_names = get_repos(org_name, args["languages"])
        if repo_names is None:
            return
        repo_targets = [
            RepositoryTarget(owner=org_name, name=repo_name)
            for repo_name in repo_names
        ]
        timestamped_print(
            f"Finished get_repos_by_language {time.time() - start_time:.2f} "
            f"seconds for {len(repo_targets)} repositories",
        )
    repo_iterator = tqdm(repo_targets)

    if args["sprint_analysis"] or args["plot_sprint"]:
        _handle_sprint_analysis(args, repo_iterator, start_time)
    else:
        _handle_individual_analysis(args, repo_iterator, start_time)


def _handle_sprint_analysis(
    args: CommandLineArgs,
    repo_iterator: tqdm,
    start_time: float,
) -> None:
    """Handle sprint analysis mode."""
    sprint_periods = calculate_sprint_periods(
        args["start_date"],
        args["end_date"],
    )
    sprint_stats: dict[str, dict[str, Any]] = {}

    process_context = ProcessRepositoriesContext(
        repositories=repo_iterator,
        start_date=args["start_date"],
        end_date=args["end_date"],
        start_time=start_time,
        sprint_stats=sprint_stats,
        sprint_periods=sprint_periods,
        use_cache=args["use_cache"],
    )
    process_repositories(process_context)

    team_metrics = calculate_sprint_team_metrics(sprint_stats)

    if args["output_path"]:
        export_sprint_csv(team_metrics, args["output_path"])
        print(f"Sprint analysis exported to {args['output_path']}")  # noqa: T201
    else:
        _print_sprint_summary(team_metrics)

    if args["plot_sprint"]:
        plotting_context = SprintPlottingContext(
            team_metrics=team_metrics,
            org_name=args["org_name"] or "",
            start_date=args["start_date"],
            end_date=args["end_date"],
            chart_type=args["chart_type"],
            chart_metrics=args["chart_metrics"],
            save_plot=args["save_plot"],
        )
        _handle_sprint_plotting(plotting_context)


def _handle_individual_analysis(
    args: CommandLineArgs,
    repo_iterator: tqdm,
    start_time: float,
) -> None:
    """Handle individual reviewer analysis mode."""
    process_context = ProcessRepositoriesContext(
        repositories=repo_iterator,
        start_date=args["start_date"],
        end_date=args["end_date"],
        start_time=start_time,
        use_cache=args["use_cache"],
    )
    reviewer_stats = process_repositories(process_context)
    calculate_reviewer_metrics(reviewer_stats)

    timestamped_print(
        f"Printing results {time.time() - start_time:.2f} seconds",
    )
    results_table = generate_results_table(reviewer_stats, args["metrics"])
    print(results_table)  # noqa: T201

    if args["plot_individual"]:
        _handle_individual_plotting(args, reviewer_stats)


def _handle_individual_plotting(
    args: CommandLineArgs,
    reviewer_stats: dict[str, dict[str, Any]],
) -> None:
    """Handle individual plotting functionality."""
    metric_display_name = SUPPORTED_INDIVIDUAL_METRICS.get(
        args["individual_chart_metric"],
        args["individual_chart_metric"],
    )

    org_name = args["org_name"] or "Organization"
    title = (
        f"{metric_display_name} Distribution - {org_name} | "
        f"{args['start_date'].date()} to {args['end_date'].date()}"
    ).strip()
    try:
        plot_individual_pie_chart(
            reviewer_stats=reviewer_stats,
            metric=args["individual_chart_metric"],
            title=title,
            save_path=args["save_plot"],
        )
    except Exception as e:  # noqa: BLE001
        print(f"Individual plotting failed: {e}")  # noqa: T201


def _print_sprint_summary(team_metrics: dict[str, dict[str, Any]]) -> None:
    """Print sprint summary to console."""
    print("Sprint Analysis Summary:")  # noqa: T201
    print("=" * 50)  # noqa: T201
    for sprint, sprint_metrics in team_metrics.items():
        print(f"\n{sprint}:")  # noqa: T201
        print(f"  Total Reviews: {sprint_metrics['total_reviews']}")  # noqa: T201
        print(f"  Total Comments: {sprint_metrics['total_comments']}")  # noqa: T201
        print(  # noqa: T201
            f"  Unique Reviewers: {sprint_metrics['unique_reviewers']}",
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


def _handle_sprint_plotting(context: SprintPlottingContext) -> None:
    """Handle sprint plotting functionality."""
    title = (
        f"Sprint Metrics for {context.org_name or ''} | "
        f"{context.start_date.date()} to {context.end_date.date()}"
    ).strip()
    try:
        plot_sprint_metrics(
            team_metrics=context.team_metrics,
            chart_type=context.chart_type,
            metrics=context.chart_metrics,
            title=title,
            save_path=context.save_plot,
        )
    except Exception as e:  # noqa: BLE001
        print(f"Plotting failed: {e}")  # noqa: T201


def _handle_cache_operations(args: CommandLineArgs) -> None:
    """Handle cache management operations."""
    cache_manager = CacheManager()

    if args["show_cache_stats"]:
        if cache_manager.cache:
            stats = cache_manager.cache.get_stats()
            print("Cache Statistics:")  # noqa: T201
            print(f"  Database path: {stats['db_path']}")  # noqa: T201
            print(f"  Total entries: {stats['total_entries']}")  # noqa: T201
            print(f"  Valid entries: {stats['valid_entries']}")  # noqa: T201
            print(f"  Expired entries: {stats['expired_entries']}")  # noqa: T201
            print(f"  Cache size: {stats['cache_size_mb']} MB")  # noqa: T201
            print(f"  Database size: {stats['db_size_mb']} MB")  # noqa: T201
            print("\nBy Table:")  # noqa: T201
            for table_name, table_stats in stats["by_table"].items():
                print(f"  {table_name}:")  # noqa: T201
                print(f"    Total: {table_stats['total']}")  # noqa: T201
                print(f"    Valid: {table_stats['valid']}")  # noqa: T201
                print(f"    Expired: {table_stats['expired']}")  # noqa: T201
                size_mb = table_stats["size_bytes"] / (1024 * 1024)
                print(f"    Size: {size_mb:.2f} MB")  # noqa: T201
        else:
            print("Cache is disabled")  # noqa: T201

    if args["clear_expired_cache"]:
        if cache_manager.cache:
            removed = cache_manager.cache.cleanup_expired()
            print(f"Cleared {removed} expired cache entries")  # noqa: T201
        else:
            print("Cache is disabled")  # noqa: T201

    if args["clear_cache"]:
        if cache_manager.cache:
            removed = cache_manager.cache.clear_all()
            print(f"Cleared all {removed} cache entries")  # noqa: T201
        else:
            print("Cache is disabled")  # noqa: T201


if __name__ == "__main__":
    main()
