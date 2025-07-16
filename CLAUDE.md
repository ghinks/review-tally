# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Review-tally is a Python CLI tool that analyzes GitHub pull request review activity for organizations. It queries GitHub's REST and GraphQL APIs to collect data about PR reviews across repositories within an organization, then generates statistics showing who has been reviewing PRs and how frequently.

## Development Commands

### Setup and Dependencies
```bash
# Install dependencies using Poetry
poetry install

# Activate virtual environment
poetry shell

# Install pre-commit hooks (one-time setup)
pre-commit install
```

### Code Quality and Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_get_prs.py

# Run tests with asyncio support (configured in pyproject.toml)
pytest tests/get_reviewers/

# Lint code with ruff
ruff check .

# Format code with ruff
ruff format .

# Type checking with mypy
mypy reviewtally/

# Sort imports with isort
isort .

# Run pre-commit hooks manually on all files
pre-commit run --all-files
```

### Running the Application
```bash
# Install in development mode
poetry install

# Run the CLI tool
review-tally -o <organization> -l <languages>

# Example usage
review-tally -o expressjs -l javascript
review-tally -o crossplane -l python,go
```

## Code Architecture

### Core Components

**Main Entry Point**: `reviewtally/main.py`
- Contains the main execution flow and orchestrates all API calls
- Handles progress tracking with tqdm
- Processes results and generates tabulated output

**CLI Interface**: `reviewtally/cli/parse_cmd_line.py`
- Argument parsing with argparse
- Date validation and timezone handling
- Language filtering support

**API Query Modules**: `reviewtally/queries/`
- `get_repos_gql.py` - Uses GraphQL to fetch repositories by language
- `get_prs.py` - REST API calls to get pull requests within date ranges
- `get_reviewers_rest.py` - Async REST API calls to fetch review data
- `local_exceptions.py` - Custom exceptions for API errors

### Data Flow

1. **Repository Discovery**: GraphQL query filters repos by specified languages
2. **PR Collection**: REST API fetches PRs within the date range for each repo
3. **Review Fetching**: Async batch processing collects review data (batches of 5)
4. **Data Aggregation**: Review counts are tallied per user across all repos
5. **Output Generation**: Results are sorted and displayed in tabular format

### Key Design Patterns

- **Async Processing**: `get_reviewers_rest.py` uses aiohttp for concurrent API calls
- **Batching**: PR review requests are batched (BATCH_SIZE = 5) to manage API rate limits
- **Error Handling**: Custom exceptions for GitHub token, organization, and login errors
- **Progress Tracking**: tqdm provides visual feedback during long-running operations

## Configuration

### Environment Variables
- `GITHUB_TOKEN` - Required GitHub personal access token
- `HTTPS_PROXY` / `https_proxy` - Optional proxy configuration

### Code Style (Ruff Configuration)
- Line length: 79 characters
- Comprehensive linting with ALL rules enabled
- Specific ignores for docstring requirements (D100-D103, D203, D212)
- Security rule S101 ignored for test files
- Excludes __init__.py files from linting

### Testing Configuration
- pytest with asyncio mode enabled
- pytest-asyncio plugin required
- Async test fixtures in `tests/fixtures/`
- Separate test modules for different components

## Important Notes

- The tool requires a valid GitHub token with appropriate permissions
- API timeout values are configured in `reviewtally/queries/__init__.py`
- The application handles both REST and GraphQL GitHub APIs
- Proxy support is built-in for corporate environments
- All dates are handled in UTC timezone