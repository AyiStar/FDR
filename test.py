from fdr import stat_utils

def test(tolerance=0.4, video=0):
    '''
    @ parameter:
        #data_path: the directory where .dat files are
        tolerance: maximum distance to be recognized
        video: the number of video
    @ return value:
        None
    '''

    db_conn = MySQLdb.connect(db='FDR')
    known_faces = load_faces(db_conn)
    print(len(known_faces))

    video_capture = cv2.VideoCapture(video)


    # Initialize some variables
    face_locations = []
    face_encodings = []
    face_names = []
    process_this_frame = True

    while True:
        # Grab a single frame of video
        ret, frame = video_capture.read()

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_frame = frame[:, :, ::-1]

        # Only process every other frame of video to save time
        if process_this_frame:
            # Find all the faces and face encodings in the current frame of video
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            face_matches = []

            for face_encoding in face_encodings:
                # See if the face is a match for the known face(s)
                distances = get_face_distances(known_faces, face_encoding)
                match = match_face(distances, tolerance)
                face_matches.append(match)

        process_this_frame = not process_this_frame


        # Display the results
        for (top, right, bottom, left), match in zip(face_locations, face_matches):

            # Draw a box around the face
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 1)

            # Draw a label with a name below the face
            #cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, match[0]+':'+'%.2f'%(match[1]), (left, bottom), font, 1.0, (0, 0, 255), 1)

        # Display the resulting image
        cv2.imshow('Video', frame)

        # Hit 'q' on the keyboard to quit!
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    #Release handle to the webcam
    video_capture.release()
    cv2.destroyAllWindows()

def main():
    ws = stat_utils.WeiboStat('ayistar', '', 'FDR')
    ws.get_text('1744348630')
    ws.word_stat()
    ws.generate_word_cloud(pic_path='./data/wordcloud/', weibo_user_name='慕寒mio')


if __name__ == '__main__':
    main()