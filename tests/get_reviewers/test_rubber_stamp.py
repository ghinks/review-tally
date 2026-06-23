import unittest

from reviewtally.queries.get_reviewers_rest import (
    get_reviewers_with_comments_for_pull_requests,
    is_rubber_stamp_review,
)
from tests.constants import TEST_GITHUB_TOKEN
from tests.mock_http import MockHTTP, mock_http
from tests.utils import (
    get_review_comments_url,
    get_reviews_url,
    read_empty_comments_file,
    read_reviews_file,
    read_rubber_stamp_reviews_file,
)


class TestIsRubberStampReview(unittest.TestCase):
    def test_approved_no_body_no_comments_is_rubber_stamp(self) -> None:
        assert is_rubber_stamp_review("APPROVED", "", 0) is True
        assert is_rubber_stamp_review("APPROVED", None, 0) is True
        assert is_rubber_stamp_review("APPROVED", "   \n", 0) is True

    def test_approved_with_body_is_not_rubber_stamp(self) -> None:
        assert is_rubber_stamp_review("APPROVED", "LGTM, thanks", 0) is False

    def test_approved_with_inline_comments_is_not_rubber_stamp(self) -> None:
        assert is_rubber_stamp_review("APPROVED", "", 2) is False

    def test_non_approval_states_never_rubber_stamp(self) -> None:
        assert is_rubber_stamp_review("COMMENTED", "", 0) is False
        assert is_rubber_stamp_review("CHANGES_REQUESTED", "", 0) is False
        assert is_rubber_stamp_review("DISMISSED", None, 0) is False
        assert is_rubber_stamp_review(None, None, 0) is False


class TestRubberStampInReviewData(unittest.TestCase):
    OWNER = "octocat"
    REPO = "Hello-World"
    PULL_REQUEST = 12
    REVIEW_ID_80 = 80
    REVIEW_ID_90 = 90

    @mock_http()
    def test_approval_with_body_not_flagged(
        self,
        mocked: MockHTTP,
    ) -> None:
        """An APPROVED review with a body is not a rubber stamp."""
        reviews_url = get_reviews_url(
            self.OWNER,
            self.REPO,
            self.PULL_REQUEST,
        )
        mocked.get(reviews_url, status=200, payload=read_reviews_file())

        comments_url = get_review_comments_url(
            self.OWNER,
            self.REPO,
            self.PULL_REQUEST,
            self.REVIEW_ID_80,
        )
        mocked.get(
            comments_url,
            status=200,
            payload=read_empty_comments_file(),
        )

        results = get_reviewers_with_comments_for_pull_requests(
            self.OWNER,
            self.REPO,
            [self.PULL_REQUEST],
            github_token=TEST_GITHUB_TOKEN,
        )

        assert results[0]["state"] == "APPROVED"
        assert results[0]["is_rubber_stamp"] is False

    @mock_http()
    def test_empty_approval_is_flagged(
        self,
        mocked: MockHTTP,
    ) -> None:
        """An APPROVED review with no body and no comments is flagged."""
        reviews_url = get_reviews_url(
            self.OWNER,
            self.REPO,
            self.PULL_REQUEST,
        )
        mocked.get(
            reviews_url,
            status=200,
            payload=read_rubber_stamp_reviews_file(),
        )

        comments_url = get_review_comments_url(
            self.OWNER,
            self.REPO,
            self.PULL_REQUEST,
            self.REVIEW_ID_90,
        )
        mocked.get(
            comments_url,
            status=200,
            payload=read_empty_comments_file(),
        )

        results = get_reviewers_with_comments_for_pull_requests(
            self.OWNER,
            self.REPO,
            [self.PULL_REQUEST],
            github_token=TEST_GITHUB_TOKEN,
        )

        assert results[0]["user"]["login"] == "stamper"
        assert results[0]["state"] == "APPROVED"
        assert results[0]["is_rubber_stamp"] is True


if __name__ == "__main__":
    unittest.main()
