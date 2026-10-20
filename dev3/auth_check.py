
import getpass
import json
import urllib.request
import urllib.error

base_url = "http://127.0.0.1:8000"

username = input("Admin username [sach_admin]: ").strip() or "sach_admin"
password = getpass.getpass("Current admin password: ")

payload = json.dumps({
    "username": username,
    "password": password
}).encode("utf-8")

login_request = urllib.request.Request(
    f"{base_url}/api/auth/login",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(login_request, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))
        token = data.get("access_token")
        print("Login HTTP:", response.status)
        print("Token received:", bool(token))
except urllib.error.HTTPError as error:
    print("Login HTTP:", error.code)
    print("Login failed. Response:", error.read().decode("utf-8"))
    raise SystemExit(1)
except Exception as error:
    print("Request failed:", type(error).__name__)
    raise SystemExit(1)

if not token:
    print("Login response mein access token nahi mila.")
    raise SystemExit(1)

me_request = urllib.request.Request(
    f"{base_url}/api/auth/me",
    headers={"Authorization": f"Bearer {token}"},
)

try:
    with urllib.request.urlopen(me_request, timeout=10) as response:
        identity = json.loads(response.read().decode("utf-8"))
        print("Auth verification HTTP:", response.status)
        print("Username:", identity.get("username"))
        print("Role:", identity.get("role"))
except urllib.error.HTTPError as error:
    print("Auth verification HTTP:", error.code)
    print("Verification failed:", error.read().decode("utf-8"))
