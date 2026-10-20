from src.equipment_detection.result import (
    DetectionResult,
    build_results,
)


def test_detection_result_to_dict():
    result = DetectionResult(
        class_id=1,
        class_name="computer",
        confidence=0.93,
        bbox=[10.0, 20.0, 100.0, 200.0],
    )

    data = result.to_dict()

    assert data["class_id"] == 1
    assert data["class_name"] == "computer"
    assert data["confidence"] == 0.93
    assert data["bbox"] == [10.0, 20.0, 100.0, 200.0]


def test_build_results():
    detections = [
        {
            "class_id": 1,
            "class_name": "computer",
            "confidence": 0.93,
            "bbox": [10, 20, 100, 200],
        },
        {
            "class_id": 5,
            "class_name": "whiteboard",
            "confidence": 0.74,
            "bbox": [30, 40, 300, 400],
        },
    ]

    results = build_results(detections)

    assert len(results) == 2
    assert isinstance(results[0], DetectionResult)
    assert results[0].class_name == "computer"
    assert results[1].class_name == "whiteboard"