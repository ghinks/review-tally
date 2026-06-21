import asyncio
import unittest

import aiohttp

from reviewtally.queries.get_reviewers_rest import fetch
from tests.constants import TEST_GITHUB_TOKEN
from tests.mock_http import MockHTTP, mock_http
from tests.utils import get_reviews_url, read_reviews_file


class TestFetch(unittest.TestCase):
    @mock_http()
    def test_fetch_json(self, mocked: MockHTTP) -> None:
        url = get_reviews_url("expressjs", "express", 1)
        payload = read_reviews_file()
        mocked.get(url, status=200, payload=payload)

        async def run_test() -> None:
            async with aiohttp.ClientSession() as session:
                result = await fetch(
                    session,
                    url,
                    github_token=TEST_GITHUB_TOKEN,
                )
                assert result == payload

        asyncio.run(run_test())
