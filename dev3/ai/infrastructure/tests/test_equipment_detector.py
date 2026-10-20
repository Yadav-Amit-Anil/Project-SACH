from pathlib import Path

from src.equipment_detection.detector import EquipmentDetector


TEST_IMAGE = (
    Path(__file__).resolve().parents[1]
    / "equipment"
    / "dataset"
    / "test"
    / "images"
    / "IMG_6980_jpg.rf.1a19e1800feb9ddfdc0ea989b6aa6a55.jpg"
)


def test_model_loads():
    detector = EquipmentDetector()

    assert detector.model is not None
    assert detector.model_path.exists()


def test_detection():
    detector = EquipmentDetector()

    detections = detector.detect(TEST_IMAGE)

    assert isinstance(detections, list)
    assert len(detections) > 0

    for detection in detections:
        assert "class_id" in detection
        assert "class_name" in detection
        assert "confidence" in detection
        assert "bbox" in detection

        assert 0 <= detection["class_id"] <= 5
        assert detection["class_name"] in {
            "chair",
            "computer",
            "desk",
            "printer",
            "projector",
            "whiteboard",
        }

        assert 0.0 <= detection["confidence"] <= 1.0
        assert len(detection["bbox"]) == 4