from face_recog import *

store_faces('HuBingyu', './pictures/hby/', './data/')

known_faces = load_faces('./data/')

recognize_face('./data/', tolerance=0.4, video=0)