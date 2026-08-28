from flask import Flask, render_template, Response, jsonify
import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

app = Flask(__name__)

# -------------------------------
# MediaPipe Hands
# -------------------------------
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# -------------------------------
# Camera
# -------------------------------
camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if camera.isOpened():
    print("✅ Camera Opened Successfully")
else:
    print("❌ Camera Open Failed")

# -------------------------------
# Tamil Font
# -------------------------------
font_path = "C:/Windows/Fonts/Nirmala.ttf"

if os.path.exists(font_path):
    font = ImageFont.truetype(font_path, 30)
else:
    font = ImageFont.load_default()

# -------------------------------
# Draw English & Tamil Text
# -------------------------------
def draw_text(frame, english, tamil):

    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)

    draw.text((20, 20), english, font=font, fill=(0, 255, 0))
    draw.text((20, 60), tamil, font=font, fill=(255, 0, 0))

    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    # -----------------------------------
# Gesture Recognition
# -----------------------------------
def recognize_gesture(lm_list):

    if len(lm_list) != 21:
        return "NO HAND", "கை இல்லை"

    index_tip = lm_list[8][2]
    index_pip = lm_list[6][2]

    middle_tip = lm_list[12][2]
    middle_pip = lm_list[10][2]

    ring_tip = lm_list[16][2]
    ring_pip = lm_list[14][2]

    pinky_tip = lm_list[20][2]
    pinky_pip = lm_list[18][2]

    # Open Palm
    if (index_tip < index_pip and
        middle_tip < middle_pip and
        ring_tip < ring_pip and
        pinky_tip < pinky_pip):

        return "HELLO", "வணக்கம்"

    # Closed Hand
    elif (index_tip > index_pip and
          middle_tip > middle_pip and
          ring_tip > ring_pip and
          pinky_tip > pinky_pip):

        return "STOP", "நிறுத்து"

    elif (index_tip < index_pip and
          middle_tip > middle_pip and
          ring_tip > ring_pip and
          pinky_tip > pinky_pip):

        return "YES", "ஆம்"

    else:
        return "HAND DETECTED", "கை கண்டறியப்பட்டது"


# -----------------------------------
# Video Generator
# -----------------------------------

def video():

    global current_text

    while True:
        success, frame = camera.read()

        if not success:
            continue

        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        result = hands.process(rgb)

        text_en = "NO HAND"
        text_ta = "கை இல்லை"

        if result.multi_hand_landmarks:

            for hand in result.multi_hand_landmarks:

                mp_draw.draw_landmarks(
                    frame,
                    hand,
                    mp_hands.HAND_CONNECTIONS
                )

        ret, buffer = cv2.imencode(".jpg", frame)

        if not ret:
            continue

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            buffer.tobytes() +
            b'\r\n'
        )


# -------------------------------
# Flask Routes
# -------------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/video")
def video_feed():
    return Response(
        video(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/text")
def text():
    return jsonify(current_text)


# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)