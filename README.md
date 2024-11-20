# pr-reviews

For a github organization get the pull requests reviews for a repository 
within a time range and produce a table with the reviewers and the number of
PRs reviewed by them.

A very linear approach is being taken
- query the org to get the repositories
- query the repositories to get the pull requests
- query the pull requests to get the reviews
- count the reviews by reviewer 

## Development

### linting
```shell
poetry run black .
```