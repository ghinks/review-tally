from .queries.get_prs import get_pull_requests_between_dates

from .queries.get_repos_gql import get_repos_by_language
from pr_reviews.queries.local_exceptions import GitHubTokenNotDefinedError
from .queries.get_reviewers_rest import get_reviewers_for_pull_request
from tabulate import tabulate
from .cli.parse_cmd_line import parse_cmd_line



def main():
    # map containing the reviewer name and the number of pull requests reviewed
    reviewer_prs = {}
    org_name, start_date, end_date, language = parse_cmd_line()
    # repositories = get_org_repos(org_name)
    # get the repositories by language
    # catch the exception thrown if no github token is provided
    # in a try clause
    try:
        repositories = get_repos_by_language(org_name, language)
    except GitHubTokenNotDefinedError as e:
        print("Error:", e)
        return
    for repo in repositories:
        pull_requests = get_pull_requests_between_dates(
            org_name, repo["name"], start_date, end_date
        )
        for pr in pull_requests:
            reviewers = get_reviewers_for_pull_request(
                org_name, repo["name"], pr["number"]
            )
            for reviewer in reviewers:
                if reviewer["login"] in reviewer_prs:
                    reviewer_prs[reviewer["login"]] += 1
                else:
                    reviewer_prs[reviewer["login"]] = 1
    # convert the dictionary to a list of lists and print out with tabulate
    table = [[k, v] for k, v in reviewer_prs.items()]
    # convert the dictionary to a list of lists and sort by the number of PRs reviewed
    table = sorted(table, key=lambda x: x[1], reverse=True)
    print(tabulate(table))


if __name__ == "__main__":
    main()
