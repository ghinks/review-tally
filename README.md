# pr-reviews

This tool is intended to retrieve basic statics about the reviews of pull
requests for a GitHub organization in a given time frame. The default time
from is 2 weeks. The tool will retrieve statistics only on repositories that
have specific languages when specified.

basic usage:
```bash
github_review_counter -o kubernetes -l python
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

The authors intent is to provide basic statistics about who is carrying out 
reviews over a period of time so that the organization can better understand
who is contributing to the review process.

A comma separated list of languages can be provided to filter the repositories
that are included in the statistics. If no languages are provided then all of
the repositories will be included in the statistics.

multiple languages:
```bash
github_review_counter -o kubernetes -l python,go
```

All languages:
```bash
github_review_counter -o kubernetes
```

Specifying the time frame:
```bash
github_review_counter -o kubernetes -l python -s 2021-01-01 -e 2021-01-31
```

## Options 

* -o, --organization The Github organization that you want to query
* -l, --languages  A comma separated list of languages that you want to include
* -s, --start-date The start date for the time frame that you want to query (optional)
* -e, --end-date The end date for the time frame that you want to query (optional)
* -h, --help Show this message and exit