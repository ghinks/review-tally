# pr-reviews

For a github organization get the pull requests reviews for all repositories 
within a time range and produce a table with the reviewers and the number of
PRs reviewed by them.

A very linear approach is being taken
- query the org to get the repositories
- query the repositories to get the pull requests
- query the pull requests to get the reviews
- count the reviews by reviewer 
- present a an ordered table of the reviewers and the number of reviews

## Usage

```shell
python pr_reviews.py --org "my-org" --start-date "2021-01-01" --end-date "2021-12-31"
```

This program uses your local environment to authenticate with github using the
GITHUB_TOKEN environment variable.

## Development

### linting
```shell
poetry run black .
```