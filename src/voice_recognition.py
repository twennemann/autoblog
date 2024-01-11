# %%
"""Import"""
import speech_recognition as sr
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import threading
from pydub import AudioSegment
import os
from pydub.silence import split_on_silence
import openai
import requests
import shutil

# %%
"""Globale Variablen und Default Pfade"""
full_text = ""
recording = False
audio_data = []
total_length_of_audio = 0
processed_length = 0
speech_engine = sr.Recognizer()

def get_base_path():
    # Ermitteln des aktuellen Skriptpfads
    current_script_path = os.path.abspath(__file__)

    # Ermitteln des übergeordneten Verzeichnisses des aktuellen Skripts (zwei Ebenen nach oben)
    base_directory = os.path.dirname(os.path.dirname(current_script_path))

    return base_directory

# Basispfad ermitteln
base_path = get_base_path()

# Pfade zu den Verzeichnissen und Textdateien festlegen
DEFAULT_PATH_TXT = os.path.join(base_path, 'output')
DEFAULT_PATH_WAV = os.path.join(base_path, 'audio_data')

blog_instructions_path = os.path.join(base_path, 'gpt_instructions', 'text_to_blog.txt')
picture_instructions_path = os.path.join(base_path, 'gpt_instructions', 'text_to_dalle.txt')
safety_guide_path = os.path.join(base_path, 'gpt_instructions', 'follow_safety_guide.txt')


# %%
"""Spracherkennung"""
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
    
    # Ersetzen Sie den Aufruf von recognize_from_file durch die folgende Logik:
    audio_data = sr.AudioData(audio.raw_data, audio.frame_rate, audio.sample_width)
    threading.Thread(target=recognize_from_audio_data, args=(audio_data,)).start()
    recordning_label.config(text="Recognition: 0%")

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
    global full_text
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
    recordning_label.config(text="Recognition complete!")
    # save_to_file(full_text)

def from_microphone():
    global recording, audio_data, full_text
    with sr.Microphone() as source:
        recordning_label.config(text="Recording...")
        while recording:
            audio_chunk = speech_engine.listen(source, timeout=1, phrase_time_limit=5)
            audio_data.append(audio_chunk)
        recordning_label.config(text="Recognition: 0%")
        #progress_bar_frame.pack(pady=20)

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
            update_progress(len(segment))
        full_text = ' '.join(texts)
        recordning_label.config(text="Recognition complete!")
        # save_to_file(full_text)


def start_stop_recording():
    global recording, audio_data
    if not recording:
        audio_data = []
        recording = True
        record_button.config(bg="red")
        threading.Thread(target=from_microphone).start()
    else:
        recording = False
        record_button.config(bg="gray")
        window.update_idletasks()

def save_to_file():
    global full_text
    if full_text == "":
        tk.messagebox.showerror("Fehler", "Es wurde noch keine Spracherkennung durchgeführt!")
        return
    elif recordning_label["text"] != "Recognition complete!":
        tk.messagebox.showerror("Fehler", "Die Texterkennung ist noch nicht fertig.")
        return
    # update_progress(total_length_of_audio - processed_length)  # Sollte den Balken auf 100% setzen
    if os.path.exists(DEFAULT_PATH_TXT):
        initial_dir = DEFAULT_PATH_TXT
    else:
        initial_dir = None

    folder_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                             initialdir=initial_dir,
                                             filetypes=[("Text files", "*.txt"),
                                                        ("All files", "*.*")])
    folder_path = folder_path.replace(".txt", "")

    if not folder_path:
        # Benutzer hat die Auswahl abgebrochen
        return

    # Stellt sicher, dass der Ordner existiert
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    else:
        # Zählt hoch, bis ein nicht existierender Pfad gefunden wird
        counter = 2
        new_folder_path = f"{folder_path}_{counter}"
        while os.path.exists(new_folder_path):
            counter += 1
            new_folder_path = f"{folder_path}_{counter}"

        # Erstellt den neuen Ordner
        os.makedirs(new_folder_path)
        folder_path = new_folder_path
        #tk.messagebox.showerror("Fehler", "Der Ordner existiert bereits.")
    
    # Erstelle Cache Ordner in folder_path
    cache_path = os.path.join(folder_path, 'cache')
    os.makedirs(cache_path)

    # Speicher der Spracherkennung
    recogniced_text_path = os.path.join(cache_path, 'recogniced_text.txt')
    with open(recogniced_text_path, 'w', encoding='utf-8') as file:
        file.write(full_text)
    # Extrahiert den Namen des Ordners aus dem Pfad
    folder_name = os.path.basename(folder_path)

    # Definiert den Pfad für die Textdatei basierend auf dem Ordnernamen
    file_path_txt = os.path.join(folder_path, f'{folder_name}.txt')
    
    style = style_entry.get()
    if style == "":
        style = None
    extra_instruction = extra_instruction_entry.get()
    if extra_instruction != "":
        extra_instruction = "\n\n Befolge Außerdem folgende Extraanweisungen:\n" + extra_instruction + "\n\n"

    blog_text = text_to_blog(full_text, file_path_txt, style, extra_instruction)

    if generate_pictures_var.get():
        pic_amount = 1
        # Ruft die Funktion auf, um Bilder zu generieren und zu speichern
        blog_to_picture(blog_text, style, file_path_txt, pic_amount, cache_path)
    else:
        # Der Haken ist nicht gesetzt, überspringe text_to_picture
        pass  # oder weiterer Code, der ausgeführt werden soll, wenn der Haken nicht gesetzt ist
    messagebox.showinfo("Info", "Saving complete!")
    return_to_default(label_text=True,
                      recording_button=True,
                      return_full_text=True)

# Funktion zum Setzen der Gesamtlänge und zum Starten des Ladebalkens
def set_total_length(length):
    global total_length_of_audio
    total_length_of_audio = length

def update_progress(length):
    global processed_length
    processed_length += length
    percentage = round(100 * (processed_length / total_length_of_audio))
    recordning_label.config(text=f"Recognition: {percentage}%")

def create_folder(folder_path):
    # Überprüft, ob der Pfad existiert
    if not os.path.exists(folder_path):
        # Erstellt den Ordner, falls er nicht existiert
        os.makedirs(folder_path)
    else:
        # Zählt hoch, bis ein nicht existierender Pfad gefunden wird
        counter = 2
        new_folder_path = f"{folder_path}_{counter}"
        while os.path.exists(new_folder_path):
            counter += 1
            new_folder_path = f"{folder_path}_{counter}"

        # Erstellt den neuen Ordner
        os.makedirs(new_folder_path)

# %%
"""AI Kommunikation"""
def text_to_blog(audio_text, safe_path=None, style=None,
                 extra_instruction=""):
    global blog_instructions_path
    if style is None:
        style = "Zufälliger Stil"
    # Öffnet die Datei und liest den Inhalt
    with open(blog_instructions_path, 'r', encoding='utf-8') as file:
        blog_instructions = file.read()

    # Abrufen der Werte der Schieberegler
    # print(sliders["temperature"].get(), sliders["top_p"].get(), sliders["frequency_penalty"].get(), sliders["presence_penalty"].get())

    # Kombiniert den Audio-Text und die Blog-Anweisungen und verwendet die Werte der Schieberegler direkt
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": audio_text + "\n" + blog_instructions + extra_instruction},
        ],
        max_tokens=2000,  # Legen Sie die maximale Anzahl von Tokens für die Antwort fest
        temperature=sliders["temperature"].get(),  
        top_p=sliders["top_p"].get(),  
        frequency_penalty=sliders["frequency_penalty"].get(),  
        presence_penalty=sliders["presence_penalty"].get(),  
    )

    blog_text = response['choices'][0]['message']['content'].strip()
    if safe_path is not None:
        blog_to_pic = f"Erstelle mir ein Bild im Stil '{style}' aus der folgenden Erzählung. Überlege dir dafür aus einigen Ereignissen der Geschichte ein Titelbild. Das kann eine bestimmte Situation aus der Geschichte sein oder auch mehrere Ereignisse, die zusammen ein verschmolzenes Bild ergeben. Sei kreativ, aber mach das Bild quadratisch. Es ist wichtig, dass der Stil gut wiedererkennbar ist. Die Erzählung lautet: \n"#Das Bild soll alle Ereignisse in einem Bild darstellen. Die Ereignisse sollen in dem Bild ineinander übergehen. Stelle die im Text beschriebenen Personen nicht mit dar! Die Erzählung lautet: \n "
        pic_style =f'\n \n Das mit der KI generierte Bild ist erzeugt im Stil: "{style}"'
        # Öffnet die Datei und schreibt den Antworttext hinein
        with open(safe_path, 'w', encoding='utf-8') as file:
            file.write(blog_to_pic + blog_text + pic_style)
    return blog_text

def blog_to_picture(blog_text, style=None, save_path=None, 
                    pic_amount=1, cache_path=None):
    global picture_instructions_path
    global safety_guide_path
    if style is None:
        style="Denk dir einen zur Geschichte passenden aber außergewöhnlichen Stil aus!"
    # Öffnet die Datei und liest den Inhalt
    with open(picture_instructions_path, 'r', encoding='utf-8') as file:
        picture_instruction = file.read()
    # Fügt den vorbereitenden Text und den Stil zur picture_instruction hinzu
    picture_instruction = f'Bitte gebe mir ausschließlich einen prompt für DALLE 3 für ein Bild im Stil: "{style}".\n{picture_instruction}'
    # Öffnet die Datei und liest den Inhalt
    with open(safety_guide_path, 'r', encoding='utf-8') as file:
        safety_guide_instruction = file.read()
    if save_path is None:
        raise ValueError("Choose a save path for the pictures")
    response_pic_instruction = openai.ChatCompletion.create(
        model="gpt-4",#"gpt-4-0613",  # Ändern Sie das Modell auf GPT-4, wenn es veröffentlicht wird
        messages=[
            {"role": "user", "content": picture_instruction + "\n" + blog_text},
        ],
        max_tokens=500,  # Legen Sie die maximale Anzahl von Tokens für die Antwort fest
        temperature=0.3,  # Steuert die Kreativität der Antwort
        top_p=0.9,  # Steuert die Diversität der Antwort
        frequency_penalty=0.5,  # Bestraft häufige Tokens
        presence_penalty=0.0,  # Bestraft oder belohnt neue Tokens
    )


    dalle_instruction = response_pic_instruction['choices'][0]['message']['content'].strip()
    if len(dalle_instruction) > 1000: # Maximale Länge für Dalle 3 Promt
        response_pic_instruction = openai.ChatCompletion.create(
            model="gpt-4",#"gpt-4-0613",  # Ändern Sie das Modell auf GPT-4, wenn es veröffentlicht wird
            messages=[
                {"role": "user", "content": f"Der Dalle3 prompt Befehl:\n '{dalle_instruction}' \n hat inklusive Leerzeichen mehr als 1000 Zeichen. Bitte kürze Ihn auf weniger auf 1000 Zeichen inklusive Leerzeichen! Der Stil des Bildes '{style}' soll dabei unbedingt genau so erhalten bleiben."},
            ],
            max_tokens=500,  # Legen Sie die maximale Anzahl von Tokens für die Antwort fest
            temperature=0.3,  # Steuert die Kreativität der Antwort
            top_p=0.9,  # Steuert die Diversität der Antwort
            frequency_penalty=0.5,  # Bestraft häufige Tokens
            presence_penalty=0.0,  # Bestraft oder belohnt neue Tokens
        )
        dalle_instruction = response_pic_instruction['choices'][0]['message']['content'].strip()

    response_safety_guide = openai.ChatCompletion.create(
        model="gpt-4",#"gpt-4-0613",  # Ändern Sie das Modell auf GPT-4, wenn es veröffentlicht wird
        messages=[
            {"role": "user", "content": safety_guide_instruction + "\n" + dalle_instruction},
        ],
        max_tokens=500,  # Legen Sie die maximale Anzahl von Tokens für die Antwort fest
        temperature=0.3,  # Steuert die Kreativität der Antwort
        top_p=0.9,  # Steuert die Diversität der Antwort
        frequency_penalty=0.5,  # Bestraft häufige Tokens
        presence_penalty=0.0,  # Bestraft oder belohnt neue Tokens
    )
    dalle_safe_instruction = response_safety_guide['choices'][0]['message']['content'].strip()
    # Generiert die Bilder
    response = openai.Image.create(
        model="dall-e-3",
        prompt = dalle_safe_instruction,
        n=pic_amount,  # Anzahl der Bilder
        size="1024x1024",
        quality="standard",
    )

    # Iteriert über die generierten Bilder
    for i, image_data in enumerate(response['data'], start=1):
        # Holt die URL des generierten Bildes
        image_url = image_data['url']

        # Lädt das Bild herunter
        response = requests.get(image_url, stream=True)

        # Überprüft, ob die Anfrage erfolgreich war
        response.raise_for_status()
        save_path = save_path.replace('.txt', f'_{i}.png')
        # Speichert das Bild in der Datei
        with open(save_path, 'wb') as file:
            response.raw.decode_content = True  # Stellt sicher, dass der Inhalt richtig dekodiert wird
            shutil.copyfileobj(response.raw, file)
    
    # Speicher Cache Daten
    if cache_path is not None:
        with open(os.path.join(cache_path, 'Dalle_instruction.txt'), 'w', encoding='utf-8') as file:
            file.write(dalle_instruction)
        with open(os.path.join(cache_path, 'Dalle_instruction_safe.txt'), 'w', encoding='utf-8') as file:
            file.write(dalle_safe_instruction)

# Funktion, um den Wert des Schiebereglers zu holen (optional)
def get_slider_value(slider):
    return(slider.get())

# %%
"""Licence"""
def get_license_folder_path():
    # Ermitteln des aktuellen Skriptpfads
    current_script_path = os.path.abspath(__file__)
    # Ermitteln des übergeordneten Verzeichnisses des aktuellen Skripts (zwei Ebenen nach oben)
    parent_directory = os.path.dirname(os.path.dirname(current_script_path))
    # Pfad zum Licence-Ordner im übergeordneten Verzeichnis
    license_folder_path = os.path.join(parent_directory, 'licence')
    return license_folder_path

def check_and_load_api_key():
    license_folder_path = get_license_folder_path()
    key_file_path = os.path.join(license_folder_path, 'openai_key.txt')

    if os.path.exists(key_file_path):
        with open(key_file_path, 'r') as file:
            openai.api_key = file.read().strip()
        display_key_active()
    else:
        display_key_entry()

def is_valid_openai_key(api_key):
    """
    Überprüft, ob der gegebene OpenAI API-Schlüssel gültig ist,
    indem eine einfache Anfrage an die OpenAI API gesendet wird.
    """
    test_url = "https://api.openai.com/v1/engines"  # Eine Anfrage, die keine Kosten verursacht
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    try:
        response = requests.get(test_url, headers=headers)
        if response.status_code == 200:
            return True  # Der API-Schlüssel ist gültig
        else:
            return False  # Ungültiger API-Schlüssel oder andere Fehler
    except Exception as e:
        print(f"Es gab einen Fehler bei der Überprüfung des API-Schlüssels: {e}")
        return False

def save_api_key_to_file(key):
    license_folder_path = get_license_folder_path()
    os.makedirs(license_folder_path, exist_ok=True)
    with open(os.path.join(license_folder_path, 'openai_key.txt'), 'w') as file:
        file.write(key)
    openai.api_key = key

def display_licensing_ui():
    window.geometry("600x200")  # Fenstergröße auf 600x200 Pixel einstellen
    api_key_label.pack(pady=20)
    api_key_entry.pack(pady=20)
    api_key_button.pack(pady=20)
    main_paned_window.pack_forget()

def display_main_ui():
    window.geometry("") # Stellt die Windowgröße auf default, sodass alle Elemente dargestellt werden
    api_key_label.pack_forget()
    api_key_entry.pack_forget()
    api_key_button.pack_forget()
    #key_active_label.pack(pady=20)
    main_paned_window.pack(fill=tk.BOTH, expand=True)

def save_api_key():
    key = api_key_entry.get()
    if key and is_valid_openai_key(key):
        license_folder_path = get_license_folder_path()
        os.makedirs(license_folder_path, exist_ok=True)
        with open(os.path.join(license_folder_path, 'openai_key.txt'), 'w') as file:
            file.write(key)
        openai.api_key = key
        display_main_ui()
    else:
        messagebox.showerror("Fehler", "Der eingebene OpenAI API Key ist ungültig!")

def display_key_entry():
    api_key_label.pack(pady=20)
    api_key_entry.pack(pady=20)
    api_key_button.pack(pady=20)

def display_key_active():
    #key_active_label.pack(pady=20)
    api_key_label.pack_forget()
    api_key_entry.pack_forget()
    api_key_button.pack_forget()

def open_change_api_key_window():
    change_window = tk.Toplevel(window)
    change_window.title("Change API Key")
    change_window.geometry("600x200")

    change_api_key_label = tk.Label(change_window, text="Enter your new OpenAI API Key:")
    change_api_key_entry = tk.Entry(change_window, width=60)
    change_api_key_button = tk.Button(change_window, text="Save New API Key", command=lambda: save_new_api_key(change_api_key_entry.get(), change_window))

    change_api_key_label.pack(pady=20)
    change_api_key_entry.pack(pady=20)
    change_api_key_button.pack(pady=20)

def save_new_api_key(key, change_window):
    if key and is_valid_openai_key(key):
        save_api_key_to_file(key)
        print("Neuer Key gespeichert")
    else:
        messagebox.showerror("Fehler", "Der eingegebene OpenAI API Key ist ungültig!")
    change_window.destroy()  # Schließt das Fenster für den API-Key-Wechsel

# %%
"""Gui"""
def return_to_default(label_text=False,
                      recording_button=False,
                      return_full_text=False):
    global full_text
    if label_text:
        recordning_label.config(text="Press the button to start recording \n"
                                "or load an Audio File.")
    if recording_button:
        record_button.config(bg="gray")
    if return_full_text:
        full_text = ""

# Globale Definition der Schieberegler für picture_pane
picture_sliders = {}

def create_picture_sliders():
    global picture_sliders
    picture_sliders = {
        "img_temperature": tk.Scale(picture_pane, from_=0, to=1, resolution=0.1, orient="horizontal", label="Bild-Kreativität"),
        "img_top_p": tk.Scale(picture_pane, from_=0, to=1, resolution=0.1, orient="horizontal", label="Bild-Diversität"),
        "img_frequency_penalty": tk.Scale(picture_pane, from_=0, to=1, resolution=0.1, orient="horizontal", label="Bestrafung häufiger Bild-Tokens"),
        "img_presence_penalty": tk.Scale(picture_pane, from_=0, to=1, resolution=0.1, orient="horizontal", label="Bestrafung/Belohnung neuer Bild-Tokens")
    }

    # Setze Standardwerte für die Bild-Schieberegler
    picture_sliders["img_temperature"].set(0.6)
    picture_sliders["img_top_p"].set(1.0)
    picture_sliders["img_frequency_penalty"].set(0.5)
    picture_sliders["img_presence_penalty"].set(0.0)

def toggle_style_entry():
    if not generate_pictures_var.get():
        if picture_pane.winfo_ismapped():
            top_paned_window.remove(picture_pane)
        enter_style_label.pack_forget()
        style_entry.pack_forget()
        # Entferne die Bild-Schieberegler vom Bildschirm
        for slider in picture_sliders.values():
            slider.pack_forget()

    else:
        # Zeige das picture_pane an, wenn die Checkbox aktiviert ist
        if not picture_pane.winfo_ismapped():
            top_paned_window.add(picture_pane)
        enter_style_label.pack(pady=(5,0))
        style_entry.pack(pady=(0,20))

        # Platziere die Bild-Schieberegler auf dem Bildschirm
        for slider in picture_sliders.values():
            slider.pack(pady=(5,5))

        
window = tk.Tk()
window.title("Speech Recognition")

# API-Key Eingabefeld und Button
api_key_label = tk.Label(window, text="Enter your OpenAI API Key:")
api_key_entry = tk.Entry(window, width=60)  # Breite auf 60 Zeichen einstellen
api_key_button = tk.Button(window, text="Save API Key", command=save_api_key)

# Überprüfen, ob der API-Key bereits gespeichert ist
# check_and_load_api_key()

# Haupt-PanedWindow-Widget, das vertikal aufgeteilt ist
main_paned_window = tk.PanedWindow(window, orient=tk.VERTICAL)
main_paned_window.pack(fill=tk.BOTH, expand=True)

# Oberes PanedWindow-Widget für die linken und rechten Bereiche
top_paned_window = tk.PanedWindow(main_paned_window, orient=tk.HORIZONTAL)
main_paned_window.add(top_paned_window)

# Linker Bereich für Speech Recognition
left_pane = tk.Frame(top_paned_window, relief=tk.RAISED, borderwidth=2)
top_paned_window.add(left_pane)

# Rechter Bereich für KI-Request
right_pane = tk.Frame(top_paned_window, relief=tk.RAISED, borderwidth=2)
top_paned_window.add(right_pane)

# Rechter Bereich für KI-Request
picture_pane = tk.Frame(top_paned_window, relief=tk.RAISED, borderwidth=2)
top_paned_window.add(picture_pane)

# Unterer Bereich (unter left_pane und right_pane)
generade_pane = tk.Frame(main_paned_window, relief=tk.RAISED, borderwidth=2)
main_paned_window.add(generade_pane)

# Erstellen der Widgets für den linken Bereich
speech_label = tk.Label(left_pane, text="Speech Recognition", font=("Arial", 16, 'bold'))
speech_label.pack(pady=20)
# Hier sollten Sie das Label-Widget als Attribut von 'window' definieren.
recordning_label= tk.Label(left_pane, text="Press the button to start recording \n"
                                            "or load an Audio File.")
recordning_label.pack(pady=20)

record_button = tk.Button(left_pane, text="⬤", command=start_stop_recording, bg="gray", font=("Arial", 20))
record_button.pack(pady=20)

load_button = tk.Button(left_pane, text="Load Audiofile", command=load_audio_file, font=("Arial", 12))
load_button.pack(pady=20)


# Erstellen der Widgets für den rechten Bereich
ki_label = tk.Label(right_pane, text="KI-Request", font=("Arial", 16, 'bold'))
ki_label.pack(pady=(20, 0))
# Erstellen der Widgets für den rechten Bereich
blog_label = tk.Label(right_pane, text="Text Settings:", font=("Arial", 12, 'bold'))
blog_label.pack(pady=(20, 0))

# Initialisiere das Eingabefeld für den Bildstil
extra_instruction_label = tk.Label(right_pane, text="Enter extra instructions:")
extra_instruction_entry = tk.Entry(right_pane)#, width=30)
# Zeige das Eingabefeld standardmäßig an
extra_instruction_label.pack(pady=(5,0))
extra_instruction_entry.pack(pady=(0,20), padx=(0,0))


# Erstelle die Schieberegler
sliders = {
    "temperature": tk.Scale(right_pane, from_=0, to=1, resolution=0.1, orient="horizontal", label="Kreativität", command=lambda value: get_slider_value(sliders["temperature"])),
    "top_p": tk.Scale(right_pane, from_=0, to=1, resolution=0.1, orient="horizontal", label="Diversität", command=lambda value: get_slider_value(sliders["top_p"])),
    "frequency_penalty": tk.Scale(right_pane, from_=0, to=1, resolution=0.1, orient="horizontal", label="Bestrafung häufiger Tokens", command=lambda value: get_slider_value(sliders["frequency_penalty"])),
    "presence_penalty": tk.Scale(right_pane, from_=0, to=1, resolution=0.1, orient="horizontal", label="Bestrafung/Belohnung neuer Tokens", command=lambda value: get_slider_value(sliders["presence_penalty"]))
}

# Setze Standardwerte für die Schieberegler
sliders["temperature"].set(0.6)
sliders["top_p"].set(1.0)
sliders["frequency_penalty"].set(0.5)
sliders["presence_penalty"].set(0.0)

# Platziere die Schieberegler auf dem Bildschirm
for slider in sliders.values():
    slider.pack(pady=(5,5))

# Checkbox für "Generate Pictures" mit Standardwert True
generate_pictures_var = tk.BooleanVar(value=True)
generate_pictures_check = tk.Checkbutton(generade_pane, text="Generate Pictures", var=generate_pictures_var, command=toggle_style_entry)
generate_pictures_check.pack(side=tk.LEFT, pady=(10, 0))

#

# Initialisiere das Eingabefeld für den Bildstil
enter_style_label = tk.Label(picture_pane, text="Enter the picture style:")
style_entry = tk.Entry(picture_pane)
# Zeige das Eingabefeld standardmäßig an
enter_style_label.pack(pady=(5,0))
style_entry.pack(pady=(0,20))
# Erstellen der Bild-Schieberegler beim Start des Programms
create_picture_sliders()

generate_blog_button = tk.Button(generade_pane, text="Generate", command=save_to_file, font=("Arial", 12))
generate_blog_button.pack(pady=20)

# Button zum Ändern des API-Schlüssels im generade_pane hinzufügen
change_api_key_button = tk.Button(generade_pane, text="Change API-Key", command=open_change_api_key_window)
change_api_key_button.pack(pady=20)


"""Anpassen der Angezeigten größen"""
# Erhöhen der Größe des rechten Bereichs
# right_pane.config(width=400)

# Anpassen der Breite der Eingabefelder
extra_instruction_entry.config(width=50)
style_entry.config(width=50)

# Anpassen der Länge der Schieberegler
slider_length = 300  # Sie können diesen Wert anpassen, um die gewünschte Länge zu erreichen
for slider in sliders.values():
    slider.config(length=slider_length)
# %%
"""Start der Anwendung"""
if not os.path.exists(os.path.join(get_license_folder_path(), 'openai_key.txt')):
    display_licensing_ui()
else:
    check_and_load_api_key()
    display_main_ui()

window.mainloop()


