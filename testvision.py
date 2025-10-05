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
import random as r


# --- Main Application Logic ---
def random_between(m, n):
    return r.uniform(m, n)

async def socketTest(websocket):
    print("Godot client connected!")
    try:
        xprec=10
        yprec=10
        while True:
            command_to_send = None
            if select.select([sys.stdin], [], [], 0)[0]:
                key_input = sys.stdin.read(1)
                x =str(random_between(100,500))
                y=str(random_between(100,500))
                xper = str(random_between(0,100))
                yper = str(random_between(0,100))
                cubex = 30
                buttony=92
                sphx=45
                diamondx=65
                
                z = random_between(2,10)
                if key_input == 'q':  # Quit
                    break
                elif key_input == 't':
                    command_to_send = {"command": "click", "x": sphx, "y": buttony}
                elif key_input == 'y':
                    command_to_send = {"command": "click", "x": cubex, "y": buttony}
                elif key_input == 'z':
                    command_to_send = {"command": "select"}
                elif key_input == 'm':  # eye movement
                    command_to_send = {"command": "cursor", "x": xprec+10, "y": yprec+10 }
                    xprec+=10
                    yprec+=10
                elif key_input == 'M':  # eye movement
                    command_to_send = {"command": "cursor", "x": yprec-10, "y": yprec-10 }
                    xprec-=10
                    yprec-=10
                elif key_input=='p':
                    command_to_send = {"command": "cursor", "x": 75, "y": 40 }
                elif key_input=='P':
                    command_to_send = {"command": "cursor", "x": 25, "y": 40 }
                elif key_input == 'o':
                    command_to_send = {"command": "stagerotate", "x": 40, "y": 75 }
                elif key_input =='O':
                    command_to_send = {"command": "stagerotate", "x": 40, "y": 25 }
                elif key_input == 'n':  # eye click
                    command_to_send = {"command": "cursor", "x": str(xper), "y": str(yper) }
                    command_to_send = {"command": "click", "x": str(xper), "y": str(yper)}
                elif key_input == 'j':  # eye click
                    command_to_send = {"command": "selectZ", "z":str(z)}
                elif key_input == 'w':
                    command_to_send = {"command":"move", "x":0, "y":0, "z":88}
                elif key_input == 'W':
                    command_to_send = {"command":"move", "x":0, "y":0, "z":11}
                elif key_input == 'a':
                    command_to_send = {"command":"move", "x":88, "y":0, "z":0}
                elif key_input == 'A':
                    command_to_send = {"command":"move", "x":11, "y":0, "z":0}
                elif key_input == 's':
                    command_to_send = {"command":"move", "x":0, "y":88, "z":0}
                elif key_input == 'S':
                    command_to_send = {"command":"move", "x":0, "y":11, "z":0}
                elif key_input == 'r':
                    command_to_send = {"command":"stagerotate", "x":0, "y":60}
                elif key_input == 'R':
                    command_to_send = {"command":"stagerotate", "x":0, "y":-60}
                elif key_input == 'k':
                    command_to_send = {"command":"stagerotate", "x":30, "y":0}
                elif key_input == 'K':
                    command_to_send = {"command":"stagerotate", "x":-30, "y":0}
                
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

