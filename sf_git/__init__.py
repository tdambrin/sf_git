from pathlib import Path

from dotenv import load_dotenv

__version__ = "1.4.2"

HERE = Path(__file__).parent
DOTENV_PATH: Path = HERE / "sf_git.conf"

if DOTENV_PATH.is_file():
    print(f"loading dotenv from {DOTENV_PATH}")
    load_dotenv(dotenv_path=DOTENV_PATH)
