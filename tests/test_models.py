import http.cookiejar
import time
from unittest.mock import patch

import pytest

from harvester.models import CircularDependencyError, FieldNotFoundError, Model


def mock_basic_fetch_content(url, data=None, headers=None, proxy=None, cookies=None):
    return b"Hello from URL", {"Content-Type": "text/html"}, http.cookiejar.CookieJar()


def test_model_requires_url_or_content():
    with pytest.raises(ValueError):
        Model()


def test_model_init_with_content_only():
    model = Model(content="Test content only")
    assert model.content() == "Test content only"
    assert model.url() is None


def test_model_init_with_url_only(monkeypatch):

    with patch("harvester.models.fetch_content", new=mock_basic_fetch_content):
        model = Model(url="http://example.com")

    assert model.url() == "http://example.com"
    assert model.content() == "Hello from URL"


def test_model_enable_cache(monkeypatch):
    calls = []

    def mock_fetch_content(url, data=None, headers=None, proxy=None, cookies=None):
        calls.append(url)
        return b"Cached content", {"Content-Type": "text/html"}, http.cookiejar.CookieJar()

    with patch("harvester.models.fetch_content", new=mock_fetch_content):
        model1 = Model(url="http://example.com", enable_cache=True)
        model2 = Model(url="http://example.com", enable_cache=True)

    assert model1.content() == "Cached content"
    assert model2.content() == "Cached content"
    assert len(calls) == 1


def test_model_wait_about(monkeypatch):
    sleep_times = []

    def mock_sleep(t):
        sleep_times.append(t)

    monkeypatch.setattr(time, "sleep", mock_sleep)

    with patch("harvester.models.fetch_content", new=mock_basic_fetch_content):
        Model(url="http://example.com", wait_about=1)

    assert len(sleep_times) == 1
    assert 1 <= sleep_times[0] <= 2.5


def test_model_response_headers(monkeypatch):
    def mock_fetch_content(url, data=None, headers=None, proxy=None, cookies=None):
        return b"content", {"Content-Type": "text/plain", "X-Test": "Value"}, cookies

    with patch("harvester.models.fetch_content", new=mock_fetch_content):
        model = Model(url="http://example.com")

    assert model.response_headers()["Content-Type"] == "text/plain"
    assert model.response_headers()["X-Test"] == "Value"


def test_model_base_url(monkeypatch):
    with patch("harvester.models.fetch_content", new=mock_basic_fetch_content):
        model = Model(url="http://example.com", wait_about=1)

    assert model.base_url() == "http://example.com"


def test_model_field_dependency_error(monkeypatch):
    """Case where two fields depend on each other cyclically."""
    from harvester.models import CharField

    class CyclicModel(Model):
        field_a = CharField(start="A", end="B", deps=["field_b"])
        field_b = CharField(start="B", end="C", deps=["field_a"])

    with patch("harvester.models.fetch_content", new=mock_basic_fetch_content):
        with pytest.raises(CircularDependencyError):
            _ = CyclicModel(url="http://example.com")


def test_model_field_not_found_error(monkeypatch):
    """Case where a field specifies a name that does not exist as a dependency."""
    from harvester.models import CharField

    class WrongDepsModel(Model):
        field_a = CharField(start="A", end="B", deps=["field_b"])  # no existe field_b

    with patch("harvester.models.fetch_content", new=mock_basic_fetch_content):
        with pytest.raises(FieldNotFoundError):
            _ = WrongDepsModel(url="http://example.com")
