"""
================================================================================
 Violence Detection Training  —  MobileNetV2 + BiLSTM  (trained on RWF-2000)
 Shreeya | KEC Minor Project | Real-Time Surveillance System
--------------------------------------------------------------------------------
 Built for Google Colab (GPU runtime: Runtime > Change runtime type > T4 GPU),
 but runs anywhere PyTorch + OpenCV are installed.

 WHAT IT DOES
   1. Downloads RWF-2000 (Kaggle mirror)
   2. Auto-detects the fight / non-fight folder layout (no hardcoded names)
   3. Samples 16 frames per clip, caches them (so re-runs are fast)
   4. Trains a MobileNetV2 (ImageNet backbone) + BiLSTM classifier
   5. Saves the best weights + prints a confusion matrix & report
      (good metrics to drop straight into your defense slides)

 OUTPUT:  violence_mobilenet_lstm.pt   <-- copy this to your local pipeline
================================================================================
"""
import os, glob, random, cv2, numpy as np, torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision.models import mobilenet_v2, MobileNet_V2_Weights
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

# ------------------------------- CONFIG -------------------------------------
SEQ_LEN   = 16          # frames sampled per clip
IMG_SIZE  = 112         # frame resolution (112 = fast + good enough)
BATCH     = 8
EPOCHS    = 15
LR        = 1e-4
FREEZE_BACKBONE = False  # False = fine-tune the whole network end-to-end (better accuracy)
CACHE_DIR = "cache"
OUT_PATH  = "violence_mobilenet_lstm.pt"
SEED      = 42
DEVICE    = "cuda" if torch.cuda.is_available() else "cpu"

random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)


# ============================================================================
# STEP 1 — DOWNLOAD DATASET  (run once)
# ============================================================================
# In Colab, easiest is kagglehub (no manual upload of kaggle.json needed if you
# log in when prompted). Uncomment to use:
#
#   !pip install -q kagglehub opencv-python-headless scikit-learn
#   import kagglehub
#   DATA_ROOT = kagglehub.dataset_download("magicearth25/video-violence-detection-dataset")
#   print("downloaded to:", DATA_ROOT)
#   # then peek at the layout once:  !ls -R {DATA_ROOT} | head -40
#
# Any mirror with fight / non-fight video folders works — discover_videos()
# below auto-detects the layout, so you don't have to rename anything.
# (Other slugs to try if needed: search Kaggle "RWF-2000".)
#
DATA_ROOT = os.environ.get("DATA_ROOT", "./RWF-2000")   # <-- set to your download path


# ============================================================================
# STEP 2 — DISCOVER VIDEOS + LABELS  (layout-agnostic)
# ============================================================================
def label_from_path(path):
    """Infer label from any folder name in the path. 0 = non-violent, 1 = violent."""
    parts = [p.lower() for p in path.replace("\\", "/").split("/")]
    for p in parts:
        # check NON-violent first (nonfight, non-violent, nonviolence, normal, ...)
        if ("non" in p and ("violen" in p or "fight" in p)) or p in ("normal", "nofight"):
            return 0
    for p in parts:
        if "fight" in p or "violen" in p or "violent" in p:
            return 1
    return None  # couldn't tell -> skipped

def split_from_path(path):
    p = path.lower()
    if "/train" in p or "\\train" in p: return "train"
    if "/val" in p or "/test" in p or "\\val" in p or "\\test" in p: return "val"
    return None

def discover_videos(root):
    exts = ("*.avi", "*.mp4", "*.mov", "*.mkv")
    files = []
    for e in exts:
        files += glob.glob(os.path.join(root, "**", e), recursive=True)
    items = []
    for f in files:
        lab = label_from_path(f)
        if lab is None:
            continue
        items.append((f, lab, split_from_path(f)))
    # If dataset had no train/val folders, make a stratified 80/20 split ourselves
    if all(s is None for _, _, s in items):
        random.shuffle(items)
        by_label = {0: [], 1: []}
        for f, l, _ in items:
            by_label[l].append(f)
        items = []
        for l, fs in by_label.items():
            cut = int(0.8 * len(fs))
            for f in fs[:cut]: items.append((f, l, "train"))
            for f in fs[cut:]: items.append((f, l, "val"))
    return items


# ============================================================================
# STEP 3 — FRAME SAMPLING + CACHING
# ============================================================================
def sample_frames(path, seq_len=SEQ_LEN, size=IMG_SIZE):
    """Uniformly sample seq_len frames from a video -> uint8 array (T, H, W, 3) RGB."""
    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:  # some codecs report 0 -> read all then subsample
        frames = []
        ok, fr = cap.read()
        while ok:
            frames.append(fr); ok, fr = cap.read()
        cap.release()
        if not frames:
            return None
        idxs = np.linspace(0, len(frames) - 1, seq_len).astype(int)
        chosen = [frames[i] for i in idxs]
    else:
        idxs = np.linspace(0, max(total - 1, 0), seq_len).astype(int)
        chosen = []
        for i in idxs:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
            ok, fr = cap.read()
            if not ok:
                fr = chosen[-1] if chosen else np.zeros((size, size, 3), np.uint8)
            chosen.append(fr)
        cap.release()
    out = []
    for fr in chosen:
        fr = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
        fr = cv2.resize(fr, (size, size))
        out.append(fr)
    return np.asarray(out, dtype=np.uint8)            # (T, H, W, 3)

def preprocess(items):
    """Decode every clip once and cache as .npy so epochs are I/O-cheap."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cached = []
    for k, (path, label, split) in enumerate(items):
        name = f"{split}_{label}_{k}.npy"
        dst = os.path.join(CACHE_DIR, name)
        if not os.path.exists(dst):
            arr = sample_frames(path)
            if arr is None or arr.shape[0] != SEQ_LEN:
                continue
            np.save(dst, arr)
        cached.append((dst, label, split))
        if (k + 1) % 100 == 0:
            print(f"  preprocessed {k+1}/{len(items)} clips")
    return cached


# ============================================================================
# STEP 4 — DATASET
# ============================================================================
class ClipDataset(Dataset):
    def __init__(self, items, train=False):
        self.items = items
        self.train = train
    def __len__(self):
        return len(self.items)
    def __getitem__(self, i):
        path, label, _ = self.items[i]
        arr = np.load(path).astype(np.float32) / 255.0      # (T,H,W,3)
        if self.train and random.random() < 0.5:             # cheap horizontal-flip aug
            arr = arr[:, :, ::-1, :].copy()
        arr = (arr - IMAGENET_MEAN) / IMAGENET_STD
        arr = np.transpose(arr, (0, 3, 1, 2))                # (T,3,H,W)
        return torch.from_numpy(arr), torch.tensor(label, dtype=torch.long)


# ============================================================================
# STEP 5 — MODEL  (verified forward/backward)
# ============================================================================
class ViolenceNet(nn.Module):
    def __init__(self, hidden=256, num_classes=2, freeze_backbone=True):
        super().__init__()
        bb = mobilenet_v2(weights=MobileNet_V2_Weights.IMAGENET1K_V1)
        self.features = bb.features
        self.pool = nn.AdaptiveAvgPool2d(1)
        if freeze_backbone:
            for p in self.features.parameters():
                p.requires_grad = False
        self.lstm = nn.LSTM(1280, hidden, batch_first=True, bidirectional=True)
        self.head = nn.Sequential(nn.Dropout(0.5), nn.Linear(hidden * 2, num_classes))
    def forward(self, x):                                     # (B,T,C,H,W)
        B, T, C, H, W = x.shape
        x = x.reshape(B * T, C, H, W)
        f = self.pool(self.features(x)).flatten(1)            # (B*T,1280)
        f = f.view(B, T, -1)
        out, _ = self.lstm(f)
        return self.head(out[:, -1, :])


# ============================================================================
# STEP 6 — TRAIN
# ============================================================================
def run():
    print("Device:", DEVICE)
    roots = [r.strip() for r in DATA_ROOT.split(";") if r.strip()]
    items = []
    for r in roots:
        found = discover_videos(r)
        print(f"  {len(found)} clips from {r}")
        items += found
    assert items, f"No labelled videos found under {DATA_ROOT}. Check the path(s)."
    n1 = sum(l for _, l, _ in items)
    print(f"Found {len(items)} clips  |  violent={n1}  non-violent={len(items)-n1}")

    items = preprocess(items)
    train_items = [x for x in items if x[2] == "train"]
    val_items   = [x for x in items if x[2] == "val"]
    print(f"train={len(train_items)}  val={len(val_items)}")

    tl = DataLoader(ClipDataset(train_items, train=True),  batch_size=BATCH, shuffle=True,  num_workers=2)
    vl = DataLoader(ClipDataset(val_items),                batch_size=BATCH, shuffle=False, num_workers=2)

    model = ViolenceNet(freeze_backbone=FREEZE_BACKBONE).to(DEVICE)
    opt = torch.optim.Adam([p for p in model.parameters() if p.requires_grad], lr=LR)
    crit = nn.CrossEntropyLoss()

    best_acc = 0.0
    for ep in range(1, EPOCHS + 1):
        model.train(); tot = 0.0
        for x, y in tl:
            x, y = x.to(DEVICE), y.to(DEVICE)
            opt.zero_grad()
            loss = crit(model(x), y); loss.backward(); opt.step()
            tot += loss.item()
        # validate
        model.eval(); preds, gts = [], []
        with torch.no_grad():
            for x, y in vl:
                p = model(x.to(DEVICE)).argmax(1).cpu().numpy()
                preds += p.tolist(); gts += y.tolist()
        acc = accuracy_score(gts, preds) if gts else 0.0
        print(f"epoch {ep:02d}  loss {tot/max(len(tl),1):.4f}  val_acc {acc:.4f}")
        if acc >= best_acc:
            best_acc = acc
            torch.save({"state_dict": model.state_dict(),
                        "seq_len": SEQ_LEN, "img_size": IMG_SIZE}, OUT_PATH)

    print(f"\nBEST val accuracy: {best_acc:.4f}  ->  saved {OUT_PATH}")
    if val_items:
        print("\nConfusion matrix [rows=true, cols=pred]  (0=non-violent, 1=violent):")
        print(confusion_matrix(gts, preds))
        print("\n" + classification_report(gts, preds, target_names=["non-violent", "violent"]))


if __name__ == "__main__":
    run()