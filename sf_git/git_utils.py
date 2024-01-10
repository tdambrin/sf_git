from git.objects.blob import Blob
from git.objects.tree import Tree
from git.repo.base import Repo
from pathlib import Path
from typing import List, Type, Union, Dict, Optional

from sf_git.models import SnowflakeGitError


def get_tracked_files(
    repo: Repo, folder: Path, branch_name: Optional[str] = None
) -> List[Union[Type[Blob], Type[Tree]]]:
    """
    Get all git tracked files in a folder inside a git repo
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
    repo_objects = [obj for obj in branch.commit.tree.traverse()]
    try:
        folder_tree = next(
            obj for obj in repo_objects if obj.abspath == str(folder)
        )
    except StopIteration:
        raise SnowflakeGitError(
            f"Unable to retrieve folder {str(folder)}"
            f" in Repository {repo.working_dir} and branch {branch.name}."
            "Please check that the files you are looking for are committed"
        )

    # get files
    tracked_files = [obj for obj in folder_tree.traverse()]
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
