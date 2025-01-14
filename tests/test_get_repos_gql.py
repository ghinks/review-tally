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
                                "languages": {
                                    "nodes": [
                                        {"name": "Python"},
                                        {"name": "JavaScript"},
                                    ],
                                },
                            },
                            {
                                "name": "repo2",
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

if __name__ == "__main__":
    unittest.main()
