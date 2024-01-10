import json
import os
import re
import socket
from urllib import parse
from urllib.parse import urlparse

import requests
import urllib3

from sf_git.rest_utils import (
    api_post,
    random_unused_port,
    start_browser,
)
from sf_git.models import (
    AuthenticationContext,
    AuthenticationMode,
    AuthenticationError,
)
from sf_git.config import SF_MAIN_APP_URL

urllib3.disable_warnings()


def authenticate_to_snowsight(
    account_name: str,
    login_name: str,
    password: str,
    auth_mode: AuthenticationMode = AuthenticationMode.PWD,
) -> AuthenticationContext:

    auth_context = AuthenticationContext()
    auth_context.main_app_url = SF_MAIN_APP_URL
    auth_context.account_name = account_name
    auth_context.login_name = login_name

    # Get App Server Url and Account Url
    app_endpoint = get_account_app_endpoint(account_name)
    if not app_endpoint["valid"]:
        raise AuthenticationError(
            f"No valid endpoint for account {account_name}"
        )

    auth_context.account = app_endpoint["account"]
    auth_context.account_url = app_endpoint["url"]
    auth_context.app_server_url = app_endpoint["appServerUrl"]
    auth_context.region = app_endpoint["region"]

    # Get master token
    if auth_mode == AuthenticationMode.PWD:
        auth_context.master_token = get_token_from_credentials(
            auth_context.account_url,
            account_name.split(".")[0],
            login_name,
            password,
        )
    elif auth_mode == AuthenticationMode.SSO:
        redirect_port = random_unused_port()
        sso_link_response = json.loads(
            get_sso_login_link(
                auth_context.account_url,
                account_name.split(".")[0],
                login_name,
                redirect_port,
            )
        )
        idp_url = sso_link_response["data"]["ssoUrl"]
        proof_key = sso_link_response["data"]["proofKey"]
        with socket.socket() as s:
            s.bind(("localhost", redirect_port))
            start_browser(idp_url)
            s.listen(5)
            conn, addr = s.accept()
            sso_token = ""
            while True:
                data = conn.recv(8188)
                if not data:
                    break
                str_data = data.decode("utf-8")
                if "token=" in str_data:
                    str_data = str_data.split("token=")[1]
                if " HTTP" in str_data:  # end of token
                    str_data = str_data.split(" HTTP")[0]
                    sso_token += str_data
                    break
                sso_token += str_data
            s.close()
            if sso_token == "":
                raise AuthenticationError("Could not retrieve SSO token")

            auth_context.master_token = get_master_token_from_sso_token(
                auth_context.account_url,
                auth_context.account_name,
                auth_context.login_name,
                sso_token,
                proof_key,
            )

    # Get client ID
    client_id_response = oauth_start_get_snowsight_client_id_in_deployment(
        auth_context.main_app_url,
        auth_context.app_server_url,
        auth_context.account_url,
    )
    oauth_nonce_cookie = client_id_response.headers["Set-cookie"]
    redirect_uri = client_id_response.headers["Location"]
    parsed = urlparse(redirect_uri)
    auth_context.client_id = parse.parse_qs(parsed.query)["client_id"][0]
    if not auth_context.organization_id:
        auth_context.organization_id = os.environ.get("SF_ORGANIZATION_ID")

    # Get oauth redirect
    oauth_response = oauth_authorize_get_oauth_redirect_from_oauth_token(
        auth_context.account_url,
        auth_context.client_id,
        auth_context.master_token,
    )
    oauth_response = json.loads(oauth_response)
    if (
        oauth_response["code"] == "390302"
        or oauth_response["message"] == "Invalid consent request."
    ):
        print(oauth_response)
        raise AuthenticationError(
            "Could not get redirect from master token "
            f"for account url {auth_context.account_url} "
            f"and client_id {auth_context.client_id}. "
            "Please check your credentials."
        )
    redirect_with_oauth_uri = urlparse(oauth_response["data"]["redirectUrl"])
    oauth_redirect_code = parse.parse_qs(redirect_with_oauth_uri.query)[
        "code"
    ][0]

    # Finalize authentication
    finalized_response = oauth_complete_get_auth_token_from_redirect(
        auth_context.app_server_url,
        auth_context.account_url,
        oauth_redirect_code,
        oauth_nonce_cookie,
        auth_context.main_app_url,
    )
    if finalized_response.status_code != 200:
        raise AuthenticationError(
            "Could not finalize authentication "
            f"for account url {auth_context.account_url} "
            f"with oauth_nonce_cookie {oauth_nonce_cookie}"
        )
    for cookie in finalized_response.cookies:
        if cookie.name.startswith("user"):
            auth_context.snowsight_token[cookie.name] = cookie.value
    if not auth_context.snowsight_token:
        raise AuthenticationError(
            "Finalized Authentication but didnt find a token"
            "in final response : {status_code : "
            f"{finalized_response.status_code}, url : "
            f"{finalized_response.url}, cookies : "
            f"{finalized_response.cookies}"
        )

    # handle different username
    params_page = finalized_response.content.decode("utf-8")
    match = re.search("(?i)var params = ({.*})", params_page, re.IGNORECASE)
    if match is not None:
        params = match.group(0).replace("var params = ", "")
        params = json.loads(params)
        username = params["user"].get("username")
        if username:
            auth_context.username = username
        else:
            auth_context.username = login_name
    else:
        auth_context.username = login_name

    return auth_context


def get_account_app_endpoint(account_name: str):
    main_app_url = SF_MAIN_APP_URL
    response = api_post(
        main_app_url,
        f"v0/validate-snowflake-url?url={account_name}",
        "*/*",
    )

    return json.loads(response)


def get_token_from_credentials(
    account_url: str, account_name: str, login_name: str, password: str
):
    request_json_template = {
        "data": {
            "ACCOUNT_NAME": account_name,
            "LOGIN_NAME": login_name,
            "PASSWORD": password,
        }
    }
    request_body = json.dumps(request_json_template)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    auth_response = requests.post(
        f"{account_url}/session/authenticate-request",
        headers=headers,
        data=request_body,
    )
    if auth_response.status_code == 200:
        response_details = json.loads(auth_response.text)
        if response_details["success"]:
            return response_details["data"]["masterToken"]


def oauth_start_get_snowsight_client_id_in_deployment(
    main_app_url: str,
    app_server_url: str,
    account_url: str,
):
    csrf = "SnowflakePS"
    state_params = (
        '{{"isSecondaryUser":false,"csrf":'
        f'"{csrf}","url":"{account_url}","browserUrl":"{main_app_url}"}}'
    )

    rest_api_url = (
        "start-oauth/snowflake?accountUrl="
        f"{parse.quote_plus(account_url)}"
        f"&state={parse.quote_plus(state_params)}"
    )
    response = requests.get(
        f"{app_server_url}/{rest_api_url}",
        allow_redirects=False,
    )

    if response.status_code == 302:
        return response

    raise AuthenticationError(
        f"No client id could be retrieved for account {account_url}"
    )


def oauth_authorize_get_oauth_redirect_from_oauth_token(
    account_url: str,
    client_id: str,
    oauth_token: str,
):
    request_json_template = {
        "masterToken": oauth_token,
        "clientId": client_id,
    }
    request_body = json.dumps(request_json_template)

    response = api_post(
        account_url,
        "oauth/authorization-request",
        "application/json",
        request_body,
        "application/json",
    )

    return response


def oauth_complete_get_auth_token_from_redirect(
    app_server_url: str,
    account_url: str,
    oauth_redirect_code: str,
    oauth_nonce_cookie,
    main_app_url: str,
):
    csrf = "SnowflakePS"
    cookie_name_value = oauth_nonce_cookie.split(";")[0].split("=")
    cookie = {cookie_name_value[0]: cookie_name_value[1]}

    state_params = (
        f'{{"isSecondaryUser":false,"csrf":"{csrf}"'
        f',"url":"{account_url}","browserUrl":"{main_app_url}",'
        f'"oauthNonce":"{list(cookie.values())[0]}"}}'
    )
    rest_api_url = (
        f"complete-oauth/snowflake?"
        f"code={oauth_redirect_code}&state={parse.quote_plus(state_params)}"
    )

    response = requests.get(
        f"{app_server_url}/{rest_api_url}",
        headers={"Accept": "text/html"},
        cookies=cookie,
        allow_redirects=True,
    )

    return response


def get_sso_login_link(
    account_url: str,
    account_name: str,
    login_name: str,
    redirect_port: int,
):
    request_json_template = {
        "data": {
            "ACCOUNT_NAME": account_name,
            "LOGIN_NAME": login_name,
            "AUTHENTICATOR": "externalbrowser",
            "BROWSER_MODE_REDIRECT_PORT": redirect_port,
        }
    }

    request_body = json.dumps(request_json_template)

    response = api_post(
        account_url,
        "session/authenticator-request",
        "application/json",
        request_body,
        "application/json",
    )

    return response


def get_master_token_from_sso_token(
    account_url: str,
    account_name: str,
    login_name: str,
    sso_token: str,
    proof_key: str,
) -> str:
    request_json_template = {
        "data": {
            "ACCOUNT_NAME": account_name,
            "LOGIN_NAME": login_name,
            "AUTHENTICATOR": "externalbrowser",
            "TOKEN": sso_token,
            "PROOF_KEY": proof_key,
        }
    }

    request_body = json.dumps(request_json_template)

    response = api_post(
        account_url,
        "session/v1/login-request",
        "application/json",
        request_body,
        "application/json",
    )

    parsed = json.loads(response)
    if not parsed["success"]:
        raise AuthenticationError(
            "Could not retrieve master token from sso_token for user"
            f"{login_name} and account {account_name}"
        )
    return parsed["data"]["masterToken"]
