import pytest
import json
import requests_mock
import re

import sf_git.models
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
        "entities": entities,
        "models": {"queries": contents},
    }

    return json.dumps(mock_response_body)


@pytest.fixture()
def get_worksheets_api_response_without_worksheets(
    monkeypatch, testing_folder
):
    mock_response_body = {"entities": [], "models": {"queries": {}}}

    return json.dumps(mock_response_body)


@pytest.fixture()
def mock_get_folders(monkeypatch, testing_folder):
    def mocked_folders(auth_context):
        with open(testing_folder / "fixtures" / "folders.json", "r") as f:
            folders_as_dict = json.load(f)
        return [sf_git.models.Folder(**f) for f in folders_as_dict]

    monkeypatch.setattr(worksheets_utils, "get_folders", mocked_folders)


@pytest.fixture()
def mock_get_worksheets(monkeypatch, testing_folder):
    def mocked_worksheets(auth_context):
        with open(testing_folder / "fixtures" / "worksheets.json", "r") as f:
            worksheets_as_dict = json.load(f)
        return [sf_git.models.Worksheet(**w) for w in worksheets_as_dict]

    monkeypatch.setattr(worksheets_utils, "get_worksheets", mocked_worksheets)


@pytest.fixture()
def mock_all_write_to_snowsight(monkeypatch):
    monkeypatch.setattr(
        worksheets_utils,
        "create_folder",
        lambda auth_context, folder_name: None,
    )
    monkeypatch.setattr(
        worksheets_utils,
        "create_worksheet",
        lambda auth_context, worksheet_name, folder_id: None,
    )
    monkeypatch.setattr(
        worksheets_utils,
        "write_worksheet",
        lambda auth_context, worksheet: None,
    )


def test_get_worksheets_when_two(
    mock_api, get_worksheets_api_response_with_worksheets, auth_context
):
    mock_api.post(
        re.compile(auth_context.app_server_url),
        text=get_worksheets_api_response_with_worksheets,
        status_code=200,
    )

    worksheets = worksheets_utils.get_worksheets(
        auth_context=auth_context,
        store_to_cache=False,
    )

    assert isinstance(worksheets, list)
    assert len(worksheets) == 2


def test_get_folders_when_two(
    mock_api, get_worksheets_api_response_with_worksheets, auth_context
):
    mock_api.post(
        re.compile(auth_context.app_server_url),
        text=get_worksheets_api_response_with_worksheets,
        status_code=200,
    )

    folders = worksheets_utils.get_folders(
        auth_context=auth_context,
    )

    assert isinstance(folders, list)
    assert len(folders) == 2


def test_get_worksheets_when_none(
    mock_api, get_worksheets_api_response_without_worksheets, auth_context
):
    mock_api.post(
        re.compile(auth_context.app_server_url),
        text=get_worksheets_api_response_without_worksheets,
        status_code=200,
    )

    worksheets = worksheets_utils.get_worksheets(
        auth_context=auth_context,
        store_to_cache=False,
    )

    assert isinstance(worksheets, list)
    assert len(worksheets) == 0


def test_get_folders_when_none(
    mock_api, get_worksheets_api_response_without_worksheets, auth_context
):
    mock_api.post(
        re.compile(auth_context.app_server_url),
        text=get_worksheets_api_response_without_worksheets,
        status_code=200,
    )

    folders = worksheets_utils.get_folders(
        auth_context=auth_context,
    )

    assert isinstance(folders, list)
    assert len(folders) == 0


def test_upload_snowsight_when_one_to_update(
    monkeypatch,
    mock_get_folders,
    mock_get_worksheets,
    mock_all_write_to_snowsight,
    testing_folder,
    auth_context,
):
    with open(
        testing_folder / "fixtures" / "worksheets_update.json", "r"
    ) as f:
        worksheets_as_dicts = json.load(f)

    worksheets = [sf_git.models.Worksheet(**w) for w in worksheets_as_dicts]
    upload_report = worksheets_utils.upload_to_snowsight(
        auth_context, worksheets
    )

    assert isinstance(upload_report, dict)
    assert set(upload_report.keys()) == {"completed", "errors"}
    assert len(upload_report["completed"]) == len(worksheets)
    assert len(upload_report["errors"]) == 0


def test_upload_snowsight_when_none_to_update(
    monkeypatch,
    mock_get_folders,
    mock_get_worksheets,
    mock_all_write_to_snowsight,
    testing_folder,
    auth_context,
):
    with open(
        testing_folder / "fixtures" / "worksheets.json", "r"
    ) as f:
        worksheets_as_dicts = json.load(f)

    worksheets = [sf_git.models.Worksheet(**w) for w in worksheets_as_dicts]
    upload_report = worksheets_utils.upload_to_snowsight(
        auth_context, worksheets
    )

    assert isinstance(upload_report, dict)
    assert set(upload_report.keys()) == {"completed", "errors"}
    assert len(upload_report["completed"]) == 0
    assert len(upload_report["errors"]) == 0
