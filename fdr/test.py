import face_utils
import audio_utils
import gui_utils
from weibo_utils import WeiboCrawler

import multiprocessing as mp
# import face_recognition
# import MySQLdb
# import cv2

# db_login = {'user':'hby', 'passwd':'', 'db':'FDR'}
# face_utils.recognize_face_from_file({'user':'ayistar', 'passwd':'', 'db':'FDR'}, '1.jpg', verbose=True)
# sr = audio_utils.SpeechRobot()
# sr.say('你好,毕昊阳,我叫胡冰玉,我有点欠揍哦', person=4, speed=3)
# gui_utils.weibo_crawl_process({'user':'hby', 'passwd':'', 'db':'FDR'}, '5924311707')
signal_queue = mp.Queue()
p = mp.Process(target=gui_utils.voice_wake_process, args=('./resources/models/doudou.pmdl', signal_queue,))
p.start()