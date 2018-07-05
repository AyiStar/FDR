# coding: utf-8

import os
import sys
import pickle
import multiprocessing as mp
import threading

import cv2
import numpy as np
import face_recognition
from PyQt5 import QtWidgets, QtGui, QtCore
import MySQLdb

import face_utils
import weibo_utils
import gui_utils


class RecordVideo(QtCore.QObject):
    '''
    @ Summary:
        An interface for camera.
        Once you click 'Start', it begin to keep
        emitting images captured by camera device.
        Once you lick 'Stop', it stops emitting.
    @ Notes:
        We expicitly set the resolution ratio to 640x480, to fit the GUI.
    '''

    image_signal = QtCore.pyqtSignal(np.ndarray)
    info_signal = QtCore.pyqtSignal()

    def __init__(self, image_queue, info_queue, video=0):
        super().__init__()

        self.camera = cv2.VideoCapture(video)
        self.image_queue = image_queue
        self.info_queue = info_queue
        #self.camera.set(3, 640)
        #self.camera.set(4, 480)
        self.timer = QtCore.QBasicTimer()

    def start_recording(self):
        self.timer.start(0, self)

    def stop_recording(self):
        self.timer.stop()

    def timerEvent(self, event):
        if (event.timerId() != self.timer.timerId()):
            return

        read, image = self.camera.read()
        if read:
            self.image_signal.emit(image)
            if self.image_queue.empty():
                self.image_queue.put(image)
            if not self.info_queue.empty():
                self.info_signal.emit()



class CameraWidget(QtWidgets.QWidget):
    '''
    @ Summary:
        On receiving the image signal emitted by RecordVideo,
        this widget do face recognition for the image,
        and then emit the match result, including name and distance.
    @ Notes:
        We could also change the image to display,
        for example, draw rectangles and matched names, etc.
        But we display those results on the top-right of the GUI,
        using RecognitionResultWidget.
    '''

    def __init__(self, width=640, height=480):

        super().__init__()
        self.image = QtGui.QImage('./resources/icons/pig.jpg')
        self.setFixedSize(width, height)



    def image_slot(self, frame):

        self.image = gui_utils.get_QImage(frame)
        self.update()


    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawImage(0, 0, self.image)
        self.image = QtGui.QImage()



class FaceRecognition(QtCore.QObject):

    def __init__(self, image_queue, result_queue, change_queue, db, user, passwd, tolerance=0.4):

        super().__init__()
        self.db = db
        self.user = user
        self.passwd = passwd
        self.tolerance = tolerance
        self.image_queue = image_queue
        self.result_queue = result_queue
        self.change_queue = change_queue
        self.process = None

    def start_recognizing(self):
        self.process = mp.Process(target=gui_utils.recognize_face_process,
                                  args=(self.image_queue, self.result_queue, self.change_queue, self.db, self.user, self.passwd, self.tolerance,))
        self.process.start()


    def stop_recognizing(self):
        if self.process is not None:
            self.process.terminate()
        while not self.image_queue.empty():
            self.image_queue.get()
        while not self.result_queue.empty():
            self.result_queue.get()



class ResultAnalysis(QtCore.QObject):
    def __init__(self, result_queue, info_queue, change_queue, db, user, passwd):

        super().__init__()
        self.db = db
        self.user = user
        self.passwd = passwd
        self.result_queue = result_queue
        self.info_queue = info_queue
        self.change_queue = change_queue
        self.process = None

    def start_analyzing(self):
        self.process = mp.Process(target=gui_utils.analyze_result_process,
                                  args=(self.result_queue, self.info_queue, self.change_queue, self.db, self.user, self.passwd))
        self.process.start()


    def stop_analyzing(self):
        if self.process is not None:
            self.process.terminate()
        while not self.result_queue.empty():
            self.result_queue.get()
        while not self.info_queue.empty():
            self.info_queue.get()



class ResultDisplayWidget(QtWidgets.QWidget):
    '''
    @ Summary:
        On receiving the result signal emitted by FaceRecognitionWidget,
        this widget display the result.
    '''

    def __init__(self, info_queue):

        super().__init__()

        self._MAX_WIDGET_NUM = 2
        self.info_queue = info_queue
        self.single_display_widget_list = []

        for i in range(self._MAX_WIDGET_NUM):
            self.single_display_widget_list.append(SingleResultDisplayWidget())

        layout = QtWidgets.QHBoxLayout()
        for widget in self.single_display_widget_list:
            layout.addWidget(widget)
        self.setLayout(layout)

    def info_slot(self):

        # result_info : [info]
        # info : {key:value}
        result_info = self.info_queue.get(True)

        self.clear_all_widgets()
        if len(result_info) > 0:
            for i, info in enumerate(result_info):
                self.single_display_widget_list[i].display(info)
        else:
            self.single_display_widget_list[0].result_label.setText('No face detected')

    def clear_all_widgets(self):
        for widget in self.single_display_widget_list:
            widget.clear()



class SingleResultDisplayWidget(QtWidgets.QWidget):

    def __init__(self):

        super().__init__()

        self.word_cloud_label = QtWidgets.QLabel()
        self.network_label = QtWidgets.QLabel()
        self.result_label = QtWidgets.QLabel()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.word_cloud_label)
        layout.addWidget(self.network_label)
        layout.addWidget(self.result_label)
        self.setLayout(layout)

    def display(self, info):

        text = []
        _SIZE = 200

        if 'word_cloud' in info:
            word_cloud = cv2.imread(info['word_cloud'])
            word_cloud = gui_utils.get_QImage(word_cloud)
            self.word_cloud_label.setPixmap(QtGui.QPixmap(word_cloud.scaled(_SIZE, _SIZE, QtCore.Qt.KeepAspectRatio)))
        else:
            self.word_cloud_label.setPixmap(QtGui.QPixmap('./resources/icons/person.png').scaled(_SIZE, _SIZE, QtCore.Qt.KeepAspectRatio))

        if 'network' in info:
            network = cv2.imread(info['network'])
            network = gui_utils.get_QImage(network)
            self.network_label.setPixmap(QtGui.QPixmap(network.scaled(_SIZE, _SIZE, QtCore.Qt.KeepAspectRatio)))
        else:
            self.network_label.setPixmap(QtGui.QPixmap('./resources/icons/social_network.jpg').scaled(_SIZE, _SIZE, QtCore.Qt.KeepAspectRatio))

        name = info['name']
        if name != '':
            text.append('Name : ' + name + '\n')
            text.append('Total meet times: {0}\n'.format(info['num_meets']))
            text.append('Past three meets : \n')
            for t, p in zip(info['meet_times'], info['meet_places']):
                text.append(t + ' , ' + p + '\n')
        else:
            text.append('A person never seen\n')
        text.append('\n')
        self.result_label.setText(''.join(text))


    def clear(self):
        self.word_cloud_label.setPixmap(QtGui.QPixmap())
        self.network_label.setPixmap(QtGui.QPixmap())
        self.result_label.setText('')



class StrangerEntryWidget(QtWidgets.QWidget):
    '''
    @ Summary:
        This widget record new faces in the camera,
        and also compute the feature vectors, and store them.
    '''
    def __init__(self, db_name, db_user, db_passwd, change_queue):

        super().__init__()

        self.change_queue = change_queue
        self.db_user = db_user
        self.db_passwd = db_passwd
        self.db_name = db_name
        self.image = None

        self.title_label = QtWidgets.QLabel('Stranger Entry')
        self.name_input = QtWidgets.QLineEdit('Name')
        self.enter_button = QtWidgets.QPushButton('Enter')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addStretch(2)
        layout.addWidget(self.name_input)
        layout.addWidget(self.enter_button)

        self.enter_button.clicked.connect(self.enter_stranger)

        self.setLayout(layout)

    def enter_stranger(self):
        person_name = self.name_input.text()
        process = mp.Process(target=gui_utils.stranger_entry_process,
                                args=(self.db_user, self.db_passwd, self.db_name, person_name, self.image, self.change_queue))
        process.start()


    def image_slot(self, image):
        self.image = image



class WeiboEntryWidget(QtWidgets.QWidget):

    def __init__(self, pic_path, db_name, user, passwd):

        super().__init__()

        self.pic_path = pic_path
        self.db_user = user
        self.db_passwd = passwd
        self.db_name = db_name

        self.title_label = QtWidgets.QLabel('Weibo Entry')
        self.person_name_input = QtWidgets.QLineEdit('Name')
        self.weibo_name_input = QtWidgets.QLineEdit('Weibo nick name')
        self.enter_button = QtWidgets.QPushButton('Enter')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(self.person_name_input)
        layout.addWidget(self.weibo_name_input)
        layout.addWidget(self.enter_button)

        self.enter_button.clicked.connect(self.enter_weibo)

        self.setLayout(layout)

    def enter_weibo(self):
        person_name = self.person_name_input.text()
        weibo_user_name = self.weibo_name_input.text()

        process = mp.Process(target=gui_utils.weibo_entry_process,
                                args=(self.db_user, self.db_passwd, self.db_name, person_name, weibo_user_name))
        process.start()



class RelationEntryWidget(QtWidgets.QWidget):

    def __init__(self, db_name, db_user, db_passwd):

        super().__init__()

        self.db_user = db_user
        self.db_passwd = db_passwd
        self.db_name = db_name

        self.title_label = QtWidgets.QLabel('Relationship Entry')
        self.person1_name_input = QtWidgets.QLineEdit('Name 1')
        self.person2_name_input = QtWidgets.QLineEdit('Name 2')
        self.relation_input = QtWidgets.QLineEdit('Relation')
        self.enter_button = QtWidgets.QPushButton('Enter')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.person1_name_input)
        layout.addWidget(self.person2_name_input)
        layout.addWidget(self.relation_input)
        layout.addWidget(self.enter_button)

        self.enter_button.clicked.connect(self.enter_relation)

        self.setLayout(layout)

    def enter_relation(self):
        person1_name = self.person1_name_input.text()
        person2_name = self.person2_name_input.text()
        relation_type = self.relation_input.text()

        process = mp.Process(target=gui_utils.relation_entry_process,
                                args=(self.db_user, self.db_passwd, self.db_name, person1_name, person2_name, relation_type))
        process.start()



class MainWidget(QtWidgets.QWidget):
    '''
    @ Summary:
        The main widget, combining the widgets above.
    '''
    def __init__(self, db_user, db_passwd, db_name, video=0):

        super().__init__()

        self.db_user = db_user
        self.db_passwd = db_passwd
        self.db_name = db_name

        self.image_queue = mp.Queue()
        self.result_queue = mp.Queue()
        self.info_queue = mp.Queue()
        self.change_queue = mp.Queue()

        self.record_video = RecordVideo(self.image_queue, self.info_queue, video=video)
        self.camera_widget = CameraWidget()
        self.face_recognition = FaceRecognition(self.image_queue, self.result_queue, self.change_queue, db_name, db_user, db_passwd)
        self.result_analysis = ResultAnalysis(self.result_queue, self.info_queue, self.change_queue, db_name, db_user, db_passwd)
        self.result_display_widget = ResultDisplayWidget(self.info_queue)
        self.strange_entry_widget = StrangerEntryWidget(db_name, db_user, db_passwd, self.change_queue)
        self.weibo_entry_widget = WeiboEntryWidget('./data/wordcloud/', db_name, db_user, db_passwd)
        self.relation_entry_widget = RelationEntryWidget(db_name, db_user, db_passwd)

        self.manage_window = None

        self.reset_button = QtWidgets.QPushButton('Reset')
        self.manage_button = QtWidgets.QPushButton('Manage')
        self.run_button = QtWidgets.QPushButton('Start')
        self.stop_button = QtWidgets.QPushButton('Pause')
        self.exit_button = QtWidgets.QPushButton('Exit')

        self.record_video.image_signal.connect(self.camera_widget.image_slot)
        self.record_video.image_signal.connect(self.strange_entry_widget.image_slot)
        self.record_video.info_signal.connect(self.result_display_widget.info_slot)

        # Create and set the layout
        total_layout = QtWidgets.QHBoxLayout()
        main_layout = QtWidgets.QVBoxLayout()
        disp_layout = QtWidgets.QHBoxLayout()
        manage_layout = QtWidgets.QHBoxLayout()
        control_layout = QtWidgets.QVBoxLayout()

        total_layout.addLayout(main_layout)
        total_layout.addLayout(disp_layout)

        disp_layout.addWidget(self.result_display_widget)

        main_layout.addWidget(self.camera_widget)
        main_layout.addLayout(manage_layout)

        manage_layout.addWidget(self.strange_entry_widget)
        manage_layout.addWidget(self.weibo_entry_widget)
        manage_layout.addWidget(self.relation_entry_widget)
        manage_layout.addLayout(control_layout)

        control_layout.addWidget(self.run_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.manage_button)
        control_layout.addWidget(self.reset_button)
        control_layout.addWidget(self.exit_button)

        self.reset_button.clicked.connect(self.setup)
        self.manage_button.clicked.connect(self.show_manage_window)
        self.run_button.clicked.connect(self.record_video.start_recording)
        self.run_button.clicked.connect(self.face_recognition.start_recognizing)
        self.run_button.clicked.connect(self.result_analysis.start_analyzing)
        self.stop_button.clicked.connect(self.record_video.stop_recording)
        self.stop_button.clicked.connect(self.face_recognition.stop_recognizing)
        self.stop_button.clicked.connect(self.result_analysis.stop_analyzing)
        self.exit_button.clicked.connect(self.face_recognition.stop_recognizing)
        self.exit_button.clicked.connect(self.result_analysis.stop_analyzing)
        self.exit_button.clicked.connect(QtCore.QCoreApplication.quit)
        self.setLayout(total_layout)

    def show_manage_window(self):
        self.manage_window = ManageWindow(self.db_user, self.db_passwd, self.db_name, self.change_queue)
        self.manage_window.show()

    def setup(self):
        os.system('./setup.sh {0}'.format(self.db_user))



class MainWindow(QtWidgets.QMainWindow):
    '''
    @ Summary:
        The main window containging the main widget.
    '''
    def __init__(self, db_user, db_passwd, db_name, video=0):

        super().__init__()
        self.main_widget = MainWidget(db_user, db_passwd, db_name, video=video)
        self.setCentralWidget(self.main_widget)
        self.setWindowTitle('Face Detection & Recognition System')
        self.setWindowIcon(QtGui.QIcon('./resources/icons/icon.jpg'))
        self.show()



class ManageWidget(QtWidgets.QWidget):

    def __init__(self, db_user, db_passwd, db_name, change_queue):

        super().__init__()

        self.change_queue = change_queue
        self.person_widget_list = []
        self.exit_button = QtWidgets.QPushButton('Exit')

        total_layout = QtWidgets.QVBoxLayout()
        main_layout = QtWidgets.QGridLayout()

        db_conn = MySQLdb.connect(user=db_user, passwd=db_passwd, db=db_name)
        db_conn.set_character_set('utf8')
        cursor = db_conn.cursor()
        cursor.execute('SET NAMES utf8;')
        cursor.execute('SET CHARACTER SET utf8;')
        cursor.execute('SET character_set_connection=utf8;')
        cursor.execute('SELECT person_ID FROM Persons')
        person_ids = [x[0] for x in cursor.fetchall()]

        for i, person_id in enumerate(person_ids):
            self.person_widget_list.append(PersonManageWidget(db_user, db_passwd, db_name, person_id, self.change_queue))
            main_layout.addWidget(self.person_widget_list[i], i//3, i%3)

        total_layout.addLayout(main_layout)
        total_layout.addWidget(self.exit_button)

        self.setLayout(total_layout)



class PersonManageWidget(QtWidgets.QWidget):

    def __init__ (self, db_user, db_passwd, db_name, person_id, change_queue):

        super().__init__()

        self.db_user = db_user
        self.db_passwd = db_passwd
        self.db_name = db_name
        self.person_id = person_id
        self.change_queue = change_queue

        self.photo_label = QtWidgets.QLabel()
        self.info_label = QtWidgets.QLabel('')
        self.name_input_label = QtWidgets.QLineEdit('')
        self.alter_button = QtWidgets.QPushButton('Alter')
        self.delete_button = QtWidgets.QPushButton('Delete')

        if os.path.exists('./data/photo/' + person_id + '.jpg'):
            self.photo_label.setPixmap(QtGui.QPixmap('./data/photo/' + person_id + '.jpg').scaled(200, 150, QtCore.Qt.KeepAspectRatio))
        else:
            self.photo_label.setPixmap(QtGui.QPixmap('./resources/icons/question.jpg').scaled(200, 150, QtCore.Qt.KeepAspectRatio))

        db_conn = MySQLdb.connect(user=db_user, passwd=db_passwd, db=db_name)
        db_conn.set_character_set('utf8')
        cursor = db_conn.cursor()
        cursor.execute('SET NAMES utf8;')
        cursor.execute('SET CHARACTER SET utf8;')
        cursor.execute('SET character_set_connection=utf8;')
        cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (person_id,))
        self.name = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(meet_ID) FROM Meets WHERE person_ID=%s', (person_id,))
        self.meet_times = cursor.fetchone()[0]
        db_conn.close()

        self.set_info_text()

        self.alter_button.clicked.connect(self.alter_person)
        self.delete_button.clicked.connect(self.delete_person)

        total_layout = QtWidgets.QHBoxLayout()
        control_layout = QtWidgets.QVBoxLayout()

        total_layout.addWidget(self.photo_label)
        total_layout.addLayout(control_layout)

        control_layout.addWidget(self.info_label)
        control_layout.addWidget(self.name_input_label)
        control_layout.addWidget(self.alter_button)
        control_layout.addWidget(self.delete_button)

        self.setLayout(total_layout)


    def delete_person(self):
        gui_utils.delete_person(self.db_user, self.db_passwd, self.db_name, self.person_id)
        self.info_label.setText('Deleted')
        self.photo_label.setPixmap(QtGui.QPixmap('./resources/icons/question.jpg').scaled(200, 150, QtCore.Qt.KeepAspectRatio))
        self.change_queue.put(0)


    def alter_person(self):
        alter_name = self.name_input_label.text()
        gui_utils.alter_person(self.db_user, self.db_passwd, self.db_name, self.person_id, alter_name)
        self.name = alter_name
        self.set_info_text()
        self.change_queue.put(0)


    def set_info_text(self):
        info_text = []
        info_text.append('Name: {0}\n'.format(self.name))
        info_text.append('Meet times: {0}\n'.format(self.meet_times))
        self.info_label.setText(''.join(info_text))



class ManageWindow(QtWidgets.QMainWindow):

    def __init__(self, db_user, db_passwd, db_name, change_queue):

        super().__init__()
        self.manage_widget = ManageWidget(db_user, db_passwd, db_name, change_queue)
        self.manage_widget.exit_button.clicked.connect(self.close)
        self.setCentralWidget(self.manage_widget)
        self.setWindowTitle('Manage Window')
        self.setWindowIcon(QtGui.QIcon('./resources/icons/icon.jpg'))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main_GUI = MainWindow('ayistar', '', 'FDR', video='tcp://192.168.1.199:8001')
    sys.exit(app.exec_())
