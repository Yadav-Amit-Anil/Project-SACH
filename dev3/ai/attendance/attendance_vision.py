import cv2
import insightface
import numpy as np
import os
import base64
import json
import queue
import requests
import threading
import time
from datetime import datetime, timezone
from ultralytics import YOLO
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect


# ==================================================
# CONFIGURATION
# ==================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

KNOWN_FACES_DIR = os.path.join(
    BASE_DIR,
    "known_faces"
)

# Face recognition threshold
RECOGNITION_THRESHOLD = 0.45


# ==================================================
# BACKEND CONFIGURATION - DEV 3
# ==================================================

CENTRES = {
    "1": ("DELHI_001", "PMKVY Training Centre - North Delhi"),
    "2": ("LUCKNOW_002", "NSTI Skill Hub - Lucknow Central"),
    "3": ("MUMBAI_003", "Jan Shikshan Sansthan - Mumbai East"),
}


def select_centre():
    print("\nSelect the centre CCTV feed to monitor:")
    for choice, (centre_id, centre_name) in CENTRES.items():
        print(f"{choice}. {centre_name} ({centre_id})")

    while True:
        selected = input("Enter choice (1-3) or centre ID: ").strip().upper()
        if selected in CENTRES:
            return CENTRES[selected][0]
        if any(centre_id == selected for centre_id, _ in CENTRES.values()):
            return selected
        print("Invalid selection. Choose 1, 2, 3, or enter a listed centre ID.")


CENTRE_ID = os.getenv("SACH_CENTRE_ID", "").strip().upper() or select_centre()
if CENTRE_ID not in {centre_id for centre_id, _ in CENTRES.values()}:
    raise ValueError(f"Unknown SACH_CENTRE_ID: {CENTRE_ID}")
BACKEND_URL = os.getenv("SACH_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
API_URL = f"{BACKEND_URL}/api/attendance/log"
CAMERA_SOURCE_VALUE = os.getenv("SACH_CAMERA_SOURCE", "0")
try:
    CAMERA_SOURCE = int(CAMERA_SOURCE_VALUE)
except ValueError:
    CAMERA_SOURCE = CAMERA_SOURCE_VALUE
CAMERA_LABEL = os.getenv("SACH_CAMERA_LABEL", "Configured camera")
WS_URL = (
    BACKEND_URL.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
    + f"/ws/stream_upload/{CENTRE_ID}/attendance"
)

# Send attendance snapshots strictly every 2 seconds.
SEND_INTERVAL = 2

last_send_time = 0

frame_queue = queue.Queue(maxsize=1)
attendance_queue = queue.Queue(maxsize=1)
stop_workers = threading.Event()


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
                "to authorize attendance submissions."
            )
        response = requests.post(
            f"{BACKEND_URL}/api/auth/login",
            json={"username": username, "password": password},
            timeout=5,
        )
        response.raise_for_status()
        token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def send_attendance_updates():
    headers = None
    while not stop_workers.is_set():
        try:
            payload = attendance_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            if headers is None:
                headers = get_api_headers()
            response = requests.post(API_URL, json=payload, headers=headers, timeout=5)
            print(
                f"[ATTENDANCE API] HTTP {response.status_code}: "
                f"{response.text[:1000]}"
            )
            if response.status_code == 401 and not os.getenv("SACH_AI_API_TOKEN"):
                headers = get_api_headers()
                response = requests.post(API_URL, json=payload, headers=headers, timeout=5)
                print(
                    f"[ATTENDANCE API RETRY] HTTP {response.status_code}: "
                    f"{response.text[:1000]}"
                )
            response.raise_for_status()
            print(
                f"[SENT TO DEV 3] Centre: {CENTRE_ID} | "
                f"Headcount: {payload['live_headcount']} | Status: {response.status_code}"
            )
        except (requests.exceptions.RequestException, RuntimeError, KeyError) as error:
            headers = None
            print(f"[ATTENDANCE API ERROR] {error}")
            if isinstance(error, requests.exceptions.HTTPError) and error.response is not None:
                print(
                    f"[ATTENDANCE API ERROR RESPONSE] HTTP "
                    f"{error.response.status_code}: {error.response.text[:1000]}"
                )


def stream_annotated_frames():
    while not stop_workers.is_set():
        try:
            headers = get_api_headers()
            token = headers["Authorization"].partition(" ")[2]
            with connect(WS_URL, open_timeout=3, close_timeout=2) as websocket:
                websocket.send(json.dumps({"type": "auth", "token": token}))
                auth_result = json.loads(websocket.recv(timeout=5))
                if auth_result.get("type") != "authenticated":
                    raise RuntimeError("The live-feed WebSocket rejected authentication.")
                while not stop_workers.is_set():
                    try:
                        frame, headcount = frame_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    encoded_ok, jpeg = cv2.imencode(".jpg", frame)
                    if not encoded_ok:
                        print("[STREAM ERROR] Could not encode camera frame.")
                        continue
                    websocket.send(json.dumps({
                        "frame": base64.b64encode(jpeg).decode("ascii"),
                        "live_headcount": headcount,
                        "centre_id": CENTRE_ID,
                        "stream_type": "attendance",
                        "frame_width": int(frame.shape[1]),
                        "frame_height": int(frame.shape[0]),
                        "camera_label": CAMERA_LABEL,
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
            if not stop_workers.is_set():
                print(f"[STREAM ERROR] {error}; reconnecting.")
                stop_workers.wait(2)


workers = [
    threading.Thread(target=send_attendance_updates, daemon=True),
    threading.Thread(target=stream_annotated_frames, daemon=True),
]


# ==================================================
# LOAD YOLO
# ==================================================

print("Loading YOLO model...")

yolo_model = YOLO("yolo11n.pt")

print("YOLO model loaded")


# ==================================================
# LOAD INSIGHTFACE
# ==================================================

print("Loading InsightFace model...")

face_app = insightface.app.FaceAnalysis(
    name="buffalo_l",
    providers=["CPUExecutionProvider"]
)

face_app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

print("InsightFace model loaded")


# ==================================================
# LOAD KNOWN FACES
# ==================================================

known_face_embeddings = []
known_face_names = []

print("Loading known faces...")
print(
    f"Known faces folder: {KNOWN_FACES_DIR}"
)

if not os.path.exists(KNOWN_FACES_DIR):
    os.makedirs(KNOWN_FACES_DIR)


for filename in os.listdir(KNOWN_FACES_DIR):

    if not filename.lower().endswith(
        (".jpg", ".jpeg", ".png")
    ):
        continue

    image_path = os.path.join(
        KNOWN_FACES_DIR,
        filename
    )

    image = cv2.imread(image_path)

    if image is None:
        print(
            f"Could not read: {filename}"
        )
        continue

    faces = face_app.get(image)

    if len(faces) == 0:
        print(
            f"No face found: {filename}"
        )
        continue

    # Select largest face
    face = max(
        faces,
        key=lambda x:
        (x.bbox[2] - x.bbox[0]) *
        (x.bbox[3] - x.bbox[1])
    )

    embedding = face.embedding

    embedding = (
        embedding /
        np.linalg.norm(embedding)
    )

    name = os.path.splitext(
        filename
    )[0]

    known_face_embeddings.append(
        embedding
    )

    known_face_names.append(
        name
    )

    print(
        f"Loaded student: {name}"
    )


print(
    f"Local face profiles loaded: "
    f"{len(known_face_names)}"
)


# ==================================================
# HELPER FUNCTION
# ==================================================

def recognize_face(face_embedding):

    if len(known_face_embeddings) == 0:
        return "Unknown", 0.0

    embedding = (
        face_embedding /
        np.linalg.norm(face_embedding)
    )

    similarities = [
        float(
            np.dot(
                embedding,
                known_embedding
            )
        )
        for known_embedding
        in known_face_embeddings
    ]

    best_index = int(
        np.argmax(similarities)
    )

    best_similarity = (
        similarities[best_index]
    )

    if (
        best_similarity
        >= RECOGNITION_THRESHOLD
    ):
        return (
            known_face_names[best_index],
            best_similarity
        )

    return (
        "Unknown",
        best_similarity
    )


# ==================================================
# START WEBCAM
# ==================================================

cap = cv2.VideoCapture(CAMERA_SOURCE)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():

    print(
        "Error: Could not open webcam"
    )

    exit()


print()
print("========================================")
print("SIH PS245 - Attendance Vision Started")
print("========================================")

print(
    f"Backend API: {API_URL}"
)

print(
    f"Centre ID: {CENTRE_ID}"
)

print(
    "Live headcount will be sent every 2 seconds"
)

print(
    "Press Q to exit"
)

print()

for worker in workers:
    worker.start()


# ==================================================
# MAIN LOOP
# ==================================================

while True:

    ret, frame = cap.read()

    if not ret:

        print(
            "Error reading webcam"
        )

        break


    # ------------------------------------------------
    # YOLO PERSON TRACKING
    # ------------------------------------------------

    results = yolo_model.track(
        source=frame,
        persist=True,
        tracker="bytetrack.yaml",
        classes=[0],
        conf=0.35,
        iou=0.5,
        verbose=False
    )

    result = results[0]

    annotated_frame = result.plot()


    # ------------------------------------------------
    # GET PERSON BOXES
    # ------------------------------------------------

    person_boxes = []

    if result.boxes is not None:

        boxes = (
            result.boxes.xyxy
            .cpu()
            .numpy()
        )

        if result.boxes.id is not None:

            track_ids = (
                result.boxes.id
                .int()
                .cpu()
                .tolist()
            )

        else:

            track_ids = [
                None
                for _ in boxes
            ]


        for box, track_id in zip(
            boxes,
            track_ids
        ):

            x1, y1, x2, y2 = map(
                int,
                box
            )

            person_boxes.append(
                {
                    "box": (
                        x1,
                        y1,
                        x2,
                        y2
                    ),
                    "track_id": track_id
                }
            )


    # ------------------------------------------------
    # LIVE PERSON COUNT
    # ------------------------------------------------

    person_count = len(
        person_boxes
    )


    # Queue API work so network latency cannot pause inference.

    current_time = time.time()

    if current_time - last_send_time >= SEND_INTERVAL:
        payload = {
            "centre_id": CENTRE_ID,
            "live_headcount": person_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        put_latest(attendance_queue, payload)
        last_send_time = current_time


    # ------------------------------------------------
    # INSIGHTFACE DETECTION
    # ------------------------------------------------

    faces = face_app.get(frame)


    # ------------------------------------------------
    # MATCH FACE TO PERSON
    # ------------------------------------------------

    recognized_students = set()


    for face in faces:

        fx1, fy1, fx2, fy2 = (
            face.bbox.astype(int)
        )


        # Face center
        face_center_x = int(
            (fx1 + fx2) / 2
        )

        face_center_y = int(
            (fy1 + fy2) / 2
        )


        # Recognize face
        name, similarity = (
            recognize_face(
                face.embedding
            )
        )


        # Find which person contains
        # this face
        matched_person = None


        for person in person_boxes:

            px1, py1, px2, py2 = (
                person["box"]
            )


            if (
                px1 <= face_center_x <= px2
                and
                py1 <= face_center_y <= py2
            ):

                matched_person = person
                break


        # ------------------------------------------------
        # DISPLAY FACE INFORMATION
        # ------------------------------------------------

        label = (
            f"Local profile: {name} "
            f"{similarity:.2f}"
        )


        if matched_person is not None:

            track_id = (
                matched_person["track_id"]
            )


            if track_id is not None:

                label += (
                    f" | ID {track_id}"
                )


            if name != "Unknown":

                recognized_students.add(
                    name
                )


        # Face rectangle
        cv2.rectangle(
            annotated_frame,
            (fx1, fy1),
            (fx2, fy2),
            (0, 255, 0),
            2
        )


        # Face label
        cv2.putText(
            annotated_frame,
            label,
            (
                fx1,
                max(fy1 - 10, 20)
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0),
            2
        )


    # ------------------------------------------------
    # DISPLAY COUNTS
    # ------------------------------------------------

    face_count = len(faces)

    recognized_count = len(
        recognized_students
    )


    cv2.putText(
        annotated_frame,
        f"Persons: {person_count}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (0, 255, 255),
        2
    )


    cv2.putText(
        annotated_frame,
        f"Faces: {face_count}",
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (0, 255, 0),
        2
    )


    cv2.putText(
        annotated_frame,
        f"Local profile matches: {recognized_count}",
        (20, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (255, 255, 0),
        2
    )


    # ------------------------------------------------
    # SHOW RECOGNIZED STUDENTS
    # ------------------------------------------------

    y_position = 150


    for student in sorted(
        recognized_students
    ):

        cv2.putText(
            annotated_frame,
            f"Local match: {student}",
            (20, y_position),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2
        )

        y_position += 30


    put_latest(frame_queue, (annotated_frame, person_count))

    # ------------------------------------------------
    # DISPLAY WINDOW
    # ------------------------------------------------

    cv2.imshow(
        "SIH PS245 - Attendance Vision",
        annotated_frame
    )


    # ------------------------------------------------
    # KEYBOARD
    # ------------------------------------------------

    key = cv2.waitKey(10)


    if key != -1:

        key = key & 0xFF


        if (
            key == ord("q")
            or
            key == ord("Q")
        ):

            print(
                "Closing attendance vision..."
            )

            break


# ==================================================
# CLEANUP
# ==================================================

stop_workers.set()
cap.release()
for worker in workers:
    worker.join(timeout=1)

cv2.destroyAllWindows()


for _ in range(5):

    cv2.waitKey(1)


print(
    "Attendance vision stopped"
)