from pathlib import Path

SECRET_KEY = "super_secure_surveillance_key_2026"   # shared Flask session + JWT signing key
JWT_ALGO = "HS256"
JWT_EXP_HOURS = 12

# ----------------- MESSAGE PACKETS (prototype) -----------------
SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

# Seed value only -- database.py copies this into the `device_location` table
# on first run. The live value is admin-editable after that (see
# database.get_device_location/update_device_location and
# api.py's /api/device_location routes) -- don't read this constant directly.
DEVICE_LOCATION = {
    "label": "Camera 1",
    "lat": 27.6710,
    "lng": 85.4298,
}

