import os
import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN_PR_REVIEW")

def get_reviewers_for_pull_request(owner: str, repo: str, pull_number: int) -> list[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    reviews = response.json()
    reviewers = [review['user'] for review in reviews]
    return reviewers

# if __name__ == '__main__':
#     owner_name = "owner_name"
#     repo_name = "repo_name"
#     pull_number = 1  # Replace with the actual pull request number
#     reviewers = get_reviewers_for_pull_request(owner_name, repo_name, pull_number)
#     for reviewer in reviewers:
#         print(f"Reviewer: {reviewer['login']}, URL: {reviewer['html_url']}")