import pytest
import shutil
from pathlib import Path
import datetime
from zoneinfo import ZoneInfo
from git import Repo, Actor


TESTING_FOLDER = Path(__file__).parent
TMP_PATH = Path('/tmp')
REPO_ROOT_PATH = TMP_PATH / "sf_git"
REPO_DATA_PATH = TMP_PATH / "sf_git" / "test_data"


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


def test_repo(repo: Repo):

    assert not repo.bare
    assert len(repo.head.reference.log()) == 1

