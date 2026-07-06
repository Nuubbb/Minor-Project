import cv2
from violence_detector import ViolenceDetector
from context_engine import ThreatAssessor, TIER_NAME

v = ViolenceDetector('violence_mobilenet_lstm.pt')

def run(path):
    a = ThreatAssessor()                 # fresh engine per clip
    v.buffer.clear(); v.prob_hist.clear(); v._count = 0
    cap = cv2.VideoCapture(path)
    tiers, maxprob = [], 0.0
    while True:
        ok, frame = cap.read()
        if not ok: break
        _, prob = v.update(frame)
        maxprob = max(maxprob, prob)
        tier, atype, msg, conf = a.assess(violence_prob=prob)
        tiers.append(tier)
    cap.release()
    top = max(tiers) if tiers else 0
    return maxprob, TIER_NAME[top]

for f in ["test_fight1.mp4", "test_fight2.mp4", "test_normal1.mp4", "test_normal2.mp4"]:
    prob, tier = run(f)
    print(f"{f:18s} raw_prob={prob:.3f}  ->  SYSTEM TIER: {tier}")