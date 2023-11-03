# %%
"""Import and Functions"""
import speech_recognition as sr
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import threading
from pydub import AudioSegment
import os
from pydub.silence import split_on_silence
from tkinter.ttk import Progressbar


speech_engine = sr.Recognizer()
# Globale Variablen für die Länge der Audiodaten
recording = False
audio_data = []

total_length_of_audio = 0
processed_length = 0

DEFAULT_PATH_TXT = r"C:\Users\twenn\Documents\GitHub\wav_to_text\text_data"
DEFAULT_PATH_WAV = r"C:\Users\twenn\Documents\GitHub\wav_to_text\wav_examples"

def return_to_default(label_text=False,
                      recording_button=False,
                      progress_bar=False):
    if label_text:
        window.label.config(text="Press the button to start recording \n"
                            "or load an Audio File.")
    if recording_button:
        window.record_button.config(bg="gray")
    if progress_bar:
        #window.progress['value'] = 0
        #window.update_idletasks()
        window.progress_bar_frame.pack_forget()  # Verstecke die Progressbar beim Zurücksetzen


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
    # audio.export("temp_audio.wav", format="wav")
    #window.label.config(text="Recognition...")
    
    
    # Ersetzen Sie den Aufruf von recognize_from_file durch die folgende Logik:
    audio_data = sr.AudioData(audio.raw_data, audio.frame_rate, audio.sample_width)
    threading.Thread(target=recognize_from_audio_data, args=(audio_data,)).start()
    window.label.config(text="Recognition...")
    window.progress_bar_frame.pack(pady=20)

def split_audio_into_segments(audio, min_segment_length=52000, max_segment_length=55000):
    global total_length_of_audio
    set_total_length(len(audio))
    # Zuerst auf Stille basierende Segmente erstellen
    segments = split_on_silence(audio, min_silence_len=500,
                                silence_thresh=-40,
                                keep_silence=500,
                                seek_step=1)
    
    final_segments = []
    current_segment = AudioSegment.empty()
    
    for segment in segments:
        if len(current_segment) + len(segment) <= max_segment_length:
            current_segment += segment
        else:
            if len(current_segment) >= min_segment_length:
                final_segments.append(current_segment)
                current_segment = segment
            else:
                current_segment += segment

    if len(current_segment) > 0:
        final_segments.append(current_segment)
    
    return final_segments


def recognize_from_audio_data(audio_data):
     # Konvertieren Sie AudioData zurück in ein AudioSegment-Objekt
    audio_segment = AudioSegment(
        audio_data.get_wav_data(),
        frame_rate=audio_data.sample_rate,
        sample_width=audio_data.sample_width,
        channels=1
    )
    
    # Verwenden Sie das AudioSegment-Objekt, um es in Segmente zu unterteilen
    segments = split_audio_into_segments(audio_segment)
    texts = []
    for segment in segments:
        segment_data = sr.AudioData(segment.raw_data, segment.frame_rate, segment.sample_width)

        text = speech_engine.recognize_google(segment_data, language="de-DE")
        texts.append(text)
        # Aktualisieren Sie den Fortschrittsbalken mit der Länge des verarbeiteten Segments
        update_progress(len(segment))

    full_text = ' '.join(texts)
    window.label.config(text="Recognition complete!")
    save_to_file(full_text)

def from_microphone():
    global recording, audio_data
    with sr.Microphone() as source:
        window.label.config(text="Recording...")
        while recording:
            audio_chunk = speech_engine.listen(source, timeout=1, phrase_time_limit=5)
            audio_data.append(audio_chunk)
        window.label.config(text="Recognition...")
        window.progress_bar_frame.pack(pady=20)

        # Kombinieren Sie alle Audio-Chunks zu einem einzigen AudioSegment
        audio_combined = sr.AudioData(b''.join([a.get_wav_data() for a in audio_data]),
                                      source.SAMPLE_RATE, source.SAMPLE_WIDTH)
        
        # Konvertieren Sie AudioData zurück in ein AudioSegment-Objekt
        audio_segment = AudioSegment(
            audio_combined.get_wav_data(),
            frame_rate=audio_combined.sample_rate,
            sample_width=audio_combined.sample_width,
            channels=1
        )
        
        # Verwenden Sie das AudioSegment-Objekt, um es in Segmente zu unterteilen
        segments = split_audio_into_segments(audio_segment)
        texts = []
        for segment in segments:
            segment_data = sr.AudioData(segment.raw_data, segment.frame_rate, segment.sample_width)
            text = speech_engine.recognize_google(segment_data, language="de-DE")
            texts.append(text)
        full_text = ' '.join(texts)
        save_to_file(full_text)


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
        window.progress['value'] = 0  # Fortschrittsbalken zurücksetzen
        window.update_idletasks()

def save_to_file(text):
    update_progress(total_length_of_audio - processed_length)  # Sollte den Balken auf 100% setzen
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
                      recording_button=True,
                      progress_bar=True)

# Funktion zum Setzen der Gesamtlänge und zum Starten des Ladebalkens
def set_total_length(length):
    global total_length_of_audio
    total_length_of_audio = length
    window.progress['maximum'] = total_length_of_audio

# Funktion zum Aktualisieren des Fortschrittsbalkens
def update_progress(length):
    global processed_length
    processed_length += length
    window.progress['value'] = processed_length
    percentage = 100 * (processed_length / total_length_of_audio)
    #window.progress_label.config(text="{:d}%".format(round(percentage)))
    #window.update_idletasks()
    # Planen Sie die GUI-Aktualisierung im Hauptthread
    window.after(0, lambda: window.progress['value'] == processed_length)
    window.after(0, lambda: window.progress_label.config(text="{:d}%".format(round(percentage))))
    

# %%
"""Gui"""
window = tk.Tk()
window.title("Speech Recognition")

window.label = tk.Label(window, text="Press the button to start recording \n"
                                     "or load an Audio File.")
window.label.pack(pady=20)

# Progressbar
#window.progress = Progressbar(window, orient=tk.HORIZONTAL, length=100, mode='determinate')
#window.progress.pack(pady=20)

# Innerhalb deiner GUI-Initialisierung
window.progress_bar_frame = tk.Frame(window)
window.progress = Progressbar(window.progress_bar_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
window.progress.pack(side=tk.LEFT)

window.progress_label = tk.Label(window.progress_bar_frame, text="0%")
window.progress_label.pack(side=tk.LEFT)

window.record_button = tk.Button(window, text="⬤", 
                                 command=start_stop_recording,
                                 bg="gray", font=("Arial", 20))
window.record_button.pack(pady=20)

load_button = tk.Button(window, text="Load Audiofile", command=load_audio_file, font=("Arial", 12))
load_button.pack(pady=20)



window.mainloop()

# %%
