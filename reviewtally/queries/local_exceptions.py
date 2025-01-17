class GitHubTokenNotDefinedError(Exception):
    """Exception raised when the GitHub token is not defined."""

    def __init__(self) -> None:
        """Initialize the exception string."""
        super().__init__("Missing GitHub token, please set the "
                         "GITHUB_TOKEN environment variable")
class LoginNotFoundError(ValueError):
    """Exception raised when the login is not found in the reviewer."""

    def __init__(self) -> None:
        """Initialize the exception string."""
        super().__init__("Login property not found in reviewer")

class NoGitHubOrgError(ValueError):
    """Exception raised when the GitHub organization is not found."""

    def __init__(self, reponame: str) -> None:
        """Initialize the exception string."""
        super().__init__(f"GitHub {reponame} organization not found")
