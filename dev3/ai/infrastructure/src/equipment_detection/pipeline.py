from pathlib import Path

from .anomaly import calculate_anomaly_score
from .compliance import calculate_compliance, count_equipment
from .detector import EquipmentDetector
from .fraud_risk import calculate_fraud_risk
from .result import build_results


class EquipmentPipeline:
    def __init__(
        self,
        model_path: str | Path | None = None,
        conf: float = 0.25,
        device: int = 0,
    ):
        if model_path is None:
            self.detector = EquipmentDetector()
        else:
            self.detector = EquipmentDetector(model_path)

        self.conf = conf
        self.device = device

    def run(self, source: str | Path) -> list[dict]:
        detections = self.detector.detect(
            source=source,
            conf=self.conf,
            device=self.device,
        )

        results = build_results(detections)

        return [
            result.to_dict()
            for result in results
        ]

    def analyze(
        self,
        source: str | Path,
        required: dict[str, int],
    ) -> dict:
        """
        Run equipment detection, compliance analysis,
        anomaly analysis, and centre fraud-risk scoring.
        """

        detections = self.detector.detect(
            source=source,
            conf=self.conf,
            device=self.device,
        )

        results = build_results(detections)

        detection_dicts = [
            result.to_dict()
            for result in results
        ]

        detected = count_equipment(detection_dicts)

        compliance = calculate_compliance(
            required=required,
            detected=detected,
        )

        assessment = {
            "detections": detection_dicts,
            "counts": detected,
            "compliance": compliance,
            "overall_compliance_percent": compliance[
                "overall_compliance_percent"
            ],
            "equipment": compliance["equipment"],
            "missing_equipment": {
                name: details["missing"]
                for name, details in compliance["equipment"].items()
                if details["missing"] > 0
            },
        }

        anomaly = calculate_anomaly_score(
            assessment
        )

        fraud_risk = calculate_fraud_risk(
            anomaly["signals"]
        )

        return {
            **assessment,
            "anomaly": anomaly,
            "fraud_risk": fraud_risk,
        }