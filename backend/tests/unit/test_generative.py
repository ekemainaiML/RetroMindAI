import builtins
from unittest.mock import MagicMock, patch

import pytest

from ai.generative.refiner import GenerativeRefiner
from core.capabilities import CapabilityRegistry


@pytest.fixture(autouse=True)
def _reset_registry():
    CapabilityRegistry.reset()
    yield
    CapabilityRegistry.reset()


@pytest.fixture
def sample_zones():
    return [
        {"id": "under_seat", "priority": 1, "label": "Under-Seat Tray", "constraints": []},
        {"id": "cargo_bay", "priority": 2, "label": "Cargo Bay", "constraints": []},
        {"id": "frame_mounted", "priority": 3, "label": "Frame Rail", "constraints": []},
    ]


@pytest.fixture
def sample_routes():
    return [
        {"id": "chassis_rail_right", "priority": 1, "label": "Right Rail", "path_type": "chassis_rail"},
        {"id": "chassis_rail_left", "priority": 2, "label": "Left Rail", "path_type": "chassis_rail"},
    ]


_original_import = builtins.__import__


def _mock_openai_import(name, *args, **kwargs):
    if name == "openai":
        mock_module = MagicMock()
        mock_module.OpenAI = MagicMock
        return mock_module
    return _original_import(name, *args, **kwargs)


def _mock_anthropic_import(name, *args, **kwargs):
    if name == "anthropic":
        mock_module = MagicMock()
        mock_module.Anthropic = MagicMock
        return mock_module
    return _original_import(name, *args, **kwargs)


class TestGenerativeRefinerInit:
    def test_init_backend_none_by_default(self):
        refiner = GenerativeRefiner()
        assert refiner._backend is None

    def test_init_backend_disabled_by_flag(self):
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = False
            refiner = GenerativeRefiner()
            refiner._init_backend()
            assert refiner._backend == "none"

    def test_init_backend_no_api_key(self):
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = ""
            mock.anthropic_api_key = ""
            refiner = GenerativeRefiner()
            refiner._init_backend()
            assert refiner._backend == "none"

    def test_init_openai_import_error(self):
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = "sk-test"
            mock.anthropic_api_key = ""

            def _raise_import(name, *args, **kwargs):
                if name == "openai":
                    raise ImportError("No module named openai")
                return _original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", _raise_import):
                refiner = GenerativeRefiner()
                refiner._init_backend()
                assert refiner._backend == "none"

    def test_init_openai_success(self):
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = "sk-test"
            mock.anthropic_api_key = ""
            with patch.object(builtins, "__import__", _mock_openai_import):
                refiner = GenerativeRefiner()
                refiner._init_backend()
                assert refiner._backend is not None
                assert refiner._backend != "none"

    def test_init_anthropic_success(self):
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = ""
            mock.anthropic_api_key = "sk-ant-test"
            with patch.object(builtins, "__import__", _mock_anthropic_import):
                refiner = GenerativeRefiner()
                refiner._init_backend()
                assert refiner._backend is not None
                assert refiner._backend != "none"


class TestRefineBatteryZones:
    def test_returns_original_when_disabled(self, sample_zones):
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = False
            refiner = GenerativeRefiner()
            result = refiner.refine_battery_zones(sample_zones, "three_wheeler")
            assert result == sample_zones

    def test_returns_original_when_no_backend(self, sample_zones):
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = ""
            mock.anthropic_api_key = ""
            refiner = GenerativeRefiner()
            result = refiner.refine_battery_zones(sample_zones, "three_wheeler")
            assert result == sample_zones

    def test_calls_llm_and_parses_response(self, sample_zones):
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = "sk-test"
            mock.anthropic_api_key = ""
            with patch.object(builtins, "__import__", _mock_openai_import):
                refiner = GenerativeRefiner()
                refiner._init_backend()
                refiner._call_llm = MagicMock(
                    return_value='[{"id":"under_seat","priority":1,"expert_note":"good"},{"id":"cargo_bay","priority":1,"expert_note":"consider reinforcement"},{"id":"frame_mounted","priority":3}]'
                )
                result = refiner.refine_battery_zones(sample_zones, "three_wheeler")
                assert len(result) == 3
                cargo = next(z for z in result if z["id"] == "cargo_bay")
                assert cargo["priority"] == 1
                assert cargo["expert_note"] == "consider reinforcement"

    def test_returns_original_on_llm_failure(self, sample_zones):
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = "sk-test"
            mock.anthropic_api_key = ""
            with patch.object(builtins, "__import__", _mock_openai_import):
                refiner = GenerativeRefiner()
                refiner._init_backend()
                refiner._call_llm = MagicMock(side_effect=RuntimeError("API error"))
                with patch("ai.generative.refiner.get_degradation_manager") as mock_gdm:
                    result = refiner.refine_battery_zones(sample_zones, "three_wheeler")
                    assert result == sample_zones
                    mock_gdm.return_value.register.assert_called()

    def test_returns_original_on_json_parse_error(self, sample_zones):
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = "sk-test"
            mock.anthropic_api_key = ""
            with patch.object(builtins, "__import__", _mock_openai_import):
                refiner = GenerativeRefiner()
                refiner._init_backend()
                refiner._call_llm = MagicMock(return_value="not valid json")
                result = refiner.refine_battery_zones(sample_zones, "three_wheeler")
                assert result == sample_zones

    def test_returns_original_on_non_list_response(self, sample_zones):
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = "sk-test"
            mock.anthropic_api_key = ""
            with patch.object(builtins, "__import__", _mock_openai_import):
                refiner = GenerativeRefiner()
                refiner._init_backend()
                refiner._call_llm = MagicMock(return_value='{"error":"bad"}')
                result = refiner.refine_battery_zones(sample_zones, "three_wheeler")
                assert result == sample_zones


class TestRefineWiringRoutes:
    def test_returns_original_when_disabled(self, sample_routes):
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = False
            refiner = GenerativeRefiner()
            result = refiner.refine_wiring_routing(sample_routes, "four_wheeler")
            assert result == sample_routes

    def test_calls_llm_and_parses(self, sample_routes):
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = "sk-test"
            mock.anthropic_api_key = ""
            with patch.object(builtins, "__import__", _mock_openai_import):
                refiner = GenerativeRefiner()
                refiner._init_backend()
                refiner._call_llm = MagicMock(
                    return_value='[{"id":"chassis_rail_right","priority":1,"expert_note":"preferred"},{"id":"chassis_rail_left","priority":2}]'
                )
                result = refiner.refine_wiring_routing(sample_routes, "four_wheeler")
                assert len(result) == 2


class TestPromptBuilding:
    def test_build_battery_prompt_includes_type(self, sample_zones):
        refiner = GenerativeRefiner()
        prompt = refiner._build_battery_prompt(sample_zones, "motorcycle", [], {})
        assert "motorcycle" in prompt
        assert "current_zones" in prompt

    def test_build_wiring_prompt_includes_type(self, sample_routes):
        refiner = GenerativeRefiner()
        prompt = refiner._build_wiring_prompt(sample_routes, "four_wheeler", [], {})
        assert "four_wheeler" in prompt
        assert "current_routes" in prompt


class TestMerge:
    def test_merge_zones_preserves_original_fields(self, sample_zones):
        refined = [
            {"id": "under_seat", "priority": 3, "expert_note": "moved down"},
        ]
        merged = GenerativeRefiner._merge_zones(refined, sample_zones)
        merged_under = next(z for z in merged if z["id"] == "under_seat")
        assert merged_under["priority"] == 3
        assert merged_under["expert_note"] == "moved down"
        assert "constraints" in merged_under

    def test_merge_routes_preserves_structure(self, sample_routes):
        refined = [
            {"id": "chassis_rail_right", "priority": 2, "expert_note": "check clearance"},
        ]
        merged = GenerativeRefiner._merge_routes(refined, sample_routes)
        merged_right = next(r for r in merged if r["id"] == "chassis_rail_right")
        assert merged_right["priority"] == 2
        assert merged_right["expert_note"] == "check clearance"
        assert merged_right["path_type"] == "chassis_rail"


class TestBatteryIntegration:
    def test_compute_battery_zones_pass_through_when_disabled(self, sample_zones):
        with patch("optimization.battery.settings") as mock:
            mock.enable_generative_design = False
            from optimization.battery import compute_battery_zones
            result = compute_battery_zones("three_wheeler")
            assert "zones" in result
            assert result["zone_count"] == 3

    def test_compute_battery_zones_with_genai_enabled(self, sample_zones):
        with patch("optimization.battery.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = ""
            mock.anthropic_api_key = ""
            from optimization.battery import compute_battery_zones
            result = compute_battery_zones("three_wheeler")
            assert "zones" in result
            assert result["zone_count"] == 3


class TestWiringIntegration:
    def test_compute_routing_pass_through_when_disabled(self, sample_routes):
        with patch("optimization.wiring.settings") as mock:
            mock.enable_generative_design = False
            from optimization.wiring import compute_routing
            result = compute_routing("three_wheeler")
            assert "routing_paths" in result

    def test_compute_routing_with_genai_enabled(self, sample_routes):
        with patch("optimization.wiring.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = ""
            mock.anthropic_api_key = ""
            from optimization.wiring import compute_routing
            result = compute_routing("three_wheeler")
            assert "routing_paths" in result


class TestCallLLM:
    def test_call_openai(self):
        mock_client = MagicMock()
        mock_client.__class__.__module__ = "openai"
        mock_client.chat.completions.create.return_value.choices[0].message.content = "response text"
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = "sk-test"
            mock.anthropic_api_key = ""
            refiner = GenerativeRefiner()
            refiner._backend = mock_client
            result = refiner._call_llm("test prompt")
            assert result == "response text"

    def test_call_anthropic(self):
        mock_client = MagicMock()
        mock_client.__class__.__module__ = "anthropic"
        mock_client.messages.create.return_value.content = [MagicMock(text="anthropic response")]
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = ""
            mock.anthropic_api_key = "sk-ant-test"
            refiner = GenerativeRefiner()
            refiner._backend = mock_client
            result = refiner._call_llm("test prompt")
            assert result == "anthropic response"

    def test_call_string_backend(self):
        refiner = GenerativeRefiner()
        refiner._backend = "none"
        assert refiner._call_llm("test") == ""

    def test_call_empty_openai_response(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value.choices[0].message.content = None
        with patch("ai.generative.refiner.settings") as mock:
            mock.enable_generative_design = True
            mock.openai_api_key = "sk-test"
            mock.anthropic_api_key = ""
            with patch.object(builtins, "__import__", _mock_openai_import):
                refiner = GenerativeRefiner()
                refiner._init_backend()
                refiner._backend = mock_client
                result = refiner._call_llm("test")
                assert result == ""
