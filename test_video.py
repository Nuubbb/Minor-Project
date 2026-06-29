import cv2
import time
from ultralytics import YOLO

# Models
general_model = YOLO("yolov8s.pt")
weapon_model = YOLO("best.pt")

# Tracking & Thresholds
DWELL_THRESHOLD = 15         
track_start_time = {}        
THREAT_CLASSES = ["guns", "knife", "violence", "pistol"]

def process_frame(img):
    img = cv2.flip(img, 1)

    # 1. Person Detection + TRACKING
    person_results = general_model.track(img, classes=[0], conf=0.5, persist=True, verbose=False)[0]
    img = person_results.plot()
    person_count = len(person_results.boxes)

    # 2. DWELL-TIME (Loitering) Check
    dwell_alert = False
    if person_results.boxes.id is not None:
        ids = person_results.boxes.id.int().tolist()
        now = time.time()
        for pid in ids:
            if pid not in track_start_time:
                track_start_time[pid] = now
            elapsed = now - track_start_time[pid]
            if elapsed > DWELL_THRESHOLD:
                dwell_alert = True

    # 3. Weapon/Violence Detection
    weapon_results = weapon_model(img, conf=0.5, verbose=False)[0]
    img = weapon_results.plot()

    alert_triggered = False
    alert_message = ""
    alert_type = ""
    alert_conf = 0.0

    for box in weapon_results.boxes:
        class_id = int(box.cls[0])
        class_name = weapon_model.names[class_id]
        if class_name.lower() in THREAT_CLASSES:
            alert_triggered = True
            alert_type = class_name
            alert_conf = float(box.conf[0])
            alert_message = "ALERT: " + class_name.upper() + " DETECTED!"
            break

    # 4. Process Loitering Alert (if no weapon takes priority)
    if dwell_alert and not alert_triggered:
        alert_triggered = True
        alert_type = "loitering"
        alert_message = "ALERT: Loitering detected!"
        alert_conf = 1.0 # System-generated alert (100% confidence)

    return img, alert_triggered, alert_message, alert_type, alert_conf, person_count