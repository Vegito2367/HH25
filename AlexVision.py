# pip install mediapipe opencv-python numpy websockets

import cv2
import mediapipe as mp
import numpy as np
import json
import time
from pathlib import Path
import asyncio
import websockets

# ============================================================================
# DEFAULTS (editable at runtime)
# ============================================================================
VMAX_X = 300.0          # px/s - REDUCED to 300
VMAX_Y = 300.0          # px/s - REDUCED to 300
DEADZONE_YAW = 10.0     # degrees - X axis deadzone
DEADZONE_ROLL = 10.0    # degrees - Y axis deadzone
HYSTERESIS_DEG = 1.0    # small hysteresis to prevent chatter
TAU_VEL = 0.18          # velocity slew time constant (seconds)
YAW_SMOOTHING = 0.7     # Smoothing factor for yaw (0-1, higher = more smoothing)

CALIB_FILE = "simple_head_calib.json"

# MediaPipe FaceMesh indices
L_EYE_OUT = 33
R_EYE_OUT = 263
L_EYE_IN = 133
R_EYE_IN = 362
NOSE_TIP = 1
NOSE_BRIDGE = 6
MOUTH_L = 61
MOUTH_R = 291

# WebSocket configuration
WS_HOST = 'localhost'
WS_PORT = 8765
WS_UPDATE_RATE = 0.03  # Send updates every 30ms (~33 FPS)

# Global variable to store connected WebSocket clients
connected_clients = set()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def initialize_camera():
    """Initialize camera with retry logic for macOS."""
    print("Initializing camera...")
    
    # Try different camera indices
    for camera_idx in [0, 1]:
        print(f"  Trying camera index {camera_idx}...")
        cap = cv2.VideoCapture(camera_idx)
        
        if not cap.isOpened():
            print(f"    Camera {camera_idx} could not be opened")
            continue
        
        # Give camera time to initialize
        time.sleep(1.0)
        
        # Set properties for better quality
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Try to read a few frames
        success_count = 0
        for attempt in range(10):
            ret, frame = cap.read()
            if ret and frame is not None:
                success_count += 1
                if success_count >= 3:
                    print(f"  ✓ Camera {camera_idx} initialized successfully")
                    print(f"    Resolution: {frame.shape[1]}x{frame.shape[0]}")
                    return cap, frame
            time.sleep(0.1)
        
        print(f"    Camera {camera_idx} opened but couldn't read frames")
        cap.release()
    
    return None, None


def estimate_yaw_with_pnp(landmarks, frame_shape):
    """
    Estimate yaw angle using cv2.solvePnP.
    Returns yaw in degrees or None if estimation fails.
    """
    h, w = frame_shape[:2]
    
    # Build simple intrinsic matrix
    fx = fy = w
    cx, cy = w / 2, h / 2
    camera_matrix = np.array([
        [fx, 0, cx],
        [0, fy, cy],
        [0, 0, 1]
    ], dtype=float)
    dist_coeffs = np.zeros(4)
    
    # 3D canonical model (approximate face landmarks in cm)
    model_points = np.array([
        (0.0, 0.0, 0.0),        # Nose tip
        (0.0, 3.0, -2.0),       # Nose bridge
        (-4.0, 1.0, -1.0),      # Left eye outer
        (4.0, 1.0, -1.0),       # Right eye outer
        (-2.5, 1.5, -1.0),      # Left eye inner
        (2.5, 1.5, -1.0),       # Right eye inner
        (-3.0, -3.0, -1.0),     # Left mouth corner
        (3.0, -3.0, -1.0),      # Right mouth corner
    ], dtype=float)
    
    # Corresponding 2D image points
    indices = [NOSE_TIP, NOSE_BRIDGE, L_EYE_OUT, R_EYE_OUT, 
               L_EYE_IN, R_EYE_IN, MOUTH_L, MOUTH_R]
    
    try:
        image_points = []
        for idx in indices:
            lm = landmarks[idx]
            image_points.append([lm.x * w, lm.y * h])
        image_points = np.array(image_points, dtype=float)
        
        # Use regular solvePnP
        success, rvec, tvec = cv2.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        
        if not success or rvec is None:
            return None
        
        # Convert rotation vector to matrix
        rmat, _ = cv2.Rodrigues(rvec)
        
        # Extract yaw (rotation around Y-axis in camera frame)
        yaw_rad = np.arctan2(rmat[0, 2], rmat[2, 2])
        yaw_deg = np.degrees(yaw_rad)
        
        # Reject extreme values
        if abs(yaw_deg) > 100:
            return None
        
        return yaw_deg
    except Exception as e:
        return None


def roll_from_eyes(landmarks, frame_shape):
    """
    Compute roll angle from eye line slope.
    Returns roll in degrees or None if computation fails.
    """
    try:
        h, w = frame_shape[:2]
        
        l_eye = landmarks[L_EYE_OUT]
        r_eye = landmarks[R_EYE_OUT]
        
        lx, ly = l_eye.x * w, l_eye.y * h
        rx, ry = r_eye.x * w, r_eye.y * h
        
        dx = rx - lx
        dy = ry - ly
        
        if abs(dx) < 1e-6:
            return 0.0
        
        # Negative sign to match "tilt left ear down = positive value" convention
        roll_rad = -np.arctan2(dy, dx)
        roll_deg = np.degrees(roll_rad)
        
        return roll_deg
    except Exception as e:
        return None


def run_calibration(cap, frame_shape):
    """
    Run 4-direction calibration + neutral.
    Returns calibration dict.
    """
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    steps = [
        ("LOOK STRAIGHT", "neutral"),
        ("TURN LEFT", "left"),
        ("TURN RIGHT", "right"),
        ("TILT LEFT EAR DOWN", "tilt_left"),
        ("TILT RIGHT EAR DOWN", "tilt_right"),
    ]
    
    calib = {}
    h, w = frame_shape[:2]
    
    for instruction, key in steps:
        print(f"\n[CALIBRATION] {instruction} - press SPACE when ready")
        
        samples_yaw = []
        samples_roll = []
        
        # Wait for space
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            
            # Try to get current readings
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)
            
            current_yaw = None
            current_roll = None
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                current_yaw = estimate_yaw_with_pnp(landmarks, frame.shape)
                current_roll = roll_from_eyes(landmarks, frame.shape)
            
            # Display instruction
            cv2.putText(frame, instruction, (50, h//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 3)
            cv2.putText(frame, "Press SPACE to capture", (50, h//2 + 80),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Show current values
            if current_yaw is not None and current_roll is not None:
                cv2.putText(frame, f"Yaw={current_yaw:.1f} Roll={current_roll:.1f}", 
                           (50, h//2 + 130),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "Detecting face...", (50, h//2 + 130),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            cv2.imshow("Head Cursor", frame)
            k = cv2.waitKey(1) & 0xFF
            if k == ord(' '):
                break
        
        # Collect samples for ~1.5 seconds (longer for better median)
        start_time = time.time()
        while time.time() - start_time < 1.5:
            ret, frame = cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)
            
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                yaw = estimate_yaw_with_pnp(landmarks, frame.shape)
                roll = roll_from_eyes(landmarks, frame.shape)
                
                if yaw is not None:
                    samples_yaw.append(yaw)
                if roll is not None:
                    samples_roll.append(roll)
            
            # Show collecting
            elapsed = time.time() - start_time
            cv2.putText(frame, f"Collecting... {len(samples_yaw)} samples", 
                       (50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Head Cursor", frame)
            cv2.waitKey(1)
        
        # Store median
        if len(samples_yaw) > 0:
            calib[f"{key}_yaw"] = float(np.median(samples_yaw))
        else:
            calib[f"{key}_yaw"] = 0.0
            
        if len(samples_roll) > 0:
            calib[f"{key}_roll"] = float(np.median(samples_roll))
        else:
            calib[f"{key}_roll"] = 0.0
        
        print(f"  Collected {len(samples_yaw)} yaw, {len(samples_roll)} roll samples")
    
    face_mesh.close()
    
    # Compute ROM and deadzone
    yaw0 = calib.get("neutral_yaw", 0)
    roll0 = calib.get("neutral_roll", 0)
    
    rom_yaw = max(
        abs(calib.get("right_yaw", yaw0) - yaw0),
        abs(yaw0 - calib.get("left_yaw", yaw0))
    )
    rom_roll = max(
        abs(calib.get("tilt_left_roll", roll0) - roll0),
        abs(calib.get("tilt_right_roll", roll0) - roll0)
    )
    
    calib["rom_yaw"] = rom_yaw
    calib["rom_roll"] = rom_roll
    calib["deadzone_yaw"] = max(5.0, 0.15 * rom_yaw)
    calib["deadzone_roll"] = max(5.0, 0.15 * rom_roll)
    
    print("\n[CALIBRATION COMPLETE]")
    print(f"  Neutral: yaw={yaw0:.1f}°, roll={roll0:.1f}°")
    print(f"  ROM: yaw={rom_yaw:.1f}°, roll={rom_roll:.1f}°")
    print(f"  Auto deadzone: yaw={calib['deadzone_yaw']:.2f}° roll={calib['deadzone_roll']:.2f}°")
    
    return calib


def update_velocity_constant(dyaw, droll, params, v_cmd_prev, dt):
    """
    Compute constant-speed command based on deadzone.
    Returns (v_cmd_x, v_cmd_y) with first-order smoothing.
    """
    deadzone_yaw = params["deadzone_yaw"]
    deadzone_roll = params["deadzone_roll"]
    hysteresis = params["hysteresis_deg"]
    vmax_x = params["vmax_x"]
    vmax_y = params["vmax_y"]
    tau = params["tau_vel"]
    
    # Target velocity
    v_target_x = 0.0
    v_target_y = 0.0
    
    # X-axis (yaw) - INVERTED
    if abs(dyaw) > deadzone_yaw + hysteresis:
        v_target_x = -vmax_x * np.sign(dyaw)
    elif abs(dyaw) < deadzone_yaw:
        v_target_x = 0.0
    else:
        if abs(v_cmd_prev[0]) > 1e-3:
            v_target_x = -vmax_x * np.sign(v_cmd_prev[0])
    
    # Y-axis (roll)
    if abs(droll) > deadzone_roll + hysteresis:
        v_target_y = -vmax_y * np.sign(droll)
    elif abs(droll) < deadzone_roll:
        v_target_y = 0.0
    else:
        if abs(v_cmd_prev[1]) > 1e-3:
            v_target_y = -vmax_y * np.sign(v_cmd_prev[1])
    
    # First-order smoothing
    alpha = dt / (tau + dt) if tau > 0 else 1.0
    v_cmd_x = v_cmd_prev[0] + (v_target_x - v_cmd_prev[0]) * alpha
    v_cmd_y = v_cmd_prev[1] + (v_target_y - v_cmd_prev[1]) * alpha
    
    return v_cmd_x, v_cmd_y


# ============================================================================
# WEBSOCKET FUNCTIONS
# ============================================================================

async def handle_client(websocket):
    """Handle a connected WebSocket client."""
    connected_clients.add(websocket)
    print(f"Client connected! Total clients: {len(connected_clients)}")
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        print(f"Client disconnected. Total clients: {len(connected_clients)}")


async def broadcast_cursor_position(x_percent, y_percent):
    """Send cursor position to all connected clients."""
    if not connected_clients:
        return
    
    command = {
        "command": "cursor",
        "x": f"{x_percent:.2f}",
        "y": f"{y_percent:.2f}"
    }
    
    # Send to all connected clients
    disconnected = set()
    for client in connected_clients:
        try:
            await client.send(json.dumps(command))
        except websockets.exceptions.ConnectionClosed:
            disconnected.add(client)
    
    # Remove disconnected clients
    for client in disconnected:
        connected_clients.discard(client)


async def websocket_server():
    """Start the WebSocket server."""
    print(f"Starting WebSocket server on ws://{WS_HOST}:{WS_PORT}")
    async with websockets.serve(handle_client, WS_HOST, WS_PORT):
        await asyncio.Future()  # run forever


# ============================================================================
# MAIN
# ============================================================================

async def main_loop():
    """Main head tracking loop that runs alongside WebSocket server."""
    # Initialize webcam
    cap, frame = initialize_camera()
    
    if cap is None or frame is None:
        print("\n❌ ERROR: Could not initialize webcam")
        print("\nTroubleshooting tips:")
        print("  1. Check if another app is using the camera")
        print("  2. Grant camera permissions in System Preferences > Security & Privacy")
        print("  3. Try restarting your computer")
        return
    
    h, w = frame.shape[:2]
    
    # Create larger window
    cv2.namedWindow("Head Cursor", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Head Cursor", 1280, 720)
    
    # Initialize MediaPipe FaceMesh
    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    # State variables
    calib = None
    cursor_x, cursor_y = w / 2, h / 2
    v_cmd = [0.0, 0.0]
    
    # PERSISTENT values - with SMOOTHING to prevent jumps
    last_valid_yaw = 0.0
    last_valid_roll = 0.0
    smoothed_yaw = 0.0
    smoothed_roll = 0.0
    
    params = {
        "vmax_x": VMAX_X,
        "vmax_y": VMAX_Y,
        "deadzone_yaw": DEADZONE_YAW,
        "deadzone_roll": DEADZONE_ROLL,
        "hysteresis_deg": HYSTERESIS_DEG,
        "tau_vel": TAU_VEL,
    }
    
    # FPS tracking
    fps = 0
    fps_time = time.time()
    fps_counter = 0
    
    prev_time = time.time()
    last_ws_send = time.time()
    
    print("\n=== HEAD CURSOR CONTROL ===")
    print("✓ Camera initialized successfully!")
    print("\nCONTROLS:")
    print("  - Turn head LEFT → cursor moves RIGHT (INVERTED)")
    print("  - Turn head RIGHT → cursor moves LEFT (INVERTED)")
    print("  - Tilt head (ear to shoulder) → cursor moves up/down")
    print("  - Speed: 300 px/s with 10° deadzone")
    print("\nKEYS:")
    print("  'c' - Calibrate (4 directions + neutral)")
    print("  's' / 'l' - Save / load calibration")
    print("  'r' - Recenter neutral to current position")
    print("  '[' / ']' - Decrease / increase speed")
    print("  '-' / '=' - Decrease / increase yaw deadzone")
    print("  ',' / '.' - Decrease / increase roll deadzone")
    print("  'q' or ESC - Quit\n")
    print(f"\nWebSocket server running on ws://{WS_HOST}:{WS_PORT}")
    print(f"Waiting for Godot client to connect...\n")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Warning: Failed to read frame, retrying...")
                await asyncio.sleep(0.1)
                continue
            
            # Mirror image
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            
            # Calculate dt and FPS
            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time
            
            fps_counter += 1
            if current_time - fps_time >= 1.0:
                fps = fps_counter
                fps_counter = 0
                fps_time = current_time
            
            # Initialize with smoothed values
            yaw = smoothed_yaw
            roll = smoothed_roll
            dyaw, droll = 0, 0
            
            # Process face
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)
            
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                
                # Always draw FaceMesh
                mp_drawing.draw_landmarks(
                    image=frame,
                    landmark_list=results.multi_face_landmarks[0],
                    connections=mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style()
                )
                
                # Estimate head pose
                yaw_new = estimate_yaw_with_pnp(landmarks, frame.shape)
                roll_new = roll_from_eyes(landmarks, frame.shape)
                
                # Update with SMOOTHING to prevent wild jumps
                if yaw_new is not None:
                    # Reject absurd frame-to-frame changes (>60° jump likely error)
                    if abs(yaw_new - smoothed_yaw) < 60:
                        # Exponential moving average
                        smoothed_yaw = YAW_SMOOTHING * smoothed_yaw + (1 - YAW_SMOOTHING) * yaw_new
                        last_valid_yaw = smoothed_yaw
                    yaw = smoothed_yaw
                
                if roll_new is not None:
                    smoothed_roll = 0.5 * smoothed_roll + 0.5 * roll_new
                    last_valid_roll = smoothed_roll
                    roll = smoothed_roll
                
                # Update cursor if calibrated
                if calib is not None:
                    yaw0 = calib.get("neutral_yaw", 0)
                    roll0 = calib.get("neutral_roll", 0)
                    
                    dyaw = yaw - yaw0
                    droll = roll - roll0
                    
                    # Use calibrated deadzones if available
                    if "deadzone_yaw" in calib:
                        params["deadzone_yaw"] = calib["deadzone_yaw"]
                    if "deadzone_roll" in calib:
                        params["deadzone_roll"] = calib["deadzone_roll"]
                    
                    # Update velocity
                    v_cmd[0], v_cmd[1] = update_velocity_constant(
                        dyaw, droll, params, v_cmd, dt
                    )
                    
                    # Integrate position
                    cursor_x += v_cmd[0] * dt
                    cursor_y += v_cmd[1] * dt
                    
                    # Clamp to window
                    cursor_x = np.clip(cursor_x, 0, w - 1)
                    cursor_y = np.clip(cursor_y, 0, h - 1)
            
            # Send cursor position via WebSocket at regular intervals
            if current_time - last_ws_send >= WS_UPDATE_RATE:
                # Convert to percentages (0-100)
                x_percent = (cursor_x / w) * 100.0
                y_percent = (cursor_y / h) * 100.0
                
                # Broadcast to all clients
                await broadcast_cursor_position(x_percent, y_percent)
                last_ws_send = current_time
            
            # Draw deadzone indicator
            cv2.circle(frame, (w//2, h//2), 60, (80, 80, 80), 2)
            cv2.putText(frame, "DEADZONE", (w//2 - 70, h//2 - 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
            
            # Draw CURSOR
            cursor_pos = (int(cursor_x), int(cursor_y))
            cv2.circle(frame, cursor_pos, 20, (255, 255, 255), 3)
            cv2.circle(frame, cursor_pos, 14, (0, 255, 0), -1)
            cv2.circle(frame, cursor_pos, 4, (255, 255, 255), -1)
            
            # Draw velocity vector
            if abs(v_cmd[0]) > 1 or abs(v_cmd[1]) > 1:
                end_x = int(cursor_x + v_cmd[0] * 0.08)
                end_y = int(cursor_y + v_cmd[1] * 0.08)
                cv2.arrowedLine(frame, cursor_pos, (end_x, end_y), 
                              (0, 255, 255), 3, tipLength=0.3)
            
            # Draw HUD
            hud_y = 30
            x_percent = (cursor_x / w) * 100.0
            y_percent = (cursor_y / h) * 100.0
            hud_lines = [
                f"FPS: {fps}",
                f"Yaw: {yaw:.1f}° (d: {dyaw:+.1f}°)",
                f"Roll: {roll:.1f}° (d: {droll:+.1f}°)",
                f"Speed: {params['vmax_x']:.0f} px/s",
                f"Deadzone: Yaw={params['deadzone_yaw']:.1f}° Roll={params['deadzone_roll']:.1f}°",
                f"Velocity: ({v_cmd[0]:+.0f}, {v_cmd[1]:+.0f}) px/s",
                f"Cursor: ({cursor_x:.0f}, {cursor_y:.0f}) = ({x_percent:.1f}%, {y_percent:.1f}%)",
                f"Calib: {'YES' if calib else 'NO - Press C'}",
                f"WS Clients: {len(connected_clients)}",
            ]
            
            for line in hud_lines:
                cv2.putText(frame, line, (15, hud_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                hud_y += 30
            
            # Draw control status
            status_y = h - 100
            status_text = []
            if calib:
                if abs(dyaw) > params["deadzone_yaw"]:
                    status_text.append(f"MOVING X: {'LEFT' if dyaw > 0 else 'RIGHT'}")
                if abs(droll) > params["deadzone_roll"]:
                    status_text.append(f"MOVING Y: {'DOWN' if droll > 0 else 'UP'}")
                if not status_text:
                    status_text.append("IN DEADZONE - STOPPED")
            else:
                status_text.append("PRESS 'C' TO CALIBRATE")
            
            for txt in status_text:
                cv2.putText(frame, txt, (15, status_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 3)
                status_y += 40
            
            cv2.imshow("Head Cursor", frame)
            
            # Handle keys (non-blocking)
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:
                break
            elif key == ord('c'):
                print("\n[Starting 4-direction calibration...]")
                new_calib = run_calibration(cap, (h, w))
                if new_calib is not None:
                    calib = new_calib
                    # Reset smoothing after calibration
                    smoothed_yaw = calib.get("neutral_yaw", 0)
                    smoothed_roll = calib.get("neutral_roll", 0)
            elif key == ord('s'):
                if calib:
                    with open(CALIB_FILE, 'w') as f:
                        json.dump(calib, f, indent=2)
                    print(f"\n[Calibration saved to {CALIB_FILE}]")
                else:
                    print("\n[No calibration to save]")
            elif key == ord('l'):
                if Path(CALIB_FILE).exists():
                    with open(CALIB_FILE, 'r') as f:
                        calib = json.load(f)
                    print(f"\n[Calibration loaded]")
            elif key == ord('r'):
                if calib:
                    calib["neutral_yaw"] = smoothed_yaw
                    calib["neutral_roll"] = smoothed_roll
                    print(f"\n[Recentered: yaw={smoothed_yaw:.1f}°, roll={smoothed_roll:.1f}°]")
            elif key == ord('['):
                params["vmax_x"] = max(100, params["vmax_x"] - 50)
                params["vmax_y"] = params["vmax_x"]
                print(f"\n[Speed: {params['vmax_x']:.0f} px/s]")
            elif key == ord(']'):
                params["vmax_x"] = min(2000, params["vmax_x"] + 50)
                params["vmax_y"] = params["vmax_x"]
                print(f"\n[Speed: {params['vmax_x']:.0f} px/s]")
            elif key == ord('-'):
                params["deadzone_yaw"] = max(1.0, params["deadzone_yaw"] - 1.0)
                print(f"\n[Yaw Deadzone: {params['deadzone_yaw']:.1f}°]")
            elif key == ord('='):
                params["deadzone_yaw"] = min(30, params["deadzone_yaw"] + 1.0)
                print(f"\n[Yaw Deadzone: {params['deadzone_yaw']:.1f}°]")
            elif key == ord(','):
                params["deadzone_roll"] = max(1.0, params["deadzone_roll"] - 1.0)
                print(f"\n[Roll Deadzone: {params['deadzone_roll']:.1f}°]")
            elif key == ord('.'):
                params["deadzone_roll"] = min(30, params["deadzone_roll"] + 1.0)
                print(f"\n[Roll Deadzone: {params['deadzone_roll']:.1f}°]")
            
            # Allow other async tasks to run
            await asyncio.sleep(0.001)
    
    finally:
        face_mesh.close()
        cap.release()
        cv2.destroyAllWindows()
        print("\n[Exiting...]")


async def main():
    """Run both the WebSocket server and head tracking loop concurrently."""
    # Run both tasks concurrently
    await asyncio.gather(
        websocket_server(),
        main_loop()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[Interrupted by user]")