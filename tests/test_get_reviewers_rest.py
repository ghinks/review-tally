import json
import os
from typing import Callable, Any
from unittest.mock import patch

import aiohttp
import pytest
from aioresponses import aioresponses
from pr_reviews.queries.get_reviewers_rest import fetch

@pytest.fixture
def read_reviews_file():
    # assume the reviews_response.json file is in the tests/fixtures directory
    with open("tests/fixtures/reviews_response.json") as file:
        return json.load(file)

@pytest.fixture
def get_reviews_url():
    def _get_reviews_url(owner: str, repo: str, pull_number: int) -> str:
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
        return url
    return _get_reviews_url


@pytest.fixture
def mock_aioresponse():
    with aioresponses() as m:
        yield m

@pytest.mark.asyncio
@patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
async def test_get_reviewers_success(read_reviews_file, get_reviews_url, mock_aioresponse):
    url = get_reviews_url("expressjs", "express", 1)
    mock_aioresponse.get(
        url,
        status=200,
        payload=read_reviews_file
    )
    async with aiohttp.ClientSession() as client:
        response = await fetch(client, url)
        assert response == read_reviews_file
