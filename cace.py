import argparse, json, socket, time
from collections import deque
import cv2, mediapipe as mp, numpy as np

# ---------------- Config (tune if needed) ----------------
BROW_BASELINE_FRAMES = 60   # frames to learn neutral brow distance
BROW_UP_FACTOR = 0.20       # % above baseline to count as "up" (e.g., 0.20 = 20%)
MOUTH_OPEN_THRESH = 0.38    # mouth-aspect-ratio threshold for open/close
SEND_FPS = 30               # UDP send rate

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

def dist(a, b): 
    return float(np.linalg.norm(a - b))

def mouth_aspect_ratio(lm):
    L = lm[MOUTH_L]; R = lm[MOUTH_R]
    U = lm[MOUTH_UP]; D = lm[MOUTH_DN]
    horiz = dist(L, R) + 1e-6
    vert = dist(U, D)
    return vert / horiz

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

        if res.multi_face_landmarks:
            lm = np.array([[p.x * w, p.y * h] for p in res.multi_face_landmarks[0].landmark], dtype=np.float32)

            # ----- Mouth open/close (MAR) -----
            mar = mouth_aspect_ratio(lm)
            mouth_open = mar > MOUTH_OPEN_THRESH

            # ----- Eyebrow up/down (relative to baseline) -----
            # Normalize brow distance by inter-ocular width for scale invariance
            brow_dist = dist(lm[L_BROW], lm[L_EYE_TOP])
            inter_ocular = dist(lm[L_EYE_IN], lm[R_EYE_IN]) + 1e-6
            brow_norm = brow_dist / inter_ocular

            if brow_baseline is None:
                brow_samples.append(brow_norm)
                if len(brow_samples) == brow_samples.maxlen:
                    brow_baseline = float(np.median(brow_samples))
            else:
                # up if current distance is >= (1 + factor) * baseline
                brow_up = brow_norm >= (brow_baseline * (1.0 + BROW_UP_FACTOR))

            if args.show:
                cv2.putText(frame, f"MouthOpen:{mouth_open}  (MAR {mar:.2f})", (10, 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,200,255), 2)
                if brow_baseline is None:
                    cv2.putText(frame, "Brow baseline calibrating...", (10, 52),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50,200,50), 2)
                else:
                    cv2.putText(frame, f"BrowUp:{brow_up}  (norm {brow_norm:.2f} / base {brow_baseline:.2f})", (10, 52),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,200,255), 2)
        else:
            if args.show:
                cv2.putText(frame, "No face", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

        # ----- Send JSON at ~SEND_FPS -----
        now = time.time()
        if now - last_send >= 1.0 / SEND_FPS:
            payload = {"mouth_open": bool(mouth_open), "brow_up": bool(brow_up)}
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