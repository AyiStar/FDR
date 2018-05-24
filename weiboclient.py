# -*-coding:utf-8-*-
import traceback
import MySQLdb
from datetime import datetime
from bs4 import BeautifulSoup
import random
import time
import requests
import re
import weibo
from statutils import WeiboStat


class WeiboClient:

    def __init__(self, cookie=None, db_user=None, db_passwd=None, db_name=None,
                app_key='3396385405', app_secret='b333b2531b57d41456a885271e8c2630',
                app_redirect_uri='https://api.weibo.com/oauth2/default.html',
                app_user='824476660@qq.com', app_passwd='zhu19970316'):
        self.cookie = cookie
        self.agents = [
            "Mozilla/5.0 (Linux; U; Android 2.3.6; en-us; Nexus S Build/GRK39F) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
            "Avant Browser/1.2.789rel1 (http://www.avantbrowser.com)",
            "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/532.5 (KHTML, like Gecko) Chrome/4.0.249.0 Safari/532.5",
            "Mozilla/5.0 (Windows; U; Windows NT 5.2; en-US) AppleWebKit/532.9 (KHTML, like Gecko) Chrome/5.0.310.0 Safari/532.9",
            "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.7 (KHTML, like Gecko) Chrome/7.0.514.0 Safari/534.7",
            "Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US) AppleWebKit/534.14 (KHTML, like Gecko) Chrome/9.0.601.0 Safari/534.14",
            "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.14 (KHTML, like Gecko) Chrome/10.0.601.0 Safari/534.14",
            "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.20 (KHTML, like Gecko) Chrome/11.0.672.2 Safari/534.20",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534.27 (KHTML, like Gecko) Chrome/12.0.712.0 Safari/534.27",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/13.0.782.24 Safari/535.1",
            "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/535.2 (KHTML, like Gecko) Chrome/15.0.874.120 Safari/535.2",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.7 (KHTML, like Gecko) Chrome/16.0.912.36 Safari/535.7",
            "Mozilla/5.0 (Windows; U; Windows NT 6.0 x64; en-US; rv:1.9pre) Gecko/2008072421 Minefield/3.0.2pre",
            "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.10) Gecko/2009042316 Firefox/3.0.10",
            "Mozilla/5.0 (Windows; U; Windows NT 6.0; en-GB; rv:1.9.0.11) Gecko/2009060215 Firefox/3.0.11 (.NET CLR 3.5.30729)",
            "Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6 GTB5",
            "Mozilla/5.0 (Windows; U; Windows NT 5.1; tr; rv:1.9.2.8) Gecko/20100722 Firefox/3.6.8 ( .NET CLR 3.5.30729; .NET4.0E)",
            "Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1",
            "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:2.0.1) Gecko/20100101 Firefox/4.0.1",
            ]
        self.db_user = db_user
        self.db_passwd = db_passwd
        self.db_name = db_name
        self.app_key = app_key
        self.app_secret = app_secret
        self.app_redirect_uri = app_redirect_uri
        self.app_user = app_user
        self.app_passwd = app_passwd
        self.db_conn = MySQLdb.connect(user=self.db_user, passwd=self.db_passwd, host='localhost', db=self.db_name, charset='utf8mb4')
        self.client = weibo.Client(self.app_key, self.app_secret, self.app_redirect_uri,
                                username=self.app_user, password=self.app_passwd)

    def __del__(self):
        self.db_conn.close()

    def get_weibo(self, uid_list):
        cursor = self.db_conn.cursor()
        try:
            for uid in uid_list: #len(self.Id_List)
                UA = random.choice(self.agents)
                header = {'User-Agen': UA}
                #print(uid)
                url = 'http://weibo.cn/u/%s' % uid
                html = requests.get(url, cookies=self.cookie, headers=header)
                user_name = BeautifulSoup(html.text, 'lxml').find('div', class_='ut').find('span', class_='ctt').get_text().split('?')[0].split()[0]
                #print(user_name)
                if BeautifulSoup(html.text, 'lxml').find('div', class_='pa', id='pagelist') != None:
                    num = int(BeautifulSoup(html.text, 'lxml').find('div', class_='pa', id='pagelist').find_all('input')[0]['value'])
                else:
                    num = 1
                pattern = r'\d+'

                for n in range(1, num+1):
                    print('{0}: {1}/{2} pages'.format(user_name, n, num))
                    url2 = 'http://weibo.cn/u/%s?page=%s' % (uid,  n)
                    html2 = requests.get(url2, cookies=self.cookie, headers=header, timeout = 10)
                    time.sleep(3)
                    soup2 = BeautifulSoup(html2.text, 'lxml').find_all('div', class_='c')
                    if len(soup2) > 3:
                        for i in range(1, len(soup2) - 2):
                            div_ls = soup2[i].find_all('div')
                            if len(div_ls) == 3:
                                tweet = div_ls[2].get_text().split('??')[0][5:]
                                tweet = tweet.encode('gbk', 'ignore')
                                tweet = str(tweet.decode('gbk', 'ignore'))
                                forwarding = div_ls[0].find('span', class_='ctt').get_text().replace('[^\u0000-\uFFFF]', '')
                                if div_ls[0].find('span', class_='ctt').find('a') != None:
                                    a_l = div_ls[0].find('span', class_='ctt').find_all('a')
                                    for a1 in a_l:
                                        if a1.get_text() == '全文':
                                            href = 'https://weibo.cn' + a1['href']
                                            req = requests.get(href, cookies=self.cookie, headers=header)
                                            time.sleep(2)
                                            forwarding = BeautifulSoup(req.text, 'lxml').find_all('div', class_='c')[2].find('span', class_='ctt').get_text()
                                            break
                                all_num = div_ls[2].find_all('a')
                                if all_num[-1].get_text() == '收藏':
                                    num_likes = int(re.findall(pattern, all_num[-4].get_text())[0])
                                    num_forwardings = int(re.findall(pattern, all_num[-3].get_text())[0])
                                    num_comments = int(re.findall(pattern, all_num[-2].get_text())[0])
                                else:
                                    num_likes = int(re.findall(pattern, all_num[-5].get_text())[0])
                                    num_forwardings = int(re.findall(pattern, all_num[-4].get_text())[0])
                                    num_comments = int(re.findall(pattern, all_num[-3].get_text())[0])
                                #print(tweet)
                                picture = 0
                                videos = 0
                                zf = 1
                                if tweet == '转发微博' or tweet.split('//@')[0] == '转发微博':
                                    luozhuan = 1
                                else: luozhuan = 0
                                others = div_ls[2].find('span', class_='ct').get_text().split('?')
                                if others[0]:
                                    post_time = str(others[0])
                            elif len(div_ls) == 1:
                                tweet = div_ls[0].find('span',class_='ctt').get_text()
                                tweet = tweet.encode('gbk', 'ignore')
                                tweet = str(tweet.decode('gbk', 'ignore'))
                                forwarding = ''
                                if div_ls[0].find('span', class_='ctt').find('a') != None:
                                    a_l = div_ls[0].find('span', class_='ctt').find_all('a')
                                    for a1 in a_l:
                                        if a1.get_text() == '全文':
                                            href = 'https://weibo.cn' + a1['href']
                                            req = requests.get(href, cookies=self.cookie, headers=header)
                                            tweet = BeautifulSoup(req.text, 'lxml').find_all('div', class_='c')[2].find('span', class_='ctt').get_text()
                                            break
                                all_num = div_ls[0].find_all('a')
                                if all_num[-1].get_text() == '收藏':
                                    num_likes = int(re.findall(pattern, all_num[-4].get_text())[0])
                                    num_forwardings = int(re.findall(pattern, all_num[-3].get_text())[0])
                                    num_comments = int(re.findall(pattern, all_num[-2].get_text())[0])
                                else:
                                    num_likes = int(re.findall(pattern, all_num[-5].get_text())[0])
                                    num_forwardings = int(re.findall(pattern, all_num[-4].get_text())[0])
                                    num_comments = int(re.findall(pattern, all_num[-3].get_text())[0])
                                #print(tweet)
                                picture = 0
                                if re.findall('秒拍视频',tweet):
                                    videos = 1
                                else:
                                    videos = 0
                                zf = 0
                                luozhuan = 0
                                others = div_ls[0].find('span', class_='ct').get_text().split('?')
                                if others[0]:
                                    post_time = str(others[0])

                            elif len(div_ls) == 2:
                                z = div_ls[1].find_all('span')
                                if len(z)>=2:
                                    zf = 1
                                    tweet = div_ls[1].get_text().split('??')[0][5:]
                                    tweet = tweet.encode('gbk', 'ignore')
                                    tweet = str(tweet.decode('gbk', 'ignore'))
                                    forwarding = div_ls[0].find('span', class_='ctt').get_text().replace('[^\u0000-\uFFFF]', '')
                                    all_num = div_ls[1].find_all('a')
                                    if div_ls[0].find('span', class_='ctt').find('a') != None:
                                        a_l = div_ls[0].find('span', class_='ctt').find_all('a')
                                        for a1 in a_l:
                                            if a1.get_text() == '全文':
                                                href = 'https://weibo.cn' + a1['href']
                                                req = requests.get(href, cookies=self.cookie, headers=header)
                                                forwarding = BeautifulSoup(req.text, 'lxml').find_all('div', class_='c')[2].find('span', class_='ctt').get_text()
                                                break
                                    if all_num[-1].get_text() == '收藏':
                                        num_likes = int(re.findall(pattern, all_num[-4].get_text())[0])
                                        num_forwardings = int(re.findall(pattern, all_num[-3].get_text())[0])
                                        num_comments = int(re.findall(pattern, all_num[-2].get_text())[0])
                                    else:
                                        num_likes = int(re.findall(pattern, all_num[-5].get_text())[0])
                                        num_forwardings = int(re.findall(pattern, all_num[-4].get_text())[0])
                                        num_comments = int(re.findall(pattern, all_num[-3].get_text())[0])
                                    #print(tweet)
                                    if tweet == '转发微博' or tweet.split('//@')[0] == '转发微博':
                                        luozhuan = 1
                                    else:
                                        luozhuan = 0
                                    videos = 0
                                    picture = 0
                                else:
                                    zf = 0
                                    luozhuan = 0
                                    str_t = div_ls[0].find('span', class_='ctt').get_text()
                                    tweet = str_t.encode('gbk', 'ignore')
                                    tweet = str(tweet.decode('gbk', 'ignore'))
                                    forwarding = ''
                                    if div_ls[0].find('span', class_='ctt').find('a') != None:
                                        a_l = div_ls[0].find('span', class_='ctt').find_all('a')
                                        for a1 in a_l:
                                            if a1.get_text() == '全文':
                                                href = 'https://weibo.cn' + a1['href']
                                                req = requests.get(href, cookies=self.cookie, headers=header, timeout=10)
                                                tweet = BeautifulSoup(req.text, 'lxml').find_all('div', class_='c')[2].find('span', class_='ctt').get_text()
                                                break
                                    all_num = div_ls[1].find_all('a')
                                    if all_num[-1].get_text() == '收藏':
                                        num_likes = int(re.findall(pattern, all_num[-4].get_text())[0])
                                        num_forwardings = int(re.findall(pattern, all_num[-3].get_text())[0])
                                        num_comments = int(re.findall(pattern, all_num[-2].get_text())[0])
                                    else:
                                        num_likes = int(re.findall(pattern, all_num[-5].get_text())[0])
                                        num_forwardings = int(re.findall(pattern, all_num[-4].get_text())[0])
                                        num_comments = int(re.findall(pattern, all_num[-3].get_text())[0])
                                    #print(tweet)
                                    videos = 0
                                    picture = 1

                                others = div_ls[1].find('span', class_='ct').get_text().split('?')
                                if others[0]:
                                    post_time = str(others[0])
                            else:
                                continue

                            sql = 'INSERT INTO Weibos (`user_id`, `user_name`, `tweet`,  `forwarding`,`num_likes`,`num_forwardings`,\
                                `num_comments`,`post_time`) VALUES ( %(user_id)s, %(user_name)s, %(tweet)s, %(forwarding)s, %(num_likes)s,\
                                 %(num_forwardings)s, %(num_comments)s, %(post_time)s)'
                            value = {
                                'user_id': uid,
                                'user_name': user_name,
                                'tweet': tweet,
                                'forwarding': forwarding,
                                'num_likes': num_likes,
                                'num_forwardings' : num_forwardings,
                                'num_comments': num_comments,
                                'post_time': post_time
                            }
                            cursor.execute(sql, value)
                            self.db_conn.commit()
                print('{0}: all pages done'.format(user_name))
        except Exception as e:
            print("Error: ", e)
            traceback.print_exc()

    def get_uid(self, nick_name):
        try:
            uid = self.client.get('users/show', screen_name=nick_name)['idstr']
            return uid
        except Exception as e:
            print('Error: user does not exist!')
            return None

    def save_info(self, person_name, nick_name, uid):
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT person_ID FROM Persons WHERE name=%s', (person_name,))
        result = cursor.fetchall()
        if len(result) == 0:
            print('Error: person does not exist')
            return False
        person_id = result[0][0]
        cursor.execute('INSERT INTO WeiboAccounts (person_ID, weibo_name, weibo_uid) VALUES (%s, %s, %s)',
                        (person_id, nick_name, uid))
        self.db_conn.commit()
        return True




def weibo_client_process(db_user, db_passwd, db_name, person_name, weibo_user_name):
    cookie = {
            "Cookie": '_T_WM=897a5cddc91313eb40a4d44efe82c041; SUB=_2A252B5M7DeRhGeRG6FsQ9SzPwjyIHXVVCz1zrDV6PUJbkdANLU7ykW1NUjSIDKEeHdnG6F3Owi33LiKgDU1zYT28; SUHB=0z1R34lEPLCsQs; SCF=Aurel-CXoF707U2FuZTejk20gZCmrDS1Ehi56ro6GtPtrzKDJCFJ88uDcB_NcEOZDfXZ7KHA6niumfXCilyuTXs.; SSOLoginState=1526981485; M_WEIBOCN_PARAMS=uicode%3D20000174%26featurecode%3D20000320%26fid%3Dhotword; MLOGIN=1',
            }
    wb = WeiboClient(cookie=cookie, db_user=db_user, db_passwd=db_passwd, db_name=db_name)
    uid = wb.get_uid(weibo_user_name)
    if uid is not None:
        # if wb.save_info(person_name, weibo_user_name, uid) == True:
        #     wb.get_weibo([uid])
        ws = WeiboStat(db_user, db_passwd, db_name)
        ws.get_text(uid)
        ws.word_stat()
        ws.generate_word_cloud(pic_path='./wordclouds/', weibo_user_name=weibo_user_name)

