"""Quick import test for the new WaterPilot files."""
import sys, traceback
sys.path.insert(0, 'c:/Users/Happy/Desktop/ndeshcool')

errors = []

def try_import(name):
    try:
        exec(f"from {name} import *")
        print(f"OK: {name}")
    except Exception as e:
        print(f"FAIL: {name} -> {e}")
        errors.append(name)

try_import("models")
try_import("services.qr_service")
try_import("services.auth_service")
try_import("pages.create_account_page")
try_import("pages.qr_scanner_page")
try_import("pages.join_registration_page")
try_import("pages.partner.settings_page")

if errors:
    print(f"\n{len(errors)} FAILURES: {errors}")
    sys.exit(1)
else:
    print("\nALL IMPORTS OK")