from fdr import *

'''
    First, use store_face to get .dat file of a person.
    Before you run the function below, you must have sevaral pictures in ./picture/hby/ as the 2nd parameter.
    The result (.dat file) will be stored in ./data/ as the 3rd parameter.
    The name of the .dat file will be Hubingyu.dat as the 1st parameter.
    You can open the .dat file as txt file to see the result.
'''
#store_face('HuBingyu', './pictures/hby/', './data/')


'''
    Now, you can just use recognize_face to show the recognition.
    Before you run the function below, you must have .dat files in ./data/ as the 1st parameter.
    You can set the tolerance by yourself, the lower tolerance is , the more strict the recognition is.
    The video will show the name of the recognized person, and the corresponding distance.
    Press 'q' to quit.
'''
#recognize_face('./data/', tolerance=0.4, video=0)