from queries.get_prs import get_pull_requests_between_dates
from queries.get_repos_rest import get_org_repos
from datetime import datetime
from queries.get_reviewers_rest import get_reviewers_for_pull_request
from tabulate import tabulate
from cli.parse_cmd_line import parse_cmd_line

if __name__ == "__main__":
    # map containing the reviewer name and the number of pull requests reviewed
    reviewer_prs = {}
    org_name, start_date, end_date = parse_cmd_line()
    repositories = get_org_repos(org_name)
    for repo in repositories:
        # print(f"Name: {repo['name']}, URL: {repo['html_url']}")
        start_date = datetime.strptime("2024-11-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        end_date = datetime.strptime("2024-12-01T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ")
        pull_requests = get_pull_requests_between_dates(
            org_name, repo["name"], start_date, end_date
        )
        for pr in pull_requests:
            # print(f"ID: {pr['id']}, Title: {pr['title']}, Created At: {pr['created_at']}, URL: {pr['html_url']}")
            reviewers = get_reviewers_for_pull_request(
                org_name, repo["name"], pr["number"]
            )
            for reviewer in reviewers:
                # print(f"Reviewer: {reviewer['login']}, URL: {reviewer['html_url']}")
                if reviewer["login"] in reviewer_prs:
                    reviewer_prs[reviewer["login"]] += 1
                else:
                    reviewer_prs[reviewer["login"]] = 1
    # convert the dictionary to a list of lists and print out with tabulate
    table = [[k, v] for k, v in reviewer_prs.items()]
    print(tabulate(table))
