import pytest
import shutil
from pathlib import Path
import datetime
from zoneinfo import ZoneInfo
from git import Repo, Actor
from dotenv import dotenv_values
from unittest.mock import patch

from sf_git.config import Config

PACKAGE_ROOT = Path(__file__).parent.parent
TEST_CONF = dotenv_values(PACKAGE_ROOT / "sf_git.test.conf")

TESTING_FOLDER = Path(__file__).parent
REPO_ROOT_PATH = Path(TEST_CONF['SNOWFLAKE_VERSIONING_REPO'])
REPO_DATA_PATH = Path(TEST_CONF['WORKSHEETS_PATH'])


@pytest.fixture(scope='session', autouse=True)
def setup_and_teardown():
    """
        Setup test envs and teardown
    """

    # ---- SETUP -----
    # Copy the content from `tests/assets/test_data`.
    if REPO_ROOT_PATH.is_dir():
        shutil.rmtree(REPO_ROOT_PATH)

    shutil.copytree(TESTING_FOLDER / "data", REPO_DATA_PATH, dirs_exist_ok=True)

    # ---- RUN TESTS -----
    yield

    # ---- TEARDOWN -----
    shutil.rmtree(REPO_ROOT_PATH)


@pytest.fixture(scope="session", name="repo")
def repo() -> Repo:
    """
        Create a git repository with sample data and history.
    """

    author = Actor("An author", "author@example.com")
    committer = Actor("A committer", "committer@example.com")
    commit_date = datetime.datetime(2024, 1, 16, tzinfo=ZoneInfo("Europe/Paris"))

    # Init repo
    repo = Repo.init(REPO_ROOT_PATH)

    # Add some commits
    repo.index.add(["test_data/*"])
    repo.index.commit(
        "Initial skeleton",
        author=author,
        committer=committer,
        author_date=commit_date,
        commit_date=commit_date,
    )

    return repo


@pytest.fixture(scope="session", autouse=True)
def mock_config():
    def side_effect_test_config():
        global_config = Config(
            repo_path=REPO_ROOT_PATH,
            worksheets_path=REPO_DATA_PATH,
            sf_account_id=TEST_CONF['SF_ACCOUNT_ID'],
            sf_login_name=TEST_CONF['SF_LOGIN_NAME'],
        )

        return global_config

    with patch("sf_git.config.global_config", side_effect_test_config()) as mocked:
        yield mocked
