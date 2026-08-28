from gtts import gTTS
import os

text = "Hello, Sign Speak AI is working"

tts = gTTS(text=text, lang="en")
tts.save("test.mp3")

os.system("test.mp3")