import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from harvester.models import FileField


@pytest.fixture
def mock_model():
    """Returns a mock object that mimics the interface of the underlying model."""
    mock = MagicMock()
    mock.request_headers.return_value = {"User-Agent": "The one, the only, the harvester!"}
    mock.proxy.return_value = {"http": "http://127.0.0.1:8080"}
    mock.cookies.return_value = None
    mock.base_url.return_value = "http://base-url.com"
    mock.response_headers.return_value = {}
    return mock


@pytest.fixture
def temp_upload_dir():
    """Creates a temporary directory to use as the 'upload_to' path. Cleans up after tests."""
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath)


@pytest.fixture
def file_field_instance(mock_model, temp_upload_dir):
    """Returns an instance of FileField with a mocked _model and a known upload directory."""
    field = FileField(start="start", end="end", upload_to=temp_upload_dir)
    field._model = mock_model
    return field


@pytest.fixture
def mock_fetch_content():
    """Fixture to patch 'fetch_content'  that yields a MagicMock to simulate network responses or exceptions."""
    with patch("harvester.models.fetch_content") as mock_fc:
        yield mock_fc


def test_is_absolute(file_field_instance):
    """Test is_absolute() returns True for a proper absolute URL."""
    assert file_field_instance.is_absolute("http://example.com") is True
    assert file_field_instance.is_absolute("https://example.com/path") is True
    assert file_field_instance.is_absolute("/some/path") is False
    assert file_field_instance.is_absolute("images/test.jpg") is False


def test_as_absolute_with_absolute_url(file_field_instance):
    """as_absolute() should return the same URL if it is already absolute."""
    original_url = "https://example.com/resource"
    result = file_field_instance.as_absolute(original_url)
    assert result == original_url


def test_as_absolute_with_relative_url(file_field_instance, mock_model):
    """If the URL is relative, as_absolute() should prepend the model's base_url."""
    mock_model.base_url.return_value = "http://base-url.com"
    relative_url = "images/photo.png"
    full_url = file_field_instance.as_absolute(relative_url)
    assert full_url == "http://base-url.com/images/photo.png"


@pytest.mark.parametrize(
    "cd_header,expected_filename",
    [
        ("attachment; filename=test.txt", "test.txt"),
        ('inline; filename="mydoc.pdf"', "mydoc.pdf"),
        ("form-data; name=file; filename=some_image.jpg", "some_image.jpg"),
    ],
)
def test_process_content_disposition_filename(file_field_instance, mock_fetch_content, cd_header, expected_filename):
    """If 'Content-Disposition' header has a filename, that filename should be used."""
    mock_fetch_content.return_value = (b"fake file content", {"Content-Disposition": cd_header}, None)

    url = "http://example.com/file"
    saved_path = file_field_instance.process(url)

    assert saved_path is not None
    assert os.path.exists(saved_path)

    assert saved_path.endswith(expected_filename)

    with open(saved_path, "rb") as f:
        assert f.read() == b"fake file content"


def test_process_no_content_disposition_uses_value_as_filename(file_field_instance, mock_fetch_content):
    """If there's no Content-Disposition or no filename, fall back to 'value' as the filename."""
    mock_fetch_content.return_value = (
        b"content with no cd header",
        {"Server": "MockServer"},  # no Content-Disposition
        None,
    )

    url = "http://example.com/path/to/file.dat"
    saved_path = file_field_instance.process(url)
    assert saved_path is not None
    assert os.path.exists(saved_path)

    # Should default to 'file.dat' from the URL
    assert saved_path.endswith("file.dat")

    with open(saved_path, "rb") as f:
        assert f.read() == b"content with no cd header"


def test_process_warn_on_error_true_returns_none_if_exception(file_field_instance, mock_fetch_content, caplog):
    """If warn_on_error=True and an exception occurs, a warning is logged and process() returns None."""
    file_field_instance.warn_on_error = True
    mock_fetch_content.side_effect = Exception("Network error")

    result = file_field_instance.process("http://example.com/fail")

    assert result is None
    assert any("Error downloading file:" in record.msg for record in caplog.records)
    assert any("Network error" in str(record.message) for record in caplog.records)


def test_process_warn_on_error_false_raises_exception(file_field_instance, mock_fetch_content):
    """If warn_on_error=False and an exception occurs, the exception is raised."""
    file_field_instance.warn_on_error = False
    mock_fetch_content.side_effect = Exception("Critical network failure")

    with pytest.raises(Exception) as exc_info:
        file_field_instance.process("http://example.com/fail")

    assert "Critical network failure" in str(exc_info.value)


def test_process_file_already_exists_creates_new_name(file_field_instance, mock_fetch_content, temp_upload_dir):
    """If a file with the same name already exists, the method should generate a new path with a numeric suffix."""
    existing_path = os.path.join(temp_upload_dir, "already_exists.txt")
    with open(existing_path, "wb") as f:
        f.write(b"old content")

    mock_fetch_content.return_value = (
        b"new content",
        {"Content-Disposition": "inline; filename=already_exists.txt"},
        None,
    )

    saved_path = file_field_instance.process("http://example.com/file")

    with open(existing_path, "rb") as f:
        assert f.read() == b"old content"

    assert saved_path != existing_path
    assert os.path.exists(saved_path)
    with open(saved_path, "rb") as f:
        assert f.read() == b"new content"


def test_process_auto_extension_from_image(file_field_instance, mock_fetch_content):
    """If there's no extension in the filename, we try to detect an image type from the raw content via imghdr."""
    # Suppose the content is recognized as a PNG
    sample_png_header = b"\x89PNG\r\n\x1a\n"  # typical PNG signature
    mock_fetch_content.return_value = (
        sample_png_header,
        {"Content-Disposition": "attachment; filename=image_no_ext"},
        None,
    )

    with patch("imghdr.what", return_value="png"):
        saved_path = file_field_instance.process("http://example.com/imagefile")

    assert saved_path.endswith(".png")
    assert os.path.exists(saved_path)


def test_process_auto_extension_from_mimetype(file_field_instance, mock_fetch_content, mock_model):
    """If no extension and it's not an image, we attempt to guess from the 'Content-Type' in response_headers()."""
    mock_fetch_content.return_value = (
        b"just some raw data",
        {"Content-Disposition": "attachment; filename=unknownfile"},
        None,
    )

    mock_model.response_headers.return_value = {"Content-Type": "application/pdf"}

    saved_path = file_field_instance.process("http://example.com/unknown")

    assert saved_path.endswith(".pdf")
    assert os.path.exists(saved_path)


def test_process_no_extension_no_image_no_mimetype(file_field_instance, mock_fetch_content, mock_model):
    """If there's no extension, not an image, and no recognized mime type, we end up with no extension at all."""
    mock_fetch_content.return_value = (b"some data", {"Content-Disposition": "attachment; filename=myfile"}, None)
    mock_model.response_headers.return_value = {}  # no content type

    saved_path = file_field_instance.process("http://example.com/blank")

    assert saved_path.endswith("myfile")
    assert os.path.exists(saved_path)
