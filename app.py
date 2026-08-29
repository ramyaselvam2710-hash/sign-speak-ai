import sqlite3
from datetime import datetime
from deep_translator import GoogleTranslator
import time
last_saved_letter = ""
last_detect_time = 0
from gtts import gTTS
import threading
import os
import csv

from flask import Flask, render_template, Response, jsonify, request, redirect, url_for,session
import cv2
import mediapipe as mp
import numpy as np
import math

from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

from flask import session

app.secret_key = "sign_speak_secret"

@app.route("/set_language/<lang>")
def set_language(lang):
    if lang in ["en", "ta"]:
        session["language"] = lang

    return redirect(request.referrer or url_for("dashboard"))

# --------------------------
# Global Variables
# --------------------------

last_saved_text = ""

last_spoken_gesture = ""
last_spoken_letter = ""

current_text = {
    "english": "NO HAND",
    "tamil": "கை இல்லை"
}

current_letter = ""
asl_letter = ""
last_asl_letter = ""
j_points = []
last_j_time = 0

current_word = ""
current_sentence = ""

words = [
    "HELLO",
    "HELP",
    "WATER",
    "FOOD",
    "YES",
    "NO",
    "PLEASE",
    "THANK YOU",
    "SORRY"
]
last_word_letter = ""
hold_letter = ""
hold_start_time = 0
last_added_letter = ""

normal_reply = ""
normal_reply_tamil = ""

# --------------------------
# Database
# --------------------------

def save_history(person, english, tamil):
    conn = sqlite3.connect("conversation.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO history (person, english, tamil, time) VALUES (?, ?, ?, ?)",
        (person, english, tamil, datetime.now())
    )

    conn.commit()
    conn.close()


# --------------------------
# Voice
# --------------------------

def speak(text, lang="en"):

    print("SPEAK FUNCTION CALLED:", text)

    try:

        filename = f"voice_{int(time.time()*1000)}.mp3"

        tts = gTTS(text=text, lang=lang)
        tts.save(filename)


    except Exception as e:

        print("Voice Error:", e)


# --------------------------
# MediaPipe
# --------------------------

import mediapipe as mp

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

camera = cv2.VideoCapture(0,cv2.CAP_MSMF)

dataset_file = "dataset.csv"                                                                                                                                                                                                                                                                                                                                                                                       
dataset_exists = os.path.isfile(dataset_file)
collect_letter = "A"

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_FPS, 30)
camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
#camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

if camera.isOpened():
    print("✅ Camera Opened Successfully")
else:
    print("❌ Camera Open Failed")


# --------------------------
# Draw English + Tamil
# --------------------------

def draw_text(frame, text_en, text_ta):

    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("C:/Windows/Fonts/Nirmala.ttf", 36)
    except:
        font = ImageFont.load_default()

    draw.text((20,20), text_en, fill=(0,255,0), font=font)
    draw.text((20,70), text_ta, fill=(255,0,0), font=font)

    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


# --------------------------
# Gesture Recognition
# --------------------------

def recognize_gesture(lm_list):

    thumb_tip = lm_list[4][1]
    thumb_ip = lm_list[3][1]

    index_tip = lm_list[8][2]
    index_pip = lm_list[6][2]

    middle_tip = lm_list[12][2]
    middle_pip = lm_list[10][2]

    ring_tip = lm_list[16][2]
    ring_pip = lm_list[14][2]

    pinky_tip = lm_list[20][2]
    pinky_pip = lm_list[18][2]

    thumb_open = thumb_tip > thumb_ip
    index_open = index_tip < index_pip
    middle_open = middle_tip < middle_pip
    ring_open = ring_tip < ring_pip
    pinky_open = pinky_tip < pinky_pip

    if thumb_open and index_open and middle_open and ring_open and pinky_open:
        return "HELLO", "வணக்கம்"

    elif (not thumb_open and
          not index_open and
          not middle_open and
          not ring_open and
          not pinky_open):
        return "STOP", "நிறுத்து"

    elif (thumb_open and
          not index_open and
          not middle_open and
          not ring_open and
          not pinky_open):
        return "LIKE", "நல்லது"

    elif (not thumb_open and
          index_open and
          middle_open and
          not ring_open and
          not pinky_open):
        return "NO", "இல்லை"

    elif (not thumb_open and
          index_open and
          not middle_open and
          not ring_open and
          pinky_open):
        return "THANK YOU", "நன்றி"

    elif (thumb_open and
          index_open and
          not middle_open and
          not ring_open and
          not pinky_open):
    
        return "PLEASE HELP ME", "தயவுசெய்து எனக்கு உதவுங்கள்"

    elif (not thumb_open and
          not index_open and
          middle_open and
          ring_open and
          pinky_open):
        return "SORRY", "மன்னிக்கவும்"


    elif index_open and not middle_open:
        return "YES / OK", "ஆம் / சரி"

    return "HAND DETECTED", "கை கண்டறியப்பட்டது"

def distance(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def detect_J(lm_list):


    global j_points

    pinky_tip = lm_list[20][2]
    pinky_pip = lm_list[18][2]

    if pinky_tip >= pinky_pip:
        j_points.clear()
        return ""

    # Pinky fingertip
    x = lm_list[20][1]
    y = lm_list[20][2]

    j_points.append((x, y))

    # Last 20 frames mattum keep pannum
    if len(j_points) > 20:
        j_points.pop(0)

    if len(j_points) == 20:

        start = j_points[0]
        end = j_points[-1]

        # movement irukka check
        move_x = abs(end[0] - start[0])
        move_y = abs(end[1] - start[1])

        if move_y > 40 and move_x > 20:
            j_points = []
            return "J"

    return ""        

def recognize_letter(lm_list):

    thumb_tip = lm_list[4][1]
    thumb_ip = lm_list[3][1]
    
    thumb_tip_x = lm_list[4][1]
    index_tip_x = lm_list[8][1]

    thumb = (lm_list[4][1], lm_list[4][2])
    index = (lm_list[8][1], lm_list[8][2])
    middle = (lm_list[12][1], lm_list[12][2])
    pinky = (lm_list[20][1], lm_list[20][2])

    thumb_index = distance(thumb, index)
    thumb_middle = distance(thumb, middle)
    thumb_pinky = distance(thumb, pinky)

    #print("Thumb-Index :", thumb_index)
    #print("Thumb-Middle:", thumb_middle)
    #print("Thumb-Pinky :", thumb_pinky)

    thumb_tip_y = lm_list[4][2]
    index_tip_y = lm_list[8][2]

    index_tip = lm_list[8][2]
    index_pip = lm_list[6][2]

    middle_tip = lm_list[12][2]
    middle_pip = lm_list[10][2]

    ring_tip = lm_list[16][2]
    ring_pip = lm_list[14][2]
    ring_tip_x = lm_list[16][1]

    pinky_tip = lm_list[20][2]
    pinky_pip = lm_list[18][2]

    thumb_open = thumb_tip > thumb_ip
    index_open = index_tip < index_pip
    middle_open = middle_tip < middle_pip
    ring_open = ring_tip < ring_pip
    pinky_open = pinky_tip < pinky_pip

    thumb_index_distance = abs(thumb_tip_x - index_tip_x)

    if (
       not index_open and
       not middle_open and
       not ring_open and
       not pinky_open and
       thumb_open and
       thumb_index > 90
    ):
       return "A"

    # B
    if (
       index_open and
       middle_open and
       ring_open and
       pinky_open and
       not thumb_open and
       thumb_index_distance < 40
    ):
       return "B"

    # C
    if (
       index_open and
       middle_open and
       ring_open and
       pinky_open and
       thumb_index_distance > 80
    ):
       return "C"
    print(
        "C CHECK",
        "Thumb-Index:", thumb_index_distance,
        "Thumb-Middle:", thumb_middle
    )

    # G (ASL)

    index_x = abs(lm_list[8][1] - lm_list[6][1])
    index_y = abs(lm_list[8][2] - lm_list[6][2])

    if (
       thumb_open and
       index_open and
       not middle_open and
       not ring_open and
       not pinky_open and
       index_x > index_y
    ):
       return "G"

    # H (ASL)

    index_x = abs(lm_list[8][1] - lm_list[6][1])
    index_y = abs(lm_list[8][2] - lm_list[6][2])

    middle_x = abs(lm_list[12][1] - lm_list[10][1])
    middle_y = abs(lm_list[12][2] - lm_list[10][2])

    if (
        thumb_open and
        index_open and
        middle_open and
        not ring_open and
        not pinky_open and
        index_x > index_y and
        middle_x > middle_y
    ):
        return "H"  

    # I (ASL)

    if (
        not thumb_open and
        not index_open and
        not middle_open and
        not ring_open and
        pinky_open
    ):
        return "I"    


    # K (ASL)

    thumb_middle = distance(
       (lm_list[4][1], lm_list[4][2]),
       (lm_list[12][1], lm_list[12][2])
    )

    if (
        thumb_open and
        index_open and
        middle_open and
        not ring_open and
        not pinky_open and
        thumb_middle < 40
    ):
       return "K"  

    # L (ASL)

    index_x = abs(lm_list[8][1] - lm_list[6][1])
    index_y = abs(lm_list[8][2] - lm_list[6][2])

    thumb_y = abs(lm_list[4][2] - lm_list[3][2])

    if (
       thumb_open and
       index_open and
       not middle_open and
       not ring_open and
       not pinky_open and
       index_y > index_x and
       thumb_y < 20
   ):
      return "L"  

    # M (ASL)

    if (
       not thumb_open and
       not index_open and
       not middle_open and
       not ring_open and
       not pinky_open and
       thumb_index > 40 and
       thumb_middle < 60
    ):
       return "M"    

    if (
       not index_open and
       not middle_open and
       not ring_open and
       not pinky_open and
       thumb_tip_x > index_tip_x and
       thumb_tip_x < ring_tip_x
    ):
       return "N"

    # O (ASL)

    thumb_index = distance(
        (lm_list[4][1], lm_list[4][2]),
        (lm_list[8][1], lm_list[8][2])
    )

    if (
       not middle_open and
       not ring_open and
       not pinky_open and
       thumb_index < 35
    ):
      return "O"   


    # P (ASL)

    index_x = abs(lm_list[8][1] - lm_list[6][1])
    index_y = abs(lm_list[8][2] - lm_list[6][2])

    middle_x = abs(lm_list[12][1] - lm_list[10][1])
    middle_y = abs(lm_list[12][2] - lm_list[10][2])

    if (
        thumb_open and
        index_open and
        middle_open and
        not ring_open and
        not pinky_open and
        index_y > index_x and
        middle_y > middle_x
    ):
        return "P" 
    # Q (ASL)

    index_x = abs(lm_list[8][1] - lm_list[6][1])
    index_y = abs(lm_list[8][2] - lm_list[6][2])

    if (
        thumb_open and
        index_open and
        not middle_open and
        not ring_open and
        not pinky_open and
        index_y > index_x
    ):
        return "Q"

    # U (ASL)

    index_middle_distance = distance(
       (lm_list[8][1], lm_list[8][2]),
       (lm_list[12][1], lm_list[12][2])
    )

    if (
       index_open and
       middle_open and
       not ring_open and
       not pinky_open and
       index_middle_distance < 25
    ):
       return "U"

    print(
       "R CHECK",
       "Thumb:", thumb_open,
       "Index:", index_open,
       "Middle:", middle_open,
       "Ring:", ring_open,
       "Pinky:", pinky_open
    )    


    # R (ASL)

    index_middle_distance = distance(
       (lm_list[8][1], lm_list[8][2]),
       (lm_list[12][1], lm_list[12][2])
    )

    if (
       index_open and
       middle_open and
       not ring_open and
       not pinky_open and
       index_middle_distance >= 25 and
       index_middle_distance <= 40
    ):
       return "R"

    # V (ASL)

    index_middle_distance = distance(
       (lm_list[8][1], lm_list[8][2]),
       (lm_list[12][1], lm_list[12][2])
    )

    if (
        index_open and
        middle_open and
        not ring_open and
        not pinky_open and
        index_middle_distance > 35
    ):
        return "V" 

    # W (ASL)

    if (
        index_open and
        middle_open and
        ring_open and
        not pinky_open and
        not thumb_open
    ):
        return "W"  

    # X (ASL)

    if (
        not thumb_open and
        not middle_open and
        not ring_open and
        not pinky_open and
        index_open
    ):
        return "X"  

    # Y (ASL)

    if (
        thumb_open and
        not index_open and
        not middle_open and
        not ring_open and
        pinky_open
    ):
        return "Y"

     # Z (ASL)

    if (
        index_open and
        not middle_open and
        not ring_open and
        not pinky_open and
        not thumb_open
    ):
        return "Z"                

    # S (ASL)

    if (
       not index_open and
       not middle_open and
       not ring_open and
       not pinky_open and
       thumb_open
    ):
       return "S"  

    # T (ASL)

    if (
       not index_open and
       not middle_open and
       not ring_open and
       not pinky_open and
       not thumb_open and
       thumb_index < 50
    ):
       return "T"   

                  

    # D (ASL)

    if (
       thumb_open and
       index_open and
       not middle_open and
       not ring_open and
       not pinky_open and
       index_y > index_x
    ):
       return "D"     
   


    # F (ASL)

    if (
        index_open and
        middle_open and
        ring_open and
        pinky_open and
        thumb_index < 80
    ):
       print("F CONDITION MATCH")
       return "F"


    # E (ASL)

    if (
        not thumb_open and
        not index_open and
        not middle_open and
        not ring_open and
        not pinky_open
    ):
        return "E"          

    return ""
    # --------------------------
# Video Function
# --------------------------
def camera_test():
    while True:
        success, frame = camera.read()

        if not success:
            print("CAMERA READ FAILED")
            continue

        frame = cv2.flip(frame, 1)

        ret, buffer = cv2.imencode(".jpg", frame)

        if not ret:
            print("JPEG ENCODE FAILED")
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )


def video():

    global current_text
    global last_saved_text
    global current_letter
    global asl_letter
    global last_asl_letter
    global last_spoken_gesture

    while True:

        asl_letter = ""

        success, frame = camera.read()

        if not success:
            print("❌ CAMERA FRAME READ FAILED")
            time.sleep(0.1)
            continue

        print("✅ CAMERA FRAME READ SUCCESS")

        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (640, 480))

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

                lm_list = []

                h, w, c = frame.shape

                for idx, lm in enumerate(hand.landmark):
                    x = int(lm.x * w)
                    y = int(lm.y * h)
                    lm_list.append((idx, x, y))

                text_en, text_ta = recognize_gesture(lm_list)
                letter = recognize_letter(lm_list)


                #if letter :
                #    current_letter = letter
                #    asl_letter = letter
                #   if asl_letter != last_asl_letter:
                #      last_asl_letter = asl_letter
                #      print("ASL LETTER:", asl_letter)
                #       threading.Thread(
                #          target=speak,
                #          args=("Letter " + asl_letter, "en"),
                #           daemon=True
                #        ).start()
                print("Detected Text:", text_en)

                if text_en not in ["NO HAND", "HAND DETECTED"]:

                    if text_en != last_saved_text:

                        save_history("Deaf & Mute", text_en, text_ta)
                        last_saved_text = text_en
                    if asl_letter == "" and text_en != last_spoken_gesture:

                        last_spoken_gesture = text_en

                

                current_text["english"] = text_en
                current_text["tamil"] = text_ta

       # frame = draw_text(frame, text_en, text_ta)

        ret, buffer = cv2.imencode(".jpg", frame)

        if not ret:
            continue

        frame = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            frame +
            b'\r\n'
        )

def video_alphabet():

    global current_letter
    global asl_letter
    global last_asl_letter
    global last_spoken_letter
    global current_word
    global last_word_letter
    global hold_letter
    global hold_start_time
    global last_added_letter
    global current_sentence

    while True:

        success, frame = camera.read()

        if not success:
           print("❌ Camera frame not available")
           time.sleep(0.1)
           continue

        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)
        if result.multi_hand_landmarks:
           print("✅ HAND DETECTED")
        else:
            print("❌ NO HAND")

        detected_letter = ""

        if result.multi_hand_landmarks:

            for hand in result.multi_hand_landmarks:

                mp_draw.draw_landmarks(
                    frame,
                    hand,
                    mp_hands.HAND_CONNECTIONS
                )

                lm_list = []

                h, w, c = frame.shape

                for idx, lm in enumerate(hand.landmark):

                    x = int(lm.x * w)
                    y = int(lm.y * h)

                    lm_list.append((idx, x, y))


                # ==========================
                # DETECT LETTER
                # ==========================

                letter = recognize_letter(lm_list)

                j_letter = detect_J(lm_list)

                if j_letter:
                    letter = j_letter

                detected_letter = letter

                print("Detected Letter =", letter)

                break


        # ==================================
        # LETTER STABILIZATION
        # ==================================

        if detected_letter:

            # New letter detected
            if detected_letter != hold_letter:

                hold_letter = detected_letter
                hold_start_time = time.time()

                current_letter = detected_letter

                print("HOLD START:", hold_letter)


            # Same letter detected continuously
            else:

                current_letter = detected_letter

                elapsed_time = time.time() - hold_start_time


                # ==================================
                # ACCEPT LETTER AFTER 1.5 SECONDS
                # ==================================

                if elapsed_time >= 1.5:

                    asl_letter = detected_letter


                    # Add only once
                    if asl_letter != last_added_letter:

                        current_word += asl_letter

                        last_added_letter = asl_letter
                        last_word_letter = asl_letter

                        print("STABLE LETTER:", asl_letter)
                        print("CURRENT WORD:", current_word)


                        # ==========================
                        # SPEAK LETTER
                        # ==========================

                        if asl_letter != last_spoken_letter:

                            last_spoken_letter = asl_letter

                            threading.Thread(
                                target=speak,
                                args=(asl_letter, "en"),
                                daemon=True
                            ).start()


        else:

            # ==================================
            # HAND REMOVED = WORD COMPLETE
            # ==================================
            if current_word != "":

                completed_word = current_word

                current_sentence += completed_word + " "

                print("CURRENT SENTENCE:", current_sentence)


                current_word = ""

                last_added_letter = ""
                last_word_letter = ""

            current_letter = ""
            asl_letter = ""

            hold_letter = ""
            hold_start_time = 0


        # ==================================
        # DISPLAY LETTER
        # ==================================

        cv2.putText(
            frame,
            "ASL LETTER : " + current_letter,
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )


        # ==================================
        # DISPLAY CURRENT WORD
        # ==================================

        cv2.putText(
            frame,
            "WORD : " + current_word,
            (20, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 0),
            2
        )


        # ==================================
        # DISPLAY SENTENCE
        # ==================================

        cv2.putText(
            frame,
            "SENTENCE : " + current_sentence,
            (20, 150),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        # ==================================
        # CAMERA FRAME
        # ==================================

        ret, buffer = cv2.imencode(".jpg", frame)

        if not ret:
            continue

        frame = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            frame +
            b'\r\n'
        )
      
# --------------------------
# Flask Routes
# --------------------------

@app.route("/")
def splash():
    return render_template("splash.html")    

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        language = request.form.get("language", "en")
        print("SELECTED LANGUAGE:",language)

        if username == "admin" and password == "1234":

            # Selected language save
            session["language"] = language

            return redirect(url_for("instructions"))

        else:
            return render_template(
                "login.html",
                error="Invalid Username or Password"
            )

    return render_template("login.html")



@app.route("/instructions")
def instructions():

    language = session.get("language", "en")

    return render_template(
        "instructions.html",
        language=language
    )   


@app.route("/dashboard")
def dashboard():

    language = session.get("language", "en")

    return render_template(
        "dashboard.html",
        language=language
    )

@app.route("/about")
def about():

    language = session.get("language", "en")

    return render_template(
        "about.html",
        language=language
    )   


@app.route("/home")
def home():
    return render_template("index.html")

@app.route("/alphabet")
def alphabet():
    language = session.get("language", "en")
    return render_template("alphabet.html", language=language)    


@app.route("/video")
def video_feed():

    return Response(
        video(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/video_test")
def video_test():
    return Response(
        camera_test(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )    

@app.route("/video_alphabet")
def video_alphabet_feed():

    return Response(
        video_alphabet(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )   

@app.route("/alphabet_text")
def alphabet_text():
    return jsonify({
        "letter": current_letter,
        "word": current_word,
        "sentence": current_sentence
    }) 

@app.route("/save_alphabet_history", methods=["POST"])
def save_alphabet_history():

    global current_word
    global current_sentence

    # தற்போதைய word அல்லது completed sentence எடு
    if current_word.strip():
        text_to_save = current_word.strip()

    elif current_sentence.strip():
        text_to_save = current_sentence.strip()

    else:
        return jsonify({
            "success": False,
            "message": "No word to save!"
        })

    # Database save
    save_history(
        "Alphabet Mode",
        text_to_save,
        text_to_save
    )

    print("ALPHABET HISTORY SAVED:", text_to_save)

    # Save பிறகு clear
    current_word = ""
    current_sentence = ""

    return jsonify({
        "success": True,
        "message": "Saved successfully!"
    })      


@app.route("/text")
def text():

    return jsonify({
        "english": current_text["english"],
        "tamil": current_text["tamil"],
        "letter": current_letter
    })

@app.route("/asl_text")
def asl_text():

    return jsonify({
        "letter": asl_letter,
        "word": current_word
    })    


@app.route("/history")
def history():

    conn = sqlite3.connect("conversation.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM history ORDER BY id DESC")
    data = cursor.fetchall()

    conn.close()

    return render_template("history.html", data=data)

@app.route("/clear_history")
def clear_history():

    conn = sqlite3.connect("conversation.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM history")

    conn.commit()
    conn.close()

    return redirect(url_for("history"))

@app.route("/delete/<int:id>")
def delete(id):

    conn = sqlite3.connect("conversation.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM history WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("history"))        


@app.route("/reply", methods=["POST"])
def reply():

    global normal_reply, normal_reply_tamil

    data = request.get_json()

    normal_reply = data["reply"]

    print("Normal Person Reply:", normal_reply)

    try:
        tamil_reply = GoogleTranslator(
            source="en",
            target="ta"
        ).translate(normal_reply)

        print("Tamil Translation:", tamil_reply)

    except Exception as e:

        print("Tamil Translation Error:", e)

        tamil_reply = normal_reply

    normal_reply_tamil = tamil_reply

    save_history("Normal", normal_reply, tamil_reply)

    speak(normal_reply)

    return jsonify({"status": "success"})


@app.route("/reply_text")
def reply_text():

    return jsonify({
        "reply": normal_reply,
        "reply_tamil": normal_reply_tamil
    })

@app.route("/delete_last",
methods=["POSST"])
def delete_last():

    global current_text

    current_text["english"] = current_text["english"][:-1]
    current_text["tamil"] =  current_text["tamil"][:-1]

    return "ok"

@app.route("/clear", methods=["POST"])
def clear():

    global current_text

    current_text["english"] = ""
    current_text["tamil"] = ""

    return "ok"  


@app.route("/speak")
def speak_route():

    text = current_text["english"]

    if text not in ["NO HAND", "HAND DETECTED"]:
        speak(text)

    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
