class GitHubTokenNotDefinedError(Exception):
    """Exception raised when the GitHub token is not defined."""

    def __init__(self) -> None:
        """Initialize the exception string."""
        super().__init__("Missing GitHub token")
class LoginNotFoundError(ValueError):
    """Exception raised when the login is not found in the reviewer."""

    def __init__(self) -> None:
        """Initialize the exception string."""
        super().__init__("Login property not found in reviewer")
