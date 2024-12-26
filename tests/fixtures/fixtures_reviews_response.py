import json
from typing import Any

import pytest


def read_reviews_file() -> dict[str, Any]:
    # assume the reviews_response.json file is in the tests/fixtures directory
    with open("tests/fixtures/reviews_response.json") as file:
        return json.load(file)

def get_reviews_url(owner: str, repo: str, pull_number: int) -> str:
    URL = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
    return URL
