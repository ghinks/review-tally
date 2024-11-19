#from queries.get_repos_gql import get_repos_gql
from queries.get_prs import get_pull_requests_between_dates
from queries.get_repos_rest import get_org_repos
from datetime import datetime
def test_get_prs():
    owner_name = "expressjs"
    repo_name = "express"
    start_date = datetime.strptime("2023-01-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
    end_date = datetime.strptime("2024-12-31T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ")
    pull_requests = get_pull_requests_between_dates(owner_name, repo_name, start_date, end_date)
    for pr in pull_requests:
        print(f"ID: {pr['id']}, Title: {pr['title']}, Created At: {pr['created_at']}, URL: {pr['html_url']}")

if __name__ == '__main__':
    org_name = "expressjs"
    #orgs_repos = get_repos_gql(org_name)
    # repositories = get_org_repos(org_name)
    # for repo in repositories:
    #     print(f"Name: {repo['name']}, URL: {repo['html_url']}")
    test_get_prs()