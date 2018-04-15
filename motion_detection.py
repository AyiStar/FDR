# coding:utf8
import cv2
from datetime import datetime
import numpy as np


def detect_video(video):
    camera = cv2.VideoCapture(video)
    history = 20    # 训练帧数

    bs = cv2.createBackgroundSubtractorKNN(detectShadows=True)# 背景减除器，设置阴影检测
    #bs = cv2.bgsegm.createBackgroundSubtractorGMG()  
    bs.setHistory(history)

    frames = 0


    while True:
        res, frame = camera.read()

        if not res:
            break

        fg_mask = bs.apply(frame)   # 获取 foreground mask

        if frames < history:
            frames += 1
            continue

        # 对原始帧进行膨胀去噪
        th = cv2.threshold(fg_mask.copy(), 244, 255, cv2.THRESH_BINARY)[1]
        th = cv2.erode(th, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), iterations=2)
        dilated = cv2.dilate(th, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (8, 3)), iterations=2)
        # 获取所有检测框
        image, contours, hier = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            if area < 3000:
                continue
            rect = cv2.minAreaRect(c)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            cv2.drawContours(frame,[box],0,(0,0,255),2)

            crop = crop_minAreaRect(frame, rect)
            #crop = cv2.resize(crop,(64,64))
            #res = cv2.matchTemplate(crop,template,cv2.TM_CCOEFF_NORMED)
            cv2.imwrite(datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S-') + str(res) + '.jpg', crop)


        cv2.imshow("detection", frame)
        cv2.imshow("back", dilated)
        if cv2.waitKey(110) & 0xff == 27:
            break
    camera.release()



def crop_minAreaRect(img, rect):

    # rotate img
    angle = rect[2]
    rows,cols = img.shape[0], img.shape[1]
    M = cv2.getRotationMatrix2D((cols/2,rows/2),angle,1)
    img_rot = cv2.warpAffine(img,M,(cols,rows))

    # rotate bounding box
    rect0 = (rect[0], rect[1], 0.0)
    box = cv2.boxPoints(rect)
    pts = np.int0(cv2.transform(np.array([box]), M))[0]    
    pts[pts < 0] = 0

    # crop
    img_crop = img_rot[pts[1][1]:pts[0][1], 
                       pts[1][0]:pts[2][0]]

    return img_crop

def main():
    detect_video(0)

if __name__ == '__main__':
    main()