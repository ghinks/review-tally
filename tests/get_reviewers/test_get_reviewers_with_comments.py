import unittest

from aioresponses import aioresponses

from reviewtally.queries.get_reviewers_rest import (
    get_reviewers_with_comments_for_pull_requests,
)
from tests.utils import (
    get_review_comments_url,
    get_reviews_url,
    read_empty_comments_file,
    read_empty_reviews_file,
    read_multiple_reviews_file,
    read_review_comments_file,
    read_reviews_file,
)


class TestGetReviewersWithComments(unittest.TestCase):
    OWNER = "octocat"
    REPO = "Hello-World"
    PULL_REQUEST_1 = 12
    PULL_REQUEST_2 = 13
    REVIEW_ID_80 = 80
    REVIEW_ID_81 = 81
    EXPECTED_COMMENT_COUNT = 2
    EXPECTED_NO_COMMENTS = 0
    EXPECTED_SINGLE_RESULT = 1
    EXPECTED_TWO_RESULTS = 2

    @aioresponses()
    def test_get_reviewers_with_comments_success(
        self, mocked: aioresponses,
    ) -> None:
        """Test successful retrieval of reviewers with comments."""
        pull_numbers = [self.PULL_REQUEST_1]

        # Mock the reviews API call
        reviews_url = get_reviews_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1,
        )
        reviews_data = read_reviews_file()
        mocked.get(reviews_url, status=200, payload=reviews_data)

        # Mock the comments API call
        comments_url = get_review_comments_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1, self.REVIEW_ID_80,
        )
        comments_data = read_review_comments_file()
        mocked.get(comments_url, status=200, payload=comments_data)

        results = get_reviewers_with_comments_for_pull_requests(
            self.OWNER, self.REPO, pull_numbers,
        )

        # Assertions
        assert len(results) == self.EXPECTED_SINGLE_RESULT
        assert results[0]["user"]["login"] == "octocat"
        assert results[0]["review_id"] == self.REVIEW_ID_80
        assert results[0]["pull_number"] == self.PULL_REQUEST_1
        # 2 comments in fixture
        assert results[0]["comment_count"] == self.EXPECTED_COMMENT_COUNT

    @aioresponses()
    def test_get_reviewers_with_comments_no_reviews(
        self, mocked: aioresponses,
    ) -> None:
        """Test handling of pull requests with no reviews."""
        pull_numbers = [self.PULL_REQUEST_1]

        # Mock empty reviews response
        reviews_url = get_reviews_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1,
        )
        empty_reviews = read_empty_reviews_file()
        mocked.get(reviews_url, status=200, payload=empty_reviews)

        results = get_reviewers_with_comments_for_pull_requests(
            self.OWNER, self.REPO, pull_numbers,
        )

        # Should return empty list when no reviews
        assert len(results) == self.EXPECTED_NO_COMMENTS

    @aioresponses()
    def test_get_reviewers_with_comments_no_comments(
        self, mocked: aioresponses,
    ) -> None:
        """Test reviews that exist but have no comments."""
        pull_numbers = [self.PULL_REQUEST_1]

        # Mock the reviews API call
        reviews_url = get_reviews_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1,
        )
        reviews_data = read_reviews_file()
        mocked.get(reviews_url, status=200, payload=reviews_data)

        # Mock empty comments response
        comments_url = get_review_comments_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1, self.REVIEW_ID_80,
        )
        empty_comments = read_empty_comments_file()
        mocked.get(comments_url, status=200, payload=empty_comments)

        results = get_reviewers_with_comments_for_pull_requests(
            self.OWNER, self.REPO, pull_numbers,
        )

        # Should have one result with 0 comments
        assert len(results) == self.EXPECTED_SINGLE_RESULT
        assert results[0]["comment_count"] == self.EXPECTED_NO_COMMENTS
        assert results[0]["user"]["login"] == "octocat"

    @aioresponses()
    def test_get_reviewers_with_comments_multiple_prs(
        self, mocked: aioresponses,
    ) -> None:
        """Test multiple pull requests."""
        pull_numbers = [self.PULL_REQUEST_1, self.PULL_REQUEST_2]

        # Mock reviews for first PR
        reviews_url_1 = get_reviews_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1,
        )
        reviews_data = read_reviews_file()
        mocked.get(reviews_url_1, status=200, payload=reviews_data)

        # Mock reviews for second PR
        reviews_url_2 = get_reviews_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_2,
        )
        mocked.get(reviews_url_2, status=200, payload=reviews_data)

        # Mock comments for first PR
        comments_url_1 = get_review_comments_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1, self.REVIEW_ID_80,
        )
        comments_data = read_review_comments_file()
        mocked.get(comments_url_1, status=200, payload=comments_data)

        # Mock comments for second PR
        comments_url_2 = get_review_comments_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_2, self.REVIEW_ID_80,
        )
        mocked.get(comments_url_2, status=200, payload=comments_data)

        results = get_reviewers_with_comments_for_pull_requests(
            self.OWNER, self.REPO, pull_numbers,
        )

        # Should have results for both PRs
        assert len(results) == self.EXPECTED_TWO_RESULTS
        pr_numbers = [result["pull_number"] for result in results]
        assert self.PULL_REQUEST_1 in pr_numbers
        assert self.PULL_REQUEST_2 in pr_numbers

    @aioresponses()
    def test_get_reviewers_with_comments_multiple_reviewers(
        self, mocked: aioresponses,
    ) -> None:
        """Test pull request with multiple reviews from different users."""
        pull_numbers = [self.PULL_REQUEST_1]

        # Mock multiple reviews response
        reviews_url = get_reviews_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1,
        )
        multiple_reviews = read_multiple_reviews_file()
        mocked.get(reviews_url, status=200, payload=multiple_reviews)

        # Mock comments for first review (octocat)
        comments_url_1 = get_review_comments_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1, self.REVIEW_ID_80,
        )
        comments_data = read_review_comments_file()
        mocked.get(comments_url_1, status=200, payload=comments_data)

        # Mock comments for second review (defunkt)
        comments_url_2 = get_review_comments_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1, self.REVIEW_ID_81,
        )
        empty_comments = read_empty_comments_file()
        mocked.get(comments_url_2, status=200, payload=empty_comments)

        results = get_reviewers_with_comments_for_pull_requests(
            self.OWNER, self.REPO, pull_numbers,
        )

        # Should have results for both reviewers
        assert len(results) == self.EXPECTED_TWO_RESULTS

        # Check first reviewer (octocat) has comments
        octocat_result = next(
            r for r in results if r["user"]["login"] == "octocat"
        )
        assert octocat_result["comment_count"] == self.EXPECTED_COMMENT_COUNT
        assert octocat_result["review_id"] == self.REVIEW_ID_80

        # Check second reviewer (defunkt) has no comments
        defunkt_result = next(
            r for r in results if r["user"]["login"] == "defunkt"
        )
        assert defunkt_result["comment_count"] == self.EXPECTED_NO_COMMENTS
        assert defunkt_result["review_id"] == self.REVIEW_ID_81

    @aioresponses()
    def test_get_reviewers_with_comments_mixed_scenarios(
        self, mocked: aioresponses,
    ) -> None:
        """Test mixed scenario: some PRs with reviews, some without."""
        pull_numbers = [self.PULL_REQUEST_1, self.PULL_REQUEST_2]

        # First PR has reviews with comments
        reviews_url_1 = get_reviews_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1,
        )
        reviews_data = read_reviews_file()
        mocked.get(reviews_url_1, status=200, payload=reviews_data)

        # Second PR has no reviews
        reviews_url_2 = get_reviews_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_2,
        )
        empty_reviews = read_empty_reviews_file()
        mocked.get(reviews_url_2, status=200, payload=empty_reviews)

        # Mock comments for first PR only
        comments_url_1 = get_review_comments_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1, self.REVIEW_ID_80,
        )
        comments_data = read_review_comments_file()
        mocked.get(comments_url_1, status=200, payload=comments_data)

        results = get_reviewers_with_comments_for_pull_requests(
            self.OWNER, self.REPO, pull_numbers,
        )

        # Should only have result for first PR
        assert len(results) == self.EXPECTED_SINGLE_RESULT
        assert results[0]["pull_number"] == self.PULL_REQUEST_1
        assert results[0]["comment_count"] == self.EXPECTED_COMMENT_COUNT

    @aioresponses()
    def test_get_revs_comments_miss_sub_at_with_timestamp(
        self, mocked: aioresponses,
    ) -> None:
        pull_numbers = [self.PULL_REQUEST_1]

        # Mock the reviews API call with missing submitted_at
        reviews_url = get_reviews_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1,
        )
        reviews_data = [
            {
                "id": self.REVIEW_ID_80,
                "user": {"login": "octocat"},
                "state": "APPROVED",
                # intentionally no submitted_at
            },
        ]
        mocked.get(reviews_url, status=200, payload=reviews_data)

        # Mock the comments API call
        comments_url = get_review_comments_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1, self.REVIEW_ID_80,
        )
        comments_data = read_review_comments_file()
        mocked.get(comments_url, status=200, payload=comments_data)

        results = get_reviewers_with_comments_for_pull_requests(
            self.OWNER, self.REPO, pull_numbers,
        )

        assert len(results) == self.EXPECTED_SINGLE_RESULT
        assert results[0]["user"]["login"] == "octocat"
        assert results[0]["review_id"] == self.REVIEW_ID_80
        assert results[0]["pull_number"] == self.PULL_REQUEST_1
        assert results[0]["comment_count"] == self.EXPECTED_COMMENT_COUNT
        # From fixture, both comments have the same created_at
        assert results[0]["submitted_at"] == "2011-04-14T16:00:49Z"

    @aioresponses()
    def test_get_reviewers_with_comments_missing_submitted_at_and_no_comments(
        self, mocked: aioresponses,
    ) -> None:
        pull_numbers = [self.PULL_REQUEST_1]

        # Mock the reviews API call with missing submitted_at
        reviews_url = get_reviews_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1,
        )
        reviews_data = [
            {
                "id": self.REVIEW_ID_80,
                "user": {"login": "octocat"},
                "state": "PENDING",
                # intentionally no submitted_at
            },
        ]
        mocked.get(reviews_url, status=200, payload=reviews_data)

        # Mock empty comments response
        comments_url = get_review_comments_url(
            self.OWNER, self.REPO, self.PULL_REQUEST_1, self.REVIEW_ID_80,
        )
        empty_comments = read_empty_comments_file()
        mocked.get(comments_url, status=200, payload=empty_comments)

        results = get_reviewers_with_comments_for_pull_requests(
            self.OWNER, self.REPO, pull_numbers,
        )

        assert len(results) == self.EXPECTED_SINGLE_RESULT
        assert results[0]["user"]["login"] == "octocat"
        assert results[0]["comment_count"] == self.EXPECTED_NO_COMMENTS
        assert results[0]["submitted_at"] is None


if __name__ == "__main__":
    unittest.main()

