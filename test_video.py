import cv2
from ultralytics import YOLO

general_model = YOLO("yolov8s.pt")
weapon_model = YOLO("best.pt")

def process_frame(img):

    img = cv2.flip(img, 1)
    
    img = general_model(img, classes=[0], conf=0.5, verbose=False)[0].plot()
    
    weapon_results = weapon_model(img, classes=[0], conf=0.5, verbose=False)[0]
    img = weapon_results.plot()
    
    alert_triggered = False
    alert_message = ""
    
    if len(weapon_results.boxes) > 0:
        alert_triggered = True
        alert_message = "CRITICAL: Threat Weapon Spotted!"
        
    return img, alert_triggered, alert_message
