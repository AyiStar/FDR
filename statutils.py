import MySQLdb
from wordcloud import WordCloud
import jieba
import jieba.analyse
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np

class WeiboStat:

    def __init__(self, db_user, db_passwd, db_name, stop_word_path='./stop_words.txt'):
        self.db_user = db_user
        self.db_passwd = db_passwd
        self.db_name = db_name
        self.text = None
        self.stat = None
        self.stop_words = set(line.strip() for line in open(stop_word_path))

    def get_text(self, uid):
        self.text = ''
        db_conn = MySQLdb.connect(user=self.db_user, passwd=self.db_passwd, host='localhost', db=self.db_name, charset='utf8mb4')
        cursor = db_conn.cursor()
        cursor.execute('SELECT tweet, forwarding FROM Weibos WHERE user_ID=%s', (uid,))
        result = cursor.fetchall()
        for tweet, forwarding in result:
            self.text += tweet
            self.text += forwarding

    def word_stat(self):
        self.word_stat = {}
        word_list = list(jieba.cut(self.text))
        for word in word_list:
            if word in self.stop_words:
                continue
            if word in self.word_stat:
                self.word_stat[word] += 1
            else:
                self.word_stat[word] = 1

    def generate_word_cloud(self, pic_path=None, weibo_user_name=None):
        mask_img = np.array(Image.open('./img/person.png'))
        word_cloud = WordCloud(font_path='./font.ttf', relative_scaling=.5, mask=mask_img,
                                width=640, height=480, background_color='white')
        word_cloud.generate_from_frequencies(self.word_stat)

        if (pic_path is not None) and (weibo_user_name is not None):
            plt.imshow(word_cloud, interpolation='bilinear')
            plt.axis('off')
            path = pic_path + '/' + weibo_user_name + '.jpg'
            plt.savefig(path)
        else:
            plt.axis('off')
            plt.imshow(word_cloud, interpolation='bilinear')
            plt.show()