# Real-Time Surveillance System

A smart surveillance platform that combines deep learning–based violence detection, weapon detection, and crowd monitoring with a full-featured web dashboard and mobile app. Built as a minor project at Kathmandu Engineering College, Tribhuvan University.


## Features

- **Violence Detection** : MobileNetV2 + BiLSTM model trained on the RLVS dataset (~98% validation accuracy) classifies video frames in real time
- **Weapon Detection** : Custom-trained YOLOv8 model (`best.pt`) detects guns and knives (mAP@50 = 0.855 overall; guns 0.975, knives 0.720)
- **Crowd Monitoring** : Rolling person-count smoothing to detect unusual crowd density, with scheduled event awareness to reduce false alarms
- **Restricted Zone Intrusion** : Draw zones on the dashboard; triggers alarm + log + screenshot + email when a person enters
- **After-Hours Detection** : Flags activity outside configured operating hours
- **Email Alerts** : Automated email notifications to operators and community broadcast to all registered residents, with one-click dismiss or broadcast from the email itself
- **Context-Aware Threat Assessment** : ThreatAssessor engine with four tiers: `IGNORE`, `LOG`, `NOTIFY`, `ALARM`
- **Community Management** : Add/edit/remove residents with phone, email, and GPS coordinates displayed on an interactive map
- **Event Scheduling** : Define expected events to suppress false crowd alerts during gatherings
- **Analytics Dashboard** : 7-day trend charts, per-type breakdowns, and AI-generated threat insights
- **Mobile App** : React Native/Expo companion app for on-the-go monitoring
- **Role-Based Access** : Admin and Resident portals with email-verified signup and approval flow


## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask |
| Detection | YOLOv8 (Ultralytics), MobileNetV2+BiLSTM (PyTorch) |
| Database | SQLite |
| Frontend | HTML/CSS/JS, Chart.js, Leaflet.js |
| Mobile | React Native, Expo |
| Alerts | smtplib (Gmail SMTP with App Password) |

---

## Project Structure

├── app.py                  # Flask routes and main application
├── detection.py            # Frame processing, violence & weapon detection loop
├── violence_detector.py    # MobileNetV2+BiLSTM inference wrapper
├── context_engine.py       # ThreatAssessor — context-aware alert logic
├── email_alert.py          # Email notifications (operator + community broadcast)
├── database.py             # SQLite schema, migrations, CRUD operations
├── config.py               # System configuration
├── auth.py                 # Authentication helpers
├── templates/              # Jinja2 HTML templates
│   ├── dashboard.html      # Main monitoring dashboard
│   ├── alerts.html         # Alert history
│   ├── community.html      # Community member management + map
│   ├── events.html         # Event scheduling
│   ├── settings.html       # System settings
│   ├── users.html          # User management (Admin)
│   └── ...
├── static/                 # Static assets (logos, CSS)
├── mobile/                 # React Native / Expo mobile app
├── best.pt                 # Trained YOLOv8 weapon detection model
├── violence_mobilenet_lstm.pt  # Trained violence detection model
├── requirements.txt        # Python dependencies
└── SETUP.md                # Detailed setup instructions


## Quick Start

### Prerequisites

- Python 3.10 or 3.11
- Webcam or CCTV RTSP URL
- Node.js 18+ (for mobile app)

### Installation

```bash
git clone https://github.com/Nuubbb/Minor-Project.git
cd Minor-Project
python -m venv venv
venv\Scripts\activate          # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
python app.py
```

The server starts at `http://0.0.0.0:5001`.

### Default Login

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |

Residents can sign up through the app with email verification and admin approval.

### Mobile App

```bash
cd mobile
npm install
npx expo start

Update `mobile/src/config.ts` with your backend's LAN IP. See [SETUP.md](SETUP.md) for detailed instructions including USB debugging setup.


## Detection Models

| Model | Architecture | Dataset | Key Metric |
|-------|-------------|---------|------------|
| Violence | MobileNetV2 + BiLSTM | RLVS | ~98% validation accuracy |
| Weapon | YOLOv8 (custom) | Custom annotated | mAP@50 = 0.855 |


## Contributors

- **Shreeya Shrestha** :(https://github.com/shreeya-12shrestha)
- **Sudarshan Baral**  :(https://github.com/Proxicenturi47)
- **Samip Shrestha**   :(https://github.com/Nuubbb)
- **Suyasa Sigdel**    :(https://github.com/SuyasaSigdel01)

## License

This project was developed as an academic minor project at Kathmandu Engineering College under Tribhuvan University.