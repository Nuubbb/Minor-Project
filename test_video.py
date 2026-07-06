"""
test_video.py — Real-Time Surveillance System (main program)
--------------------------------------------------------------------------------
Architecture:
    DETECTORS  ->  produce raw signals (violence score, weapons, people, IDs)
    ENGINE     ->  ThreatAssessor combines signals + context -> a RESPONSE TIER
    ACTIONS    ->  tier decides what happens (log / notify / siren)

The engine (context_engine.py) is the single decision-maker. Detectors only
report what they see; they do NOT decide alarms. This is the false-alarm
reduction core of the project.
"""
import cv2
import os
import time
import winsound
from datetime import datetime
from ultralytics import YOLO
from database import init_db, log_alert
from violence_detector import ViolenceDetector
from context_engine import ThreatAssessor, IGNORE, LOG, NOTIFY, ALARM

# ----------------- INPUT SOURCE -----------------
USE_WEBCAM = False                 # True = live camera, False = play a video file
VIDEO_PATH = "fight.mp4"           # video file to test on (put it in this folder)

# weapon class names to treat as weapons (matches any dataset's naming via keywords)
WEAPON_KEYWORDS = ("gun", "knife", "knive", "pistol", "rifle", "handgun", "shotgun", "weapon", "blade")

# how often (seconds) the SAME alert type may re-log / re-notify / re-siren (anti-spam)
ACTION_COOLDOWN = 5

# ----------------- SETUP -----------------
init_db()
general_model = YOLO("yolov8s.pt")                                   # person detection + tracking
weapon_model = YOLO("best.pt")                                       # gun/knife detection
violence_detector = ViolenceDetector("violence_mobilenet_lstm.pt")  # temporal violence model
assessor = ThreatAssessor()                                          # the context-aware decision engine

last_action = {}   # alert_type -> last time we acted on it (anti-spam)


def notify(message):
    """Desktop notification when a threat appears. Real popup if plyer is
    installed; always prints + shows on screen so it never crashes the demo."""
    print("[NOTIFY]", message)
    try:
        from plyer import notification
        notification.notify(title="Surveillance Alert", message=message, timeout=5)
    except Exception:
        pass   # plyer missing -> console + on-screen banner still work


def siren():
    """Siren on ALARM. Plays siren.wav if present, else a beep pattern."""
    try:
        if os.path.exists("siren.wav"):
            winsound.PlaySound("siren.wav", winsound.SND_ASYNC)
            return
    except Exception:
        pass
    winsound.Beep(1000, 150)
    winsound.Beep(1300, 150)


def should_act(alert_type):
    """Anti-spam: True only if ACTION_COOLDOWN seconds passed since last action."""
    now = time.time()
    if now - last_action.get(alert_type, 0) >= ACTION_COOLDOWN:
        last_action[alert_type] = now
        return True
    return False


def detect_signals(img):
    """Run every detector and return RAW signals only (no decisions here)."""
    # person detection + ByteTrack IDs
    person_results = general_model.track(img, classes=[0], conf=0.5,
                                         persist=True, verbose=False)[0]
    img = person_results.plot()
    person_count = len(person_results.boxes)
    track_ids = (person_results.boxes.id.int().tolist()
                 if person_results.boxes.id is not None else [])

    # weapon detection -> list of (class_name, confidence)
    weapon_results = weapon_model(img, conf=0.5, verbose=False)[0]
    img = weapon_results.plot()
    weapons = []
    for box in weapon_results.boxes:
        name = weapon_model.names[int(box.cls[0])].lower()
        if any(k in name for k in WEAPON_KEYWORDS):
            weapons.append((name, float(box.conf[0])))

    return img, person_count, track_ids, weapons


# ----------------- INPUT -----------------
if USE_WEBCAM:
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)   # live camera (DSHOW = reliable on Windows)
else:
    cap = cv2.VideoCapture(VIDEO_PATH)         # play a video file

if not cap.isOpened():
    print("ERROR: could not open input. Check VIDEO_PATH or the camera.")

# on-screen colour per tier (BGR): LOG=yellow, NOTIFY=orange, ALARM=red
TIER_COLOR = {LOG: (0, 255, 255), NOTIFY: (0, 165, 255), ALARM: (0, 0, 255)}

# ----------------- MAIN LOOP -----------------
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 1) violence score from the temporal model (clean frame, before boxes/flip)
    is_violent, violence_prob = violence_detector.update(frame)

    # 2) run detectors -> raw signals (also draws the boxes)
    img = cv2.flip(frame, 1) if USE_WEBCAM else frame.copy()   # mirror the live camera only
    img, person_count, track_ids, weapons = detect_signals(img)

    # 3) THE BRAIN: engine combines all signals + context -> a response tier
    tier, alert_type, message, conf = assessor.assess(
        violence_prob=violence_prob,
        weapons=weapons,
        person_count=person_count,
        track_ids=track_ids,
        current_hour=datetime.now().hour)

    # 4) act on the tier
    if tier != IGNORE:
        # persistent on-screen banner every frame the condition holds
        cv2.putText(img, message, (20, 50), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, TIER_COLOR.get(tier, (0, 0, 255)), 2)
        # log / notify / siren -- throttled so it never spams
        if should_act(alert_type):
            log_alert(alert_type, conf)             # every tier is recorded to the database
            if tier >= NOTIFY:
                notify(message)                     # NOTIFY + ALARM -> desktop notification
            if tier == ALARM:
                siren()                             # ALARM only -> siren

    # live violence score readout (green = calm, red = violent) -- demo eye-candy
    cv2.putText(img, f"Violence: {violence_prob:.2f}", (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (0, 0, 255) if is_violent else (0, 255, 0), 2)

    cv2.imshow("Surveillance System", img)
    if cv2.waitKey(1) == 27:   # ESC to exit
        break

cap.release()
cv2.destroyAllWindows()