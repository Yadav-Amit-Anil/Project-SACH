from src.equipment_detection.fraud_risk import calculate_fraud_risk


def test_no_anomaly_has_zero_risk():
    result = calculate_fraud_risk([])

    assert result["risk_score"] == 0.0
    assert result["risk_level"] == "LOW"
    assert result["signals"] == []


def test_missing_equipment_adds_ten_risk():
    signals = [
        {
            "type": "missing_equipment",
            "equipment": "computer",
            "missing": 1,
        }
    ]

    result = calculate_fraud_risk(signals)

    assert result["risk_score"] == 10.0
    assert result["risk_level"] == "LOW"
    assert result["signals"] == signals


def test_multiple_signals_are_combined():
    signals = [
        {
            "type": "missing_equipment",
            "equipment": "computer",
            "missing": 1,
        },
        {
            "type": "low_compliance",
            "compliance_percent": 40.0,
        },
    ]

    result = calculate_fraud_risk(signals)

    assert result["risk_score"] == 10.0
    assert result["risk_level"] == "LOW"
    assert len(result["signals"]) == 2


def test_risk_score_is_capped_at_100():
    signals = [
        {"type": "attendance_mismatch"},
        {"type": "repeated_liveness_failure"},
        {"type": "suspicious_ip"},
        {"type": "power_anomaly"},
        {"type": "historical_violation"},
    ]

    result = calculate_fraud_risk(signals)

    assert 0.0 <= result["risk_score"] <= 100.0
def test_unknown_signal_does_not_add_risk():
    signals = [
        {
            "type": "unknown_signal",
        }
    ]

    result = calculate_fraud_risk(signals)

    assert result["risk_score"] == 0.0
    assert result["risk_level"] == "LOW"
    assert result["signals"] == signals


def test_risk_score_is_capped_at_100():
    signals = [
        {"type": "attendance_mismatch"},
        {"type": "repeated_liveness_failure"},
        {"type": "suspicious_ip"},
        {"type": "power_anomaly"},
        {"type": "historical_violation"},
        {"type": "attendance_mismatch"},
        {"type": "suspicious_ip"},
    ]

    result = calculate_fraud_risk(signals)

    assert result["risk_score"] == 100.0
    assert result["risk_level"] == "HIGH"


def test_high_risk_level():
    signals = [
        {"type": "attendance_mismatch"},
        {"type": "suspicious_ip"},
        {"type": "power_anomaly"},
    ]

    result = calculate_fraud_risk(signals)

    assert result["risk_score"] == 55.0
    assert result["risk_level"] == "HIGH"