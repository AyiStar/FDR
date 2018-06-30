import sys, os
from PyQt5 import QtWidgets, QtGui, QtCore
import qdarkstyle
import MySQLdb
from datetime import datetime



class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, db_login):
        super().__init__()

        # main widget
        self.main_widget = MainWidget(db_login)
        self.setCentralWidget(self.main_widget)
        self.setWindowTitle('社交眼镜后台系统')
        self.setWindowIcon(QtGui.QIcon('./resources/icons/icon.jpg'))
        self.statusBar().showMessage('Ready')

        # menu bar setting
        menu_bar = self.menuBar()

        sort_menu = menu_bar.addMenu('&排序方式')
        sort_by_name_action = QtWidgets.QAction('按姓名排序', self, checkable=True)
        sort_by_recent_meet_action = QtWidgets.QAction('按见面时间排序', self, checkable=True)
        sort_by_meet_times_action = QtWidgets.QAction('按见面次数排序', self, checkable=True)
        sort_by_name_action.setChecked(True)
        sort_menu.addAction(sort_by_name_action)
        sort_menu.addAction(sort_by_recent_meet_action)
        sort_menu.addAction(sort_by_meet_times_action)

        check_menu = menu_bar.addMenu('&查看方式')
        check_in_image_action = QtWidgets.QAction('图标查看', self, checkable=True)
        check_in_list_action = QtWidgets.QAction('列表查看', self, checkable=True)
        check_in_image_action.setChecked(True)
        check_menu.addAction(check_in_image_action)
        check_menu.addAction(check_in_list_action)

        help_menu = menu_bar.addMenu('&帮助')
        about_action = QtWidgets.QAction('关于', self)
        help_menu.addAction(about_action)


        # tool bar setting
        exitAct = QtWidgets.QAction(QtGui.QIcon('./resources/icons/exit.png'), '退出', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.triggered.connect(QtWidgets.qApp.quit)
        refreshAct = QtWidgets.QAction(QtGui.QIcon('./resources/icons/refresh.png'), '刷新', self)
        refreshAct.setShortcut('Ctrl+R')
        # refreshAct.triggered.connect(self.main_widget.refresh)
        searchAct = QtWidgets.QAction(QtGui.QIcon('./resources/icons/search.png'), '搜索', self)
        searchAct.setShortcut('Ctrl+F')
        tool_bar = self.addToolBar('工具栏')
        tool_bar.addAction(refreshAct)
        tool_bar.addAction(searchAct)
        tool_bar.addAction(exitAct)

        self.show()



class MainWidget(QtWidgets.QWidget):

    def __init__(self, db_login):
        super().__init__()
        self.layout = QtWidgets.QHBoxLayout()
        self.person_list_widget = PersonListWidget(db_login)
        self.layout.addWidget(self.person_list_widget)
        self.setLayout(self.layout)



class PersonListWidget(QtWidgets.QWidget):

    def __init__(self, db_login):
        super().__init__()
        self.layout = QtWidgets.QVBoxLayout()
        self.tabs = QtWidgets.QTabWidget()
        self.known_person_list_widget = self.KnownPersonListWidget(db_login)
        self.unknown_person_list_widget = self.UnknownPersonListWidget(db_login)
        self.tabs.addTab(self.known_person_list_widget, '认识的人')
        self.tabs.addTab(self.unknown_person_list_widget, '陌生人')
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    class KnownPersonListWidget(QtWidgets.QWidget):

        def __init__(self, db_login):
            super().__init__()
            self.db_login = db_login
            self.manage_widgets = {}
            self.layout = QtWidgets.QGridLayout()
            self.setMinimumWidth(600)
            self.refresh()
            self.setLayout(self.layout)

        def refresh(self):
            db_conn = MySQLdb.connect(user=self.db_login['user'], passwd=self.db_login['passwd'], db=self.db_login['db'])
            cursor = db_conn.cursor()
            cursor.execute('SELECT person_ID FROM Persons WHERE name!=%s', ('Unknown',))
            person_ids = [x[0] for x in cursor.fetchall()]

            for i, person_id in enumerate(person_ids):
                button = QtWidgets.QPushButton()
                button.setFixedSize(QtCore.QSize(200, 150))
                if os.path.exists('./data/photo/' + person_id + '.jpg'):
                    button.setIcon(QtGui.QIcon('./data/photo/' + person_id + '.jpg'))
                else:
                    button.setIcon(QtGui.QIcon('./resources/icons/question.jpg'))
                button.setIconSize(QtCore.QSize(200, 150))
                self.manage_widgets[person_id] = PersonManageWidget(self.db_login, person_id)
                button.clicked.connect(self.manage_widgets[person_id].show)
                self.layout.addWidget(button, i//3, i%3)

            db_conn.close()





    class UnknownPersonListWidget(QtWidgets.QWidget):

        def __init__(self, db_login):
            super().__init__()
            self.layout = QtWidgets.QGridLayout()
            self.refresh()
            self.setLayout(self.layout)

        def refresh(self):
            photo_label = QtWidgets.QLabel()
            photo_label.setPixmap(QtGui.QPixmap('./resources/icons/question.jpg').scaled(200, 150, QtCore.Qt.KeepAspectRatio))
            self.layout.addWidget(photo_label, 0, 0)



class PersonManageWidget(QtWidgets.QWidget):

    def __init__(self, db_login, person_id):
        super().__init__()
        self.setWindowTitle('人物信息')
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
            self.db_login = db_login
            db_conn = MySQLdb.connect(user=self.db_login['user'], passwd=self.db_login['passwd'], db=self.db_login['db'])
            db_conn.set_character_set('utf8')
            cursor = db_conn.cursor()
            weibo_name = 'None'
            weibo_uid = 'None'
            if cursor.execute('SELECT weibo_name, weibo_uid FROM WeiboAccounts WHERE person_ID=%s', (person_id,)) > 0:
                weibo_name, weibo_uid = cursor.fetchone()
            cursor.execute('SELECT post_time, tweet, forwarding FROM Weibos WHERE user_ID=%s', (weibo_uid,))
            tweets = cursor.fetchall()


            self.word_cloud_label = QtWidgets.QLabel()
            if os.path.exists('./data/wordcloud/' + weibo_name + '.jpg'):
                self.word_cloud_label.setPixmap(QtGui.QPixmap('./data/wordcloud/' + weibo_name + '.jpg').scaled(360, 360, QtCore.Qt.KeepAspectRatio))
            else:
                self.word_cloud_label.setPixmap(QtGui.QPixmap('./resources/icons/person.png').scaled(360, 360, QtCore.Qt.KeepAspectRatio))

            self.weibo_name_label = QtWidgets.QLabel(''.join(['微博昵称: ', weibo_name]))
            self.last_post_time_label = QtWidgets.QLabel(''.join(['最近微博发布时间: ', 'None' if len(tweets)== 0 else tweets[0][0]]))
            self.last_tweet_label = QtWidgets.QLabel(''.join(['最近微博: ', 'None' if len(tweets) == 0 else (tweets[0][1] if len(tweets[0][1]) > 0 else tweets[0][2])]))
            self.last_tweet_label.setWordWrap(True)
            self.more_button = QtWidgets.QPushButton('详细信息')
            self.more_button.clicked.connect(lambda: self.more_table.hide() if self.more_table.isVisible() else self.more_table.show())

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
            self.info_layout.addWidget(self.last_post_time_label)
            self.info_layout.addWidget(self.last_tweet_label)
            self.info_layout.addWidget(self.more_button)
            self.info_layout.addStretch(0)

            self.base_layout = QtWidgets.QHBoxLayout()
            self.base_layout.addWidget(self.word_cloud_label)
            self.base_layout.addLayout(self.info_layout)

            self.layout = QtWidgets.QVBoxLayout()
            self.layout.addLayout(self.base_layout)
            self.layout.addWidget(self.more_table)
            self.setLayout(self.layout)

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




def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5()
                        + 'QLabel{qproperty-alignment: AlignCenter;}'
                        + 'QLabel{font-family: "宋体";}'
                    )
    main = MainWindow({'user':'ayistar', 'passwd':'', 'db':'FDR'})
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()