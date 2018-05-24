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
from weiboclient import WeiboClient
from statutils import WeiboStat

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