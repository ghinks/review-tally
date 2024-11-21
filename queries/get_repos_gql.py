import os
import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_repos_by_language(org: str, language: str) -> list[dict]:
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
    variables = {
        "org": org
    }
    response = requests.post(url, headers=headers, json={"query": query, "variables": variables})
    response.raise_for_status()
    data = response.json()
    # Filter repositories by language
    repos = []
    # check that language is defined and if not return all repositories
    if language is None:
        for repo in data["data"]["organization"]["repositories"]["nodes"]:
            repos.append(repo)
    else:
        for repo in data["data"]["organization"]["repositories"]["nodes"]:
            for lang in repo["languages"]["nodes"]:
                if lang["name"].lower() == language.lower():
                    repos.append(repo)
                    break
    return repos
