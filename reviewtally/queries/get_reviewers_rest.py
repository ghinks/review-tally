import asyncio
import os
from typing import Any

import aiohttp

from reviewtally.queries import AIOHTTP_TIMEOUT

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# get proxy settings from environment variables
HTTPS_PROXY = os.getenv("HTTPS_PROXY")
# check for lowercase https_proxy
if not HTTPS_PROXY:
    HTTPS_PROXY = os.getenv("https_proxy")


async def fetch(client: aiohttp.ClientSession, url: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    if HTTPS_PROXY:
        async with client.get(url,
                              headers=headers,
                              proxy=HTTPS_PROXY) as response:
            return await response.json()
    else:
        async with client.get(url, headers=headers) as response:
            return await response.json()


async def fetch_batch(urls: list[str]) -> tuple[Any]:
    async with aiohttp.ClientSession(timeout=AIOHTTP_TIMEOUT) as session:
        tasks = [fetch(session, url) for url in urls]
        return await asyncio.gather(*tasks)  # type: ignore[return-value]



def get_reviewers_for_pull_requests(
    owner: str, repo: str, pull_numbers: list[int],
) -> list[dict]:
    urls = [
        f"https://api.github.com/repos/{owner}/{repo}"
        f"/pulls/{pull_number}/reviews"
        for pull_number in pull_numbers
    ]
    reviewers = asyncio.run(fetch_batch(urls))
    return [item["user"] for sublist in reviewers for item in sublist]


def get_reviewers_with_comments_for_pull_requests(
    owner: str, repo: str, pull_numbers: list[int],
) -> list[dict]:
    # First, get all reviews for the pull requests
    review_urls = [
        f"https://api.github.com/repos/{owner}/{repo}"
        f"/pulls/{pull_number}/reviews"
        for pull_number in pull_numbers
    ]
    reviews_response = asyncio.run(fetch_batch(review_urls))

    # Collect all comment URLs for batch fetching
    comment_urls = []
    review_metadata = []

    for i, sublist in enumerate(reviews_response):
        pull_number = pull_numbers[i]
        for review in sublist:
            user = review["user"]
            review_id = review["id"]

            comment_url = (
                f"https://api.github.com/repos/{owner}/{repo}"
                f"/pulls/{pull_number}/reviews/{review_id}/comments"
            )
            comment_urls.append(comment_url)
            review_metadata.append({
                "user": user,
                "review_id": review_id,
                "pull_number": pull_number,
            })

    # Fetch all comments in batches
    if comment_urls:
        comments_response = asyncio.run(
            fetch_batch(comment_urls),
        )

        # Combine the data
        reviewer_data = []
        for i, comments in enumerate(comments_response):
            metadata = review_metadata[i]
            comment_count = len(comments) if comments else 0

            reviewer_data.append({
                "user": metadata["user"],
                "review_id": metadata["review_id"],
                "pull_number": metadata["pull_number"],
                "comment_count": comment_count,
            })

        return reviewer_data

    return []
