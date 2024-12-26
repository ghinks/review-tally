# Python
import json
import pytest
import unittest
from unittest.mock import AsyncMock, patch
import aiohttp
import asyncio
import os

from aioresponses import aioresponses

from pr_reviews.queries.get_reviewers_rest import (fetch, fetch_batch,
                                                   get_reviewers_for_pull_requests)
from tests.fixtures.fixtures_reviews_response import read_reviews_file, \
    get_reviews_url

import asyncio
import os


class TestGetReviewersRest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestGetReviewersRest, self).__init__(*args, **kwargs)
        self.REVIEWS_RESPONSE = read_reviews_file()

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    async def test_fetch(self):
        with aioresponses() as mock_get:
            url = get_reviews_url("expressjs",
                              "express",
                              1)
            mock_get.get(url, status=200, payload=self.REVIEWS_RESPONSE)
            response = await fetch(url)
            assert response == self.REVIEWS_RESPONSE



if __name__ == "__main__":
    unittest.main()
