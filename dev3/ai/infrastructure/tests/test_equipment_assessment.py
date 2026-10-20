from src.equipment_detection.assessment import build_assessment


def test_build_assessment():
    counts = {
        "computer": 1,
        "whiteboard": 1,
    }

    compliance = {
        "overall_compliance_percent": 66.67,
        "equipment": {
            "computer": {
                "required": 2,
                "detected": 1,
                "missing": 1,
                "compliance_percent": 50.0,
            },
            "whiteboard": {
                "required": 1,
                "detected": 1,
                "missing": 0,
                "compliance_percent": 100.0,
            },
        },
    }

    result = build_assessment(
        counts,
        compliance,
    )

    assert result["counts"] == counts
    assert result["overall_compliance_percent"] == 66.67

    assert result["missing_equipment"] == {
        "computer": 1,
    }

    assert result["compliant_equipment"] == {
        "whiteboard": 100.0,
    }

    assert result["non_compliant_equipment"] == {
        "computer": 50.0,
    }


def test_build_assessment_with_no_missing_equipment():
    counts = {
        "computer": 2,
    }

    compliance = {
        "overall_compliance_percent": 100.0,
        "equipment": {
            "computer": {
                "required": 2,
                "detected": 2,
                "missing": 0,
                "compliance_percent": 100.0,
            },
        },
    }

    result = build_assessment(
        counts,
        compliance,
    )

    assert result["missing_equipment"] == {}
    assert result["compliant_equipment"] == {
        "computer": 100.0,
    }
    assert result["non_compliant_equipment"] == {}