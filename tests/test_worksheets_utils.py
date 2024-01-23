import pytest
import json
import requests_mock
import re

import sf_git.worksheets_utils as worksheets_utils


@pytest.fixture
def mock_api():
    with requests_mock.Mocker() as m:
        yield m


@pytest.fixture
def get_worksheets_api_response_with_worksheets(monkeypatch, testing_folder):

    with open(testing_folder / "fixtures" / "contents.json") as f:
        contents = json.loads(f.read())

    with open(testing_folder / "fixtures" / "entities.json") as f:
        entities = json.loads(f.read())

    mock_response_body = {
        "entities": [entities],
        "models": {
            "queries": contents
        }
    }

    return json.dumps(mock_response_body)


@pytest.fixture()
def get_worksheets_api_response_without_worksheets(monkeypatch, testing_folder):

    mock_response_body = {
        "entities": [],
        "models": {
            "queries": {}
        }
    }

    return json.dumps(mock_response_body)


def test_get_worksheets_when_one(
        mock_api,
        get_worksheets_api_response_with_worksheets,
        auth_context
):

    mock_api.post(re.compile(auth_context.app_server_url), text=get_worksheets_api_response_with_worksheets, status_code=200)

    worksheets = worksheets_utils.get_worksheets(
        auth_context=auth_context,
        store_to_cache=False,
    )

    assert isinstance(worksheets, list)
    assert len(worksheets) == 1


def test_get_folders_when_one(
        mock_api,
        get_worksheets_api_response_with_worksheets,
        auth_context
):

    mock_api.post(re.compile(auth_context.app_server_url), text=get_worksheets_api_response_with_worksheets, status_code=200)

    folders = worksheets_utils.get_worksheets(
        auth_context=auth_context,
        store_to_cache=False,
    )

    assert isinstance(folders, list)
    assert len(folders) == 1


def test_get_worksheets_when_none(
        mock_api,
        get_worksheets_api_response_without_worksheets,
        auth_context
):

    mock_api.post(re.compile(auth_context.app_server_url), text=get_worksheets_api_response_without_worksheets, status_code=200)

    worksheets = worksheets_utils.get_worksheets(
        auth_context=auth_context,
        store_to_cache=False,
    )

    assert isinstance(worksheets, list)
    assert len(worksheets) == 0


def test_get_folders_when_none(
        mock_api,
        get_worksheets_api_response_without_worksheets,
        auth_context
):

    mock_api.post(re.compile(auth_context.app_server_url), text=get_worksheets_api_response_without_worksheets, status_code=200)

    folders = worksheets_utils.get_folders(
        auth_context=auth_context,
    )

    assert isinstance(folders, list)
    assert len(folders) == 0
