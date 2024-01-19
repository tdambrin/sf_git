from git import Repo


def test_repo(repo: Repo):

    assert not repo.bare
    assert len(repo.head.reference.log()) == 1


def test_config():
    from sf_git.config import global_config
    assert global_config.sf_login_name == "fake"
