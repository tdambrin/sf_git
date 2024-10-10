import click

import sf_git.config as config
import sf_git.commands


@click.group()
def cli():
    pass


@click.group()
@click.version_option(sf_git.__version__)
@click.pass_context
def cli(ctx):
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

    sf_git.commands.init_repo_procedure(path=path, mkdir=mkdir)


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

    if get:
        sf_git.commands.get_config_repo_procedure(get, click.echo)
    else:
        sf_git.commands.set_config_repo_procedure(
            git_repo=git_repo,
            save_dir=save_dir,
            account=account,
            username=username,
            password=password,
            logger=click.echo,
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

    username = username or config.GLOBAL_CONFIG.sf_login_name
    account_id = account_id or config.GLOBAL_CONFIG.sf_account_id
    password = password or config.GLOBAL_CONFIG.sf_pwd

    sf_git.commands.fetch_worksheets_procedure(
        username=username,
        account_id=account_id,
        auth_mode=auth_mode,
        password=password,
        store=store,
        only_folder=only_folder,
        logger=click.echo,
    )


@click.command("commit")
@click.option(
    "--branch",
    "-b",
    type=str,
    help="Branch to commit to. Default is current.",
)
@click.option("--message", "-m", type=str, help="Commit message")
def commit(
    branch: str,
    message: str,
):
    """
    Commit Snowsight worksheets to Git repository.
    """

    sf_git.commands.commit_procedure(
        branch=branch, message=message, logger=click.echo
    )


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
    username: str,
    account_id: str,
    auth_mode: str,
    password: str,
    branch: str,
    only_folder: str,
):
    """
    Upload locally stored worksheets to Snowsight user workspace.
    The local directory containing worksheets data is named {username}.
    More flexibility to come.
    """

    username = username or config.GLOBAL_CONFIG.sf_login_name
    account_id = account_id or config.GLOBAL_CONFIG.sf_account_id
    password = password or config.GLOBAL_CONFIG.sf_pwd

    sf_git.commands.push_worksheets_procedure(
        username=username,
        account_id=account_id,
        auth_mode=auth_mode,
        password=password,
        branch=branch,
        only_folder=only_folder,
        logger=click.echo,
    )


@click.command("diff")
def diff():
    """
    Displays unstaged changes on worksheets
    """

    sf_git.commands.diff_procedure(logger=click.echo)


@click.group()
@click.version_option(sf_git.__version__)
@click.pass_context
def cli(ctx):
    pass


cli.add_command(init)
cli.add_command(config_repo)
cli.add_command(fetch_worksheets)
cli.add_command(commit)
cli.add_command(push_worksheets)
cli.add_command(diff)

if __name__ == "__main__":
    cli()
