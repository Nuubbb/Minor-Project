import cv2
from ultralytics import YOLO
webcam=cv2.VideoCapture(0)
<<<<<<< HEAD
model = YOLO("yolov8n.pt")
>>>>>>> 9ae77fabb9210f4ea6cc51d53b4f7c8d645a4c34
while True:
    ret,img=webcam.read()
    if not ret:
        break
    img=cv2.flip(img,1)
    results=model(img, verbose=False)
    img=results[0].plot()
    cv2.imshow("Surveillance System",img)
    key=cv2.waitKey(1)
    if key==27:
        break
webcam.release()
cv2.destroyAllWindows()