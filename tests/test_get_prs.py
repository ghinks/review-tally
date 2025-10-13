import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from reviewtally.exceptions.local_exceptions import PaginationError
from reviewtally.queries.get_prs import (
    get_pull_requests_between_dates,
)


class TestGetPullRequestsBetweenDates(unittest.TestCase):
    PR_NUMBER_1 = 1
    PR_NUMBER_2 = 2
    PR_NUMBER_3 = 3
    # Define the mock response data
    MOCK_RESP_DATA = (
        {
            "created_at": "2023-01-01T12:00:00Z",
            "number": PR_NUMBER_1,
            "title": "Test PR 1",
        },
        {
            "created_at": "2023-01-02T12:00:00Z",
            "number": PR_NUMBER_2,
            "title": "Test PR 2",
        },
        {
            "created_at": "2022-01-02T12:00:00Z",
            "number": PR_NUMBER_2,
            "title": "Test PR 3, this should not be included",
        },
    )
    EXPECTED_LEN = len(MOCK_RESP_DATA)

    @patch("requests.get")
    def test_get_pull_requests_between_dates(self, mock_get) -> None:  # noqa: ANN001
        # Create a mock response object and set its json method
        # to return the mock data
        mock_response = Mock()
        mock_response.json.return_value = (
            TestGetPullRequestsBetweenDates.MOCK_RESP_DATA
        )
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Define the input parameters
        owner = "test_owner"
        repo = "test_repo"
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 1, 3, tzinfo=timezone.utc)

        # Call the function to test
        pull_requests = get_pull_requests_between_dates(
            owner,
            repo,
            start_date,
            end_date,
        )

        # Assert the result
        assert (
            len(pull_requests)
            == TestGetPullRequestsBetweenDates.EXPECTED_LEN - 1
        )
        assert (
            pull_requests[0]["number"]
            == TestGetPullRequestsBetweenDates.PR_NUMBER_1
        )
        assert (
            pull_requests[1]["number"]
            == TestGetPullRequestsBetweenDates.PR_NUMBER_2
        )

    @patch("requests.get")
    def test_raises_after_100_pages(self, mock_get) -> None:  # noqa: ANN001
        # Always return a non-empty page with a PR newer than end_date,
        # so pagination continues until the function's max-page limit is hit.
        def side_effect(*_args: object, **_kwargs: object) -> Mock:
            resp = Mock()
            resp.status_code = 200
            resp.json.return_value = (
                {
                    "created_at": "2023-01-01T12:00:00Z",
                    "number": 1,
                    "title": "PR",
                },
            )
            return resp

        mock_get.side_effect = side_effect

        owner = "test_owner"
        repo = "test_repo"
        # Pick an end_date in the far past so the loop doesn't break early.
        start_date = datetime(1970, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(1970, 1, 2, tzinfo=timezone.utc)

        with self.assertRaises(PaginationError):
            get_pull_requests_between_dates(owner, repo, start_date, end_date)


if __name__ == "__main__":
    unittest.main()
