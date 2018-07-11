import copy
import csv
import os
import time
import json
import pickle
import urllib.request
import math
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



def recognize_face_process(q_image, q_result, q_change, q_change_in, db, user, passwd, tolerance, test=False):
    '''
        q_image: image IN
        q_result: result OUT
        q_change: change OUT
    '''
    MEET_INTERVAL = 30
    CONFIRM_GRADE = 3
    unknown_confirm = 0
    db_conn = MySQLdb.connect(db=db, user=user, passwd=passwd)
    db_conn.set_character_set('utf8')
    known_faces = face_utils.load_faces(db, user, passwd)
    # current_place = face_utils.get_geolocation()
    current_place = '湖北省武汉市'

    while True:
        image = q_image.get(True)
        rgb_image = image[:, :, ::-1]
        face_locations = face_recognition.face_locations(rgb_image, number_of_times_to_upsample=1)
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations, num_jitters=1)
        face_matches = []
        need_update = False

        for face_encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
            # See if the face is a match for the known face(s)
            distances = face_utils.get_face_distances(known_faces, face_encoding)
            match_id, match_dist = face_utils.match_face(distances, tolerance)
            match = (match_id, match_dist, top, right, bottom, left)
            face_matches.append(match)

        face_matches.sort(key=lambda x: x[5])

        if [match for match in face_matches if len(match[0])==0]:
            unknown_confirm += 1
        else:
            unknown_confirm = 0

        for match in face_matches:

            person_id, match_dist, top, right, bottom, left = match

            if len(person_id) > 0: # known

                cursor = db_conn.cursor()
                cursor.execute('SET NAMES utf8;')
                cursor.execute('SET CHARACTER SET utf8;')
                cursor.execute('SET character_set_connection=utf8;')
                if cursor.execute('SELECT name, last_meet_time FROM Persons WHERE person_ID=%s', (person_id,)) <= 0:
                    # print('Error: no such person')
                    continue
                name, last_meet_time = cursor.fetchone()

                # update database
                current_time = datetime.now()
                if (current_time - last_meet_time).seconds < MEET_INTERVAL:
                    continue
                # current_place = face_utils.get_geolocation()
                current_time = current_time.strftime('%Y-%m-%d-%H-%M-%S')
                cursor.execute('UPDATE Persons SET last_meet_time=%s WHERE person_ID=%s',
                                (current_time, person_id,))
                cursor.execute('INSERT INTO Meets (meet_time, meet_place, person_ID) VALUES (%s,%s,%s)',
                                (current_time, current_place, person_id,))
                db_conn.commit()

            else: # Unknown

                cursor = db_conn.cursor()

                if unknown_confirm < CONFIRM_GRADE:
                    continue
                unknown_confirm = 0
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
                # current_place = face_utils.get_geolocation()
                cursor.execute('INSERT INTO Meets (meet_time, meet_place, person_ID) VALUES (%s,%s,%s)',
                                (current_time, current_place, person_id,))

                # point out the face in the picture
                temp_image = image.copy()
                cv2.circle(temp_image, (int((left + right)/2), int((top + bottom)/2)),
                            int(math.sqrt(((right - left)**2 + (bottom - top)**2))/2),
                            (255,0,0), thickness=7)

                cv2.imwrite('./data/photo/' + person_id + '.jpg', temp_image)
                db_conn.commit()
                need_update = True

        if not q_change_in.empty():
            q_change_in.get()
            known_faces = face_utils.load_faces(db, user, passwd)

        if need_update:
            q_change.put(0)
            while not q_change.empty():
                pass

        if q_result.empty() and len(face_matches) > 0:
            q_result.put(face_matches)
            while not q_result.empty():
                pass


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



def weibo_crawl_process(db_login, uid, progress_queue=None):

    weibo_crawler = weibo_utils.WeiboCrawler(db_login)
    weibo_data = weibo_crawler.get_weibos(uid, progress_queue=progress_queue)
    progress_queue.put('正在写入数据库...')
    weibo_crawler.export_to_database(weibo_data)
    progress_queue.put('正在分析文本...')
    weibo_stat = stat_utils.WeiboStat(db_login['user'], db_login['passwd'], db_login['db'])
    weibo_stat.get_text(uid)
    weibo_stat.word_stat()
    weibo_stat.generate_hot_word(uid, 5)
    weibo_stat.generate_word_cloud('./data/wordcloud/', uid)
    progress_queue.put('完成!')
    time.sleep(1)



def delete_person(db_login, person_id):
    db_conn = MySQLdb.connect(user=db_login['user'], passwd=db_login['passwd'], db=db_login['db'])
    cursor = db_conn.cursor()

    cursor.execute('DELETE FROM Persons WHERE person_ID=%s', (person_id,))
    cursor.execute('DELETE FROM Meets   WHERE person_ID=%s', (person_id,))
    cursor.execute('DELETE FROM Vectors WHERE person_ID=%s', (person_id,))
    cursor.execute('DELETE FROM WeiboAccounts WHERE person_ID=%s', (person_id,))
    cursor.execute('DELETE FROM Relations WHERE person1_ID=%s OR person2_ID=%s', (person_id, person_id))

    # TODO delete weibos as well
    db_conn.commit()
    db_conn.close()



def alter_person(db_login, person_id, alter_info):

    db_conn = MySQLdb.connect(user=db_login['user'], passwd=db_login['passwd'], db=db_login['db'])
    db_conn.set_character_set('utf8')
    cursor = db_conn.cursor()
    cursor.execute('SET NAMES utf8;')
    cursor.execute('SET CHARACTER SET utf8;')
    cursor.execute('SET character_set_connection=utf8;')

    # name
    if 'name' in alter_info:
        cursor.execute('UPDATE Persons SET name=%s WHERE person_ID=%s', (alter_info['name'], person_id))
    db_conn.commit()

    # relation
    if 'relationship' in alter_info:
        network_stat = stat_utils.NetworkStat(db_login['user'], db_login['passwd'], db_login['db'])
        for relation in alter_info['relationship']:
            if relation['namea'] and relation['nameb']:
                return '关系输入格式错误'
            elif not relation['namea'] and not relation['nameb']:
                return '关系输入格式错误'
            elif not relation['namea']:
                if cursor.execute('SELECT person_ID FROM Persons WHERE name=%s', (relation['nameb'],)) == 0:
                    return relation['nameb'] + '不存在'
                person2_id = cursor.fetchall()[0][0]
                cursor.execute('DELETE FROM Relations WHERE person1_ID=%s AND person2_ID=%s', (person_id, person2_id,))
                cursor.execute('DELETE FROM Relations WHERE person1_ID=%s AND person2_ID=%s', (person2_id, person_id,))
                cursor.execute('INSERT INTO Relations (person1_ID, person2_ID, relation_type) VALUES (%s, %s, %s)',
                                (person_id, person2_id, relation['rel']))
                db_conn.commit()
                network_stat.generate_network(person2_id)
            elif not relation['nameb']:
                if cursor.execute('SELECT person_ID FROM Persons WHERE name=%s', (relation['namea'],)) == 0:
                    return relation['namea'] + '不存在'
                person1_id = cursor.fetchall()[0][0]
                cursor.execute('DELETE FROM Relations WHERE person1_ID=%s AND person2_ID=%s', (person1_id, person_id,))
                cursor.execute('DELETE FROM Relations WHERE person1_ID=%s AND person2_ID=%s', (person_id, person1_id,))
                cursor.execute('INSERT INTO Relations (person1_ID, person2_ID, relation_type) VALUES (%s, %s, %s)',
                                (person1_id, person_id, relation['rel']))
                db_conn.commit()
                network_stat.generate_network(person1_id)
            else:
                pass
        db_conn.commit()
        network_stat.generate_network(person_id)

    # weibo
    if 'weibo' in alter_info:
        weibo_crawler = weibo_utils.WeiboCrawler(db_login)
        uid = weibo_crawler.get_uid(alter_info['weibo'])
        if uid:
            cursor.execute('DELETE FROM WeiboAccounts WHERE person_ID=%s', (person_id,))
            cursor.execute('INSERT INTO WeiboAccounts (person_ID, weibo_name, weibo_uid) VALUES (%s, %s, %s)',
                            (person_id, alter_info['weibo'], uid,))
        else:
            return '微博用户不存在'
    db_conn.commit()

    db_conn.close()
    return ''


