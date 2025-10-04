import argparse, json, socket, time
from collections import deque
import cv2, mediapipe as mp, numpy as np

# ---------------- Config (tune if needed) ----------------
BROW_BASELINE_FRAMES = 60   # frames to learn neutral brow distance
BROW_UP_FACTOR = 0.12       # lowered: easier to trigger brow_up
MOUTH_OPEN_THRESH = 0.38    # mouth-aspect-ratio threshold for open/close
SEND_FPS = 30               # UDP send rate

# Blink tuning (more sensitive)
BLINK_EAR_THRESH = 0.22     # raised a bit so blinks register sooner
BLINK_MIN_FRAMES = 1        # count blink if eyes closed for >= 1 frame
DOUBLE_BLINK_WINDOW = 0.6   # seconds between two blinks to count as double
DOUBLE_BLINK_HOLD = 0.2     # seconds to hold the output flag = True

# MediaPipe FaceMesh
mp_face_mesh = mp.solutions.face_mesh

# Landmark indices (MediaPipe)
# Mouth
MOUTH_L, MOUTH_R = 61, 291
MOUTH_UP, MOUTH_DN = 13, 14
# Brow vs eyelid (use left side for simplicity)
L_BROW = 105
L_EYE_TOP = 159
# Inter-ocular normalization references
L_EYE_IN, R_EYE_IN = 133, 362
# Eyes
L_EYE_OUT, L_EYE_INNER = 33, 133
R_EYE_OUT, R_EYE_INNER = 263, 362
L_EYE_UP,  L_EYE_DN = 159, 145
R_EYE_UP,  R_EYE_DN = 386, 374

def dist(a, b): 
    return float(np.linalg.norm(a - b))

def mouth_aspect_ratio(lm):
    L = lm[MOUTH_L]; R = lm[MOUTH_R]
    U = lm[MOUTH_UP]; D = lm[MOUTH_DN]
    horiz = dist(L, R) + 1e-6
    vert = dist(U, D)
    return vert / horiz

def eye_aspect_ratio(lm, up, dn, inn, outn):
    vertical = dist(lm[up], lm[dn])
    horiz = dist(lm[inn], lm[outn]) + 1e-6
    return vertical / horiz

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", type=str, default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9001)
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    # Camera (Windows-friendly backends)
    cap = cv2.VideoCapture(args.camera, cv2.CAP_MSMF)
    if not cap.isOpened():
        cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("ERROR: cannot open camera"); return

    if args.show:
        cv2.namedWindow("Mouth & Brows (Python→UDP)", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Mouth & Brows (Python→UDP)", 960, 540)

    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=False,          # iris not needed here
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    brow_samples = deque(maxlen=BROW_BASELINE_FRAMES)
    brow_baseline = None

    # Blink state
    l_run = 0
    r_run = 0
    blink_active = False              # current blink state (closed)
    blink_times = deque(maxlen=4)     # recent blink "edges" (open->closed) times
    double_blink_until = 0.0          # hold-true timer

    last_send = 0
    w = h = 0

    print("[i] Hold a neutral face for ~2 seconds to set brow baseline. Press Q to quit.")
    while True:
        ok, frame = cap.read()
        if not ok: break
        if w == 0: h, w = frame.shape[:2]

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = face_mesh.process(rgb)

        mouth_open = False
        brow_up = False
        double_blink = False

        if res.multi_face_landmarks:
            lm = np.array([[p.x * w, p.y * h] for p in res.multi_face_landmarks[0].landmark], dtype=np.float32)

            # ----- Mouth open/close (MAR) -----
            mar = mouth_aspect_ratio(lm)
            mouth_open = mar > MOUTH_OPEN_THRESH

            # ----- Eyebrow up/down (relative to baseline) -----
            brow_dist = dist(lm[L_BROW], lm[L_EYE_TOP])
            inter_ocular = dist(lm[L_EYE_IN], lm[R_EYE_IN]) + 1e-6
            brow_norm = brow_dist / inter_ocular

            if brow_baseline is None:
                brow_samples.append(brow_norm)
                if len(brow_samples) == brow_samples.maxlen:
                    brow_baseline = float(np.median(brow_samples))
            else:
                brow_up = brow_norm >= (brow_baseline * (1.0 + BROW_UP_FACTOR))

            # ----- Blink detection (more sensitive double-blink) -----
            l_ear = eye_aspect_ratio(lm, L_EYE_UP, L_EYE_DN, L_EYE_INNER, L_EYE_OUT)
            r_ear = eye_aspect_ratio(lm, R_EYE_UP, R_EYE_DN, R_EYE_INNER, R_EYE_OUT)

            if l_ear < BLINK_EAR_THRESH:
                l_run += 1
            else:
                l_run = 0
            if r_ear < BLINK_EAR_THRESH:
                r_run += 1
            else:
                r_run = 0

            is_blink = (l_run >= BLINK_MIN_FRAMES) and (r_run >= BLINK_MIN_FRAMES)

            # Detect the blink "edge" (transition open -> closed)
            if is_blink and not blink_active:
                t = time.time()
                blink_times.append(t)
                # Check last two edges within window
                if len(blink_times) >= 2:
                    if (blink_times[-1] - blink_times[-2]) <= DOUBLE_BLINK_WINDOW:
                        double_blink_until = t + DOUBLE_BLINK_HOLD
                blink_active = True
            # Reset active flag when eyes open again
            if not is_blink and blink_active:
                blink_active = False

            # Output flag held briefly so receiver can catch it
            if time.time() < double_blink_until:
                double_blink = True

            if args.show:
                cv2.putText(frame, f"MouthOpen:{mouth_open} (MAR {mar:.2f})", (10, 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,200,255), 2)
                if brow_baseline is None:
                    cv2.putText(frame, "Brow baseline calibrating...", (10, 52),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50,200,50), 2)
                else:
                    cv2.putText(frame, f"BrowUp:{brow_up}", (10, 52),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,200,255), 2)
                cv2.putText(frame, f"DoubleBlink:{double_blink}", (10, 76),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200,200,0), 2)
        else:
            l_run = 0
            r_run = 0
            if args.show:
                cv2.putText(frame, "No face", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

        # ----- Send JSON at ~SEND_FPS -----
        now = time.time()
        if now - last_send >= 1.0 / SEND_FPS:
            payload = {"mouth_open": bool(mouth_open), "brow_up": bool(brow_up), "double_blink": bool(double_blink)}
            try:
                sock.sendto(json.dumps(payload).encode("utf-8"), (args.host, args.port))
            except OSError:
                pass
            last_send = now

        if args.show:
            cv2.imshow("Mouth & Brows (Python→UDP)", frame)
            k = cv2.waitKey(1) & 0xFF
            if k in (ord('q'), ord('Q')): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
