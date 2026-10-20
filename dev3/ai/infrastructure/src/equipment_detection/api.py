from pathlib import Path

from .pipeline import EquipmentPipeline


class EquipmentDetectionAPI:
    def __init__(
        self,
        model_path: str | Path | None = None,
        conf: float = 0.25,
        device: int = 0,
    ):
        self.pipeline = EquipmentPipeline(
            model_path=model_path,
            conf=conf,
            device=device,
        )

    def detect(self, image_path: str | Path):
        return self.pipeline.run(image_path)


if __name__ == "__main__":
    api = EquipmentDetectionAPI()

    image = (
        Path(__file__).resolve().parents[2]
        / "equipment"
        / "dataset"
        / "test"
        / "images"
        / "IMG_6980_jpg.rf.1a19e1800feb9ddfdc0ea989b6aa6a55.jpg"
    )

    results = api.detect(image)

    print("EQUIPMENT DETECTION API: OK")
    print(f"Detections: {len(results)}")
    print(results)
