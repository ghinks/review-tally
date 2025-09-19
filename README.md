# review-tally

This tool is intended to retrieve a basic review count for the pull
requests for a GitHub organization in a given time frame. The default time
from is 2 weeks. The tool will retrieve statistics only on all repositories in
the specified organization unless there are specific languages specified.

This tool uses the GitHub API to retrieve the data. The tool requires that 
you have your GitHub token set as an environment variable. The environment
variable should be named `GITHUB_TOKEN`.

basic usage:
```bash
review-tally -o expressjs -l javascript
```
 
which would produce the following output

```shell
user                   total
---------------------  --
user1                  26
user2                  18
user3                  15
```
This output shows the number of reviews that each user has carried out in the
time period for the repositories that have python as a language specified.

A comma separated list of languages can be provided to filter the repositories
that are included in the statistics. If no languages are provided then all of
the repositories will be included in the statistics.

multiple languages:
```bash
review-tally -o crossplane -l python,go
```

All languages:
```bash
review-tally -o expressjs
```

Specifying the time frame:
```bash
review-tally -o expressjs -l javascript -s 2021-01-01 -e 2021-01-31
```

Customizing metrics displayed:
```bash
review-tally -o expressjs -l javascript -m reviews,engagement,thoroughness
```

## Sprint Analysis
If aggregate data is required sprint over sprint then the `--sprint-analysis`
option can be used. This will produce a CSV file with the data for each sprint.

```shell
review-tally -o expressjs -l javascript --sprint-analysis --output-path sprint_analysis.csv
```

## Sprint Plotting
The tool can generate interactive charts showing sprint metrics over time. You can use `--plot-sprint` to create visualizations that open in your browser.

### Basic plotting (automatically enables sprint analysis):
```shell
review-tally -o expressjs -l javascript --plot-sprint
```

### Plotting with custom chart type and metrics:
```shell
review-tally -o expressjs -l javascript --plot-sprint --chart-type line --chart-metrics total_reviews,unique_reviewers
```

### Saving the plot to a file:
```shell
review-tally -o expressjs -l javascript --plot-sprint --save-plot sprint_metrics.html
```

### Combining with CSV export:
```shell
review-tally -o expressjs -l javascript --sprint-analysis --plot-sprint --output-path sprint_data.csv
```


## Options

* -o, --organization The Github organization that you want to query
* -l, --languages  A comma separated list of languages that you want to include
* -s, --start-date The start date for the time frame that you want to query (optional)
* -e, --end-date The end date for the time frame that you want to query (optional)
* -m, --metrics Comma-separated list of metrics to display (reviews,comments,avg-comments,engagement,thoroughness). Default: reviews,comments,avg-comments
* -h, --help Show this message and exit
* -v, --version Show the version of the tool
* --sprint-analysis selects the sprint analysis option
* --output-path specifices the output file for sprint analysis
* --plot-sprint Generate interactive charts showing sprint metrics (opens in browser)
* --chart-type Chart type for sprint metrics (bar or line). Default: bar
* --chart-metrics Comma-separated sprint metrics to plot. Default: total_reviews,total_comments. Available: total_reviews,total_comments,unique_reviewers,avg_comments_per_review,reviews_per_reviewer,avg_response_time_hours,avg_completion_time_hours,active_review_days
* --save-plot Optional path to save the interactive HTML chart
* --no-cache Disable PR review caching (always fetch fresh data from API). By default, caching is enabled for better performance.

## GitHub API Rate Limiting

This tool uses GitHub's REST and GraphQL APIs extensively to gather pull request and review data. GitHub enforces rate limits to ensure fair usage of their API resources.

### Rate Limit Information

GitHub API rate limits vary depending on your authentication method:

- **Personal Access Token**: 5,000 requests per hour
- **GitHub App**: 15,000 requests per hour (per installation)
- **OAuth App**: 5,000 requests per hour (per user)

For GraphQL API:
- **Personal Access Token**: 5,000 points per hour (each query has a different point cost)

### Checking Your Current Rate Limit

You can check your current rate limit status using curl:

```bash
# Check REST API rate limit
curl -H "Authorization: Bearer YOUR_GITHUB_TOKEN" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/rate_limit

# Check GraphQL API rate limit
curl -H "Authorization: Bearer YOUR_GITHUB_TOKEN" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/rate_limit | jq '.resources.graphql'
```

Replace `YOUR_GITHUB_TOKEN` with your actual GitHub personal access token.

### Rate Limiting Best Practices

- **Use caching**: This tool includes built-in caching (enabled by default) to reduce API calls
- **Smaller time ranges**: Process smaller date ranges to avoid hitting limits on large organizations
- **Monitor usage**: Use the curl commands above to monitor your rate limit consumption
- **GitHub Apps**: Consider using a GitHub App for higher rate limits if processing very large datasets

### Useful Links

- [GitHub REST API Rate Limiting](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [GitHub GraphQL API Rate Limiting](https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api)
- [Creating a Personal Access Token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [GitHub Apps vs Personal Access Tokens](https://docs.github.com/en/apps/creating-github-apps/about-github-apps/about-github-apps)