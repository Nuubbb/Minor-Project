import cv2
import winsound
from ultralytics import YOLO

# Load models globally so they don't reload on every frame
general_model = YOLO("yolov8s.pt")
weapon_model = YOLO("best.pt")

# Must be lowercase to match .lower() check
THREAT_CLASSES = ["guns", "knife", "violence", "pistol"]

def process_frame(img):
    img = cv2.flip(img, 1)
    
    # Process General Objects (Persons)
    img = general_model(img, classes=[0], conf=0.5, verbose=False)[0].plot()
    
    # Process Weapons
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
            alert_message = f"ALERT: {class_name.upper()} DETECTED!"
            break
        
    return img, alert_triggered, alert_message, alert_type, alert_conf

if __name__ == "__main__":
    from database import init_db, log_alert
    init_db()
    
    webcam = cv2.VideoCapture(0)
    while True:
        ret, img = webcam.read()
        if not ret: break

        img, alert_triggered, alert_message, alert_type, alert_conf = process_frame(img)

        if alert_triggered:
            cv2.putText(img, alert_message, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            winsound.Beep(1000, 200)
            log_alert(alert_type, alert_conf)

        cv2.imshow("Surveillance System", img)
        if cv2.waitKey(1) == 27: break # ESC

    webcam.release()
    cv2.destroyAllWindows()