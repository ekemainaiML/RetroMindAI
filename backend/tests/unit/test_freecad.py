from unittest.mock import MagicMock, patch

import pytest

from core.capabilities import CapabilityRegistry


@pytest.fixture(autouse=True)
def _reset_registry():
    CapabilityRegistry.reset()
    yield
    CapabilityRegistry.reset()


class TestFreeCADClientInit:
    def test_init_defaults(self):
        with patch("infrastructure.freecad_client.settings") as mock:
            mock.freecad_host = ""
            mock.enable_cad_export = False
            from infrastructure.freecad_client import FreeCADClient
            client = FreeCADClient()
            assert client._base_url == ""
            assert client._available is False

    def test_init_with_host(self):
        with patch("infrastructure.freecad_client.settings") as mock:
            mock.freecad_host = "http://freecad:8100"
            mock.enable_cad_export = False
            from infrastructure.freecad_client import FreeCADClient
            client = FreeCADClient()
            assert client._base_url == "http://freecad:8100"


class TestCheckAvailable:
    def test_returns_false_when_disabled(self):
        with patch("infrastructure.freecad_client.settings") as mock:
            mock.enable_cad_export = False
            from infrastructure.freecad_client import FreeCADClient
            client = FreeCADClient()
            assert client.check_available() is False

    def test_returns_false_when_no_host(self):
        with patch("infrastructure.freecad_client.settings") as mock:
            mock.enable_cad_export = True
            mock.freecad_host = ""
            from infrastructure.freecad_client import FreeCADClient
            client = FreeCADClient()
            assert client.check_available() is False

    def test_returns_false_on_connection_error(self):
        with patch("infrastructure.freecad_client.settings") as mock:
            mock.enable_cad_export = True
            mock.freecad_host = "http://freecad:8100"
            with patch("infrastructure.freecad_client.httpx") as mock_httpx:
                mock_httpx.get.side_effect = ConnectionError("refused")
                from infrastructure.freecad_client import FreeCADClient
                client = FreeCADClient()
                assert client.check_available() is False
                assert client._available is False

    def test_returns_false_on_non_200(self):
        with patch("infrastructure.freecad_client.settings") as mock:
            mock.enable_cad_export = True
            mock.freecad_host = "http://freecad:8100"
            with patch("infrastructure.freecad_client.httpx") as mock_httpx:
                mock_response = MagicMock()
                mock_response.status_code = 503
                mock_httpx.get.return_value = mock_response
                from infrastructure.freecad_client import FreeCADClient
                client = FreeCADClient()
                assert client.check_available() is False

    def test_returns_true_on_success(self):
        with patch("infrastructure.freecad_client.settings") as mock:
            mock.enable_cad_export = True
            mock.freecad_host = "http://freecad:8100"
            with patch("infrastructure.freecad_client.httpx") as mock_httpx:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_httpx.get.return_value = mock_response
                from infrastructure.freecad_client import FreeCADClient
                client = FreeCADClient()
                assert client.check_available() is True
                assert client._available is True


class TestExportStep:
    def test_returns_none_when_not_available(self):
        from infrastructure.freecad_client import FreeCADClient
        client = FreeCADClient()
        client._available = False
        assert client.export_step({}) is None

    def test_returns_bytes_on_success(self):
        from infrastructure.freecad_client import FreeCADClient
        client = FreeCADClient()
        client._available = True
        with patch("infrastructure.freecad_client.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"step data here"
            mock_httpx.post.return_value = mock_response
            result = client.export_step({"vehicle_classification": {"type": "four_wheeler"}})
            assert result == b"step data here"

    def test_returns_none_on_http_error(self):
        from infrastructure.freecad_client import FreeCADClient
        client = FreeCADClient()
        client._available = True
        with patch("infrastructure.freecad_client.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_httpx.post.return_value = mock_response
            result = client.export_step({})
            assert result is None

    def test_returns_none_on_exception(self):
        from infrastructure.freecad_client import FreeCADClient
        client = FreeCADClient()
        client._available = True
        with patch("infrastructure.freecad_client.httpx") as mock_httpx:
            mock_httpx.post.side_effect = RuntimeError("timeout")
            result = client.export_step({})
            assert result is None


class TestExportStl:
    def test_returns_none_when_not_available(self):
        from infrastructure.freecad_client import FreeCADClient
        client = FreeCADClient()
        client._available = False
        assert client.export_stl({}) is None

    def test_returns_bytes_on_success(self):
        from infrastructure.freecad_client import FreeCADClient
        client = FreeCADClient()
        client._available = True
        with patch("infrastructure.freecad_client.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"stl data"
            mock_httpx.post.return_value = mock_response
            result = client.export_stl({})
            assert result == b"stl data"


class TestCadEndpointImport:
    def test_router_exists(self):
        from api.v1.endpoints.cad_export import router
        assert router is not None

    def test_routes_registered(self):
        from api.v1.endpoints.cad_export import router
        routes = [r.path for r in router.routes]
        assert "/cad/export/{assessment_id}" in routes
