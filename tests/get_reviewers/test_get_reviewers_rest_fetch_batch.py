import asyncio
import unittest

from aioresponses import aioresponses

from pr_reviews.queries.get_reviewers_rest import fetch_batch
from tests.utils import read_reviews_file, get_reviews_url

class TestFetchBatch(unittest.TestCase):
    @aioresponses()
    def test_fetch_json(self, mocked: aioresponses) -> None:
        payload = read_reviews_file()
        urls =[]
        for pull_number in range(2):
            url = get_reviews_url("expressjs",
                                       "express",
                                       pull_number)
            urls.append(url)
            mocked.get(url, status=200, payload=payload)

        async def run_test() -> None:
            result = await fetch_batch(urls)
            assert result == [payload, payload]

        asyncio.run(run_test())
