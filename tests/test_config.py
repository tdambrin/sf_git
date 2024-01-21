from git import Repo
from sf_git import DOTENV_PATH
from sf_git.config import GLOBAL_CONFIG


def test_repo(repo: Repo):

    assert not repo.bare
    assert len(repo.head.reference.log()) == 1


def test_dotenv_path():
    from dotenv import dotenv_values
    values = dotenv_values(DOTENV_PATH)
    assert values['SF_LOGIN_NAME'] == GLOBAL_CONFIG.sf_login_name
