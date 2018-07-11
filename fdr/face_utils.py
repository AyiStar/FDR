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
import math
from datetime import datetime



def detect_face(image):


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
    #full_path = pic_path + '/' + datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S-') + '.jpg'
    #cv2.imwrite(full_path, crop_image)

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
        distances: dict{id:distance}
        tolerance: the maximum distance to recognize
    @ return value:
        match: tuple (id, distance), id may be ''
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



def get_geolocation():
    url = 'http://api.map.baidu.com/location/ip?ak=uUNkiGCf08sLOwqXyOhYAUKLdyqhIK6H&sn=e62fe445afb83f1fb6ffe3e43297d6bb'
    req = urllib.request.urlopen(url)
    res = req.read().decode()
    tmp = json.loads(res)
    return tmp['content']['address']



def recognize_face_from_file(db_login, file_path, tolerance=0.4, verbose=False):

    image = cv2.imread(file_path)
    if image is None:
        print('Error: image file not found')
        return

    MEET_INTERVAL = 30
    CONFIRM_GRADE = 3
    current_place = '湖北省武汉市武汉大学大学生创新创业中心'
    rgb_image = image[:, :, ::-1]

    if verbose:
        print('recognizing from ' + file_path)

    db_conn = MySQLdb.connect(db=db_login['db'], user=db_login['user'], passwd=db_login['passwd'])
    db_conn.set_character_set('utf8')
    known_faces = load_faces(db_login['db'], db_login['user'], db_login['passwd'])
    face_locations = face_recognition.face_locations(rgb_image, number_of_times_to_upsample=1)
    face_encodings = face_recognition.face_encodings(rgb_image, face_locations, num_jitters=1)
    face_matches = []

    for face_encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
        # See if the face is a match for the known face(s)
        distances = get_face_distances(known_faces, face_encoding)
        match_id, match_dist = match_face(distances, tolerance)
        match = (match_id, match_dist, top, right, bottom, left)
        face_matches.append(match)

    if verbose:
        print(str(len(face_matches)) + ' face(s) detected')

    for match in face_matches:

        person_id, match_dist, top, right, bottom, left = match

        if len(person_id) > 0: # known

            cursor = db_conn.cursor()
            cursor.execute('SET NAMES utf8;')
            cursor.execute('SET CHARACTER SET utf8;')
            cursor.execute('SET character_set_connection=utf8;')
            if cursor.execute('SELECT name, last_meet_time FROM Persons WHERE person_ID=%s', (person_id,)) <= 0:
                print('Error: no such person')
                continue
            name, last_meet_time = cursor.fetchone()

            if verbose:
                print('Known person ' + name)

            # update database
            current_time = datetime.now()
            if (current_time - last_meet_time).seconds < MEET_INTERVAL:
                continue
            # current_place = get_geolocation()
            current_time = current_time.strftime('%Y-%m-%d-%H-%M-%S')
            cursor.execute('UPDATE Persons SET last_meet_time=%s WHERE person_ID=%s',
                            (current_time, person_id,))
            cursor.execute('INSERT INTO Meets (meet_time, meet_place, person_ID) VALUES (%s,%s,%s)',
                            (current_time, current_place, person_id,))
            db_conn.commit()

        else: # Unknown

            if verbose:
                print('Unknown person, storing')

            cursor = db_conn.cursor()
            temp_result = face_recognition.face_encodings(image, known_face_locations=[(top, right, bottom, left)])
            if len(temp_result) == 0:
                continue
            cursor.execute('SELECT UUID()')
            person_id = cursor.fetchone()[0]
            name = 'Unknown'
            current_time = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S')
            cursor.execute('INSERT INTO Persons (person_ID, name, last_meet_time) VALUES (%s, %s, %s)', (person_id, name, current_time))
            vector = pickle.dumps(temp_result[0])
            cursor.execute('INSERT INTO Vectors (vector, person_ID) VALUES (%s,%s)', (vector, person_id))
            # current_place = get_geolocation()
            cursor.execute('INSERT INTO Meets (meet_time, meet_place, person_ID) VALUES (%s,%s,%s)',
                            (current_time, current_place, person_id,))

            # point out the face in the picture
            temp_image = image.copy()
            cv2.circle(temp_image, (int((left + right)/2), int((top + bottom)/2)),
                        int(math.sqrt(((right - left)**2 + (bottom - top)**2))/2),
                        (255,0,0), thickness=7)

            cv2.imwrite('./data/photo/' + person_id + '.jpg', temp_image)
            db_conn.commit()