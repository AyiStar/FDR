# coding: utf-8

import face_recognition
import cv2
import numpy as np
import copy
import csv
import os
import time
import urllib.request
import json
import pickle
import MySQLdb
from datetime import datetime



def detect_face(image, pic_path):


    # Initialize some variables
    face_locations = []

    # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
    rgb_image = image[:, :, ::-1]

    # Find all the faces in the current frame of video
    face_locations = face_recognition.face_locations(rgb_image)

    if len(face_locations) == 0:
        return None

    # Display the results
    top, right, bottom, left = face_locations[0]

    # Crop the rect and write it
    crop_image = image[top:bottom, left:right].copy()
    full_path = pic_path + '/' + datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S-') + '.jpg'
    cv2.imwrite(full_path, crop_image)

    return crop_image



def store_face(name, img_path, db_conn):
    '''
    @ parameter:
        name: name of the person to be recorded
        img_path: path of pictures of the person
        db_conn: database connection
    @ return value:
        None
    '''

    full_path = img_path + '/' + name
    if not os.path.exists(full_path):
        print('No picture provided!')
        return

    cursor = db_conn.cursor()
    cursor.execute('SELECT name, person_ID FROM Persons WHERE name=%s', (name,))
    person_id = ''
    result = cursor.fetchall()
    if len(result) > 0:
        person_id = result[0][1]
    else:
        cursor.execute('SELECT UUID()')
        person_id = cursor.fetchone()[0]
        current_time = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S')
        cursor.execute('INSERT INTO Persons (person_ID, name, last_meet_time) VALUES (%s, %s, %s)', (person_id, name, current_time))

    for file_name in os.listdir(full_path):
        if file_name.endswith('.jpg') or file_name.endswith('.bmp'):
            img = face_recognition.load_image_file(full_path + '/' + file_name)
            recognition_result = face_recognition.face_encodings(img)
            if len(recognition_result) == 0:
                print('in file {0} : no face detected'.format(file_name))
                continue
            vector = pickle.dumps(recognition_result[0])
            cursor.execute('INSERT INTO Vectors (vector, person_ID) VALUES (%s,%s)', (vector, person_id))

    db_conn.commit()


def load_faces(db, user, passwd):
    '''
    @ parameter:
        db_conn: database connect object
    @ return value:
        known_faces: dict{uuid:[face_encoding]}
    '''

    db_conn = MySQLdb.connect(db=db, user=user, passwd=passwd)
    known_faces = {}
    cursor = db_conn.cursor()
    cursor.execute('SELECT DISTINCT Persons.person_ID FROM Persons, Vectors WHERE Persons.person_ID = Vectors.person_ID ')
    pids = cursor.fetchall()
    for pid, in pids:
        known_faces[pid] = []
        cursor.execute('SELECT Vectors.vector FROM Persons, Vectors WHERE Persons.person_ID = Vectors.person_ID AND Persons.person_ID = %s', (pid,))
        vectors = cursor.fetchall()
        for vector, in vectors:
            known_faces[pid].append(pickle.loads(vector))
    return known_faces



def get_face_distances(known_faces, unknown_face):
    '''
    @ parameter:
        known_faces: dict{name:[face_encoding]}
        unknown_faces: 128-d array (face encoding)
    @ return value:
        distances: dict{name:distance}
    '''

    '''
        When using a distance threshold of 0.6, the dlib model obtains an accuracy
    of 99.38% on the standard LFW face recognition benchmark, which is
    comparable to other state-of-the-art methods for face recognition as of
    February 2017. This accuracy means that, when presented with a pair of face
    images, the tool will correctly identify if the pair belongs to the same
    person or is from different people 99.38% of the time.
    '''

    distances = {}
    for name in known_faces:
        match_dist = 1000 # Large enough
        for known_face in known_faces[name]:
            dist = np.linalg.norm(known_face - unknown_face)
            if dist < match_dist:
                match_dist = dist
        distances[name] = match_dist

    return distances



def match_face(distances, tolerance):
    '''
    @ parameter:
        distances: dict{name:distance}
        tolerance: the maximum distance to recognize
    @ return value:
        match: tuple (name, distance), name may be 'Unknown'
    '''

    match_name = None
    match_dist = 1000 # Large enough
    for person_id in distances:
        if distances[person_id] < match_dist:
            match_dist = distances[person_id]
            match_id = person_id
    if match_dist > tolerance:
        match_id = ''
    return (match_id, match_dist)



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



def get_geolocation():
    url = 'http://api.map.baidu.com/location/ip?ak=uUNkiGCf08sLOwqXyOhYAUKLdyqhIK6H&sn=e62fe445afb83f1fb6ffe3e43297d6bb'
    req = urllib.request.urlopen(url)
    res = req.read().decode()
    tmp = json.loads(res)
    return tmp['content']['address']




def recognize_face_process(q_image, q_result, db, user, passwd, tolerance, test=False):

    db_conn = MySQLdb.connect(db=db, user=user, passwd=passwd)
    known_faces = load_faces(db, user, passwd)
    face_locations = []
    face_encodings = []
    face_names = []

    while True:
        image = q_image.get(True)
        #print('get a image')
        rgb_image = image[:, :, ::-1]
        face_locations = face_recognition.face_locations(rgb_image, number_of_times_to_upsample=1)
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations, num_jitters=1)
        face_matches = []

        for face_encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
            # See if the face is a match for the known face(s)
            distances = get_face_distances(known_faces, face_encoding)
            match_id, match_dist = match_face(distances, tolerance)
            face_matches.append((match_id, match_dist, top, right, bottom, left))


        q_result.put((face_matches, image))


        if test:
            if len(face_matches) == 0:
                print('No face')
            else:
                print('Detected face')

                for (top, right, bottom, left), match in zip(face_locations, face_matches):
                    # Draw a box around the face
                    cv2.rectangle(image, (left, top), (right, bottom), (0, 0, 255), 1)

                    # Draw a label with a name below the face
                    #cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                    font = cv2.FONT_HERSHEY_DUPLEX
                    cv2.putText(image, match[0]+':'+'%.2f'%(match[1]), (left, bottom), font, 1.0, (0, 0, 255), 1)

                if not os.path.exists('./test_result/'):
                    os.mkdir('./test_result')
                cv2.imwrite('./test_result/' + datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S') + '.jpg', image)



def analyze_result_process(q_result, q_info, db, user, passwd):

    MEET_INTERVAL = 10
    CONFIRM_GRADE = 3
    db_conn = MySQLdb.connect(db=db, user=user, passwd=passwd)
    db_conn.set_character_set('utf8')
    unknown_confirm = 0

    while True:
        face_matches, image = q_result.get(True)
        result_info = []

        for match in face_matches:
            info = {}
            person_id = match[0]
            if len(person_id) > 0: # known
                unknown_confirm = 0
                cursor = db_conn.cursor()
                cursor.execute('SET NAMES utf8;')
                cursor.execute('SET CHARACTER SET utf8;')
                cursor.execute('SET character_set_connection=utf8;')
                cursor.execute('SELECT name, last_meet_time FROM Persons WHERE person_ID=%s', (person_id,))
                result = cursor.fetchone()
                name = result[0]
                last_meet_time = result[1]
                # get info
                info['name'] = name
                info['distance'] = match[1]
                info['last_meet_time'] = last_meet_time.strftime('%Y-%m-%d-%H-%M-%S')
                cursor.execute('SELECT meet_time, meet_place FROM Meets WHERE person_ID=%s', (person_id,))
                result = cursor.fetchall()[-3:]
                info['meet_times'] = []
                info['meet_places'] = []
                for t, p in result:
                    info['meet_times'].append(t.strftime('%Y-%m-%d-%H-%M-%S'))
                    info['meet_places'].append(p)
                result_info.append(info)
                # update database
                current_time = datetime.now()
                if (current_time - last_meet_time).seconds < MEET_INTERVAL:
                    continue
                current_place = get_geolocation()
                current_time = current_time.strftime('%Y-%m-%d-%H-%M-%S')
                cursor.execute('UPDATE Persons SET last_meet_time=%s WHERE person_ID=%s',
                                (current_time, person_id,))
                cursor.execute('INSERT INTO Meets (meet_time, meet_place, person_ID) VALUES (%s,%s,%s)',
                                (current_time, current_place, person_id,))
                db_conn.commit()
            else: # Unknown
                info['name'] = 'Unknown'
                info['distance'] = match[1]
                result_info.append(info)

                if unknown_confirm < CONFIRM_GRADE:
                    unknown_confirm += 1
                    continue
                unknown_confirm = 0
                cursor = db_conn.cursor()
                cursor.execute('SELECT UUID()')
                person_id = cursor.fetchone()[0]
                name = 'Unknown'
                current_time = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S')
                cursor.execute('INSERT INTO Persons (person_ID, name, last_meet_time) VALUES (%s, %s, %s)', (person_id, name, current_time))
                current_place = get_geolocation()
                cursor.execute('UPDATE Persons SET last_meet_time=%s WHERE person_ID=%s',
                                (current_time, person_id,))
                cursor.execute('INSERT INTO Meets (meet_time, meet_place, person_ID) VALUES (%s,%s,%s)',
                                (current_time, current_place, person_id,))
                db_conn.commit()


        #print(result_info)
        q_info.put(result_info)
