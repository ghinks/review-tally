#from queries.get_repos_gql import get_repos_gql
from queries.get_prs import get_pull_requests_between_dates
from queries.get_repos_rest import get_org_repos
from datetime import datetime
from queries.get_reviewers_rest import get_reviewers_for_pull_request
def test_get_prs():
    owner_name = "expressjs"
    repo_name = "express"
    start_date = datetime.strptime("2023-01-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
    end_date = datetime.strptime("2024-12-31T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ")
    pull_requests = get_pull_requests_between_dates(owner_name, repo_name, start_date, end_date)
    for pr in pull_requests:
        print(f"ID: {pr['id']}, Title: {pr['title']}, Created At: {pr['created_at']}, URL: {pr['html_url']}")

def test_get_reviewers():
    owner_name = "expressjs"
    repo_name = "express"
    pull_number = 6141  # Replace with the actual pull request number
    reviewers = get_reviewers_for_pull_request(owner_name, repo_name, pull_number)
    for reviewer in reviewers:
        print(f"Reviewer: {reviewer['login']}, URL: {reviewer['html_url']}")

if __name__ == '__main__':
    # map containing the reviewer name and the number of pull requests reviewed
    reviewer_prs = {}
    org_name = "expressjs"
    repositories = get_org_repos(org_name)
    for repo in repositories:
        #print(f"Name: {repo['name']}, URL: {repo['html_url']}")
        start_date = datetime.strptime("2024-11-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        end_date = datetime.strptime("2024-12-01T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ")
        pull_requests = get_pull_requests_between_dates(org_name, repo['name'], start_date, end_date)
        for pr in pull_requests:
            #print(f"ID: {pr['id']}, Title: {pr['title']}, Created At: {pr['created_at']}, URL: {pr['html_url']}")
            reviewers = get_reviewers_for_pull_request(org_name, repo['name'], pr['number'])
            for reviewer in reviewers:
                #print(f"Reviewer: {reviewer['login']}, URL: {reviewer['html_url']}")
                if reviewer['login'] in reviewer_prs:
                    reviewer_prs[reviewer['login']] += 1
                else:
                    reviewer_prs[reviewer['login']] = 1
    print(reviewer_prs)