import json
import os
import re
import git
from typing import List, Optional

from sf_git.config import global_config
from sf_git.models import Worksheet, WorksheetError
from sf_git.git_utils import get_tracked_files, get_blobs_content


def save_worksheets_to_cache(worksheets: List[Worksheet]):
    """
    Save worksheets to cache.

    For each worksheet, two files are created/overriden:
        - .<ws_name>_metadata.json (worksheet infos)
        - <ws_name>.sql or <ws_name>.py (worksheet content)
    """

    print(f"[Worksheets] Saving to {global_config.worksheets_path}")
    if not os.path.exists(global_config.worksheets_path):
        os.makedirs(global_config.worksheets_path, exist_ok=True)

    for ws in worksheets:
        ws_name = re.sub(r"[ :/]", "_", ws.name)
        extension = "py" if ws.content_type == "python" else "sql"
        if ws.folder_name:
            folder_name = re.sub(r"[ :/]", "_", ws.folder_name)
            file_name = f"{folder_name}/{ws_name}.{extension}"
            worksheet_metadata_file_name = (
                f"{folder_name}/.{ws_name}_metadata.json"
            )

            # create folder if not exists
            if not os.path.exists(global_config.worksheets_path / folder_name):
                os.mkdir(global_config.worksheets_path / folder_name)
        else:
            file_name = f"{ws_name}.{extension}"
            worksheet_metadata_file_name = f".{ws_name}_metadata.json"

        with open(global_config.worksheets_path / file_name, "w") as f:
            f.write(ws.content)
        ws_metadata = {
            "name": ws.name,
            "_id": ws._id,
            "folder_name": ws.folder_name,
            "folder_id": ws.folder_id,
            "content_type": ws.content_type,
        }
        with open(
            global_config.worksheets_path / worksheet_metadata_file_name, "w"
        ) as f:
            f.write(json.dumps(ws_metadata))
    print("[Worksheets] Saved")


def load_worksheets_from_cache(
    branch_name: Optional[str] = None,
    only_folder: Optional[str] = None,
) -> List[Worksheet]:
    """
    Load worksheets from cache.
    """

    print(f"[Worksheets] Loading from {global_config.worksheets_path}")
    if not os.path.exists(global_config.worksheets_path):
        raise WorksheetError(
            "Could not retrieve worksheets from cache. "
            f"The folder {global_config.worksheets_path} does not exist"
        )

    # get file content from git utils
    repo = git.Repo(global_config.repo_path)
    # import ipdb; ipdb.set_trace()
    tracked_files = [f for f in get_tracked_files(repo, global_config.worksheets_path, branch_name)]

    # filter on worksheet files
    ws_metadata_files = [
        f for f in tracked_files if f.name.endswith("_metadata.json")
    ]
    if len(ws_metadata_files) == 0:
        return []

    # map to worksheet objects
    worksheets = []
    metadata_contents = get_blobs_content(ws_metadata_files)

    for wsf in metadata_contents.values():
        ws_metadata = json.loads(wsf)
        if only_folder and ws_metadata["folder_name"] != only_folder:
            continue
        current_ws = Worksheet(
            ws_metadata["_id"],
            ws_metadata["name"],
            ws_metadata["folder_id"],
            ws_metadata["folder_name"],
            content_type=ws_metadata.get("content_type", "sql"),
        )
        extension = "py" if current_ws.content_type == "python" else "sql"
        content_filename = re.sub(
            r"[ :/]", "_", f"{ws_metadata['name']}.{extension}"
        )

        try:
            content_blob = next(
                f for f in tracked_files if f.name == content_filename
            )
        except StopIteration:
            print(f'{content_filename} not found in {[f.name for f in tracked_files]}')
            pass  # FixMe
        ws_content_as_dict = get_blobs_content([content_blob])
        ws_content = list(ws_content_as_dict.values())[0]
        current_ws.content = ws_content
        worksheets.append(current_ws)

    return worksheets
