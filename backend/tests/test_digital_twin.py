from ai.digital_twin.data import DigitalTwinDataGenerator


def test_generates_minimal_structure():
    gen = DigitalTwinDataGenerator()
    result = gen.generate({}, "three_wheeler")
    assert result["vehicle_type"] == "three_wheeler"
    assert result["dimensions"]["length"] == 2800
    assert result["dimensions"]["width"] == 1200
    assert result["dimensions"]["height"] == 1700
    assert result["deviations_3d"] == []
    assert result["retrofit_components"] == []
    assert "view_angles" in result


def test_generates_with_deviations():
    gen = DigitalTwinDataGenerator()
    assessment = {
        "deviation_result": {
            "deviations": [
                {
                    "parameter": "wheelbase_mm",
                    "severity": "moderate",
                    "delta_pct": -4.65,
                },
                {
                    "parameter": "ground_clearance_mm",
                    "severity": "major",
                    "delta_pct": 15.3,
                },
            ]
        }
    }
    result = gen.generate(assessment, "three_wheeler")
    assert len(result["deviations_3d"]) == 2
    assert result["deviations_3d"][0]["parameter"] == "wheelbase_mm"
    assert result["deviations_3d"][0]["location"] == "chassis_center"
    assert result["deviations_3d"][0]["severity"] == "moderate"
    assert result["deviations_3d"][0]["color"] == "#f59e0b"
    assert result["deviations_3d"][1]["location"] == "underbody"
    assert result["deviations_3d"][1]["color"] == "#ef4444"


def test_generates_retrofit_components():
    gen = DigitalTwinDataGenerator()
    assessment = {
        "recommendations": [
            {"id": "battery_pack_location", "title": "Battery", "category": "battery"},
            {"id": "motor_selection", "title": "Motor", "category": "motor"},
            {"id": "controller_and_bms", "title": "Controller", "category": "controller"},
        ]
    }
    result = gen.generate(assessment, "three_wheeler")
    assert len(result["retrofit_components"]) == 3
    assert result["retrofit_components"][0]["id"] == "battery_pack"
    assert result["retrofit_components"][1]["id"] == "motor"
    assert result["retrofit_components"][2]["id"] == "controller"


def test_generates_top_three_recommendations():
    gen = DigitalTwinDataGenerator()
    assessment = {
        "recommendations": [
            {"id": "battery_pack_location", "title": "Battery", "category": "battery"},
            {"id": "motor_selection", "title": "Motor", "category": "motor"},
            {"id": "controller_and_bms", "title": "Controller", "category": "controller"},
            {"id": "wiring_harness", "title": "Wiring", "category": "wiring"},
            {"id": "regenerative_braking", "title": "Regen", "category": "controller"},
        ]
    }
    result = gen.generate(assessment, "three_wheeler")
    assert len(result["retrofit_components"]) == 3


def test_motorcycle_defaults():
    gen = DigitalTwinDataGenerator()
    result = gen.generate({}, "motorcycle")
    assert result["vehicle_type"] == "motorcycle"
    assert result["dimensions"]["length"] == 2000
    assert result["dimensions"]["width"] == 800
    assert result["dimensions"]["height"] == 1100


def test_unknown_vehicle_type():
    gen = DigitalTwinDataGenerator()
    result = gen.generate({}, "unknown")
    assert result["vehicle_type"] == "unknown"
    assert result["dimensions"]["length"] == 2800
