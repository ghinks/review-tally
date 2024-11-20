import os
import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN_PR_REVIEW")


def get_org_repos(org: str) -> list[dict]:
    url = f"https://api.github.com/orgs/{org}/repos"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    repos = []
    params = {"per_page": 100, "page": 1}

    while True:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        repos.extend(data)
        if "next" in response.links:
            params["page"] += 1
        else:
            break

    return repos
