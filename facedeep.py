import face_recognition
import cv2
import numpy as np
import os
import mysql.connector
import pandas as pd
from datetime import datetime, timedelta


CurrentFolder = os.getcwd()  # Read current folder path


# Create empty lists for face encodings and names
known_face_encodings = []
known_face_names = []
last_recorded_time = {}

# Loop through all image files in the current folder
for file_name in os.listdir(CurrentFolder):
    if file_name.endswith(".png") or file_name.endswith(".jpg"):
        # Construct the full path to the image file
        image_path = os.path.join(CurrentFolder, file_name)
        
        # Load the image and learn how to recognize it
        image = face_recognition.load_image_file(image_path)
        face_encoding = face_recognition.face_encodings(image)[0]

        # Add the face encoding and corresponding name to the lists
        known_face_encodings.append(face_encoding)
        known_face_names.append(file_name[:-4])  # Remove the file extension from the name


# Get a reference to webcam #0 (the default one)
video_capture = cv2.VideoCapture(0)

# Initialize some variables
face_locations = []
face_encodings = []
face_names = []
process_this_frame = True
# Create an empty dataframe to store the records
df = pd.DataFrame(columns=['Name', 'Date', 'Time'])
# Create a connection to the database
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="beeah_attendance_system_test"
)
# Create a variable to track the check-in/out status (0 - None, 1 - Check-in, 2 - Check-out)
check_status = 0
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
        
        face_names = []
        current_time = datetime.now()
        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]
            else:
                name = "Unknown"
                
            face_names.append(name)

            if check_status == 1 and name != "Unknown":
                if name not in last_recorded_time or current_time - last_recorded_time[name] >= timedelta(seconds=30):
                    print(name)

                    # Get the current date and time
                    now = datetime.now()
                    date = now.strftime("%Y-%m-%d")
                    time = now.strftime("%H:%M:%S")

                    # Add the record to the dataframe
                    df = pd.concat([df, pd.DataFrame({'Name': [name], 'Date': [date], 'Time': [time]})], ignore_index=True)

                    # Insert the record into the database
                    cursor = mydb.cursor()
                    sql = "INSERT INTO employees_timesheet_test (employee_code , date, time, check_in_out) VALUES (%s, %s, %s, %s)"
                    values = (name, date, time, "Check-in")
                    cursor.execute(sql, values)
                    mydb.commit()

                    # Update the last recorded time for the person
                    last_recorded_time[name] = current_time
                    check_status = 0  # Reset check_status back to None
                else:
                    print("Too soon to record check-in for", name)
            elif check_status == 2 and name != "Unknown":
                if name not in last_recorded_time or current_time - last_recorded_time[name] >= timedelta(seconds=30):
                    print(name)

                    # Get the current date and time
                    now = datetime.now()
                    date = now.strftime("%Y-%m-%d")
                    time = now.strftime("%H:%M:%S")
                                                                                                
                    # Add the record to the dataframe
                    df= pd.concat([df, pd.DataFrame({'Name': [name], 'Date': [date], 'Time': [time]})], ignore_index=True)

                    # Insert the record into the database
                    cursor = mydb.cursor()
                    sql = "INSERT INTO employees_timesheet_test (employee_code , date, time, check_in_out) VALUES (%s, %s, %s, %s)"
                    values = (name, date, time, "Check-out")
                    cursor.execute(sql, values)
                    mydb.commit()

                    

                    # Update the last recorded time for the person
                    last_recorded_time[name] = current_time
                    check_status = 0  # Reset check_status back to None
                else:
                    print("Too soon to record check-out for", name)
            else:
                print("Unknown")

    process_this_frame = not process_this_frame
    
    # Display the results
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
        top *= 4
        right *= 4
        bottom *= 4
        left *=4
        
        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 100, 255), 2)

        # Draw a label with a name below the face
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)

    # Display the resulting image
    cv2.imshow('Video', frame)

    # Check for key press (c for check-in, o for check-out)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('c'):
        check_status = 1  # Set check_status to Check-in
    elif key == ord('o'):
        check_status = 2  # Set check_status to Check-out

    # Hit 'q' on the keyboard to quit
    if key == ord('q'):
        break

# Close the database connection
mydb.close()

# Save the dataframe to a CSV file
df.to_csv('records.csv', index=False)

# Release handle to the webcam
video_capture.release()
cv2.destroyAllWindows()