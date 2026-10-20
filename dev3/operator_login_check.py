
import getpass
import json
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000"


def post_json(path, payload):
    request = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"detail": body}


def main():
    print("SACH Operator Login Check")
    print("-------------------------")

    username = "delhi001_operator"
    password = getpass.getpass("Operator password: ")

    status, result = post_json(
        "/api/auth/login",
        {"username": username, "password": password},
    )
    del password

    if status != 200:
        print(f"Login failed (HTTP {status}).")
        print("Server response:", result)
        return

    token = result.get("access_token") or result.get("token")
    if not token:
        print("Login response mein token field nahi mila.")
        print("Available response fields:", list(result.keys()))
        return

    print("Login successful.")
    print("Token received: Yes (hidden)")

    request = urllib.request.Request(
        BASE_URL + "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            me = json.loads(response.read().decode("utf-8"))
            print("/api/auth/me HTTP status:", response.status)
            print("Account details:", json.dumps(me, indent=2))
    except urllib.error.HTTPError as exc:
        print("/api/auth/me failed (HTTP", exc.code, ").")
        print(exc.read().decode("utf-8", errors="replace"))
    finally:
        del token


if __name__ == "__main__":
    main()
