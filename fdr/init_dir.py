#-*- coding: utf-8 -*-

import os
import shutil

if os.path.exists('./data/'):
    shutil.rmtree('./data/')
os.mkdir('./data/')
os.mkdir('./data/photo/')
os.mkdir('./data/wordcloud/')
os.mkdir('./data/network/')