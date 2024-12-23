import unittest
from unittest.mock import patch, Mock
from pr_reviews.queries.get_repos_gql import get_repos_by_language

class TestGetReposByLanguage(unittest.TestCase):
    @patch('pr_reviews.queries.get_repos_gql.requests.post')
    def test_get_repos_by_language(self, mock_post):
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
                                    "nodes": [{"name": "Python"}, {"name": "JavaScript"}]
                                }
                            },
                            {
                                "name": "repo2",
                                "languages": {
                                    "nodes": [{"name": "Java"}, {"name": "C++"}]
                                }
                            }
                        ]
                    }
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Test with a specific language
        repos = get_repos_by_language("test_org", ["Python"])
        self.assertEqual(repos, ["repo1"])

        # Test with an empty language list
        repos = get_repos_by_language("test_org", [])
        self.assertEqual(repos, ["repo1", "repo2"])

if __name__ == '__main__':
    unittest.main()