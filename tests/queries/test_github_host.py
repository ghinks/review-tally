import unittest

from reviewtally.queries import (
    DEFAULT_GITHUB_HOST,
    build_github_api_url,
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
            build_github_api_url("repos/octocat/Hello-World"),
            "https://api.github.com/repos/octocat/Hello-World",
        )

    def test_custom_host_without_scheme(self) -> None:
        set_github_host("ghe.example.com/api/v3")
        self.assertEqual(
            get_github_host(),
            "https://ghe.example.com/api/v3",
        )
        self.assertEqual(
            build_github_api_url("graphql"),
            "https://ghe.example.com/api/v3/graphql",
        )


if __name__ == "__main__":
    unittest.main()

