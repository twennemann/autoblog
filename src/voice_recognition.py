# %%
"""Import and Functions"""
import speech_recognition as sr
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import threading
from pydub import AudioSegment
import os

speech_engine = sr.Recognizer()

recording = False
audio_data = []

DEFAULT_PATH_TXT = r"C:\Users\twenn\Documents\GitHub\wav_to_text\text_data"
DEFAULT_PATH_WAV = r"C:\Users\twenn\Documents\GitHub\wav_to_text\wav_examples"

def return_to_default(label_text=False, recording_button=False):
    if label_text:
        window.label.config(text="Press the button to start recording")
    if recording_button:
        window.record_button.config(bg="gray")

def load_audio_file():
    if os.path.exists(DEFAULT_PATH_WAV):
        initial_dir = DEFAULT_PATH_WAV
    else:
        initial_dir = None
    file_path = filedialog.askopenfilename(initialdir=initial_dir,
                                           filetypes=[("Audio files", "*.wav;*.mp3;*.ogg"),
                                                      ("All files", "*.*")])
    if not file_path:
        return

    if file_path.endswith(".ogg"):
        audio = AudioSegment.from_ogg(file_path)
    else:
        audio = AudioSegment.from_wav(file_path) if file_path.endswith(".wav") else AudioSegment.from_mp3(file_path)
    audio.export("temp_audio.wav", format="wav")
    window.label.config(text="Recognition...")
    # audio_data = sr.AudioData(audio.raw_data, audio.frame_rate, audio.sample_width)
    # threading.Thread(target=recognize_from_audio_data, args=(audio_data,)).start()
    threading.Thread(target=recognize_from_file, args=("temp_audio.wav",)).start()
    #recognize_from_audio_data(audio_data)

def recognize_from_audio_data(audio_data):
    text = speech_engine.recognize_google(audio_data, language="de-DE")
    window.label.config(text="Recognition complete!")
    save_to_file(text)

def recognize_from_file(file_name):
    with sr.AudioFile(file_name) as f:
        data = speech_engine.record(f)
        text = speech_engine.recognize_google(data, language="de-DE")
        save_to_file(text)
    if file_name == "temp_audio.wav":
        os.remove("temp_audio.wav")
    
def from_microphone():
    global recording, audio_data
    with sr.Microphone() as source:
        window.label.config(text="Recording...")
        while recording:
            audio_chunk = speech_engine.listen(source, timeout=1, phrase_time_limit=5)
            audio_data.append(audio_chunk)
        window.label.config(text="Recognition...")
        audio_combined = sr.AudioData(b''.join([a.get_wav_data() for a in audio_data]),
                                      source.SAMPLE_RATE, source.SAMPLE_WIDTH)
        text = speech_engine.recognize_google(audio_combined, language="de-DE")
        save_to_file(text)


def start_stop_recording():
    global recording, audio_data
    if not recording:
        audio_data = []
        recording = True
        window.record_button.config(bg="red")
        threading.Thread(target=from_microphone).start()
    else:
        recording = False
        window.record_button.config(bg="gray")

def save_to_file(text):
    if os.path.exists(DEFAULT_PATH_TXT):
        initial_dir = DEFAULT_PATH_TXT
    else:
        initial_dir = None
    file_name = filedialog.asksaveasfilename(defaultextension=".txt",
                                             initialdir=initial_dir,
                                             filetypes=[("Text files", "*.txt"),
                                                        ("All files", "*.*")])
    if file_name:
        with open(file_name, 'w') as f:
            f.write(text)
        messagebox.showinfo("Info", "Text saved successfully!")
    return_to_default(label_text=True,
                      recording_button=True)

# %%
"""Gui"""
window = tk.Tk()
window.title("Speech Recognition")

window.label = tk.Label(window, text="Press the button to start recording")
window.label.pack(pady=20)

window.record_button = tk.Button(window, text="⬤", 
                                 command=start_stop_recording,
                                 bg="gray", font=("Arial", 20))
window.record_button.pack(pady=20)

load_button = tk.Button(window, text="Load Audiofile", command=load_audio_file, font=("Arial", 12))
load_button.pack(pady=20)

window.mainloop()

# %%
