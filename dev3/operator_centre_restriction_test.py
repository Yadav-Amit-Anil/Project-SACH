
import getpass
import json
import urllib.request
import urllib.error

base = "http://127.0.0.1:8000"

password = getpass.getpass("Operator password: ")
login_data = json.dumps({
    "username": "delhi001_operator",
    "password": password
}).encode()
del password

login_req = urllib.request.Request(
    base + "/api/auth/login",
    data=login_data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

with urllib.request.urlopen(login_req, timeout=15) as response:
    login_result = json.loads(response.read().decode())

token = login_result.get("access_token") or login_result.get("token")
print("Login successful. Token hidden.")

payload = json.dumps({
    "centre_id": "LUCKNOW_002",
    "live_headcount": 1
}).encode()

attendance_req = urllib.request.Request(
    base + "/api/attendance/log",
    data=payload,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(attendance_req, timeout=15) as response:
        print("Attendance HTTP status:", response.status)
        print("Response:", response.read().decode())
except urllib.error.HTTPError as error:
    print("Attendance HTTP status:", error.code)
    print("Response:", error.read().decode())
finally:
    del token
