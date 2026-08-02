import cv2
import threading
import time
import platform
import os
from datetime import datetime
from ultralytics import YOLO

from database import log_alert, get_active_event, get_restricted_zones, get_settings
from violence_detector import ViolenceDetector          # YOUR temporal violence model
from context_engine import ThreatAssessor, IGNORE, LOG, NOTIFY, ALARM   # YOUR context engine
from config import SCREENSHOT_DIR
try:
    from email_alert import send_email_alert          # emails the logged-in operator
except Exception:
    send_email_alert = None

# ----------------- DETECTION SETUP (loaded once) -----------------
general_model = YOLO("yolov8n.pt")                                    # person detection (nano = faster)
weapon_model = YOLO("best.pt")                              # gun/knife detection
violence_detector = ViolenceDetector("violence_mobilenet_lstm.pt")   # temporal violence model
assessor = ThreatAssessor()
_settings_cache = {"checked": 0.0}

def _reload_settings():
    """Reload admin settings into the assessor every 30 seconds."""
    t = time.time()
    if t - _settings_cache["checked"] > 30:
        try:
            s = get_settings()
            assessor.violence_threshold = float(s["violence_threshold"])
            assessor.violence_streak_needed = int(s["violence_streak"])
            assessor.weapon_conf = float(s["weapon_conf"])
            assessor.closing_hour = int(s["closing_hour"])
            assessor.dwell_seconds = int(s["dwell_seconds"])
            assessor.log_cooldown = int(s["log_cooldown"])
            assessor.notify_cooldown = int(s["notify_cooldown"])
        except Exception as e:
            print("[settings] reload skip:", e)
        _settings_cache["checked"] = t                                         # context-aware decision engine

WEAPON_KEYWORDS = ("gun", "knife", "knive", "pistol", "rifle", "handgun", "shotgun", "weapon", "blade")
ACTION_COOLDOWN = 5.0
last_action = {}
_last_email = {"t": 0.0}   # throttle emails: at most one per minute
TIER_COLOR = {LOG: (0, 255, 255), NOTIFY: (0, 165, 255), ALARM: (0, 0, 255)}


def trigger_audio_alarm():
    """Cross-platform function to play an alarm sound."""
    try:
        current_os = platform.system()
        if current_os == "Windows":
            import winsound
            winsound.Beep(1000, 200)
        elif current_os == "Darwin": # Mac OS
            # The '&' runs it in the background so it doesn't freeze the video feed
            os.system('afplay /System/Library/Sounds/Glass.aiff &')
        else: # Linux or other
            print('\a') # Triggers terminal bell
    except Exception as e:
        print(f"[audio] skip: {e}")


def _save_alert_screenshot(alert_id, img):
    """Persist the annotated frame for a just-logged alert (message-packets prototype)."""
    try:
        cv2.imwrite(str(SCREENSHOT_DIR / f"alert_{alert_id}.jpg"), img)
    except Exception as e:
        print("[screenshot] skip:", e)


def _should_act(alert_type):
    """Anti-spam: only log/beep once per ACTION_COOLDOWN seconds per alert type."""
    now = time.time()
    if now - last_action.get(alert_type, 0) >= ACTION_COOLDOWN:
        last_action[alert_type] = now
        return True
    return False


def _detect_persons(frame):
    """Fast person detection + tracking (nano model). Runs often."""
    boxes, count, ids = [], 0, []
    try:
        pr = general_model.track(frame, classes=[0], conf=0.5, persist=True, verbose=False, imgsz=320)[0]
        count = len(pr.boxes)
        ids = pr.boxes.id.int().tolist() if pr.boxes.id is not None else []
        id_list = ids if ids else [None] * count
        for i, xyxy in enumerate(pr.boxes.xyxy.cpu().numpy().astype(int)):
            x1, y1, x2, y2 = xyxy
            pid = id_list[i] if i < len(id_list) else None
            label = f"id:{pid} person" if pid is not None else "person"
            boxes.append((x1, y1, x2, y2, label, (0, 255, 0)))
    except Exception as e:
        print("[person det] skip:", e)
    return boxes, count, ids


def _detect_weapons(frame):
    """Weapon detection (heavier model). Runs RARELY -- weapons are rare + mostly static."""
    boxes, weapons = [], []
    try:
        wr = weapon_model(frame, conf=0.5, verbose=False, imgsz=320)[0]
        for xyxy, cls, conf in zip(wr.boxes.xyxy.cpu().numpy().astype(int),
                                   wr.boxes.cls.cpu().numpy().astype(int),
                                   wr.boxes.conf.cpu().numpy()):
            name = weapon_model.names[int(cls)]
            if any(k in name.lower() for k in WEAPON_KEYWORDS):   # only real weapons
                x1, y1, x2, y2 = xyxy
                boxes.append((x1, y1, x2, y2, f"{name} {conf:.2f}", (0, 0, 255)))
                weapons.append((name.lower(), float(conf)))
    except Exception as e:
        print("[weapon det] skip:", e)
    return boxes, weapons


def _draw_boxes(img, boxes):
    """Draw cached boxes onto a frame (used on skipped frames)."""
    for (x1, y1, x2, y2, label, color) in boxes:
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, label, (x1, max(15, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    return img


_event_cache = {"checked": 0.0, "active": None}
def current_event():
    """Return (name, expected_crowd) if an event is active now, else None. Cached 30s."""
    t = time.time()
    if t - _event_cache["checked"] > 30:
        _event_cache["active"] = get_active_event()
        _event_cache["checked"] = t
    return _event_cache["active"]


def generate_frames(operator_email=None, source=None, operator_username="system"):
    """Live feed: reads, detects, and yields frames. Stops AUTOMATICALLY when the
    browser disconnects (no background thread -> no alarms after logout)."""

    # Optional: If you are using a CCTV camera, uncomment the next line and replace '0' below
    # cctv_url = "rtsp://admin:SecurePass2026@192.168.1.150:554/cam/realmonitor?channel=1&subtype=1"
    cctv_url = "rtsp://admin:YourPassword@192.168.1.150:554/Streaming/Channels/101"

    # Safest selection logic:
    if source == 'cctv':
        camera = cv2.VideoCapture(cctv_url)  # 1. Use CCTV if specifically requested
    elif source:
        camera = cv2.VideoCapture(source)    # 2. Use demo.mp4 if requested
    else:
        camera = cv2.VideoCapture(0)

    violence_detector.buffer.clear(); violence_detector.prob_hist.clear(); violence_detector._count = 0
    fail_count = 0
    DETECT_EVERY = 30  # Optimized person detection frequency
    WEAPON_EVERY = 10  # Optimized weapon detection frequency
    frame_no = 0
    person_boxes, weapon_boxes = [], []
    person_count, track_ids, weapons = 0, [], []

    try:
        while True:
            success, frame = camera.read()
            if not success:
                if source and source != 'cctv':  # VIDEO FILE -> loop back to the start
                    camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    fail_count += 1
                    if fail_count > 5:
                        break
                    continue
                # Webcam or CCTV: network/device drops are expected -- retry
                # indefinitely rather than giving up after a handful of
                # failures (an RTSP stream can drop out for a few seconds
                # and recover on its own).
                time.sleep(0.1)
                continue

            fail_count = 0
            frame = cv2.resize(frame, (480, 360))

            _reload_settings()
            is_violent, violence_prob = violence_detector.update(frame)

            frame_no += 1
            if frame_no % DETECT_EVERY == 0:
                person_boxes, person_count, track_ids = _detect_persons(frame)
            if frame_no % WEAPON_EVERY == 0:
                weapon_boxes, weapons = _detect_weapons(frame)

            img = _draw_boxes(frame.copy(), person_boxes + weapon_boxes)

            ev = current_event()
            tier, alert_type, message, conf = assessor.assess(
                violence_prob=violence_prob, weapons=weapons,
                person_count=person_count, track_ids=track_ids,
                current_hour=datetime.now().hour,
                event_active=ev is not None,
                event_expected_crowd=(ev[1] if ev else 0)
            )

            if tier != IGNORE:
                cv2.putText(img, message, (20, 50), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, TIER_COLOR.get(tier, (0, 0, 255)), 2)

                if _should_act(alert_type):
                    # Pass the logged-in operator's username to the database logger
                    new_id = log_alert(alert_type, conf, operator_username)
                    _save_alert_screenshot(new_id, img)

                    if tier == ALARM:
                        trigger_audio_alarm()

                    if operator_email and send_email_alert and (time.time() - _last_email["t"] > 60):
                        _last_email["t"] = time.time()  # max ONE email per minute
                        threading.Thread(target=send_email_alert,
                                         args=(operator_email, message, new_id),
                                         daemon=True).start()  # non-blocking

            # ---- HUD overlay ----
            h, w = img.shape[:2]
            ts = datetime.now().strftime("%H:%M:%S")
            cv2.putText(img, ts, (w - 100, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)
            cv2.putText(img, f"Violence: {violence_prob:.2f}", (20, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 0, 255) if is_violent else (0, 255, 0), 2)
            crowd_limit = 3
            count_color = (0, 0, 255) if person_count >= crowd_limit else (0, 255, 0)
            count_label = f"Persons: {person_count}"
            if person_count >= crowd_limit:
                count_label += "  CROWD"
            cv2.putText(img, count_label, (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, count_color, 2)
            now_ts = time.time()
            after_hours = datetime.now().hour >= assessor.closing_hour
            if after_hours and track_ids:
                for pid in track_ids:
                    start = assessor._track_start.get(pid)
                    if start and (now_ts - start) > assessor.dwell_seconds * 0.5:
                        dwell = int(now_ts - start)
                        loiter_color = (0, 0, 255) if dwell >= assessor.dwell_seconds else (0, 165, 255)
                        loiter_label = f"Loiter id:{pid} {dwell}s"
                        if dwell >= assessor.dwell_seconds:
                            loiter_label += " ALERT"
                        cv2.putText(img, loiter_label, (20, 150),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, loiter_color, 2)
                        break

            ret, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 50])
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    finally:
        camera.release()  # always release when the browser disconnects
