import pytest

from harvester.utils import fix_url, force_decode, is_url


class TestUtils:

    @pytest.mark.parametrize(
        "bytes_array, expected, codecs_to_try_first, deep",
        [
            (b"Hello world", "Hello world", None, False),
            (b"Hola mundo", "Hola mundo", ["latin-1"], False),
            (b"caf\xc3\xa9", "café", None, False),
        ],
    )
    def test_force_decode_basic(self, bytes_array, expected, codecs_to_try_first, deep):
        result = force_decode(bytes_array, codecs_to_try_first=codecs_to_try_first, deep_encoding_discovery=deep)
        assert result == expected

    def test_force_decode_with_chardet_installed(self, monkeypatch):
        """Simulates that chardet is installed and detects the 'utf-8' codec."""
        try:
            import chardet  # Verificamos si está instalado, si no, saltamos el test
        except ImportError:
            pytest.skip("chardet no está instalado, se omite este test.")

        # Si chardet está instalado, probamos un caso forzando deep=True
        result = force_decode(b"caf\xc3\xa9", deep_encoding_discovery=True)
        assert result == "café"

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("http://example.com", True),
            ("https://example.com/path?query=string", True),
            ("ftp://example.com/whatever", True),
            ("not_a_url", False),
            ("www.example.com", False),  # sin protocolo
            ("", False),
        ],
    )
    def test_is_url(self, value, expected):
        assert is_url(value) == expected

    @pytest.mark.parametrize(
        "url, expected",
        [
            ("http://example.com/path with spaces?query=1", "http://example.com/path%20with%20spaces?query=1"),
            ("http://example.com/áéíóú", "http://example.com/%C3%A1%C3%A9%C3%AD%C3%B3%C3%BA"),
            ("http://example.com/path?param=valo&param2=2", "http://example.com/path?param=valo&param2=2"),
            ("https://example.com/test path/?foo=bar baz", "https://example.com/test%20path/?foo=bar+baz"),
        ],
    )
    def test_fix_url(self, url, expected):
        assert fix_url(url) == expected
