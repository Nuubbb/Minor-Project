"""
violence_detector.py
--------------------------------------------------------------------------------
Live violence detection for the Real-Time Surveillance System.

Loads the MobileNetV2 + BiLSTM model trained on Colab and watches a rolling
window of camera frames, returning a smoothed violent / non-violent decision.
Runs alongside the YOLO detectors in test_video.py.

USAGE (in test_video.py):
    from violence_detector import ViolenceDetector
    vdet = ViolenceDetector("violence_mobilenet_lstm.pt")   # once, before the loop
    ...
    is_violent, prob = vdet.update(frame)                    # once per frame, in the loop
"""
import cv2, numpy as np, torch
import torch.nn as nn
from collections import deque
from torchvision.models import mobilenet_v2

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class ViolenceNet(nn.Module):
    """Same architecture as training — weights are loaded from your trained .pt."""
    def __init__(self, hidden=256, num_classes=2):
        super().__init__()
        bb = mobilenet_v2(weights=None)          # weights come from violence_mobilenet_lstm.pt
        self.features = bb.features
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.lstm = nn.LSTM(1280, hidden, batch_first=True, bidirectional=True)
        self.head = nn.Sequential(nn.Dropout(0.5), nn.Linear(hidden * 2, num_classes))

    def forward(self, x):                         # x: (B, T, C, H, W)
        B, T, C, H, W = x.shape
        x = x.reshape(B * T, C, H, W)
        f = self.pool(self.features(x)).flatten(1)
        f = f.view(B, T, -1)
        out, _ = self.lstm(f)
        return self.head(out[:, -1, :])


class ViolenceDetector:
    """
    Call update(frame) once per camera frame.
    Returns (is_violent: bool, prob: float)  -- prob is the smoothed violence score 0..1.

    Tuning knobs:
      sample_every : push every Nth frame into the buffer (spreads the 16 frames
                     over ~2-3 seconds so the motion window matches training).
      threshold    : how confident before we call it violence (raise to reduce
                     false alarms, lower to catch more).
      smooth       : average the last N predictions to stop the label flickering.
    """
    def __init__(self, model_path="violence_mobilenet_lstm.pt", device=None,
                 seq_len=16, img_size=112, sample_every=5, threshold=0.75, smooth=5):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.seq_len = seq_len
        self.img_size = img_size
        self.sample_every = sample_every
        self.threshold = threshold

        self.model = ViolenceNet().to(self.device)
        ckpt = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.eval()

        self.buffer = deque(maxlen=seq_len)
        self.prob_hist = deque(maxlen=smooth)
        self._count = 0
        self.last_prob = 0.0
        self.is_violent = False
        print(f"[ViolenceDetector] loaded '{model_path}' on {self.device}")

    def _prep(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, (self.img_size, self.img_size)).astype(np.float32) / 255.0
        rgb = (rgb - IMAGENET_MEAN) / IMAGENET_STD
        return np.transpose(rgb, (2, 0, 1))       # (3, H, W)

    def update(self, frame_bgr):
        self._count += 1
        if self._count % self.sample_every == 0:
            self.buffer.append(self._prep(frame_bgr))
            if len(self.buffer) == self.seq_len:
                clip = np.stack(self.buffer)                          # (T,3,H,W)
                x = torch.from_numpy(clip).unsqueeze(0).to(self.device)  # (1,T,3,H,W)
                with torch.no_grad():
                    prob = torch.softmax(self.model(x), dim=1)[0, 1].item()
                self.prob_hist.append(prob)
                self.last_prob = sum(self.prob_hist) / len(self.prob_hist)
                self.is_violent = self.last_prob >= self.threshold
        return self.is_violent, self.last_prob