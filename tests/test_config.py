from git import Repo


def test_repo(repo: Repo):

    assert not repo.bare
    assert len(repo.head.reference.log()) == 1
