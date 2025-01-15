from unittest.mock import MagicMock

from harvester.models import (
    BooleanField,
    CharField,
    FloatField,
    IntegerField,
    ModelField,
)


class FakeModel:
    def __init__(self, text="", url="http://example.com"):
        self._text = text
        self._url = url

    def content(self):
        return self._text

    def url(self):
        return self._url

    def base_url(self):
        return "http://example.com"

    def request_headers(self):
        return {}

    def response_headers(self):
        return {}

    def cookies(self):
        return None

    def proxies(self):
        return {}

    def proxy(self):
        return {}

    def disguise(self):
        return False

    def wait_about(self):
        return None

    def cache_enabled(self):
        return False

    def deep_encoding_discovery(self):
        return False


def test_boolean_field_found():
    text = "Lorem ipsum <body>some text</body>"
    model = FakeModel(text=text)
    field = BooleanField(value="text")
    result = field(model)

    assert result is True


def test_boolean_field_not_found():
    text = "Lorem ipsum <body>no hay nada</body>"
    model = FakeModel(text=text)
    field = BooleanField(value="foobar")
    result = field(model)

    assert result is False


def test_char_field_basic():
    text = "Hello, this is the start pattern:VALUEthe end pattern"
    model = FakeModel(text)
    field = CharField(start=r"start pattern:", end=r"the end pattern", stripped=True)
    result = field(model)

    assert result == "VALUE"


def test_char_field_strip_tags():
    text = "start <b>hello</b> world end"
    model = FakeModel(text)
    field = CharField(start="start", end="end", strip_tags=True)
    result = field(model)

    assert result == " hello world "


def test_integer_field_basic():
    text = "Numbers:  1,234  <b> 3,500. </b>  567"
    model = FakeModel(text)
    field = IntegerField(start="Numbers:  ", end="<b", thousands_marks=[",", "."])
    result = field(model)

    assert result == 1234


def test_float_field_basic():
    text = "Price: 1,234.56 USD"
    model = FakeModel(text)
    field = FloatField(start="Price:", end="USD", decimal_mark=".")
    result = field(model)

    assert abs(result - 1234.56) < 1e-9


def test_model_field_with_url(monkeypatch):
    """Tests if the extracted value is a URL, the class is instantiated with that URL."""
    MockModelClass = MagicMock()

    text = "Go to <a>http://example.com/detail</a> now!"
    parent_model = FakeModel(text)
    field = ModelField(cls=MockModelClass, start="<a>", end="</a>", ignore_url_process=False)
    field(parent_model)

    MockModelClass.assert_called_once_with(
        url="http://example.com/detail",
        proxies=parent_model.proxies(),
        disguise=parent_model.disguise(),
        wait_about=parent_model.wait_about(),
        enable_cache=parent_model.cache_enabled(),
        headers=parent_model.request_headers(),
        cookies=parent_model.cookies(),
        deep_encoding_discovery=parent_model.deep_encoding_discovery(),
    )
