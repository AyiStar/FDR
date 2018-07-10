from collections import Counter
import requests
import re
import MySQLdb
from wordcloud import WordCloud
import jieba
import jieba.analyse
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from PIL import Image
import numpy as np
import networkx as nx


class WeiboStat:

    def __init__(self, db_user, db_passwd, db_name, stop_word_path='./resources/stop_words.txt'):
        self.db_user = db_user
        self.db_passwd = db_passwd
        self.db_name = db_name
        self.text = None
        self.stat = None
        self.stop_words = set(line.strip() for line in open(stop_word_path, encoding='utf-8'))

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
            if word in self.stop_words or len(word) == 1:
                continue
            if word in self.word_stat:
                self.word_stat[word] += 1
            else:
                self.word_stat[word] = 1

    def generate_hot_word(self, uid, num_hot_words):
        word_counter = Counter(self.word_stat)
        hot_words = word_counter.most_common(num_hot_words)
        db_conn = MySQLdb.connect(user=self.db_user, passwd=self.db_passwd, db=self.db_name)
        db_conn.set_character_set('utf8')
        cursor = db_conn.cursor()
        cursor.execute('SET NAMES utf8;')
        cursor.execute('SET CHARACTER SET utf8;')
        cursor.execute('SET character_set_connection=utf8;')
        cursor.execute('DELETE FROM WeiboHotWords WHERE weibo_uid=%s', (uid,))
        for word, freq in hot_words:
            description = get_knowledge(word)
            cursor.execute('INSERT INTO WeiboHotWords (weibo_uid, hot_word, frequency, description) VALUES (%s, %s, %s, %s)',
                            (uid, word, freq, description,))
        db_conn.commit()
        db_conn.close()


    def generate_word_cloud(self, pic_path, uid):
        mask_img = np.array(Image.open('./resources/icons/person.png'))
        word_cloud = WordCloud(font_path='./resources/font.ttf', relative_scaling=.5,
                                width=640, height=480,
                                background_color='black')
        word_cloud.generate_from_frequencies(self.word_stat)
        plt.axes([0,0,1,1])
        plt.imshow(word_cloud, interpolation='nearest')
        plt.axis('off')
        path = pic_path + '/' + uid + '.jpg'
        plt.savefig(path)



class NetworkStat:

    def __init__(self, db_user, db_passwd, db_name):
        self.db_user = db_user
        self.db_passwd = db_passwd
        self.db_name = db_name

    def generate_network(self, person_id, pic_path=None):
        db_conn = MySQLdb.connect(user=self.db_user, passwd=self.db_passwd, db=self.db_name)
        db_conn.set_character_set('utf8')
        cursor = db_conn.cursor()
        cursor.execute('SET NAMES utf8;')
        cursor.execute('SET CHARACTER SET utf8;')
        cursor.execute('SET character_set_connection=utf8;')
        Chinese_font = fm.FontProperties(fname='./resources/font.ttf')
        nx.set_fontproperties(Chinese_font)
        G = nx.MultiDiGraph()
        node_labels = {}
        edge_labels = {}

        G.add_node(person_id)
        cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (person_id,))
        person_name = cursor.fetchone()[0]
        node_labels[person_id] = person_name

        cursor.execute('SELECT relation_type, person2_ID FROM Relations WHERE person1_ID=%s', (person_id,))
        result = cursor.fetchall()
        for relation_type, person2_id in result:
            G.add_node(person2_id)
            cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (person2_id,))
            person2_name = cursor.fetchone()[0]
            node_labels[person2_id] = person2_name
            G.add_edge(person_id, person2_id)
            edge_labels[(person_id, person2_id)] = relation_type

        cursor.execute('SELECT relation_type, person1_ID FROM Relations WHERE person2_ID=%s', (person_id,))
        result = cursor.fetchall()
        for relation_type, person1_id in result:
            G.add_node(person1_id)
            cursor.execute('SELECT name FROM Persons WHERE person_ID=%s', (person1_id,))
            person1_name = cursor.fetchone()[0]
            node_labels[person1_id] = person1_name
            G.add_edge(person1_id, person_id)
            edge_labels[(person1_id, person_id)] = relation_type

        pos = nx.spring_layout(G)
        plt.axis('off')
        nx.draw_networkx(G, pos, labels=node_labels, width=1.5, font_size=48)
        #nx.draw_networkx_edges(G, pos)
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=48)
        plt.savefig('./data/network/' + person_id + '.jpg')
        plt.clf()
        db_conn.close()



def get_knowledge(keyword):
    try:
        url="http://apis.haoservice.com/efficient/robot?info="+keyword+" 是什么"+"&address=&key=5babd8b63012466bb3deed9daeca8aae"
        r = requests.get(url, timeout=5)
        json_obj = r.json()
        if(json_obj["reason"]=="成功"):
            text = json_obj["result"]["text"]
            if(len(text)>=30):
                #print("返回合法")
                textlist=text.split("。")
                if(len(textlist)==1):
                    returntext = (textlist[0])
                else:
                    if(len(str(textlist[0]))>50):
                        returntext=str(textlist[0]) + "。"
                    else:
                        returntext=(textlist[0])+"。"+str(textlist[1])+"。"
                        if(len(returntext)>=60):
                            returntext = str(textlist[0]) + "。"
            else:
                #print("舍弃")
                #print(json_obj["result"]["text"])
                returntext = ""
            return re.sub(u"\\（.*?）|\\(.*?\\)|\\[.*?]|\\【.*?】", "", returntext)
        else:
            return ""
            #print("未查询到有效内容")
    except:
        return ''