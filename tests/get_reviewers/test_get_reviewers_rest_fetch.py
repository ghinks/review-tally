import asyncio
import unittest

import aiohttp
from aioresponses import aioresponses

from reviewtally.queries.get_reviewers_rest import fetch
from tests.utils import get_reviews_url, read_reviews_file


class TestFetch(unittest.TestCase):
    @aioresponses()
    def test_fetch_json(self, mocked: aioresponses) -> None:
        url = get_reviews_url("expressjs", "express", 1)
        payload = read_reviews_file()
        mocked.get(url, status=200, payload=payload)

        async def run_test() -> None:
            async with aiohttp.ClientSession() as session:
                result = await fetch(session, url)
                assert result == payload

        asyncio.run(run_test())
