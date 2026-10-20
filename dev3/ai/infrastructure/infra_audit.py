import cv2
import base64
import json
import os
import queue
import requests
import threading
import time
import numpy as np
from datetime import datetime, timezone
from src.equipment_detection.detector import CLASS_NAMES, EquipmentDetector
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

BACKEND_URL = os.getenv("SACH_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


def put_latest(target_queue, value):
    try:
        target_queue.put_nowait(value)
    except queue.Full:
        try:
            target_queue.get_nowait()
        except queue.Empty:
            pass
        target_queue.put_nowait(value)


def get_api_headers():
    token = os.getenv("SACH_AI_API_TOKEN")
    if not token:
        username = os.getenv("SACH_AI_USERNAME")
        password = os.getenv("SACH_AI_PASSWORD")
        if not username or not password:
            raise RuntimeError(
                "Set SACH_AI_API_TOKEN or SACH_AI_USERNAME and SACH_AI_PASSWORD "
                "to authorize audit submissions."
            )
        response = requests.post(
            f"{BACKEND_URL}/api/auth/login",
            json={"username": username, "password": password},
            timeout=5,
        )
        response.raise_for_status()
        token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def send_audit_updates(update_queue, stop_event, centre_id):
    headers = None
    while not stop_event.is_set():
        try:
            payload = update_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            if headers is None:
                headers = get_api_headers()
            response = requests.post(
                f"{BACKEND_URL}/api/audit/live",
                json=payload,
                headers=headers,
                timeout=5,
            )
            print(
                f"[AUDIT API] HTTP {response.status_code}: "
                f"{response.text[:1000]}"
            )
            if response.status_code == 401 and not os.getenv("SACH_AI_API_TOKEN"):
                headers = get_api_headers()
                response = requests.post(
                    f"{BACKEND_URL}/api/audit/live",
                    json=payload,
                    headers=headers,
                    timeout=5,
                )
                print(
                    f"[AUDIT API RETRY] HTTP {response.status_code}: "
                    f"{response.text[:1000]}"
                )
            response.raise_for_status()
            print(
                f"[PUSHED] {centre_id} | "
                f"Status Code: {response.status_code}"
            )
        except (requests.exceptions.RequestException, RuntimeError, KeyError) as error:
            headers = None
            print(f"[AUDIT API ERROR] {error}")
            if isinstance(error, requests.exceptions.HTTPError) and error.response is not None:
                print(
                    f"[AUDIT API ERROR RESPONSE] HTTP "
                    f"{error.response.status_code}: {error.response.text[:1000]}"
                )


def stream_annotated_frames(frame_queue, stop_event, centre_id):
    ws_url = (
        BACKEND_URL.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        + f"/ws/stream_upload/{centre_id}/infra"
    )
    while not stop_event.is_set():
        try:
            headers = get_api_headers()
            token = headers["Authorization"].partition(" ")[2]
            with connect(ws_url, open_timeout=3, close_timeout=2) as websocket:
                websocket.send(json.dumps({"type": "auth", "token": token}))
                auth_result = json.loads(websocket.recv(timeout=5))
                if auth_result.get("type") != "authenticated":
                    raise RuntimeError("The live-feed WebSocket rejected authentication.")
                while not stop_event.is_set():
                    try:
                        frame, live_status = frame_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    encoded_ok, jpeg = cv2.imencode(".jpg", frame)
                    if not encoded_ok:
                        print("[STREAM ERROR] Could not encode camera frame.")
                        continue
                    websocket.send(json.dumps({
                        "frame": base64.b64encode(jpeg).decode("ascii"),
                        **live_status,
                    }))
        except (
            OSError,
            TimeoutError,
            ConnectionClosed,
            RuntimeError,
            KeyError,
            ValueError,
            requests.exceptions.RequestException,
        ) as error:
            if not stop_event.is_set():
                print(f"[STREAM ERROR] {error}; reconnecting.")
                stop_event.wait(2)


def receive_attendance_frames(frame_queue, stop_event, centre_id):
    ws_url = (
        BACKEND_URL.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        + f"/ws/live_feed/{centre_id}/attendance"
    )
    while not stop_event.is_set():
        try:
            headers = get_api_headers()
            token = headers["Authorization"].partition(" ")[2]
            with connect(
                ws_url,
                open_timeout=3,
                close_timeout=2,
                max_queue=1,
            ) as websocket:
                websocket.send(json.dumps({"type": "auth", "token": token}))
                auth_result = json.loads(websocket.recv(timeout=5))
                if auth_result.get("type") != "authenticated":
                    raise RuntimeError(
                        "The attendance visual source rejected authentication."
                    )
                print(f"[VISUAL SOURCE] Connected to Dev1 feed for {centre_id}.")
                while not stop_event.is_set():
                    try:
                        message = json.loads(websocket.recv(timeout=5))
                    except TimeoutError:
                        continue
                    if (
                        not isinstance(message, dict)
                        or
                        message.get("centre_id") != centre_id
                        or message.get("stream_type") != "attendance"
                        or not isinstance(message.get("frame"), str)
                    ):
                        continue
                    frame_bytes = base64.b64decode(
                        message["frame"],
                        validate=True,
                    )
                    frame = cv2.imdecode(
                        np.frombuffer(frame_bytes, dtype=np.uint8),
                        cv2.IMREAD_COLOR,
                    )
                    if frame is None:
                        print("[VISUAL SOURCE ERROR] Dev1 sent an invalid image frame.")
                        continue
                    put_latest(frame_queue, (frame, message))
        except (
            OSError,
            TimeoutError,
            ConnectionClosed,
            RuntimeError,
            KeyError,
            ValueError,
            requests.exceptions.RequestException,
        ) as error:
            if not stop_event.is_set():
                print(
                    f"[VISUAL SOURCE ERROR] {error}; reconnecting to "
                    f"Dev1 attendance feed for {centre_id}."
                )
                stop_event.wait(2)


centre_map = {
    "1": "DELHI_001",
    "2": "LUCKNOW_002",
    "3": "MUMBAI_003",
}

configured_centre = os.getenv("SACH_CENTRE_ID", "").strip().upper()
if configured_centre:
    if configured_centre not in centre_map.values():
        raise ValueError(f"Unknown SACH_CENTRE_ID: {configured_centre}")
    CENTRE_ID = configured_centre
else:
    print("================================================")
    print("   SACH - Smart Attendance & Compliance Hub   ")
    print("   Field Auditor Infrastructure Scanner v1.0   ")
    print("================================================")
    print("Select Training Centre to Audit:")
    print("1. DELHI_001   - PMKVY Training Centre (North Delhi)")
    print("2. LUCKNOW_002 - NSTI Skill Hub (Lucknow Central)")
    print("3. MUMBAI_003  - Jan Shikshan Sansthan (Mumbai East)")
    print("================================================")
    while True:
        choice = input("Enter Choice Number (1, 2, or 3): ").strip().upper()
        if choice in centre_map.values():
            CENTRE_ID = choice
            break
        if choice in centre_map:
            CENTRE_ID = centre_map[choice]
            break
        print("Invalid choice. Please enter 1, 2, or 3.")

print(f"\n[AUDIT STARTED] Monitored Centre: {CENTRE_ID}\n")

# Use Dev2's trained equipment model instead of COCO class IDs.
model = EquipmentDetector().model
computer_class_id = next(
    class_id
    for class_id, class_name in CLASS_NAMES.items()
    if class_name == "computer"
)
source_frame_queue = queue.Queue(maxsize=1)
frame_queue = queue.Queue(maxsize=1)
audit_queue = queue.Queue(maxsize=1)
stop_workers = threading.Event()
workers = [
    threading.Thread(
        target=receive_attendance_frames,
        args=(source_frame_queue, stop_workers, CENTRE_ID),
        daemon=True,
    ),
    threading.Thread(
        target=send_audit_updates,
        args=(audit_queue, stop_workers, CENTRE_ID),
        daemon=True,
    ),
    threading.Thread(
        target=stream_annotated_frames,
        args=(frame_queue, stop_workers, CENTRE_ID),
        daemon=True,
    ),
]

SEND_INTERVAL = 2
COUNT_CHANGE_THRESHOLD = 5
last_send_time = 0
last_sent_count = None

for worker in workers:
    worker.start()

while not stop_workers.is_set():
    try:
        frame, source_message = source_frame_queue.get(timeout=1)
    except queue.Empty:
        continue
    results = model.predict(
        source=frame,
        classes=[computer_class_id],
        conf=0.25,
        verbose=False,
    )
    result = results[0]
    detected_pcs = (
        int((result.boxes.cls == computer_class_id).sum().item())
        if result.boxes is not None else 0
    )
    live_status = {
        "detected_computers": detected_pcs,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_centre_id": CENTRE_ID,
        "source_stream_type": "attendance",
        "source_received_at": source_message.get("received_at"),
        "source_camera_label": source_message.get("camera_label"),
    }

    annotated_frame = result.plot()
    cv2.putText(annotated_frame, f"SACH Audit [{CENTRE_ID}]: {detected_pcs} Computers", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow("SACH - Infrastructure Audit Camera", annotated_frame)

    current_time = time.time()
    if (
        last_sent_count is None
        or current_time - last_send_time >= SEND_INTERVAL
        or abs(detected_pcs - last_sent_count) >= COUNT_CHANGE_THRESHOLD
    ):
        payload = {
            "centre_id": CENTRE_ID,
            "detected_computers": detected_pcs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        put_latest(audit_queue, payload)
        last_send_time = current_time
        last_sent_count = detected_pcs

    put_latest(frame_queue, (annotated_frame, live_status))

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

stop_workers.set()
for worker in workers:
    worker.join(timeout=1)
cv2.destroyAllWindows()