import cv2
from violence_detector import ViolenceDetector

v = ViolenceDetector('violence_mobilenet_lstm.pt')
cap = cv2.VideoCapture('demo.mp4')
fps = cap.get(cv2.CAP_PROP_FPS) or 25
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"demo.mp4: {total} frames, {total/fps:.0f} seconds\n")

probs = []
while True:
    ok, f = cap.read()
    if not ok: break
    probs.append(v.update(f)[1])
cap.release()

# print the score at each second so you see WHERE it spikes
print("second : score")
for i in range(0, len(probs), int(fps)):
    sec = i // int(fps)
    print(f"  {sec:3d}s  : {probs[i]:.2f}")