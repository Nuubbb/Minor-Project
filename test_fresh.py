import subprocess, cv2, os
from violence_detector import ViolenceDetector

# --- download fresh test videos from YouTube (model has never seen these) ---
downloads = [
    ("test_fight1.mp4",  "ytsearch1:real street fight cctv footage"),
    ("test_fight2.mp4",  "ytsearch1:security camera fight"),
    ("test_normal1.mp4", "ytsearch1:people walking street cctv"),
    ("test_normal2.mp4", "ytsearch1:shopping mall cctv normal day"),
]
for out, query in downloads:
    if not os.path.exists(out):
        print("downloading:", query)
        subprocess.run(["yt-dlp", "-f", "mp4", "-o", out, query])

# --- score each one ---
v = ViolenceDetector('violence_mobilenet_lstm.pt')

def score(path):
    cap = cv2.VideoCapture(path)
    v.buffer.clear(); v.prob_hist.clear(); v._count = 0
    probs = []
    while True:
        ok, frame = cap.read()
        if not ok: break
        probs.append(v.update(frame)[1])
    cap.release()
    return max(probs) if probs else 0.0

print("\n=== RESULTS on FRESH videos (never seen) ===")
for out, _ in downloads:
    if os.path.exists(out):
        tag = "FIGHT " if "fight" in out else "NORMAL"
        print(f"  [{tag}] max violence prob: {score(out):.3f}   ({out})")