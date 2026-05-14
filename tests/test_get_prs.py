import os
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from reviewtally.exceptions.local_exceptions import (
    PaginationError,
    SearchLimitReachedError,
)
from reviewtally.queries import build_github_rest_api_url, set_github_host
from reviewtally.queries.get_prs import get_pull_requests_between_dates


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
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"})
    def test_get_pull_requests_between_dates(self, mock_get) -> None:  # noqa: ANN001
        # Create mock responses for Search API format
        # Search API filters by date server-side, so only return PRs in range
        # (The third PR from 2022 would NOT be returned by the real API)
        filtered_prs = [
            pr
            for pr in TestGetPullRequestsBetweenDates.MOCK_RESP_DATA
            if pr["created_at"].startswith("2023")  # Only 2023 PRs
        ]

        mock_response_1 = Mock()
        mock_response_1.json.return_value = {"items": filtered_prs}
        mock_response_1.status_code = 200
        mock_response_1.headers = {}

        mock_response_2 = Mock()
        mock_response_2.json.return_value = {"items": []}
        mock_response_2.status_code = 200
        mock_response_2.headers = {}

        mock_get.side_effect = [mock_response_1, mock_response_2]

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

        # Assert the result - expect only the 2 PRs from 2023
        expected_pr_count = 2
        assert len(pull_requests) == expected_pr_count
        assert (
            pull_requests[0]["number"]
            == TestGetPullRequestsBetweenDates.PR_NUMBER_1
        )
        assert (
            pull_requests[1]["number"]
            == TestGetPullRequestsBetweenDates.PR_NUMBER_2
        )

    @patch("requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"})
    def test_raises_after_100_pages(self, mock_get) -> None:  # noqa: ANN001
        # Always return a non-empty page in Search API format,
        # so pagination continues until the function's max-page limit is hit.
        def side_effect(*_args: object, **_kwargs: object) -> Mock:
            resp = Mock()
            resp.status_code = 200
            resp.headers = {}
            # Search API format: {"items": [...]}
            resp.json.return_value = {
                "items": [
                    {
                        "created_at": "2023-01-01T12:00:00Z",
                        "number": 1,
                        "title": "PR",
                    },
                ],
            }
            return resp

        mock_get.side_effect = side_effect

        owner = "test_owner"
        repo = "test_repo"
        # Pick an end_date in the far past so the loop doesn't break early.
        start_date = datetime(1970, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(1970, 1, 2, tzinfo=timezone.utc)

        with self.assertRaises(PaginationError):
            get_pull_requests_between_dates(owner, repo, start_date, end_date)

    @patch("requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"})
    def test_search_limit_reached(self, mock_get) -> None:  # noqa: ANN001
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {
            "total_count": 1200,
            "items": [{"number": 1}],
        }
        mock_get.return_value = mock_response

        owner = "test_owner"
        repo = "test_repo"
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 1, 2, tzinfo=timezone.utc)

        with self.assertRaises(SearchLimitReachedError) as cm:
            get_pull_requests_between_dates(owner, repo, start_date, end_date)

        self.assertIn("1200 results found", str(cm.exception))

    @patch("requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"})
    def test_search_limit_reached_fallback(self, mock_get) -> None:  # noqa: ANN001
        # First call: SearchLimitReachedError
        mock_resp_limit = Mock()
        mock_resp_limit.status_code = 200
        mock_resp_limit.headers = {}
        mock_resp_limit.json.return_value = {
            "total_count": 1200,
            "items": [],
        }

        # Subsequent calls: Weekly chunks
        mock_resp_ok = Mock()
        mock_resp_ok.status_code = 200
        mock_resp_ok.headers = {}
        mock_resp_ok.json.return_value = {
            "total_count": 50,
            "items": [{"number": 1}],
        }

        # Each chunk fetch will have two calls: one for results,
        # one empty to break the loop
        mock_resp_empty = Mock()
        mock_resp_empty.status_code = 200
        mock_resp_empty.headers = {}
        mock_resp_empty.json.return_value = {"items": []}

        # 14 days = 2 weekly chunks
        mock_get.side_effect = [
            mock_resp_limit,  # Initial full fetch fails
            mock_resp_ok,
            mock_resp_empty,  # First week
            mock_resp_ok,
            mock_resp_empty,  # Second week
        ]

        owner = "test_owner"
        repo = "test_repo"
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 1, 15, tzinfo=timezone.utc)

        pull_requests = get_pull_requests_between_dates(
            owner,
            repo,
            start_date,
            end_date,
            use_cache=False,
        )

        self.assertEqual(len(pull_requests), 2)
        # Check that we called the API for the full range and then the chunks
        # 5 calls total (1 limit + 2*2 for chunks)
        self.assertEqual(mock_get.call_count, 5)

    @patch("requests.get")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"})
    def test_fetch_uses_configured_host(self, mock_get) -> None:  # noqa: ANN001
        set_github_host("https://ghe.example.com/api/v3")
        self.addCleanup(set_github_host, None)

        mock_response = Mock()
        mock_response.json.return_value = {"items": []}
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_get.return_value = mock_response

        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 1, 2, tzinfo=timezone.utc)

        get_pull_requests_between_dates("test", "repo", start_date, end_date)

        expected_url = build_github_rest_api_url("search/issues")
        called_url = mock_get.call_args.args[0]
        self.assertEqual(called_url, expected_url)


if __name__ == "__main__":
    unittest.main()
