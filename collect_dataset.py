import cv2
import mediapipe as mp
import csv
import os

# ----------------------------
# MediaPipe Setup
# ----------------------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

mp_draw = mp.solutions.drawing_utils

# ----------------------------
# Camera
# ----------------------------
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Camera Open Failed")
    exit()

print("Camera Opened Successfully")

# ----------------------------
# Dataset
# ----------------------------
label = input("Enter Letter (A-Z): ").upper()

filename = "dataset.csv"
file_exists = os.path.isfile(filename)

# ----------------------------
# Main Loop
# ----------------------------
while True:

    success, frame = camera.read()

    if not success:
        continue

    frame = cv2.flip(frame, 1)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    result = hands.process(rgb)

    landmarks = []

    if result.multi_hand_landmarks:

        for hand in result.multi_hand_landmarks:

            mp_draw.draw_landmarks(
                frame,
                hand,
                mp_hands.HAND_CONNECTIONS
            )

            landmarks = []

            for lm in hand.landmark:
                landmarks.append(lm.x)
                landmarks.append(lm.y)
                landmarks.append(lm.z)

    cv2.putText(
        frame,
        f"Letter : {label}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.putText(
        frame,
        "S = Save   Q = Quit",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 0),
        2
    )

    cv2.imshow("Dataset Collection", frame)
    cv2.namedWindow("Dataset Collection")
    cv2.setWindowProperty(
    "Dataset Collection",
    cv2.WND_PROP_TOPMOST,
    1
)

    key = cv2.waitKey(1) & 0xFF
    print(key)

    # Save
    if key == ord("s") and len(landmarks) == 63:

        with open(filename, "a", newline="") as f:

            writer = csv.writer(f)

            if not file_exists:

                header = ["label"]

                for i in range(21):
                    header.extend([f"x{i}", f"y{i}", f"z{i}"])

                writer.writerow(header)
                file_exists = True

            writer.writerow([label] + landmarks)

        print(f"{label} Saved")

    # Quit
    if key == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()