import unittest

from aioresponses import aioresponses

from reviewtally.queries.get_reviewers_rest import (
    get_reviewers_for_pull_requests,
)
from tests.utils import get_reviews_url, read_reviews_file


class TestGetReviewers(unittest.TestCase):
    OWNER = "expressjs"
    REPO = "express"
    PULL_REQUESTS: tuple[int, ...] = (1, 2)

    @aioresponses()
    def test_get_reviewers(self, mocked: aioresponses) -> None:
        payload = read_reviews_file()
        urls = []
        for pull_number in self.PULL_REQUESTS:
            url = get_reviews_url(self.OWNER, self.REPO, pull_number)
            urls.append(url)
            mocked.get(url, status=200, payload=payload)

        results = get_reviewers_for_pull_requests(
            self.OWNER,
            self.REPO,
            self.PULL_REQUESTS,
        )
        assert results[0]["id"] == 1
