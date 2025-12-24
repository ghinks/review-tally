import os
import unittest
from unittest.mock import Mock, patch

from reviewtally.queries.get_repos_gql import get_repos_by_language


class TestGetReposByLanguage(unittest.TestCase):
    @patch("reviewtally.queries.get_repos_gql.requests.post")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    def test_get_repos_by_language(self, mock_post) -> None:  # noqa: ANN001
        # Mock the response from the GitHub API
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "organization": {
                    "repositories": {
                        "nodes": [
                            {
                                "name": "repo1",
                                "pullRequests": {
                                    "totalCount": 150,
                                },
                                "languages": {
                                    "nodes": [
                                        {"name": "Python"},
                                        {"name": "JavaScript"},
                                    ],
                                },
                            },
                            {
                                "name": "repo2",
                                "pullRequests": {
                                    "totalCount": 75,
                                },
                                "languages": {
                                    "nodes": [
                                        {"name": "Java"},
                                        {"name": "C++"},
                                    ],
                                },
                            },
                        ],
                    },
                },
            },
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Test with a specific language
        repos = get_repos_by_language("test_org", ["Python"])
        assert repos == ["repo1"]

        # Test with an empty language list
        repos = get_repos_by_language("test_org", [])
        assert repos == ["repo1", "repo2"]

    @patch("reviewtally.queries.get_repos_gql.requests.post")
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
    def test_archived_repos_are_ignored(self, mock_post) -> None:  # noqa: ANN001
        # Mock the response from the GitHub API with archived repos
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {
                "organization": {
                    "repositories": {
                        "nodes": [
                            {
                                "name": "active_repo",
                                "isArchived": False,
                                "pullRequests": {
                                    "totalCount": 50,
                                },
                                "languages": {
                                    "nodes": [
                                        {"name": "Python"},
                                    ],
                                },
                            },
                            {
                                "name": "archived_repo",
                                "isArchived": True,
                                "pullRequests": {
                                    "totalCount": 100,
                                },
                                "languages": {
                                    "nodes": [
                                        {"name": "Python"},
                                    ],
                                },
                            },
                            {
                                "name": "another_active_repo",
                                "isArchived": False,
                                "pullRequests": {
                                    "totalCount": 75,
                                },
                                "languages": {
                                    "nodes": [
                                        {"name": "JavaScript"},
                                    ],
                                },
                            },
                        ],
                    },
                },
            },
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Test that archived repos are excluded
        repos = get_repos_by_language("test_org", [])
        assert repos == ["active_repo", "another_active_repo"]
        assert "archived_repo" not in repos

        # Test archived repos excluded with language filter
        repos = get_repos_by_language("test_org", ["Python"])
        assert repos == ["active_repo"]
        assert "archived_repo" not in repos


if __name__ == "__main__":
    unittest.main()
