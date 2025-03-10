import os

import requests

from reviewtally.queries import GRAPHQL_TIMEOUT
from reviewtally.queries.local_exceptions import (
    GitHubTokenNotDefinedError,
    NoGitHubOrgError,
)

# exceptions.py


def get_repos_by_language(org: str, languages: list[str]) -> list[str]:
    # check org and raise an exception if it is not defined
    if not org:
        raise NoGitHubOrgError(org)

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
        timeout=GRAPHQL_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    if data["data"]["organization"] is None:
        raise NoGitHubOrgError(org)
    # Filter repositories by language
    return [
        repo["name"]
        for repo in data["data"]["organization"]["repositories"]["nodes"]
        if not languages or any(
            node["name"].lower() in
                [language.lower() for language in languages]
            for node in repo["languages"]["nodes"])
    ]
