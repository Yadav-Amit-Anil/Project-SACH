from __future__ import annotations

from typing import Any


RISK_WEIGHTS = {
    "missing_equipment": 10.0,
    "attendance_mismatch": 20.0,
    "repeated_liveness_failure": 15.0,
    "suspicious_ip": 20.0,
    "power_anomaly": 15.0,
    "historical_violation": 10.0,
}


def calculate_fraud_risk(
    signals: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate a prototype centre fraud-risk score
    from anomaly signals.

    This score is an investigation-priority indicator,
    not proof of fraud.
    """

    risk_score = 0.0

    for signal in signals:
        signal_type = signal.get("type")

        weight = RISK_WEIGHTS.get(
            signal_type,
            0.0,
        )

        risk_score += weight

    risk_score = round(
        min(100.0, max(0.0, risk_score)),
        2,
    )

    if risk_score < 20.0:
     risk_level = "LOW"
    elif risk_score < 50.0:
     risk_level = "MEDIUM"
    else:
     risk_level = "HIGH"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "signals": signals,
    }