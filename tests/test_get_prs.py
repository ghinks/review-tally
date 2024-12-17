import unittest
from unittest.mock import patch, Mock
from datetime import datetime
from pr_reviews.queries.get_prs import get_pull_requests_between_dates


class TestGetPullRequestsBetweenDates(unittest.TestCase):
    @patch("requests.get")
    def test_get_pull_requests_between_dates(self, mock_get):
        # Define the mock response data
        mock_response_data = [
            {"created_at": "2023-01-01T12:00:00Z", "number": 1, "title": "Test PR 1"},
            {"created_at": "2023-01-02T12:00:00Z", "number": 2, "title": "Test PR 2"},
        ]

        # Create a mock response object and set its json method to return the mock data
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Define the input parameters
        owner = "test_owner"
        repo = "test_repo"
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 3)

        # Call the function to test
        result = get_pull_requests_between_dates(owner, repo, start_date, end_date)

        # Assert the result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["number"], 1)
        self.assertEqual(result[1]["number"], 2)


if __name__ == "__main__":
    unittest.main()
