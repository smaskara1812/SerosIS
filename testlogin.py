"""
Standalone script to test the AD (Active Directory) authentication endpoint
directly, the same way UnifiedAuthenticationView.try_ad_authentication()
does in PortPermitApp/portPermitAPI/views.py.

Usage:
    python test_ad_login.py
    python test_ad_login.py --alias jdoe
"""

import argparse
import base64
import getpass
import json
import sys

import requests

AD_AUTH_URL = "https://mobileservices.essar.com/prod/web/ldap/api/AuthAPI/IsAccountAuthorized/"


def test_ad_login(alias: str, password: str) -> None:
    encoded_username = base64.b64encode(alias.encode()).decode()
    encoded_password = base64.b64encode(password.encode()).decode()

    headers = {
        "UserID": encoded_username,
        "Password": encoded_password,
    }

    print(f"\nCalling AD endpoint: {AD_AUTH_URL}")
    print(f"UserID header (base64): {encoded_username}")

    try:
        response = requests.get(AD_AUTH_URL, headers=headers, timeout=15)
    except requests.RequestException as exc:
        print(f"\n[FAIL] Request to AD API failed: {exc}")
        sys.exit(1)

    print(f"HTTP status: {response.status_code}")

    if response.status_code != 200:
        print(f"[FAIL] Non-200 response.\nBody: {response.text}")
        sys.exit(1)

    try:
        data = response.json()
    except ValueError:
        print(f"[FAIL] Response was not valid JSON.\nBody: {response.text}")
        sys.exit(1)

    print("Response JSON:")
    print(json.dumps(data, indent=2))

    if data.get("isSuccess", False):
        print(f"\n[SUCCESS] AD authentication succeeded for alias '{alias}'.")
        print(f"AD token: {data.get('token', '')}")
    else:
        print(f"\n[FAIL] AD authentication failed for alias '{alias}'.")


def main():
    parser = argparse.ArgumentParser(description="Test AD login against the AD AuthAPI.")
    parser.add_argument("--alias", "-u", help="AD alias/username", default=None)
    args = parser.parse_args()

    alias = args.alias or input("Enter alias (AD username): ").strip()
    password = getpass.getpass("Enter password: ")

    if not alias or not password:
        print("Alias and password are required.")
        sys.exit(1)

    test_ad_login(alias, password)


if __name__ == "__main__":
    main()
