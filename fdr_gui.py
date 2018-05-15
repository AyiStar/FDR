# coding: utf-8

import os
import sys
import time
import pickle
import multiprocessing as mp
import cv2
import numpy as np
import face_recognition
from PyQt5 import QtWidgets, QtGui, QtCore
import utils
import MySQLdb




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
        self.image = QtGui.QImage('./img/pig.jpg')
        self.setFixedSize(width, height)



    def image_slot(self, frame):

        self.image = self.get_QImage(frame)
        self.update()

    def get_QImage(self, image):
        height, width, channel = image.shape
        image = QtGui.QImage(image.data, width,height, 3 * width, QtGui.QImage.Format_RGB888)
        image = image.rgbSwapped()
        return image


    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawImage(0, 0, self.image)
        self.image = QtGui.QImage()



class FaceRecognition(QtCore.QObject):

    def __init__(self, image_queue, result_queue, db_conn, tolerance=0.4):

        super().__init__()
        self.db_conn = db_conn
        self.tolerance = tolerance
        self.known_faces = utils.load_faces(self.db_conn)
        self.image_queue = image_queue
        self.result_queue = result_queue
        self.process = None

    def start_recognizing(self):
        self.process = mp.Process(target=utils.recognize_face_process,
                                  args=(self.image_queue, self.result_queue, self.db_conn, self.tolerance, ))
        self.process.start()


    def stop_recognizing(self):
        if self.process is not None:
            self.process.terminate()
        while not self.image_queue.empty():
            self.image_queue.get()
        while not self.result_queue.empty():
            self.result_queue.get()



class ResultAnalysis(QtCore.QObject):
    def __init__(self, result_queue, info_queue, db_conn):

        super().__init__()
        self.db_conn = db_conn
        self.result_queue = result_queue
        self.info_queue = info_queue
        self.process = None

    def start_analyzing(self):
        self.process = mp.Process(target=utils.analyze_result_process,
                                  args=(self.result_queue, self.info_queue, self.db_conn, ))
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

        self.info_queue = info_queue
        self.result_label = QtWidgets.QLabel('Name : --\nDistance : --\n')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.result_label)
        self.setLayout(layout)

    def info_slot(self):

        result_info = self.info_queue.get(True)

        if len(result_info) > 0:
            text = []
            for info in result_info:
                text.append('Name : ' + info['name'] + '\n')
                if ('meet_times' in info) and ('meet_places' in info):
                    text.append('Past three meets : \n')
                    for t, p in zip(info['meet_times'], info['meet_places']):
                        text.append(t + ' , ' + p + '\n')
                text.append('\n')
            self.result_label.setText(''.join(text))
        else:
            self.result_label.setText('No face detected')



class StrangerEntryWidget(QtWidgets.QWidget):
    '''
    @ Summary:
        This widget record new faces in the camera,
        and also compute the feature vectors, and store them.
    '''
    def __init__(self, pic_path, db_conn):

        super().__init__()

        self.pic_path = pic_path
        self.db_conn = db_conn
        self.image = None

        self.img_label  = QtWidgets.QLabel()
        self.img_label.setPixmap(QtGui.QPixmap('./img/dog.jpg').scaled(128, 128, QtCore.Qt.KeepAspectRatio))
        self.name_input = QtWidgets.QLineEdit('Your name')
        self.enter_button = QtWidgets.QPushButton('Enter New Data')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.img_label)
        layout.addWidget(self.name_input)
        layout.addWidget(self.enter_button)

        self.enter_button.clicked.connect(self.enter_stranger)

        self.setLayout(layout)

    def enter_stranger(self):
        cursor = self.db_conn.cursor()
        name = self.name_input.text()
        full_path = self.pic_path + '/' + name + '/'
        if not os.path.exists(full_path):
            os.mkdir(full_path)

        face = utils.detect_face(self.image, full_path)
        if face is not None:
            # show the image
            self.img_label.setPixmap(QtGui.QPixmap(self.get_QImage(face)).scaled(128, 128, QtCore.Qt.KeepAspectRatio))
            # store the image
            person_id = ''
            cursor.execute('SELECT name, person_ID FROM Persons WHERE name=%s', (name,))
            result = cursor.fetchall()
            if len(result) > 0:
                person_id = result[0][1]
            else:
                cursor.execute('SELECT UUID()')
                person_id = cursor.fetchone()[0]
                current_time = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S')
                cursor.execute('INSERT INTO Persons (person_ID, name, last_meet_time) VALUES (%s, %s, %s)', (person_id, name, current_time))
            vector = pickle.dumps(face_recognition.face_encodings(face)[0])
            cursor.execute('INSERT INTO Vectors (vector, person_ID) VALUES (%s,%s)', (vector, person_id))
            self.db_conn.commit()


    def image_slot(self, image):
        self.image = image

    def get_QImage(self, image):
        height, width, channel = image.shape
        image = QtGui.QImage(image.data, width, height, 3 * width, QtGui.QImage.Format_RGB888)
        image = image.rgbSwapped()
        return image



class MainWidget(QtWidgets.QWidget):
    '''
    @ Summary:
        The main widget, combining the widgets above.
    '''
    def __init__(self, pic_path, db_conn, video=0):

        super().__init__()

        self.image_queue = mp.Queue()
        self.result_queue = mp.Queue()
        self.info_queue = mp.Queue()

        self.record_video = RecordVideo(self.image_queue, self.info_queue, video=video)
        self.camera_widget = CameraWidget()
        self.face_recognition = FaceRecognition(self.image_queue, self.result_queue, db_conn)
        self.result_analysis = ResultAnalysis(self.result_queue, self.info_queue, db_conn)
        self.result_display_widget = ResultDisplayWidget(self.info_queue)
        self.strange_entry_widget = StrangerEntryWidget(pic_path, db_conn)

        self.run_button = QtWidgets.QPushButton('Start')
        self.stop_button = QtWidgets.QPushButton('Stop')
        self.exit_button = QtWidgets.QPushButton('Exit')

        self.record_video.image_signal.connect(self.camera_widget.image_slot)
        self.record_video.image_signal.connect(self.strange_entry_widget.image_slot)
        self.record_video.info_signal.connect(self.result_display_widget.info_slot)

        # Create and set the layout
        total_layout = QtWidgets.QHBoxLayout()
        manage_layout = QtWidgets.QVBoxLayout()
        control_layout = QtWidgets.QVBoxLayout()

        total_layout.addWidget(self.camera_widget)
        total_layout.addLayout(manage_layout)

        manage_layout.addWidget(self.result_display_widget)
        manage_layout.addWidget(self.strange_entry_widget)
        manage_layout.addLayout(control_layout)

        control_layout.addWidget(self.run_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.exit_button)

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



class MainWindow(QtWidgets.QMainWindow):
    '''
    @ Summary:
        The main window containging the main widget.
    '''
    def __init__(self, pic_path, db_conn, video=0):

        super().__init__()
        self.main_widget = MainWidget(pic_path, db_conn, video=video)
        self.setCentralWidget(self.main_widget)
        self.setWindowTitle('Face Detection & Recognition System')
        self.setWindowIcon(QtGui.QIcon('./img/icon.jpg'))
        self.show()



if __name__ == '__main__':
    db_conn = MySQLdb.connect(db='FDR')
    app = QtWidgets.QApplication(sys.argv)
    main_GUI = MainWindow('./pictures/', db_conn, video=0)
    sys.exit(app.exec_())
    db_conn.close()
