import cv2

def frames(path, seconds=None):
    cap = cv2.VideoCapture(path); fps = cap.get(5) or 25
    out = []; lim = int(fps*seconds) if seconds else 10**9
    while len(out) < lim:
        ok, f = cap.read()
        if not ok: break
        out.append(cv2.resize(f, (640, 480)))
    cap.release(); return out, fps

normal, fps  = frames("test_normal2.mp4", 10)   # 20s calm (longer)
violence, _  = frames("clip_violence.mp4", 10)  # 20s fight (longer)

allf = normal + violence
o = cv2.VideoWriter("demo.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps, (640, 480))
for f in allf: o.write(f)
o.release()
print(f"demo.mp4: {len(normal)/fps:.0f}s normal -> {len(violence)/fps:.0f}s violence")