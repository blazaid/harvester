import pytest

from harvester.models import CharField


@pytest.fixture
def mock_model():
    """Return a mock model with a content method that returns the given content."""
    class MockModel:
        def __init__(self, content):
            self._content = content

        def content(self):
            return self._content

    return MockModel


def test_charfield_basic_extraction(mock_model):
    """Test basic extraction of a CharField."""
    field = CharField(start="<tag>", end="</tag>")
    model = mock_model("<tag>Test</tag>")

    assert field(model) == "Test"


def test_charfield_as_list(mock_model):
    """Test extraction of a CharField as a list."""
    field = CharField(start="<tag>", end="</tag>", as_list=True)
    model = mock_model("<tag>Test1</tag><tag>Test2</tag>")

    assert field(model) == ["Test1", "Test2"]


def test_charfield_with_prefix(mock_model):
    """Test extraction of a CharField with a prefix."""
    class MockModelWithPrefix:
        def __init__(self, content, prefix):
            self._content = content
            self.prefix_field = prefix

        def content(self):
            return self._content

    model = MockModelWithPrefix("<tag>Test</tag>", "Prefix-")
    field = CharField(start="<tag>", end="</tag>", prefix="prefix_field")

    assert field(model) == "Prefix-Test"


def test_charfield_with_suffix(mock_model):
    """Test extraction of a CharField with a suffix."""
    class MockModelWithSuffix:
        def __init__(self, content, suffix):
            self._content = content
            self.suffix_field = suffix

        def content(self):
            return self._content

    model = MockModelWithSuffix("<tag>Test</tag>", "-Suffix")
    field = CharField(start="<tag>", end="</tag>", suffix="suffix_field")

    assert field(model) == "Test-Suffix"


def test_charfield_strip_tags(mock_model):
    """Test extraction of a CharField with tags stripped."""
    field = CharField(start="<tag>", end="</tag>", strip_tags=True)
    model = mock_model("<tag><b>Bold</b></tag>")

    assert field(model) == "Bold"


def test_charfield_decode_html(mock_model):
    """Test extraction of a CharField with HTML entities decoded."""
    field = CharField(start="<tag>", end="</tag>", decode_html=True)
    model = mock_model("<tag>&amp;</tag>")

    assert field(model) == "&"


def test_charfield_stripped(mock_model):
    """Test extraction of a CharField with stripped content."""
    field = CharField(start="<tag>", end="</tag>", stripped=True)
    model = mock_model("<tag>   Test   </tag>")

    assert field(model) == "Test"


def test_charfield_with_empty_content(mock_model):
    """Test extraction of a CharField with empty content."""
    field = CharField(start="<tag>", end="</tag>")
    model = mock_model("")

    assert field(model) is None


def test_charfield_with_no_match(mock_model):
    """Test extraction of a CharField with no match."""
    field = CharField(start="<tag>", end="</tag>")
    model = mock_model("<other>Content</other>")

    assert field(model) is None
