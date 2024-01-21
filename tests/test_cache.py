import pytest

import sf_git.cache as cache
from sf_git.models import SnowflakeGitError, Worksheet
import sf_git.config as config


def test_load_ws_after_init(repo):

    worksheets = cache.load_worksheets_from_cache(
        repo,
        branch_name='main',
    )

    assert isinstance(worksheets, list)
    assert len(worksheets) == 7


def test_load_ws_wrong_branch(repo):

    with pytest.raises(SnowflakeGitError):
        cache.load_worksheets_from_cache(
            repo,
            branch_name='non_existing'
        )


def test_load_ws_from_existing_folder(repo):

    # Todo: only_folder param is the SF one, not intuitive
    worksheets = cache.load_worksheets_from_cache(
        repo,
        only_folder='Benchmarking Tutorials'
    )

    assert isinstance(worksheets, list)
    assert len(worksheets) == 4


def test_load_ws_from_non_existing_folder(repo):
    worksheets = cache.load_worksheets_from_cache(
        repo,
        only_folder='Non existing'
    )

    assert isinstance(worksheets, list)
    assert len(worksheets) == 0


@pytest.mark.parametrize(
    "worksheet",
    [Worksheet(
        _id="worksheet_id_01",
        name="test_worksheet_01",
        folder_id="folder_id_01",
        folder_name="Benchmarking_Tutorials",
        content_type="sql",
        content="SELECT count(*) from PASSING_TESTS"
    )]
)
def test_save_sql_ws_to_cache_existing_folder(worksheet):

    cache.save_worksheets_to_cache([worksheet])

    expected_file_path = config.GLOBAL_CONFIG.worksheets_path / "Benchmarking_Tutorials" / f"{worksheet.name}.sql"

    assert expected_file_path.is_file()
    with open(expected_file_path, "r") as f:
        assert f.read() == worksheet.content


@pytest.mark.parametrize(
    "worksheet",
    [Worksheet(
        _id="worksheet_id_02",
        name="test_worksheet_02",
        folder_id="folder_id_01",
        folder_name="Benchmarking_Tutorials",
        content_type="python",
        content="import sf_git; print(sf_git.__version__)"
    )]
)
def test_save_py_ws_to_cache_existing_folder(
        worksheet
):

    cache.save_worksheets_to_cache([worksheet])

    expected_file_path = config.GLOBAL_CONFIG.worksheets_path / "Benchmarking_Tutorials" / f"{worksheet.name}.py"

    assert expected_file_path.is_file()
    with open(expected_file_path, "r") as f:
        assert f.read() == worksheet.content


@pytest.mark.parametrize(
    "worksheet",
    [Worksheet(
        _id="worksheet_id_03",
        name="test_worksheet_03",
        folder_id="folder_id_02",
        folder_name="new_folder_for_test",
        content_type="sql",
        content="SELECT count(*) from PASSING_TESTS"
    )]
)
def test_save_sql_ws_to_cache_new_folder(worksheet):

    cache.save_worksheets_to_cache([worksheet])

    expected_file_path = config.GLOBAL_CONFIG.worksheets_path / "new_folder_for_test" / f"{worksheet.name}.sql"

    assert expected_file_path.is_file()
    with open(expected_file_path, "r") as f:
        assert f.read() == worksheet.content


@pytest.mark.parametrize(
    "worksheet",
    [Worksheet(
        _id="worksheet_id_04",
        name="test_worksheet_04",
        folder_id="folder_id_02",
        folder_name="new_folder_for_test",
        content_type="scala",
        content='println("Coming soon");'
    )]
)
def test_save_unsupported_extension_ws_to_cache_new_folder(worksheet):

    cache.save_worksheets_to_cache([worksheet])

    # Todo: defaults to sql as of now
    expected_file_path = config.GLOBAL_CONFIG.worksheets_path / "new_folder_for_test" / f"{worksheet.name}.scala"

    assert not expected_file_path.is_file()


@pytest.mark.run(after='test_save_py_ws_to_cache_existing_folder')
def test_load_only_tracked_files(
    repo,
):

    worksheets = cache.load_worksheets_from_cache(
        repo,
        only_folder="Benchmarking Tutorials"
    )

    assert isinstance(worksheets, list)
    assert 'test_worksheet_02' not in [ws.name for ws in worksheets]


@pytest.mark.run(after='test_save_sql_ws_to_cache_new_folder')
def test_load_only_tracked_files(
    repo,
):

    worksheets = cache.load_worksheets_from_cache(
        repo,
        only_folder="new_folder_for_test"
    )

    assert isinstance(worksheets, list)
    assert len(worksheets) == 0
