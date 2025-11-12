# Release Notes - v0.5.4

## What's Changed

### Bug Fixes
* **Fail fast on invalid repositories (#174)**: The tool now validates repository existence before processing, providing immediate feedback when a repository is not found or inaccessible. This prevents wasted API calls and gives users clearer error messages with HTTP status codes.
* **Improved HTTP error handling**: Enhanced error handling in PR request processing to better distinguish between retryable errors (network issues) and non-retryable errors (404, 422), preventing unnecessary retry attempts on permanent failures.

### Improvements
* **Refined retry logic**: Removed rate limiting from retryable status codes for cleaner error handling flow.
* **Code quality**: Updated ruff linting to comply with line length standards.

## Technical Details

The main improvements in this release focus on robustness and fail-fast behavior:

- Repository validation now happens upfront using the GitHub REST API
- HTTP errors with status codes 404 and 422 now fail immediately instead of retrying
- Better separation between connection errors (retryable) and client errors (non-retryable)
- Improved error messages that include HTTP status codes for easier debugging

## Commits Since v0.5.3
- Working with Windsurf for issue #174 (6178de6)
- lint/ruff line lengths (f169c04)
- remove rate limiting from retryable status codes (d9786b6)
- Merge pull request #177 from ghinks/feat/fail-fast-invalid-repo-174 (4c8cb9e)

**Full Changelog**: https://github.com/ghinks/review-tally/compare/v0.5.3...v0.5.4
