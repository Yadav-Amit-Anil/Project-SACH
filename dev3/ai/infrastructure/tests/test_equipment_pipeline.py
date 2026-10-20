from pathlib import Path

from src.equipment_detection.pipeline import EquipmentPipeline


TEST_IMAGE = (
    Path(__file__).resolve().parents[1]
    / "equipment"
    / "dataset"
    / "test"
    / "images"
    / "IMG_6980_jpg.rf.1a19e1800feb9ddfdc0ea989b6aa6a55.jpg"
)


def test_pipeline_returns_detections():
    pipeline = EquipmentPipeline()

    results = pipeline.run(TEST_IMAGE)

    assert isinstance(results, list)
    assert len(results) > 0


def test_pipeline_result_structure():
    pipeline = EquipmentPipeline()

    results = pipeline.run(TEST_IMAGE)

    for result in results:
        assert "class_id" in result
        assert "class_name" in result
        assert "confidence" in result
        assert "bbox" in result

        assert isinstance(result["class_id"], int)
        assert isinstance(result["class_name"], str)
        assert 0.0 <= result["confidence"] <= 1.0
        assert len(result["bbox"]) == 4
def test_pipeline_analyze():
    pipeline = EquipmentPipeline()

    required = {
        "computer": 2,
        "whiteboard": 1,
    }

    result = pipeline.analyze(
        TEST_IMAGE,
        required,
    )

    assert isinstance(result, dict)

    assert "detections" in result
    assert "counts" in result
    assert "compliance" in result

    assert isinstance(result["detections"], list)
    assert isinstance(result["counts"], dict)
    assert isinstance(result["compliance"], dict)

    assert (
        "overall_compliance_percent"
        in result["compliance"]
    )

    assert "equipment" in result["compliance"]
def test_pipeline_analyze_contains_fraud_risk():
    pipeline = EquipmentPipeline()

    required = {
        "computer": 2,
        "whiteboard": 1,
    }

    result = pipeline.analyze(
        TEST_IMAGE,
        required,
    )

    assert "fraud_risk" in result

    fraud_risk = result["fraud_risk"]

    assert isinstance(fraud_risk, dict)
    assert "risk_score" in fraud_risk
    assert "risk_level" in fraud_risk
    assert "signals" in fraud_risk

    assert 0.0 <= fraud_risk["risk_score"] <= 100.0

    assert fraud_risk["risk_level"] in {
        "LOW",
        "MEDIUM",
        "HIGH",
    }

    assert isinstance(
        fraud_risk["signals"],
        list,
    )