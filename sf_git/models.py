from dataclasses import dataclass, field
from enum import Enum


class AuthenticationMode(Enum):
    SSO = "SSO"
    PWD = "PWD"


class AuthenticationError(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return f"AuthenticationError: {self.message}"
        else:
            return "AuthenticationError: failed with no more information."


@dataclass
class AuthenticationContext:
    """To store authentication result information"""

    account: str = ""
    account_name: str = ""
    account_url: str = ""
    app_server_url: str = ""
    client_id: str = ""
    main_app_url: str = ""
    master_token: str = ""
    organization_id: str = ""
    region: str = ""
    snowsight_token: dict = field(default_factory=dict)
    login_name: str = ""
    username: str = ""


class SnowsightError(Enum):
    PERMISSION = "PERMISSION"
    UNKNOWN = "UNKNOWN"


class WorksheetError(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
            if len(args) > 1:
                self.snowsight_error = SnowsightError.PERMISSION
            else:
                self.snowsight_error = SnowsightError.UNKNOWN
        else:
            self.message = None
            self.snowsight_error = SnowsightError.UNKNOWN

    def __str__(self):
        if self.message:
            return (
                f"WorksheetError: {self.message}."
                f" Error type is {self.snowsight_error}"
            )
        else:
            return "WorksheetError: no more information provided"


class Worksheet:
    def __init__(
        self,
        _id: str,
        name: str,
        folder_id: str,
        folder_name: str,
        content: str = "To be filled",
        content_type: str = "sql",
    ):
        self._id = _id
        self.name = name
        self.folder_id = folder_id
        self.folder_name = folder_name
        self.content = content
        self.content_type = content_type

    def to_dict(self):
        return {
            "_id": self._id,
            "name": self.name,
            "folder_id": self.folder_id,
            "folder_name": self.folder_name,
            "content": self.content,
            "content_type": self.content_type,
        }


class Folder:
    def __init__(self, _id: str, name: str, worksheets=None):
        if worksheets is None:
            worksheets = []
        self._id = _id
        self.name = name
        self.worksheets = worksheets

    def to_dict(self):
        return {
            "_id": self._id,
            "name": self.name,
            "worksheets": self.worksheets,
        }


class SnowflakeGitError(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = "Not provided"

    def __str__(self):
        if self.message:
            return f"SnowflakeGitError: {self.message}."
        else:
            return "SnowflakeGitError: no more information provided"
