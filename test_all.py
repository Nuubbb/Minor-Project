import cv2, glob
from ultralytics import YOLO
from violence_detector import ViolenceDetector
from context_engine import ThreatAssessor, TIER_NAME

v = ViolenceDetector('violence_mobilenet_lstm.pt')
person_model = YOLO('yolov8n.pt')          # count people -> lets the engine tell crowd from fight

def run(path):
    a = ThreatAssessor()
    v.buffer.clear(); v.prob_hist.clear(); v._count = 0
    cap = cv2.VideoCapture(path)
    maxprob, max_tier, max_people, person_count, fno = 0.0, 0, 0, 0, 0
    while True:
        ok, f = cap.read()
        if not ok: break
        f = cv2.resize(f, (640, 480))
        _, p = v.update(f)
        maxprob = max(maxprob, p)
        fno += 1
        if fno % 5 == 0:                    # detect people every 5th frame
            pr = person_model(f, classes=[0], conf=0.5, verbose=False)[0]
            person_count = len(pr.boxes)
        max_people = max(max_people, person_count)
        tier, _, _, _ = a.assess(violence_prob=p, person_count=person_count)
        max_tier = max(max_tier, tier)
    cap.release()
    return maxprob, max_people, TIER_NAME[max_tier]

print(f"{'video':22s} {'raw':>6s} {'people':>7s}  system_tier")
print("-" * 52)
for f in sorted(glob.glob('*.mp4')):
    mp, ppl, tier = run(f)
    print(f"{f:22s} {mp:6.2f} {ppl:7d}  {tier}")