import cv2
webcam=cv2.VideoCapture(0)

while True:
    ret,img=webcam.read()
    if not ret:
        break
    img=cv2.flip(img,1)
    cv2.imshow("Surveillance System",img)
    key=cv2.waitKey(1)
    if key==27:
        break
webcam.release()
cv2.destroyAllWindows()