import face_recognition
import cv2
import numpy as np
import csv
import os




def store_face(name, img_path, data_path):
    '''
    @ parameter:
        name: name of the person to be recorded
        img_path: path of pictures of the person
        data_path: path of data file to store the encoding
    @ return value:
        None
    '''

    face_encodings = []
    for file_name in os.listdir(img_path):
        if file_name.endswith('.jpg'):
            img = face_recognition.load_image_file(img_path + '/' + file_name)
            face_encodings.append(face_recognition.face_encodings(img)[0])
    np.savetxt(data_path + '/' + name + '.dat', face_encodings, delimiter=',')



def load_faces(data_path):
    '''
    @ parameter:
        data_path: the path of data file to be read
    @ return value:
        known_faces: dict{name:[face_encoding]}
    '''

    known_faces = {}
    for file_name in os.listdir(data_path):
        if file_name.endswith('.dat'):
            name = file_name.rstrip('.dat')
            face_encodings = np.loadtxt(data_path + '/' + file_name, delimiter=',')
            known_faces[name] = face_encodings

    return known_faces



def get_face_distances(known_faces, unknown_face):
    '''
    @ parameter:
        known_faces: dict{name:[face_encoding]}
        unknown_faces: 128-d array (face encoding)
    @ return value:
        distances: dict{name:distance}
    '''

    distances = {}
    for name in known_faces:
        match_dist = 1000 # Large enough
        for known_face in known_faces[name]:
            dist = np.linalg.norm(known_face - unknown_face)
            if dist < match_dist:
                match_dist = dist
        distances[name] = match_dist

    return distances



def match_face(distances, tolerance):
    '''
    @ parameter:
        distances: dict{name:distance}
        tolerance: the maximum distance to recognize
    @ return value:
        match: tuple (name, distance), name may be 'Unknown'
    '''

    match_name = None
    match_dist = 1000 # Large enough
    for name in distances:
        if distances[name] < match_dist:
            match_dist = distances[name]
            match_name = name
    if match_dist > tolerance:
        match_name = 'Unknown'
    return (match_name, match_dist)



def recognize_face(data_path, tolerance, video=0):
    '''
    @ parameter:
        data_path: the directory where .dat files are
        tolerance: maximum distance to be recognized
        video: the number of video
    @ return value:
        None
    '''

    known_faces = load_faces(data_path)

    video_capture = cv2.VideoCapture(video)


    # Initialize some variables
    face_locations = []
    face_encodings = []
    face_names = []
    process_this_frame = True

    while True:
        # Grab a single frame of video
        ret, frame = video_capture.read()

        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_small_frame = small_frame[:, :, ::-1]

        # Only process every other frame of video to save time
        if process_this_frame:
            # Find all the faces and face encodings in the current frame of video
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            face_matches = []

            for face_encoding in face_encodings:
                # See if the face is a match for the known face(s)
                distances = get_face_distances(known_faces, face_encoding)
                match = match_face(distances, tolerance)
                face_matches.append(match)

        process_this_frame = not process_this_frame


        # Display the results
        for (top, right, bottom, left), match in zip(face_locations, face_matches):

            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Draw a box around the face
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

            # Draw a label with a name below the face
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            #cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
            cv2.putText(frame, match[0]+':'+'%.2f'%(match[1]), (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

        # Display the resulting image
        cv2.imshow('Video', frame)

        # Hit 'q' on the keyboard to quit!
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    #Release handle to the webcam
    video_capture.release()
    cv2.destroyAllWindows()