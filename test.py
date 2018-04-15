from face_detection import *

#get_my_face(12000, 'my_faces')
#get_other_faces('samples', 'other_faces')

train('./test/my_faces', './test/other_faces', './test/train_result_5000/', max=5000)

#recognize_face('./test')