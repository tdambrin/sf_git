import pytest
import shutil
from pathlib import Path
import datetime
from zoneinfo import ZoneInfo
from git import Repo, Actor
from dotenv import dotenv_values

import sf_git.models
from sf_git.config import Config

PACKAGE_ROOT = Path(__file__).parent.parent
TEST_CONF = dotenv_values(PACKAGE_ROOT / "sf_git.test.conf")

TESTING_FOLDER = Path(__file__).parent.absolute()
REPO_ROOT_PATH = Path(TEST_CONF["SNOWFLAKE_VERSIONING_REPO"]).absolute()
REPO_DATA_PATH = Path(TEST_CONF["WORKSHEETS_PATH"]).absolute()


@pytest.fixture(scope="session", name="testing_folder")
def testing_folder():
    return TESTING_FOLDER


@pytest.fixture(scope="session", name="fixture_dotenv_path")
def dotenv_path():
    return REPO_ROOT_PATH / "sf_git.test.conf"


@pytest.fixture(scope="session", name="repo_root_path")
def repo_root_path():
    return REPO_ROOT_PATH


@pytest.fixture(scope="session", autouse=True)
def setup_and_teardown():
    """
    Setup test envs and teardown
    """

    # ---- SETUP -----
    # Copy the content from `tests/assets/test_data`.
    if REPO_ROOT_PATH.is_dir():
        shutil.rmtree(REPO_ROOT_PATH)

    shutil.copytree(
        TESTING_FOLDER / "data", REPO_DATA_PATH, dirs_exist_ok=True
    )
    shutil.copy(PACKAGE_ROOT / "sf_git.test.conf", REPO_ROOT_PATH)

    # ---- RUN TESTS -----
    yield

    # ---- TEARDOWN -----
    shutil.rmtree(REPO_ROOT_PATH)


@pytest.fixture(autouse=True, name="test_config")
def mock_config(monkeypatch):
    import sf_git.config as config

    global_config = Config(
        repo_path=REPO_ROOT_PATH,
        worksheets_path=REPO_DATA_PATH,
        sf_account_id=TEST_CONF["SF_ACCOUNT_ID"],
        sf_login_name=TEST_CONF["SF_LOGIN_NAME"],
        sf_pwd=TEST_CONF["SF_PWD"],
    )
    monkeypatch.setattr(config, "GLOBAL_CONFIG", global_config)

    return global_config


@pytest.fixture(scope="session", name="repo")
def repo() -> Repo:
    """
    Create a git repository with sample data and history.
    """

    author = Actor("An author", "author@example.com")
    committer = Actor("A committer", "committer@example.com")
    commit_date = datetime.datetime(
        2024, 1, 16, tzinfo=ZoneInfo("Europe/Paris")
    )

    # Init repo
    repo = Repo.init(REPO_ROOT_PATH)

    # Add some commits
    repo.index.add([REPO_DATA_PATH])
    repo.index.commit(
        "Initial skeleton",
        author=author,
        committer=committer,
        author_date=commit_date,
        commit_date=commit_date,
    )

    return repo


@pytest.fixture(scope="session", name="auth_context")
def auth_context() -> sf_git.models.AuthenticationContext:
    import sf_git.config as config

    context = sf_git.models.AuthenticationContext(
        app_server_url="https://test_snowflake.com",
        account_url="https://account.test_snowflake.com",
        account="fake.snowflake.account",
        account_name=config.GLOBAL_CONFIG.sf_account_id,
        client_id="fake",
        main_app_url="https://test_snowflake.com",
        master_token="fake",
        organization_id="fake.organization",
        region="west-europe",
        snowsight_token={"fake": "fake"},
        login_name=config.GLOBAL_CONFIG.sf_login_name,
        username=config.GLOBAL_CONFIG.sf_login_name,
    )

    return context
