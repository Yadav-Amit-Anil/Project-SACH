from __future__ import annotations

from typing import Iterable


def count_equipment(
    detections: Iterable[dict],
) -> dict[str, int]:
    """
    Count detected equipment by class_name.

    Example:
        [
            {"class_name": "computer"},
            {"class_name": "computer"},
            {"class_name": "whiteboard"},
        ]

    returns:
        {
            "computer": 2,
            "whiteboard": 1,
        }
    """

    counts: dict[str, int] = {}

    for detection in detections:
        class_name = detection.get("class_name")

        if not class_name:
            continue

        counts[class_name] = counts.get(class_name, 0) + 1

    return counts


def calculate_compliance(
    required: dict[str, int],
    detected: dict[str, int],
) -> dict:
    """
    Compare required equipment against detected equipment.

    Compliance for each equipment type is capped at 100%.

    Overall compliance is calculated from total required
    versus total detected, also capped at 100%.
    """

    equipment = {}

    total_required = 0
    total_detected = 0

    for name, required_count in required.items():
        if required_count < 0:
            raise ValueError(
                f"Required count cannot be negative: {name}"
            )

        detected_count = max(
            0,
            detected.get(name, 0),
        )

        total_required += required_count
        total_detected += min(
            detected_count,
            required_count,
        )

        if required_count == 0:
            percentage = 100.0
        else:
            percentage = min(
                100.0,
                (detected_count / required_count) * 100,
            )

        missing = max(
            0,
            required_count - detected_count,
        )

        equipment[name] = {
            "required": required_count,
            "detected": detected_count,
            "missing": missing,
            "compliance_percent": round(
                percentage,
                2,
            ),
        }

    if total_required == 0:
        overall = 100.0
    else:
        overall = (
            total_detected / total_required
        ) * 100

    return {
        "overall_compliance_percent": round(
            min(100.0, overall),
            2,
        ),
        "equipment": equipment,
    }