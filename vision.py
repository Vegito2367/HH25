# vision_controller.py
# This script uses OpenCV to capture video and MediaPipe to detect facial gestures.
# It then sends commands over a WebSocket to a client (like a Godot game).
# It also displays a video feed with visual feedback.

import cv2
import mediapipe as mp
import asyncio
import websockets
import json
import math

# --- Gesture Detection Logic ---

# Calculate distance between two points
def distance(p1, p2):
    return math.sqrt(((p1.x - p2.x) ** 2) + ((p1.y - p2.y) ** 2))

# --- Main Application Logic ---

async def vision_server(websocket):
    print("Godot client connected!")

    # --- MediaPipe Initialization ---
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    mp_face_mesh = mp.solutions.face_mesh
    
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5)

    cap = cv2.VideoCapture(0)

    # --- Gesture State Variables ---
    left_wink_counter = 0
    right_wink_counter = 0
    WINK_THRESHOLD = 0.05 # How closed the eye needs to be to be considered a wink
    WINK_CONSECUTIVE_FRAMES = 3 # How many frames it must be a wink for

    try:
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                continue

            # Flip image for selfie view, and convert BGR to RGB for MediaPipe.
            image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
            
            # To improve performance, optionally mark the image as not writeable to
            # pass by reference.
            image.flags.writeable = False
            results = face_mesh.process(image)
            image.flags.writeable = True

            # Convert the image color back from RGB to BGR for OpenCV display.
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            command_to_send = None

            if results.multi_face_landmarks:
                face_landmarks = results.multi_face_landmarks[0]
                
                # --- Draw Face Mesh for Visual Feedback ---
                mp_drawing.draw_landmarks(
                    image=image,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style())
                mp_drawing.draw_landmarks(
                    image=image,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_contours_style())

                # --- Gesture Detection Logic ---
                # These landmark indices are for the vertical points of the eyes
                # Left eye
                left_eye_top = face_landmarks.landmark[159]
                left_eye_bottom = face_landmarks.landmark[145]
                left_eye_horizontal_left = face_landmarks.landmark[33]
                left_eye_horizontal_right = face_landmarks.landmark[133]

                # Right eye
                right_eye_top = face_landmarks.landmark[386]
                right_eye_bottom = face_landmarks.landmark[374]
                right_eye_horizontal_left = face_landmarks.landmark[362]
                right_eye_horizontal_right = face_landmarks.landmark[263]

                # Calculate Eye Aspect Ratio (EAR) approximation
                left_vertical_dist = distance(left_eye_top, left_eye_bottom)
                left_horizontal_dist = distance(left_eye_horizontal_left, left_eye_horizontal_right)
                # Add a small epsilon to avoid division by zero
                left_ear = left_vertical_dist / (left_horizontal_dist + 1e-6)

                right_vertical_dist = distance(right_eye_top, right_eye_bottom)
                right_horizontal_dist = distance(right_eye_horizontal_left, right_eye_horizontal_right)
                right_ear = right_vertical_dist / (right_horizontal_dist + 1e-6)

                # Check for left wink
                # if left_ear < WINK_THRESHOLD:
                #     left_wink_counter += 1
                # else:
                #     if left_wink_counter > WINK_CONSECUTIVE_FRAMES:
                #         print("LEFT WINK DETECTED")
                #         command_to_send = {"command": "insert", "shape": "sphere"}
                #     left_wink_counter = 0

                # # Check for right wink
                # if right_ear < WINK_THRESHOLD:
                #     right_wink_counter += 1
                # else:
                #     if right_wink_counter > WINK_CONSECUTIVE_FRAMES:
                #         print("RIGHT WINK DETECTED")
                #         command_to_send = {"command": "insert", "shape": "cube"}
                #     right_wink_counter = 0

                key = cv2.waitKey(5) & 0xFF
                if key == 27:  # ESC key
                    break
                elif key == ord('t') or key == ord('T'):
                    print("T KEY PRESSED, COMMAND SENT")
                    command_to_send = {"command": "insert", "shape": "sphere"}
                # --- Send Command & Provide Visual Feedback ---
                if command_to_send:
                    await websocket.send(json.dumps(command_to_send))
                    print(f"Sent: {command_to_send}")
                    # Put feedback text on the screen
                    feedback_text = f"ACTION: {command_to_send['command'].upper()} {command_to_send['shape'].upper()}"
                    cv2.putText(image, feedback_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                                1, (0, 255, 0), 2, cv2.LINE_AA)

            # --- Display Video Feed ---
            cv2.imshow('Assistive 3D Modeler - Vision Controller', image)
            
            

            # A short sleep is crucial to allow other async tasks (like websockets) to run.
            await asyncio.sleep(0.01)

    except websockets.exceptions.ConnectionClosed:
        print("Godot client disconnected.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cap.release()
        face_mesh.close()
        cv2.destroyAllWindows()
        print("Vision controller shut down.")

async def main():
    host = 'localhost'
    port = 8765
    print(f"Starting WebSocket server on ws://{host}:{port}")
    async with websockets.serve(vision_server, host, port):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())

