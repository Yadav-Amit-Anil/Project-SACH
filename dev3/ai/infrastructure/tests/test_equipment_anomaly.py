from src.equipment_detection.anomaly import calculate_anomaly_score


def test_no_anomaly_when_fully_compliant():
    assessment = {
        "overall_compliance_percent": 100.0,
        "missing_equipment": {},
    }

    result = calculate_anomaly_score(assessment)

    assert result["anomaly_score"] == 0.0
    assert result["risk_level"] == "LOW"
    assert result["signals"] == []


def test_missing_equipment_creates_anomaly():
    assessment = {
        "overall_compliance_percent": 66.67,
        "missing_equipment": {
            "computer": 1,
        },
    }

    result = calculate_anomaly_score(assessment)

    assert result["anomaly_score"] == 33.33
    assert result["risk_level"] == "MEDIUM"

    assert result["signals"] == [
        {
            "type": "missing_equipment",
            "equipment": "computer",
            "missing": 1,
        }
    ]


def test_high_anomaly_score():
    assessment = {
        "overall_compliance_percent": 40.0,
        "missing_equipment": {
            "computer": 2,
            "projector": 1,
        },
    }

    result = calculate_anomaly_score(assessment)

    assert result["anomaly_score"] == 60.0
    assert result["risk_level"] == "HIGH"

    assert len(result["signals"]) == 3

    assert {
        "type": "low_compliance",
        "compliance_percent": 40.0,
    } in result["signals"]

    assert {
        "type": "missing_equipment",
        "equipment": "computer",
        "missing": 2,
    } in result["signals"]

    assert {
        "type": "missing_equipment",
        "equipment": "projector",
        "missing": 1,
    } in result["signals"]


def test_low_compliance_creates_compliance_signal():
    assessment = {
        "overall_compliance_percent": 40.0,
        "missing_equipment": {},
    }

    result = calculate_anomaly_score(assessment)

    assert result["anomaly_score"] == 60.0
    assert result["risk_level"] == "HIGH"

    assert {
        "type": "low_compliance",
        "compliance_percent": 40.0,
    } in result["signals"]
def test_anomaly_result_contains_explanation():
    assessment = {
        "overall_compliance_percent": 66.67,
        "missing_equipment": {
            "computer": 1,
        },
    }

    result = calculate_anomaly_score(assessment)

    assert "reasons" in result
    assert "recommendations" in result

    assert "1 computer is missing." in result["reasons"]

    assert (
        "Verify the availability of the required computer."
        in result["recommendations"]
    )