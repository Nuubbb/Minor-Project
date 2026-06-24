import cv2
from ultralytics import YOLO
webcam=cv2.VideoCapture(0)
model= YOLO("yolov8s.pt")
while True:
    ret,img=webcam.read()
    if not ret:
        break
    img=cv2.flip(img,1)
    results=model(img, classes=[0], conf=0.5, verbose=False)
    img=results[0].plot()
    cv2.imshow("Surveillance System",img)
    key=cv2.waitKey(1)
    if key==27:
        break
webcam.release()
cv2.destroyAllWindows()