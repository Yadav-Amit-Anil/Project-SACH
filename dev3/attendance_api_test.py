
import getpass
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"
CENTRE_ID = "DELHI_001"
LIVE_HEADCOUNT = 1

username = input("Admin username [sach_admin]: ").strip() or "sach_admin"
password = getpass.getpass("Current admin password: ")

def api_request(path, payload=None, token=None):
    body = None
    headers = {}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers=headers,
        method="POST" if payload is not None else "GET",
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        raw = response.read().decode("utf-8")
        return response.status, json.loads(raw)

try:
    status, login = api_request(
        "/api/auth/login",
        {"username": username, "password": password},
    )
    token = login.get("access_token")

    if not token:
        print("Login response mein token nahi mila.")
        raise SystemExit(1)

    print("Login HTTP:", status)
    print("Token received: True")

    status, result = api_request(
        "/api/attendance/log",
        {
            "centre_id": CENTRE_ID,
            "live_headcount": LIVE_HEADCOUNT,
        },
        token,
    )

    print("Attendance API HTTP:", status)
    print("API status:", result.get("status"))
    print("Logged record:", result.get("logged"))
    print(
        "Updated centre headcount:",
        result.get("updated_centre_status", {}).get("live_headcount"),
    )

except urllib.error.HTTPError as error:
    print("HTTP error:", error.code)
    print("Response:", error.read().decode("utf-8"))
except Exception as error:
    print("Request failed:", type(error).__name__, str(error))
