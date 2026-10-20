from src.equipment_detection.compliance import (
    calculate_compliance,
    count_equipment,
)


def test_count_equipment():
    detections = [
        {"class_name": "computer"},
        {"class_name": "computer"},
        {"class_name": "whiteboard"},
        {"class_name": "chair"},
    ]

    result = count_equipment(detections)

    assert result == {
        "computer": 2,
        "whiteboard": 1,
        "chair": 1,
    }


def test_count_empty_detections():
    assert count_equipment([]) == {}


def test_calculate_compliance():
    required = {
        "computer": 20,
        "chair": 20,
        "whiteboard": 1,
    }

    detected = {
        "computer": 17,
        "chair": 20,
        "whiteboard": 1,
    }

    result = calculate_compliance(
        required,
        detected,
    )

    assert result["equipment"]["computer"]["missing"] == 3
    assert result["equipment"]["chair"]["missing"] == 0
    assert result["equipment"]["whiteboard"]["missing"] == 0

    assert (
        result["equipment"]["computer"]
        ["compliance_percent"]
        == 85.0
    )

    assert (
        result["equipment"]["chair"]
        ["compliance_percent"]
        == 100.0
    )


def test_missing_equipment():
    required = {
        "computer": 20,
        "whiteboard": 1,
    }

    detected = {
        "computer": 17,
    }

    result = calculate_compliance(
        required,
        detected,
    )

    assert (
        result["equipment"]["computer"]["missing"]
        == 3
    )

    assert (
        result["equipment"]["whiteboard"]["missing"]
        == 1
    )


def test_detection_above_required_is_capped():
    required = {
        "computer": 10,
    }

    detected = {
        "computer": 15,
    }

    result = calculate_compliance(
        required,
        detected,
    )

    assert (
        result["equipment"]["computer"]
        ["compliance_percent"]
        == 100.0
    )

    assert (
        result["equipment"]["computer"]["missing"]
        == 0
    )