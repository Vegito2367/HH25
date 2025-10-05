# pip install mediapipe opencv-python numpy websockets

import cv2
import mediapipe as mp
import numpy as np
import json
import time
from pathlib import Path
import asyncio
import websockets
from collections import deque

# ============================================================================
# DEFAULTS (editable at runtime)
# ============================================================================
VMAX_X = 300.0          # px/s
VMAX_Y = 300.0          # px/s
DEADZONE_YAW = 10.0     # degrees - X axis deadzone
DEADZONE_ROLL = 10.0    # degrees - Y axis deadzone
HYSTERESIS_DEG = 1.0    # small hysteresis to prevent chatter
TAU_VEL = 0.18          # velocity slew time constant (seconds)
YAW_SMOOTHING = 0.3     # Smoothing factor for yaw (0-1, higher = more smoothing)

# Face gesture detection config
BROW_BASELINE_FRAMES = 60   # frames to learn neutral brow distance
BROW_UP_FACTOR = 0.20       # increased: requires more eyebrow movement to trigger
BROW_HOLD_TIME = 0.65       # seconds eyebrows must be held up to trigger delete
MOUTH_OPEN_THRESH = 0.38    # mouth-aspect-ratio threshold for open/close
BLINK_EAR_THRESH = 0.22     # raised a bit so blinks register sooner
BLINK_MIN_FRAMES = 1        # count blink if eyes closed for >= 1 frame
TRIPLE_BLINK_WINDOW = 1.2   # seconds window for three blinks to cycle mode
TRIPLE_BLINK_HOLD = 0.2     # seconds to hold the output flag = True

CALIB_FILE = "simple_head_calib.json"

# MediaPipe FaceMesh indices
L_EYE_OUT = 33
R_EYE_OUT = 263
L_EYE_IN = 133
R_EYE_IN = 362
NOSE_TIP = 1
NOSE_BRIDGE = 6

# Face gesture landmarks
MOUTH_L, MOUTH_R = 61, 291
MOUTH_UP, MOUTH_DN = 13, 14
L_BROW = 105
L_EYE_TOP = 159
L_EYE_UP, L_EYE_DN = 159, 145
R_EYE_UP, R_EYE_DN = 386, 374
L_EYE_INNER, R_EYE_INNER = 133, 362

# WebSocket configuration
WS_HOST = 'localhost'
WS_PORT = 8765
WS_UPDATE_RATE = 0.03  # Send updates every 30ms (~33 FPS)
SELECT_CLICK_COOLDOWN = 2.0  # Minimum seconds between select/click commands

# Global variable to store connected WebSocket clients
connected_clients = set()

# Global flag for shutdown
shutdown_flag = False

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


def dist(a, b): 
    return float(np.linalg.norm(a - b))


def mouth_aspect_ratio(lm, w, h):
    """Calculate mouth aspect ratio for open/close detection."""
    L = np.array([lm[MOUTH_L].x * w, lm[MOUTH_L].y * h])
    R = np.array([lm[MOUTH_R].x * w, lm[MOUTH_R].y * h])
    U = np.array([lm[MOUTH_UP].x * w, lm[MOUTH_UP].y * h])
    D = np.array([lm[MOUTH_DN].x * w, lm[MOUTH_DN].y * h])
    horiz = dist(L, R) + 1e-6
    vert = dist(U, D)
    return vert / horiz


def eye_aspect_ratio(lm, up, dn, inn, outn, w, h):
    """Calculate eye aspect ratio for blink detection."""
    vertical = dist(
        np.array([lm[up].x * w, lm[up].y * h]),
        np.array([lm[dn].x * w, lm[dn].y * h])
    )
    horiz = dist(
        np.array([lm[inn].x * w, lm[inn].y * h]),
        np.array([lm[outn].x * w, lm[outn].y * h])
    ) + 1e-6
    return vertical / horiz


def estimate_yaw_geometric(landmarks, frame_shape):
    """
    Estimate yaw using geometric method: nose position relative to eyes.
    This is much more robust than solvePnP.
    Returns yaw in arbitrary units (not degrees, but proportional to head turn).
    """
    try:
        h, w = frame_shape[:2]
        
        # Get eye positions
        l_eye = landmarks[L_EYE_OUT]
        r_eye = landmarks[R_EYE_OUT]
        nose = landmarks[NOSE_TIP]
        
        # Convert to pixel coordinates
        l_eye_x = l_eye.x * w
        r_eye_x = r_eye.x * w
        nose_x = nose.x * w
        
        # Calculate eye center
        eye_center_x = (l_eye_x + r_eye_x) / 2.0
        
        # Calculate eye width (distance between eyes)
        eye_width = abs(r_eye_x - l_eye_x)
        
        if eye_width < 10:  # Too small, probably bad detection
            return None
        
        # Calculate nose offset from eye center, normalized by eye width
        # This gives a ratio that's approximately proportional to yaw angle
        nose_offset = nose_x - eye_center_x
        yaw_ratio = nose_offset / eye_width
        
        # Convert to pseudo-degrees (scale by 50 to get reasonable range)
        yaw_deg = yaw_ratio * 50.0
        
        # Clamp to reasonable range
        yaw_deg = np.clip(yaw_deg, -60, 60)
        
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
                current_yaw = estimate_yaw_geometric(landmarks, frame.shape)
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
        
        # Collect samples for ~1.5 seconds
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
                yaw = estimate_yaw_geometric(landmarks, frame.shape)
                roll = roll_from_eyes(landmarks, frame.shape)
                
                if yaw is not None:
                    samples_yaw.append(yaw)
                if roll is not None:
                    samples_roll.append(roll)
            
            # Show collecting
            cv2.putText(frame, f"Collecting... {len(samples_yaw)} samples", 
                       (50, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Head Cursor", frame)
            cv2.waitKey(1)
        
        # Store median
        if len(samples_yaw) > 5:
            calib[f"{key}_yaw"] = float(np.median(samples_yaw))
        else:
            print(f"  WARNING: Only {len(samples_yaw)} yaw samples - using 0.0")
            calib[f"{key}_yaw"] = 0.0
            
        if len(samples_roll) > 5:
            calib[f"{key}_roll"] = float(np.median(samples_roll))
        else:
            print(f"  WARNING: Only {len(samples_roll)} roll samples - using 0.0")
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
    calib["deadzone_yaw"] = max(8.0, 0.25 * rom_yaw)  # Larger minimum deadzone
    calib["deadzone_roll"] = max(8.0, 0.25 * rom_roll)
    
    print("\n[CALIBRATION COMPLETE]")
    print(f"  Neutral: yaw={yaw0:.1f}, roll={roll0:.1f}°")
    print(f"  ROM: yaw={rom_yaw:.1f}, roll={rom_roll:.1f}°")
    print(f"  Auto deadzone: yaw={calib['deadzone_yaw']:.2f} roll={calib['deadzone_roll']:.2f}°")
    
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
    
    # X-axis (yaw) - NO LONGER INVERTED
    if abs(dyaw) > deadzone_yaw + hysteresis:
        v_target_x = vmax_x * np.sign(dyaw)
    elif abs(dyaw) < deadzone_yaw:
        v_target_x = 0.0
    else:
        if abs(v_cmd_prev[0]) > 1e-3:
            v_target_x = vmax_x * np.sign(v_cmd_prev[0])
    
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


async def broadcast_cursor(x_percent, y_percent, mode_name):
    """Send cursor position to all connected clients."""
    if not connected_clients:
        return
    
    # Send command based on current mode
    command = {
        "command": mode_name,
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


async def broadcast_command(command_name, x_percent, y_percent):
    """Send a command with coordinates to all connected clients."""
    command = {
        "command": command_name,
        "x": f"{x_percent:.2f}",
        "y": f"{y_percent:.2f}"
    }
    
    # Send to all connected clients even if none connected (for logging)
    disconnected = set()
    for client in connected_clients:
        try:
            await client.send(json.dumps(command))
        except websockets.exceptions.ConnectionClosed:
            disconnected.add(client)
    
    # Remove disconnected clients
    for client in disconnected:
        connected_clients.discard(client)
    
    return command


async def websocket_server():
    """Start the WebSocket server."""
    global shutdown_flag
    print(f"Starting WebSocket server on ws://{WS_HOST}:{WS_PORT}")
    
    async with websockets.serve(handle_client, WS_HOST, WS_PORT):
        # Wait until shutdown flag is set
        while not shutdown_flag:
            await asyncio.sleep(0.1)
        print("WebSocket server shutting down...")


# ============================================================================
# MAIN
# ============================================================================

async def main_loop():
    """Main head tracking loop that runs alongside WebSocket server."""
    global shutdown_flag
    
    # Initialize webcam
    cap, frame = initialize_camera()
    
    if cap is None or frame is None:
        print("\n❌ ERROR: Could not initialize webcam")
        print("\nTroubleshooting tips:")
        print("  1. Check if another app is using the camera")
        print("  2. Grant camera permissions in System Preferences > Security & Privacy")
        print("  3. Try restarting your computer")
        shutdown_flag = True
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
    
    # Initialize to None so first detection sets the value
    smoothed_yaw = None
    smoothed_roll = None
    
    # Face gesture state
    brow_samples = deque(maxlen=BROW_BASELINE_FRAMES)
    brow_baseline = None
    l_run = 0
    r_run = 0
    blink_active = False
    blink_times = deque(maxlen=4)
    triple_blink_until = 0.0
    
    # Previous states for edge detection
    prev_mouth_open = False
    prev_brow_up = False
    prev_triple_blink = False
    
    # Brow hold timer
    brow_up_start_time = None
    brow_triggered = False
    
    # Rate limiting for select/click commands
    last_select_click_time = 0.0
    
    # Mode cycling: 0=cursor, 1=move, 2=stagerotate
    current_mode = 0
    mode_names = ["cursor", "move", "cursor"]
    
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
    
    print("\n=== HEAD CURSOR + FACE GESTURES CONTROL ===")
    print("✓ Camera initialized successfully!")
    print("✓ Using robust geometric yaw estimation")
    print("\nHEAD CONTROLS:")
    print("  - Turn head LEFT → cursor moves LEFT")
    print("  - Turn head RIGHT → cursor moves RIGHT")
    print("  - Tilt head (ear to shoulder) → cursor moves up/down")
    print("\nFACE GESTURES:")
    print("  - Mouth open → 'select' (or 'click' if in bottom 15%)")
    print("    * Rate limited: 2 second cooldown between select/click")
    print("  - Triple blink (3 blinks in 1 sec) → cycles mode (cursor → move → stagerotate)")
    print("  - Eyebrow raise (hold 0.65s) → 'delete' command")
    print("\nWEBSOCKET COMMANDS:")
    print("  - cursor/move/stagerotate: continuous position updates (based on mode)")
    print("  - select: mouth open outside click zone")
    print("  - click: mouth open in click zone")
    print("  - delete: eyebrow raise (hold 0.65s)")
    print("\nKEYS:")
    print("  'c' - Calibrate (4 directions + neutral)")
    print("  's' / 'l' - Save / load calibration")
    print("  'r' - Recenter neutral to current position")
    print("  '[' / ']' - Decrease / increase speed")
    print("  '-' / '=' - Decrease / increase yaw deadzone")
    print("  ',' / '.' - Decrease / increase roll deadzone")
    print("  'q' or ESC - Quit\n")
    print(f"\nWebSocket server running on ws://{WS_HOST}:{WS_PORT}")
    print(f"Broadcasting: cursor position + face gestures\n")
    
    try:
        while not shutdown_flag:
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
            
            # Initialize with smoothed values (or 0 if None)
            yaw = smoothed_yaw if smoothed_yaw is not None else 0.0
            roll = smoothed_roll if smoothed_roll is not None else 0.0
            dyaw, droll = 0, 0
            
            # Face gesture states
            mouth_open = False
            brow_up = False
            triple_blink = False
            
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
                yaw_new = estimate_yaw_geometric(landmarks, frame.shape)
                roll_new = roll_from_eyes(landmarks, frame.shape)
                
                # Update with smoothing
                if yaw_new is not None:
                    if smoothed_yaw is None:
                        smoothed_yaw = yaw_new
                    else:
                        smoothed_yaw = YAW_SMOOTHING * smoothed_yaw + (1 - YAW_SMOOTHING) * yaw_new
                    yaw = smoothed_yaw
                
                if roll_new is not None:
                    if smoothed_roll is None:
                        smoothed_roll = roll_new
                    else:
                        smoothed_roll = 0.5 * smoothed_roll + 0.5 * roll_new
                    roll = smoothed_roll
                
                # ----- Face Gesture Detection -----
                
                # Mouth open/close
                mar = mouth_aspect_ratio(landmarks, w, h)
                mouth_open = mar > MOUTH_OPEN_THRESH
                
                # Eyebrow up/down (but first check if eyes are open)
                # Calculate eye aspect ratios first
                l_ear = eye_aspect_ratio(landmarks, L_EYE_UP, L_EYE_DN, L_EYE_INNER, L_EYE_OUT, w, h)
                r_ear = eye_aspect_ratio(landmarks, R_EYE_UP, R_EYE_DN, R_EYE_INNER, R_EYE_OUT, w, h)
                
                # Only detect eyebrow raise if eyes are open
                eyes_open = (l_ear > BLINK_EAR_THRESH) and (r_ear > BLINK_EAR_THRESH)
                
                if eyes_open:
                    brow_pt = np.array([landmarks[L_BROW].x * w, landmarks[L_BROW].y * h])
                    eye_top_pt = np.array([landmarks[L_EYE_TOP].x * w, landmarks[L_EYE_TOP].y * h])
                    brow_dist = dist(brow_pt, eye_top_pt)
                    
                    l_eye_in = np.array([landmarks[L_EYE_IN].x * w, landmarks[L_EYE_IN].y * h])
                    r_eye_in = np.array([landmarks[R_EYE_IN].x * w, landmarks[R_EYE_IN].y * h])
                    inter_ocular = dist(l_eye_in, r_eye_in) + 1e-6
                    brow_norm = brow_dist / inter_ocular
                    
                    if brow_baseline is None:
                        brow_samples.append(brow_norm)
                        if len(brow_samples) == brow_samples.maxlen:
                            brow_baseline = float(np.median(brow_samples))
                    else:
                        brow_up = brow_norm >= (brow_baseline * (1.0 + BROW_UP_FACTOR))
                
                # MUTUAL EXCLUSION: If mouth is open or eyes closed, brow cannot be up
                if mouth_open or not eyes_open:
                    brow_up = False
                
                # Blink detection
                if l_ear < BLINK_EAR_THRESH:
                    l_run += 1
                else:
                    l_run = 0
                if r_ear < BLINK_EAR_THRESH:
                    r_run += 1
                else:
                    r_run = 0
                
                is_blink = (l_run >= BLINK_MIN_FRAMES) and (r_run >= BLINK_MIN_FRAMES)
                
                if is_blink and not blink_active:
                    t = time.time()
                    
                    # Remove old blinks outside the time window
                    while blink_times and (t - blink_times[0]) > TRIPLE_BLINK_WINDOW:
                        blink_times.popleft()
                    
                    # Add current blink
                    blink_times.append(t)
                    
                    # Log blink timing
                    if len(blink_times) >= 2:
                        time_since_last = t - blink_times[-2]
                        print(f"[Blink detected] Count: {len(blink_times)}, Time since last: {time_since_last:.3f}s")
                    else:
                        print(f"[Blink detected] Count: 1 (starting new sequence)")
                    
                    # Check if we have 3 blinks within the window
                    if len(blink_times) >= 3:
                        # Check if first and third blink are within window
                        time_span = blink_times[-1] - blink_times[-3]
                        if time_span <= TRIPLE_BLINK_WINDOW:
                            triple_blink_until = t + TRIPLE_BLINK_HOLD
                            print(f"[TRIPLE BLINK DETECTED] All 3 blinks in {time_span:.3f}s")
                        else:
                            print(f"[Blink timing] 3 blinks but too slow: {time_span:.3f}s > {TRIPLE_BLINK_WINDOW}s")
                    
                    blink_active = True
                
                if not is_blink and blink_active:
                    blink_active = False
                
                if time.time() < triple_blink_until:
                    triple_blink = True
                
                # Update cursor if calibrated
                if calib is not None and smoothed_yaw is not None:
                    yaw0 = calib.get("neutral_yaw", 0)
                    roll0 = calib.get("neutral_roll", 0)
                    
                    dyaw = yaw - yaw0
                    droll = roll - roll0
                    
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
                else:
                    v_cmd = [0.0, 0.0]
            else:
                # No face detected
                v_cmd = [0.0, 0.0]
                l_run = 0
                r_run = 0
            
            # Send cursor position via WebSocket at regular intervals
            if current_time - last_ws_send >= WS_UPDATE_RATE:
                x_percent = (cursor_x / w) * 100.0
                y_percent = (cursor_y / h) * 100.0
                
                await broadcast_cursor(x_percent, y_percent, mode_names[current_mode])
                last_ws_send = current_time
            
            # Send face gesture commands when state changes
            if mouth_open != prev_mouth_open:
                if mouth_open:
                    # Check if enough time has passed since last select/click
                    if current_time - last_select_click_time >= SELECT_CLICK_COOLDOWN:
                        x_percent = (cursor_x / w) * 100.0
                        y_percent = (cursor_y / h) * 100.0
                        if y_percent >= 85.0:
                            cmd = await broadcast_command("click", x_percent, y_percent)
                            print(f"\n[WS] {json.dumps(cmd)}")
                        else:
                            cmd = await broadcast_command("select", x_percent, y_percent)
                            print(f"\n[WS] {json.dumps(cmd)}")
                        last_select_click_time = current_time
                    else:
                        # Cooldown still active
                        remaining = SELECT_CLICK_COOLDOWN - (current_time - last_select_click_time)
                        print(f"\n[Select/Click on cooldown: {remaining:.1f}s remaining]")
                prev_mouth_open = mouth_open
            
            if brow_up != prev_brow_up:
                if brow_up:
                    # Eyebrows just went up - start timer
                    brow_up_start_time = current_time
                    brow_triggered = False
                else:
                    # Eyebrows went down - reset timer
                    brow_up_start_time = None
                    brow_triggered = False
                prev_brow_up = brow_up
            
            # Check if eyebrows have been held up long enough
            if brow_up and brow_up_start_time is not None and not brow_triggered:
                hold_duration = current_time - brow_up_start_time
                if hold_duration >= BROW_HOLD_TIME:
                    # Brow sends delete command
                    x_percent = (cursor_x / w) * 100.0
                    y_percent = (cursor_y / h) * 100.0
                    cmd = await broadcast_command("delete", x_percent, y_percent)
                    print(f"\n[WS] {json.dumps(cmd)}")
                    brow_triggered = True
            
            if triple_blink and not prev_triple_blink:
                # Triple blink cycles through cursor → move → stagerotate
                current_mode = (current_mode + 1) % 3
                x_percent = (cursor_x / w) * 100.0
                y_percent = (cursor_y / h) * 100.0
                cmd = await broadcast_command(mode_names[current_mode], x_percent, y_percent)
                print(f"\n[WS] {json.dumps(cmd)}")
            prev_triple_blink = triple_blink
            
            # Draw deadzone indicator
            cv2.circle(frame, (w//2, h//2), 60, (80, 80, 80), 2)
            cv2.putText(frame, "DEADZONE", (w//2 - 70, h//2 - 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
            
            # Draw click zone indicator (bottom 15%)
            click_zone_y = int(h * 0.85)
            cv2.line(frame, (0, click_zone_y), (w, click_zone_y), (255, 0, 255), 2)
            cv2.putText(frame, "CLICK ZONE", (w - 200, click_zone_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
            
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
            
            # Draw HUD (top)
            hud_y = 30
            x_percent = (cursor_x / w) * 100.0
            y_percent = (cursor_y / h) * 100.0
            in_click_zone = y_percent >= 85.0
            cooldown_remaining = max(0, SELECT_CLICK_COOLDOWN - (current_time - last_select_click_time))
            
            # Determine select/click status
            if cooldown_remaining > 0:
                status_text = f"ON COOLDOWN ({cooldown_remaining:.1f}s)"
            else:
                status_text = "READY"
            
            if in_click_zone:
                next_action = "CLICK"
            else:
                next_action = "SELECT"
            
            hud_lines = [
                f"FPS: {fps}",
                f"MODE: {mode_names[current_mode]} | Click Zone: {in_click_zone}",
                f"SELECT/CLICK: {status_text} | Next: {next_action}",
                f"Yaw: {yaw:.1f} (d: {dyaw:+.1f})",
                f"Roll: {roll:.1f}° (d: {droll:+.1f}°)",
                f"Speed: {params['vmax_x']:.0f} px/s",
                f"Deadzone: Yaw={params['deadzone_yaw']:.1f} Roll={params['deadzone_roll']:.1f}°",
                f"Velocity: ({v_cmd[0]:+.0f}, {v_cmd[1]:+.0f}) px/s",
                f"Cursor: ({cursor_x:.0f}, {cursor_y:.0f}) = ({x_percent:.1f}%, {y_percent:.1f}%)",
                f"Mouth: {mouth_open} | Brow: {brow_up} {'(blocked)' if mouth_open and not brow_up else ''} | Blink3x: {triple_blink}",
                f"Calib: {'YES' if calib else 'NO - Press C'} | Brow: {'SET' if brow_baseline else 'LEARNING'}",
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
                    status_text.append(f"MOVING X: {'RIGHT' if dyaw > 0 else 'LEFT'}")
                if abs(droll) > params["deadzone_roll"]:
                    status_text.append(f"MOVING Y: {'UP' if droll > 0 else 'DOWN'}")
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
                print("\n[ESC/Q pressed - shutting down...]")
                shutdown_flag = True
                break
            elif key == ord('c'):
                print("\n[Starting 4-direction calibration...]")
                print("TIP: Keep your head at a normal distance from camera")
                new_calib = run_calibration(cap, (h, w))
                if new_calib is not None:
                    calib = new_calib
                    smoothed_yaw = calib.get("neutral_yaw", 0)
                    smoothed_roll = calib.get("neutral_roll", 0)
                    # Apply calibrated deadzones to params (only once after calibration)
                    params["deadzone_yaw"] = calib.get("deadzone_yaw", DEADZONE_YAW)
                    params["deadzone_roll"] = calib.get("deadzone_roll", DEADZONE_ROLL)
                    print(f"[Applied calibrated deadzones: yaw={params['deadzone_yaw']:.1f} roll={params['deadzone_roll']:.1f}°]")
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
                    if smoothed_yaw is None:
                        smoothed_yaw = calib.get("neutral_yaw", 0)
                    if smoothed_roll is None:
                        smoothed_roll = calib.get("neutral_roll", 0)
                    # Apply loaded deadzones to params
                    params["deadzone_yaw"] = calib.get("deadzone_yaw", DEADZONE_YAW)
                    params["deadzone_roll"] = calib.get("deadzone_roll", DEADZONE_ROLL)
            elif key == ord('r'):
                if calib and smoothed_yaw is not None and smoothed_roll is not None:
                    calib["neutral_yaw"] = smoothed_yaw
                    calib["neutral_roll"] = smoothed_roll
                    print(f"\n[Recentered: yaw={smoothed_yaw:.1f}, roll={smoothed_roll:.1f}°]")
            elif key == ord('['):
                params["vmax_x"] = max(100, params["vmax_x"] - 50)
                params["vmax_y"] = params["vmax_x"]
                print(f"\n[Speed: {params['vmax_x']:.0f} px/s]")
            elif key == ord(']'):
                params["vmax_x"] = min(2000, params["vmax_x"] + 50)
                params["vmax_y"] = params["vmax_x"]
                print(f"\n[Speed: {params['vmax_x']:.0f} px/s]")
            elif key == ord('-'):
                params["deadzone_yaw"] = max(0.5, params["deadzone_yaw"] - 0.5)
                print(f"\n[Yaw Deadzone: {params['deadzone_yaw']:.1f}]")
            elif key == ord('='):
                params["deadzone_yaw"] = min(30, params["deadzone_yaw"] + 0.5)
                print(f"\n[Yaw Deadzone: {params['deadzone_yaw']:.1f}]")
            elif key == ord(','):
                params["deadzone_roll"] = max(1.0, params["deadzone_roll"] - 1.0)
                print(f"\n[Roll Deadzone: {params['deadzone_roll']:.1f}°]")
            elif key == ord('.'):
                params["deadzone_roll"] = min(30, params["deadzone_roll"] + 1.0)
                print(f"\n[Roll Deadzone: {params['deadzone_roll']:.1f}°]")
            
            # Allow other async tasks to run
            await asyncio.sleep(0.001)
    
    finally:
        print("[Cleaning up camera and windows...]")
        face_mesh.close()
        cap.release()
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        shutdown_flag = True
        print("[Cleanup complete]")


async def main():
    """Run both the WebSocket server and head tracking loop concurrently."""
    global shutdown_flag
    
    # Create tasks
    ws_task = asyncio.create_task(websocket_server())
    main_task = asyncio.create_task(main_loop())
    
    # Wait for main loop to complete
    await main_task
    
    # Cancel websocket server
    ws_task.cancel()
    try:
        await ws_task
    except asyncio.CancelledError:
        pass
    
    print("\n[All tasks completed]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[Interrupted by user]")
    finally:
        cv2.destroyAllWindows()
        print("[Exit complete]")