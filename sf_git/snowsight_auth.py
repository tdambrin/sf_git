import json
import os
import re
import socket
import uuid
from typing import Any, Dict
from urllib import parse
from urllib.parse import urlparse

import requests
import urllib3

import sf_git.config as config
from sf_git.models import (
    AuthenticationContext,
    AuthenticationError,
    AuthenticationMode,
)
from sf_git.rest_utils import (
    agg_cookies_from_responses,
    api_get,
    api_post,
    random_unused_port,
    start_browser,
)

urllib3.disable_warnings()


def authenticate_to_snowsight(
    account_name: str,
    login_name: str,
    password: str,
    auth_mode: AuthenticationMode = AuthenticationMode.PWD,
) -> AuthenticationContext:
    auth_context = AuthenticationContext()
    auth_context.main_app_url = config.GLOBAL_CONFIG.sf_main_app_url
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

    # Get unverified csrf
    bootstrap_response = get_csrf_from_boostrap_cookie(auth_context)
    csrf_cookie = next(
        (c for c in bootstrap_response.cookies if c.name.startswith("csrf-")),
        None,
    )
    if not csrf_cookie:
        raise AuthenticationError("Could not get csrf from bootstrap endpoint")
    auth_context.csrf = csrf_cookie.value
    auth_context.cookies = bootstrap_response.cookies

    # Get client ID
    client_id_responses = oauth_start_get_snowsight_client_id_in_deployment(
        auth_context=auth_context
    )
    parsed = urlparse(client_id_responses.url)
    parsed_query = parse.parse_qs(parsed.query)
    auth_context.cookies = agg_cookies_from_responses(
        client_id_responses
    )  # client_id_responses.history[-1].cookies
    state = json.loads(parsed_query["state"][0])
    auth_context.oauth_nonce = state["oauthNonce"]
    auth_context.auth_originator = state.get("originator")
    auth_context.window_id = state.get("windowId")
    auth_context.auth_code_challenge = parsed_query["code_challenge"][0]
    auth_context.auth_code_challenge_method = parsed_query[
        "code_challenge_method"
    ][0]
    auth_context.auth_redirect_uri = parsed_query["redirect_uri"][0]
    auth_context.client_id = parsed_query["client_id"][0]

    if not auth_context.organization_id:
        auth_context.organization_id = os.environ.get("SF_ORGANIZATION_ID")

    # Get master token
    if auth_mode == AuthenticationMode.PWD:
        auth_response = get_token_from_credentials(
            auth_context=auth_context,
            login_name=login_name,
            password=password,
        )
        auth_response_details = json.loads(auth_response.text)
        if not auth_response_details["success"]:
            raise AuthenticationError("Invalid credentials")

        auth_context.master_token = auth_response_details["data"][
            "masterToken"
        ]
        auth_context.auth_session_token = auth_response_details["data"][
            "token"
        ]
        auth_context.server_version = auth_response_details["data"].get(
            "serverVersion"
        )

        oauth_response = oauth_get_master_token_from_credentials(
            auth_context=auth_context, login_name=login_name, password=password
        )
        oauth_response_details = json.loads(oauth_response.text)
        if not oauth_response_details["success"]:
            raise AuthenticationError("Invalid credentials")
        auth_context.master_token = oauth_response_details["data"][
            "masterToken"
        ]

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

    # Get oauth redirect
    oauth_response = oauth_authorize_get_oauth_redirect_from_oauth_token(
        auth_context=auth_context
    )
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

    # Finalize authentication
    finalized_response = oauth_complete_get_auth_token_from_redirect(
        auth_context=auth_context, url=oauth_response["data"]["redirectUrl"]
    )
    if finalized_response.status_code != 200:
        raise AuthenticationError(
            "Could not finalize authentication "
            f"for account url {auth_context.account_url} "
            f"with oauth_nonce_cookie {auth_context.oauth_nonce}"
        )
    auth_context.cookies = agg_cookies_from_responses(finalized_response)
    for cookie in finalized_response.cookies:
        if cookie.name.startswith("user"):
            auth_context.snowsight_token[cookie.name] = cookie.value
    if not auth_context.snowsight_token:
        raise AuthenticationError(
            "Finalized Authentication but didnt find a token"
            " in final response : {status_code : "
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


def get_account_app_endpoint(account_name: str) -> Dict[str, Any]:
    main_app_url = config.GLOBAL_CONFIG.sf_main_app_url
    response = api_post(
        main_app_url,
        f"v0/validate-snowflake-url?url={account_name}",
        "*/*",
    )

    return json.loads(response)


def get_csrf_from_boostrap_cookie(
    auth_context: AuthenticationContext,
) -> requests.Response:
    response = api_get(
        base_url=auth_context.main_app_url,
        rest_api_url="bootstrap",
        accept_header="*/*",
        allow_redirect=True,
        as_obj=True,
        cookies=auth_context.cookies,
    )
    return response


def oauth_start_get_snowsight_client_id_in_deployment(
    auth_context: AuthenticationContext,
) -> requests.Response:
    state_params = (
        '{"csrf":'
        f'"{auth_context.csrf}","url":"{auth_context.account_url}","windowId":"{uuid.uuid4()}","browserUrl":"{auth_context.main_app_url}"}}'  # noqa: E501
    )

    rest_api_url = (
        "start-oauth/snowflake?accountUrl="
        f"{auth_context.account_url}"
        f"&&state={parse.quote_plus(state_params)}"
    )

    response = api_get(
        base_url=auth_context.app_server_url,
        rest_api_url=rest_api_url,
        accept_header="text/html",
        csrf=auth_context.csrf,
        allow_redirect=True,
        cookies=auth_context.cookies,
        as_obj=True,
    )

    if response.status_code == 200:
        return response

    raise AuthenticationError(
        f"No client id could be retrieved for account {auth_context.account_url}"
    )


def get_token_from_credentials(
    auth_context: AuthenticationContext,
    login_name: str,
    password: str,
) -> requests.Response:
    request_body = {
        "data": {
            "ACCOUNT_NAME": auth_context.account_name.split(".")[0],
            "LOGIN_NAME": login_name,
            "PASSWORD": password,
        }
    }

    auth_response = api_post(
        base_url=auth_context.account_url,
        rest_api_url="session/v1/login-request",
        request_type_header="application/json",
        accept_header="application/json",
        request_body=json.dumps(request_body),
        cookies=auth_context.cookies,
        as_obj=True,
    )
    return auth_response


def oauth_get_master_token_from_credentials(
    auth_context: AuthenticationContext,
    login_name: str,
    password: str,
) -> requests.Response:
    state_params = (
        f'{{"csrf":"{auth_context.csrf}"'
        f',"url":"{auth_context.account_url}","browserUrl":"{auth_context.main_app_url}"'
        f',"originator":"{auth_context.auth_originator}","oauthNonce":"{auth_context.oauth_nonce}"}}'
    )

    request_body = {
        "data": {
            "ACCOUNT_NAME": auth_context.account_name.split(".")[0],
            "LOGIN_NAME": login_name,
            "clientId": auth_context.client_id,
            "redirectURI": auth_context.auth_redirect_uri,
            "responseType": "code",
            "state": state_params,
            "scope": "refresh_token",
            "codeChallenge": auth_context.auth_code_challenge,
            "codeChallengeMethod": auth_context.auth_code_challenge_method
            or "S256",
            "CLIENT_APP_ID": "Snowflake UI",
            "CLIENT_APP_VERSION": 20241007103851,
            "PASSWORD": password,
        }
    }
    return api_post(
        base_url=auth_context.account_url,
        rest_api_url="session/authenticate-request",
        accept_header="application/json",
        request_body=json.dumps(request_body),
        request_type_header="application/json",
        cookies=auth_context.cookies,
        as_obj=True,
        allow_redirect=True,
    )


def oauth_authorize_get_oauth_redirect_from_oauth_token(
    auth_context: AuthenticationContext,
) -> Dict[str, Any]:
    state_params = (
        f'{{"csrf":"{auth_context.csrf}"'
        f',"url":"{auth_context.account_url}","windowId":"{auth_context.window_id}","browserUrl":"{auth_context.main_app_url}"'  # noqa: E501
        f',"originator":"{auth_context.auth_originator}","oauthNonce":"{auth_context.oauth_nonce}"}}'
    )
    request_body = {
        "masterToken": auth_context.master_token,
        "clientId": auth_context.client_id,
        "redirectURI": auth_context.auth_redirect_uri,
        "responseType": "code",
        "state": state_params,
        "scope": "refresh_token",
        "codeChallenge": auth_context.auth_code_challenge,
        "codeChallengeMethod": auth_context.auth_code_challenge_method
        or "S256",
    }

    response_content = api_post(
        base_url=auth_context.account_url,
        rest_api_url="oauth/authorization-request",
        accept_header="application/json",
        request_body=json.dumps(request_body),
        request_type_header="application/json",
        csrf=auth_context.csrf,
        cookies=auth_context.cookies,
        allow_redirect=True,
    )

    return json.loads(response_content)


def oauth_complete_get_auth_token_from_redirect(
    auth_context: AuthenticationContext,
    url: str,
) -> requests.Response:
    headers = {
        "Accept": "*/*",
        "Referer": f"{auth_context.main_app_url}/",
    }

    response = requests.get(
        url,
        headers=headers,
        allow_redirects=True,
        timeout=10,
        cookies=auth_context.cookies,
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
