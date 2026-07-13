# Setup Guide

How to get the backend and mobile app running on a new machine.

## 0. Transfer the code

If you haven't pushed to a remote yet, make sure these large binary files
actually travel with the repo (a plain `git clone` only picks them up if
they're committed):

- `best.pt`, `yolov8n.pt`, `yolov8s.pt`, `yolov8m.pt`
- `violence_mobilenet_lstm.pt`
- `database.db`

## 1. Backend (Python)

**Requirements:**
- Python **3.10 or 3.11**. `torch==2.3.1` in `requirements.txt` will fail to
  install on very new Python versions (3.13+), so check `python3 --version`
  first. If your system Python is too new, install 3.10 via `pyenv` (or
  equivalent) and use that instead.
- **Linux only:** opencv-python needs a couple of system libs that minimal
  installs often lack:
  ```bash
  sudo apt install libgl1 libglib2.0-0   # Debian/Ubuntu
  ```
- A webcam, or an accessible CCTV RTSP URL — live detection reads from
  `cv2.VideoCapture(0)` by default.

**Install and run:**
```bash
cd Surveillance-System
python3.10 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
This binds to `0.0.0.0:5001` and prints the LAN IP it's reachable on, e.g.
`Running on http://192.168.1.82:5001` — note that IP, you'll need it below.

## 2. Mobile app (Node/Expo)

**Requirements:**
- Node.js 18+ and npm.
- No Android/iOS SDK needed if you're just using a physical phone — install
  the **Expo Go** app from the Play Store / App Store.

**Point it at your backend:**

Edit `mobile/src/config.ts` and set `API_BASE_URL` to the LAN IP from step 1:
```ts
export const API_BASE_URL = "http://192.168.x.x:5001";
```

**Install and run:**
```bash
cd mobile
npm install
npx expo start
```
Scan the printed QR code with Expo Go. Your phone and the backend machine
must be on the **same Wi-Fi network**.

Alternative for Android over USB (no Wi-Fi dependency): enable USB debugging
on the phone, connect it, then:
```bash
adb reverse tcp:5001 tcp:5001
adb reverse tcp:8081 tcp:8081
npx expo start --localhost
```
and set `API_BASE_URL` to `http://127.0.0.1:5001` instead.

## 3. Log in

Seeded admin account: `admin` / `admin123` (role: Admin). Operators can also
sign up in-app.
