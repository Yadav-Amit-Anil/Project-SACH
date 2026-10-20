from pathlib import Path

from ultralytics import YOLO


MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "models"
    / "equipment_yolo11n_v2.pt"
)

CLASS_NAMES = {
    0: "chair",
    1: "computer",
    2: "desk",
    3: "printer",
    4: "projector",
    5: "whiteboard",
}


class EquipmentDetector:
    def __init__(self, model_path: str | Path = MODEL_PATH):
        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Equipment model not found: {self.model_path}"
            )

        self.model = YOLO(str(self.model_path))

    def predict(
        self,
        source: str | Path,
        conf: float = 0.25,
        device: int = 0,
    ):
        source = Path(source)

        if not source.exists():
            raise FileNotFoundError(
                f"Input image not found: {source}"
            )

        return self.model.predict(
            source=str(source),
            conf=conf,
            device=device,
            verbose=False,
        )

    def detect(
        self,
        source: str | Path,
        conf: float = 0.25,
        device: int = 0,
    ):
        results = self.predict(
            source=source,
            conf=conf,
            device=device,
        )

        detections = []

        for box in results[0].boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])

            x1, y1, x2, y2 = map(
                float,
                box.xyxy[0].tolist()
            )

            detections.append(
                {
                    "class_id": class_id,
                    "class_name": CLASS_NAMES[class_id],
                    "confidence": confidence,
                    "bbox": [x1, y1, x2, y2],
                }
            )

        return detections


if __name__ == "__main__":
    detector = EquipmentDetector()

    print("Model loaded successfully.")
    print(f"Model: {detector.model_path}")
    print(f"Classes: {CLASS_NAMES}")