import json
import shutil

import dotenv
import pytest
from click import UsageError
from git.repo import Repo

import sf_git.commands
from sf_git.models import Worksheet
import sf_git.config as config


@pytest.fixture
def worksheets(testing_folder):
    with open(testing_folder / "fixtures" / "worksheets.json", "r") as f:
        worksheets_as_dict = json.load(f)
    return [Worksheet(**w) for w in worksheets_as_dict]


@pytest.fixture
def mock_authenticate_to_snowsight(auth_context, monkeypatch):
    def get_fake_auth_context(account_id, username, password, auth_mode=None):
        return auth_context

    monkeypatch.setattr(
        sf_git.commands, "authenticate_to_snowsight", get_fake_auth_context
    )


@pytest.fixture
def mock_sf_get_worksheets(worksheets, monkeypatch):
    def get_fake_worksheets(auth_context, store_to_cache, only_folder):
        return worksheets

    monkeypatch.setattr(
        sf_git.commands, "sf_get_worksheets", get_fake_worksheets
    )


@pytest.fixture
def mock_load_worksheets_from_cache(worksheets, monkeypatch):
    def get_fixture_worksheets(repo, branch_name, only_folder):
        return worksheets

    monkeypatch.setattr(
        sf_git.commands, "load_worksheets_from_cache", get_fixture_worksheets
    )


@pytest.fixture
def no_print(monkeypatch):
    def do_nothing(worksheets, logger):
        pass

    monkeypatch.setattr(sf_git.commands, "print_worksheets", do_nothing)


@pytest.fixture
def no_upload(monkeypatch):
    def successful_upload(auth_context, worksheets):
        return {
            "completed": [worksheet.name for worksheet in worksheets],
            "errors": [],
        }

    monkeypatch.setattr(
        sf_git.commands, "upload_to_snowsight", successful_upload
    )


@pytest.fixture
def alternative_repo_path(testing_folder):
    return testing_folder / "tmp" / "sf_git_test_alternative"


@pytest.fixture(name="alternative_repo")
def setup_and_teardown(alternative_repo_path):
    """
    Setup alternative git repo and teardown
    """

    # ---- SETUP -----
    Repo.init(alternative_repo_path, mkdir=True)

    # ---- RUN TESTS -----
    yield

    # ---- TEARDOWN -----
    shutil.rmtree(alternative_repo_path)


def test_fetch_worksheets_when_pwd_auth_with_pwd(
    mock_authenticate_to_snowsight,
    mock_sf_get_worksheets,
    no_print,
):
    worksheets = sf_git.commands.fetch_worksheets_procedure(
        username=config.GLOBAL_CONFIG.sf_login_name,
        account_id=config.GLOBAL_CONFIG.sf_account_id,
        auth_mode="PWD",
        password=config.GLOBAL_CONFIG.sf_pwd,
        store=False,
        only_folder="",
        logger=lambda x: None,
    )

    assert isinstance(worksheets, list)
    assert len(worksheets) == 1


def test_fetch_worksheets_when_pwd_auth_without_pwd(
    mock_authenticate_to_snowsight,
    mock_sf_get_worksheets,
    no_print,
):
    with pytest.raises(UsageError):
        sf_git.commands.fetch_worksheets_procedure(
            username=config.GLOBAL_CONFIG.sf_login_name,
            account_id=config.GLOBAL_CONFIG.sf_account_id,
            auth_mode="PWD",
            password=None,
            store=False,
            only_folder="",
            logger=lambda x: None,
        )


def test_push_worksheets_when_pwd_auth_without_pwd(
    mock_authenticate_to_snowsight,
    mock_load_worksheets_from_cache,
    no_upload,
    no_print,
):
    with pytest.raises(UsageError):
        sf_git.commands.push_worksheets_procedure(
            username=config.GLOBAL_CONFIG.sf_login_name,
            account_id=config.GLOBAL_CONFIG.sf_account_id,
            auth_mode="PWD",
            password=None,
            only_folder="",
            logger=lambda x: None,
        )


def test_push_worksheets_when_pwd_auth_with_pwd(
    repo,
    mock_authenticate_to_snowsight,
    mock_load_worksheets_from_cache,
    no_upload,
    no_print,
):
    report = sf_git.commands.push_worksheets_procedure(
        username=config.GLOBAL_CONFIG.sf_login_name,
        account_id=config.GLOBAL_CONFIG.sf_account_id,
        auth_mode="PWD",
        password=config.GLOBAL_CONFIG.sf_pwd,
        only_folder="",
        logger=lambda x: None,
    )

    assert isinstance(report, dict)
    assert len(report["completed"]) == 1
    assert len(report["errors"]) == 0


@pytest.mark.parametrize(
    "key",
    [
        "SNOWFLAKE_VERSIONING_REPO",
        "WORKSHEETS_PATH",
        "SF_ACCOUNT_ID",
        "SF_LOGIN_NAME",
        "SF_PWD",
    ],
)
def test_get_config_repo_procedure_when_key_exists(
    key,
    fixture_dotenv_path,
    monkeypatch,
):
    dotenv_config = dotenv.dotenv_values(fixture_dotenv_path)
    monkeypatch.setattr(sf_git.commands, "DOTENV_PATH", fixture_dotenv_path)

    value = sf_git.commands.get_config_repo_procedure(
        key, logger=lambda x: None
    )

    assert value == dotenv_config[key]


def test_get_config_repo_procedure_when_key_doesnt_exists(
    fixture_dotenv_path,
    monkeypatch,
):
    monkeypatch.setattr(sf_git.commands, "DOTENV_PATH", fixture_dotenv_path)

    with pytest.raises(UsageError):
        sf_git.commands.get_config_repo_procedure(
            "NOT_EXISTING", logger=lambda x: None
        )


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            {"username": "new_login", "password": "new_password"},
            {"SF_LOGIN_NAME": "new_login", "SF_PWD": "************"},
        ),
    ],
)
def test_set_config_repo_procedure_when_key_exists(
    params,
    expected,
    fixture_dotenv_path,
    repo,
    monkeypatch,
):
    dotenv_config = dotenv.dotenv_values(fixture_dotenv_path)
    monkeypatch.setattr(sf_git.commands, "DOTENV_PATH", fixture_dotenv_path)

    updates = sf_git.commands.set_config_repo_procedure(**params)

    assert updates == expected


def test_set_config_procedure_when_valid_repo(
    alternative_repo_path,
    fixture_dotenv_path,
    repo,
    alternative_repo,
    monkeypatch,
):
    params = {"git_repo": str(alternative_repo_path)}
    expected = {"SNOWFLAKE_VERSIONING_REPO": str(alternative_repo_path)}

    monkeypatch.setattr(sf_git.commands, "DOTENV_PATH", fixture_dotenv_path)

    updates = sf_git.commands.set_config_repo_procedure(**params)

    assert updates == expected


def test_set_config_procedure_when_invalid_repo(
    fixture_dotenv_path,
    repo,
    testing_folder,
    monkeypatch,
):
    params = {"git_repo": str(testing_folder / "not_initialized")}

    monkeypatch.setattr(sf_git.commands, "DOTENV_PATH", fixture_dotenv_path)

    with pytest.raises(UsageError):
        sf_git.commands.set_config_repo_procedure(**params)


def test_set_config_repo_ws_path_when_invalid(
    alternative_repo_path,
    alternative_repo,
    fixture_dotenv_path,
    repo,
    testing_folder,
    monkeypatch,
):
    params = {
        "git_repo": str(alternative_repo_path),
        "save_dir": str(testing_folder / "not_a_subdirectory"),
    }

    monkeypatch.setattr(sf_git.commands, "DOTENV_PATH", fixture_dotenv_path)

    with pytest.raises(UsageError):
        sf_git.commands.set_config_repo_procedure(**params)


def test_set_config_repo_ws_path_when_valid(
    alternative_repo_path,
    alternative_repo,
    fixture_dotenv_path,
    repo,
    testing_folder,
    monkeypatch,
):
    params = {
        "git_repo": str(alternative_repo_path),
        "save_dir": str(alternative_repo_path / "a_subdirectory"),
    }
    expected = {
        "SNOWFLAKE_VERSIONING_REPO": str(alternative_repo_path),
        "WORKSHEETS_PATH": str(alternative_repo_path / "a_subdirectory"),
    }

    monkeypatch.setattr(sf_git.commands, "DOTENV_PATH", fixture_dotenv_path)

    updates = sf_git.commands.set_config_repo_procedure(**params)

    assert isinstance(updates, dict)
    assert updates == expected


def test_set_config_ws_path_when_valid(
    fixture_dotenv_path,
    repo,
    repo_root_path,
    testing_folder,
    monkeypatch,
):
    params = {"save_dir": str(repo_root_path / "a_subdirectory")}
    expected = {"WORKSHEETS_PATH": str(repo_root_path / "a_subdirectory")}

    monkeypatch.setattr(sf_git.commands, "DOTENV_PATH", fixture_dotenv_path)

    updates = sf_git.commands.set_config_repo_procedure(**params)

    assert isinstance(updates, dict)
    assert updates == expected
