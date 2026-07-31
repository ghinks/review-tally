# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Review-tally is a Python CLI tool (version 0.5.6) that analyzes GitHub pull request review activity for organizations or specific repositories. It queries GitHub's REST and GraphQL APIs to collect data about PR reviews, generates reviewer statistics, supports sprint-based team metrics, and produces tabular and interactive Plotly visualizations.

## Development Commands

### Setup and Dependencies
```bash
# Install dependencies using Poetry (Python 3.11+ required)
poetry install

# Activate virtual environment
poetry shell

# Install pre-commit hooks (one-time setup)
pre-commit install
```

### Code Quality and Testing
```bash
# Run all non-integration tests
poetry run pytest -m "not integration"

# Run all tests including integration tests
poetry run pytest

# Run specific test directory
poetry run pytest tests/get_reviewers/
poetry run pytest tests/analysis/
poetry run pytest tests/cache/

# Lint code with ruff
poetry run ruff check .

# Format code with ruff
poetry run ruff format .

# Type checking with mypy
poetry run mypy reviewtally/

# Sort imports with isort
poetry run isort .

# Run pre-commit hooks manually on all files (runs ruff-check)
poetry run pre-commit run --all-files
```

### Running the Application
```bash
# Run by organization and language
review-tally -o <organization> -l <languages>

# Run against specific repositories (via config file)
review-tally -c config.toml

# Example usage
review-tally -o expressjs -l javascript
review-tally -o crossplane -l python,go

# Sprint analysis with CSV export
review-tally -o myorg -l go --sprint-analysis --output-path results.csv

# Interactive Plotly chart in browser
review-tally -o myorg -l python --plot-sprint
review-tally -o myorg -l python --plot-individual --individual-chart-metric reviews

# Cache management
review-tally --cache-stats
review-tally --clear-expired-cache
review-tally --clear-cache

# Show version
review-tally --version
```

## Code Architecture

### Directory Structure
```
reviewtally/
├── main.py                    # Entry point, orchestrates all analysis modes
├── data_collection.py         # Core data collection and aggregation logic
├── metrics_calculation.py     # Individual reviewer metric computations
├── output_formatting.py       # Tabular output generation with tabulate
├── cli/
│   └── parse_cmd_line.py      # CLI argument parsing, config loading, TypedDict
├── queries/
│   ├── __init__.py            # Timeouts, retries, SSL config, URL builders
│   ├── get_repos_gql.py       # GraphQL: fetch repositories by language
│   ├── get_prs.py             # REST: fetch PRs within date range
│   └── get_reviewers_rest.py  # Async REST: fetch reviews and comments
├── analysis/
│   ├── sprint_periods.py      # 14-day sprint period calculations
│   └── team_metrics.py        # Sprint-level team metric aggregation
├── cache/
│   ├── __init__.py            # TTL threshold constants
│   ├── cache_manager.py       # High-level cache interface (singleton)
│   └── sqlite_cache.py        # SQLite-backed TTL cache implementation
├── exporters/
│   └── sprint_export.py       # CSV export for sprint metrics
├── visualization/
│   ├── individual_plot.py     # Plotly pie charts for individual reviewer metrics
│   └── sprint_plot.py         # Plotly bar/line charts for sprint metrics
└── exceptions/
    └── local_exceptions.py    # Custom exceptions for API/validation errors
tests/
├── analysis/                  # Tests for sprint_periods and team_metrics
├── cache/                     # Tests for cache date range logic
├── cli/                       # Tests for CLI argument parsing
├── get_reviewers/             # Async tests for reviewer REST fetching
├── integration/               # Integration tests (run separately with -m integration)
├── queries/                   # Tests for GitHub host URL building
├── fixtures/                  # JSON fixture files for API responses
└── test_get_prs.py            # Tests for PR fetching
```

### Core Components

**Main Entry Point** (`reviewtally/main.py`):
- Parses CLI args and configures the GitHub host
- Routes between two primary modes: individual analysis and sprint analysis
- Handles cache management operations (show stats, clear, clear expired) as early exits
- Validates repository targets via REST API when `--repositories` config key is used

**CLI Interface** (`reviewtally/cli/parse_cmd_line.py`):
- `CommandLineArgs` TypedDict defines all CLI arguments with types
- Supports both CLI flags and a TOML config file (`-c config.toml`)
- Config file keys use kebab-case (e.g., `github-host`, `start-date`)
- Mutual exclusivity: `--plot-sprint` and `--plot-individual` cannot be combined
- Default date range: last 14 days if not specified

**API Query Modules** (`reviewtally/queries/`):
- `__init__.py` — shared constants: `GENERAL_TIMEOUT=60s`, `REVIEWERS_TIMEOUT=900s`, `MAX_RETRIES=10`, exponential backoff (`BACKOFF_MULTIPLIER=2.0`, `MAX_BACKOFF=600s`), connection pool settings, `MAX_PR_COUNT=100000`; URL builders `build_github_rest_api_url()` and `get_github_graphql_url()`; `set_github_host()` for GitHub Enterprise support
- `get_repos_gql.py` — GraphQL query to discover repos by language within an org
- `get_prs.py` — paginated REST API to fetch PRs in a date range with cache integration
- `get_reviewers_rest.py` — async aiohttp-based fetching of reviews and review comments per PR, with cache integration

**Data Collection** (`reviewtally/data_collection.py`):
- `process_repositories()` — iterates repos, fetches PRs, then calls `collect_review_data()`
- `collect_review_data()` — batches PRs (`BATCH_SIZE=5`), fetches reviewers, accumulates `reviewer_stats` and optionally `sprint_stats`
- Uses dataclasses: `RepositoryTarget`, `ProcessRepositoriesContext`, `ReviewDataContext`, `SprintPlottingContext`
- `DEBUG_FLAG=False` — set to `True` to enable timestamped debug prints

**Metrics Calculation** (`reviewtally/metrics_calculation.py`):
- `calculate_reviewer_metrics()` — computes per-reviewer: engagement level (High/Medium/Low), thoroughness score (0-100), avg response time, avg completion time, active review days
- Engagement thresholds: High ≥ 2.0 avg comments/review, Medium ≥ 0.5

**Sprint Analysis** (`reviewtally/analysis/`):
- `sprint_periods.py` — generates 14-day sprint windows with `YYYY-MM-DD` labels
- `team_metrics.py` — aggregates sprint data: total reviews/comments, unique reviewers, avg comments/review, reviews/reviewer, team engagement, time metrics

**Output Formatting** (`reviewtally/output_formatting.py`):
- `generate_results_table()` — builds tabulate table sorted by reviews (desc), then comments (desc)
- Available metrics for `-m` flag: `reviews`, `comments`, `avg-comments`, `engagement`, `thoroughness`, `response-time`, `completion-time`, `active-days`

**Caching** (`reviewtally/cache/`):
- SQLite database at `~/.review-tally-cache/api_cache.db`
- Two tables: `pr_reviews_cache` (PR review data), `pr_metadata_cache` (PR metadata)
- TTL strategy: open PRs expire in 1 hour; PRs < 7 days old expire in 1 hour; PRs 7–30 days old expire in 6 hours; PRs > 30 days old never expire
- Cache automatically disabled during pytest (`PYTEST_CURRENT_TEST` env var) and when `REVIEW_TALLY_DISABLE_CACHE=1`
- Global singleton via `get_cache_manager()`

**Visualization** (`reviewtally/visualization/`):
- `individual_plot.py` — Plotly pie chart for one reviewer metric across all reviewers; opens in browser; slices < 3% suppressed
- `sprint_plot.py` — Plotly bar or line chart for sprint metrics over time; opens in browser
- Both support `--save-plot <path.html>` for saving interactive HTML

**Exceptions** (`reviewtally/exceptions/local_exceptions.py`):
- `GitHubTokenNotDefinedError`, `HTTPErrorBadTokenError`, `LoginNotFoundError`, `NoGitHubOrgError`, `MalformedDateError`, `PaginationError`

### Data Flow

**Individual Analysis Mode** (default):
1. Repository Discovery: GraphQL filters repos by language OR use configured `repositories` list
2. PR Collection: REST API fetches merged/closed PRs within date range per repo (cached)
3. Review Fetching: Async batch processing (batches of 5) fetches reviews and comments per PR (cached)
4. Metrics Calculation: `calculate_reviewer_metrics()` computes derived stats per reviewer
5. Output: Tabular display via tabulate; optional Plotly pie chart

**Sprint Analysis Mode** (`--sprint-analysis` or `--plot-sprint`):
1. Same repo/PR/review collection as individual mode
2. Reviews are bucketed into 14-day sprint periods by `submitted_at` timestamp
3. Team-level metrics aggregated per sprint by `calculate_sprint_team_metrics()`
4. Output: Console summary or CSV (`--output-path`) or interactive Plotly chart (`--plot-sprint`)

### Key Design Patterns

- **Async Processing**: `get_reviewers_rest.py` uses aiohttp with connection pooling for concurrent API calls
- **Batching**: PR review requests are batched (`BATCH_SIZE=5`) to manage API rate limits
- **Retry Logic**: Exponential backoff (max 10 retries) for transient HTTP 5xx errors
- **Caching**: SQLite with TTL-based expiration; disabled automatically during tests
- **GitHub Enterprise Support**: `set_github_host()` + `--github-host` flag with embedded path extraction
- **Config File**: TOML config via `-c config.toml` for all CLI options
- **Context Objects**: Dataclasses used as context objects to reduce function parameter count
- **Progress Tracking**: tqdm progress bar over repo iteration

## Configuration

### Environment Variables
- `GITHUB_TOKEN` — Required GitHub personal access token
- `HTTPS_PROXY` / `https_proxy` — Optional proxy configuration
- `REVIEW_TALLY_DISABLE_CACHE` — Set to `1`, `true`, or `yes` to disable caching

### TOML Config File (optional, `-c config.toml`)
```toml
org = "myorg"
start-date = "2024-01-01"
end-date = "2024-03-31"
languages = ["python", "go"]
metrics = ["reviews", "comments", "avg-comments"]
github-host = "github.mycompany.com"
github-rest-path = "/api/v3"
github-graphql-path = "/api/graphql"
repositories = ["owner/repo1", "owner/repo2"]
sprint-analysis = false
plot-sprint = false
plot-individual = false
chart-type = "bar"
chart-metrics = ["total-reviews", "total-comments"]
individual-chart-metric = "reviews"
save-plot = "output.html"
output-path = "sprint.csv"
no-cache = false
```

### Code Style (Ruff Configuration)
- Line length: 79 characters
- All ruff rules enabled (`select = ["ALL"]`)
- Ignored: `D100-D103` (missing docstrings), `D203`, `D212`
- Test files also ignore: `S101` (assert), `PT009`, `PT027`, `ANN401`
- Integration tests also ignore: `C901`, `PLR0912`, `S603`, `T201`
- Excluded from linting: `reviewtally/**/__init__.py`, `tests/__init__.py`, `tests/get_reviewers/__init__.py`
- Pre-commit hook: ruff-check only (via `.pre-commit-config.yaml`)

### Testing Configuration
- pytest asyncio mode: `auto` (all async tests run automatically)
- Required plugin: `pytest-asyncio`
- Integration tests: marked with `@pytest.mark.integration`, excluded from CI unit test run
- Cache is automatically disabled during all pytest runs
- Fixture JSON files: `tests/fixtures/` (reviews, comments, edge cases)

## CI/CD

### GitHub Actions (`ci.yml`)
Runs on pull requests and manual dispatch:
- Matrix: `[windows-latest, ubuntu-latest, macos-latest]` × `[3.11, 3.12, 3.13]`
- Steps: ruff check → mypy → pytest (non-integration) → poetry build

### Publishing (`publish.yml`)
Automated PyPI publishing workflow (separate from CI).

## Available CLI Metrics

### Individual Analysis (`-m` flag)
| Flag Value        | Description                              |
|-------------------|------------------------------------------|
| `reviews`         | Total review count (default)             |
| `comments`        | Total review comment count (default)     |
| `avg-comments`    | Average comments per review (default)    |
| `engagement`      | High/Medium/Low engagement level         |
| `thoroughness`    | Thoroughness score 0-100                 |
| `response-time`   | Avg time from PR open to first review    |
| `completion-time` | Span from first to last review           |
| `active-days`     | Number of distinct days with reviews     |

### Individual Pie Chart (`--individual-chart-metric`)
Same set as above (use hyphen form via CLI, e.g., `response-time`).

### Sprint Chart (`--chart-metrics`)
`total-reviews`, `total-comments`, `unique-reviewers`, `avg-comments-per-review`, `reviews-per-reviewer`, `avg-response-time-hours`, `avg-completion-time-hours`, `active-review-days`

## Important Notes

- The tool requires a valid GitHub token (`GITHUB_TOKEN`) with `repo` read scope
- API timeout values are configured in `reviewtally/queries/__init__.py`
- All dates are handled in UTC timezone; timestamps use `%Y-%m-%dT%H:%M:%SZ` format
- Proxy support is built-in: aiohttp and requests both honor `HTTPS_PROXY`/`https_proxy`
- Repositories with > 100,000 PRs (`MAX_PR_COUNT`) are skipped to avoid runaway fetching
- `--plot-sprint` and `--plot-individual` are mutually exclusive
- Sprint periods are fixed at 14 days, labeled by their start date (`YYYY-MM-DD`)
- The `submitted_at` field on GitHub review objects can occasionally be `null`; such reviews are excluded from time-based metrics with a warning printed to stdout
- Cache database is stored at `~/.review-tally-cache/api_cache.db` and persists between runs
