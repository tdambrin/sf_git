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
    shutil.copy(PACKAGE_ROOT / "sf_git.test.conf", REPO_ROOT_PATH)

    # ---- RUN TESTS -----
    yield

    # ---- TEARDOWN -----
    shutil.rmtree(REPO_ROOT_PATH)


@pytest.fixture(scope="session", autouse=True)
def mock_config():
    def side_effect_test_config():
        GLOBAL_CONFIG = Config(
            repo_path=REPO_ROOT_PATH,
            worksheets_path=REPO_DATA_PATH,
            sf_account_id=TEST_CONF['SF_ACCOUNT_ID'],
            sf_login_name=TEST_CONF['SF_LOGIN_NAME'],
        )

        return GLOBAL_CONFIG

    with patch("sf_git.config.GLOBAL_CONFIG", side_effect_test_config()) as mocked:
        yield mocked


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


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    import sf_git
    monkeypatch.setattr(sf_git, "DOTENV_PATH", REPO_ROOT_PATH / 'sf_git.test.conf')
