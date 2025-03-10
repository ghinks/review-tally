import asyncio
import os
from typing import Any

import aiohttp
from aiohttp import ClientTimeout

from reviewtally.queries import REVIEWERS_TIMEOUT

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
    timeout = ClientTimeout(total=REVIEWERS_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
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
