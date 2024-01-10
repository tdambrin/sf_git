import json
from urllib import parse
import pandas as pd
import requests
from typing import Optional

from sf_git.cache import save_worksheets_to_cache
from sf_git.models import (
    AuthenticationContext,
    Folder,
    SnowsightError,
    Worksheet,
    WorksheetError,
)


def get_worksheets(
    auth_context: AuthenticationContext,
    store_to_cache: Optional[bool] = False,
    only_folder: Optional[str]=None
) -> list:
    """
    Get list of worksheets available for authenticated user
    """

    optionsparams = (
        '{"sort":{"col":"viewed","dir":"desc"},"limit":500,"owner":null,'
        '"types":["query", "folder"],"showNeverViewed":"if-invited"}'
    )

    request_json_template = {
        "options": optionsparams,
        "location": "worksheets",
    }
    req_body = parse.urlencode(request_json_template)

    sf_context_name = auth_context.username
    snowflake_context = f"{sf_context_name}::{auth_context.account_url}"

    res = requests.post(
        f"{auth_context.app_server_url}/v0/organizations/"
        f"{auth_context.organization_id}/entities/list",
        data=req_body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Snowflake-Context": snowflake_context,
            "Referer": auth_context.main_app_url,
        },
        cookies=auth_context.snowsight_token,
        timeout=90,
    )

    if res.status_code != 200:
        raise WorksheetError(
            "Failed to get worksheet list\n" f"\t Reason is {res.text}"
        )
    res_data = json.loads(res.text)
    entities = res_data["entities"]
    contents = res_data["models"]["queries"]

    worksheets = []
    for worksheet in entities:
        if only_folder is not None and worksheet["info"]["folderName"] != only_folder:
            continue
        if worksheet["entityType"] == "query":
            current_ws = Worksheet(
                worksheet["entityId"],
                worksheet["info"]["name"],
                worksheet["info"]["folderId"],
                worksheet["info"]["folderName"],
                content_type=worksheet["info"]["queryLanguage"],
            )
            worksheets.append(current_ws)
    for i, _ in enumerate(worksheets):
        content = contents[worksheets[i]._id]
        if "query" in content.keys():
            worksheets[i].content = content["query"]
        else:
            worksheets[i].content = ""

    if store_to_cache:
        save_worksheets_to_cache(worksheets)

    return worksheets


def print_worksheets(worksheets: list, n=10):
    worksheets_df = pd.DataFrame([ws.to_dict() for ws in worksheets])
    print(worksheets_df.head(n))


def write_worksheet(
    auth_context: AuthenticationContext, worksheet: Worksheet
) -> Optional[WorksheetError]:
    """Write local worksheet to Snowsight worksheet."""

    request_json_template = {
        "action": "saveDraft",
        "id": worksheet._id,
        "projectId": worksheet._id,
        "query": worksheet.content,
    }

    req_body = parse.urlencode(request_json_template)

    sf_context_name = auth_context.username
    snowflake_context = f"{sf_context_name}::{auth_context.account_url}"
    res = requests.post(
        f"{auth_context.app_server_url}/v0/queries",
        data=req_body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Snowflake-Context": snowflake_context,
            "Referer": auth_context.main_app_url,
        },
        cookies=auth_context.snowsight_token,
        timeout=90,
    )

    if res.status_code != 200:
        error_type = (
            SnowsightError.PERMISSION
            if res.status_code == 403
            else SnowsightError.UNKNOWN
        )
        return WorksheetError(
            f"Failed to write worksheet {worksheet.name}\n"
            f"\t Reason is {res.text}",
            error_type,
        )


def create_worksheet(
    auth_context: AuthenticationContext,
    worksheet_name: str,
    folder_id: str = None,
) -> str:
    """Create empty worksheet on Snowsight user workspace.

    :returns: str new worksheet id.
    """

    request_json_template = {
        "action": "create",
        "orgId": auth_context.organization_id,
        "name": worksheet_name,
    }

    if folder_id:
        request_json_template["folderId"] = folder_id

    req_body = parse.urlencode(request_json_template)

    sf_context_name = auth_context.username
    snowflake_context = f"{sf_context_name}::{auth_context.account_url}"

    res = requests.post(
        f"{auth_context.app_server_url}/v0/queries",
        data=req_body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Snowflake-Context": snowflake_context,
            "Referer": auth_context.main_app_url,
        },
        cookies=auth_context.snowsight_token,
        timeout=90,
    )

    if res.status_code != 200:
        raise WorksheetError(
            f"Failed to create worksheet {worksheet_name}\n"
            f"\t Reason is {res.text}"
        )
    response_data = json.loads(res.text)
    return response_data["pid"]


def get_folders(auth_context: AuthenticationContext) -> list:
    """
    Get list of folders on authenticated user workspace
    """

    optionsparams = (
        '{"sort":{"col":"viewed","dir":"desc"},"limit":500,"owner":null,'
        '"types":["query", "folder"],"showNeverViewed":"if-invited"}'
    )

    request_json_template = {
        "options": optionsparams,
        "location": "worksheets",
    }
    req_body = parse.urlencode(request_json_template)

    sf_context_name = auth_context.username
    snowflake_context = f"{sf_context_name}::{auth_context.account_url}"

    res = requests.post(
        f"{auth_context.app_server_url}/v0/organizations/"
        f"{auth_context.organization_id}/entities/list",
        data=req_body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Snowflake-Context": snowflake_context,
            "Referer": auth_context.main_app_url,
        },
        cookies=auth_context.snowsight_token,
        timeout=90,
    )

    if res.status_code != 200:
        raise WorksheetError(
            "Failed to get folder list\n" f"\t Reason is {res.text}"
        )
    res_data = json.loads(res.text)
    entities = res_data["entities"]

    folders = []
    for entity in entities:
        if entity["entityType"] == "folder":
            current_folder = Folder(
                entity["entityId"],
                entity["info"]["name"],
            )
            folders.append(current_folder)
    return folders


def print_folders(folders: list, n=10):
    folders_df = pd.DataFrame([f.to_dict() for f in folders])
    print(folders_df.head(n))


def create_folder(
    auth_context: AuthenticationContext, folder_name: str
) -> str:
    """Create empty folder on Snowsight user workspace.

    :returns: str new folder id.
    """

    request_json_template = {
        "orgId": auth_context.organization_id,
        "name": folder_name,
        "type": "list",
        "visibility": "private",
    }

    req_body = parse.urlencode(request_json_template)

    sf_context_name = auth_context.username
    snowflake_context = f"{sf_context_name}::{auth_context.account_url}"

    res = requests.post(
        f"{auth_context.app_server_url}/v0/folders",
        data=req_body,
        headers={
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Snowflake-Context": snowflake_context,
            "Referer": auth_context.main_app_url,
        },
        cookies=auth_context.snowsight_token,
        timeout=90,
    )

    if res.status_code != 200:
        raise WorksheetError(
            f"Failed to create folder {folder_name}\n"
            f"\t Reason is {res.text}"
        )
    response_data = json.loads(res.text)
    return response_data["createdFolderId"]


def upload_to_snowsight(
    auth_context: AuthenticationContext, worksheets: list
) -> Optional[list]:
    """
    Upload worksheets to Snowsight user workspace
    keeping folder architecture.
    """

    ss_folders = get_folders(auth_context)
    ss_folders = {folder.name: folder for folder in ss_folders}

    ss_worksheets = get_worksheets(auth_context)
    ss_worksheets = {ws.name: ws for ws in ss_worksheets}

    print(
        " ## Writing local worksheet to SnowSight"
        f" for user {auth_context.username} ##"
    )
    worksheet_errors = []
    for ws in worksheets:
        # folder management
        if ws.folder_name:
            if ws.folder_name in ss_folders.keys():
                folder_id = ss_folders[ws.folder_name]._id
            else:
                print(f"creating folder {ws.folder_name}")
                folder_id = create_folder(auth_context, ws.folder_name)
        else:
            folder_id = None

        # worksheet management
        if ws.name not in ss_worksheets.keys():
            print(f"creating worksheet {ws.name}")
            worksheet_id = create_worksheet(auth_context, ws.name, folder_id)
            update_content = True
        else:
            worksheet_id = ws._id
            update_content = ws.content != ss_worksheets[ws.name].content

        # content management
        if ws.content and update_content:
            print(f"updating worksheet {ws.name}")
            err = write_worksheet(
                auth_context,
                Worksheet(
                    worksheet_id,
                    ws.name,
                    folder_id,
                    ws.folder_name,
                    ws.content,
                ),
            )
            if err is not None:
                worksheet_errors.append({"name": ws.name, "error": err})

    print(" ## SnowSight updated ##")

    if len(worksheet_errors) > 1:
        return worksheet_errors
