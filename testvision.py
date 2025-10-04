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
import sys, select


# --- Main Application Logic ---

async def socketTest(websocket):
    print("Godot client connected!")
    try:
        while True:
            command_to_send = None
            if select.select([sys.stdin], [], [], 0)[0]:
                    key_input = sys.stdin.read(1)
                    if key_input == 'q':  # Quit
                        break
                    elif key_input == 't':
                        print("T KEY PRESSED, COMMAND SENT")
                        command_to_send = {"command": "insert", "shape": "sphere"}
                    elif key_input == 'y':
                        print("Y KEY PRESSED, COMMAND SENT")
                        command_to_send = {"command": "insert", "shape": "cube"}
                    elif key_input =='u':
                        command_to_send = {"command":"selectXY", "x":"20.5","y":"30.5"}
                    elif key_input =='i':
                        command_to_send = {"command":"selectXY", "x":"40.5","y":"20.5"}
            if command_to_send:
                await websocket.send(json.dumps(command_to_send))
                print(f"Sent: {command_to_send}")           
            # A short sleep is crucial to allow other async tasks (like websockets) to run.
            await asyncio.sleep(0.01)

    except websockets.exceptions.ConnectionClosed:
        print("Godot client disconnected.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("FATAL ERROR OCCURED")

async def main():
    host = 'localhost'
    port = 8765
    print(f"Starting WebSocket server on ws://{host}:{port}")
    async with websockets.serve(socketTest, host, port):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())

