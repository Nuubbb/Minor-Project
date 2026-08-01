import os, shutil, sys
PROJECT = os.path.dirname(os.path.abspath(__file__))
DELETE_FILES = ["fix_all.py","fix_all_templates.py","fix_all_v2.py","fix_close.py","fix_dash.py","fix_dash2.py","fix_dashboard","fix_every","fix_everything.py","fix_line.py","fix_link.py","fix_logo.py","fix_logo2.py","detection_backup.py","detection_new.py","test_all.py","test_fresh.py","test_system.py","test_video.py","demo.py","check_demo.py","normal.py","prof.py","make_weapon_clip.py","yolov8m.pt","yolov8s.pt","text.txt","middefense_a4267c93-96d6-4915-912a-d4c0878fa8c3.docx"]
DELETE_DIRS = ["extra_normal","__pycache__"]
dry = "--go" not in sys.argv
if dry: print("=== DRY RUN ===\n")
total = 0
for name in DELETE_FILES:
    path = os.path.join(PROJECT, name)
    if os.path.exists(path):
        size = os.path.getsize(path)
        total += size
        print(f"  DELETE {name} ({size//1024} KB)")
        if not dry: os.remove(path)
for name in DELETE_DIRS:
    path = os.path.join(PROJECT, name)
    if os.path.isdir(path):
        size = sum(os.path.getsize(os.path.join(dp,f)) for dp,_,fns in os.walk(path) for f in fns)
        total += size
        print(f"  DELETE {name}/ ({size//1024//1024} MB)")
        if not dry: shutil.rmtree(path)
print(f"\nTotal: {total//1024//1024} MB {'would be' if dry else ''} freed.")
if dry: print("\nRun with --go to delete:\n  python cleanup.py --go")
