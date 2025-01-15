import http.cookiejar
import urllib.error
from email.message import Message
from unittest.mock import MagicMock, patch
from urllib.request import HTTPCookieProcessor, ProxyHandler

import pytest

from harvester.utils import fetch_content


@pytest.fixture
def mock_response():
    """Creates a mock response object with .read() and .headers for testing."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"Mocked response content"
    mock_resp.headers = {"Content-Type": "text/html", "Server": "MockServer"}
    return mock_resp


@pytest.fixture
def mock_urlopen_fixture(mock_response):
    """Function to mock the urlopen function for testing fetch_content."""

    def mock_urlopen(*args, **kwargs):
        return mock_response

    with patch("urllib.request.OpenerDirector.open", new=mock_urlopen):
        yield


@pytest.mark.parametrize("content_type", ["form", "json"])
def test_fetch_content_success(mock_urlopen_fixture, content_type):
    """Test successful requests with both 'form' and 'json' content types."""
    content, headers, cj = fetch_content(
        url="http://example.com",
        data={"key": "value"},
        content_type=content_type,
    )

    assert content == b"Mocked response content"
    assert headers.get("Content-Type") == "text/html"
    assert headers.get("Server") == "MockServer"
    assert isinstance(cj, http.cookiejar.CookieJar)


def test_fetch_content_no_data(mock_urlopen_fixture):
    """Test calling the function without passing data to ensure it still returns a response."""
    content, headers, cj = fetch_content(url="http://example.com")

    assert content == b"Mocked response content"
    assert headers.get("Server") == "MockServer"
    assert isinstance(cj, http.cookiejar.CookieJar)


def test_fetch_content_custom_headers(mock_urlopen_fixture):
    """Ensure that custom headers are appended or overwritten correctly."""
    content, headers, _ = fetch_content(
        url="http://example.com", headers={"User-Agent": "CustomAgent/2.0", "X-Api-Key": "12345"}
    )

    assert content == b"Mocked response content"
    assert headers["Server"] == "MockServer"


def test_fetch_content_invalid_content_type():
    """Verifies that ValueError is raised if an unsupported content_type is provided."""
    with pytest.raises(ValueError) as e:
        fetch_content(data={"pot": "ato"}, url="http://example.com", content_type="xml")

    assert "Unsupported content_type: xml" in str(e.value)


def test_fetch_content_normalize_url(mock_urlopen_fixture):
    """Tests the usage of the normalize_url_function to transform the URL."""
    content, headers, _ = fetch_content(url="example.com", normalize_url_function=lambda _: "http://example.com")

    assert content == b"Mocked response content"


def test_fetch_content_with_proxy(monkeypatch, mock_response):
    """Tests that a proxy dictionary is passed to the ProxyHandler."""

    with patch("harvester.utils.build_opener") as mock_build_opener:
        # Create a simulated instace of 'opener' that returns 'mock_response' when .open() is called
        mock_opener_instance = MagicMock()
        mock_opener_instance.open.return_value = mock_response

        # Now, if build_opener(...) is called, then our 'opener' mock will be returned
        mock_build_opener.return_value = mock_opener_instance

        # Let's fetch the content with a proxy
        content, headers, cookie_jar = fetch_content(url="http://example.com", proxy={"http": "http://127.0.0.1:8080"})

        # Ensure that build_opener was called once
        mock_build_opener.assert_called_once()

        # Ensure that the number of arguments were instances of ProxyHandler and HTTPCookieProcessor and that they have
        # the expected values
        called_args = mock_build_opener.call_args[0]
        assert len(called_args) == 2

        proxy_handler = called_args[0]
        assert isinstance(proxy_handler, ProxyHandler)
        assert getattr(proxy_handler, "proxies", None) == {"http": "http://127.0.0.1:8080"}

        cookie_processor = called_args[1]
        assert isinstance(cookie_processor, HTTPCookieProcessor)

        # Ensure that the opener was called with the URL and expected values
        mock_opener_instance.open.assert_called_once_with("http://example.com", data=None, timeout=10)

        # Finally, check that the content and headers are the same as the mock_response
        assert content == b"Mocked response content"
        assert headers.get("Server") == "MockServer"
        assert isinstance(cookie_jar, http.cookiejar.CookieJar)


def test_fetch_content_with_cookies(mock_urlopen_fixture):
    """Verifies that a CookieJar can be provided and returned with updated cookies."""
    my_cj = http.cookiejar.CookieJar()
    content, headers, returned_cj = fetch_content(url="http://example.com", cookies=my_cj)

    assert returned_cj is my_cj
    assert content == b"Mocked response content"


def test_fetch_content_timeout(monkeypatch, mock_response):
    """Test that the timeout parameter is used. We simply ensure it doesn't raise errors when a timeout is provided."""
    check_timeout = 5

    def mock_urlopen(self, req, data=None, timeout=None):
        assert timeout == check_timeout
        return mock_response

    with patch("urllib.request.OpenerDirector.open", new=mock_urlopen):
        content, headers, _ = fetch_content(url="http://example.com", timeout=check_timeout)

    assert content == b"Mocked response content"


def test_fetch_content_http_error(monkeypatch):
    """Test that an HTTPError is raised if the server returns an HTTP error."""

    def mock_urlopen(*args, **kwargs):
        raise urllib.error.HTTPError(url="http://example.com", code=404, msg="Not Found", hdrs=Message(), fp=None)

    with patch("urllib.request.OpenerDirector.open", new=mock_urlopen):
        with pytest.raises(urllib.error.HTTPError) as e:
            fetch_content(url="http://example.com")

    assert e.value.code == 404
    assert "Not Found" in str(e.value)


def test_fetch_content_url_error(monkeypatch):
    """Test that a URLError is raised if the URL is invalid or unreachable."""

    def mock_urlopen(*args, **kwargs):
        raise urllib.error.URLError("Name or service not known")

    with patch("urllib.request.OpenerDirector.open", new=mock_urlopen):
        with pytest.raises(urllib.error.URLError) as e:
            fetch_content(url="http://invalid_url")

    assert "Name or service not known" in str(e.value)


def test_fetch_content_generic_exception(monkeypatch):
    """Test that a generic Exception is raised for other unexpected errors."""

    def mock_urlopen(*args, **kwargs):
        raise Exception("Something unexpected happened")

    with patch("urllib.request.OpenerDirector.open", new=mock_urlopen):
        with pytest.raises(Exception) as e:
            fetch_content(url="http://example.com")

    assert "Something unexpected happened" in str(e.value)
