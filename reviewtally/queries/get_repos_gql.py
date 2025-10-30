from __future__ import annotations

import sys

import requests

from reviewtally.exceptions.local_exceptions import (
    GitHubTokenNotDefinedError,
    HTTPErrorBadTokenError,
    NoGitHubOrgError,
)
from reviewtally.queries import (
    GRAPHQL_TIMEOUT,
    MAX_PR_COUNT,
    build_github_api_url,
    require_github_token,
)

# exceptions.py


def get_repos_by_language(org: str, languages: list[str]) -> list[str]:
    # check org and raise an exception if it is not defined
    if not org:
        raise NoGitHubOrgError(org)

    # check for github_token and raise an exception if it
    # is not defined
    github_token = require_github_token()
    url = build_github_api_url("graphql")
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
            pullRequests {
              totalCount
            }
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

    # Filter repositories by language and PR count
    filtered_repos = []
    for repo in data["data"]["organization"]["repositories"]["nodes"]:
        # Check language filter
        if languages and not any(
            node["name"].lower()
            in [language.lower() for language in languages]
            for node in repo["languages"]["nodes"]
        ):
            continue

        # Check PR count threshold
        pr_count = repo["pullRequests"]["totalCount"]
        if pr_count > MAX_PR_COUNT:
            print(  # noqa: T201
                f"Warning: Skipping repository '{repo['name']}' "
                f"with {pr_count} PRs (exceeds threshold of {MAX_PR_COUNT})",
            )
            continue

        filtered_repos.append(repo["name"])

    return filtered_repos


def get_repos(
    org_name: str,
    languages: list[str],
) -> list[str] | None:
    try:
        return list(get_repos_by_language(org_name, languages))
    except requests.exceptions.HTTPError as e:
        print(HTTPErrorBadTokenError(f"{e}"))  # noqa: T201
        sys.exit(1)
    except GitHubTokenNotDefinedError as e:
        print("Error:", e)  # noqa: T201
        return None
    except NoGitHubOrgError as e:
        print("Error:", e)  # noqa: T201
        return None
