import os
from pathlib import Path, PosixPath, WindowsPath
import platform
from dataclasses import dataclass
from typing import Union


@dataclass
class Config:
    """Package configuration, git, Snowflake and Filesystem"""

    sf_main_app_url: str = "https://app.snowflake.com"
    repo_path: Union[PosixPath, WindowsPath] = None
    worksheets_path: Union[PosixPath, WindowsPath] = None
    sf_account_id: str = None
    sf_login_name: str = None
    sf_pwd: str = None

    def __post_init__(self):
        # make paths windows if necessary
        if platform.system() == "Windows":
            if self.repo_path:
                self.repo_path = WindowsPath(self.repo_path)
            if self.worksheets_path:
                self.worksheets_path = WindowsPath(self.worksheets_path)
        self.repo_path = self.repo_path.absolute()
        self.worksheets_path = self.worksheets_path.absolute()


GLOBAL_CONFIG = Config(
    repo_path=Path(os.environ["SNOWFLAKE_VERSIONING_REPO"]).absolute(),
    worksheets_path=Path(
        os.environ.get("WORKSHEETS_PATH") or "/tmp/snowflake_worksheets"
    ).absolute(),
    sf_account_id=os.environ.get("SF_ACCOUNT_ID"),
    sf_login_name=os.environ.get("SF_LOGIN_NAME"),
    sf_pwd=os.environ.get("SF_PWD"),
)
