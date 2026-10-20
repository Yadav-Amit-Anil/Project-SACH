
import getpass
import json
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000"
ADMIN_USERNAME = "sach_admin"
NEW_USERNAME = "delhi001_operator"
CENTRE_ID = "DELHI_001"


def post_json(path, payload, token=None):
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            details = json.loads(body)
        except json.JSONDecodeError:
            details = {"detail": body}
        return exc.code, details


def main():
    print("SACH Centre Operator Account Setup")
    print("----------------------------------")

    admin_password = getpass.getpass(
        "Existing sach_admin password: "
    )

    status, result = post_json(
        "/api/auth/login",
        {
            "username": ADMIN_USERNAME,
            "password": admin_password,
        },
    )

    # Login ke baad local variable se password hata do.
    del admin_password

    if status != 200:
        print(f"Admin login failed (HTTP {status}).")
        print("Server response:", result)
        return

    token = result.get("access_token") or result.get("token")
    if not token:
        print("Login response mein token nahi mila.")
        print("Response fields:", list(result.keys()))
        return

    print("Admin login successful.")

    operator_password = getpass.getpass(
        "New operator password (12-128 characters): "
    )
    confirm_password = getpass.getpass(
        "Confirm new operator password: "
    )

    if operator_password != confirm_password:
        print("Passwords match nahi karte. Account create nahi hua.")
        return

    if not 12 <= len(operator_password) <= 128:
        print("Password 12 se 128 characters ka hona chahiye.")
        return

    status, result = post_json(
        "/api/auth/users",
        {
            "username": NEW_USERNAME,
            "password": operator_password,
            "role": "CENTRE_OPERATOR",
            "centre_id": CENTRE_ID,
        },
        token=token,
    )

    del operator_password
    del confirm_password
    del token

    if status == 201:
        user = result.get("user", {})
        print("\nOperator account created successfully.")
        print("Username:", user.get("username", NEW_USERNAME))
        print("Role:", user.get("role", "CENTRE_OPERATOR"))
        print("Centre:", user.get("centre_id", CENTRE_ID))
    elif status == 409:
        print("Account already exists. Duplicate account create nahi hua.")
        print("Server response:", result)
    else:
        print(f"\nAccount creation failed (HTTP {status}).")
        print("Server response:", result)


if __name__ == "__main__":
    main()
