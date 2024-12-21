class GitHubTokenNotDefinedError(Exception):
    """Exception raised when the GitHub token is not defined."""

    pass


class LoginNotFoundError(ValueError):
    """Exception raised when the login is not found in the reviewer."""

    def __init__(self):
        super().__init__("login not found in reviewer")
