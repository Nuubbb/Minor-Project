import cv2
img = cv2.imread('knife.jpg')
if img is None:
    print("knife.jpg not found in this folder!")
else:
    img = cv2.resize(img, (640, 480))
    fps = 25
    out = cv2.VideoWriter('weapon_clip.mp4', cv2.VideoWriter_fourcc(*'mp4v'), fps, (640, 480))
    for _ in range(fps * 8):        # 8-second clip of the knife
        out.write(img)
    out.release()
    print("weapon_clip.mp4 created (8s of knife.jpg)")