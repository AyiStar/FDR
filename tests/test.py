# coding: utf-8

from multiprocessing import Process, Queue
from faceutils import *
import cv2
import time
from datetime import datetime
import numpy as np
import os
import face_recognition
import MySQLdb
from weibo_utils import WeiboClient
from stat_utils import WeiboStat

def test(tolerance=0.4, video=0):
    '''
    @ parameter:
        #data_path: the directory where .dat files are
        tolerance: maximum distance to be recognized
        video: the number of video
    @ return value:
        None
    '''

    db_conn = MySQLdb.connect(db='FDR')
    known_faces = load_faces(db_conn)
    print(len(known_faces))

    video_capture = cv2.VideoCapture(video)


    # Initialize some variables
    face_locations = []
    face_encodings = []
    face_names = []
    process_this_frame = True

    while True:
        # Grab a single frame of video
        ret, frame = video_capture.read()

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_frame = frame[:, :, ::-1]

        # Only process every other frame of video to save time
        if process_this_frame:
            # Find all the faces and face encodings in the current frame of video
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            face_matches = []

            for face_encoding in face_encodings:
                # See if the face is a match for the known face(s)
                distances = get_face_distances(known_faces, face_encoding)
                match = match_face(distances, tolerance)
                face_matches.append(match)

        process_this_frame = not process_this_frame


        # Display the results
        for (top, right, bottom, left), match in zip(face_locations, face_matches):

            # Draw a box around the face
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 1)

            # Draw a label with a name below the face
            #cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, match[0]+':'+'%.2f'%(match[1]), (left, bottom), font, 1.0, (0, 0, 255), 1)

        # Display the resulting image
        cv2.imshow('Video', frame)

        # Hit 'q' on the keyboard to quit!
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    #Release handle to the webcam
    video_capture.release()
    cv2.destroyAllWindows()

def main():
    cookie = {
            "Cookie": '_T_WM=897a5cddc91313eb40a4d44efe82c041; SUB=_2A252B5M7DeRhGeRG6FsQ9SzPwjyIHXVVCz1zrDV6PUJbkdANLU7ykW1NUjSIDKEeHdnG6F3Owi33LiKgDU1zYT28; SUHB=0z1R34lEPLCsQs; SCF=Aurel-CXoF707U2FuZTejk20gZCmrDS1Ehi56ro6GtPtrzKDJCFJ88uDcB_NcEOZDfXZ7KHA6niumfXCilyuTXs.; SSOLoginState=1526981485; M_WEIBOCN_PARAMS=uicode%3D20000174%26featurecode%3D20000320%26fid%3Dhotword; MLOGIN=1',
            }
    wb = WeiboClient(cookie=cookie, db_user='ayistar', db_passwd='', db_name='FDR')
    uid = wb.get_uid('慕寒mio')
    # print(uid)
    # wb.get_weibo([uid])
    ws = WeiboStat('ayistar', '', 'FDR')
    ws.get_text(uid)
    ws.word_stat()
    ws.generate_word_cloud()


if __name__ == '__main__':
    main()