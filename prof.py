import cv2, time
from ultralytics import YOLO
from violence_detector import ViolenceDetector
v = ViolenceDetector('violence_mobilenet_lstm.pt')
p = YOLO('yolov8n.pt'); w = YOLO('best.pt')
c = cv2.VideoCapture('demo.mp4')
tv=ty=0.0; n=0
while n<50:
    ok,f=c.read()
    if not ok: break
    f=cv2.resize(f,(640,480))
    s=time.time(); v.update(f); tv+=time.time()-s
    s=time.time(); p.track(f,classes=[0],persist=True,verbose=False); w(f,verbose=False); ty+=time.time()-s
    n+=1
print('violence:', round(tv/n*1000), 'ms/frame')
print('yolo    :', round(ty/n*1000), 'ms/frame')
print('MODELS-ONLY FPS:', round(n/(tv+ty),1))
