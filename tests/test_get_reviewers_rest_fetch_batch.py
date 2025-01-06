import asyncio
import json
import unittest
from pathlib import Path

from aioresponses import aioresponses

from pr_reviews.queries.get_reviewers_rest import fetch_batch


class TestFetchBatch(unittest.TestCase):
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
        payload = self.read_reviews_file()
        urls =[]
        for pull_number in range(2):
            url = self.get_reviews_url("expressjs",
                                       "express",
                                       pull_number)
            urls.append(url)
            mocked.get(url, status=200, payload=payload)

        async def run_test() -> None:
            result = await fetch_batch(urls)
            assert result == [payload, payload]

        asyncio.run(run_test())
