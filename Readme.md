# Real-Time Surveillance System

An AI-powered surveillance system that detects **weapons**, **violence**, **crowd anomalies**, **loitering**, and **restricted-zone intrusions** in real time from a webcam, video file, or RTSP/CCTV feed. Built with Flask, YOLOv8, and a custom MobileNet-LSTM violence classifier.

---

## Features

- **Weapon Detection** — Custom-trained YOLOv8 model identifies guns, knives, and other weapons in the video feed.
- **Violence Detection** — A MobileNet + LSTM temporal model analyzes sequences of frames to detect violent activity.
- **Crowd Monitoring** — Tracks person count using YOLOv8 with persistent object tracking; flags unusual crowd density.
- **After-Hours Loitering** — Detects people lingering beyond a configurable dwell time after closing hours.
- **Restricted Zone Intrusion** — Admins draw restricted zones on the feed; the system alerts when anyone enters them.
- **Context-Aware Alerting** — A threat assessor engine combines all detections with time-of-day, active events, and configurable thresholds to decide severity (Log / Notify / Alarm).
- **Email Alerts** — Sends email notifications to the on-duty operator when high-severity events are detected, with screenshots attached.
- **Community Broadcasting** — Admins can broadcast critical alerts to registered community/colony members via email.
- **Event Scheduling** — Schedule known events (gatherings, functions) so the system adjusts crowd thresholds and reduces false alarms.
- **Role-Based Access** — Admin and Resident roles with separate dashboards, user approval workflow, and email verification on signup.
- **Live Dashboard** — Real-time video feed, alert table with dismiss/false-alarm controls, threat distribution charts, and AI-generated suggestions.
- **Admin Settings** — Configurable closing hour, dwell time, violence threshold, weapon confidence, and cooldown timers — all from the web UI.
- **Cross-Platform Audio Alarm** — Triggers an audible alert on Windows, macOS, and Linux when an ALARM-tier event fires.

---

## How It Works

**Detection Pipeline**
- **Input** → Webcam, video file, or RTSP/CCTV stream
- **Person Detection** → YOLOv8 Nano (`yolov8n.pt`) with persistent tracking, runs every N frames
- **Weapon Detection** → Custom YOLOv8 model (`best.pt`), runs at a lower frequency
- **Violence Detection** → MobileNet + LSTM (`violence_mobilenet_lstm.pt`) analyzes frame buffers temporally
- **Context Engine** → Combines all signals with time, zones, events, and admin thresholds
- **Output** → Annotated video feed + tiered alerts (Log → Notify → Alarm) + email + audio

**User Flow**
- **Sign Up** → Email verification → Admin approval → Account active
- **Sign In** → Role-based dashboard (Admin gets full controls, Residents see alerts)
  - Live Feed with detection overlays
  - Alert History with dismiss/false-alarm options
  - User Management (Admin)
  - Event Scheduling (Admin)
  - Community Members (Admin)
  - Restricted Zones (Admin)
  - System Settings (Admin)
- **Logout** → Feed stops automatically (no background processing)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 3.0, Python |
| Object Detection | YOLOv8 (Ultralytics) |
| Violence Model | MobileNet + LSTM (PyTorch) |
| Video Processing | OpenCV |
| Database | SQLite |
| Auth | Werkzeug password hashing, email verification, DNS MX validation |
| Frontend | Jinja2 templates, HTML/CSS/JS |
| Alerts | SMTP email with screenshots |

---

## Getting Started

### Prerequisites

- Python 3.9+
- A webcam, video file, or RTSP camera URL
- (Optional) SMTP credentials for email alerts

### Installation

```bash
git clone https://github.com/Nuubbb/Minor-Project.git
cd Minor-Project
pip install -r requirements.txt
```

### Configuration

Edit `config.py` to set your secret key, SMTP credentials, and screenshot directory.

### Run

```bash
python app.py
```

The server starts at `http://localhost:5001`. Open it in your browser, sign up, and start monitoring.

---

## Project Structure

```
Minor-Project/
├── app.py                  # Flask app — routes, auth, dashboard
├── api.py                  # REST API endpoints
├── auth.py                 # Authentication helpers
├── detection.py            # Detection pipeline (person, weapon, violence, zones)
├── violence_detector.py    # MobileNet + LSTM violence classifier
├── context_engine.py       # Threat assessor — combines signals into tiered alerts
├── email_alert.py          # Email notifications and community broadcasts
├── database.py             # SQLite schema, queries, and helpers
├── config.py               # App configuration (secret key, paths, SMTP)
├── normal.py               # Normal detection profile
├── prof.py                 # Profiling script
├── train_violence.py       # Training script for the violence model
├── best.pt                 # Custom-trained YOLOv8 weapon detection weights
├── violence_mobilenet_lstm.pt  # Violence detection model weights
├── yolov8n.pt / yolov8m.pt / yolov8s.pt  # YOLOv8 general models
├── requirements.txt        # Python dependencies
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS, JS, and static assets
├── mobile/                 # Mobile app files
├── cache/                  # Cached detection data
└── SETUP.md                # Additional setup notes
```

---

## Limitations

- SQLite is used for simplicity — not suitable for high-concurrency production deployments.
- Model weights (`best.pt`, `violence_mobilenet_lstm.pt`) are included in the repo, which inflates the repo size.
- The DISMISS_SECRET for email-based alert dismissal is hardcoded — should be replaced with proper token-based auth in production.
- RTSP camera URL is hardcoded in `detection.py` — needs to be moved to config or the admin settings page.

---

## License

For licensing inquiries, please open an issue or contact the author directly.
