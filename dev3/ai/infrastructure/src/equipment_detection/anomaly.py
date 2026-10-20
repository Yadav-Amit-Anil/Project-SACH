from __future__ import annotations

from typing import Any


def calculate_anomaly_score(
    assessment: dict[str, Any],
) -> dict[str, Any]:
    """
    Calculate an explainable infrastructure anomaly score.
    """

    overall_compliance = float(
        assessment.get("overall_compliance_percent", 100.0)
    )

    missing_equipment = assessment.get(
        "missing_equipment",
        {},
    )

    anomaly_score = round(
        max(
            0.0,
            min(
                100.0,
                100.0 - overall_compliance,
            ),
        ),
        2,
    )

    if anomaly_score == 0.0:
        risk_level = "LOW"
    elif anomaly_score < 50.0:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    signals = []
    reasons = []
    recommendations = []

    # Low compliance signal
    if overall_compliance < 50.0:
        signals.append(
            {
                "type": "low_compliance",
                "compliance_percent": overall_compliance,
            }
        )

        reasons.append(
            f"Overall compliance is {overall_compliance:.2f}%."
        )

        recommendations.append(
            "Review the infrastructure requirements and "
            "address the missing equipment."
        )

    # Missing equipment signals
    for equipment, missing in missing_equipment.items():
        if missing <= 0:
            continue

        signals.append(
            {
                "type": "missing_equipment",
                "equipment": equipment,
                "missing": missing,
            }
        )

        equipment_label = equipment.replace("_", " ")

        if missing == 1:
            reasons.append(
                f"1 {equipment_label} is missing."
            )
        else:
            reasons.append(
                f"{missing} {equipment_label}s are missing."
            )

        recommendations.append(
            f"Verify the availability of the required "
            f"{equipment_label}."
        )

    return {
        "anomaly_score": anomaly_score,
        "risk_level": risk_level,
        "signals": signals,
        "reasons": reasons,
        "recommendations": recommendations,
    }