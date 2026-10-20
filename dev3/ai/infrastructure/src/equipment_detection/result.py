from dataclasses import dataclass
from typing import List


@dataclass
class DetectionResult:
    class_id: int
    class_name: str
    confidence: float
    bbox: List[float]

    def to_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bbox": self.bbox,
        }


def build_results(detections: list[dict]) -> list[DetectionResult]:
    return [
        DetectionResult(
            class_id=int(detection["class_id"]),
            class_name=str(detection["class_name"]),
            confidence=float(detection["confidence"]),
            bbox=[
                float(value)
                for value in detection["bbox"]
            ],
        )
        for detection in detections
    ]