import os
import requests
from datetime import datetime

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def get_pull_requests_between_dates(
    owner: str, repo: str, start_date: str, end_date: str
) -> list[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    params = {"state": "all", "sort": "updated", "direction": "desc", "per_page": 100}
    pull_requests = []
    page = 1

    while True:
        response = requests.get(url, headers=headers, params={**params, "page": page})
        response.raise_for_status()
        prs = response.json()
        if not prs:
            break
        for pr in prs:
            created_at = datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            if start_date <= created_at <= end_date:
                pull_requests.append(pr)
        page += 1

    return pull_requests
