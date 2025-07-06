# Python
import json
from pathlib import Path


def read_reviews_file() -> str:
    # assume the reviews_response.json file is in the tests/fixtures directory
    with Path("tests/fixtures/reviews_response.json").open("r") as file:
        return json.load(file)

def get_reviews_url(owner: str, repo: str, pull_number: int) -> str:
    return f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/reviews"


def read_review_comments_file() -> list[dict]:
    path = Path("tests/fixtures/review_comments_response.json")
    with path.open("r") as file:
        return json.load(file)


def read_multiple_reviews_file() -> list[dict]:
    path = Path("tests/fixtures/multiple_reviews_response.json")
    with path.open("r") as file:
        return json.load(file)


def read_empty_reviews_file() -> list[dict]:
    with Path("tests/fixtures/empty_reviews_response.json").open("r") as file:
        return json.load(file)


def read_empty_comments_file() -> list[dict]:
    with Path("tests/fixtures/empty_comments_response.json").open("r") as file:
        return json.load(file)


def get_review_comments_url(
    owner: str, repo: str, pull_number: int, review_id: int,
) -> str:
    return (
        f"https://api.github.com/repos/{owner}/{repo}"
        f"/pulls/{pull_number}/reviews/{review_id}/comments"
    )
