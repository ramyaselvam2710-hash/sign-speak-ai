def recognize_gesture(lm_list):

    # No hand detected
    if len(lm_list) != 21:
        return "NO HAND", "கை இல்லை"

    # Thumb
    thumb_tip = lm_list[4][1]
    thumb_ip = lm_list[3][1]

    # Index
    index_tip = lm_list[8][2]
    index_pip = lm_list[6][2]

    # Middle
    middle_tip = lm_list[12][2]
    middle_pip = lm_list[10][2]

    # Ring
    ring_tip = lm_list[16][2]
    ring_pip = lm_list[14][2]

    # Pinky
    pinky_tip = lm_list[20][2]
    pinky_pip = lm_list[18][2]

    # Finger states
    thumb_open = thumb_tip > thumb_ip
    index_open = index_tip < index_pip
    middle_open = middle_tip < middle_pip
    ring_open = ring_tip < ring_pip
    pinky_open = pinky_tip < pinky_pip

    # OPEN HAND
    if index_open and middle_open and ring_open and pinky_open:
        return "HELLO", "வணக்கம்"

    # CLOSED FIST
    elif (not index_open and
          not middle_open and
          not ring_open and
          not pinky_open):
        return "STOP", "நிறுத்து"

    # ONLY INDEX FINGER
    elif (index_open and
          not middle_open and
          not ring_open and
          not pinky_open):
        return "YES / OK", "ஆம் / சரி"

    # THUMBS UP
    elif (thumb_open and
          not index_open and
          not middle_open and
          not ring_open and
          not pinky_open):
        return "GOOD", "நல்லது"

    # DEFAULT
    return "HAND DETECTED", "கை கண்டறியப்பட்டது"