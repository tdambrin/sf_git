import os
from pathlib import Path, WindowsPath
import platform


SF_MAIN_APP_URL = "https://app.snowflake.com"

# Root of Git repository for worksheets versioning
REPO_PATH = Path(os.environ["SNOWFLAKE_VERSIONING_REPO"]).absolute()
WORKSHEETS_PATH = Path(
    os.environ.get("WORKSHEETS_PATH") or "/tmp/snowflake_worksheets"
).absolute()
if platform.system() == "Windows":
    REPO_PATH = WindowsPath(REPO_PATH)
    WORKSHEETS_PATH = WindowsPath(WORKSHEETS_PATH)


SF_ACCOUNT_ID = os.environ.get("SF_ACCOUNT_ID")
SF_LOGIN_NAME = os.environ.get("SF_LOGIN_NAME")
SF_PWD = os.environ.get("SF_PWD")
