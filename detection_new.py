import threading, queue

_latest_frame = {}  # source -> latest annotated JPEG bytes

def _detection_worker(source, operator_email, operator_username):
    """Background thread: reads frames, runs ALL models, stores latest result."""
    if source == 'cctv':
        cctv_url = "rtsp://admin:YourPassword@192.168.1.150:554/Streaming/Channels/101"
        camera = cv2.VideoCapture(cctv_url)
    elif source:
        camera = cv2.VideoCapture(source)
    else:
        camera = cv2.VideoCapture(0)

    violence_detector.buffer.clear()
    violence_detector.prob_hist.clear()
    violence_detector._count = 0

    frame_no = 0
    person_boxes, weapon_boxes = [], []
    person_count, track_ids, weapons = 0, [], []
    DETECT_EVERY = 15
    WEAPON_EVERY = 10
    key = id(threading.current_thread())
    _latest_frame[key] = None
    _latest_frame[f"{key}_stop"] = False

    try:
        while not _latest_frame.get(f"{key}_stop"):
            success, frame = camera.read()
            if not success:
                if source and source != 'cctv':
                    camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                time.sleep(0.1)
                continue

            frame = cv2.resize(frame, (640, 480))
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
                    new_id = log_alert(alert_type, conf, operator_username)
                    _save_alert_screenshot(new_id, img)
                    if tier == ALARM:
                        trigger_audio_alarm()
                    if operator_email and send_email_alert and (time.time() - _last_email["t"] > 60):
                        _last_email["t"] = time.time()
                        threading.Thread(target=send_email_alert,
                                         args=(operator_email, message, new_id),
                                         daemon=True).start()

            cv2.putText(img, f"Violence: {violence_prob:.2f}", (20, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 0, 255) if is_violent else (0, 255, 0), 2)

            ret, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ret:
                _latest_frame[key] = buffer.tobytes()
    finally:
        camera.release()


def generate_frames(operator_email=None, source=None, operator_username="system"):
    """Yield latest frame from the background detection thread — never blocks."""
    worker = threading.Thread(target=_detection_worker,
                              args=(source, operator_email, operator_username),
                              daemon=True)
    key = id(worker)
    worker.start()

    try:
        while worker.is_alive():
            jpg = _latest_frame.get(key)
            if jpg:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')
            time.sleep(0.03)  # ~30 fps cap on yield rate
    finally:
        _latest_frame[f"{key}_stop"] = True
        worker.join(timeout=3)
