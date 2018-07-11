import os
import sys
import face_utils


if not os.path.exists('extra_photo'):
    print('please create a folder named extra_photo and put photos in it')
    sys.exit(0)

db_login = {'user':'hby', 'passwd':'', 'db':'FDR'}

for file_name in os.listdir('extra_photo'):
    face_utils.recognize_face_from_file(db_login, './extra_photo/' + file_name, verbose=True)

