import asyncio
import unittest

from aioresponses import aioresponses
from pr_reviews.queries.get_reviewers_rest import get_reviewers_for_pull_requests
from tests.utils import read_reviews_file, get_reviews_url

class TestGetReviewers(unittest.TestCase):
    OWNER = "expressjs"
    REPO = "express"
    PULL_REQUESTS = [1, 2]
    @aioresponses()
    def test_get_reviewers(self, mocked: aioresponses) -> None:
        payload = read_reviews_file()
        urls =[]
        for pull_number in self.PULL_REQUESTS:
            url = get_reviews_url(self.OWNER,
                                  self.REPO,
                                  pull_number)
            urls.append(url)
            mocked.get(url, status=200, payload=payload)

        results = get_reviewers_for_pull_requests(self.OWNER,
                                                       self.REPO,
                                                       self.PULL_REQUESTS)
        print(results[0])
        assert results[0]['id'] == 1


