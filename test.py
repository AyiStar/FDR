from multiprocessing import Process, Queue
from utils import *
import cv2
import time
from datetime import datetime
import numpy as np
import os
import face_recognition



def video_capture(q_image, video):

    camera = cv2.VideoCapture(video)

    while True:

        read, image = camera.read()
        cv2.imshow('video', image)

        if q_image.empty():
            q_image.put(image)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    camera.release()
    cv2.destroyAllWindows()


def recognize_face(q_image, data_path, tolerance, test=False):

    known_faces = load_faces(data_path)
    face_locations = []
    face_encodings = []
    face_names = []

    while True:
        image = q_image.get(True)
        #print('get a image')
        rgb_image = image[:, :, ::-1]
        face_locations = face_recognition.face_locations(rgb_image, number_of_times_to_upsample=0, model="cnn")
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations, num_jitters=1)
        face_matches = []

        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            distances = get_face_distances(known_faces, face_encoding)
            match = match_face(distances, tolerance)
            face_matches.append(match)

        for (top, right, bottom, left), match in zip(face_locations, face_matches):

            # Draw a box around the face
            cv2.rectangle(image, (left, top), (right, bottom), (0, 0, 255), 1)

            # Draw a label with a name below the face
            #cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(image, match[0]+':'+'%.2f'%(match[1]), (left, bottom), font, 1.0, (0, 0, 255), 1)

        if len(face_matches) > 0:
            print('detect a person')

        if test == True:
            if not os.path.exists('./test_result/'):
                os.mkdir('./test_result')
            cv2.imwrite('./test_result/' + datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S-') + '.jpg', image)



def main(video=0):
    q = Queue()
    p_video_capture = Process(target=video_capture, args=(q, video))
    p_face_recognition = Process(target=recognize_face, args=(q, './data/', 0.4, True))

    p_face_recognition.start()
    p_video_capture.start()

    p_video_capture.join()
    p_face_recognition.terminate()



if __name__ == '__main__':
    main(video=0)