
import getpass
import json
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "delhi001_operator"
CENTRE_ID = "DELHI_001"


def request_json(path, method="GET", payload=None, token=None):
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            try:
                result = json.loads(body) if body else {}
            except json.JSONDecodeError:
                result = {"response": body}
            return response.status, result
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            result = json.loads(body)
        except json.JSONDecodeError:
            result = {"detail": body}
        return exc.code, result


def main():
    print("SACH Operator Attendance API Test")
    print("---------------------------------")
    print("Centre:", CENTRE_ID)

    password = getpass.getpass("Operator password: ")

    status, result = request_json(
        "/api/auth/login",
        method="POST",
        payload={"username": USERNAME, "password": password},
    )
    del password

    if status != 200:
        print(f"Login failed: HTTP {status}")
        print("Response:", result)
        return

    token = result.get("access_token") or result.get("token")
    if not token:
        print("Login response mein token nahi mila.")
        return

    print("Login successful. Token hidden.")

    # NOTE: This creates a real test attendance record and
    # updates the centre's live_headcount to 1.
    confirm = input(
        "Send TEST attendance for DELHI_001? Type YES to continue: "
    ).strip()

    if confirm != "YES":
        print("Test cancelled. No attendance request sent.")
        del token
        return

    status, result = request_json(
        "/api/attendance/log",
        method="POST",
        payload={
            "centre_id": CENTRE_ID,
            "live_headcount": 1,
        },
        token=token,
    )

    print("\nAttendance API HTTP status:", status)
    print("Response:", json.dumps(result, indent=2))
    del token

    if status == 200:
        print("\nPASS: Operator attendance request accepted.")
    else:
        print("\nFAIL: Operator attendance request was not accepted.")


if __name__ == "__main__":
    main()
