from pathlib import Path
from typing import List, Type, Union, Dict, Optional
import re

import git
from git.objects.blob import Blob
from git.objects.tree import Tree
from git.repo.base import Repo

from sf_git.models import SnowflakeGitError


def get_tracked_files(
    repo: Repo, folder: Path, branch_name: Optional[str] = None
) -> List[Union[Type[Blob], Type[Tree]]]:
    """
    Get all git tracked files in a folder inside a git repo

    :param repo: git repository tracking files
    :param folder: name of folder inside git repo to only load from
    :param branch_name: branch to consider, default is active branch

    :returns: list of blobs (file) and tree (dir)
    """

    # check that folder is in git
    repo_wd = Path(repo.working_dir)
    if repo_wd not in folder.parents:
        return []

    # retrieve branch, active one by default
    if branch_name is not None:
        available_branches = {b.name: b for b in repo.branches}
        if branch_name not in available_branches.keys():
            raise SnowflakeGitError(
                f"Unable to retrieve branch {branch_name}"
                f" in Repository {repo.working_dir}."
                "Please check that the branch name is correct"
            )
        branch = available_branches[branch_name]
    else:
        branch = repo.active_branch

    # get to folder by folder names
    repo_objects = branch.commit.tree.traverse()
    try:
        folder_tree = next(
            obj for obj in repo_objects if obj.abspath == str(folder)
        )
    except StopIteration as exc:
        raise SnowflakeGitError(
            f"Unable to retrieve folder {str(folder)}"
            f" in Repository {repo.working_dir} and branch {branch.name}."
            "Please check that the files you are looking for are committed"
        ) from exc

    # get files
    tracked_files = folder_tree.traverse()
    return tracked_files


def get_blobs_content(blobs: List[Blob]) -> Dict[str, bytes]:
    """
    Get blob contents and return as {blob_name: content}.
    Allow to get file content from git trees easily.
    """

    contents = {
        b.name: b.data_stream.read() for b in blobs if isinstance(b, Blob)
    }
    return contents


def diff(
    repo: git.Repo,
    subdirectory: Union[str, Path] = None,
    file_extensions: Union[str, List[str]] = None,
) -> str:
    """
    Get git diff output with subdirectory and file extension filters

    :param repo: git repository
    :param subdirectory: only on files within this subdirectory
    :param file_extensions: only match files with these extensions

    :returns: str, git diff output
    """
    # Check input
    if subdirectory and isinstance(subdirectory, str):
        subdirectory = Path(subdirectory)
    if file_extensions and isinstance(file_extensions, str):
        file_extensions = [file_extensions]

    # Get blobs
    search_path = (
        subdirectory
        if subdirectory
        else Path(repo.git.rev_parse("--show-toplevel"))
    )
    globs = []
    if not file_extensions:
        globs.extend(search_path.glob("**/*"))
    else:
        for extension in file_extensions:
            globs.extend(list(search_path.glob(f"**/*.{extension}")))

    # Get git diff output
    if not globs:
        return ""

    diff_output = repo.git.diff(globs)

    # Add coloring
    diff_output = re.sub(
        r"^(\++)(.*?)$",
        "\033[32m\\1\\2\033[0m",
        diff_output,
        flags=re.MULTILINE,
    )
    diff_output = re.sub(
        r"^(-+)(.*?)$",
        "\033[31m\\1\\2\033[0m",
        diff_output,
        flags=re.MULTILINE,
    )

    return diff_output
