import os
import requests
from datetime import datetime

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN_PR_REVIEW")

def get_pull_requests_between_dates(owner: str, repo: str, start_date: str, end_date: str) -> list[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    params = {
        "state": "all",
        "sort": "updated",
        "direction": "desc",
        "per_page": 100
    }
    pull_requests = []
    page = 1

    while True:
        response = requests.get(url, headers=headers, params={**params, "page": page})
        response.raise_for_status()
        prs = response.json()
        if not prs:
            break
        for pr in prs:
            created_at = datetime.strptime(pr['created_at'], "%Y-%m-%dT%H:%M:%SZ")
            if start_date <= created_at <= end_date:
                pull_requests.append(pr)
        page += 1

    return pull_requests

if __name__ == '__main__':
    owner_name = "owner_name"
    repo_name = "repo_name"
    start_date = datetime.strptime("2023-01-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
    end_date = datetime.strptime("2023-12-31T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ")
    pull_requests = get_pull_requests_between_dates(owner_name, repo_name, start_date, end_date)
    for pr in pull_requests:
        print(f"ID: {pr['id']}, Title: {pr['title']}, Created At: {pr['created_at']}, URL: {pr['html_url']}")