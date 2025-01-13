import pytest
import time
from unittest.mock import patch, MagicMock
from harvester.models import Model, CircularDependencyError, FieldNotFoundError


class TestModelBasic:

    def test_model_requires_url_or_content(self):
        with pytest.raises(ValueError):
            Model()  # ni url ni content

    def test_model_init_with_content_only(self):
        model = Model(content="Test content only")
        assert model.content() == "Test content only"
        assert model.url() is None

    def test_model_init_with_url_only(self, monkeypatch):
        # Mockeamos la respuesta de Model.touch para evitar requests
        def mock_touch(self, url, data=None, headers=None, proxy=None, cookies=None):
            return (b"Hello from URL", {"Content-Type": "text/html"}, cookies)

        monkeypatch.setattr(Model, "touch", mock_touch)

        model = Model(url="http://example.com")
        assert model.url() == "http://example.com"
        assert model.content() == "Hello from URL"

    def test_model_enable_cache(self, monkeypatch):
        # Probamos que si enable_cache=True, la segunda vez no se llame a la red
        calls = []

        def mock_touch(self, url, data=None, headers=None, proxy=None, cookies=None):
            calls.append(url)
            return (b"Cached content", {"Content-Type": "text/html"}, cookies)

        monkeypatch.setattr(Model, "touch", mock_touch)

        model1 = Model(url="http://example.com", enable_cache=True)
        assert model1.content() == "Cached content"

        # Creamos otro model con la misma URL
        model2 = Model(url="http://example.com", enable_cache=True)
        # Ahora no debería llamar a mock_touch, pues la info está cacheada
        assert model2.content() == "Cached content"
        # Verificamos que solo ha habido 1 llamada real
        assert len(calls) == 1

    def test_model_wait_about(self, monkeypatch):
        # Revisamos que duerma el tiempo indicado
        sleep_times = []

        def mock_sleep(t):
            sleep_times.append(t)

        monkeypatch.setattr(time, "sleep", mock_sleep)

        def mock_touch(self, url, data=None, headers=None, proxy=None, cookies=None):
            return (b"", {}, cookies)

        monkeypatch.setattr(Model, "touch", mock_touch)

        Model(url="http://example.com", wait_about=1)
        # Esperamos que haya dormido entre 1 y 2.5s (aprox uniform(1, 2.5))
        assert len(sleep_times) == 1
        assert 1 <= sleep_times[0] <= 2.5

    def test_model_response_headers(self, monkeypatch):
        def mock_touch(self, url, data=None, headers=None, proxy=None, cookies=None):
            return (b"content", {"Content-Type": "text/plain", "X-Test": "Value"}, cookies)

        monkeypatch.setattr(Model, "touch", mock_touch)
        model = Model(url="http://example.com")
        assert model.response_headers()["Content-Type"] == "text/plain"
        assert model.response_headers()["X-Test"] == "Value"

    def test_model_base_url(self, monkeypatch):
        def mock_touch(self, url, data=None, headers=None, proxy=None, cookies=None):
            return (b"Test", {}, cookies)

        monkeypatch.setattr(Model, "touch", mock_touch)

        model = Model(url="http://example.com/path?foo=bar")
        assert model.base_url() == "http://example.com"

    def test_model_field_dependency_error(self, monkeypatch):
        """
        Simularemos un caso en el que dos fields dependan cíclicamente el uno del otro.
        """

        # Creamos una clase con dos fields que se refieren entre sí
        from harvester.models import CharField

        class CyclicModel(Model):
            field_a = CharField(start="A", end="B", deps=["field_b"])
            field_b = CharField(start="B", end="C", deps=["field_a"])

        def mock_touch(self, url, data=None, headers=None, proxy=None, cookies=None):
            return (b"ABC", {}, cookies)

        monkeypatch.setattr(Model, "touch", mock_touch)

        with pytest.raises(CircularDependencyError):
            _ = CyclicModel(url="http://example.com")

    def test_model_field_not_found_error(self, monkeypatch):
        """
        Caso en que un field especifica como dependencia un nombre que no existe.
        """
        from harvester.models import CharField

        class WrongDepsModel(Model):
            field_a = CharField(start="A", end="B", deps=["field_b"])  # no existe field_b

        def mock_touch(self, url, data=None, headers=None, proxy=None, cookies=None):
            return (b"foo", {}, cookies)

        monkeypatch.setattr(Model, "touch", mock_touch)

        with pytest.raises(FieldNotFoundError):
            _ = WrongDepsModel(url="http://example.com")

    def test_model_touch_ok(self, monkeypatch):
        """
        Verificar que Model.touch realice la llamada y retorne la tupla adecuada.
        """
        from harvester.models import Model

        # Llamada real no se quiere, se mockea
        import io

        mock_response = io.BytesIO(b"Fake content")
        mock_response.headers = {"Content-Type": "text/html"}
        mock_cookiejar = MagicMock()

        opener_mock = MagicMock()
        opener_mock.open.return_value = mock_response

        def build_opener_mock(*args, **kwargs):
            return opener_mock

        with patch("harvester.models.build_opener", build_opener_mock):
            content, headers, cookies = Model.touch("http://test.com")
            assert content == b"Fake content"
            assert headers["Content-Type"] == "text/html"
            assert cookies is not None  # Devuelto por constructor

        # Verificar que open se llama con la URL
        opener_mock.open.assert_called_once_with("http://test.com", data=None)

    def test_model_process_meta_drop_before_after(self):
        """
        Probamos las funciones privadas __process_drop_before y __process_drop_after.
        Creamos una subclase con Meta.
        """

        class MyModel(Model):
            class Meta:
                drop_before = r"start"
                drop_after = r"end"

        content = "123start Hello this is content end 456"
        model = MyModel(content=content)
        # Tras el constructor, se habría procesado. Veamos si se ajusta
        # al resultado esperado: "Hello this is content"
        # El constructor llama a process_meta de forma interna si se codifica en tu Model,
        # pero si no, puedes llamar manualmente a model.process_meta().
        processed = model.process_meta(model.content())
        assert "Hello this is content" in processed
        assert "123start" not in processed
        assert "end 456" not in processed
