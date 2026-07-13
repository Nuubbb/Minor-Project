// Point this at the machine running the Flask backend (app.py now binds
// host='0.0.0.0' so it's reachable from other devices on the LAN).
//   - Physical phone on the same Wi-Fi as the server: use the server
//     machine's LAN IP, e.g. `ip addr` / `ifconfig` (Linux/Mac) or
//     `ipconfig` (Windows) -- e.g. "http://192.168.1.82:5001".
//   - Android emulator on the SAME machine as the server: use the special
//     alias "http://10.0.2.2:5001" (routes to the host's localhost).
//   - iOS simulator on the SAME machine as the server: "http://127.0.0.1:5001" works directly.
//   - Physical phone connected over USB with `adb reverse tcp:5001 tcp:5001`
//     run on the host: "http://127.0.0.1:5001" also works directly.
export const API_BASE_URL = "http://127.0.0.1:5001";
