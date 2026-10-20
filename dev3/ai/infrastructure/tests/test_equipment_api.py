from pathlib import Path

from src.equipment_detection import EquipmentDetectionAPI


TEST_IMAGE = (
    Path(__file__).resolve().parents[1]
    / "equipment"
    / "dataset"
    / "test"
    / "images"
    / "IMG_6980_jpg.rf.1a19e1800feb9ddfdc0ea989b6aa6a55.jpg"
)


def test_detection_api():
    api = EquipmentDetectionAPI()

    results = api.detect(TEST_IMAGE)

    assert isinstance(results, list)
    assert len(results) > 0

    for result in results:
        assert "class_id" in result
        assert "class_name" in result
        assert "confidence" in result
        assert "bbox" in result

        assert 0 <= result["confidence"] <= 1
        assert len(result["bbox"]) == 4
