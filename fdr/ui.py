import sys, os
import time
from datetime import datetime
import multiprocessing as mp
import threading
import json
import socket

from PyQt5 import QtWidgets, QtGui, QtCore
import qdarkstyle
import MySQLdb
import numpy as np
import cv2

import gui_utils
import audio_utils


'''
    Global Variables
'''
# used in network communication
MSG_ACC = False
RECV_DATA = ''
VOICE_SIG = False

# used in UPDATE
NEED_UPDATE = False

# used in status report
STATUS_INFO = ''

# used in weibo crawling
WEIBO_CRAWL_SIG = ''



class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, db_login, video):
        super().__init__()
        self.db_login = db_login

        # queues for IPC
        self.image_queue = mp.Queue()
        self.result_queue = mp.Queue()
        self.update_queue = mp.Queue()

        # socket
        self.socket_server = SocketServer()

        # timer
        self.status_timer = QtCore.QBasicTimer()
        self.status_timer.start(250, self)

        # status bar
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)

        # main widget
        self.main_widget = MainWidget(self.db_login)
        self.setCentralWidget(self.main_widget)
        self.setWindowTitle('社交小助手')
        self.setWindowIcon(QtGui.QIcon('./resources/icons/icon.jpg'))

        self.main_timer_widget = MainTimerWidget(video, self.image_queue, self.update_queue, self.result_queue)
        self.video_widget = VideoWidget()
        self.face_recognition = FaceRecognition(self.image_queue, self.result_queue, self.update_queue, self.db_login)
        self.audio_module = AudioModule(self.db_login)
        self.weibo_crawl = WeiboCrawl(self.db_login)
        # self.voice_wake = VoiceWake()

        self.main_timer_widget.update_signal.connect(self.main_widget.update_slot)
        self.main_timer_widget.update_signal.connect(self.face_recognition.update_slot)
        self.main_timer_widget.result_signal.connect(self.main_widget.result_slot)
        self.main_timer_widget.result_signal.connect(self.audio_module.result_slot)
        self.main_timer_widget.result_signal.connect(self.result_slot)
        self.main_timer_widget.voice_signal.connect(self.audio_module.voice_slot)
        self.main_timer_widget.weibo_crawl_signal.connect(self.weibo_crawl.weibo_crawl_slot)
        # self.voice_wake.hot_word_signal.connect(self.audio_module.hot_word_slot)

        self.face_recognition.start_recognizing()
        self.main_timer_widget.start_timing()
        # self.voice_wake.start_voice_wake()

        self.center()
        self.init_menu_bar()
        self.init_tool_bar()
        self.init_directory()

        global STATUS_INFO
        STATUS_INFO = '准备就绪'

    def center(self):
        # set center of screen
        frameGm = self.frameGeometry()
        screen = QtWidgets.QApplication.desktop().screenNumber(QtWidgets.QApplication.desktop().cursor().pos())
        centerPoint = QtWidgets.QApplication.desktop().screenGeometry(screen).center()
        # cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

    def init_menu_bar(self):
        self.menu_bar = self.menuBar()
        self.menu_bar.setNativeMenuBar(False)

        self.sort_menu = self.menu_bar.addMenu('&排序方式')
        self.sort_by_recent_meet_action = QtWidgets.QAction('按见面时间排序', self, checkable=True)
        self.sort_by_meet_times_action = QtWidgets.QAction('按见面次数排序', self, checkable=True)
        self.sort_by_name_action = QtWidgets.QAction('按姓名排序', self, checkable=True)
        self.sort_by_name_action.triggered.connect(self.on_sort_by_name_action)
        self.sort_by_meet_times_action.triggered.connect(self.on_sort_by_meet_times_action)
        self.sort_by_recent_meet_action.triggered.connect(self.on_sort_by_recent_meet_action)
        self.sort_by_recent_meet_action.setChecked(True)
        self.sort_menu.addAction(self.sort_by_recent_meet_action)
        self.sort_menu.addAction(self.sort_by_meet_times_action)
        self.sort_menu.addAction(self.sort_by_name_action)

        self.check_menu = self.menu_bar.addMenu('&查看方式')
        self.check_in_image_action = QtWidgets.QAction('图标查看', self, checkable=True)
        self.check_in_list_action = QtWidgets.QAction('列表查看', self, checkable=True)
        self.check_in_image_action.setChecked(True)
        self.check_menu.addAction(self.check_in_image_action)
        self.check_menu.addAction(self.check_in_list_action)

        self.help_menu = self.menu_bar.addMenu('&帮助')
        self.about_action = QtWidgets.QAction('关于', self)
        self.help_menu.addAction(self.about_action)

    def init_tool_bar(self):
        # exit action
        exitAct = QtWidgets.QAction(QtGui.QIcon('./resources/icons/exit.png'), '退出', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.triggered.connect(self.on_exit_action)

        # refresh action
        refreshAct = QtWidgets.QAction(QtGui.QIcon('./resources/icons/refresh.png'), '刷新', self)
        refreshAct.setShortcut('Ctrl+R')
        refreshAct.triggered.connect(self.on_refresh_action)

        # search action
        searchAct = QtWidgets.QAction(QtGui.QIcon('./resources/icons/search.png'), '搜索', self)
        searchAct.setShortcut('Ctrl+F')
        searchAct.triggered.connect(self.on_search_action)

        # network action
        networkAct = QtWidgets.QAction(QtGui.QIcon('./resources/icons/network.png'), '联网', self)
        networkAct.triggered.connect(self.on_network_action)

        # video action
        videoAct = QtWidgets.QAction(QtGui.QIcon('./resources/icons/video.png'), '视频', self)
        videoAct.triggered.connect(self.on_video_action)

        # start/stop action
        start_stopAct = QtWidgets.QAction(QtGui.QIcon('./resources/icons/start_stop.jpg'), '开始/暂停', self)
        start_stopAct.triggered.connect(self.on_start_stop_action)

        tool_bar = self.addToolBar('工具栏')
        tool_bar.addAction(start_stopAct)
        tool_bar.addAction(refreshAct)
        tool_bar.addAction(networkAct)
        tool_bar.addAction(videoAct)
        tool_bar.addAction(searchAct)
        tool_bar.addAction(exitAct)

    def init_directory(self):
        if not os.path.exists('./data'):
            os.mkdir('./data')
            os.mkdir('./data/photo')
            os.mkdir('./data/network')
            os.mkdir('./data/wordcloud')

    def timerEvent(self, event):
        global STATUS_INFO
        if (event.timerId() == self.status_timer.timerId()):
            self.status_bar.showMessage(str(STATUS_INFO))

    def on_video_action(self):
        if not self.video_widget.isVisible():
            self.main_timer_widget.image_signal.connect(self.video_widget.image_slot)
            self.video_widget.show()
        else:
            self.main_timer_widget.image_signal.disconnect(self.video_widget.image_slot)
            self.video_widget.hide()

    def on_network_action(self):
        global STATUS_INFO
        STATUS_INFO = '正在设置网络'
        ip, ip_ok = QtWidgets.QInputDialog.getText(self, '本机IP地址', '', text='192.168.1.101')
        if not ip_ok:
            return
        port, port_ok = QtWidgets.QInputDialog.getInt(self, '设置开放端口号', '', value=2333)
        if not port_ok:
            return
        self.socket_server.set_address(ip, port)
        self.socket_server.open_socket()

    def on_refresh_action(self):
        global NEED_UPDATE
        global STATUS_INFO
        NEED_UPDATE = True
        STATUS_INFO = '已刷新'

    def on_start_stop_action(self):
        self.main_timer_widget.isRecording = not self.main_timer_widget.isRecording

    def on_search_action(self):
        if not self.main_widget.get_search_mode():
            self.main_widget.set_search_mode(True)
        else:
            self.main_widget.set_search_mode(False)

    def on_exit_action(self):
        global STATUS_INFO
        STATUS_INFO = '正在退出'
        self.main_timer_widget.stop_timing()
        self.face_recognition.stop_recognizing()
        #self.voice_wake.stop_voice_wake()
        self.image_queue.close()
        self.update_queue.close()
        self.result_queue.close()
        time.sleep(0.5)
        QtWidgets.qApp.quit()

    def on_sort_by_name_action(self):
        self.sort_by_name_action.setChecked(True)
        self.sort_by_meet_times_action.setChecked(False)
        self.sort_by_recent_meet_action.setChecked(False)

    def on_sort_by_meet_times_action(self):
        self.sort_by_name_action.setChecked(False)
        self.sort_by_meet_times_action.setChecked(True)
        self.sort_by_recent_meet_action.setChecked(False)

    def on_sort_by_recent_meet_action(self):
        self.sort_by_name_action.setChecked(False)
        self.sort_by_meet_times_action.setChecked(False)
        self.sort_by_recent_meet_action.setChecked(True)

    def result_slot(self, result):
        global STATUS_INFO
        person_id_list = [r[0] for r in result if r[0]]
        person_name_list = []
        db_conn = MySQLdb.connect(user=self.db_login['user'], passwd=self.db_login['passwd'], db=self.db_login['db'])
        db_conn.set_character_set('utf8')
        cursor = db_conn.cursor()
        cursor.execute('SET NAMES utf8;')
        cursor.execute('SET CHARACTER SET utf8;')
        cursor.execute('SET character_set_connection=utf8;')
        for person_id in person_id_list:
            if cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (person_id,)) > 0:
                person_name = cursor.fetchone()[0]
                person_name_list.append(person_name if person_name != 'Unknown' else '陌生人')
        STATUS_INFO = '从左至右识别到: ' + ','.join(person_name_list)



class MainWidget(QtWidgets.QWidget):

    def __init__(self, db_login):
        super().__init__()

        self.layout = QtWidgets.QVBoxLayout()
        self.search_line_edit = QtWidgets.QLineEdit()
        self.search_line_edit.textChanged.connect(self.search_slot)
        self.person_list_tab_widget = PersonListTabWidget(db_login)
        self.layout.addWidget(self.search_line_edit)
        self.layout.addWidget(self.person_list_tab_widget)
        self.search_line_edit.hide()
        self.search_mode = False
        self.setLayout(self.layout)

    def get_search_mode(self):
        return self.search_mode

    def set_search_mode(self, enable):
        if enable:
            self.search_mode = True
            self.search_line_edit.show()
        else:
            self.search_mode = False
            self.search_line_edit.clear()
            self.search_line_edit.hide()

    def search_slot(self):
        search_text = self.search_line_edit.text()
        self.person_list_tab_widget.refresh(search_filter=search_text)

    def update_slot(self):
        self.person_list_tab_widget.refresh()

    def result_slot(self, result):
        person_id_list = [r[0] for r in result]
        self.person_list_tab_widget.twinkle(person_id_list)



class PersonListTabWidget(QtWidgets.QWidget):

    def __init__(self, db_login):
        super().__init__()
        self.layout = QtWidgets.QVBoxLayout()
        self.tabs = QtWidgets.QTabWidget()
        self.known_person_list_widget = PersonListWidget(db_login, known=True)
        self.unknown_person_list_widget = PersonListWidget(db_login, known=False)
        self.known_person_list_scroll_area = QtWidgets.QScrollArea()
        self.known_person_list_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.known_person_list_scroll_area.setWidget(self.known_person_list_widget)
        self.known_person_list_scroll_area.setMinimumWidth(self.known_person_list_widget.sizeHint().width())
        self.unknown_person_list_scroll_area = QtWidgets.QScrollArea()
        self.unknown_person_list_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.unknown_person_list_scroll_area.setWidget(self.unknown_person_list_widget)
        self.unknown_person_list_scroll_area.setMinimumWidth(self.unknown_person_list_widget.sizeHint().width())
        self.tabs.addTab(self.known_person_list_scroll_area, '认识的人')
        self.tabs.addTab(self.unknown_person_list_scroll_area, '陌生人')
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)


    def refresh(self, search_filter=''):
        self.known_person_list_widget.refresh(search_filter=search_filter)
        self.unknown_person_list_widget.refresh(search_filter=search_filter)

    def twinkle(self, person_id_list):
        self.known_person_list_widget.twinkle(person_id_list)
        self.unknown_person_list_widget.twinkle(person_id_list)



class PersonListWidget(QtWidgets.QWidget):

    def __init__(self, db_login, known):
        super().__init__()
        self.db_login = db_login
        self.known = known
        self.person_display_widgets = {}
        self.layout = QtWidgets.QGridLayout()
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.setMinimumWidth(600)
        self.refresh()
        self.setLayout(self.layout)

    def refresh(self, search_filter=''):
        db_conn = MySQLdb.connect(user=self.db_login['user'], passwd=self.db_login['passwd'], db=self.db_login['db'])
        db_conn.set_character_set('utf8')
        cursor = db_conn.cursor()
        cursor.execute('SET NAMES utf8;')
        cursor.execute('SET CHARACTER SET utf8;')
        cursor.execute('SET character_set_connection=utf8;')
        if self.known:
            pattern = search_filter.replace('', '%')
            cursor.execute('SELECT person_ID FROM Persons WHERE name!=%s AND name LIKE %s ORDER BY last_meet_time DESC', ('Unknown', pattern))
        else:
            cursor.execute('SELECT person_ID FROM Persons WHERE name=%s ORDER BY last_meet_time DESC', ('Unknown',))
        person_ids = [x[0] for x in cursor.fetchall()]

        # clear the layout
        self.person_display_widgets = {}
        for i in reversed(range(self.layout.count())):
            self.layout.itemAt(i).widget().setParent(None)

        for i, person_id in enumerate(person_ids):
            self.person_display_widgets[person_id] = PersonDisplayWidget(self.db_login, person_id)
            self.layout.addWidget(self.person_display_widgets[person_id], i//3, i%3)

        db_conn.close()

    def twinkle(self, person_id_list):
        for person_id in self.person_display_widgets:
            if person_id in person_id_list:
                self.person_display_widgets[person_id].setTwinkle(True)
            else:
                self.person_display_widgets[person_id].setTwinkle(False)


    def update_slot(self):
        self.refresh()



class PersonDisplayWidget(QtWidgets.QWidget):

    def __init__(self, db_login, person_id):
        super().__init__()
        self.db_login = db_login
        self.person_id = person_id
        self.setFixedWidth(240)

        db_conn = MySQLdb.connect(user=db_login['user'], passwd=db_login['passwd'], db=db_login['db'])
        db_conn.set_character_set('utf8')
        cursor = db_conn.cursor()
        cursor.execute('SET NAMES utf8;')
        cursor.execute('SET CHARACTER SET utf8;')
        cursor.execute('SET character_set_connection=utf8;')

        cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (person_id,))
        self.name = cursor.fetchone()[0]
        cursor.execute('SELECT meet_time, meet_place FROM Meets WHERE person_ID=%s ORDER BY meet_time DESC', (person_id,))
        meet_results = cursor.fetchall()
        self.last_meet_time = meet_results[0][0].strftime('%Y年%m月%d日%H时%M分')
        self.last_meet_place = meet_results[0][1]
        self.meet_times = len(meet_results)

        # button
        self.button = QtWidgets.QPushButton()
        self.button.setFixedSize(QtCore.QSize(200, 150))
        if os.path.exists('./data/photo/' + person_id + '.jpg'):
            self.button.setIcon(QtGui.QIcon('./data/photo/' + person_id + '.jpg'))
        else:
            self.button.setIcon(QtGui.QIcon('./resources/icons/question.jpg'))
        self.button.setIconSize(QtCore.QSize(200, 150))
        self.button.clicked.connect(self.on_check_action)


        self.check_widget = None
        self.alter_widget = None
        self.amend_widget = None

        # button tips
        btn_tips = ''.join(['总见面次数: ', str(self.meet_times), '\n',
                            '最近见面时间: ', self.last_meet_time, '\n',
                            '最近见面地点: ', self.last_meet_place])
        self.button.setToolTip(btn_tips)

        # button frame effect
        self.effect = QtWidgets.QGraphicsDropShadowEffect(self.button)
        self.effect.setColor(QtGui.QColor(87, 250, 255))
        self.effect.setOffset(0, 0)
        self.effect.setBlurRadius(30)
        self.button.setGraphicsEffect(self.effect)
        self.effect.setEnabled(False)

        # twinkle timer
        self.twinkle_timer = QtCore.QBasicTimer()
        # communication timer
        self.commu_timer = QtCore.QBasicTimer()
        # alter info dict
        self.alter_info = {}

        # label
        label = QtWidgets.QLabel(self.name)

        # context menu
        self.context_menu = QtWidgets.QMenu(self)
        self.check_action = self.context_menu.addAction('&查看')
        self.alter_action = self.context_menu.addAction('&修改')
        self.delete_action = self.context_menu.addAction('&删除')
        self.amend_action = self.context_menu.addAction('&修正')
        self.check_action.triggered.connect(self.on_check_action)
        self.alter_action.triggered.connect(self.on_alter_action)
        self.delete_action.triggered.connect(self.on_delete_action)
        self.amend_action.triggered.connect(self.on_amend_action)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda: self.context_menu.exec_(QtGui.QCursor.pos()))

        # set layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(self.button)
        self.layout.addWidget(label)
        self.setLayout(self.layout)

        db_conn.close()

    def setTwinkle(self, enable):
        if enable and not self.twinkle_timer.isActive():
            self.twinkle_timer.start(500, self)
        if not enable and self.twinkle_timer.isActive():
            self.twinkle_timer.stop()
            self.effect.setEnabled(False)

    def timerEvent(self, event):
        if (event.timerId() == self.twinkle_timer.timerId()):
            if self.effect.isEnabled():
                self.effect.setEnabled(False)
            else:
                self.effect.setEnabled(True)
        elif (event.timerId() == self.commu_timer.timerId()):
            global MSG_ACC
            global RECV_DATA
            global STATUS_INFO

            if MSG_ACC:
                STATUS_INFO = '成功获取输入'
                # process json
                self.alter_info = json.loads(RECV_DATA)
                display_info = ['获取输入信息如下\n']
                if 'name' in self.alter_info:
                    display_info.extend(['姓名: ', self.alter_info['name'], '\n'])
                if 'weibo' in self.alter_info:
                    display_info.extend(['微博昵称: ', self.alter_info['weibo'], '\n'])
                if 'relationship' in self.alter_info:
                    display_info.extend(['关系:\n'])
                    for i, relation in self.alter_info['relationship']:
                        if not relation['namea']:
                            display_info.extend([str(i), ': ', 'TA是', relation['nameb'], '的', relation['rel'], '\n'])
                        elif not relation['nameb']:
                            display_info.extend([str(i), ': ', relation['namea'], '是TA的', relation['rel'], '\n'])
                        else:
                            display_info.extend([str(i), ': 输入错误\n'])
                display_info.append('是否确认修改?')
                self.alter_widget.get_alter_info(''.join(display_info))
                MSG_ACC = False

    def on_check_action(self):
        self.check_widget = PersonCheckWidget(self.db_login, self.person_id)
        self.check_widget.show()

    def on_alter_action(self):
        global MSG_ACC
        global NEED_UPDATE
        global STATUS_INFO

        MSG_ACC = False
        self.commu_timer.start(200, self)

        self.alter_widget = PersonAlterWidget()
        self.alter_widget.wait_for_info()
        self.alter_widget.exec_()

        if self.alter_widget.clickedButton() == self.alter_widget.button(QtWidgets.QMessageBox.No):
            STATUS_INFO = '取消信息修改'
        else:
            alter_result = gui_utils.alter_person(self.db_login, self.person_id, self.alter_info)
            if alter_result:
                STATUS_INFO = '信息修改失败: ' + alter_result
            else:
                STATUS_INFO = '信息修改成功'
            NEED_UPDATE = True
        self.commu_timer.stop()

    def on_delete_action(self):
        global NEED_UPDATE
        global STATUS_INFO
        confirm_msg = ''.join(['确认要删除', self.name, '吗?'])
        reply = QtWidgets.QMessageBox.question(self, 'Message', confirm_msg,
                                                QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:

            gui_utils.delete_person(self.db_login, self.person_id)
            STATUS_INFO = '删除成功'
            NEED_UPDATE = True
        else:
            STATUS_INFO = '取消删除'


    def on_amend_action(self):
        self.amend_widget = PersonAmendWidget(self.db_login, self.person_id)
        self.amend_widget.show()



class PersonCheckWidget(QtWidgets.QWidget):

    def __init__(self, db_login, person_id):
        super().__init__()
        self.setWindowTitle('信息查看')
        self.layout = QtWidgets.QVBoxLayout()
        self.tabs = QtWidgets.QTabWidget()
        self.base_info_widget = self.BaseInfoWidget(db_login, person_id)
        self.weibo_info_widget = self.WeiboInfoWidget(db_login, person_id)
        self.network_info_widget = self.NetworkInfoWidget(db_login, person_id)
        self.tabs.addTab(self.base_info_widget, '基本信息')
        self.tabs.addTab(self.weibo_info_widget, '兴趣分析')
        self.tabs.addTab(self.network_info_widget, '关系网络')
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    class BaseInfoWidget(QtWidgets.QWidget):

        def __init__(self, db_login, person_id):
            super().__init__()
            self.db_login = db_login
            db_conn = MySQLdb.connect(user=self.db_login['user'], passwd=self.db_login['passwd'], db=self.db_login['db'])
            db_conn.set_character_set('utf8')
            cursor = db_conn.cursor()
            # cursor.execute('SET NAMES utf8;')
            # cursor.execute('SET CHARACTER SET utf8;')
            # cursor.execute('SET character_set_connection=utf8;')
            cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (person_id,))
            name = cursor.fetchone()[0]
            cursor.execute('SELECT meet_time, meet_place FROM Meets WHERE person_ID=%s ORDER BY meet_time DESC', (person_id,))
            meets = cursor.fetchall()


            self.photo_label = QtWidgets.QLabel()
            if os.path.exists('./data/photo/' + person_id + '.jpg'):
                self.photo_label.setPixmap(QtGui.QPixmap('./data/photo/' + person_id + '.jpg').scaled(360, 360, QtCore.Qt.KeepAspectRatio))
            else:
                self.photo_label.setPixmap(QtGui.QPixmap('./resources/icons/question.jpg').scaled(360, 360, QtCore.Qt.KeepAspectRatio))

            self.name_label = QtWidgets.QLabel(''.join(['姓名: ', name]))
            self.last_meet_time_label = QtWidgets.QLabel(''.join(['最近见面时间: ', meets[0][0].strftime('%Y年%m月%d日%H时%M分')]))
            self.last_meet_place_label = QtWidgets.QLabel(''.join(['最近见面地点: ', meets[0][1]]))
            self.more_button = QtWidgets.QPushButton('详细信息')
            self.more_button.clicked.connect(lambda: self.more_table.hide() if self.more_table.isVisible() else self.more_table.show())

            self.more_table = QtWidgets.QTableWidget()
            self.more_table.setRowCount(len(meets))
            self.more_table.setColumnCount(2)
            self.more_table.verticalHeader().setVisible(False)
            self.more_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
            self.more_table.setHorizontalHeaderLabels(['见面时间', '见面地点'])
            self.more_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
            self.more_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
            self.more_table.setMinimumHeight(200)
            self.more_table.hide()
            for i, meet in enumerate(meets):
                self.more_table.setItem(i, 0, QtWidgets.QTableWidgetItem(meet[0].strftime('%Y年%m月%d日%H时%M分')))
                self.more_table.setItem(i, 1, QtWidgets.QTableWidgetItem(meet[1]))


            self.info_layout = QtWidgets.QVBoxLayout()
            self.info_layout.addStretch(0)
            self.info_layout.addWidget(self.name_label)
            self.info_layout.addWidget(self.last_meet_time_label)
            self.info_layout.addWidget(self.last_meet_place_label)
            self.info_layout.addWidget(self.more_button)
            self.info_layout.addStretch(0)

            self.base_layout = QtWidgets.QHBoxLayout()
            self.base_layout.addWidget(self.photo_label)
            self.base_layout.addLayout(self.info_layout)

            self.layout = QtWidgets.QVBoxLayout()
            self.layout.addLayout(self.base_layout)
            self.layout.addWidget(self.more_table)
            self.setLayout(self.layout)

    class WeiboInfoWidget(QtWidgets.QWidget):

        def __init__(self, db_login, person_id):
            super().__init__()
            global WEIBO_CRAWL_SIG
            self.db_login = db_login
            db_conn = MySQLdb.connect(user=self.db_login['user'], passwd=self.db_login['passwd'], db=self.db_login['db'])
            db_conn.set_character_set('utf8')
            cursor = db_conn.cursor()
            weibo_name = 'None'
            self.weibo_uid = 'None'
            if cursor.execute('SELECT weibo_name, weibo_uid FROM WeiboAccounts WHERE person_ID=%s', (person_id,)) > 0:
                weibo_name, self.weibo_uid = cursor.fetchone()
            cursor.execute('SELECT post_time, tweet, forwarding FROM Weibos WHERE user_ID=%s', (self.weibo_uid,))
            tweets = cursor.fetchall()

            self.word_cloud_label = QtWidgets.QLabel()
            if os.path.exists('./data/wordcloud/' + self.weibo_uid + '.jpg'):
                self.word_cloud_label.setPixmap(QtGui.QPixmap('./data/wordcloud/' + self.weibo_uid + '.jpg').scaled(360, 360, QtCore.Qt.KeepAspectRatio))
            else:
                self.word_cloud_label.setPixmap(QtGui.QPixmap('./resources/icons/person.png').scaled(360, 360, QtCore.Qt.KeepAspectRatio))

            self.weibo_name_label = QtWidgets.QLabel(''.join(['微博昵称: ', weibo_name]))
            self.crawl_button = QtWidgets.QPushButton('获取数据')
            self.crawl_button.clicked.connect(self.on_crawl_button)
            self.more_button = QtWidgets.QPushButton('详细信息')
            self.more_button.clicked.connect(lambda: self.more_table.hide() if self.more_table.isVisible() else self.more_table.show())

            if weibo_name == 'None':
                self.crawl_button.setEnabled(False)
                self.more_button.setEnabled(False)
            elif len(tweets) == 0:
                self.crawl_button.setEnabled(True)
                self.more_button.setEnabled(False)
            else:
                self.crawl_button.setEnabled(False)
                self.more_button.setEnabled(True)

            self.more_table = QtWidgets.QTableWidget()
            self.more_table.setRowCount(len(tweets))
            self.more_table.setColumnCount(2)
            self.more_table.verticalHeader().setVisible(False)
            self.more_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
            self.more_table.setHorizontalHeaderLabels(['发布时间', '微博内容'])
            self.more_table.horizontalHeaderItem(0).setTextAlignment(QtCore.Qt.AlignLeft)
            self.more_table.horizontalHeaderItem(1).setTextAlignment(QtCore.Qt.AlignLeft)
            self.more_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
            self.more_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
            self.more_table.setMinimumHeight(200)
            self.more_table.hide()
            for i, tweet in enumerate(tweets):
                self.more_table.setItem(i, 0, QtWidgets.QTableWidgetItem(tweet[0]))
                self.more_table.setItem(i, 1, QtWidgets.QTableWidgetItem(tweet[1] if len(tweet[1]) > 0 else len(tweet[2])))


            self.info_layout = QtWidgets.QVBoxLayout()
            self.info_layout.addStretch(0)
            self.info_layout.addWidget(self.weibo_name_label)
            self.info_layout.addWidget(self.crawl_button)
            self.info_layout.addWidget(self.more_button)
            self.info_layout.addStretch(0)

            self.base_layout = QtWidgets.QHBoxLayout()
            self.base_layout.addWidget(self.word_cloud_label)
            self.base_layout.addLayout(self.info_layout)

            self.layout = QtWidgets.QVBoxLayout()
            self.layout.addLayout(self.base_layout)
            self.layout.addWidget(self.more_table)
            self.setLayout(self.layout)

        def on_crawl_button(self):
            global WEIBO_CRAWL_SIG
            WEIBO_CRAWL_SIG = self.weibo_uid

    class NetworkInfoWidget(QtWidgets.QWidget):

        def __init__(self, db_login, person_id):
            super().__init__()
            self.db_login = db_login
            db_conn = MySQLdb.connect(user=self.db_login['user'], passwd=self.db_login['passwd'], db=self.db_login['db'])
            db_conn.set_character_set('utf8')
            cursor = db_conn.cursor()
            cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (person_id,))
            person_name = cursor.fetchone()[0]
            cursor.execute('SELECT relation_type, person2_ID FROM Relations WHERE person1_ID=%s', (person_id,))
            result_1 = cursor.fetchall()
            cursor.execute('SELECT relation_type, person1_ID FROM Relations WHERE person2_ID=%s', (person_id,))
            result_2 = cursor.fetchall()

            self.layout = QtWidgets.QHBoxLayout()

            self.network_label = QtWidgets.QLabel()
            if os.path.exists('./data/network/' + person_id + '.jpg'):
                self.network_label.setPixmap(QtGui.QPixmap('./data/network/' + person_id + '.jpg').scaled(360, 360, QtCore.Qt.KeepAspectRatio))
            else:
                self.network_label.setPixmap(QtGui.QPixmap('./resources/icons/social_network.jpg').scaled(360, 360, QtCore.Qt.KeepAspectRatio))

            self.relation_table = QtWidgets.QTableWidget()
            self.relation_table.setColumnCount(1)
            self.relation_table.setRowCount(len(result_1) + len(result_2))
            self.relation_table.verticalHeader().setVisible(False)
            self.relation_table.setHorizontalHeaderLabels(['文字描述'])
            self.relation_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
            self.relation_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
            self.relation_table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
            for i, (relation_type, person2_id) in enumerate(result_1):
                cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (person2_id,))
                person2_name = cursor.fetchone()[0]
                self.relation_table.setItem(i, 0, QtWidgets.QTableWidgetItem(''.join([person_name, '是', person2_name, '的', relation_type])))
            for i, (relation_type, person1_id) in enumerate(result_2):
                cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (person1_id,))
                person1_name = cursor.fetchone()[0]
                self.relation_table.setItem(len(result_1) + i, 0, QtWidgets.QTableWidgetItem(''.join([person1_name, '是', person_name, '的', relation_type])))


            self.layout.addWidget(self.network_label)
            self.layout.addWidget(self.relation_table)
            self.setLayout(self.layout)



class PersonAlterWidget(QtWidgets.QMessageBox):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('信息修改')


    def wait_for_info(self):
        self.setText('等待信息输入...')
        self.setStandardButtons(QtWidgets.QMessageBox.No)
        btn_no = self.button(QtWidgets.QMessageBox.No)
        btn_no.setText('取消')

    def get_alter_info(self, info):
        self.setText(info)
        self.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        btn_yes = self.button(QtWidgets.QMessageBox.Yes)
        btn_yes.setText('确认')
        btn_no = self.button(QtWidgets.QMessageBox.No)
        btn_no.setText('取消')



class PersonAmendWidget(QtWidgets.QWidget):

    def __init__(self, db_login, person_id):
        super().__init__()
        self.setWindowTitle('信息修正')
        self.db_login = db_login
        self.person_id = person_id
        self.tip_label = QtWidgets.QLabel('请选择要修正的人,或点击下方按钮取消')
        self.cancel_button = QtWidgets.QPushButton('取消')
        self.cancel_button.clicked.connect(self.close)
        self.list_layout = QtWidgets.QGridLayout()
        self.list_layout.setAlignment(QtCore.Qt.AlignTop)
        self.person_amend_display_widgets = {}

        # refresh
        db_conn = MySQLdb.connect(user=self.db_login['user'], passwd=self.db_login['passwd'], db=self.db_login['db'])
        db_conn.set_character_set('utf8')
        cursor = db_conn.cursor()
        cursor.execute('SET NAMES utf8;')
        cursor.execute('SET CHARACTER SET utf8;')
        cursor.execute('SET character_set_connection=utf8;')
        cursor.execute('SELECT person_ID FROM Persons WHERE name!=%s ORDER BY last_meet_time DESC', ('Unknown', ))
        person_ids = [x[0] for x in cursor.fetchall()]

        for i, person_id in enumerate(person_ids):
            self.person_amend_display_widgets[person_id] = self.PersonAmendDisplayWidget(self.db_login, person_id, self.person_id, self)
            self.list_layout.addWidget(self.person_amend_display_widgets[person_id], i//3, i%3)

        db_conn.close()

        # set layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.tip_label)
        self.layout.addLayout(self.list_layout)
        self.layout.addWidget(self.cancel_button)
        self.setLayout(self.layout)

    class PersonAmendDisplayWidget(QtWidgets.QWidget):
        def __init__(self, db_login, person_id, amending_id, parent):
            super().__init__()
            self.db_login = db_login
            self.person_id = person_id
            self.amending_id = amending_id
            self.parent = parent
            self.setFixedWidth(240)

            db_conn = MySQLdb.connect(user=db_login['user'], passwd=db_login['passwd'], db=db_login['db'])
            db_conn.set_character_set('utf8')
            cursor = db_conn.cursor()
            cursor.execute('SET NAMES utf8;')
            cursor.execute('SET CHARACTER SET utf8;')
            cursor.execute('SET character_set_connection=utf8;')

            cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (person_id,))
            self.name = cursor.fetchone()[0]
            cursor.execute('SELECT meet_time, meet_place FROM Meets WHERE person_ID=%s ORDER BY meet_time DESC', (person_id,))
            meet_results = cursor.fetchall()
            self.last_meet_time = meet_results[0][0].strftime('%Y年%m月%d日%H时%M分')
            self.last_meet_place = meet_results[0][1]
            self.meet_times = len(meet_results)

            # button
            self.button = QtWidgets.QPushButton()
            self.button.setFixedSize(QtCore.QSize(200, 150))
            if os.path.exists('./data/photo/' + person_id + '.jpg'):
                self.button.setIcon(QtGui.QIcon('./data/photo/' + person_id + '.jpg'))
            else:
                self.button.setIcon(QtGui.QIcon('./resources/icons/question.jpg'))
            self.button.setIconSize(QtCore.QSize(200, 150))
            self.button.clicked.connect(self.on_button_clicked)

            # button tips
            btn_tips = ''.join(['总见面次数: ', str(self.meet_times), '\n',
                                '最近见面时间: ', self.last_meet_time, '\n',
                                '最近见面地点: ', self.last_meet_place])
            self.button.setToolTip(btn_tips)

            # label
            label = QtWidgets.QLabel(self.name)

            # set layout
            self.layout = QtWidgets.QVBoxLayout()
            self.layout.setAlignment(QtCore.Qt.AlignCenter)
            self.layout.addWidget(self.button)
            self.layout.addWidget(label)
            self.setLayout(self.layout)

            db_conn.close()


        def on_button_clicked(self):
            confirm_msg = ''.join(['确认要修正为', self.name, '吗?'])
            reply = QtWidgets.QMessageBox.question(self, '', confirm_msg,
                                                    QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                global NEED_UPDATE
                global STATUS_INFO
                # amend self.amending_id to self.person_id
                db_conn = MySQLdb.connect(user=self.db_login['user'], passwd=self.db_login['passwd'], db=self.db_login['db'])
                db_conn.set_character_set('utf8')
                cursor = db_conn.cursor()
                cursor.execute('SET NAMES utf8;')
                cursor.execute('SET CHARACTER SET utf8;')
                cursor.execute('SET character_set_connection=utf8;')
                cursor.execute('UPDATE Vectors SET person_ID=%s WHERE person_ID=%s', (self.person_id, self.amending_id))
                cursor.execute('UPDATE Meets SET person_ID=%s WHERE person_ID=%s', (self.person_id, self.amending_id))
                cursor.execute('UPDATE WeiboAccounts SET person_ID=%s WHERE person_ID=%s', (self.person_id, self.amending_id))
                cursor.execute('UPDATE Relations SET person1_ID=%s WHERE person1_ID=%s', (self.person_id, self.amending_id))
                cursor.execute('UPDATE Relations SET person2_ID=%s WHERE person2_ID=%s', (self.person_id, self.amending_id))
                cursor.execute('DELETE FROM Persons WHERE person_ID=%s', (self.amending_id,))
                db_conn.commit()
                db_conn.close()
                NEED_UPDATE = True
                STATUS_INFO = '修正完成'
                self.parent.close()
            else:
                pass



class MainTimerWidget(QtWidgets.QWidget):

    image_signal = QtCore.pyqtSignal(np.ndarray)
    result_signal = QtCore.pyqtSignal(object)
    update_signal = QtCore.pyqtSignal()
    voice_signal = QtCore.pyqtSignal()
    weibo_crawl_signal = QtCore.pyqtSignal(str)

    def __init__(self, video, image_queue, update_queue, result_queue):
        super().__init__()
        self.timer = QtCore.QBasicTimer()
        self.camera = cv2.VideoCapture(video)
        self.image_queue = image_queue
        self.update_queue = update_queue
        self.result_queue = result_queue
        self.isRecording = False

    def start_timing(self):
        self.timer.start(0, self)

    def stop_timing(self):
        self.timer.stop()

    def timerEvent(self, event):
        if (event.timerId() != self.timer.timerId()):
            return

        if self.isRecording:
            read, image = self.camera.read()
            if read:
                self.image_signal.emit(image)
                if self.image_queue.empty():
                    self.image_queue.put(image)

        if not self.update_queue.empty():
            self.update_queue.get()
            self.update_signal.emit()

        global NEED_UPDATE
        if NEED_UPDATE:
            self.update_signal.emit()
            NEED_UPDATE = False

        if not self.result_queue.empty():
            result = self.result_queue.get()
            self.result_signal.emit(result)

        global VOICE_SIG
        if VOICE_SIG:
            self.voice_signal.emit()
            VOICE_SIG = False

        global WEIBO_CRAWL_SIG
        if WEIBO_CRAWL_SIG:
            self.weibo_crawl_signal.emit(WEIBO_CRAWL_SIG)
            WEIBO_CRAWL_SIG = ''



class VideoWidget(QtWidgets.QWidget):

    def __init__(self, width=640, height=480):
        super().__init__()
        self.image = QtGui.QImage('./resources/icons/pig.jpg')
        self.setFixedSize(width, height)
        self.setWindowTitle('摄像头实时画面')

    def image_slot(self, frame):
        self.image = gui_utils.get_QImage(frame)
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawImage(0, 0, self.image)
        self.image = QtGui.QImage()



class FaceRecognition(QtCore.QObject):

    def __init__(self, image_queue, result_queue, update_queue, db_login, tolerance=0.4):

        super().__init__()
        self.db = db_login['db']
        self.user = db_login['user']
        self.passwd = db_login['passwd']
        self.tolerance = tolerance
        self.image_queue = image_queue
        self.result_queue = result_queue
        self.update_queue = update_queue
        self.update_queue_in = mp.Queue()
        self.process = None

    def start_recognizing(self):
        self.process = mp.Process(target=gui_utils.recognize_face_process,
                                  args=(self.image_queue, self.result_queue, self.update_queue, self.update_queue_in, self.db, self.user, self.passwd, self.tolerance))
        self.process.start()

    def stop_recognizing(self):
        if self.process is not None:
            self.process.terminate()
        # while not self.result_queue.empty():
        #     self.result_queue.get()
        # while not self.update_queue.empty():
        #     self.update_queue.get()
        # while not self.update_queue_in.empty():
        #     self.update_queue_in.get()
        self.update_queue_in.close()

    def update_slot(self):
        self.update_queue_in.put(0)



class SocketServer(QtCore.QObject):

    def __init__(self):
        super().__init__()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = None
        self.timer = QtCore.QBasicTimer()
        self.clientAddrList = []

    def __del__(self):
        self.sock.close()

    def set_address(self, ip, port):
        self.addr = (ip, port)

    def open_socket(self):
        global STATUS_INFO
        self.sock.bind(self.addr)
        self.sock.listen(10)
        self.sock.setblocking(False)
        STATUS_INFO = '[网络设置成功]' + str(self.addr[0]) + ':' + str(self.addr[1])
        self.timer.start(200, self)

    def timerEvent(self, event):

        global MSG_ACC
        global RECV_DATA
        global VOICE_SIG

        if (event.timerId() != self.timer.timerId()):
            return
        try:
            clientSocket, clientAddr = self.sock.accept()
        except:
            pass
        else:
            global STATUS_INFO
            STATUS_INFO = '建立新的网络连接'
            clientSocket.setblocking(False)
            self.clientAddrList.append((clientSocket, clientAddr))
        for clientSocket, clientAddr in self.clientAddrList:
            try:
                RECV_DATA = clientSocket.recv(1024).decode("utf-8")
            except:
                pass
            else:
                if len(RECV_DATA)>0:
                    # print(RECV_DATA)
                    if RECV_DATA == 'voice':
                        VOICE_SIG = True
                        # print('语音播放')
                        return
                    MSG_ACC = True



class AudioModule(QtCore.QObject):

    def __init__(self, db_login):
        super().__init__()
        self.db_login = db_login
        self.speech_robot = audio_utils.SpeechRobot()
        self.result = None

    def result_slot(self, result):
        self.result = result

    def voice_slot(self):
        db_conn = MySQLdb.connect(user=self.db_login['user'], passwd=self.db_login['passwd'], db=self.db_login['db'])
        db_conn.set_character_set('utf8')
        cursor = db_conn.cursor()
        cursor.execute('SET NAMES utf8;')
        cursor.execute('SET CHARACTER SET utf8;')
        cursor.execute('SET character_set_connection=utf8;')
        person_id_list = [r[0] for r in self.result]
        speech_content = []

        if len(person_id_list) == 1:
            speech_content.append('在您面前的是')
        else:
            speech_content.append('一共识别到' + str(len(person_id_list)) + '人')
            speech_content.append('按从左至右顺序')
        for i, person_id in enumerate(person_id_list):
            if len(person_id_list) > 1:
                speech_content.append('第' + str(i+1) + '位')
            # name
            if cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (person_id,)) > 0:
                name = cursor.fetchone()[0]
                speech_content.append(name if name != 'Unknown' else '陌生人')
            else:
                speech_content.append('陌生人')
            # relations
            cursor.execute('SELECT person1_ID, person2_ID, relation_type FROM Relations \
                            WHERE person1_ID=%s OR person2_ID=%s', (person_id, person_id,))
            relations = cursor.fetchall()[:3]
            for relation in relations:
                if relation[0] == person_id:
                    cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (relation[1],))
                    person2_name = cursor.fetchone()[0]
                    speech_content.append('他是' + person2_name + '的' + relation[2])
                else:
                    cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (relation[0],))
                    person1_name = cursor.fetchone()[0]
                    speech_content.append(person1_name + '是他的' + relation[2])
            # TODO weibos

        # print(','.join(speech_content))
        speech_thread = threading.Thread(target=self.speech_robot.say, args=(','.join(speech_content),))
        speech_thread.start()

    def hot_word_slot(self, hot_word):
        if hot_word == '豆豆':
            self.speech_robot.say('你好,我是豆豆')



class WeiboCrawl(QtCore.QObject):

    def __init__(self, db_login):
        super().__init__()
        self.db_login = db_login
        self.timer = QtCore.QBasicTimer()
        self.progress_queue = None
        self.progress_widget = None
        self.weibo_crawl_process = None

    def start_crawl_weibo(self, uid):
        db_conn = MySQLdb.connect(user=self.db_login['user'], passwd=self.db_login['passwd'], db=self.db_login['db'])
        db_conn.set_character_set('utf8')
        cursor = db_conn.cursor()
        cursor.execute('SET NAMES utf8;')
        cursor.execute('SET CHARACTER SET utf8;')
        cursor.execute('SET character_set_connection=utf8;')
        cursor.execute('SELECT weibo_name FROM WeiboAccounts WHERE weibo_uid=%s', (uid,))
        self.weibo_name = cursor.fetchone()[0]
        self.progress_queue = mp.Queue()
        self.progress_widget = self.ProgressWidget(self.weibo_name)
        self.progress_widget.show()
        self.weibo_crawl_process = mp.Process(target=gui_utils.weibo_crawl_process, args=(self.db_login, uid, self.progress_queue,))
        self.weibo_crawl_process.start()
        self.timer.start(100, self)

    def timerEvent(self, event):
        global STATUS_INFO
        if (event.timerId() != self.timer.timerId()):
            return
        if self.progress_queue is not None and not self.progress_queue.empty():
            now, total = self.progress_queue.get()
            self.progress_widget.set_progress((now / total)*100)
        if not self.weibo_crawl_process.is_alive():
            self.timer.stop()
            self.progress_widget.close()
            self.progress_queue.close()
            self.progress_widget = None
            self.progress_queue = None
            self.weibo_crawl_process = None
            STATUS_INFO = '微博' + self.weibo_name + '获取完成'

    def weibo_crawl_slot(self, uid):
        self.start_crawl_weibo(uid)

    class ProgressWidget(QtWidgets.QWidget):

        def __init__(self, weibo_name):
            super().__init__()
            self.setWindowTitle('正在爬取微博')
            self.weibo_name_label = QtWidgets.QLabel('微博名: ' + weibo_name)
            self.progress_bar = QtWidgets.QProgressBar()
            self.progress_bar.setValue(0)
            self.layout = QtWidgets.QVBoxLayout()
            self.layout.addWidget(self.weibo_name_label)
            self.layout.addWidget(self.progress_bar)
            self.setLayout(self.layout)

        def set_progress(self, value):
            self.progress_bar.setValue(value)



class VoiceWake(QtCore.QObject):

    hot_word_signal = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.signal_queue = None
        self.timer = QtCore.QBasicTimer()
        self.wake_up_detecter = None

    def start_voice_wake(self):
        self.signal_queue = mp.Queue()
        self.wake_up_detecter = mp.Process(target=gui_utils.voice_wake_process, args=('./resources/models/doudou.pmdl', self.signal_queue,))
        self.wake_up_detecter.start()
        self.timer.start(200, self)

    def stop_voice_wake(self):
        self.timer.stop()
        self.wake_up_detecter.terminate()
        self.signal_queue.close()
        self.wake_up_detecter = None
        self.signal_queue = None


    def timerEvent(self, event):
        if (event.timerId() != self.timer.timerId()):
            return
        if self.signal_queue is not None and not self.signal_queue.empty():
            hot_word = self.signal_queue.get()
            self.hot_word_signal.emit(hot_word)
            print(hot_word)



def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5()
                        + 'QLabel{qproperty-alignment: AlignCenter;}'
                        + 'QLabel{font-family: "宋体";}'
                    )
    main = MainWindow({'user':'hby', 'passwd':'', 'db':'FDR'}, video=0)
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()