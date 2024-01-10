import http
import http.cookies
import http.server
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
    auth_token: str = None,
):
    start_time = time.time()

    try:
        session = requests.Session()
        session.verify = False
        session.max_redirects = 0

        headers = requests.models.CaseInsensitiveDict()
        if referer:
            headers["Referer"] = referer
        if snowflake_context:
            headers["x-snowflake-context"] = snowflake_context
        if auth_token:
            cookie = http.cookies.SimpleCookie()
            cookie.load(auth_token)
            session.cookies.set_cookie(cookie)

        headers["Accept"] = accept_header

        content_type = request_type_header
        headers["Content-Type"] = content_type

        # As exception for the login
        # Remove sensitive data
        if rest_api_url.startswith(
            "session/authenticate-request"
        ) or rest_api_url.startswith("session/v1/login-request"):
            pattern = r'"PASSWORD": "(.*)"'
            request_body = re.sub(
                pattern,
                r'"PASSWORD":"****"',
                request_body,
                flags=re.IGNORECASE,
            )

        response = session.post(
            base_url + "/" + rest_api_url,
            headers=headers,
            data=request_body,
            timeout=60,
        )

        if response.status_code < 400:
            result_string = response.text or ""
            logging.info(
                f"POST {base_url}/{rest_api_url} returned "
                f"{response.status_code}"
                f"({response.reason})\nRequest Headers:\n{headers}\nCookies:\n"
                "{len(result_string)}:\n{result_string}"
            )

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

            return ""
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


def random_unused_port():
    sock = socket.socket()
    sock.bind(("", 0))
    return sock.getsockname()[1]


def start_browser(url):
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
        raise NotImplementedError(
            "Unsupported platform: %s" % platform.system()
        )
