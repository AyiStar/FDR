import copy
import csv
import os
import time
import json
import pickle
import urllib.request
from datetime import datetime

import face_recognition
import cv2
import numpy as np
import MySQLdb
from PyQt5 import QtGui
import networkx

import face_utils
import stat_utils
import weibo_utils



def get_QImage(image):
    height, width, channel = image.shape
    image = QtGui.QImage(image.data, width, height, 3 * width, QtGui.QImage.Format_RGB888)
    image = image.rgbSwapped()
    return image



def recognize_face_process(q_image, q_result, q_change, db, user, passwd, tolerance, test=False):

    db_conn = MySQLdb.connect(db=db, user=user, passwd=passwd)
    known_faces = face_utils.load_faces(db, user, passwd)
    face_locations = []
    face_encodings = []
    face_names = []

    while True:
        image = q_image.get(True)
        cursor = db_conn.cursor()
        if not q_change.empty():
            q_change.get()
            known_faces = face_utils.load_faces(db, user, passwd)
        rgb_image = image[:, :, ::-1]
        face_locations = face_recognition.face_locations(rgb_image, number_of_times_to_upsample=1)
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations, num_jitters=1)
        face_matches = []

        for face_encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
            # See if the face is a match for the known face(s)
            distances = face_utils.get_face_distances(known_faces, face_encoding)
            match_id, match_dist = face_utils.match_face(distances, tolerance)
            face_matches.append((match_id, match_dist, top, right, bottom, left))

        if q_result.empty():
            q_result.put((face_matches, image))


        if test:
            if len(face_matches) == 0:
                print('No face')
            else:
                print('Detected face')

                # for (top, right, bottom, left), match in zip(face_locations, face_matches):
                #     # Draw a box around the face
                #     cv2.rectangle(image, (left, top), (right, bottom), (0, 0, 255), 1)

                #     # Draw a label with a name below the face
                #     #cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                #     font = cv2.FONT_HERSHEY_DUPLEX
                #     cv2.putText(image, match[0]+':'+'%.2f'%(match[1]), (left, bottom), font, 1.0, (0, 0, 255), 1)

                # if not os.path.exists('../tests/test_result/'):
                #     os.mkdir('../tests/test_result/')
                # cv2.imwrite('../tests/test_result/' + datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S') + '.jpg', image)



def analyze_result_process(q_result, q_info, q_change, db, user, passwd):

    MEET_INTERVAL = 30
    CONFIRM_GRADE = 5
    db_conn = MySQLdb.connect(db=db, user=user, passwd=passwd)
    db_conn.set_character_set('utf8')
    unknown_confirm = 0

    while True:
        face_matches, image = q_result.get(True)
        print('receive a result')
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
                cursor.execute('SELECT COUNT(meet_ID) FROM Meets WHERE person_ID=%s', (person_id,))
                result = cursor.fetchone()
                info['num_meets'] = result[0]
                cursor.execute('SELECT meet_time, meet_place FROM Meets WHERE person_ID=%s', (person_id,))
                result = cursor.fetchall()[-3:]
                info['meet_times'] = []
                info['meet_places'] = []
                for t, p in result:
                    info['meet_times'].append(t.strftime('%Y-%m-%d-%H-%M-%S'))
                    info['meet_places'].append(p)
                cursor.execute('SELECT weibo_name, weibo_uid FROM WeiboAccounts WHERE person_ID=%s', (person_id,))
                result = cursor.fetchall()
                if len(result) > 0:
                    weibo_name, weibo_uid = result[0]
                    word_cloud_path = './data/wordcloud/' + weibo_name + '.jpg'
                    if os.path.exists(word_cloud_path):
                        info['word_cloud'] = word_cloud_path
                network_path = './data/network/' + person_id + '.jpg'
                if os.path.exists(network_path):
                    info['network'] = network_path
                result_info.append(info)

                # update database
                current_time = datetime.now()
                if (current_time - last_meet_time).seconds < MEET_INTERVAL:
                    continue
                current_place = face_utils.get_geolocation()
                current_time = current_time.strftime('%Y-%m-%d-%H-%M-%S')
                cursor.execute('UPDATE Persons SET last_meet_time=%s WHERE person_ID=%s',
                                (current_time, person_id,))
                cursor.execute('INSERT INTO Meets (meet_time, meet_place, person_ID) VALUES (%s,%s,%s)',
                                (current_time, current_place, person_id,))
                db_conn.commit()

            else: # Unknown

                cursor = db_conn.cursor()

                # get info
                info['name'] = ''
                info['distance'] = match[1]
                result_info.append(info)

                if unknown_confirm < CONFIRM_GRADE:
                    unknown_confirm += 1
                    continue
                unknown_confirm = 0
                top = match[2]
                right = match[3]
                bottom = match[4]
                left = match[5]
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
                current_place = face_utils.get_geolocation()
                cursor.execute('INSERT INTO Meets (meet_time, meet_place, person_ID) VALUES (%s,%s,%s)',
                                (current_time, current_place, person_id,))
                cv2.imwrite('./data/photo/' + person_id + '.jpg', image)
                db_conn.commit()
                q_change.put(0)
                while not q_change.empty():
                    pass


        print(result_info)
        # q_info.put(result_info)



def stranger_entry_process(db_user, db_passwd, db_name, person_name, image, q_change, tolerance=0.4):

    db_conn = MySQLdb.connect(user=db_user, passwd=db_passwd, db=db_name)
    cursor = db_conn.cursor()
    known_faces = face_utils.load_faces(db_name, db_user, db_passwd)

    rgb_image = image[:, :, ::-1]
    face_locations = face_recognition.face_locations(rgb_image, number_of_times_to_upsample=1)
    if len(face_locations) > 1:
        print("Error: too many people in camera")
        return
    face_encodings = face_recognition.face_encodings(rgb_image, face_locations, num_jitters=1)
    face_matches = []

    distances = face_utils.get_face_distances(known_faces, face_encodings[0])
    person_id, match_dist = face_utils.match_face(distances, tolerance)


    if person_id == '':
        cursor.execute('SELECT UUID()')
        person_id = cursor.fetchone()[0]
        current_time = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S')
        cursor.execute('INSERT INTO Persons (person_ID, name, last_meet_time) VALUES (%s, %s, %s)', (person_id, person_name, current_time))
        # store the image
        cv2.imwrite('./data/photo/' + person_id + '.jpg', self.image)
    else:
        cursor.execute('UPDATE Persons SET name=%s WHERE person_ID=%s', (person_name, person_id))
    vector = pickle.dumps(face_encodings[0])
    cursor.execute('INSERT INTO Vectors (vector, person_ID) VALUES (%s,%s)', (vector, person_id))
    db_conn.commit()
    q_change.put(0)



def weibo_entry_process(db_user, db_passwd, db_name, person_name, weibo_user_name):
    cookie = {
            "Cookie": '_T_WM=46ac77aa23a8c1ecba62cea35d74782a; SUB=_2A252M0H0DeRhGeBP6FcU8CbEwzyIHXVV3G-8rDV6PUJbkdANLW_9kW1NRU6EfTCytvr8Jijab7SH2IrbDcZ6rBBK; SUHB=0M2Vamy4SBy7uA; SCF=ArZJ2F9V-QuNENdMfe1ebva5AQUlf13tiq0ofE3CYdI9N-YhR3ydNMtVgWq23eD_wmj5kfNH_2EvoD_QMK9eCJg.; M_WEIBOCN_PARAMS=luicode%3D10000011%26lfid%3D102803_ctg1_8999_-_ctg1_8999_home; MLOGIN=1',
            }
    wb = weibo_utils.WeiboClient(cookie=cookie, db_user=db_user, db_passwd=db_passwd, db_name=db_name)
    uid = wb.get_uid(weibo_user_name)
    if uid is not None:
        wb.save_info(person_name, weibo_user_name, uid)
        wb.get_weibo([uid])
        ws = stat_utils.WeiboStat(db_user, db_passwd, db_name)
        ws.get_text(uid)
        ws.word_stat()
        ws.generate_word_cloud(pic_path='./data/wordcloud/', weibo_user_name=weibo_user_name)



def relation_entry_process(db_user, db_passwd, db_name, person1_name, person2_name, relation_type):
    db_conn = MySQLdb.connect(user=db_user, passwd=db_passwd, db=db_name)
    cursor = db_conn.cursor()
    # get person 1
    cursor.execute("SELECT person_ID FROM Persons WHERE name=%s", (person1_name,))
    result = cursor.fetchall()
    if len(result) == 0:
        print('Error: person 1 does not exist')
        return
    person1_id = result[0][0]
    # get person 2
    cursor.execute("SELECT person_ID FROM Persons WHERE name=%s", (person2_name,))
    result = cursor.fetchall()
    if len(result) == 0:
        print('Error: person 2 does not exist')
        return
    person2_id = result[0][0]
    # insert relation
    cursor.execute("INSERT INTO Relations (person1_ID, person2_ID, relation_type) VALUES (%s, %s, %s)",
                    (person1_id, person2_id, relation_type))
    db_conn.commit()
    ns = stat_utils.NetworkStat(db_user, db_passwd, db_name)
    ns.generate_network(person1_id)
    ns.generate_network(person2_id)



def delete_person(db_user, db_passwd, db_name, person_id):
    db_conn = MySQLdb.connect(user=db_user, passwd=db_passwd, db=db_name)
    cursor = db_conn.cursor()

    cursor.execute('DELETE FROM Persons WHERE person_ID=%s', (person_id,))
    cursor.execute('DELETE FROM Meets   WHERE person_ID=%s', (person_id,))
    cursor.execute('DELETE FROM Vectors WHERE person_ID=%s', (person_id,))
    cursor.execute('DELETE FROM WeiboAccounts WHERE person_ID=%s', (person_id,))
    cursor.execute('DELETE FROM Relations WHERE person1_ID=%s OR person2_ID=%s', (person_id, person_id))

    # TODO delete weibos as well
    db_conn.commit()
    db_conn.close()



def alter_person(db_user, db_passwd, db_name, person_id, alter_name):
    db_conn = MySQLdb.connect(user=db_user, passwd=db_passwd, db=db_name)
    db_conn.set_character_set('utf8')
    cursor = db_conn.cursor()
    cursor.execute('SET NAMES utf8;')
    cursor.execute('SET CHARACTER SET utf8;')
    cursor.execute('SET character_set_connection=utf8;')

    cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (person_id,))
    origin_name = cursor.fetchone()[0]
    cursor.execute('SELECT person_ID FROM Persons WHERE name=%s', (alter_name,))
    result = cursor.fetchall()

    if len(result) > 0:
        # alter_name exists
        alter_person_id = result[0][0]
        cursor.execute('DELETE FROM Persons WHERE person_ID=%s', (person_id,))
        cursor.execute('UPDATE Vectors SET person_ID=%s WHERE person_ID=%s', (alter_person_id,person_id))
        cursor.execute('UPDATE Meets SET person_ID=%s WHERE person_ID=%s', (alter_person_id,person_id))
        cursor.execute('UPDATE WeiboAccounts SET person_ID=%s WHERE person_ID=%s', (alter_person_id,person_id))
        cursor.execute('UPDATE Relations SET person1_ID=%s WHERE person1_ID=%s', (alter_person_id,person_id))
        cursor.execute('UPDATE Relations SET person2_ID=%s WHERE person2_ID=%s', (alter_person_id,person_id))
    else:
        # a new name
        cursor.execute('UPDATE Persons SET name=%s WHERE person_ID=%s', (alter_name, person_id))

    db_conn.commit()
    db_conn.close()