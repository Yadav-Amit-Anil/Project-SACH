from __future__ import annotations

from typing import Any


def build_assessment(
    counts: dict[str, int],
    compliance: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a clean infrastructure assessment
    from equipment counts and compliance results.
    """

    equipment = compliance.get("equipment", {})

    missing_equipment = {
        name: details["missing"]
        for name, details in equipment.items()
        if details["missing"] > 0
    }

    compliant_equipment = {
        name: details["compliance_percent"]
        for name, details in equipment.items()
        if details["compliance_percent"] >= 100.0
    }

    non_compliant_equipment = {
        name: details["compliance_percent"]
        for name, details in equipment.items()
        if details["compliance_percent"] < 100.0
    }

    return {
        "counts": counts,
        "overall_compliance_percent": compliance[
            "overall_compliance_percent"
        ],
        "equipment": equipment,
        "missing_equipment": missing_equipment,
        "compliant_equipment": compliant_equipment,
        "non_compliant_equipment": non_compliant_equipment,
    }