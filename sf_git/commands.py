import os
import platform
from typing import Callable, List
from pathlib import Path, WindowsPath
import git
import dotenv

from click import UsageError

import sf_git.config as config
from sf_git.cache import load_worksheets_from_cache
from sf_git.snowsight_auth import authenticate_to_snowsight
from sf_git.models import AuthenticationMode, SnowflakeGitError, Worksheet
from sf_git.worksheets_utils import get_worksheets as sf_get_worksheets
from sf_git.worksheets_utils import (
    print_worksheets,
    upload_to_snowsight,
)
from sf_git import DOTENV_PATH


def init_repo_procedure(path: str, mkdir: bool = False) -> str:
    """
    Initialize a git repository.

    :param path: absolute or relative path to git repository root
    :param mkdir: create the repository if it doesn't exist

    :return: new value of versioning repo in sf_git config
    """
    p_constructor = WindowsPath if platform.system() == "Windows" else Path
    abs_path = p_constructor(path).absolute()
    if not os.path.exists(abs_path) and not mkdir:
        raise UsageError(
            f"[Init] {abs_path} does not exist."
            "\nPlease provide a path towards an existing directory"
            " or add the --mkdir option to create it."
        )

    # create repository
    git.Repo.init(path, mkdir=mkdir)

    # set as sf_git versioning repository
    dotenv.set_key(
        DOTENV_PATH,
        key_to_set="SNOWFLAKE_VERSIONING_REPO",
        value_to_set=str(abs_path),
    )

    return dotenv.get_key(DOTENV_PATH, "SNOWFLAKE_VERSIONING_REPO")


def get_config_repo_procedure(key: str, logger: Callable = print) -> str:
    """
    Get sf_git config value.

    :param key: key to retrieve value for
    :param logger: logging function e.g. print

    :returns: sf_git config value
    """
    dotenv_config = dotenv.dotenv_values(DOTENV_PATH)
    if key not in dotenv_config.keys():
        raise UsageError(
            f"[Config] {key} does not exist.\n"
            "Config values to be retrieved are "
            f"{list(dotenv_config.keys())}"
        )

    logger(dotenv_config[key])

    return dotenv_config[key]


def set_config_repo_procedure(
    git_repo: str = None,
    save_dir: str = None,
    account: str = None,
    username: str = None,
    password: str = None,
    logger: Callable = print,
) -> dict:
    """
    Set sf_git config values.

    :param git_repo: if provided, set the git repository path
    :param save_dir: if provided, set the worksheet directory path
    :param account: if provided, set the account id
    :param username: if provided, set the user login name
    :param password: if provided, set the user password
    :param logger: logging function e.g. print

    :returns: dict with newly set keys and their values
    """

    updates = {}

    # check repositories
    if git_repo:
        git_repo = Path(git_repo).absolute()
        if not os.path.exists(git_repo):
            raise UsageError(
                f"[Config] {git_repo} does not exist."
                "Please provide path towards an existing git repository"
                " or create a new one with sfgit init."
            )
    if save_dir:
        save_dir = Path(save_dir).absolute()
        # get git_repo
        git_repo = (
            Path(git_repo).absolute()
            if git_repo
            else config.GLOBAL_CONFIG.repo_path
        )
        if git_repo not in save_dir.parents and git_repo != save_dir:
            raise UsageError(
                "[Config] "
                f"{save_dir} is not a subdirectory of {git_repo}.\n"
                "Please provide a saving directory within the git repository."
            )

    if git_repo:
        dotenv.set_key(
            DOTENV_PATH,
            key_to_set="SNOWFLAKE_VERSIONING_REPO",
            value_to_set=str(git_repo),
        )
        logger(f"Set SNOWFLAKE_VERSIONING_REPO to {str(git_repo)}")
        updates["SNOWFLAKE_VERSIONING_REPO"] = dotenv.get_key(
            DOTENV_PATH, "SNOWFLAKE_VERSIONING_REPO"
        )

    if save_dir:
        dotenv.set_key(
            DOTENV_PATH,
            key_to_set="WORKSHEETS_PATH",
            value_to_set=str(save_dir),
        )
        logger(f"Set WORKSHEETS_PATH to {str(save_dir)}")
        updates["WORKSHEETS_PATH"] = dotenv.get_key(
            DOTENV_PATH, "WORKSHEETS_PATH"
        )

    if account:
        dotenv.set_key(
            DOTENV_PATH,
            key_to_set="SF_ACCOUNT_ID",
            value_to_set=account,
        )
        logger(f"Set SF_ACCOUNT_ID to {account}")
        updates["SF_ACCOUNT_ID"] = dotenv.get_key(DOTENV_PATH, "SF_ACCOUNT_ID")

    if username:
        dotenv.set_key(
            DOTENV_PATH,
            key_to_set="SF_LOGIN_NAME",
            value_to_set=username,
        )
        logger(f"Set SF_LOGIN_NAME to {username}")
        updates["SF_LOGIN_NAME"] = dotenv.get_key(DOTENV_PATH, "SF_LOGIN_NAME")

    if password:
        dotenv.set_key(
            DOTENV_PATH,
            key_to_set="SF_PWD",
            value_to_set=password,
        )
        logger("Set SF_PWD to provided password.")
        updates["SF_LOGIN_NAME"] = "*" * len(password)

    return updates


def fetch_worksheets_procedure(
    username: str,
    account_id: str,
    auth_mode: str = None,
    password: str = None,
    only_folder: str = None,
    store: bool = True,
    logger: Callable = print,
) -> List[Worksheet]:
    """
    Fetch worksheets from Snowsight.

    :param username: username to authenticate
    :param account_id: account id to authenticate
    :param auth_mode: authentication mode, supported are PWD (default) and SSO
    :param password: password to authenticate (not required for SSO)
    :param only_folder: name of folder if only fetch a specific folder from Snowsight
    :param store: (flag) save worksheets locally in configured worksheet directory
    :param logger: logging function e.g. print

    :returns: list of fetched worksheets
    """

    # Get auth parameters
    logger(" ## Authenticating to Snowsight ##")

    if auth_mode:
        if auth_mode == "SSO":
            auth_mode = AuthenticationMode.SSO
            password = None
        elif auth_mode == "PWD":
            auth_mode = AuthenticationMode.PWD
            if not password:
                raise UsageError(
                    "No password provided for PWD authentication mode."
                    "Please provide one."
                )
        else:
            raise UsageError(f"{auth_mode} is not supported.")
    else:  # default
        auth_mode = AuthenticationMode.PWD
        if not password:
            raise UsageError(
                "No password provided for PWD authentication mode."
                "Please provide one."
            )
    logger(f"auth with {username} and {password}")
    auth_context = authenticate_to_snowsight(
        account_id, username, password, auth_mode=auth_mode
    )

    if auth_context.snowsight_token != "":
        logger(f" ## Authenticated as {auth_context.username}##")
    else:
        logger(" ## Authentication failed ##")
        exit(1)

    logger(" ## Getting worksheets ##")
    worksheets = sf_get_worksheets(
        auth_context, store_to_cache=store, only_folder=only_folder
    )

    logger("## Got worksheets ##")
    print_worksheets(worksheets, logger=logger)

    if store and worksheets:
        logger(
            f"## Worksheets saved to {dotenv.get_key(DOTENV_PATH, 'WORKSHEETS_PATH')} ##"
        )

    return worksheets


def commit_procedure(branch: str, message: str, logger: Callable) -> str:
    """
    Commits all worksheets in worksheet directory

    :param branch: name of branch to commit to, defaults to active one
    :param message: commit message
    :param logger: logging function e.g. print

    :returns: commit sha
    """
    # Get git repo
    try:
        repo = git.Repo(config.GLOBAL_CONFIG.repo_path)
    except git.InvalidGitRepositoryError:
        raise SnowflakeGitError(
            f"Could not find Git Repository here : {config.GLOBAL_CONFIG.repo_path}"
        )

    # Get git branch
    if branch:
        available_branches = {b.name: b for b in repo.branches}
        if branch not in available_branches.keys():
            raise UsageError(f"Could not find branch {branch}")
        branch = available_branches[branch]

        # and checkout if necessary
        if repo.active_branch.name != branch.name:
            repo.head.reference = branch
    else:
        branch = repo.active_branch

    # Add worksheets to staged files
    repo.index.add(config.GLOBAL_CONFIG.worksheets_path)

    # Commit
    if message:
        commit_message = message
    else:
        commit_message = "[UPDATE] Snowflake worksheets"

    c = repo.index.commit(message=commit_message)

    logger(f"## Committed worksheets to branch {branch.name}")

    return c.hexsha


def push_worksheets_procedure(
    username: str,
    account_id: str,
    auth_mode: str = None,
    password: str = None,
    branch: str = None,
    only_folder: str = None,
    logger: Callable = print,
) -> dict:
    """
    Push committed worksheet to Snowsight.

    :param username: username to authenticate
    :param account_id: account id to authenticate
    :param auth_mode: authentication mode, supported are PWD (default) and SSO
    :param password: password to authenticate (not required for SSO)
    :param only_folder: name of folder if only push a specific folder to Snowsight
    :param branch: branch to get worksheets from
    :param logger: logging function e.g. print

    :returns: upload report with success and errors per worksheet
    """
    # Get auth parameters
    logger(" ## Authenticating to Snowsight ##")
    if not username:
        raise SnowflakeGitError("No username to authenticate with.")
    if not account_id:
        raise SnowflakeGitError("No account to authenticate with.")

    if auth_mode:
        if auth_mode == "SSO":
            auth_mode = AuthenticationMode.SSO
            password = None
        elif auth_mode == "PWD":
            auth_mode = AuthenticationMode.PWD
            if not password:
                raise UsageError(
                    "No password provided for PWD authentication mode."
                    "Please provide one."
                )
        else:
            raise UsageError(f"{auth_mode} is not supported.")
    else:  # default
        auth_mode = AuthenticationMode.PWD
        if not password:
            raise UsageError(
                "No password provided for PWD authentication mode."
                "Please provide one."
            )

    auth_context = authenticate_to_snowsight(
        account_id, username, password, auth_mode=auth_mode
    )

    if auth_context.snowsight_token != "":
        logger(f" ## Authenticated as {auth_context.login_name}##")
    else:
        logger(" ## Authentication failed ##")
        exit(1)

    # get file content from git utils
    repo = git.Repo(config.GLOBAL_CONFIG.repo_path)

    logger(f" ## Getting worksheets from cache for user {username} ##")
    worksheets = load_worksheets_from_cache(
        repo=repo,
        branch_name=branch,
        only_folder=only_folder,
    )

    logger("## Got worksheets ##")
    print_worksheets(worksheets, logger=logger)

    logger("## Uploading to SnowSight ##")
    upload_report = upload_to_snowsight(auth_context, worksheets)
    worksheet_errors = upload_report["errors"]
    logger("## Uploaded to SnowSight ##")

    if worksheet_errors is not None:
        logger("Errors happened for the following worksheets :")
        for err in worksheet_errors:
            logger(
                f"Name : {err['name']} "
                f"| Error type : {err['error'].snowsight_error}"
            )

    return upload_report
