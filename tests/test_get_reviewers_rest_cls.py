import asyncio
import json
import unittest
from pathlib import Path

import aiohttp
from aioresponses import aioresponses

from pr_reviews.queries.get_reviewers_rest import fetch


class TestFetchJson(unittest.TestCase):
    def read_reviews_file(self) -> str:
        # assume the reviews_response.json file is in
        # the tests/fixtures directory
        with Path("tests/fixtures/reviews_response.json").open("r") as file:
            return json.dumps(json.load(file))

    def get_reviews_url(self, owner: str, repo: str, pull_number: int) -> str:
            return ("https://api.github.com/repos/"
                   f"{owner}/{repo}/pulls/{pull_number}/reviews")

    @aioresponses()
    def test_fetch_json(self, mocked: aioresponses) -> None:
        url = self.get_reviews_url("expressjs", "express", 1)
        payload = self.read_reviews_file()
        mocked.get(url, status=200, payload=payload)

        async def run_test() -> None:
            async with aiohttp.ClientSession() as session:
                    result = await fetch(session,url)
                    assert result == payload

        asyncio.run(run_test())
