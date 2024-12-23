import os

import requests

from pr_reviews.queries import TIMEOUT
from pr_reviews.queries.local_exceptions import GitHubTokenNotDefinedError

# exceptions.py


def get_repos_by_language(org: str, languages: list[str]) -> list[str]:
    # check for github_token and raise an exception if it
    # is not defined

    github_token = os.getenv("GITHUB_TOKEN")

    if github_token is None:
        raise GitHubTokenNotDefinedError
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Content-Type": "application/json",
    }
    query = """
    query($org: String!) {
      organization(login: $org) {
        repositories(first: 100) {
          nodes {
            name
            languages(first: 10) {
              nodes {
                name
              }
            }
          }
        }
      }
    }
    """
    variables = {"org": org}
    response = requests.post(
        url,
        headers=headers,
        json={"query": query, "variables": variables},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    # Filter repositories by language
    return [
        repo["name"]
        for repo in data["data"]["organization"]["repositories"]["nodes"]
        if not languages or any(
            node["name"].lower() in
                [language.lower() for language in languages]
            for node in repo["languages"]["nodes"])
    ]
