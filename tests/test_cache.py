import sf_git.cache as cache


def test_load_ws_after_init(repo, test_config, monkeypatch):

    import sf_git.config as config
    monkeypatch.setattr(config, "GLOBAL_CONFIG", test_config)

    worksheets = cache.load_worksheets_from_cache(
        repo,
        branch_name='main',
    )

    assert isinstance(worksheets, list)
    assert len(worksheets) == 7
