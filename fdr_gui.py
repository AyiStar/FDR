import os
import sys
import time
import cv2
import numpy as np
import face_recognition
from PyQt5 import QtWidgets, QtGui, QtCore
import fdr




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

    def __init__(self, video=0):
        super().__init__()

        self.camera = cv2.VideoCapture(video)
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

    #result_signal = QtCore.pyqtSignal(object)
    result_signal = QtCore.pyqtSignal(str, float)

    def __init__(self, data_path):

        super().__init__()
        self.known_faces = fdr.load_faces(data_path)
        self.face_recognition_thread = FaceRecognitionThread()

    def image_slot(self, image):
        self.face_recognition_thread.setup(image, self.known_faces)
        self.face_recognition_thread.matches_signal.connect(self.matches_slot)
        self.face_recognition_thread.start()

    def matches_slot(self, face_matches):
        if len(face_matches) > 0:
            self.result_signal.emit(face_matches[0][0], face_matches[0][1])



class FaceRecognitionThread(QtCore.QThread):

    matches_signal = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.image = None
        self.known_faces = None

    def run(self):
        face_matches = self.recognize_face(self.image)
        self.matches_signal.emit(face_matches)
        time.sleep(1)

    def setup(self, image, known_faces):
        self.image = image
        self.known_faces = known_faces

    def recognize_face(self, image):

        # Initialize some variables
        face_locations = []
        face_encodings = []
        face_names = []

        # Resize frame of video to 1/4 size for faster face recognition processing
        #small_image = cv2.resize(self.image, (0, 0), fx=0.25, fy=0.25)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_image = image[:, :, ::-1]

        # Find all the faces and face encodings in the current frame of video
        face_locations = face_recognition.face_locations(rgb_image)
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        face_matches = []

        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            distances = fdr.get_face_distances(self.known_faces, face_encoding)
            match = fdr.match_face(distances, 0.4)
            face_matches.append(match)


        # Display the results

        for (top, right, bottom, left), match in zip(face_locations, face_matches):

            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Draw a box around the face and a label with a name below the face
            '''
            if match[0] == 'Unknown':
                cv2.rectangle(image, (left, top), (right, bottom), (0, 0, 255), 1)
                cv2.putText(image, match[0]+':'+'%.2f'%(match[1]), (left, bottom+30), cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 0, 255), 1)
            else:
                cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 1)
                cv2.putText(image, match[0]+':'+'%.2f'%(match[1]), (left, bottom+30), cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 0), 1)
            '''

        return face_matches



class RecogitionResultWidget(QtWidgets.QWidget):
    '''
    @ Summary:
        On receiving the result signal emitted by FaceRecognitionWidget,
        this widget display the result.
    '''

    def __init__(self, pic_path):

        super().__init__()

        self.pic_path = pic_path

        self.img_label  = QtWidgets.QLabel()
        self.img_label.setPixmap(QtGui.QPixmap('./img/question.jpg').scaled(128, 128, QtCore.Qt.KeepAspectRatio))
        self.name_label = QtWidgets.QLabel('Name : --')
        self.dist_label = QtWidgets.QLabel('Distance: --')

        layout = QtWidgets.QVBoxLayout()

        layout.addWidget(self.img_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.dist_label)

        self.setLayout(layout)

    def result_slot(self, name : str, distance : float):

        pic_file_name = ''
        if name == 'Unknown':
            pic_file_name = './img/question.jpg'
        else:
            pic_full_path = self.pic_path + '/' + name + '/'
            pic_file_name = pic_full_path + os.listdir(pic_full_path)[0]

        name_text = 'Name : ' + name
        dist_text = 'Distance : %.3f' % distance

        self.img_label.setPixmap(QtGui.QPixmap(pic_file_name).scaled(128, 128, QtCore.Qt.KeepAspectRatio))
        self.name_label.setText(name_text)
        self.dist_label.setText(dist_text)



class StrangerEntryWidget(QtWidgets.QWidget):
    '''
    @ Summary:
        This widget record new faces in the camera,
        and also compute the feature vectors, and store them.
    '''
    def __init__(self, pic_path, data_path):

        super().__init__()

        self.pic_path = pic_path
        self.data_path = data_path
        self.image = None

        self.img_label  = QtWidgets.QLabel()
        self.img_label.setPixmap(QtGui.QPixmap('./img/dog.jpg').scaled(128, 128, QtCore.Qt.KeepAspectRatio))
        self.name_input = QtWidgets.QLineEdit('Your name')
        self.number_input = QtWidgets.QLineEdit('Positive Int')
        self.enter_button = QtWidgets.QPushButton('Enter New Data')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.img_label)
        layout.addWidget(self.name_input)
        layout.addWidget(self.number_input)
        layout.addWidget(self.enter_button)

        self.enter_button.clicked.connect(self.enter_stranger)

        self.setLayout(layout)

    def enter_stranger(self):
        name = self.name_input.text()
        num_pic = int(self.number_input.text())

        full_path = self.pic_path + '/' + name + '/'
        if not os.path.exists(full_path):
            os.mkdir(full_path)

        for n in range(num_pic):
            face = fdr.detect_face(self.image, full_path)
            if face is not None:
                self.img_label.setPixmap(QtGui.QPixmap(self.get_QImage(face)).scaled(128, 128, QtCore.Qt.KeepAspectRatio))
            #time.sleep(1)

        fdr.store_face(name, self.pic_path, self.data_path)


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
    def __init__(self, pic_path, data_path, video=0):

        super().__init__()

        self.camera_widget = CameraWidget()
        self.recognition_result_widget = RecogitionResultWidget(pic_path)
        self.strange_entry_widget = StrangerEntryWidget(pic_path, data_path)
        self.record_video = RecordVideo(video=video)
        self.face_recognition = FaceRecognition(data_path)
        self.run_button = QtWidgets.QPushButton('Start')
        self.stop_button = QtWidgets.QPushButton('Stop')
        self.exit_button = QtWidgets.QPushButton('Exit')

        self.record_video.image_signal.connect(self.camera_widget.image_slot)
        self.record_video.image_signal.connect(self.face_recognition.image_slot)
        self.record_video.image_signal.connect(self.strange_entry_widget.image_slot)
        self.face_recognition.result_signal.connect(self.recognition_result_widget.result_slot)

        # Create and set the layout
        total_layout = QtWidgets.QHBoxLayout()
        manage_layout = QtWidgets.QVBoxLayout()
        control_layout = QtWidgets.QVBoxLayout()

        total_layout.addWidget(self.camera_widget)
        total_layout.addLayout(manage_layout)

        manage_layout.addWidget(self.recognition_result_widget)
        manage_layout.addWidget(self.strange_entry_widget)
        manage_layout.addLayout(control_layout)

        control_layout.addWidget(self.run_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.exit_button)

        self.run_button.clicked.connect(self.record_video.start_recording)
        self.stop_button.clicked.connect(self.record_video.stop_recording)
        self.exit_button.clicked.connect(QtCore.QCoreApplication.quit)
        self.setLayout(total_layout)



class MainWindow(QtWidgets.QMainWindow):
    '''
    @ Summary:
        The main window containging the main widget.
    '''
    def __init__(self, pic_path, data_path, video=0):

        super().__init__()
        self.main_widget = MainWidget(pic_path, data_path, video=video)
        self.setCentralWidget(self.main_widget)
        self.setWindowTitle('Face Detection & Recognition System')
        self.setWindowIcon(QtGui.QIcon('./img/icon.jpg'))
        self.show()



if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main_GUI = MainWindow('./pictures/', './data/', video=0)
    sys.exit(app.exec_())
