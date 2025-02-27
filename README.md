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

## Options 

* -o, --organization The Github organization that you want to query
* -l, --languages  A comma separated list of languages that you want to include
* -s, --start-date The start date for the time frame that you want to query (optional)
* -e, --end-date The end date for the time frame that you want to query (optional)
* -h, --help Show this message and exit
* -v, --version Show the version of the tool