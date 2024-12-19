import os
import requests

from pr_reviews.queries.local_exceptions import GitHubTokenNotDefinedError

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# exceptions.py


def get_repos_by_language(org: str, languages: list[str]) -> list[str]:
    # check for github_token and raise an exception if it
    # is not defined
    if GITHUB_TOKEN is None:
        raise GitHubTokenNotDefinedError("GITHUB_TOKEN is not defined")
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
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
        url, headers=headers, json={"query": query, "variables": variables}
    )
    response.raise_for_status()
    data = response.json()
    # Filter repositories by language
    repo_names = [
        repo["name"]
        for repo in data["data"]["organization"]["repositories"]["nodes"]
        for node in repo["languages"]["nodes"]
        if node["name"].lower() in [language.lower() for language in languages]
    ]
    return repo_names
