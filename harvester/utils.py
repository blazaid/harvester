import cgi
import http.cookiejar
import json
import re
from typing import Callable, Dict, Optional
from urllib.parse import quote, quote_plus, unquote, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPCookieProcessor, ProxyHandler, build_opener

from ._version import __version__


def force_decode(bytes_array, codecs_to_try_first=None, deep_encoding_discovery=False):
    """Forces the decoding of the supplied bytes array.

    :param bytes_array: The bytes to decode
    :param codecs_to_try_first: A codec or list of codecs to try before the default codecs. It's and optional parameter.
    :param deep_encoding_discovery: If a deep analysis is needed to dicover the encoding. For this purpose, the 3rd party
        library "chardet" is needed. If not found, an error message will be displayed and the decode process will
        continue as if deep_codec_discovery wasn't activated (i.e. False). Defaults to False.
    :return: The string decoded.
    :raises UnicodeDecodeError: If the bytes array couldn't be decoded with user supplied and default codecs.
    """
    if codecs_to_try_first is None:
        codecs_to_try_first = []
    elif isinstance(codecs_to_try_first, str):
        codecs_to_try_first = [codecs_to_try_first]

    for codec in codecs_to_try_first:
        try:
            return bytes_array.decode(codec)
        except UnicodeDecodeError:
            pass

    if deep_encoding_discovery:
        try:
            import chardet

            codec = chardet.detect(bytes_array)["encoding"]
            return bytes_array.decode(codec)
        except ImportError:
            print('deep_encoding_discovery works only with 3rd party library "chardet". Ignoring deep analysis.')
        except UnicodeDecodeError:
            pass

    default_codecs = [
        "utf8",
        "cp1252",
        "iso8859",
    ]
    for codec in default_codecs:
        try:
            return bytes_array.decode(codec)
        except UnicodeDecodeError:
            pass
    raise ValueError()


########################################################################################################################
# Navigation functions
#
def fetch_content(
    *,
    url: str,
    data: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
    proxy: Optional[Dict[str, str]] = None,
    cookies: Optional[http.cookiejar.CookieJar] = None,
    content_type: str = "form",
    timeout: int = 10,
    normalize_url_function: Optional[Callable[[str], str]] = None,
):
    """Sends an HTTP request and returns a tuple (content, headers, cookiejar).

    :param url: The URL to request.
    :param data: Data to be sent to the server (e.g., POST parameters).
    :param headers: Custom HTTP headers as a dictionary (e.g. {"User-Agent": "..."}).
    :param proxy: Proxy configuration in the form of a dictionary (e.g. {"http": "http://127.0.0.1:8080"}).
    :param cookies: An instance of `http.cookiejar.CookieJar` that holds cookies to be reused or persisted across
        requests.
    :param content_type: Defines how the `data` should be encoded. Supported values are "form" for
        application/x-www-form-urlencoded and "json" for JSON. For other content types, handle the encoding manually.
    :param timeout: Maximum time (in seconds) to wait for a response.
    :param normalize_url_function: An optional function to normalize the URL before making the request (e.g., adding
        http:// if missing).
    :return: A tuple consisting of the response content (in bytes or a string indicating an error), the response headers
        as a dictionary, and the `CookieJar` used in this request.
    :raises ValueError: If an unsupported `content_type` is provided.
    :raises urllib.error.HTTPError: If the server returns an HTTP error (e.g., 404, 500, ...)
    :raises urllib.error.URLError: If the URL is invalid or the server is unreachable (e.g., unreachable server, DNS
        failure, ...).
    :raises Exception: For any other unexpected error.

    Example usage:

    >>> content, response_headers, cj = touch(
    ...     url="http://example.com",
    ...     data={"param": "value"},
    ...     headers={"User-Agent": "The amazing harvester"},
    ...     content_type="form",
    ... )
    >>> print(content, resp_headers)
    """
    # First, let's prepare the request
    if cookies is None:
        cookies = http.cookiejar.CookieJar()
    opener = build_opener(ProxyHandler(proxy or {}), HTTPCookieProcessor(cookies))
    combined_headers = {
        **{"User-Agent": f"Harvester/{__version__}"},  # The default headers
        **(headers or {}),  # The provided ones or an empty set of headers
    }
    opener.addheaders = list(combined_headers.items())

    # Now, if data is provided, let's encode it
    data_to_send = None
    if data:
        if content_type == "form":
            # x-www-form-urlencoded
            data_to_send = urlencode(data).encode("utf-8")
        elif content_type == "json":
            # JSON
            data_to_send = json.dumps(data).encode("utf-8")
            if "Content-Type" not in combined_headers:
                combined_headers["Content-Type"] = "application/json"
            opener.addheaders = list(combined_headers.items())
        else:
            raise ValueError(f"Unsupported content_type: {content_type}")

    # If the user provided a function to normalize the url, let's do it
    if normalize_url_function is not None:
        url = normalize_url_function(url)

    # And now, the request
    response = opener.open(url, data=data_to_send, timeout=timeout)
    content = response.read()
    resp_headers = dict(response.headers.items())
    return content, resp_headers, cookies


def is_url(value):
    """Checks if the given value is an url or not.

    :param value: The possible url.
    :return: True if the parameter is an url, False otherwise.
    """
    return (
        re.match(
            r"^(?:http|ftp)s?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|"  # ...or ipv4
            r"\[?[A-F0-9]*:[A-F0-9:]+\]?)"  # ...or ipv6
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            value,
            re.IGNORECASE,
        )
        is not None
    )


def fix_url(url):
    """Fixes the url so it can be requested by urllib (i.e. spaces, odd characters, ...).

    :param url: The url to be fixed.
    :return: The url fixed.
    """
    scheme, netloc, path, qs, anchor = urlsplit(url)
    path = quote(path, "/%")
    qs = quote_plus(qs, ":&=")
    return urlunsplit((scheme, netloc, path, qs, anchor))


def parse_content_disposition_filename(value: str) -> str:
    """Parses the Content-Disposition header to extract the filename, following the RFC conventions.  Supports both
    `filename` and the RFC 5987 `filename*` parameter for encoded filenames.

    :param value: The value of the Content-Disposition header.
    :return: The filename extracted from the header, or None if no filename was found.
    :raises ValueError: If no Content-Disposition header is provided.
    """
    if not value:
        raise ValueError("No Content-Disposition header provided")

    # cgi.parse_header returns something like:
    #   ("attachment", {"filename": "myfile.txt"}) or
    #   ("attachment", {"filename*": "UTF-8''the%20fucking%20file.txt"})
    disposition, params = cgi.parse_header(value)

    filename = ""
    # Check for  first
    if "filename*" in params:
        # RFC 5987 encoded filename (e.g. filename*="UTF-8''the%20fucking%20file.txt")
        encoded = params["filename*"]
        parts = encoded.split("'", 2)
        if len(parts) == 3:
            # Format: <charset>'<language>'<percent-encoded-data>
            filename = unquote(parts[2])
        else:
            # Splitting didn't work, so fallback to raw
            filename = encoded
    elif "filename" in params:
        # Normal filename
        filename = params["filename"]

    return filename
