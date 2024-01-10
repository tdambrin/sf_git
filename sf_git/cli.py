import git
import os
from pathlib import Path
import dotenv

import click
from click import UsageError

from sf_git.cache import load_worksheets_from_cache
from sf_git.config import (
    REPO_PATH,
    WORKSHEETS_PATH,
    SF_ACCOUNT_ID,
    SF_LOGIN_NAME,
    SF_PWD,
)
from sf_git.snowsight_auth import authenticate_to_snowsight
from sf_git.models import AuthenticationMode
from sf_git.worksheets_utils import get_worksheets as sf_get_worksheets
from sf_git.worksheets_utils import (
    print_worksheets,
    upload_to_snowsight,
)


@click.group()
def cli():
    pass


@click.command("init")
@click.option(
    "--path",
    "-p",
    type=str,
    help="Absolute path of Git repository to be created.",
    default=".",
    show_default=True,
)
@click.option(
    "--mkdir",
    help="""(Flag) If provided, the repository directory will be created
            if it doesn't exist""",
    is_flag=True,
    default=False,
    show_default=True,
)
def init(path: str, mkdir: bool):
    """
    Initialize a git repository and set it as the sfgit versioning repository.
    """

    abs_path = Path(path).absolute()
    if not os.path.exists(abs_path) and not mkdir:
        raise UsageError(
            f"[Init] {abs_path} does not exist."
            "\nPlease provide a path towards an existing directory"
            " or add the --mkdir option to create it."
        )

    # create repository
    git.Repo.init(path, mkdir=mkdir)

    # set as sfgit versioning repository
    dotenv_path = Path(__file__).parent / "sf_git.conf"
    dotenv.set_key(
        dotenv_path,
        key_to_set="SNOWFLAKE_VERSIONING_REPO",
        value_to_set=str(abs_path),
    )


@click.command("config")
@click.option(
    "--get",
    help="If provided, print the current value for following config option",
    type=str,
)
@click.option(
    "--git-repo",
    "-r",
    type=str,
    help="Absolute path of Git repository used for versioning",
)
@click.option(
    "--save-dir",
    "-d",
    type=str,
    help="""Absolute path of directory to save worksheets in.
             Must be included in fit repository. Created if does not exist.
        """,
)
@click.option(
    "--account",
    "-a",
    type=str,
    help="""
           Default account for Snowsight authentication.
        """,
)
@click.option(
    "--username",
    "-u",
    type=str,
    help="""
           Default username for Snowsight authentication.
        """,
)
@click.option(
    "--password",
    "-p",
    type=str,
    help="""
           Default password for Snowsight authentication.
        """,
)
def config_repo(
    get: str,
    git_repo: str,
    save_dir: str,
    account: str,
    username: str,
    password: str,
):
    """
    Configure sfgit for easier version control.
    Git_repo configuration is mandatory.
    """

    dotenv_path = Path(__file__).parent / "sf_git.conf"
    if get:
        config = dotenv.dotenv_values(dotenv_path)
        if get not in config.keys():
            raise UsageError(
                f"[Config] {get} does not exist.\n"
                "Config values to be retrieved are "
                f"{list(config.keys())}"
            )

        click.echo(config[get])
        return

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
        git_repo = Path(git_repo).absolute() if git_repo else REPO_PATH
        if (
            git_repo not in save_dir.parents
            and git_repo != save_dir
        ):
            raise UsageError(
                "[Config] "
                f"{save_dir} is not a subdirectory of {git_repo}.\n"
                "Please provide a saving directory within the git repository."
            )

    if git_repo:
        dotenv.set_key(
            dotenv_path,
            key_to_set="SNOWFLAKE_VERSIONING_REPO",
            value_to_set=str(git_repo),
        )
    if save_dir:
        dotenv.set_key(
            dotenv_path,
            key_to_set="WORKSHEETS_PATH",
            value_to_set=str(save_dir),
        )
    if account:
        dotenv.set_key(
            dotenv_path,
            key_to_set="SF_ACCOUNT_ID",
            value_to_set=account,
        )
    if username:
        dotenv.set_key(
            dotenv_path,
            key_to_set="SF_LOGIN_NAME",
            value_to_set=username,
        )
    if password:
        dotenv.set_key(
            dotenv_path,
            key_to_set="SF_PWD",
            value_to_set=password,
        )


@click.command("fetch")
@click.option(
    "--username",
    "-u",
    type=str,
    help="Snowflake user",
)
@click.option("--account-id", "-a", type=str, help="Snowflake Account Id")
@click.option(
    "--auth-mode",
    "-am",
    type=str,
    help="Authentication Mode. Currently supports PWD (Default) and SSO.",
    default="PWD",
    show_default=True,
)
@click.option("--password", "-p", type=str, help="Snowflake password")
@click.option(
    "--store/--no-store",
    "-l",
    help="(Flag) Whether to store the worksheets or just display them.",
    default=True,
    show_default=True,
)
@click.option(
    "--only-folder",
    "-only",
    type=str,
    help="Only fetch worksheets with given folder name",
)
def fetch_worksheets(
    username: str,
    account_id: str,
    auth_mode: str,
    password: str,
    store: bool,
    only_folder: str,
):
    """
    Fetch worksheets from user Snowsight account and store them in cache.
    """

    # Get auth parameters
    click.echo(" ## Authenticating to Snowsight ##")
    username = username or SF_LOGIN_NAME
    if not username:
        raise Exception("No username to authenticate with.")

    account_id = account_id or SF_ACCOUNT_ID
    if not account_id:
        raise Exception("No account to authenticate with.")

    if auth_mode:
        if auth_mode == "SSO":
            auth_mode = AuthenticationMode.SSO
            password = None
        elif auth_mode == "PWD":
            auth_mode = AuthenticationMode.PWD
            password = password or SF_PWD
            if not password:
                raise UsageError(
                    "No password provided for PWD authentication mode."
                    "Please provide one."
                )
        else:
            raise UsageError(f"{auth_mode} is not supported.")
    else:  # default
        auth_mode = AuthenticationMode.PWD
        password = password or SF_PWD
        if not password:
            raise UsageError(
                "No password provided for PWD authentication mode."
                "Please provide one."
            )
    click.echo(f"auth with {username} and {password}")
    auth_context = authenticate_to_snowsight(
        account_id, username, password, auth_mode=auth_mode
    )

    if auth_context.snowsight_token != "":
        click.echo(f" ## Authenticated as {auth_context.username}##")
    else:
        click.echo(" ## Authentication failed ##")
        exit(1)

    click.echo(" ## Getting worksheets ##")
    worksheets = sf_get_worksheets(
        auth_context,
        store_to_cache=store,
        only_folder=only_folder
    )

    click.echo("## Got worksheets ##")
    print_worksheets(worksheets)

    if store:
        click.echo("## Worksheets saved to cache ##")


@click.command("commit")
@click.option(
    "--branch",
    "-b",
    type=str,
    help="Branch to commit to. Default is current.",
)
@click.option("--message", "-m", type=str, help="Commit message")
@click.option(
    "--username",
    "-u",
    type=str,
    help="""User for which worksheets will be committed.
        All users worksheets will be committed if not provided""",
)
def commit(
    branch: str,
    message: str,
    username: str,
):
    """
    Commit Snowsight worksheets to Git repository.
    """
    # Get git repo
    try:
        repo = git.Repo(REPO_PATH)
    except git.InvalidGitRepositoryError:
        raise Exception(f"Could not find Git Repository here : {REPO_PATH}")

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
    repo.index.add(WORKSHEETS_PATH)

    # Commit
    if message:
        commit_message = message
    else:
        commit_message = "[UPDATE] Snowflake worksheets"

    repo.index.commit(message=commit_message)

    click.echo(f"## Committed worksheets to branch {branch.name}")


@click.command("push")
@click.option("--username", "-u", type=str, help="Snowflake user")
@click.option(
    "--account-id",
    "-a",
    type=str,
    help="Snowflake Account Id",
)
@click.option(
    "--auth-mode",
    "-am",
    type=str,
    help="Authentication Mode. Currently supports PWD (Default) and SSO.",
    default="PWD",
    show_default=True,
)
@click.option("--password", "-p", type=str, help="Snowflake password")
@click.option(
    "--branch",
    "-b",
    type=str,
    help="Branch to commit to. Default is current.",
)
@click.option(
    "--only-folder",
    "-only",
    type=str,
    help="Only push worksheets with given folder name",
)
def push_worksheets(
    username: str, account_id: str, auth_mode: str, password: str,
    branch: str, only_folder: str,
):
    """
    Upload locally stored worksheets to Snowsight user workspace.
    The local directory containing worksheets data is named {username}.
    More flexibility to come.
    """

    # Get auth parameters
    click.echo(" ## Authenticating to Snowsight ##")
    username = username or SF_LOGIN_NAME
    if not username:
        raise Exception("No username to authenticate with.")
    account_id = account_id or SF_ACCOUNT_ID
    if not account_id:
        raise Exception("No account to authenticate with.")

    if auth_mode:
        if auth_mode == "SSO":
            auth_mode = AuthenticationMode.SSO
            password = None
        elif auth_mode == "PWD":
            auth_mode = AuthenticationMode.PWD
            password = password or SF_PWD
            if not password:
                raise UsageError(
                    "No password provided for PWD authentication mode."
                    "Please provide one."
                )
        else:
            raise UsageError(f"{auth_mode} is not supported.")
    else:  # default
        auth_mode = AuthenticationMode.PWD
        password = password or SF_PWD
        if not password:
            raise UsageError(
                "No password provided for PWD authentication mode."
                "Please provide one."
            )

    auth_context = authenticate_to_snowsight(
        account_id, username, password, auth_mode=auth_mode
    )

    if auth_context.snowsight_token != "":
        click.echo(f" ## Authenticated as {auth_context.login_name}##")
    else:
        click.echo(" ## Authentication failed ##")
        exit(1)

    click.echo(f" ## Getting worksheets from cache for user {username} ##")
    snowsight_username = auth_context.username
    worksheets = load_worksheets_from_cache(
        branch_name=branch,
        only_folder=only_folder,
    )

    click.echo("## Got worksheets ##")
    print_worksheets(worksheets)

    click.echo("## Uploading to SnowSight ##")
    worksheet_errors = upload_to_snowsight(auth_context, worksheets)
    click.echo("## Uploaded to SnowSight ##")

    if worksheet_errors is not None:
        click.echo("Errors happened for the following worksheets :")
        for err in worksheet_errors:
            click.echo(
                f"Name : {err['name']} "
                f"| Error type : {err['error'].snowsight_error}"
            )


cli.add_command(init)
cli.add_command(config_repo)
cli.add_command(fetch_worksheets)
cli.add_command(commit)
cli.add_command(push_worksheets)

if __name__ == "__main__":
    cli()
