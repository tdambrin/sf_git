import logging
import platform
import re
import socket
import subprocess
import time

import requests


def api_post(
    base_url: str,
    rest_api_url: str,
    accept_header: str,
    request_body: str = None,
    request_type_header: str = None,
    snowflake_context: str = None,
    referer: str = None,
    csrf: str = None,
    cookies: requests.cookies.RequestsCookieJar = None,  # noqa
    allow_redirect: bool = False,
    as_obj: bool = False,
):
    start_time = time.time()

    if not base_url.endswith("/"):
        base_url += "/"

    try:
        session = requests.Session()
        session.verify = False
        session.max_redirects = 20

        headers = requests.models.CaseInsensitiveDict()
        if referer:
            headers["Referer"] = referer
        if snowflake_context:
            headers["x-snowflake-context"] = snowflake_context
        if cookies:
            session.cookies.update(cookies)
        if csrf:
            headers["X-CSRF-Token"] = csrf

        headers["Accept"] = accept_header

        content_type = request_type_header
        headers["Content-Type"] = content_type

        response = session.post(
            base_url + rest_api_url,
            headers=headers,
            data=request_body,
            timeout=60,
            allow_redirects=allow_redirect,
        )

        if response.status_code < 400:
            result_string = response.text or ""
            logging.info(
                f"POST {base_url}/{rest_api_url} returned "
                f"{response.status_code}"
                f"({response.reason})\nRequest Headers:\n{headers}\nCookies:\n"
                f"{len(result_string)}:\n{result_string}"
            )
            if as_obj:
                return response
            return result_string
        else:
            result_string = response.text or ""
            cookies_list = response.headers.get("Set-Cookie")
            if result_string:
                logging.error(
                    f"POST {base_url}/{rest_api_url}"
                    f" returned {response.status_code}"
                    f" ({response.reason})\n"
                    f"Request Headers:\n{headers}\n"
                    f"Cookies:\n{cookies_list}\n"
                    f"Request:\n{request_body}\n"
                    f"Response Length {len(result_string)}"
                )
            else:
                logging.error(
                    f"POST {base_url}/{rest_api_url} "
                    f"returned {response.status_code}\n"
                    f"Request Headers:\n{headers}\nCookies:\n{cookies_list}\n"
                    f"Request:\n{request_body}"
                )
            if response.status_code in (401, 403):
                logging.warning(
                    f"POST {base_url}/{rest_api_url} "
                    f"returned {response.status_code} ({response.reason}),"
                    f" Request:\n{request_body}"
                )

            response.raise_for_status()
    except requests.exceptions.RequestException as ex:
        logging.error(
            f"POST {base_url}/{rest_api_url} "
            f"threw {ex.__class__.__name__} ({ex})"
        )
        logging.error(ex)

        logging.error(
            f"POST {base_url}/{rest_api_url} "
            f"threw {ex.__class__.__name__} ({ex})"
        )

        return ""
    finally:
        elapsed_time = time.time() - start_time
        logging.info(f"POST {base_url}/{rest_api_url} took {elapsed_time:.2f}")


def api_get(
    base_url: str,
    rest_api_url: str,
    accept_header: str,
    snowflake_context: str = None,
    referer: str = None,
    csrf: str = None,
    cookies: requests.cookies.RequestsCookieJar = None,  # noqa
    allow_redirect: bool = True,
    as_obj: bool = False,
):
    start_time = time.time()

    if not base_url.endswith("/"):
        base_url += "/"
    try:
        session = requests.Session()
        session.verify = False
        session.max_redirects = 20

        headers = requests.models.CaseInsensitiveDict()
        if referer:
            headers["Referer"] = referer
        if snowflake_context:
            headers["x-snowflake-context"] = snowflake_context
        if cookies:
            session.cookies.update(cookies)
        if csrf:
            headers["X-CSRF-Token"] = csrf

        headers["Accept"] = accept_header

        response = session.get(
            base_url + rest_api_url,
            headers=headers,
            timeout=60,
            allow_redirects=allow_redirect,
        )

        if response.status_code < 400:
            result_string = response.text or ""
            logging.info(
                f"POST {base_url}/{rest_api_url} returned "
                f"{response.status_code}"
                f"({response.reason})\nRequest Headers:\n{headers}\nCookies:\n"
                f"{len(result_string)}:\n{result_string}"
            )
            if as_obj:
                return response
            return result_string
        else:
            result_string = response.text or ""
            cookies_list = response.headers.get("Set-Cookie")
            if result_string:
                logging.error(
                    f"GET {base_url}/{rest_api_url}"
                    f" returned {response.status_code}"
                    f" ({response.reason})\n"
                    f"Request Headers:\n{headers}\n"
                    f"Cookies:\n{cookies_list}\n"
                    f"Response Length {len(result_string)}"
                )
            else:
                logging.error(
                    f"GET {base_url}/{rest_api_url} "
                    f"returned {response.status_code}\n"
                    f"Request Headers:\n{headers}\nCookies:\n{cookies_list}\n"
                )
            if response.status_code in (401, 403):
                logging.warning(
                    f"GET {base_url}/{rest_api_url} "
                    f"returned {response.status_code} ({response.reason}),"
                )

            response.raise_for_status()
    except requests.exceptions.RequestException as ex:
        logging.error(
            f"GET {base_url}/{rest_api_url} "
            f"threw {ex.__class__.__name__} ({ex})"
        )
        logging.error(ex)

        logging.error(
            f"GET {base_url}/{rest_api_url} "
            f"threw {ex.__class__.__name__} ({ex})"
        )

        return ""
    finally:
        elapsed_time = time.time() - start_time
        logging.info(f"GET {base_url}/{rest_api_url} took {elapsed_time:.2f}")


def random_unused_port() -> int:
    sock = socket.socket()
    sock.bind(("", 0))
    return sock.getsockname()[1]


def start_browser(url: str):
    if platform.system() == "Windows":
        subprocess.Popen(
            ["cmd", "/c", "start", url.replace("&", "^&")],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    elif platform.system() == "Linux":
        subprocess.Popen(["xdg-open", url])
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", url])
    else:
        raise NotImplementedError(f"Unsupported platform: {platform.system()}")


def agg_cookies_from_responses(
    response_flow: requests.Response,
) -> requests.cookies.RequestsCookieJar:
    if not response_flow.history:
        return response_flow.cookies

    agg_cookies: requests.cookies.RequestsCookieJar = response_flow.history[
        0
    ].cookies
    for resp in response_flow.history[1:]:
        agg_cookies.update(resp.cookies)
    agg_cookies.update(response_flow.cookies)
    return agg_cookies
