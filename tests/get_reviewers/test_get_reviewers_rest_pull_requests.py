import unittest

from reviewtally.queries.get_reviewers_rest import (
    get_reviewers_for_pull_requests,
)
from tests.constants import TEST_GITHUB_TOKEN
from tests.mock_http import MockHTTP, mock_http
from tests.utils import get_reviews_url, read_reviews_file


class TestGetReviewers(unittest.TestCase):
    OWNER = "expressjs"
    REPO = "express"
    PULL_REQUESTS: tuple[int, ...] = (1, 2)

    @mock_http()
    def test_get_reviewers(self, mocked: MockHTTP) -> None:
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
            github_token=TEST_GITHUB_TOKEN,
        )
        assert results[0]["id"] == 1

    @mock_http()
    def test_get_reviewers_skips_missing_user(
        self,
        mocked: MockHTTP,
    ) -> None:
        reviews_payload = [
            {"id": 1, "user": {"login": "octocat", "id": 1}},
            {"id": 2, "user": None},
            {"id": 3, "user": {}},
        ]
        url = get_reviews_url(self.OWNER, self.REPO, 1)
        mocked.get(url, status=200, payload=reviews_payload)

        results = get_reviewers_for_pull_requests(
            self.OWNER,
            self.REPO,
            [1],
            github_token=TEST_GITHUB_TOKEN,
        )
        assert len(results) == 1
        assert results[0]["login"] == "octocat"

