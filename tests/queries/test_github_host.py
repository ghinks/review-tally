import unittest

from reviewtally.queries import (
    DEFAULT_GITHUB_HOST,
    build_github_rest_api_url,
    get_github_graphql_url,
    get_github_host,
    set_github_host,
)


class TestGithubHostConfiguration(unittest.TestCase):
    def tearDown(self) -> None:
        set_github_host(None)

    def test_defaults_to_public_github(self) -> None:
        set_github_host(None)
        self.assertEqual(get_github_host(), DEFAULT_GITHUB_HOST)
        self.assertEqual(
            build_github_rest_api_url("repos/octocat/Hello-World"),
            "https://api.github.com/repos/octocat/Hello-World",
        )
        self.assertEqual(
            get_github_graphql_url(),
            "https://api.github.com/graphql",
        )

    def test_host_with_embedded_path_populates_rest_default(self) -> None:
        set_github_host("ghe.example.com/api/v3")
        self.assertEqual(get_github_host(), "https://ghe.example.com")
        self.assertEqual(
            build_github_rest_api_url("repos/acme/widgets"),
            "https://ghe.example.com/api/v3/repos/acme/widgets",
        )
        self.assertEqual(
            get_github_graphql_url(),
            "https://ghe.example.com/api/v3/graphql",
        )

    def test_custom_paths_override_defaults(self) -> None:
        set_github_host(
            "https://ghe.example.com",
            rest_path="/api/v3",
            graphql_path="/api/graphql",
        )
        self.assertEqual(get_github_host(), "https://ghe.example.com")
        self.assertEqual(
            build_github_rest_api_url("repos/acme/widgets"),
            "https://ghe.example.com/api/v3/repos/acme/widgets",
        )
        self.assertEqual(
            get_github_graphql_url(),
            "https://ghe.example.com/api/graphql",
        )


if __name__ == "__main__":
    unittest.main()

