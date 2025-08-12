import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from reviewtally.queries.get_prs import (
    get_pull_requests_between_dates,
)


class TestGetPullRequestsBetweenDates(unittest.TestCase):
    PR_NUMBER_1 = 1
    PR_NUMBER_2 = 2
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
            owner, repo, start_date, end_date,
        )

        # Assert the result
        assert (
            len(pull_requests) == TestGetPullRequestsBetweenDates.EXPECTED_LEN
        )
        assert (
            pull_requests[0]["number"]
            == TestGetPullRequestsBetweenDates.PR_NUMBER_1
        )
        assert (
            pull_requests[1]["number"]
            == TestGetPullRequestsBetweenDates.PR_NUMBER_2
        )


if __name__ == "__main__":
    unittest.main()
