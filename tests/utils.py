# Python
import json
from pathlib import Path


def read_reviews_file() -> str:
    # assume the reviews_response.json file is in the tests/fixtures directory
    with Path("tests/fixtures/reviews_response.json").open("r") as file:
        return json.load(file)

def get_reviews_url(owner: str, repo: str, pull_number: int) -> str:
    return f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
