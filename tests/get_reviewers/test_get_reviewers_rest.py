import json
import os
from pathlib import Path
from typing import Callable
from unittest.mock import patch

import aiohttp
import pytest
from aioresponses import aioresponses

from pr_reviews.queries.get_reviewers_rest import fetch


@pytest.fixture
def read_reviews_file() -> str:
    # assume the reviews_response.json file is in the tests/fixtures directory
    with Path("tests/fixtures/reviews_response.json").open("r") as file:
        return json.dumps(json.load(file))

@pytest.fixture
def get_reviews_url() -> callable:
    def _get_reviews_url(owner: str, repo: str, pull_number: int) -> str:
        return f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
    return _get_reviews_url


@pytest.fixture
def mock_aioresponse() -> aioresponses:
    with aioresponses() as m:
        yield m

@pytest.mark.asyncio
@patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
async def test_get_reviewers_success(read_reviews_file: str,
                                     get_reviews_url: Callable[[],str],
                                     mock_aioresponse: aioresponses) -> None:
    url = get_reviews_url("expressjs", "express", 1)
    mock_aioresponse.get(
        url,
        status=200,
        payload=read_reviews_file,
    )
    async with aiohttp.ClientSession() as client:
        response = await fetch(client, url)
        assert response == read_reviews_file
