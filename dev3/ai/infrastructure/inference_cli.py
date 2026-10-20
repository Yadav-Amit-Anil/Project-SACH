import base64
import contextlib
import json
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
import torch

from src.equipment_detection.detector import CLASS_NAMES, EquipmentDetector


def decode_image(value: str, output_path: Path) -> None:
    encoded = value.partition(",")[2] if value.startswith("data:") else value
    image_bytes = base64.b64decode(encoded, validate=True)
    image_array = cv2.imdecode(
        np.frombuffer(image_bytes, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )
    if image_array is None:
        raise ValueError("An evidence image could not be decoded.")
    if not cv2.imwrite(str(output_path), image_array):
        raise OSError("Could not prepare an evidence image for Dev2 inference.")


def run_scan(payload: dict) -> dict:
    images = payload.get("images")
    required = payload.get("required")
    if not isinstance(images, list) or not images:
        raise ValueError("At least one evidence image is required.")
    if not isinstance(required, dict):
        raise ValueError("Required equipment counts are missing.")

    detector = EquipmentDetector()
    device = 0 if torch.cuda.is_available() else "cpu"
    view_results = []
    annotated_images = []

    with tempfile.TemporaryDirectory(prefix="sach-dev2-scan-") as temp_dir:
        temp_path = Path(temp_dir)
        for view_index, image in enumerate(images, start=1):
            if not isinstance(image, str):
                raise ValueError(f"Evidence view {view_index} is invalid.")
            image_path = temp_path / f"view-{view_index}.jpg"
            decode_image(image, image_path)

            with contextlib.redirect_stdout(sys.stderr):
                prediction = detector.predict(
                    image_path,
                    conf=0.25,
                    device=device,
                )[0]

            detections = []
            counts = {name: 0 for name in CLASS_NAMES.values()}
            for box in prediction.boxes:
                class_id = int(box.cls[0])
                class_name = CLASS_NAMES.get(class_id)
                if class_name is None:
                    continue
                counts[class_name] += 1
                detections.append({
                    "class_name": class_name,
                    "confidence": round(float(box.conf[0]), 4),
                    "bbox": [round(float(value), 1) for value in box.xyxy[0].tolist()],
                })

            encoded_ok, annotated = cv2.imencode(
                ".jpg",
                prediction.plot(),
                [cv2.IMWRITE_JPEG_QUALITY, 70],
            )
            if not encoded_ok:
                raise RuntimeError(f"Could not encode annotated view {view_index}.")

            view_results.append({
                "view": view_index,
                "counts": counts,
                "detections": detections,
            })
            annotated_images.append(
                "data:image/jpeg;base64,"
                + base64.b64encode(annotated).decode("ascii")
            )

    # Use the largest count seen in a single view to avoid counting the
    # same equipment repeatedly across overlapping room photographs.
    detected = {
        name: max(view["counts"].get(name, 0) for view in view_results)
        for name in required
    }
    return {
        "model": detector.model_path.name,
        "device": "cuda" if device == 0 else "cpu",
        "supported_classes": sorted(CLASS_NAMES.values()),
        "detected": detected,
        "views": view_results,
        "annotated_images": annotated_images,
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        with contextlib.redirect_stdout(sys.stderr):
            result = run_scan(payload)
        json.dump(result, sys.stdout, separators=(",", ":"))
        return 0
    except Exception as error:
        print(f"Dev2 inference failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
